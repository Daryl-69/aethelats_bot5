"""
modal_bot3.py — Bot 3 (Qwen2.5-1.5B-Instruct + LoRA adapter) on Modal.com
===========================================================================
Model:   Qwen/Qwen2.5-1.5B-Instruct       (base — public HF, ~3GB)
Adapter: Unded-17/bot3-qwen25-resume-structurer  (LoRA — public HF, 37MB)
GPU:     T4  (plenty for 1.5B model)

Deploy:   modal deploy backend/modal_bot3.py
Test:     modal run   backend/modal_bot3.py

Secrets required:
  None — both repos are public. No HF_TOKEN needed.
  If you want to add one anyway:
    modal secret create hf-secret HF_TOKEN=hf_xxx

After deploy, copy the printed URL → set MODAL_BOT3_URL in your HF Space secrets.
"""

import json
import os
import re

import modal

# ── Config ────────────────────────────────────────────────────────────────────
BASE_MODEL   = "Qwen/Qwen2.5-1.5B-Instruct"   # public base model
ADAPTER_REPO = "Unded-17/bot3-qwen25-resume-structurer"  # public LoRA adapter
BASE_DIR     = "/model-cache/base"
ADAPTER_DIR  = "/model-cache/adapter"

_MAX_OUTPUT_TOKENS = 1024   # raised from 512 — long resumes with 5+ jobs were getting truncated


# ── Download both base model + adapter at image build time ────────────────────
def _download_models():
    """Bakes both model + adapter into the image at build time."""
    from huggingface_hub import snapshot_download

    print(f"[Bot3/build] Downloading base model: {BASE_MODEL}")
    snapshot_download(
        repo_id=BASE_MODEL,
        local_dir=BASE_DIR,
        ignore_patterns=["*.gguf", "*.bin", "original/*"],
    )

    print(f"[Bot3/build] Downloading LoRA adapter: {ADAPTER_REPO}")
    snapshot_download(
        repo_id=ADAPTER_REPO,
        local_dir=ADAPTER_DIR,
        ignore_patterns=["*.gguf", "*.bin"],
    )
    print("[Bot3/build] ✓ All weights downloaded.")


bot3_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch==2.4.0",
        "numpy<2",
        "transformers==4.44.2",  # pinned: last version compatible with torch 2.4.0
        "peft>=0.11.0",          # required to load LoRA adapters
        "accelerate",
        "sentencepiece",
        "huggingface_hub",
        "fastapi[standard]",
        extra_index_url="https://download.pytorch.org/whl/cu121",
    )
    .run_function(_download_models)   # no secret needed — both repos are public
)

app = modal.App("aethel-bot3-structurer", image=bot3_image)


# ── Request model ─────────────────────────────────────────────────────────────
from pydantic import BaseModel  # noqa: E402


class StructureRequest(BaseModel):
    sanitized_text: str
    max_new_tokens: int = _MAX_OUTPUT_TOKENS


# ── Inference class ───────────────────────────────────────────────────────────
@app.cls(
    gpu="T4",             # 1.5B model fits easily on T4
    scaledown_window=300,
    secrets=[modal.Secret.from_name("hf-secret")] if os.environ.get("MODAL_HF_SECRET") else [],
)
class Bot3Structurer:

    @modal.enter()
    def load_model(self):
        """Boot hook — loads base model + LoRA adapter onto GPU once."""
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from peft import PeftModel

        print(f"[Bot3/Modal] Loading tokenizer from {BASE_DIR} ...")
        self.tokenizer = AutoTokenizer.from_pretrained(
            BASE_DIR,
            local_files_only=True,
            trust_remote_code=True,
        )

        print(f"[Bot3/Modal] Loading base model {BASE_MODEL} onto GPU ...")
        base = AutoModelForCausalLM.from_pretrained(
            BASE_DIR,
            torch_dtype=torch.float16,
            device_map="auto",
            local_files_only=True,
            trust_remote_code=True,
        )

        print(f"[Bot3/Modal] Applying LoRA adapter from {ADAPTER_DIR} ...")
        self.model = PeftModel.from_pretrained(base, ADAPTER_DIR, local_files_only=True)
        self.model.eval()
        print("[Bot3/Modal] ✓ Qwen2.5-1.5B + LoRA ready on GPU.")

    def _build_prompt(self, sanitized_text: str) -> str:
        """Qwen2.5 ChatML format — must match fine-tuning format."""
        system_msg = (
            "You are a precise resume parser. "
            "Extract ALL technical skills mentioned ANYWHERE in the resume — "
            "not just in the Skills section. Also scan: job responsibility bullets, "
            "project descriptions, certifications, and achievement statements. "
            "A skill used in context (e.g. 'built dashboard in React') counts just as much as listed skills. "
            "For job_history, include the responsibilities/bullets list for each role. "
            "For total_years_experience compute from date ranges; if 'Present' use 2025. "
            "Return ONLY valid JSON with these exact keys: "
            "total_years_experience (float), technical_skills (list of strings), "
            "job_history (list of {title, company, duration, responsibilities}), "
            "highest_degree (string), education (list), experience (list), "
            "work_experience_summary (object). "
            "No markdown fences, no explanation — pure JSON only."
        )
        return (
            f"<|im_start|>system\n{system_msg}<|im_end|>\n"
            f"<|im_start|>user\nParse this resume:\n\n{sanitized_text}<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )

    @staticmethod
    def _parse_output(text: str) -> dict:
        """Extract valid JSON from raw model output, with light repair."""
        text = re.sub(r"```(?:json)?", "", text).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        repaired = re.sub(r",\s*([}\]])", r"\1", text)
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            pass
        return {"error": f"Could not parse JSON. Raw output: {text[:300]}"}

    @modal.fastapi_endpoint(method="POST")
    def structure(self, req: StructureRequest) -> dict:
        """
        POST /structure
        Body: { "sanitized_text": "...", "max_new_tokens": 512 }
        Returns: { "structured_data": {...} }  or  { "error": "..." }
        """
        import torch

        prompt = self._build_prompt(req.sanitized_text)
        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            max_length=2048,
            truncation=True,
        ).to("cuda")

        eos_id = self.tokenizer.convert_tokens_to_ids("<|im_end|>")

        with torch.no_grad():
            output_ids = self.model.generate(
                **inputs,
                max_new_tokens=req.max_new_tokens,
                do_sample=False,
                temperature=1.0,
                pad_token_id=self.tokenizer.eos_token_id,
                eos_token_id=eos_id if eos_id != self.tokenizer.unk_token_id else self.tokenizer.eos_token_id,
            )

        new_tokens = output_ids[0][inputs["input_ids"].shape[1]:]
        raw_text = self.tokenizer.decode(new_tokens, skip_special_tokens=True)
        print(f"[Bot3/Modal] Raw output ({len(new_tokens)} tokens): {raw_text[:300]}")

        result = self._parse_output(raw_text)
        if "error" not in result:
            return {"structured_data": result}
        return result


# ── Local test ────────────────────────────────────────────────────────────────
@app.local_entrypoint()
def test():
    sample = """
SKILLS
Python, FastAPI, PostgreSQL, Docker, Redis, AWS, React, TypeScript

EXPERIENCE
Backend Engineer | [COMPANY]
Jan 2022 – Present

Junior Developer | [COMPANY]
Jun 2020 – Dec 2021

EDUCATION
Bachelor of Science in Computer Science, [UNIVERSITY], 2020
GPA: 3.7/4.0
"""
    structurer = Bot3Structurer()
    result = structurer.structure.remote({"sanitized_text": sample.strip()})
    print(json.dumps(result, indent=2))
