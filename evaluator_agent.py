"""
Bot 4 — Resume Evaluator (Phi-3.5 + LoRA)
==========================================
Calls the fine-tuned Phi-3.5 model via the HuggingFace Serverless
Inference API (free shared GPUs).

Priority order:
  1. COLAB_URL          — Google Colab with Cloudflare tunnel (if set)
  2. HF_ENDPOINT_URL    — dedicated HF endpoint (~$0.06/hr, always-on)
  3. HF Inference API   — FREE, shared GPU, auto-retry on cold starts

The free HF API may return 503 while the model is loading onto shared
hardware.  This module handles that automatically with exponential
back-off, retrying up to 4 times (~90s total) so the user never sees
a raw "model is loading" error.
"""

import json
import os
import re
import time
from pathlib import Path
import requests

# ── Config ────────────────────────────────────────────────────────────────────
HF_REPO_ID      = os.environ.get("HF_REPO_ID", "Unded-17/bot4-phi35-resume-evaluator")
HF_TOKEN        = os.environ.get("HF_TOKEN", "")
HF_ENDPOINT_URL = os.environ.get("HF_ENDPOINT_URL", "")
COLAB_URL       = os.environ.get("COLAB_URL", "")
# Set this in your HF Space secrets after running: modal deploy backend/modal_bot4.py
MODAL_BOT4_URL  = os.environ.get("MODAL_BOT4_URL", "")

# Retry config for HF Serverless Inference API cold starts
_MAX_RETRIES    = 2       # max retry attempts on 503 (reduced to keep UX fast)
_RETRY_DELAYS   = [10, 15]  # seconds to wait between retries (~25s total max)
_REQUEST_TIMEOUT = 60     # seconds per individual request

# ── Prompt template (must match fine-tuning format) ───────────────────────────
_SYSTEM_PROMPT = (
    "You are an objective resume scoring assistant. "
    "Score the candidate's structured JSON resume against the provided "
    "job description rubric. Return ONLY valid JSON with keys: "
    "'overall_score' (0-100), 'skill_match_score' (0-100), "
    "'experience_score' (0-100), 'education_score' (0-100), "
    "'missing_skills' (list of strings), 'strengths' (list of strings), "
    "'recommendation' (one of: Strong Hire / Hire / Maybe / No Hire), "
    "and 'reasoning' (2-3 sentence string)."
)


def _build_hf_payload(structured_json: dict, jd_skills: list[str], job_title: str, max_new_tokens: int) -> dict:
    """Build the request payload for the HuggingFace Inference API."""
    rubric = {"job_title": job_title, "required_skills": jd_skills}
    user_msg = (
        f"Candidate Resume JSON:\n{json.dumps(structured_json, indent=2)}\n\n"
        f"Job Description Rubric:\n{json.dumps(rubric, indent=2)}"
    )
    # Phi-3 chat template — same format as training
    prompt = (
        f"<|system|>\n{_SYSTEM_PROMPT}<|end|>\n"
        f"<|user|>\n{user_msg}<|end|>\n"
        f"<|assistant|>\n"
    )
    return {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": max_new_tokens,
            "temperature": 0.1,
            "do_sample": False,
            "return_full_text": False,
        },
    }


def _parse_hf_response(raw: list | dict) -> dict:
    """Extract and parse the JSON scorecard from the HF API response."""
    if isinstance(raw, list) and raw:
        text = raw[0].get("generated_text", "")
    elif isinstance(raw, dict):
        text = raw.get("generated_text", str(raw))
    else:
        text = str(raw)

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return {"error": f"Could not parse JSON from model output: {text[:300]}"}


