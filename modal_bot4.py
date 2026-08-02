"""
modal_bot4.py — Bot 4 (Phi-3.5 fine-tune) on Modal.com
========================================================
Deploy with:  modal deploy backend/modal_bot4.py
Test with:    modal run   backend/modal_bot4.py

This exposes a web endpoint your HF Space calls instead of
the broken HF Inference API. The GPU is ONLY active during
inference (~5s per resume), so the $5 free credit lasts months.

Setup (one-time):
  1. pip install modal
  2. modal setup          (links your Modal account)
  3. modal secret create hf-secret HF_TOKEN=<your_hf_token>
  4. modal deploy backend/modal_bot4.py
  5. Copy the printed URL into your HF Space's BOT4_MODAL_URL secret.
"""

import json
import os
import re

import modal

# ── Config ────────────────────────────────────────────────────────────────────
MODEL_REPO = "Unded-17/bot4-phi35-resume-evaluator"
MODEL_DIR  = "/model-cache"

# ── Image: install deps and bake model weights in at build time ───────────────
# Baking the weights into the image means cold starts only cost the time
# to move weights from disk → GPU VRAM (~10-15s), not a full download.

def _download_model():
    """Called once at image build time. Downloads model into /model-cache."""
    from huggingface_hub import snapshot_download
    snapshot_download(
        repo_id=MODEL_REPO,
        local_dir=MODEL_DIR,
        token=os.environ["HF_TOKEN"],
        ignore_patterns=["*.gguf", "*.bin"],   # skip non-safetensor formats
    )


bot4_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch==2.5.1",
        "numpy<2",
        "transformers==4.46.3",  # supports tokenizers>=0.20 (required for Phi-3.5 tokenizer format)
        "accelerate",
        "sentencepiece",
        "huggingface_hub",
        "fastapi[standard]",
        extra_index_url="https://download.pytorch.org/whl/cu121",
    )
    .run_function(
        _download_model,
        secrets=[modal.Secret.from_name("hf-secret")],
    )
    .run_commands(
        "python -c \"import json, os; "
        "d='/model-cache'; "
        "os.system(f'rm -f {d}/*.py'); "
        "f1=f'{d}/config.json'; "
        "d1=json.load(open(f1)); "
        "d1.pop('auto_map', None); "
        "d1.pop('_name_or_path', None); "
        "os.remove(f1); "
        "json.dump(d1, open(f1, 'w')); "
        "f2=f'{d}/tokenizer_config.json'; "
        "d2=json.load(open(f2)); "
        "d2.pop('auto_map', None); "
        "d2.pop('_name_or_path', None); "
        "os.remove(f2); "
        "json.dump(d2, open(f2, 'w'))\""
    )
)

app = modal.App("aethel-bot4-evaluator", image=bot4_image)

# ── System prompt (must exactly match fine-tuning format) ────────────────────
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

from pydantic import BaseModel
from typing import Any

class EvaluateRequest(BaseModel):
    structured_data: dict[str, Any] = {}
    jd_skills:       list[str]      = []
    job_title:       str            = "Software Engineer"
    max_new_tokens:  int            = 1500


# ── The inference class ───────────────────────────────────────────────────────
@app.cls(
    gpu="T4",                  # cheapest GPU, plenty for Phi-3.5
    scaledown_window=300,      # keep warm for 5 min after last request
    secrets=[modal.Secret.from_name("hf-secret")],
)
class Bot4Evaluator:

    @modal.enter()
    def load_model(self):
        """Called once when the container boots. Loads model into GPU VRAM."""
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        print(f"[Bot4/Modal] Loading tokenizer from {MODEL_DIR} ...")
        self.tokenizer = AutoTokenizer.from_pretrained(
            MODEL_DIR,
            local_files_only=True
        )

        print(f"[Bot4/Modal] Loading model onto GPU ...")
        self.model = AutoModelForCausalLM.from_pretrained(
            MODEL_DIR,
            torch_dtype=torch.float16,
            device_map="auto",
            local_files_only=True
        )
        self.model.eval()
        print("[Bot4/Modal] ✓ Phi-3.5 ready on GPU.")

    def _build_prompt(self, structured_json: dict, jd_skills: list, job_title: str) -> str:
        """Build the Phi-3 chat-format prompt (identical to training format)."""
        rubric   = {"job_title": job_title, "required_skills": jd_skills}
        user_msg = (
            f"Candidate Resume JSON:\n{json.dumps(structured_json, indent=2)}\n\n"
            f"Job Description Rubric:\n{json.dumps(rubric, indent=2)}"
        )
        return (
            f"<|system|>\n{_SYSTEM_PROMPT}<|end|>\n"
            f"<|user|>\n{user_msg}<|end|>\n"
            f"<|assistant|>\n"
        )

    def _parse_output(self, text: str) -> dict:
        """Extract JSON scorecard from raw model output."""
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return {"error": f"Could not parse JSON from model output: {text[:300]}"}

    @modal.fastapi_endpoint(method="POST")
    def evaluate(self, req: EvaluateRequest) -> dict:
        """
        POST /evaluate
        Body: EvaluateRequest JSON — see model above.
        Returns the same scorecard dict as evaluator_agent.py
        """
        import torch

        prompt = self._build_prompt(req.structured_data, req.jd_skills, req.job_title)

        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            max_length=2048,
            truncation=True,
        ).to("cuda")

        with torch.no_grad():
            output_ids = self.model.generate(
                **inputs,
                max_new_tokens=req.max_new_tokens,
                temperature=0.1,
                do_sample=False,
                pad_token_id=self.tokenizer.eos_token_id,
            )

        # Decode only the newly generated tokens (not the prompt)
        new_tokens = output_ids[0][inputs["input_ids"].shape[1]:]
        raw_text   = self.tokenizer.decode(new_tokens, skip_special_tokens=True)
        print(f"[Bot4/Modal] Raw output: {raw_text[:200]}")

        return self._parse_output(raw_text)



# ── Local test (modal run backend/modal_bot4.py) ──────────────────────────────
@app.local_entrypoint()
def test():
    sample_resume = {
        "total_years_experience": 3,
        "technical_skills": ["Python", "FastAPI", "Docker", "PostgreSQL"],
        "highest_degree": "Bachelor",
        "experience": [
            {"title": "Backend Engineer", "company": "[COMPANY]",
             "duration_months": 36, "type": "Job"}
        ],
    }
    sample_skills = ["Python", "FastAPI", "Docker", "Kubernetes", "CI/CD"]

    evaluator = Bot4Evaluator()
    result = evaluator.evaluate.remote({
        "structured_data": sample_resume,
        "jd_skills": sample_skills,
        "job_title": "Backend Engineer",
    })
    print(json.dumps(result, indent=2))