def _call_hf_inference_api(payload: dict) -> dict:
    """
    Call the HF Serverless Inference API with automatic retry on 503 cold starts.

    When the model is not loaded on shared hardware, HF returns a 503 with
    {"error": "Model is currently loading", "estimated_time": 45.2}.
    We wait and retry automatically so the user doesn't have to.
    """
    api_url = f"https://api-inference.huggingface.co/models/{HF_REPO_ID}"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}

    for attempt in range(_MAX_RETRIES + 1):
        try:
            print(f"[Bot4] HF Inference API attempt {attempt + 1}/{_MAX_RETRIES + 1} ...")
            resp = requests.post(api_url, headers=headers, json=payload, timeout=_REQUEST_TIMEOUT)

            # 503 = model is loading on shared GPU
            if resp.status_code == 503:
                try:
                    error_data = resp.json()
                    estimated = error_data.get("estimated_time", "unknown")
                except:
                    estimated = "unknown"

                if attempt < _MAX_RETRIES:
                    wait = _RETRY_DELAYS[attempt] if attempt < len(_RETRY_DELAYS) else 30
                    print(f"[Bot4] Model loading (estimated {estimated}s). Waiting {wait}s before retry ...")
                    time.sleep(wait)
                    continue
                else:
                    return {
                        "error": (
                            f"Model is still loading after {_MAX_RETRIES} retries. "
                            f"Estimated time: {estimated}s. Please try again in ~60 seconds."
                        )
                    }

            # 429 = rate limited
            if resp.status_code == 429:
                if attempt < _MAX_RETRIES:
                    wait = 15
                    print(f"[Bot4] Rate limited. Waiting {wait}s ...")
                    time.sleep(wait)
                    continue
                return {"error": "HuggingFace rate limit exceeded. Please try again later."}

            resp.raise_for_status()
            return _parse_hf_response(resp.json())

        except requests.exceptions.Timeout:
            if attempt < _MAX_RETRIES:
                print(f"[Bot4] Request timed out. Retrying ...")
                continue
            return {"error": "HuggingFace request timed out after multiple attempts."}
        except requests.exceptions.HTTPError as e:
            error_detail = e.response.text if e.response else str(e)
            try:
                error_detail = e.response.json().get("detail", error_detail)
            except:
                pass
            return {"error": f"HF Inference API error: {error_detail}"}
        except Exception as e:
            return {"error": f"HF Inference API failed: {e}"}

    return {"error": "HF Inference API failed after all retries."}


def _groq_fallback(structured_data: dict, jd_skills: list[str], job_title: str) -> dict:
    """
    Priority 4: Fast Groq LLM fallback when all fine-tuned model endpoints are down.

    Uses llama-3.3-70b-versatile via Groq API to produce the same output schema
    as the fine-tuned Phi-3.5 model. Slightly less calibrated, but always fast
    and prevents the infinite-loading UX problem.
    """
    try:
        from groq import Groq
        import os as _os

        # Try rotating keys (same pattern as main.py)
        api_key = None
        for i in range(1, 10):
            k = _os.environ.get(f"GROQ_PRIMARY_KEY_{i}")
            if k:
                api_key = k
                break
        if not api_key:
            api_key = _os.environ.get("GROQ_API_KEY", "")
        if not api_key:
            return {"error": "No Groq API keys configured for fallback."}

        groq_client = Groq(api_key=api_key)
        rubric = {"job_title": job_title, "required_skills": jd_skills}

        prompt = (
            f"You are an objective resume scoring assistant.\n"
            f"Score this candidate's structured resume JSON against the job description rubric.\n\n"
            f"Candidate Resume JSON:\n{json.dumps(structured_data, indent=2)}\n\n"
            f"Job Description Rubric:\n{json.dumps(rubric, indent=2)}\n\n"
            f"Return ONLY valid JSON with these keys:\n"
            f"- overall_score (0-100)\n"
            f"- skill_match_score (0-100)\n"
            f"- experience_score (0-100)\n"
            f"- education_score (0-100)\n"
            f"- missing_skills (list of strings)\n"
            f"- strengths (list of strings)\n"
            f"- recommendation (one of: Strong Hire / Hire / Maybe / No Hire)\n"
            f"- reasoning (2-3 sentence string)\n"
        )

        resp = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=1024,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content.strip()
        result = json.loads(raw)
        print(f"[Bot4] ✓ Groq fallback succeeded: score={result.get('overall_score')}")
        return result
    except Exception as e:
        print(f"[Bot4] Groq fallback also failed: {e}")
        return {"error": f"All Bot 4 endpoints failed. Last: {e}"}

def evaluate_resume(
    structured_data: dict,
    jd_skills: list[str],
    job_title: str = "Software Engineer",
    max_new_tokens: int = 1024,
) -> dict:
    """
    Run Bot 4 inference.

    Priority order:
      1. COLAB_URL        — Google Colab GPU via Cloudflare tunnel
      2. HF_ENDPOINT_URL  — dedicated HF endpoint (fastest, ~$0.06/hr)
      3. HF Inference API — free, shared GPU, auto-retry on cold starts

    Args:
        structured_data: The JSON produced by Bot 3 (structure_agent).
        jd_skills:       List of required skills from the JD Builder.
        job_title:       The target job title string.
        max_new_tokens:  Max tokens to generate.

    Returns:
        A dict with keys: overall_score, skill_match_score,
        experience_score, education_score, missing_skills,
        strengths, recommendation, reasoning.
        On failure, returns {"error": "<message>"}.
    """
    if not HF_TOKEN:
        return {
            "error": (
                "HF_TOKEN is not set. "
                "1) Get a free token at https://huggingface.co/settings/tokens  "
                "2) Set HF_TOKEN env var  "
                "3) Run scripts/upload_bot4_to_hf.py to upload your model first."
            )
        }

    payload = _build_hf_payload(structured_data, jd_skills, job_title, max_new_tokens)

    # ── Priority 1: Modal.com GPU endpoint (free $5 credit, serverless) ────────
    modal_url = os.environ.get("MODAL_BOT4_URL", MODAL_BOT4_URL)
    if modal_url:
        try:
            api_url = modal_url.rstrip("/")
            print(f"[Bot4] Trying Modal endpoint: {api_url}")
            resp = requests.post(
                api_url,
                json={
                    "structured_data": structured_data,
                    "jd_skills": jd_skills,
                    "job_title": job_title,
                    "max_new_tokens": max_new_tokens,
                },
                timeout=120,   # Allow enough time for Modal serverless GPU cold start (can take 60-90s)
            )
            resp.raise_for_status()
            result = resp.json()
            if "error" not in result:
                print("[Bot4] ✓ Modal GPU succeeded.")
                return result
            print(f"[Bot4] Modal returned error: {result['error']}. Falling through ...")
        except Exception as e:
            print(f"[Bot4] Modal unavailable ({e}). Falling through ...")

    # ── Priority 2: HF Dedicated Endpoint ─────────────────────────────────────
    hf_endpoint = os.environ.get("HF_ENDPOINT_URL", HF_ENDPOINT_URL)
    if hf_endpoint:
        try:
            api_url = hf_endpoint.rstrip("/")
            print(f"[Bot4] Trying HF Dedicated Endpoint at: {api_url}")
            resp = requests.post(api_url, headers={"Authorization": f"Bearer {HF_TOKEN}"},
                                 json=payload, timeout=_REQUEST_TIMEOUT)
            resp.raise_for_status()
            result = _parse_hf_response(resp.json())
            if "error" not in result:
                print("[Bot4] ✓ HF Dedicated Endpoint succeeded.")
                return result
            print(f"[Bot4] Dedicated endpoint returned error. Falling through ...")
        except Exception as e:
            print(f"[Bot4] Dedicated endpoint failed ({e}). Falling through ...")

    # ── Priority 3: HF Free Inference API (likely 404 for custom models) ───────
    print(f"[Bot4] Using HF Free Inference API: {HF_REPO_ID}")
    print("[Bot4] Note: first request may take 30-90s while model loads on shared GPU.")
    hf_result = _call_hf_inference_api(payload)
    if "error" not in hf_result:
        return hf_result
    print(f"[Bot4] HF Free API failed: {hf_result.get('error')}. Trying Groq fallback...")

    # ── Priority 4: Groq LLM fallback (fast, always-on) ───────────────────────
    return _groq_fallback(structured_data, jd_skills, job_title)
