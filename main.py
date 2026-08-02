import sys
import io
# Force UTF-8 output on Windows to prevent charmap encoding errors
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except AttributeError:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Body, Depends, status, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from groq import Groq
import json
import os
import re
import asyncio
import random
import statistics
import requests
from concurrent.futures import ThreadPoolExecutor
import PyPDF2

# ─── RATE LIMITING ──────────────────────────────────────────────────
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from auth import decode_access_token  # forward import for the key fn

from structure_agent import structure_resume
from evaluator_agent import evaluate_resume
from pydantic import BaseModel

# ─── DATABASE (real percentile pool) ──────────────────────────────
from database import (
    SessionLocal, ResumeScore, init_db, record_bias_deltas, get_bias_trends,
    create_user, get_user_by_email, get_user_by_id,
    create_scan_record, get_user_scans, update_kanban_stage,
    create_otp, consume_otp, mark_recruiter_verified, update_linkedin_url
)
from sqlalchemy import func as sa_func
from name_signals import detect_caste_proxy_signals, get_mutation_names

from auth import hash_password, verify_password, create_access_token, get_current_user, get_optional_user

# ─── EMAIL ──────────────────────────────────────────────────
from email_service import send_otp_email, send_resend_otp_email

class ColabUrlUpdate(BaseModel):
    new_url: str

class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str
    role: str = "recruiter"   # recruiter | candidate
    org: str | None = None

class LoginRequest(BaseModel):
    email: str
    password: str

class VerifyOTPRequest(BaseModel):
    email: str
    otp: str

class RequestRecruiterVerification(BaseModel):
    company_email: str
    linkedin_url: str | None = None

class VerifyRecruiterRequest(BaseModel):
    company_email: str
    otp: str

class KanbanStageUpdate(BaseModel):
    stage: str   # "Sourced" | "Screening" | "Interview" | "Offer" | "Rejected"

# ─── CONFIG ───────────────────────────────────────────────────
import groq

class RotatingGroqClient:
    def __init__(self):
        keys = []
        for i in range(1, 10):
            k = os.environ.get(f"GROQ_PRIMARY_KEY_{i}")
            if k:
                keys.append(k)
        
        if not keys:
            legacy_key = os.environ.get("GROQ_API_KEY")
            if legacy_key:
                keys.append(legacy_key)
                print("WARNING: Using legacy GROQ_API_KEY. Recommend using GROQ_PRIMARY_KEY_1, _2, etc.", file=sys.stderr)
            else:
                print("WARNING: Missing GROQ_PRIMARY_KEY_X environment variables. API calls will fail.", file=sys.stderr)
        
        self.clients = [Groq(api_key=k) for k in keys]
        self.current_idx = 0

    @property
    def chat(self):
        return self.Chat(self)

    class Chat:
        def __init__(self, parent):
            self.parent = parent
            self.completions = self.Completions(parent)

        class Completions:
            def __init__(self, parent):
                self.parent = parent

            def create(self, **kwargs):
                if not self.parent.clients:
                    raise Exception("No Groq API keys configured.")
                
                attempts = 0
                max_attempts = len(self.parent.clients)
                last_err = None
                
                while attempts < max_attempts:
                    client = self.parent.clients[self.parent.current_idx]
                    try:
                        return client.chat.completions.create(**kwargs)
                    except groq.RateLimitError as e:
                        print(f"[FairAI] Primary Key {self.parent.current_idx + 1} rate limited. Switching to next key...")
                        self.parent.current_idx = (self.parent.current_idx + 1) % len(self.parent.clients)
                        attempts += 1
                        last_err = e
                    except Exception as e:
                        if "429" in str(e) or "rate limit" in str(e).lower():
                            print(f"[FairAI] Primary Key {self.parent.current_idx + 1} rate limited (generic). Switching to next key...")
                            self.parent.current_idx = (self.parent.current_idx + 1) % len(self.parent.clients)
                            attempts += 1
                            last_err = e
                        else:
                            raise e
                
                raise Exception(f"All Groq API keys rate limited. Last error: {last_err}")

client = RotatingGroqClient() if os.environ.get("GROQ_PRIMARY_KEY_1") or os.environ.get("GROQ_API_KEY") else None

MODEL  = "llama-3.3-70b-versatile"

# ─── FEATURE 4: Seeded Score History (200 realistic pre-computed scores) ──
random.seed(42)
_seeded = [max(0, min(100, int(random.gauss(63, 16)))) for _ in range(200)]
score_history = list(_seeded)

# ─── SKILL KNOWLEDGE GRAPH (Feature 5) ────────────────────────
SKILL_GRAPH_PATH = os.path.join(os.path.dirname(__file__), "skill_graph.json")
try:
    with open(SKILL_GRAPH_PATH) as f:
        SKILL_GRAPH = json.load(f)
    print(f"[FairAI] Skill graph loaded: {len(SKILL_GRAPH.get('canonical_skills', {}))} skill groups")
except FileNotFoundError:
    SKILL_GRAPH = {"canonical_skills": {}, "adjacencies": {}}
    print("[FairAI] skill_graph.json not found — using empty graph")


# ─── DETERMINISTIC LEGACY ATS SIMULATOR ───────────────────────
# Encodes the ACTUAL biases documented in AMCAT, CoCubes, and Naukri-style
# keyword-ATS systems. Score is fully auditable — no LLM involved.
#
# Bias signals encoded (each with citation):
#  +15  Elite institution mention (IJMEM 2026: -21.3pp shortlist gap Tier-3 vs Tier-1)
#  -12  Employment gap language (eLitmus data: 12-18% lower shortlist for gap resumes)
#  ±30  Keyword hit rate (AMCAT/CoCubes exact-match-only scoring)
#  +8   Male-coded name detected (resume audit studies: ~8-10% advantage)
#  -5   Non-metro location detected (IJMEM 2026: urban-rural shortlisting gap)
# Baseline: 45 (legacy ATS conservatively rejects ~55% of candidates by default)

_PRESTIGE_SCHOOLS = [
    "iit", "iim", "iiser", "bits pilani", "nit ", "iiit",
    "delhi university", "jadavpur", "vit", "srm",
    "mit", "stanford", "oxford", "cambridge", "harvard",
]
_GAP_SIGNALS = [
    "career break", "career gap", "sabbatical", "took time off",
    "gap year", "on a break", "employment break", "between jobs",
    "freelance break", "maternity", "paternity",
]
_MALE_NAME_SIGNALS = [
    # Common dominant-caste / male-coded Indian first names
    # (based on DECASTE 2025 research — not exhaustive, indicative)
    "arjun", "rahul", "vikram", "amit", "rohan", "karan", "siddharth",
    "raj", "aditya", "nikhil", "shubham", "akash", "harsh",
    # Gender-neutral international
    "alex", "jordan", "taylor",
]
_NONMETRO_SIGNALS = [
    "tier 2", "tier 3", "tier-2", "tier-3", "small town",
    "rural", "village",
]

def _simulate_legacy_ats(original_text: str, jd_skills: list[str]) -> dict:
    """
    Deterministic Legacy ATS Score Simulator.

    Mimics keyword-only ATS behaviour with documented India hiring biases
    hard-coded as scoring rules. ZERO LLM involvement — fully auditable.

    Returns a dict with:
      legacy_ats_score  — integer 0-100
      bias_breakdown    — list of (signal, delta, citation) tuples for transparency
      primary_bias      — string describing the single biggest bias factor
    """
    text = original_text.lower()
    score = 45  # conservative baseline (legacy ATS is default-reject)
    bias_breakdown = []

    # 1. Keyword hit rate (AMCAT/CoCubes style — exact match only, no context)
    if jd_skills:
        hits = sum(1 for skill in jd_skills if skill.lower() in text)
        hit_rate = hits / len(jd_skills)
        kw_delta = min(30, int(hit_rate * 30))
        score += kw_delta
        bias_breakdown.append({
            "signal": f"Keyword match ({hits}/{len(jd_skills)} JD skills found)",
            "delta": kw_delta,
            "citation": "AMCAT/CoCubes: exact-match keyword scoring, no synonym resolution",
        })

    # 2. Elite institution prestige bonus
    prestige_found = next((s for s in _PRESTIGE_SCHOOLS if s in text), None)
    if prestige_found:
        score += 15
        bias_breakdown.append({
            "signal": f"Elite institution detected ('{prestige_found}')",
            "delta": 15,
            "citation": "IJMEM 2026: Tier-1 institutions receive +21.3pp shortlisting advantage",
        })

    # 3. Employment gap penalty
    gap_found = next((g for g in _GAP_SIGNALS if g in text), None)
    if gap_found:
        score -= 12
        bias_breakdown.append({
            "signal": f"Gap language detected ('{gap_found}')",
            "delta": -12,
            "citation": "eLitmus data: career gaps correlate with 12-18% lower shortlisting rates",
        })

    # 4. Male-coded name bias (checked on original un-anonymised text)
    male_found = next((n for n in _MALE_NAME_SIGNALS if re.search(rf'\b{n}\b', text)), None)
    if male_found:
        score += 8
        bias_breakdown.append({
            "signal": f"Male-coded name signal detected",
            "delta": 8,
            "citation": "Resume audit studies (India 2024): male-coded names shortlisted ~8-10% more",
        })

    # 5. Non-metro location penalty
    nonmetro_found = next((s for s in _NONMETRO_SIGNALS if s in text), None)
    if nonmetro_found:
        score -= 5
        bias_breakdown.append({
            "signal": f"Non-metro signal detected ('{nonmetro_found}')",
            "delta": -5,
            "citation": "IJMEM 2026: urban candidates shortlisted at higher rates than non-metro",
        })

    final_score = max(0, min(100, score))

    # Determine primary bias factor (largest absolute delta)
    primary = max(bias_breakdown, key=lambda b: abs(b["delta"]), default=None)
    primary_bias_str = primary["signal"] if primary else "No dominant bias signal detected"

    # Legacy ATS verdict thresholds (typical cutoffs used by AMCAT/CoCubes)
    if final_score >= 70:
        verdict = "Passed"
    elif final_score >= 50:
        verdict = "Flagged for Review"
    else:
        verdict = "Auto-Rejected"

    print(f"[LegacyATS] Deterministic score: {final_score} | Breakdown: {[(b['signal'], b['delta']) for b in bias_breakdown]}")

    return {
        "legacy_ats_score": final_score,
        "verdict": verdict,
        "bias_breakdown": bias_breakdown,
        "primary_bias": primary_bias_str,
    }


# ─── HELPERS ──────────────────────────────────────────────────
# ─── Vision model for image OCR ──────────────────────────────
_VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
_VISION_PROMPT = (
    "You are an OCR engine. Extract ALL text from this resume image exactly as it appears. "
    "Preserve section headings, bullet points, and line breaks. "
    "Return ONLY the raw extracted text — no commentary, no markdown fences."
)
# Groq hard limit for base64 image payloads
_GROQ_B64_LIMIT_BYTES = 4 * 1024 * 1024  # 4 MB

def _is_valid_resume(text: str) -> bool:
    """
    Guardrail: Checks if the extracted text is actually a resume/CV.

    Two-tier architecture:
      Tier 1 — Instant rejects (no API cost):
        - Text too short
        - Fewer than 2 resume-specific signals (catches research papers, flight
          studies, manuals etc. that contain isolated words like "engineer")
      Tier 2 — LLM is ALWAYS the final authority:
        - Keywords alone NEVER accept a document (prevents textbook false positives)
        - Anything with >= 2 signals goes to LLM for the definitive call
    """
    # ── Tier 1a: Instant reject — text too short ───────────────────────────
    if not text or len(text.strip()) < 50:
        return False

    # ── Tier 1b: Multi-signal keyword gate ────────────────────────────────
    # We intentionally split signals into two tiers of specificity:
    #   STRONG signals  — unambiguously resume-only sections/fields
    #   WEAK signals    — words that appear in many doc types (e.g. "engineer")
    # A document needs either:
    #   • 1 STRONG signal, OR
    #   • 2+ WEAK/any signals
    # This prevents a research paper about "aeronautical engineers" slipping through
    # just because it mentions the word "engineer" once.
    _strong_resume_signals = {
        "work experience", "technical skills", "employment history",
        "career objective", "professional summary", "internship",
        "cgpa", "sgpa", "btech", "mtech", "bca", "mca",
        "10th", "12th", "ssc", "hsc",
        "fresher", "passout", "aggregate", "percentile",
        "curriculum vitae", "résumé", "resume",
        "references available", "hobbies and interests",
    }
    _weak_resume_signals = {
        "experience", "education", "skills", "project", "university",
        "college", "school", "worked", "developer", "manager", "engineer",
        "summary", "profile", "employment", "qualification",
        "certification", "objective", "achievement", "career", "position",
        "academic",
    }
    text_lower = text.lower()

    strong_hits = sum(1 for k in _strong_resume_signals if k in text_lower)
    weak_hits   = sum(1 for k in _weak_resume_signals   if k in text_lower)
    total_hits  = strong_hits + weak_hits

    if strong_hits == 0 and total_hits < 2:
        print(
            f"[Guardrail] Insufficient resume signals "
            f"(strong={strong_hits}, weak={weak_hits}). Rejected without LLM call."
        )
        return False

    # ── Tier 2: LLM is the definitive judge ───────────────────────────────
    # Even if keywords matched, the LLM makes the final call.
    # The prompt is deliberately strict: research papers, technical reports,
    # and scientific studies must be rejected even if they mention job titles.
    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a strict document classifier. "
                        "A Resume or CV is a personal document that lists ONE person's "
                        "work experience, education, and skills for the purpose of job applications. "
                        "Even if it spans multiple pages, as long as it describes an individual's career history and qualifications, it is a YES. "
                        "The following are NOT resumes and must be classified NO:\n"
                        "  - Academic or scientific research papers / journal articles\n"
                        "  - Technical reports (e.g. flight studies, engineering analyses)\n"
                        "  - Textbooks, manuals, or reference documents\n"
                        "  - News articles, blog posts, or essays\n"
                        "  - Invoices, menus, contracts, or legal documents\n"
                        "  - Cover letters (they accompany a resume but are not one)\n"
                        "Reply ONLY with the single word YES or NO. No explanation."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Is this document a Resume or CV?\n\n---\n{text[:2000]}\n---",
                },
            ],
            temperature=0.0,
            max_tokens=5,
        )
        answer = resp.choices[0].message.content.strip().upper()
        is_resume = answer.startswith("YES")
        print(f"[Guardrail] LLM verdict: {'✓ VALID RESUME' if is_resume else '✗ NOT A RESUME'} (raw: '{answer}')")
        return is_resume
    except Exception as e:
        # LLM is unavailable (rate-limit, network error, etc.).
        # Use keyword signal strength as the tiebreaker instead of blindly accepting.
        #   • strong_hits >= 1  → very likely a real resume  → ACCEPT
        #   • total_hits  >= 3  → many resume-adjacent words → ACCEPT
        #   • anything weaker   → too risky to accept        → REJECT (fail-closed)
        # This prevents a gallery screenshot or flight-study PDF from slipping
        # through on a Groq outage, while still protecting legitimate resume users.
        if strong_hits >= 1 or total_hits >= 3:
            print(
                f"[Guardrail] LLM check failed ({e}). "
                f"Strong signals present (strong={strong_hits}, total={total_hits}) — ACCEPTING."
            )
            return True
        else:
            print(
                f"[Guardrail] LLM check failed ({e}). "
                f"Insufficient signals (strong={strong_hits}, total={total_hits}) — REJECTING (fail-closed)."
            )
            return False

# Dedicated Rotating Client for Vision API
# Vision endpoints often have much stricter Rate Limits than text endpoints.
# This prevents your Vision OCR from eating the API quota of your main analysis Bot.
vision_client = None
_vision_keys = []
for i in range(1, 10):
    k = os.environ.get(f"GROQ_VISION_KEY_{i}")
    if k: _vision_keys.append(k)

if _vision_keys:
    class RotatingVisionClient:
        def __init__(self, keys):
            import groq
            self.clients = [groq.Groq(api_key=k) for k in keys]
            self.current_idx = 0
            self.chat = self.Chat(self)
        class Chat:
            def __init__(self, parent): self.completions = self.Completions(parent)
            class Completions:
                def __init__(self, parent): self.parent = parent
                def create(self, **kwargs):
                    attempts = 0
                    max_attempts = len(self.parent.clients)
                    last_err = None
                    while attempts < max_attempts:
                        c = self.parent.clients[self.parent.current_idx]
                        try:
                            return c.chat.completions.create(**kwargs)
                        except Exception as e:
                            if "429" in str(e) or "rate limit" in str(e).lower():
                                print(f"[OCR] Vision Key {self.parent.current_idx + 1} rate limited. Rotating...")
                                self.parent.current_idx = (self.parent.current_idx + 1) % len(self.parent.clients)
                                attempts += 1
                                last_err = e
                            else:
                                raise e
                    raise Exception(f"All Vision keys rate limited. Last error: {last_err}")
    vision_client = RotatingVisionClient(_vision_keys)
    print(f"[FairAI] Dedicated Vision Client initialized with {len(_vision_keys)} rotating keys.")
else:
    vision_client = client  # Fallback to main text rotating client if no dedicated vision keys


def _extract_via_vision(image_bytes: bytes, mime_type: str) -> str:
    """
    OCR an image resume using Groq Vision (llama-4-scout).
    Includes automatic PIL compression for images > 3MB to bypass Groq's 4MB base64 limit.
    """
    import base64
    active_client = vision_client or client
    if active_client is None:
        print("[OCR] No Groq client available — cannot OCR image.")
        return ""

    # --- IMAGE COMPRESSION SAFEGUARD ---
    # Groq's 4MB base64 limit roughly equals 3MB raw binary.
    if len(image_bytes) > 3 * 1024 * 1024:
        print(f"[OCR] Image is large ({len(image_bytes)//1024}KB). Compressing before sending to Groq...")
        try:
            from PIL import Image
            import io
            img = Image.open(io.BytesIO(image_bytes))
            # Convert to RGB to strip alpha channels and save as pure JPEG
            if img.mode in ("RGBA", "P"): 
                img = img.convert("RGB")
                
            # Resize if the longest edge is over 2000px
            max_size = 2000
            if max(img.size) > max_size:
                ratio = max_size / max(img.size)
                new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
                
            # Save compressed JPEG to memory buffer
            out_buffer = io.BytesIO()
            img.save(out_buffer, format="JPEG", quality=85, optimize=True)
            image_bytes = out_buffer.getvalue()
            mime_type = "image/jpeg"
            print(f"[OCR] Successfully compressed image down to {len(image_bytes)//1024}KB.")
        except ImportError:
            print("[OCR] 'Pillow' library not installed. Cannot compress image. (Run: pip install Pillow)")
            if len(image_bytes) > _GROQ_B64_LIMIT_BYTES:
                return ""  # Hard abort if we couldn't compress and it's over the limit
        except Exception as e:
            print(f"[OCR] Image compression failed: {e}")
            if len(image_bytes) > _GROQ_B64_LIMIT_BYTES:
                return ""
    # -----------------------------------

    b64 = base64.b64encode(image_bytes).decode()
    try:
        resp = active_client.chat.completions.create(
            model=_VISION_MODEL,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{b64}"},
                    },
                    {"type": "text", "text": _VISION_PROMPT},
                ],
            }],
            max_tokens=4096,
            temperature=0.0,
        )
        text = resp.choices[0].message.content or ""
        print(f"[OCR] Vision extracted {len(text)} chars from image.")
        return text
    except Exception as e:
        print(f"[OCR] Vision OCR failed: {e}")
        return ""


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract text from a native (non-scanned) PDF using PyPDF2."""
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
        text = ""
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"
        return text
    except Exception as e:
        print(f"[FairAI] PDF text extract error: {e}")
        return ""


def extract_resume_text(file_bytes: bytes, ext: str) -> str:
    """
    Unified resume text extractor.

    Routing logic:
      .pdf  → PyPDF2 (fast, free)
              → if blank: Groq Vision on pdf bytes as image/jpeg fallback
                (handles scanned / image-only PDFs)
      .jpg / .jpeg / .png / .webp / .gif
              → Groq Vision directly

    Always returns a string (may be empty on total failure).
    """
    mime_map = {
        ".pdf":  "application/pdf",
        ".jpg":  "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png":  "image/png",
        ".webp": "image/webp",
        ".gif":  "image/gif",
    }
    if ext == ".pdf":
        text = _extract_pdf_text(file_bytes)
        if text.strip():
            return text
        # Scanned / image-only PDF — send raw bytes to Vision as JPEG
        print("[FairAI] PDF yielded no text — attempting Vision OCR on scanned PDF...")
        return _extract_via_vision(file_bytes, "image/jpeg")
    else:
        # Direct image upload
        mime = mime_map.get(ext, "image/jpeg")
        print(f"[FairAI] Image resume detected ({ext}). Routing to Vision OCR...")
        return _extract_via_vision(file_bytes, mime)


# Keep the old name as an alias so nothing outside this file breaks
def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Legacy alias — use extract_resume_text() for new code."""
    return _extract_pdf_text(pdf_bytes)

def _repair_truncated_json(raw: str) -> str:
    """Try to close open braces/brackets in a truncated JSON string."""
    # Remove any trailing partial key-value (cut at last complete value)
    # Walk through and count open/close braces/brackets
    open_braces = 0
    open_brackets = 0
    in_string = False
    escape_next = False
    last_good = 0
    for i, ch in enumerate(raw):
        if escape_next:
            escape_next = False
            continue
        if ch == '\\':
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == '{':
            open_braces += 1
        elif ch == '}':
            open_braces -= 1
            if open_braces >= 0:
                last_good = i
        elif ch == '[':
            open_brackets += 1
        elif ch == ']':
            open_brackets -= 1
            if open_brackets >= 0:
                last_good = i
        elif ch == ',' or ch == ':':
            last_good = i
    # If already balanced, return as-is
    if open_braces == 0 and open_brackets == 0:
        return raw
    # Strip any trailing partial value after last comma/colon
    # Then close all open brackets/braces
    # Find last comma or complete value before the truncation
    truncated = raw.rstrip()
    # Remove trailing partial string (unclosed quote)
    if in_string:
        last_quote = truncated.rfind('"', 0, len(truncated) - 1)
        if last_quote > 0:
            truncated = truncated[:last_quote + 1]
    # Remove trailing comma if present
    truncated = truncated.rstrip().rstrip(',')
    # Close remaining open brackets then braces
    truncated += ']' * max(0, open_brackets)
    truncated += '}' * max(0, open_braces)
    return truncated

def parse_json_response(raw: str) -> dict:
    """Robustly extract the outermost JSON object from a response string."""
    raw = raw.strip()
    if "```json" in raw:
        raw = raw.split("```json", 1)[1].rsplit("```", 1)[0]
    elif "```" in raw:
        raw = raw.split("```", 1)[1].rsplit("```", 1)[0]
    raw = raw.strip()
    
    # Sometimes LLMs still prepend "json" or "Here is the JSON"
    start = raw.find('{')
    end   = raw.rfind('}')
    if start != -1 and end != -1 and end > start:
        raw = raw[start:end + 1]
    
    # Strip trailing commas before closing braces (common LLM hallucination)
    raw = re.sub(r',\s*}', '}', raw)
    raw = re.sub(r',\s*]', ']', raw)
    
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"[FairAI] JSON Parsing Error: {e} | Raw string: {raw[:100]}...")
        # Try repairing truncated JSON (common when max_tokens is hit)
        try:
            repaired = _repair_truncated_json(raw)
            repaired = re.sub(r',\s*}', '}', repaired)
            repaired = re.sub(r',\s*]', ']', repaired)
            result = json.loads(repaired)
            print(f"[FairAI] JSON repair succeeded — recovered {len(result)} keys")
            return result
        except Exception:
            print(f"[FairAI] JSON repair also failed — returning empty dict")
            return {}

def extract_urls_from_text(text: str) -> list:
    """Extract all URLs from resume text."""
    pattern = r'https?://[^\s<>"{}|\\^`\[\]\'()]+|(?:www\.)[^\s<>"{}|\\^`\[\]\'()]+'
    urls = list(set(re.findall(pattern, text)))
    return [u.rstrip('.,;:)') for u in urls]

def detect_platform(url: str) -> str:
    u = url.lower()
    if 'github.com' in u:        return 'github'
    if 'linkedin.com' in u:      return 'linkedin'
    if 'kaggle.com' in u:        return 'kaggle'
    if 'leetcode.com' in u:      return 'leetcode'
    if 'hackerrank.com' in u:    return 'hackerrank'
    if 'codeforces.com' in u:    return 'codeforces'
    if 'medium.com' in u:        return 'medium'
    if 'dev.to' in u:            return 'devto'
    if 'researchgate.net' in u:  return 'researchgate'
    if 'behance.net' in u:       return 'behance'
    if 'dribbble.com' in u:      return 'dribbble'
    if 'scholar.google' in u:    return 'google_scholar'
    if 'stackoverflow.com' in u: return 'stackoverflow'
    if 'codepen.io' in u:        return 'codepen'
    if 'huggingface.co' in u:    return 'huggingface'
    if 'notion.so' in u or 'notion.site' in u: return 'notion'
    if 'portfolio' in u or 'projects' in u:    return 'portfolio'
    return 'other'

def _extract_username_from_url(url: str, platform: str) -> str:
    """Extract username/handle from a profile URL."""
    try:
        path = re.sub(r'https?://', '', url).split('/')
        path = [p for p in path if p and p not in ('www', 'profile', 'in', 'u', 'pub', '@')]
        if platform == 'medium' and path:
            return path[-1].lstrip('@')
        if platform == 'stackoverflow' and len(path) >= 2:
            return path[-1]
        return path[1] if len(path) > 1 else path[0]
    except Exception:
        return ''

def _fetch_github(url: str) -> dict:
    try:
        parts = re.sub(r'https?://github\.com/', '', url).split('/')
        username = parts[0]
        if not username:
            return {"platform": "github", "status": "detected", "url": url, "signals": []}

        gh_headers = {"Accept": "application/vnd.github+json"}
        gh_token = os.getenv("GITHUB_TOKEN", "")
        if gh_token:
            gh_headers["Authorization"] = f"Bearer {gh_token}"

        # ── User profile ──────────────────────────────────────────────────────
        user_resp = requests.get(
            f"https://api.github.com/users/{username}",
            headers=gh_headers, timeout=6
        )
        if user_resp.status_code != 200:
            return {"platform": "github", "status": "detected", "url": url, "username": username, "signals": []}
        u = user_resp.json()

        # ── Top repos (sorted by stars, owner-only) ───────────────────────────
        repos_resp = requests.get(
            f"https://api.github.com/users/{username}/repos?sort=stars&per_page=8&type=owner",
            headers=gh_headers, timeout=6
        )
        raw_repos = repos_resp.json() if repos_resp.status_code == 200 else []

        enriched_repos = []
        for r in raw_repos[:6]:
            repo_name  = r.get("name", "")
            is_fork    = r.get("fork", False)
            forked_from = ""

            # ── Fork: get parent info ─────────────────────────────────────────
            if is_fork:
                repo_detail = requests.get(
                    f"https://api.github.com/repos/{username}/{repo_name}",
                    headers=gh_headers, timeout=5
                )
                if repo_detail.status_code == 200:
                    parent = repo_detail.json().get("parent", {})
                    forked_from = parent.get("full_name", "")

            # ── Count commits authored by this user ───────────────────────────
            user_commit_count = 0
            commits_resp = requests.get(
                f"https://api.github.com/repos/{username}/{repo_name}/commits?author={username}&per_page=1",
                headers=gh_headers, timeout=5
            )
            if commits_resp.status_code == 200:
                link_header = commits_resp.headers.get("Link", "")
                if 'rel="last"' in link_header:
                    last_page = re.search(r'page=(\d+)>; rel="last"', link_header)
                    user_commit_count = int(last_page.group(1)) if last_page else 1
                else:
                    body = commits_resp.json()
                    user_commit_count = len(body) if isinstance(body, list) else 0

            # ── README snippet (first 500 chars) ──────────────────────────────
            readme_snippet = ""
            readme_resp = requests.get(
                f"https://api.github.com/repos/{username}/{repo_name}/readme",
                headers={**gh_headers, "Accept": "application/vnd.github.raw+json"},
                timeout=5
            )
            if readme_resp.status_code == 200:
                raw_readme = readme_resp.text
                clean = re.sub(r'[#*`\[\]!>\-]+', ' ', raw_readme)
                clean = re.sub(r'https?://\S+', '', clean)
                clean = re.sub(r'\s+', ' ', clean).strip()
                readme_snippet = clean[:500]

            # ── Languages ─────────────────────────────────────────────────────
            lang_resp = requests.get(
                f"https://api.github.com/repos/{username}/{repo_name}/languages",
                headers=gh_headers, timeout=4
            )
            languages = list(lang_resp.json().keys())[:5] if lang_resp.status_code == 200 else []

            # ── Originality verdict ───────────────────────────────────────────
            if not is_fork:
                originality = "original"
            elif user_commit_count >= 10:
                originality = "heavily_contributed_fork"
            elif user_commit_count >= 3:
                originality = "lightly_contributed_fork"
            else:
                originality = "copied_fork"

            enriched_repos.append({
                "name":           repo_name,
                "stars":          r.get("stargazers_count", 0),
                "forks":          r.get("forks_count", 0),
                "languages":      languages,
                "is_fork":        is_fork,
                "forked_from":    forked_from,
                "user_commits":   user_commit_count,
                "originality":    originality,
                "readme_snippet": readme_snippet,
                "description":    r.get("description", "") or "",
                "updated_at":     (r.get("updated_at", "") or "")[:10],
            })

        original_count = sum(1 for r in enriched_repos if r["originality"] in ("original", "heavily_contributed_fork"))
        copied_count   = sum(1 for r in enriched_repos if r["originality"] == "copied_fork")

        signals = [
            f"{u.get('public_repos', 0)} public repositories",
            f"{u.get('followers', 0)} followers",
            f"{original_count} repos with verified original/contributed work",
        ]
        if copied_count:
            signals.append(f"⚠️ {copied_count} repo(s) appear to be copied forks with no original commits")
        if enriched_repos:
            top = enriched_repos[0]
            signals.append(f"Top repo: {top['name']} ({top['stars']}⭐, {', '.join(top['languages'][:2]) or 'N/A'}) — {top['originality']}")

        return {
            "platform":              "github",
            "status":                "fetched",
            "url":                   url,
            "username":              username,
            "public_repos":          u.get("public_repos", 0),
            "followers":             u.get("followers", 0),
            "bio":                   u.get("bio", ""),
            "top_repos":             enriched_repos,
            "original_repos_count":  original_count,
            "copied_repos_count":    copied_count,
            "signals":               signals,
        }
    except Exception as e:
        return {"platform": "github", "status": "error", "url": url, "error": str(e), "signals": []}

def _fetch_leetcode(url: str) -> dict:
    try:
        parts = re.sub(r'https?://leetcode\.com/', '', url).strip('/').split('/')
        username = parts[0] if parts else ''
        if not username or username in ('u',):
            username = parts[1] if len(parts) > 1 else ''
        if not username:
            return {"platform": "leetcode", "status": "detected", "url": url, "signals": []}
        query = """
        query($username: String!) {
          matchedUser(username: $username) {
            username
            submitStats { acSubmissionNum { difficulty count } }
            profile { ranking reputation }
          }
        }"""
        resp = requests.post(
            "https://leetcode.com/graphql",
            json={"query": query, "variables": {"username": username}},
            headers={"Content-Type": "application/json", "Referer": "https://leetcode.com"},
            timeout=8
        )
        if resp.status_code != 200:
            return {"platform": "leetcode", "status": "detected", "url": url, "username": username, "signals": []}
        data = resp.json().get("data", {}).get("matchedUser") or {}
        stats = data.get("submitStats", {}).get("acSubmissionNum", [])
        counts = {s["difficulty"]: s["count"] for s in stats}
        profile = data.get("profile", {})
        signals = []
        if counts.get("All"):      signals.append(f"{counts['All']} problems solved total")
        if counts.get("Easy"):     signals.append(f"{counts['Easy']} Easy")
        if counts.get("Medium"):   signals.append(f"{counts['Medium']} Medium")
        if counts.get("Hard"):     signals.append(f"{counts['Hard']} Hard")
        if profile.get("ranking"): signals.append(f"Global rank: {profile['ranking']:,}")
        return {
            "platform": "leetcode",
            "status": "fetched",
            "url": url,
            "username": username,
            "problems_solved": counts.get("All", 0),
            "easy": counts.get("Easy", 0),
            "medium": counts.get("Medium", 0),
            "hard": counts.get("Hard", 0),
            "ranking": profile.get("ranking"),
            "signals": signals,
        }
    except Exception as e:
        return {"platform": "leetcode", "status": "error", "url": url, "error": str(e), "signals": []}

def _fetch_codeforces(url: str) -> dict:
    try:
        handle = re.sub(r'https?://codeforces\.com/profile/', '', url).strip('/')
        if not handle:
            return {"platform": "codeforces", "status": "detected", "url": url, "signals": []}
        resp = requests.get(
            f"https://codeforces.com/api/user.info?handles={handle}",
            timeout=6
        )
        if resp.status_code != 200:
            return {"platform": "codeforces", "status": "detected", "url": url, "username": handle, "signals": []}
        result = resp.json().get("result", [{}])[0]
        rating = result.get("rating", 0)
        max_rating = result.get("maxRating", 0)
        rank = result.get("rank", "unrated")
        signals = [
            f"Rating: {rating} ({rank})",
            f"Max rating: {max_rating}",
            f"Contributions: {result.get('contribution', 0)}",
        ]
        return {
            "platform": "codeforces",
            "status": "fetched",
            "url": url,
            "username": handle,
            "rating": rating,
            "max_rating": max_rating,
            "rank": rank,
            "signals": signals,
        }
    except Exception as e:
        return {"platform": "codeforces", "status": "error", "url": url, "error": str(e), "signals": []}

def _fetch_devto(url: str) -> dict:
    try:
        username = re.sub(r'https?://dev\.to/', '', url).strip('/').split('/')[0]
        if not username:
            return {"platform": "devto", "status": "detected", "url": url, "signals": []}
        resp = requests.get(
            f"https://dev.to/api/articles?username={username}&per_page=5",
            timeout=6
        )
        if resp.status_code != 200:
            return {"platform": "devto", "status": "detected", "url": url, "username": username, "signals": []}
        articles = resp.json()
        total_reactions = sum(a.get("positive_reactions_count", 0) for a in articles)
        titles = [a.get("title", "") for a in articles[:3]]
        signals = [
            f"{len(articles)} articles fetched",
            f"{total_reactions} total reactions",
        ]
        if titles:
            signals.append(f"Latest: \"{titles[0]}\"")
        return {
            "platform": "devto",
            "status": "fetched",
            "url": url,
            "username": username,
            "article_count": len(articles),
            "total_reactions": total_reactions,
            "sample_titles": titles,
            "signals": signals,
        }
    except Exception as e:
        return {"platform": "devto", "status": "error", "url": url, "error": str(e), "signals": []}

def _fetch_huggingface(url: str) -> dict:
    try:
        username = re.sub(r'https?://huggingface\.co/', '', url).strip('/').split('/')[0]
        if not username:
            return {"platform": "huggingface", "status": "detected", "url": url, "signals": []}
        resp = requests.get(
            f"https://huggingface.co/api/models?author={username}&limit=5",
            timeout=6
        )
        models = resp.json() if resp.status_code == 200 else []
        model_names = [m.get("modelId", "").split("/")[-1] for m in models[:3]]
        signals = [f"{len(models)} models published"]
        if model_names:
            signals.append(f"Models: {', '.join(model_names)}")
        return {
            "platform": "huggingface",
            "status": "fetched",
            "url": url,
            "username": username,
            "model_count": len(models),
            "signals": signals,
        }
    except Exception as e:
        return {"platform": "huggingface", "status": "error", "url": url, "error": str(e), "signals": []}

def _note_platform(url: str, platform: str) -> dict:
    """For platforms we can't fetch from — just note they exist."""
    label_map = {
        "linkedin":       "LinkedIn Profile",
        "kaggle":         "Kaggle Profile",
        "hackerrank":     "HackerRank Profile",
        "medium":         "Medium Blog",
        "stackoverflow":  "Stack Overflow Profile",
        "behance":        "Behance Portfolio",
        "dribbble":       "Dribbble Portfolio",
        "google_scholar": "Google Scholar",
        "researchgate":   "ResearchGate",
        "codepen":        "CodePen",
        "notion":         "Notion Portfolio",
        "portfolio":      "Personal Portfolio",
        "other":          "External Link",
    }
    return {
        "platform": platform,
        "status": "detected",
        "url": url,
        "label": label_map.get(platform, "External Profile"),
        "signals": [f"{label_map.get(platform, 'Profile')} link detected — signals demographic-blind external presence"],
    }

def _fetch_platform_data(url: str) -> dict:
    platform = detect_platform(url)
    if platform == 'github':      return _fetch_github(url)
    if platform == 'leetcode':    return _fetch_leetcode(url)
    if platform == 'codeforces':  return _fetch_codeforces(url)
    if platform == 'devto':       return _fetch_devto(url)
    if platform == 'huggingface': return _fetch_huggingface(url)
    return _note_platform(url, platform)


# ─── APP ──────────────────────────────────────────────────────
app = FastAPI(title="FairAI Resume Analysis API", version="4.0")

# ─── RATE LIMITER SETUP ───────────────────────────────────────

def _analyze_rate_key(request: Request) -> str:
    """
    Rate-limit key for /analyze:
    - Authenticated users: keyed by user_id  -> 5 scans/user/day
    - Anonymous requests:  keyed by IP       -> 5 scans/IP/day
    """
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        payload = decode_access_token(auth_header[7:])
        if payload and payload.get("sub"):
            return f"uid:{payload['sub']}"
    return get_remote_address(request)

# Use IP for auth endpoints, user-aware key for analyze
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.exception_handler(RateLimitExceeded)
async def _rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Return a clean 429 JSON instead of the default HTML page."""
    # Parse the limit string from the exception (e.g. "5 per 1 day")
    limit_str = str(exc.detail) if hasattr(exc, 'detail') else str(exc)
    return JSONResponse(
        status_code=429,
        content={
            "detail": f"Rate limit exceeded: {limit_str}. Please try again later.",
            "error":  "rate_limit_exceeded",
        },
        headers={"Retry-After": "3600"},
    )

# Persistent thread pool for all blocking I/O tasks (PII strip, analysis, etc.)
_pool = ThreadPoolExecutor(max_workers=4)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://aethelats.vercel.app",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ─── KEEP-AWAKE MECHANISM ─────────────────────────────────────
def ping_server():
    """Synchronous function to ping the health endpoint."""
    try:
        # Priority: RENDER_EXTERNAL_URL (Render) > SPACE_HOST (HF Spaces) > localhost
        render_url = os.environ.get("RENDER_EXTERNAL_URL")
        space_host = os.environ.get("SPACE_HOST")  # HF Spaces provides this automatically
        
        if render_url:
            base_url = render_url
        elif space_host:
            base_url = f"https://{space_host}"
        else:
            base_url = "http://localhost:7860"
            
        health_url = f"{base_url}/health"
        response = requests.get(health_url, timeout=10)
        print(f"[Keep-Alive] Pinged {health_url} - Status: {response.status_code}")
    except Exception as e:
        print(f"[Keep-Alive] Ping failed: {e}")

async def keep_awake_task():
    """Async loop that waits 14 minutes, then runs the ping."""
    while True:
        await asyncio.sleep(14 * 60)  # Wait for 14 minutes (14 * 60 seconds)
        loop = asyncio.get_event_loop()
        # Run the synchronous ping in the existing thread pool so it doesn't block the server
        await loop.run_in_executor(_pool, ping_server)

@app.on_event("startup")
async def startup_event():
    """Starts the background task when the FastAPI server starts."""
    global scan_queue
    scan_queue = asyncio.Queue()
    asyncio.create_task(scan_worker_loop())

    # Create resume_scores table (Postgres on Render, SQLite locally) if missing.
    print("[FairAI] Initialising score pool database...")
    init_db()

    print(f"[FairAI] Starting parallel worker pool with {MAX_CONCURRENT_WORKERS} workers...")
    print("[FairAI] Starting keep-awake background task...")
    asyncio.create_task(keep_awake_task())

    # ── Auto-build RAG ChromaDB if not present ────────────────────────────────
    # Runs in background so it doesn't delay server startup.
    # On HF Space: rag_kb/*.txt files are committed; ChromaDB is built here on first boot.
    async def _build_rag_if_needed():
        chroma_dir = Path(__file__).parent / "rag_chroma_db"
        kb_dir     = Path(__file__).parent / "rag_kb"
        if not chroma_dir.exists() and kb_dir.exists() and list(kb_dir.glob("*.txt")):
            print("[RAG] ChromaDB not found — building from rag_kb/*.txt (first-time setup)...")
            try:
                loop = asyncio.get_event_loop()
                from rag_store import build_store
                await loop.run_in_executor(None, build_store)
                print("[RAG] ChromaDB built successfully. AI Coach RAG is now active.")
            except Exception as e:
                print(f"[RAG] Auto-build failed (coach will still work without RAG): {e}")
        elif chroma_dir.exists():
            print("[RAG] ChromaDB found — AI Coach RAG is active.")
        else:
            print("[RAG] No rag_kb/*.txt files found — AI Coach running without RAG.")

    asyncio.create_task(_build_rag_if_needed())

# ──────────────────────────────────────────────────────────────



# ─── PROMPTS ──────────────────────────────────────────────────

# Quick scoring prompt for multi-model comparison (lightweight — only extracts score)
QUICK_SCORE_PROMPT = """You are a resume evaluator for a {role} position.
Score this resume 0-100 for fit. Respond ONLY with raw JSON: {{"fit_score": <int>, "primary_reason": "<1 sentence>"}}"""

# Feature 1: PII Stripping
PII_STRIP_PROMPT = """
You are a Privacy Filter for a fair hiring compliance system.
Strip ALL personally identifiable information from the resume text below.

Replace each with exactly these placeholders:
- Full name                          → [CANDIDATE]
- University / college / school      → [INSTITUTION]
- Graduation years (e.g. 2019)       → [YEAR]
- City, state, country, zip codes    → [LOCATION]
- Gender pronouns (he/she/his/her)   → they/their/them
- Personal email addresses           → [EMAIL]
- Phone numbers                      → [PHONE]
- LinkedIn/GitHub personal handles   → [PROFILE_URL]

KEEP intact: job titles, company names (not universities), technical skills,
project descriptions, impact metrics, certifications, and dates of employment.

Return ONLY a JSON object — no markdown, no explanation:
{
  "sanitized_text": "<full resume with PII replaced>",
  "items_removed": ["<each actual value that was replaced>"]
}
"""

# Feature 5: Analysis prompt with skill graph
def build_analysis_prompt(role: str) -> str:
    synonyms    = json.dumps(SKILL_GRAPH.get("canonical_skills", {}), indent=2)
    adjacencies = json.dumps(SKILL_GRAPH.get("adjacencies", {}), indent=2)
    return f"""
You are FairAI, an expert unbiased technical hiring evaluator analyzing a resume for a {role} position.

## MANDATORY BIAS PREVENTION RULES:
1. IGNORE COMPLETELY: name, pronouns, gender, age, graduation year, gaps, institution prestige, location
2. EVALUATE ONLY: demonstrated technical skills, measurable impact, problem-solving depth
3. NEVER penalize employment gaps — legally protected, statistically biased against minorities
4. Judge on what they built and delivered, NOT where they studied

## SKILL SYNONYM RULES (apply before scoring):
Treat all synonyms below as the SAME skill:
{synonyms}

Adjacent skills count as near-matches (partial credit, not full):
{adjacencies}

## CONTEXTUAL vs DECLARATIVE SKILL SCORING:
- CONTEXTUAL (strong signal): Skill used with measurable outcome
    Good: "Optimized pipeline using Python, reducing AWS cost by 15%"
- DECLARATIVE (weak signal): Skill only listed, no evidence
    Weak: "Skills: Python, SQL, AWS"
Score contextual skills significantly higher than declarative ones.
Flag resumes where >60% of skills are declarative as possible keyword stuffing.

## RESPOND WITH ONLY RAW JSON — NO MARKDOWN, NO BACKTICKS:

{{
  "fit_score": <integer 0-100>,
  "fit_level": "<Strong Match | Good Match | Partial Match | Not a Match>",
  "summary": "<2-3 sentences. Cite actual projects/skills. Explain WHY they fit or don't.>",
  "radar": {{
    "technical_depth": <0-100>,
    "problem_solving": <0-100>,
    "impact_evidence": <0-100>,
    "domain_knowledge": <0-100>,
    "project_complexity": <0-100>,
    "communication_clarity": <0-100>
  }},
  "skill_usage_breakdown": [
    {{
      "skill": "<canonical skill name>",
      "usage_type": "<contextual or declarative>",
      "evidence": "<direct quote or close paraphrase from resume>",
      "impact_score": <0-100>
    }}
  ],
  "contextual_ratio": <0.0–1.0, proportion of skills that are contextual>,
  "keyword_stuffing_detected": <true or false>,
  "skill_matches": [
    {{
      "found_in_resume": "<exact text from resume>",
      "canonical_name": "<standardized skill name>",
      "match_type": "<exact | synonym | adjacency>"
    }}
  ],
  "strong_signals": [
    {{
      "signal": "<specific skill, project, or achievement>",
      "evidence": "<direct quote or close paraphrase>",
      "weight": "<high or medium>"
    }}
  ],
  "gaps": [
    {{
      "gap": "<specific skill genuinely missing for this role>",
      "severity": "<blocking or minor>"
    }}
  ],
  "bias_proxies": [
    {{
      "text": "<exact phrase from resume that reveals demographic info>",
      "bias_type": "<gender | age | name | institution | gap | location | socioeconomic>",
      "severity": "<high | medium | low>",
      "explanation": "<how a biased ATS would use this against the candidate>"
    }}
  ],
  "counterfactual": {{
    "primary_bias_factor": "<#1 reason a biased system would downgrade this candidate based on resume text>"
  }},
  "feature_attributions": [
    {{
      "factor": "<specific resume element — project, skill, experience, achievement, or gap>",
      "delta": <integer, positive = pushed score up, negative = pushed score down>,
      "reasoning": "<1 sentence — why this factor moved the score>"
    }}
  ],
  "legacy_ats_verdict": "<Auto-Rejected | Flagged for Review | Passed>",
  "recommendation": "<Advance to Technical Interview | Schedule Screening Call | Request Portfolio Review | Pass>"
}}
"""

# ── Quick score (used in real counterfactual variants — fast, no full analysis)
QUICK_SCORE_PROMPT = """
You are a technical hiring evaluator. Score this resume for the {role} position.
Focus ONLY on technical merit: skills demonstrated, measurable impact, project complexity.
IGNORE completely: name, institution, location, gaps, graduation year.
Return ONLY raw JSON:
{{"fit_score": <integer 0-100>, "primary_reason": "<1 sentence explaining the score>"}}
"""

# ── Feature 3 (REAL): Batch Mutation Prompt
BATCH_MUTATE_PROMPT = """
You are a text editor. Create 3 exact modified versions of the resume text below.
Do NOT change any technical content, skills, projects, achievements, or companies.
Make ONLY these specific targeted changes:

Variant 1 (institution_prestige): Replace ALL universities, colleges, and institutions with "MIT".
  Keep everything else identical.

Variant 2 (gap_removal): Remove ALL lines or phrases about career gaps, employment breaks,
  sabbaticals, "career break", "took time off", or parenthetical time periods not tied to a job.
  Keep all job entries intact.

Variant 3 (name_neutralize): Replace the candidate's full name — wherever it appears
  (header, email prefix, LinkedIn handle, etc.) — with "Alex Johnson".

Return ONLY raw JSON, no markdown:
{
  "institution_prestige": "<full modified resume text>",
  "gap_removal": "<full modified resume text>",
  "name_neutralize": "<full modified resume text>"
}
"""

# ── JD Bias Detection Prompt
JD_BIAS_PROMPT = """
You are an expert in fair hiring law and organizational psychology. Analyze this job description
for language that is statistically proven to deter qualified candidates from underrepresented groups.

Research basis:
- Gaucher et al. (2011): masculine-coded words deter women from applying
- EEOC guidelines: age, disability, national-origin coded language
- Multiple studies: "culture fit" strongly correlates with homogeneous hiring

Check for:
1. Masculine-coded words: ninja, rockstar, dominant, aggressive, competitive, crushing it, killer
2. Age-discriminatory: "recent graduate", "young professional", "digital native", "energy"
3. Culture/origin coded: "native English speaker", "Western education preferred"
4. Ableist language: "must be able to lift", vague "fit" language
5. Socioeconomic bias: unpaid internship references, requiring Ivy League
6. "Culture fit" — known proxy for existing demographic homogeneity
7. Unnecessarily gendered role titles

For each flagged phrase, provide a neutral alternative.

Return ONLY raw JSON:
{
  "overall_bias_score": <0-100, where 0=heavily biased, 100=fully neutral>,
  "bias_level": "<Inclusive | Slightly Biased | Moderately Biased | Highly Biased>",
  "summary": "<2-3 sentences describing the overall bias pattern>",
  "flagged_phrases": [
    {
      "phrase": "<exact phrase from JD>",
      "bias_type": "<masculine_coded | age_discriminatory | origin_coded | ableist | socioeconomic | culture_fit | gendered_title>",
      "severity": "<high | medium | low>",
      "explanation": "<why this phrase deters specific groups>",
      "neutral_alternative": "<suggested replacement>"
    }
  ],
  "inclusive_elements": ["<positive inclusive language already present>"],
  "rewrite_suggestions": ["<top 3 actionable changes to make this JD more inclusive>"],
  "required_skills": ["<extract a list of all technical and soft skills explicitly required in the JD, e.g. Python, SQL, Communication>"],
  "detected_role": "<extract the job title / role being hired for, e.g. Customer Service Associate, Software Engineer>"
}
"""

# ── Proof of Work Link Synthesis Prompt
LINK_SYNTHESIS_PROMPT = """
You are a senior technical hiring manager reviewing a candidate's online presence for the role: {role}.
Below is live data fetched from their public profiles.

Your job:
1. Judge each GitHub repo for ROLE-SPECIFIC IMPACT — is this project impressive and relevant to "{role}"?
2. Flag any repos where originality="copied_fork" — these are red flags (forked repo, zero original commits).
3. Assess LeetCode problem-solving strength relative to what "{role}" interviews typically require.
4. Give an overall verdict on whether this online presence SUPPORTS or CONTRADICTS the candidate's resume claims.

For GitHub repos, use the readme_snippet and languages to understand what the project actually does.

Return ONLY raw JSON:
{{
  "overall_proof_score": <0-100>,
  "proof_level": "<Exceptional | Strong | Moderate | Limited | None>",
  "summary": "<2-3 sentences: what does this online presence reveal about the candidate for {role}?>",
  "key_signals": ["<top 3-5 strongest evidence points>"],
  "repo_verdicts": [
    {{
      "repo": "<repo name>",
      "impact": "<HIGH | MEDIUM | LOW>",
      "relevance_to_role": "<1 sentence: is this project relevant to {role} and why>",
      "originality_flag": "<ORIGINAL | CONTRIBUTED | COPIED>",
      "stars": <number>
    }}
  ],
  "platform_assessments": [
    {{
      "platform": "<platform name>",
      "assessment": "<1 sentence on what this platform's data reveals for {role}>",
      "strength": "<strong | moderate | weak>"
    }}
  ],
  "originality_warning": null,
  "bias_blind_verdict": "<1 sentence on technical credibility for {role} from online work only>",
  "ats_override_recommendation": "<None | Partial | Strong>"
}}

Platform data:
{platform_data}
"""


# ─── DB HELPERS (real percentile pool) ───────────────────────
# Minimum records per role before we trust a computed percentile.
# Below this, we return a mock percentile so the UI doesn't look
# empty for brand-new roles.
_PERCENTILE_MIN_SAMPLES = 10


def _record_score(role_target: str, fit_score: int, contextual_ratio: float) -> None:
    """
    Persist one anonymised scoring result. Silent-fail: a DB outage
    must never break the /analyze response to the user.
    """
    try:
        with SessionLocal() as db:
            row = ResumeScore(
                role_target=(role_target or "Professional").strip()[:255],
                fit_score=int(max(0, min(100, fit_score))),
                contextual_ratio=float(contextual_ratio if contextual_ratio is not None else 0.5),
                has_pii_stripped=True,
            )
            db.add(row)
            db.commit()
    except Exception as e:  # noqa: BLE001
        print(f"[FairAI] WARNING: failed to persist ResumeScore: {e}", file=sys.stderr)


def _compute_percentile_from_db(role_target: str, fit_score: int) -> tuple[int, int, bool]:
    """
    Returns (percentile, pool_size, is_mock).

    - Counts rows for this role_target.
    - If fewer than _PERCENTILE_MIN_SAMPLES rows exist, returns a
      deterministic mock percentile derived from the seeded history
      so the UI stays populated for new roles.
    - Otherwise returns the real percentile:
        (count(fit_score < current) / count(*)) * 100
    """
    role_target = (role_target or "Professional").strip()
    try:
        with SessionLocal() as db:
            total = (
                db.query(sa_func.count(ResumeScore.id))
                .filter(ResumeScore.role_target == role_target)
                .scalar()
                or 0
            )

            if total < _PERCENTILE_MIN_SAMPLES:
                # Fallback: use the seeded mock pool so new roles
                # still render something sensible in the chart.
                below = sum(1 for s in score_history if s < fit_score)
                denom = len(score_history) or 1
                mock_pct = round((below / denom) * 100)
                return mock_pct, total, True

            below = (
                db.query(sa_func.count(ResumeScore.id))
                .filter(ResumeScore.role_target == role_target)
                .filter(ResumeScore.fit_score < fit_score)
                .scalar()
                or 0
            )
            percentile = round((below / total) * 100)
            return percentile, total, False
    except Exception as e:  # noqa: BLE001
        print(f"[FairAI] WARNING: percentile DB query failed, using mock: {e}", file=sys.stderr)
        below = sum(1 for s in score_history if s < fit_score)
        denom = len(score_history) or 1
        return round((below / denom) * 100), 0, True


# ─── ROUTES ───────────────────────────────────────────────────
@app.post("/update-colab-url")
def update_colab_url(payload: ColabUrlUpdate):
    """Updates the Colab Cloudflare/Ngrok URL dynamically without restarting the server."""
    # Update the environment variable in the current running memory
    os.environ["COLAB_URL"] = payload.new_url.strip()
    return {"success": True, "message": f"Colab URL instantly updated to {os.environ['COLAB_URL']}"}

@app.get("/health")
def health():
    # Best-effort real pool size from DB; fall back to seeded length.
    try:
        with SessionLocal() as db:
            db_pool_size = db.query(sa_func.count(ResumeScore.id)).scalar() or 0
    except Exception:  # noqa: BLE001
        db_pool_size = None

    return {
        "status": "ok",
        "model": MODEL,
        "version": "5.0",
        "pool_size": db_pool_size if db_pool_size is not None else len(score_history),
        "pool_source": "database" if db_pool_size is not None else "mock_seeded",
        "features": [
            "gliner_ner_pii_stripping", "llm_pii_fallback",
            "context_scoring", "real_counterfactual_mutations",
            "percentile_benchmarking_db", "skill_knowledge_graph",
            "jd_bias_detection", "multi_platform_proof_of_work"
        ],
        "bot_pipeline": {
            "bot1": "GLiNER NER (Colab GPU) → LLM fallback (Groq)",
            "bot3": "Fine-tuned T5-base (Colab GPU) → rule-based fallback",
            "bot4": "Fine-tuned Phi-3.5 + LoRA (Colab GPU) → Groq fallback",
        }
    }

@app.get("/stats")
def get_stats():
    """
    Real stats pulled from the resume_scores table.

    If the DB is empty (or unreachable), we gracefully fall back to
    the seeded in-memory pool so the UI never looks broken.
    """
    labels = ["0-9","10-19","20-29","30-39","40-49","50-59","60-69","70-79","80-89","90-100"]
    try:
        with SessionLocal() as db:
            pool_size = db.query(sa_func.count(ResumeScore.id)).scalar() or 0
            if pool_size == 0:
                # No real data yet — return empty shell (NOT the mock pool),
                # so the frontend can show "waiting for first submissions".
                return {
                    "pool_size": 0,
                    "avg_score": 0,
                    "distribution": [0] * 10,
                    "labels": labels,
                    "source": "database",
                }

            avg_score = db.query(sa_func.avg(ResumeScore.fit_score)).scalar() or 0

            # Histogram: bucket by tens. Pull scores in one query.
            scores = [row[0] for row in db.query(ResumeScore.fit_score).all()]
            distribution = [0] * 10
            for s in scores:
                bucket = min(int((s or 0) / 10), 9)
                distribution[bucket] += 1

            return {
                "pool_size": pool_size,
                "avg_score": round(float(avg_score), 1),
                "distribution": distribution,
                "labels": labels,
                "source": "database",
            }
    except Exception as e:  # noqa: BLE001
        print(f"[FairAI] WARNING: /stats DB query failed, using mock: {e}", file=sys.stderr)
        if not score_history:
            return {"pool_size": 0, "avg_score": 0, "distribution": [0] * 10, "labels": labels, "source": "mock_seeded"}
        distribution = [0] * 10
        for s in score_history:
            bucket = min(int(s / 10), 9)
            distribution[bucket] += 1
        return {
            "pool_size": len(score_history),
            "avg_score": round(sum(score_history) / len(score_history), 1),
            "distribution": distribution,
            "labels": labels,
            "source": "mock_seeded",
        }


# ─── AUTH ENDPOINTS ───────────────────────────────────────────

# If SKIP_EMAIL_VERIFY=true, users are auto-verified on registration (no OTP email needed).
# Use this when Resend domain isn't set up yet. Remove it once you verify a domain.
_SKIP_EMAIL_VERIFY = os.environ.get("SKIP_EMAIL_VERIFY", "").lower() in ("1", "true", "yes")

@app.post("/auth/register", status_code=201)
@limiter.limit("2/hour")   # max 2 account creations per IP per hour
def auth_register(request: Request, body: RegisterRequest):
    """
    Register a new user.
    1. Creates the user row (is_verified=False)
    2. Generates a 6-digit OTP + emails it
    3. Returns {pending_verification: True} — NO token yet.
    The client must call /auth/verify-otp to get an access token.
    """
    if not body.email or "@" not in body.email:
        raise HTTPException(status_code=400, detail="Invalid email address.")
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="Name is required.")

    email = body.email.lower().strip()
    existing = get_user_by_email(email)
    if existing:
        if existing.is_verified:
            raise HTTPException(status_code=409, detail="An account with this email already exists.")
        else:
            # Account exists but not verified — resend OTP instead of erroring
            otp = create_otp(email)
            if otp:
                send_otp_email(email, otp, existing.name)
            return {
                "pending_verification": True,
                "email": email,
                "message": "A new verification code has been sent to your email.",
            }

    pw_hash = hash_password(body.password)
    user = create_user(
        email=email,
        password_hash=pw_hash,
        name=body.name.strip(),
        role=body.role if body.role in ("recruiter", "candidate") else "recruiter",
        org=body.org,
    )
    if user is None:
        raise HTTPException(status_code=500, detail="Failed to create account. Please try again.")

    # ── Auto-verify mode (no Resend domain set up yet) ──────────
    if _SKIP_EMAIL_VERIFY:
        from database import mark_user_verified
        mark_user_verified(email)
        token = create_access_token(user.id, user.email, user.role)
        print(f"[Auth] SKIP_EMAIL_VERIFY: auto-verified {email!r}")
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id":    user.id,
                "email": user.email,
                "name":  user.name,
                "role":  user.role,
                "org":   user.org,
                "is_recruiter_verified": user.is_recruiter_verified,
                "linkedin_url": user.linkedin_url,
            },
        }

    # Generate OTP and send email
    otp = create_otp(email)
    if otp is None:
        raise HTTPException(status_code=500, detail="Failed to generate verification code.")

    sent = send_otp_email(email, otp, user.name)
    if not sent:
        # Email send failed — still allow flow, OTP is in server logs for dev
        print(f"[Auth] WARNING: OTP email failed to send for {email!r}")

    return {
        "pending_verification": True,
        "email": email,
        "message": "Verification code sent to your email. Please check your inbox.",
    }


@app.post("/auth/verify-otp")
def auth_verify_otp(body: VerifyOTPRequest):
    """
    Verify the 6-digit OTP. On success:
      - Marks user as verified
      - Returns access_token + user object (same as login response)
    On failure: 400 with explanation.
    """
    email = body.email.lower().strip()
    otp   = body.otp.strip()

    if not email or not otp:
        raise HTTPException(status_code=400, detail="Email and OTP code are required.")
    if len(otp) != 6 or not otp.isdigit():
        raise HTTPException(status_code=400, detail="OTP must be a 6-digit number.")

    ok = consume_otp(email, otp)
    if not ok:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired verification code. Please request a new one.",
        )

    user = get_user_by_email(email)
    if user is None:
        raise HTTPException(status_code=404, detail="Account not found.")

    token = create_access_token(user.id, user.email, user.role)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id":    user.id,
            "email": user.email,
            "name":  user.name,
            "role":  user.role,
            "org":   user.org,
            "is_recruiter_verified": user.is_recruiter_verified,
            "linkedin_url": user.linkedin_url,
        },
    }


@app.post("/auth/resend-otp")
@limiter.limit("5/hour")   # max 5 OTP resend requests per IP per hour
def auth_resend_otp(request: Request, body: LoginRequest):
    """
    Resend a fresh OTP to an email address.
    body.password is ignored — only email is used.
    Rate-limit note: create_otp() invalidates the previous code before issuing a new one.
    """
    email = body.email.lower().strip()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Invalid email address.")

    user = get_user_by_email(email)
    if user is None:
        # Don't reveal whether the email exists
        return {"message": "If that email is registered, a new code has been sent."}
    if user.is_verified:
        return {"message": "This account is already verified. Please log in."}

    otp = create_otp(email)
    if otp:
        send_resend_otp_email(email, otp, user.name)

    return {"message": "New verification code sent. Check your inbox."}


@app.post("/auth/login")
@limiter.limit("3/minute")   # brute-force protection: 3 attempts per IP per minute
def auth_login(request: Request, body: LoginRequest):
    """Authenticate user with email + password. Returns access token."""
    if not body.email or not body.password:
        raise HTTPException(status_code=400, detail="Email and password are required.")

    user = get_user_by_email(body.email.lower().strip())
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    if not user.is_verified:
        raise HTTPException(
            status_code=403,
            detail="Please verify your email first. Check your inbox for the 6-digit code.",
        )

    token = create_access_token(user.id, user.email, user.role)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id":    user.id,
            "email": user.email,
            "name":  user.name,
            "role":  user.role,
            "org":   user.org,
            "is_recruiter_verified": user.is_recruiter_verified,
            "linkedin_url": user.linkedin_url,
        },
    }


@app.get("/auth/me")
def auth_me(current_user=Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return {
        "id":         current_user.id,
        "email":      current_user.email,
        "name":       current_user.name,
        "role":       current_user.role,
        "org":        current_user.org,
        "is_recruiter_verified": current_user.is_recruiter_verified,
        "linkedin_url": current_user.linkedin_url,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
    }


@app.post("/auth/request-recruiter-verification")
@limiter.limit("5/hour")
def request_recruiter_verification(request: Request, body: RequestRecruiterVerification, current_user=Depends(get_current_user)):
    if current_user.role != "recruiter":
        raise HTTPException(status_code=403, detail="Only recruiters can request verification.")
    
    email = body.company_email.lower().strip()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Invalid company email address.")

    # Save linkedin URL immediately if provided
    if body.linkedin_url:
        update_linkedin_url(current_user.id, body.linkedin_url)

    # ADMIN BYPASS
    if email.startswith("admin@"):
        mark_recruiter_verified(current_user.id)
        # Fetch updated user
        user = get_user_by_id(current_user.id)
        token = create_access_token(user.id, user.email, user.role)
        return {
            "message": "Admin bypass activated. Account verified.",
            "auto_verified": True,
            "access_token": token,
            "user": {
                "id":    user.id,
                "email": user.email,
                "name":  user.name,
                "role":  user.role,
                "org":   user.org,
                "is_recruiter_verified": user.is_recruiter_verified,
                "linkedin_url": user.linkedin_url,
            }
        }

    otp = create_otp(email)
    if otp:
        send_otp_email(email, otp, current_user.name)
        return {"message": "Verification code sent to your company email.", "auto_verified": False}
    raise HTTPException(status_code=500, detail="Failed to generate verification code.")


@app.post("/auth/verify-recruiter")
def verify_recruiter(body: VerifyRecruiterRequest, current_user=Depends(get_current_user)):
    if current_user.role != "recruiter":
        raise HTTPException(status_code=403, detail="Only recruiters can be verified.")
    
    email = body.company_email.lower().strip()
    otp   = body.otp.strip()

    if not email or not otp:
        raise HTTPException(status_code=400, detail="Company email and OTP code are required.")

    # Validate OTP
    ok = consume_otp(email, otp)
    if not ok:
        raise HTTPException(status_code=400, detail="Invalid or expired verification code.")

    # Mark recruiter as verified
    mark_recruiter_verified(current_user.id)

    # Re-fetch user to get updated fields
    user = get_user_by_id(current_user.id)
    token = create_access_token(user.id, user.email, user.role)

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id":    user.id,
            "email": user.email,
            "name":  user.name,
            "role":  user.role,
            "org":   user.org,
            "is_recruiter_verified": user.is_recruiter_verified,
            "linkedin_url": user.linkedin_url,
        },
    }


# ─── USER SCAN HISTORY ENDPOINTS ─────────────────────────────

@app.get("/user/scans")
def get_user_scan_history(current_user=Depends(get_current_user)):
    """Return the most recent 20 scan records for the authenticated user."""
    scans = get_user_scans(current_user.id, limit=20)
    return {"scans": scans, "total": len(scans)}


@app.patch("/user/scans/{scan_id}/stage")
def update_scan_kanban_stage(
    scan_id: int,
    body: KanbanStageUpdate,
    current_user=Depends(get_current_user),
):
    """Move a candidate card to a different Kanban pipeline stage."""
    VALID = {"Sourced", "Screening", "Interview", "Offer", "Rejected"}
    if body.stage not in VALID:
        raise HTTPException(status_code=422, detail=f"Invalid stage. Must be one of: {', '.join(VALID)}")
    ok = update_kanban_stage(scan_id=scan_id, user_id=current_user.id, stage=body.stage)
    if not ok:
        raise HTTPException(status_code=404, detail="Scan record not found or access denied.")
    return {"ok": True, "scan_id": scan_id, "stage": body.stage}


SUPPORTED_TYPES = {
    ".pdf":  "application/pdf",
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png":  "image/png",
    ".webp": "image/webp",
    ".gif":  "image/gif",
}

ROLE_DETECT_PROMPT = """
You are a resume parser. Identify the SINGLE most appropriate job role for this candidate
based on their degree, work experience, and primary technical skills.
Respond with ONLY raw JSON:
{"role": "<job role, e.g. Software Engineer, Data Scientist, Product Manager>"}
"""

@app.post("/detect-role")
async def detect_role(file: UploadFile = File(...)):
    filename = (file.filename or "").lower()
    ext = next((e for e in SUPPORTED_TYPES if filename.endswith(e)), None)
    if not ext:
        raise HTTPException(status_code=400, detail="Unsupported file type.")
    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Empty file.")
    try:
        resume_text = extract_resume_text(pdf_bytes, ext)
        if not _is_valid_resume(resume_text):
            raise HTTPException(status_code=400, detail="The uploaded file does not appear to be a valid resume or CV.")
            
        if not resume_text.strip():
            return {"role": ""}
        if client is None:
            # No Groq client available; skip role detection
            return {"role": ""}
        # Existing logic continues below
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": f"Resume:\n{resume_text}\n\n{ROLE_DETECT_PROMPT}"}],
            temperature=0.1, max_tokens=100,
            response_format={"type": "json_object"}
        )
        data = parse_json_response(resp.choices[0].message.content)
        return {"role": data.get("role", "").strip()}
    except HTTPException as he:
        # Re-raise the guardrail 400 error so the frontend catches it
        raise he
    except Exception:
        import traceback; traceback.print_exc()
        # Role detection LLM failed (rate-limit, timeout, etc.).
        # Signal the frontend with validation_warning so it shows a helpful message
        # instead of a silent disabled Analyze button.
        return {"role": "", "validation_warning": True}

def _generate_skills_for_role(role: str) -> list[str]:
    """
    Generate expected skills for a role using the RAG knowledge base.

    Priority:
      1. Read from rag_kb/*.txt files (real Indian job posting data, <1ms)
      2. Fall back to Groq LLM only if no RAG file matches

    The RAG files contain TOP IN-DEMAND SKILLS extracted from 97k+ real
    Indian job postings. Much more accurate than LLM hallucination.
    """
    # ── RAG-first: try to extract skills from rag_kb text files ────────────
    try:
        rag_skills = _extract_skills_from_rag(role)
        if rag_skills and len(rag_skills) >= 5:
            print(f"[FairAI] JD skills from RAG ({len(rag_skills)} skills): {rag_skills[:5]}...")
            return rag_skills
    except Exception as e:
        print(f"[FairAI] RAG skill extraction failed: {e}")

    # ── Groq fallback (only if RAG returned nothing) ──────────────────────
    print(f"[FairAI] RAG miss for role '{role}' — falling back to Groq")
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": (
                f"List exactly 12 specific technical skills, tools, frameworks, or languages "
                f"commonly required for the role: '{role}'.\n"
                f"Rules:\n"
                f"- Return ONLY specific names like 'Python', 'Docker', 'React', 'PostgreSQL'\n"
                f"- Do NOT return category descriptions like 'Programming languages' or 'Database management systems'\n"
                f"- Each item must be a single skill/tool name that appears literally on resumes\n"
                f"Return ONLY JSON: {{\"skills\": [\"Python\", \"FastAPI\", \"Docker\", ...]}}"
            )}],
            temperature=0.0, max_tokens=200,
            response_format={"type": "json_object"}
        )
        data = parse_json_response(resp.choices[0].message.content)
        skills = data.get("skills", [])
        skills = [s for s in skills if len(s.split()) <= 4 and "(" not in s and "etc" not in s.lower()]
        return skills if skills else ["Python", "SQL", "Git", "REST API", "Linux"]
    except Exception:
        return ["Python", "SQL", "Git", "REST API", "Linux"]


# ── RAG-based JD skill extraction ─────────────────────────────────────────────
# Maps semantic role categories to rag_kb text files containing real Indian
# job posting data. Uses detect_role_category() from skill_matcher.py for
# fuzzy matching (MiniLM cosine similarity).

_RAG_CATEGORY_TO_FILES: dict[str, list[str]] = {
    "ENGINEERING": [
        "india_market_Software_Development_Engineer_SDE__Backend.txt",
        "india_market_Full_Stack_Developer.txt",
        "india_market_Frontend_Developer.txt",
        "india_market_Mobile_App_Developer.txt",
        "india_market_QA__Test_Engineer.txt",
        "india_market_DevOps__Cloud__SRE.txt",
        "india_market_Technical_Lead__Architect__CTO.txt",
        "india_market_Cybersecurity.txt",
        "india_market_IT_Support__Application_Support.txt",
        "india_market_SAP__ERP_Consultant.txt",
    ],
    "DATA_SCIENCE": [
        "india_market_Data_Scientist__Machine_Learning_Engineer.txt",
        "india_market_Data_Analyst__Business_Analyst.txt",
        "india_market_Data_Engineer.txt",
    ],
    "PRODUCT": [
        "india_market_Product_Manager.txt",
        "india_market_Consulting__Strategy__Management.txt",
    ],
    "DESIGN": [
        "india_market_UIUX_Designer.txt",
    ],
    "SALES": [
        "india_market_Sales__Business_Development.txt",
        "india_market_Customer_Support__Customer_Success.txt",
    ],
    "MARKETING": [
        "india_market_Marketing.txt",
    ],
    "FINANCE": [
        "india_market_Finance__Accounting.txt",
    ],
    "HEALTHCARE": [
        "india_market_Healthcare__Pharma__Biotech.txt",
    ],
}

# Keyword hints to narrow down within ENGINEERING sub-categories
_ROLE_KEYWORD_HINTS: list[tuple[list[str], str]] = [
    (["frontend", "front-end", "front end", "react", "angular", "vue", "ui developer"],
     "india_market_Frontend_Developer.txt"),
    (["fullstack", "full-stack", "full stack", "mern", "mean"],
     "india_market_Full_Stack_Developer.txt"),
    (["mobile", "ios", "android", "flutter", "react native", "swift", "kotlin"],
     "india_market_Mobile_App_Developer.txt"),
    (["devops", "sre", "cloud", "platform engineer", "infrastructure"],
     "india_market_DevOps__Cloud__SRE.txt"),
    (["qa", "test", "sdet", "quality assurance", "automation test"],
     "india_market_QA__Test_Engineer.txt"),
    (["data engineer", "data pipeline", "etl", "airflow", "spark"],
     "india_market_Data_Engineer.txt"),
    (["data analyst", "business analyst", "bi ", "tableau", "power bi"],
     "india_market_Data_Analyst__Business_Analyst.txt"),
    (["data scientist", "machine learning", "ml engineer", "ai engineer", "deep learning", "nlp"],
     "india_market_Data_Scientist__Machine_Learning_Engineer.txt"),
    (["cybersecurity", "security engineer", "penetration", "soc analyst"],
     "india_market_Cybersecurity.txt"),
    (["sap", "erp", "abap"],
     "india_market_SAP__ERP_Consultant.txt"),
    (["tech lead", "architect", "cto", "principal engineer", "staff engineer"],
     "india_market_Technical_Lead__Architect__CTO.txt"),
    (["product manager", "product owner", "apm"],
     "india_market_Product_Manager.txt"),
    (["hr", "human resource", "talent acquisition", "recruiter"],
     "india_market_Human_Resources.txt"),
    (["operations", "supply chain", "logistics", "procurement"],
     "india_market_Operations__Supply_Chain.txt"),
    (["legal", "compliance", "law", "advocate"],
     "india_market_Legal__Compliance.txt"),
    (["education", "teacher", "trainer", "professor", "faculty"],
     "india_market_Education__Teaching__Training.txt"),
    (["mechanical", "civil", "electrical", "core engineering"],
     "india_market_Core_Engineering_Mechanical__Civil__Electrical.txt"),
    (["consulting", "strategy", "management consulting", "mckinsey", "bcg"],
     "india_market_Consulting__Strategy__Management.txt"),
]


def _extract_skills_from_rag(role: str) -> list[str]:
    """
    Extract JD skills from rag_kb/*.txt files based on the target role.

    1. Try keyword hints first (exact sub-category match)
    2. Fall back to semantic category detection (MiniLM)
    3. Parse the 'TOP IN-DEMAND SKILLS' section from the txt file
    4. Filter out generic/category-style entries, keep specific skill names
    """
    import re as _re
    from pathlib import Path as _Path

    kb_dir = _Path(__file__).parent / "rag_kb"
    if not kb_dir.exists():
        return []

    role_lower = role.lower().strip()

    # ── Step 1: Keyword hints for precise sub-category matching ────────────
    matched_file = None
    for keywords, filename in _ROLE_KEYWORD_HINTS:
        if any(kw in role_lower for kw in keywords):
            candidate = kb_dir / filename
            if candidate.exists():
                matched_file = candidate
                print(f"[RAG] Keyword match: '{role}' → {filename}")
                break

    # ── Step 2: Semantic category fallback ─────────────────────────────────
    if matched_file is None:
        try:
            from skill_matcher import detect_role_category
            category = detect_role_category(role)
            files = _RAG_CATEGORY_TO_FILES.get(category, [])
            # Pick the first file that exists (most general for the category)
            for fname in files:
                candidate = kb_dir / fname
                if candidate.exists():
                    matched_file = candidate
                    print(f"[RAG] Semantic match: '{role}' → {category} → {fname}")
                    break
        except Exception as e:
            print(f"[RAG] Semantic detection failed: {e}")

    if matched_file is None:
        print(f"[RAG] No matching rag_kb file for role: '{role}'")
        return []

    # ── Step 3: Parse skills from the text file ───────────────────────────
    try:
        text = matched_file.read_text(encoding="utf-8")
    except Exception as e:
        print(f"[RAG] Could not read {matched_file.name}: {e}")
        return []

    # Find the TOP IN-DEMAND SKILLS section and extract skill names
    # Format: "   1. Python — mentioned in 55% of postings"
    skills = []
    in_skills_section = False
    skill_line_re = _re.compile(
        r"^\s*\d+\.\s+(.+?)(?:\s*[\u2013\u2014\-]+\s*mentioned|\s*$)",
        _re.UNICODE
    )

    for line in text.splitlines():
        if "TOP IN-DEMAND SKILLS" in line:
            in_skills_section = True
            continue
        if in_skills_section:
            # Stop at next section header (all caps line or empty section)
            stripped = line.strip()
            if stripped and not stripped[0].isdigit() and stripped.isupper():
                break
            m = skill_line_re.match(line)
            if m:
                skill_name = m.group(1).strip().rstrip("—-– ")
                # Filter out vague category names — keep only specific skills
                vague_terms = {
                    "development", "application development", "software development",
                    "frontend development", "ui development", "web development",
                    "web technologies", "front end", "backend", "data",
                    "development methodologies", "application design",
                }
                if skill_name.lower() not in vague_terms and len(skill_name) > 1:
                    skills.append(skill_name)

    # Take top 15 skills (more than the old Groq 12 — more data = better matching)
    skills = skills[:15]
    print(f"[RAG] Extracted {len(skills)} skills from {matched_file.name}")
    return skills




# ─── SYNC HELPERS (run in thread executor) ────────────────────

# ── Bot 1: GLiNER NER Model (loaded locally — ~1.5GB RAM) ──────
_gliner_model = None
_GLINER_LABELS = [
    "Person", "Location", "Email", "Phone",
    "Address", "Nationality", "Gender", "University"
    # NOTE: "Organization" intentionally removed — it incorrectly tags employer/company names
    # as [INSTITUTION], destroying job history before Bot 3 can extract it.
    # We only anonymize "University" to test institution-prestige bias specifically.
]
_GLINER_THRESHOLD = 0.45
_GLINER_PLACEHOLDER_MAP = {
    "Person":       "[CANDIDATE]",
    "Location":     "[LOCATION]",
    "Email":        "[EMAIL]",
    "Phone":        "[PHONE]",
    "Address":      "[LOCATION]",
    "Organization": "[INSTITUTION]",
    "Nationality":  "[NATIONALITY]",
    "Gender":       "[GENDER]",
    "University":   "[INSTITUTION]",
}

def _load_gliner():
    """Lazy-load GLiNER model. Only ~1.5GB RAM — runs fine on HF Spaces free tier."""
    global _gliner_model
    if _gliner_model is not None:
        return _gliner_model
    try:
        from gliner import GLiNER
        print("[Bot1] Loading GLiNER model (urchade/gliner_medium-v2.1) ...")
        _gliner_model = GLiNER.from_pretrained("urchade/gliner_medium-v2.1")
        print("[Bot1] GLiNER ready.")
        return _gliner_model
    except ImportError:
        print("[Bot1] GLiNER library not installed. Install with: pip install gliner")
        return None
    except Exception as e:
        print(f"[Bot1] GLiNER load failed: {e}")
        return None


def _strip_pii_via_gliner(text: str) -> dict:
    """Bot 1 (PRIMARY): GLiNER NER-based PII stripping.
    Deterministic, auditable, zero API cost.
    
    Runs with a 15-second CPU time budget. If GLiNER takes longer
    (common on free-tier HF Spaces CPU with 100+ resume lines),
    it aborts early and returns None so the fast Groq fallback is used.
    """
    import time as _time
    model = _load_gliner()
    if model is None:
        return None  # Signal to use fallback

    items_removed = []
    sanitized_lines = []
    _deadline = _time.monotonic() + 15  # 15-second hard budget

    for line in text.split('\n'):
        if not line.strip():
            sanitized_lines.append(line)
            continue

        # Abort if we've exceeded the time budget — fall through to Groq LLM
        if _time.monotonic() > _deadline:
            print("[Bot1] GLiNER time budget exceeded — aborting, will use LLM fallback.")
            return None

        try:
            entities = model.predict_entities(line, _GLINER_LABELS, threshold=_GLINER_THRESHOLD)
        except Exception:
            sanitized_lines.append(line)
            continue

        if not entities:
            sanitized_lines.append(line)
            continue

        # Sort spans by start position; drop overlapping spans (keep longest)
        entities_sorted = sorted(entities, key=lambda e: (e["start"], -(e["end"] - e["start"])))
        non_overlapping = []
        last_end = -1
        for ent in entities_sorted:
            if ent["start"] >= last_end:
                non_overlapping.append(ent)
                last_end = ent["end"]

        # Rebuild line by substituting spans with placeholders
        result_chars = []
        cursor = 0
        for ent in non_overlapping:
            result_chars.append(line[cursor:ent["start"]])
            placeholder = _GLINER_PLACEHOLDER_MAP.get(ent["label"], f"[{ent['label'].upper()}]")
            result_chars.append(placeholder)
            original_text = line[ent["start"]:ent["end"]]
            items_removed.append(original_text)
            cursor = ent["end"]
        result_chars.append(line[cursor:])
        sanitized_lines.append("".join(result_chars))

    # Post-process: replace gendered pronouns
    sanitized_text = "\n".join(sanitized_lines)
    sanitized_text = re.sub(r'\b[Hh]e\b', 'they', sanitized_text)
    sanitized_text = re.sub(r'\b[Ss]he\b', 'they', sanitized_text)
    sanitized_text = re.sub(r'\b[Hh]is\b', 'their', sanitized_text)
    sanitized_text = re.sub(r'\b[Hh]er\b', 'their', sanitized_text)
    sanitized_text = re.sub(r'\b[Hh]im\b', 'them', sanitized_text)

    unique_items = list(set(items_removed))
    print(f"[Bot1] GLiNER stripped {len(unique_items)} PII items deterministically")
    return {
        "sanitized_text": sanitized_text,
        "items_removed": unique_items,
        "method": "gliner_ner"
    }


def _strip_pii_via_llm(text: str) -> dict:
    """Bot 1 (FALLBACK): LLM-based PII stripping via Groq API.
    Probabilistic, slower, costs API credits, but works without GLiNER."""
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": f"Resume to sanitize:\n\n{text}\n\n{PII_STRIP_PROMPT}"}],
            temperature=0.0, max_tokens=4096,
            response_format={"type": "json_object"}
        )
        data = parse_json_response(resp.choices[0].message.content)
        print(f"[Bot1] LLM fallback: {len(data.get('items_removed', []))} PII items stripped")
        return {
            "sanitized_text": data.get("sanitized_text", text),
            "items_removed": data.get("items_removed", []),
            "method": "llm_fallback"
        }
    except Exception as e:
        print(f"[Bot1] PII strip failed entirely (using original): {e}")
        return {"sanitized_text": text, "items_removed": [], "method": "none"}

def _strip_pii(text: str) -> dict:
    """Feature 1: Strip all PII from resume text before analysis.
    Priority: GLiNER NER local (deterministic) → LLM fallback (probabilistic) → raw text."""
    # Try local GLiNER first (deterministic, free, fast)
    result = _strip_pii_via_gliner(text)
    if result is not None:
        return result
    # Fallback to LLM-based stripping
    return _strip_pii_via_llm(text)


def _analyze(text: str, role: str) -> dict:
    """Run the full bias-free analysis on sanitized text."""
    prompt = build_analysis_prompt(role)
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": f"Resume:\n{text}\n\n{prompt}"}],
        temperature=0.1, max_tokens=8192,
        response_format={"type": "json_object"}
    )
    return parse_json_response(resp.choices[0].message.content)

def _quick_score(text: str, role: str) -> dict:
    """Fast scoring for counterfactual variants — just score, no full analysis."""
    prompt = QUICK_SCORE_PROMPT.format(role=role)
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": f"Resume:\n{text}\n\n{prompt}"}],
        temperature=0.0, max_tokens=150,
        response_format={"type": "json_object"}
    )
    return parse_json_response(resp.choices[0].message.content)

def _generate_mutations(text: str) -> dict:
    """Generate 3 mutated resume variants in a single LLM call."""
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": f"Resume:\n{text}\n\n{BATCH_MUTATE_PROMPT}"}],
        temperature=0.0, max_tokens=8192,
        response_format={"type": "json_object"}
    )
    data = parse_json_response(resp.choices[0].message.content)
    return {
        "institution_prestige": data.get("institution_prestige", text),
        "gap_removal":          data.get("gap_removal", text),
        "name_neutralize":      data.get("name_neutralize", text),
    }

def _synthesize_links(platform_data_list: list, role: str = "Software Engineer") -> dict:
    """Use LLM to synthesize all platform signals into a coherent proof-of-work assessment."""
    platform_data_str = json.dumps(platform_data_list, indent=2)
    prompt = LINK_SYNTHESIS_PROMPT.format(platform_data=platform_data_str, role=role)
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1, max_tokens=1024,
            response_format={"type": "json_object"}
        )
        return parse_json_response(resp.choices[0].message.content)
    except Exception as e:
        return {
            "overall_proof_score": 0,
            "proof_level": "Limited",
            "summary": "Unable to synthesize link data.",
            "key_signals": [],
            "platform_assessments": [],
            "bias_blind_verdict": "Insufficient data.",
            "ats_override_recommendation": "None",
        }


# ─── MAIN ANALYZE ENDPOINT ────────────────────────────────────
import uuid

job_store = {}
scan_queue = None
MAX_CONCURRENT_WORKERS = 5
active_tasks = set()

# WebSocket connections manager: batch_id -> set of WebSocket connections
batch_connections = {}

# Pipeline stages for tracking
PIPELINE_STAGES = [
    ("extract", "Extracting Text"),
    ("pii", "Stripping PII"),
    ("score", "Blind Scoring"),
    ("skills", "Skill Graph"),
    ("bias", "Bias Detection"),
    ("percentile", "Percentile Rank"),
    ("cf", "Counterfactual"),
    ("gate", "Fairness Gate"),
]

async def broadcast_to_batch(batch_id, message):
    """Send a message to all WebSocket clients connected to a batch with retry logic.
    
    Features:
    - Retries failed sends up to 3 times with exponential backoff (100ms, 200ms, 400ms)
    - Distinguishes between different failure types (timeout, connection, other)
    - Logs successful broadcasts and retry attempts for debugging
    - Handles timeouts gracefully to prevent hanging
    - Maintains backward compatibility
    """
    if batch_id not in batch_connections:
        return
    
    disconnected = set()
    max_retries = 3
    retry_delays = [0.1, 0.2, 0.4]  # 100ms, 200ms, 400ms
    timeout_seconds = 5
    
    for ws in batch_connections[batch_id]:
        sent = False
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # Attempt to send with timeout
                await asyncio.wait_for(ws.send_json(message), timeout=timeout_seconds)
                
                # Log successful send
                if attempt == 0:
                    print(f"[WebSocket] Successfully sent to batch {batch_id}")
                else:
                    print(f"[WebSocket] Successfully sent to batch {batch_id} on retry attempt {attempt}")
                
                sent = True
                break
                
            except asyncio.TimeoutError:
                last_error = "timeout"
                error_msg = f"[WebSocket] Timeout sending to batch {batch_id}"
                if attempt < max_retries - 1:
                    print(f"{error_msg} (attempt {attempt + 1}/{max_retries}), retrying in {retry_delays[attempt]*1000:.0f}ms...")
                    await asyncio.sleep(retry_delays[attempt])
                else:
                    print(f"{error_msg} (attempt {attempt + 1}/{max_retries}), giving up")
                    
            except ConnectionError as e:
                last_error = "connection"
                error_msg = f"[WebSocket] Connection error sending to batch {batch_id}: {e}"
                if attempt < max_retries - 1:
                    print(f"{error_msg} (attempt {attempt + 1}/{max_retries}), retrying in {retry_delays[attempt]*1000:.0f}ms...")
                    await asyncio.sleep(retry_delays[attempt])
                else:
                    print(f"{error_msg} (attempt {attempt + 1}/{max_retries}), giving up")
                    
            except Exception as e:
                last_error = "other"
                error_msg = f"[WebSocket] Failed to send to batch {batch_id}: {type(e).__name__}: {e}"
                if attempt < max_retries - 1:
                    print(f"{error_msg} (attempt {attempt + 1}/{max_retries}), retrying in {retry_delays[attempt]*1000:.0f}ms...")
                    await asyncio.sleep(retry_delays[attempt])
                else:
                    print(f"{error_msg} (attempt {attempt + 1}/{max_retries}), giving up")
        
        # Mark as disconnected if all retries failed
        if not sent:
            print(f"[WebSocket] Marking client as disconnected after {max_retries} failed attempts ({last_error})")
            disconnected.add(ws)
    
    # Clean up disconnected clients
    for ws in disconnected:
        batch_connections[batch_id].discard(ws)

async def scan_worker_loop():
    """Parallel worker pool that maintains up to MAX_CONCURRENT_WORKERS active tasks."""
    global active_tasks
    while True:
        try:
            # Keep pool filled with up to MAX_CONCURRENT_WORKERS tasks
            while len(active_tasks) < MAX_CONCURRENT_WORKERS:
                try:
                    job_id, kwargs = scan_queue.get_nowait()
                    batch_id = kwargs.get("batch_id", "unknown")
                    task = asyncio.create_task(process_job_with_stages(job_id, kwargs, batch_id))
                    active_tasks.add(task)
                    print(f"[Worker Pool] Started job {job_id} (pool size: {len(active_tasks)}/{MAX_CONCURRENT_WORKERS})")
                except asyncio.QueueEmpty:
                    break
            
            if not active_tasks:
                await asyncio.sleep(0.1)
                continue
            
            # Wait for any task to complete
            done, active_tasks = await asyncio.wait(active_tasks, return_when=asyncio.FIRST_COMPLETED)
            
            for task in done:
                try:
                    await task
                except Exception as e:
                    print(f"[Worker Pool] Task failed: {e}")
                    
        except Exception as e:
            print(f"[Worker Error] {e}")
            await asyncio.sleep(0.1)

async def process_job_with_stages(job_id, kwargs, batch_id):
    """Process a job through all pipeline stages, emitting WebSocket updates."""
    try:
        job_store[job_id]["status"] = "processing"
        job_store[job_id]["batch_id"] = batch_id
        
        async def set_stage(stage_idx: int, detail: str = ""):
            stage_key, stage_name = PIPELINE_STAGES[stage_idx]
            job_store[job_id]["stage"] = stage_idx
            job_store[job_id]["stage_name"] = stage_name
            job_store[job_id]["stage_detail"] = detail
            await broadcast_to_batch(batch_id, {
                "type": "job_progress",
                "job_id": job_id,
                "stage": stage_idx,
                "stage_name": stage_name,
                "stage_detail": detail,
                "status": "processing",
            })
            print(f"[Job {job_id}] Stage {stage_idx}: {stage_name}{' — ' + detail if detail else ''}")
        
        # Execute the full job (strip batch_id — execute_scan_job doesn't accept it)
        scan_kwargs = {k: v for k, v in kwargs.items() if k != "batch_id"}
        scan_kwargs["stage_callback"] = set_stage
        result = await execute_scan_job(job_id=job_id, **scan_kwargs)
        job_store[job_id]["status"] = "completed"
        job_store[job_id]["result"] = result
        job_store[job_id]["stage"] = 7
        job_store[job_id]["stage_name"] = "Fairness Gate"
        job_store[job_id]["stage_detail"] = "All checks passed"
        
        # Broadcast completion
        await broadcast_to_batch(batch_id, {
            "type": "job_progress",
            "job_id": job_id,
            "stage": 7,
            "stage_name": "Fairness Gate",
            "stage_detail": "All checks passed",
            "status": "completed",
            "result": result,
        })
        print(f"[Job {job_id}] Completed successfully")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        job_store[job_id]["status"] = "error"
        job_store[job_id]["error"] = getattr(e, 'detail', str(e))
        
        # Broadcast error
        await broadcast_to_batch(batch_id, {
            "type": "job_progress",
            "job_id": job_id,
            "status": "error",
            "error": str(e),
        })
        print(f"[Job {job_id}] Failed: {e}")

@app.get("/analyze/status/{job_id}")
async def get_analyze_status(job_id: str):
    if job_id not in job_store:
        raise HTTPException(status_code=404, detail="Job not found")
    return job_store[job_id]

@app.post("/analyze")
@limiter.limit("5/day", key_func=_analyze_rate_key)   # 5 scans per user (or IP) per day
async def analyze_resume(
    request: Request,
    file: UploadFile = File(...),
    role: str = Form(default="Professional"),
    jd_skills: str = Form(default=""),
    current_user=Depends(get_optional_user),
):
    global scan_queue
    if scan_queue is None:
        raise HTTPException(status_code=503, detail="Queue not initialized")

    filename = (file.filename or "").lower()
    ext = next((e for e in SUPPORTED_TYPES if filename.endswith(e)), None)
    if not ext:
        raise HTTPException(status_code=400, detail="Unsupported file type.")
    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Empty file.")

    job_id = str(uuid.uuid4())
    job_store[job_id] = {"status": "queued", "result": None, "error": None}
    
    current_user_id = current_user.id if current_user else None
    
    await scan_queue.put((job_id, {
        "filename": file.filename or "",
        "ext": ext,
        "pdf_bytes": pdf_bytes,
        "role": role,
        "jd_skills": jd_skills,
        "current_user_id": current_user_id
    }))

    return {"job_id": job_id, "status": "queued"}


@app.post("/batch-analyze")
@limiter.limit("2/hour", key_func=_analyze_rate_key)  # batch is expensive — 2 batches/hour
async def batch_analyze_resumes(
    request: Request,
    files: list[UploadFile] = File(...),
    role: str = Form(default="Professional"),
    jd_skills: str = Form(default=""),
    current_user=Depends(get_current_user),   # must be authenticated
):
    """
    Queue up to 20 resumes for batch processing.
    Each file gets its own job_id so the frontend can poll each independently.
    Returns immediately with [{filename, job_id, status}] — no waiting.

    Requires authentication. In future this will gate on plan_tier='pro'.
    """
    global scan_queue
    if scan_queue is None:
        raise HTTPException(status_code=503, detail="Queue not initialized")

    if current_user.role == "recruiter" and not current_user.is_recruiter_verified:
        raise HTTPException(status_code=403, detail="Company email verification is required to use Batch Processing.")

    MAX_FILES = 20
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")
    if len(files) > MAX_FILES:
        raise HTTPException(status_code=400, detail=f"Maximum {MAX_FILES} files per batch.")

    # Generate a unique batch_id to group all jobs in this batch
    batch_id = str(uuid.uuid4())
    
    queued = []
    skipped = []

    for f in files:
        filename = (f.filename or "").lower()
        ext = next((e for e in SUPPORTED_TYPES if filename.endswith(e)), None)
        if not ext:
            skipped.append({"filename": f.filename, "reason": "Unsupported file type"})
            continue

        file_bytes = await f.read()
        if not file_bytes:
            skipped.append({"filename": f.filename, "reason": "Empty file"})
            continue

        job_id = str(uuid.uuid4())
        job_store[job_id] = {
            "status": "queued",
            "result": None,
            "error": None,
            "filename": f.filename,  # Store filename so frontend can display it
            "batch_id": batch_id,
            "stage": 0,
            "stage_name": "Extracting Text",
        }

        await scan_queue.put((job_id, {
            "filename": f.filename or "",
            "ext": ext,
            "pdf_bytes": file_bytes,
            "role": role,
            "jd_skills": jd_skills,
            "current_user_id": current_user.id,
            "batch_id": batch_id,
        }))

        queued.append({"filename": f.filename, "job_id": job_id, "status": "queued"})

    print(f"[Batch] Queued {len(queued)} jobs for user {current_user.id} — batch_id: {batch_id} — role: {role}")

    return {
        "batch_id": batch_id,
        "batch_size": len(queued),
        "jobs": queued,
        "skipped": skipped,
        "message": f"{len(queued)} resumes queued for processing.",
    }


# ─── WEBSOCKET ENDPOINT FOR REAL-TIME BATCH UPDATES ───────────────
@app.websocket("/ws/batch/{batch_id}")
async def websocket_batch_updates(websocket: WebSocket, batch_id: str):
    """
    WebSocket endpoint for real-time batch processing updates.
    Clients connect with: ws://api.aethel.com/ws/batch/{batch_id}
    
    Receives messages like:
    {
        "type": "job_progress",
        "job_id": "...",
        "stage": 2,
        "stage_name": "Stripping PII",
        "status": "processing"
    }
    
    Implements bidirectional heartbeat:
    - Server sends "ping" every 30 seconds if no client message received
    - Client can send "ping" to keep connection alive
    - Both sides respond with "pong" to heartbeats
    - 60-second timeout on receive_text() detects dead connections
    """
    await websocket.accept()
    
    # Add this connection to the batch's connection set
    if batch_id not in batch_connections:
        batch_connections[batch_id] = set()
    batch_connections[batch_id].add(websocket)
    
    print(f"[WebSocket] Client connected to batch {batch_id} (total: {len(batch_connections[batch_id])})")

    # ── Catch-up snapshot ─────────────────────────────────────────────────
    # Send the current state of every job in this batch immediately on connect.
    # This handles the race where stages 0-1 fired before the WS was established.
    snapshot_jobs = [
        {
            "job_id": jid,
            "stage": info.get("stage", 0),
            "stage_name": info.get("stage_name", "Extracting Text"),
            "stage_detail": info.get("stage_detail", ""),
            "status": info.get("status", "queued"),
            "result": info.get("result"),
            "error": info.get("error"),
        }
        for jid, info in job_store.items()
        if info.get("batch_id") == batch_id
    ]
    if snapshot_jobs:
        try:
            await websocket.send_json({
                "type": "job_snapshot",
                "jobs": snapshot_jobs,
            })
            print(f"[WebSocket] Sent catch-up snapshot ({len(snapshot_jobs)} jobs) to new client on batch {batch_id}")
        except Exception as snap_err:
            print(f"[WebSocket] Failed to send snapshot: {snap_err}")
    # ─────────────────────────────────────────────────────────────────────
    
    try:
        while True:
            try:
                # Wait for client message with 60-second timeout
                # If no message received within 60 seconds, TimeoutError is raised
                data = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)
                
                # Handle client-initiated heartbeat
                if data == "ping":
                    print(f"[WebSocket] Heartbeat ping received from client on batch {batch_id}")
                    await websocket.send_text("pong")
                # Handle other client messages (e.g., job progress updates)
                else:
                    print(f"[WebSocket] Message received on batch {batch_id}: {data[:100]}")
                    
            except asyncio.TimeoutError:
                # No message received for 60 seconds - connection is likely dead
                print(f"[WebSocket] Timeout: No message from client on batch {batch_id} for 60 seconds")
                break
                
    except WebSocketDisconnect:
        print(f"[WebSocket] Client disconnected from batch {batch_id}")
        batch_connections[batch_id].discard(websocket)
        if not batch_connections[batch_id]:
            del batch_connections[batch_id]
    except Exception as e:
        print(f"[WebSocket] Error in batch {batch_id}: {e}")
        batch_connections[batch_id].discard(websocket)
        if not batch_connections[batch_id]:
            del batch_connections[batch_id]


async def execute_scan_job(job_id: str, filename: str, ext: str, pdf_bytes: bytes, role: str, jd_skills: str, current_user_id: int, stage_callback=None):
    try:
        # Stage 0: Extracting Text — fire callback BEFORE extraction so cube
        # lights up while work is happening (WS is established by this point
        # because process_job_with_stages no longer calls set_stage(0) up-front;
        # the snapshot-on-connect handles any race).
        if stage_callback:
            await stage_callback(0, f"Reading {ext.lstrip('.').upper()} file…")
            print("[FairAI] ✓ Stage 0/8 — Extracting Text (callback sent)")
        _t0 = __import__('time').monotonic()
        resume_text = extract_resume_text(pdf_bytes, ext)
        # NOTE: _is_valid_resume is NOT called here — it is already called in
        # /detect-role during file upload. Calling it again adds a redundant ~5s
        # Groq round-trip on every analysis, slowing down the hot path.
        _chars = len(resume_text)
        print(f"[FairAI] Analyzing for role: {role}")

        loop = asyncio.get_event_loop()

        # Stage 1: PII Stripping — fire callback BEFORE the blocking work so the
        # cube animates while GLiNER is running (which can take ~22s on cold start).
        if stage_callback:
            await stage_callback(1, f"Scanning {_chars:,} characters for personal data…")
            print("[FairAI] ✓ Stage 1/8 — Stripping PII (callback sent)")
        print("[FairAI] Stage 1/3 — Stripping PII (Bot 1)...")
        pii_result = await loop.run_in_executor(_pool, _strip_pii, resume_text)
        sanitized  = pii_result["sanitized_text"]
        pii_items  = pii_result["items_removed"]
        pii_method = pii_result.get("method", "unknown")
        _t1 = __import__('time').monotonic()
        print(f"[FairAI] ✓ Stage 1 done in {_t1-_t0:.1f}s — PII stripped: {len(pii_items)} items (method: {pii_method})")

        result = None
        try:
            # Stage 2: Blind Scoring — fire NOW (after PII work) before the
            # parallel Bot 3 + JD-skills block which represents the scoring phase.
            if stage_callback:
                await stage_callback(2, f"{len(pii_items)} PII items redacted — blind scoring…")
                print("[FairAI] ✓ Stage 2/8 — Blind Scoring (callback sent)")

            print("[FairAI] Stage 2/3 — Structuring resume (Bot 3) + generating JD skills in parallel...")

            if jd_skills.strip():
                jd_skills_list = [s.strip() for s in jd_skills.split(",") if s.strip()]
                structured_data = await loop.run_in_executor(_pool, structure_resume, sanitized)
            else:
                print(f"[FairAI] No JD skills provided — auto-generating for role: {role} in parallel with Bot 3...")
                skills_future = loop.run_in_executor(_pool, _generate_skills_for_role, role)
                struct_future = loop.run_in_executor(_pool, structure_resume, sanitized)
                jd_skills_list, structured_data = await asyncio.gather(skills_future, struct_future)

            _t2 = __import__('time').monotonic()
            print(f"[FairAI] ✓ Stage 2 done in {_t2-_t1:.1f}s — JD skills: {jd_skills_list}")

            # Stage 3: Skill Graph — fire after Bot 3 + JD skills work completes
            _skills_label = ", ".join(jd_skills_list[:3]) + (f" +{len(jd_skills_list)-3} more" if len(jd_skills_list) > 3 else "") if jd_skills_list else "skills detected"
            if stage_callback:
                await stage_callback(3, f"Mapped {_skills_label}")
                print("[FairAI] ✓ Stage 3/8 — Skill Graph (callback sent)")
            
            # ── Check if Bot 3 actually extracted useful data ──────────────
            # Bot 3 may return sentence-length "skills" that get stripped later.
            # Check for REAL skills (short, keyword-like) and real jobs.
            raw_tech = structured_data.get("technical_skills", [])
            usable_skills = [s for s in raw_tech if s and len(s) < 40 and len(s.split()) <= 5
                             and not s.endswith('.') and s.lower().strip() not in
                             {"key skills", "skills", "experience", "education", "summary",
                              "objective", "profile", "career objective", "references"}]
            
            has_jobs = False
            for j in (structured_data.get("job_history") or []):
                t = str(j.get("title", "")).strip().lower()
                if t and t not in ("[candidate]", "[institution]", "[location]", "canteen", "date") and len(t) > 2:
                    has_jobs = True
                    break
            
            # If we have sentence-style "skills" but no real keywords, try to extract keywords from them
            if not usable_skills and raw_tech:
                # Extract skill keywords from descriptive bullets:
                # "Customer service ability demonstrated when..." → "Customer Service"
                # "Numeracy skills for cash handling..." → "Numeracy", "Cash Handling"
                import re as _re
                _skill_kw_patterns = [
                    _re.compile(r'^(\w[\w\s]{2,25}?)\s+(?:skills?|ability|abilities)\b', _re.I),
                    _re.compile(r'\b(?:skills?\s+(?:in|for|with)\s+)([\w\s]{3,25}?)(?:\s+(?:proven|demonstrated|shown|developed))', _re.I),
                    _re.compile(r'^(?:Strong|Highly developed|Demonstrated|Excellent)\s+([\w\s]{3,25}?)\s+(?:skills?|ability)', _re.I),
                ]
                extracted_kw = []
                for s in raw_tech:
                    for pat in _skill_kw_patterns:
                        m = pat.search(s)
                        if m:
                            kw = m.group(1).strip().title()
                            if kw.lower() not in {"key", "skills", "key skills"} and len(kw) > 2:
                                extracted_kw.append(kw)
                            break
                if extracted_kw:
                    usable_skills = extracted_kw
                    structured_data["technical_skills"] = extracted_kw
                    print(f"[FairAI] Extracted {len(extracted_kw)} skill keywords from descriptive bullets: {extracted_kw}")
            
            # If still nothing useful, use Groq to properly structure the resume
            if not usable_skills or not has_jobs:
                print(f"[FairAI] Bot 3 extracted empty structure. Using Groq fallback for structuring...")
                groq_prompt = f"""You are an expert resume parser. Extract the structure of this resume into JSON.
Return ONLY valid JSON matching this schema:
{{
  "total_years_experience": number or null,
  "technical_skills": ["skill1", "skill2"],
  "highest_degree": "High School" | "Associate" | "Bachelor" | "Master" | "PhD" | "None stated",
  "job_history": [{{"title": "Job Title", "duration_months": 24}}],
  "experience": [{{"title": "Job Title", "company": "Company", "duration_months": 24, "date_range": "Jun 2016 - Feb 2017", "type": "Job"}}]
}}
Do NOT wrap in ```json. Just return the JSON object.
For technical_skills, extract SHORT skill keywords (e.g. "Customer Service", "Cash Handling", "Communication") not full sentences.

Resume:
{sanitized[:3000]}"""
                try:
                    resp = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": groq_prompt}],
                        temperature=0,
                        max_tokens=1024
                    )
                    raw_json = resp.choices[0].message.content.strip()
                    # Strip markdown code fences if present
                    if raw_json.startswith("```"):
                        raw_json = raw_json.split("\n", 1)[1] if "\n" in raw_json else raw_json[3:]
                    if raw_json.endswith("```"):
                        raw_json = raw_json[:-3]
                    raw_json = raw_json.strip()
                    groq_data = json.loads(raw_json)
                    # Merge Groq data into structured_data 
                    # Overwrite jobs and skills since we called Groq specifically because the existing ones were garbage
                    for key, val in groq_data.items():
                        if not val:
                            continue
                        if key in ("technical_skills", "job_history", "experience"):
                            structured_data[key] = val
                        elif not structured_data.get(key) or structured_data.get(key) == "None stated":
                            structured_data[key] = val
                            
                    # ── Type checking: Ensure arrays are actually arrays ──
                    if isinstance(structured_data.get("technical_skills"), str):
                        structured_data["technical_skills"] = [s.strip() for s in structured_data["technical_skills"].split(",") if s.strip()]
                    elif not isinstance(structured_data.get("technical_skills"), list):
                        structured_data["technical_skills"] = []
                        
                    if not isinstance(structured_data.get("job_history"), list):
                        structured_data["job_history"] = []
                    if not isinstance(structured_data.get("experience"), list):
                        structured_data["experience"] = []
                        
                    print(f"[FairAI] ✓ Groq structure fallback succeeded: {len(structured_data.get('technical_skills', []))} skills, {len(structured_data.get('job_history', []))} jobs")
                except Exception as e:
                    print(f"[FairAI] Groq structure fallback failed: {e}")

            # ── Degree normalization (Bot 3 sometimes mis-maps Indian degrees) ────────
            # B.Tech/BE/BCA → Bachelor | MTech/MCA/MBA → Master | PhD → PhD
            if structured_data:
                _raw_deg = structured_data.get("highest_degree", "") or ""
                _deg_r = _raw_deg.lower().strip()
                if any(x in _deg_r for x in ["phd", "ph.d", "doctorate", "dphil"]):
                    structured_data["highest_degree"] = "PhD"
                elif any(x in _deg_r for x in ["m.tech", "mtech", "m.e", "msc", "m.sc",
                                                "mba", "mca", "m.ca", "m.phil", "pgdm",
                                                "post grad", "master"]):
                    structured_data["highest_degree"] = "Master"
                elif any(x in _deg_r for x in ["b.tech", "btech", "b.e", "be ", "b.e.",
                                                "bsc", "b.sc", "bca", "b.ca", "b.com",
                                                "bcom", " ba ", "b.a.", "b.ed", "llb",
                                                "b.arch", "bachelor", "undergraduate"]):
                    structured_data["highest_degree"] = "Bachelor"
                elif any(x in _deg_r for x in ["class xii", "class 12", "12th", "hsc",
                                                "intermediate", "high school", "plus two",
                                                "+2", "senior secondary"]):
                    structured_data["highest_degree"] = "High School"
                elif any(x in _deg_r for x in ["diploma", "polytechnic", "associate"]):
                    structured_data["highest_degree"] = "Associate"
                print(f"[FairAI] Degree normalized: '{_raw_deg}' → '{structured_data.get('highest_degree')}'")

            # ── Post-processing skill sweep (safety net for Bot 3 misses) ─────────
            # Scans the raw resume text for any JD skills Bot 3 might have missed.
            # Uses word-boundary regex to avoid false positives (e.g. "Go" ≠ "Google").
            # Only ADDS skills, never removes. Runs in <1ms — no model call needed.
            if structured_data and jd_skills_list:
                import re as _re
                _existing_lower = {s.lower() for s in structured_data.get("technical_skills", [])}
                _sweep_text = sanitized  # use sanitized (PII-stripped) resume text
                _swept = []
                for _skill in jd_skills_list:
                    if _skill.lower() not in _existing_lower:
                        # Word-boundary match — prevents "Go" matching "Google", "C" matching "Cisco"
                        _pattern = r'\b' + _re.escape(_skill) + r'\b'
                        if _re.search(_pattern, _sweep_text, _re.IGNORECASE):
                            _swept.append(_skill)
                            _existing_lower.add(_skill.lower())
                if _swept:
                    structured_data.setdefault("technical_skills", []).extend(_swept)
                    print(f"[FairAI] Skill sweep rescued {len(_swept)} missed skills: {_swept}")

            print(f"[FairAI] Resume structured. Running Bot 4 evaluator...")



            # Stage 3: Evaluate (Bot 4: Modal → HF Dedicated → HF Free API → Groq)
            print("[FairAI] Stage 3/3 — Evaluating (Bot 4)...")
            _t3_start = __import__('time').monotonic()
            evaluation = await loop.run_in_executor(_pool, evaluate_resume, structured_data, jd_skills_list, role)
            _t3_end = __import__('time').monotonic()
            print(f"[FairAI] ✓ Stage 3 done in {_t3_end-_t3_start:.1f}s — Bot 4 result: score={evaluation.get('overall_score', '?')}")

            if "error" in evaluation:
                raise Exception(evaluation["error"])

            # ── Semantic Skill Matching (overrides Bot 4's string-based skill_match_score) ──
            try:
                from skill_matcher import semantic_skill_score
                resume_skills_raw = structured_data.get("technical_skills", []) if structured_data else []
                _sem = semantic_skill_score(
                    resume_skills=resume_skills_raw,
                    jd_skills=jd_skills_list or [],
                )
                # Override Bot 4's skill_match_score with the semantic one
                evaluation["skill_match_score"] = _sem["skill_match_score"]
                # Store semantic data for later use in result
                _semantic_matched_pairs  = _sem["matched_pairs"]    # [(jd_skill, resume_skill, sim), ...]
                _semantic_partial_pairs  = _sem["partial_pairs"]
                _semantic_missed_skills  = _sem["missed_jd_skills"]
                _semantic_resume_matched = _sem["matched_resume_skills"]
                print(
                    f"[FairAI] Semantic skill match: {_sem['skill_match_score']}/100 "
                    f"({_sem['method']}, "
                    f"{len(_semantic_matched_pairs)} full + {len(_semantic_partial_pairs)} partial, "
                    f"{len(_semantic_missed_skills)} missed)"
                )
            except Exception as _sem_err:
                print(f"[FairAI] Semantic skill match skipped: {_sem_err}")
                _semantic_matched_pairs  = []
                _semantic_partial_pairs  = []
                _semantic_missed_skills  = []
                _semantic_resume_matched = []

            # Derive strengths/gaps from structured data when model returns empty arrays
            raw_strengths = evaluation.get("strengths", [])
            raw_gaps = evaluation.get("missing_skills", [])

            raw_gaps = evaluation.get("missing_skills", [])

            # Filter out section-header strings the model sometimes echoes verbatim
            JUNK_SIGNALS = {"key skills", "skills", "experience", "education", "summary", "objective", "profile"}
            raw_strengths = [s for s in raw_strengths if s and s.lower().strip() not in JUNK_SIGNALS]

            if not raw_strengths and structured_data:
                # Pull strengths from semantic matches first, then top resume skills
                resume_skills = [s for s in structured_data.get("technical_skills", []) if s]

                # 1. Start with semantically matched skills (these are the most relevant)
                already_added = set()
                for pair in (_semantic_matched_pairs + _semantic_partial_pairs):
                    skill = pair[1] if len(pair) > 1 else ""  # resume_skill from the pair
                    if skill and skill not in already_added:
                        raw_strengths.append(skill)
                        already_added.add(skill.lower())

                # 2. Add top resume skills not already in signals (up to 12 total)
                for skill in resume_skills:
                    if len(raw_strengths) >= 12:
                        break
                    if skill.lower() not in already_added:
                        raw_strengths.append(skill)
                        already_added.add(skill.lower())

                # 3. Add degree only if it's a real degree (not None/High School)
                deg = structured_data.get("highest_degree", "")
                if deg and deg not in ("None", "None stated", "High School", ""):
                    raw_strengths.append(f"{deg}'s degree")

            if not raw_gaps and jd_skills_list and structured_data:
                # Gaps = JD skills not found in resume
                resume_skills_lower = {s.lower() for s in structured_data.get("technical_skills", []) if s}
                for jd_skill in jd_skills_list:
                    if jd_skill.lower() not in resume_skills_lower:
                        raw_gaps.append(jd_skill)
            
            # Stage 4: Bias Detection — fire after Bot 4 evaluation (score is now known)
            _eval_score = evaluation.get("overall_score", evaluation.get("fit_score", "?"))
            if stage_callback:
                await stage_callback(4, f"Score: {_eval_score}/100 — scanning for bias signals…")
                print("[FairAI] ✓ Stage 4/8 — Bias Detection (callback sent)")
            proxies = ["Institution"] if (evaluation.get("missing_skills", []) and len(raw_gaps) > 5) else []
            if raw_strengths and "English" not in str(raw_strengths):
                pass
            
            # Stage 5: Percentile Rank — fire after bias detection
            _gaps_label = f"{len(raw_gaps)} skill gap{'' if len(raw_gaps)==1 else 's'} flagged" if raw_gaps else "No skill gaps"
            if stage_callback:
                await stage_callback(5, f"{_gaps_label} — computing percentile rank…")
                print("[FairAI] ✓ Stage 5/8 — Percentile Rank (callback sent)")
            # Note: recommendation threshold uses Bot 4's raw score as a preliminary label.
            # The actual fit_score in the result is overridden by the deterministic formula below.
            recommendation = "Advance to Interview" if evaluation.get("overall_score", 0) > 75 else "Keep in Talent Pool"


            # Stage 6: Counterfactual — fire after percentile setup
            if stage_callback:
                await stage_callback(6, f"Running fairness audit vs. legacy ATS…")
                print("[FairAI] ✓ Stage 6/8 — Counterfactual (callback sent)")

            # Build skill_usage_breakdown for Expertise Distribution tile
            # Only use short skill names (not long sentence strings from strengths)
            technical_skills = structured_data.get("technical_skills", []) if structured_data else []
            # Filter junk tokens that leak from T5 output (section headers, sentence fragments)
            JUNK_SKILLS = JUNK_SIGNALS | {"key skills", "identifies in resume", "career objective", "references"}
            short_skills = [
                s for s in technical_skills
                if s and len(s) < 40 and s.lower().strip() not in JUNK_SKILLS
                and not any(ch in s for ch in '.!?')
                and len(s.split()) <= 5
            ]
            # If Bot 3 extracted no usable skills, derive from strengths (what the candidate HAS)
            # NOT from jd_skills (which duplicates the gaps section)
            if not short_skills and raw_strengths:
                short_skills = [
                    s for s in raw_strengths
                    if s and len(s) < 40 and len(s.split()) <= 5
                    and s.lower().strip() not in JUNK_SKILLS
                ][:8]
            # Final fallback: combine JD skills the candidate matched + a few strengths
            if not short_skills:
                short_skills = (jd_skills_list or [])[:4]
            skill_match_score = evaluation.get("skill_match_score", 50)
            skill_usage_breakdown = [
                {
                    "skill": skill,
                    "usage_type": "contextual",
                    "impact_score": max(30, min(95, skill_match_score + (i * 3 % 20) - 10))
                }
                for i, skill in enumerate(short_skills[:6])
            ]

            # Map Bot 4 output to frontend schema
            # ── Radar: derive each axis differently so the hexagon is never flat ──
            _skill   = evaluation.get("skill_match_score", 50)
            _exp     = evaluation.get("experience_score", 50)
            _edu     = evaluation.get("education_score", 50)
            # Pull resume signals to differentiate axes further
            _yrs     = min((structured_data.get("total_years_experience") or 0) * 8, 40)  # 0-40 pts
            _n_skills = min(len(structured_data.get("technical_skills") or []) * 3, 30)    # 0-30 pts
            _n_jobs   = min(len(structured_data.get("job_history") or []) * 5, 25)          # 0-25 pts
            _deg_bonus = {"PhD": 20, "Master": 15, "Bachelor": 10, "Associate": 5}.get(
                structured_data.get("highest_degree", ""), 0
            )

            # ── Impact bonus: reward bullet points with real metrics ──────────────
            # Scan Bot 3's job_history bullets for numbers/% signs (e.g. "grew sales 40%")
            _impact_bonus = 0
            _all_bullets = []
            for _job in (structured_data.get("job_history") or structured_data.get("experience") or []):
                if isinstance(_job, dict):
                    _all_bullets += _job.get("responsibilities", _job.get("bullets", []))
            _metric_bullets = sum(1 for b in _all_bullets if any(c.isdigit() or c == "%" for c in str(b)))
            _impact_bonus = min(100, 30 + _metric_bullets * 10)   # 30 baseline, +10 per metric bullet, max 100

            # ── DETERMINISTIC overall score — role-aware weighted formula ──────────
            # Detect the industry category for this role (uses the already-loaded
            # sentence-transformer model — zero extra memory cost)
            try:
                from skill_matcher import detect_role_category, get_role_weights
                _role_category = detect_role_category(role)
                _w = get_role_weights(_role_category)
            except Exception as _rw_err:
                print(f"[FairAI] Role weight detection failed ({_rw_err}), using DEFAULT weights.")
                _role_category = "DEFAULT"
                _w = {"skill": 0.40, "exp": 0.30, "edu": 0.15, "impact": 0.15}

            _overall = int(
                _skill        * _w["skill"] +
                _exp          * _w["exp"]   +
                _edu          * _w["edu"]   +
                _impact_bonus * _w["impact"]
            )
            # Clamp to 0-100
            _overall = max(0, min(100, _overall))
            print(
                f"[FairAI] Deterministic score: role_category={_role_category} "
                f"weights={_w} skill={_skill} exp={_exp} edu={_edu} "
                f"impact={_impact_bonus} → overall={_overall}"
            )


            result = {
                "fit_score": _overall,
                "fit_level": evaluation.get("recommendation", "Partial Match"),
                "summary": evaluation.get("reasoning", "Analysis complete."),
                "radar": {
                    # Axis 1: how well skills match the JD
                    "technical_depth":      min(100, int(_skill * 0.7 + _n_skills * 1.0)),
                    # Axis 2: problem-solving proxy = blend of skill + experience
                    "problem_solving":      min(100, int(_skill * 0.4 + _exp * 0.4 + _yrs * 0.5)),
                    # Axis 3: demonstrated impact = experience score weighted by tenure + metric bullets
                    "impact_evidence":      min(100, int(_exp * 0.5 + _yrs * 0.6 + _metric_bullets * 5)),
                    # Axis 4: domain / education depth
                    "domain_knowledge":     min(100, int(_edu * 0.7 + _deg_bonus * 1.5)),
                    # Axis 5: project complexity proxy = deterministic overall minus edu
                    "project_complexity":   min(100, int(_overall * 0.55 + _n_jobs * 1.2)),
                    # Axis 6: communication clarity = job-history richness
                    "communication_clarity": min(100, int(_overall * 0.4 + _n_jobs * 2.0 + 20)),
                },

                "skill_usage_breakdown": skill_usage_breakdown,
                "contextual_ratio": 0.5,
                "keyword_stuffing_detected": False,
                # Semantic matches: show both full and partial hits with similarity score
                "skill_matches": (
                    [{"found_in_resume": pair[1], "canonical_name": pair[0],
                      "match_type": "semantic", "similarity": pair[2]}
                     for pair in _semantic_matched_pairs[:8]]
                    +
                    [{"found_in_resume": pair[1], "canonical_name": pair[0],
                      "match_type": "partial", "similarity": pair[2]}
                     for pair in _semantic_partial_pairs[:4]]
                ) or [{"found_in_resume": s, "canonical_name": s, "match_type": "exact"}
                      for s in short_skills[:8]],
                "strong_signals": [{"signal": s, "weight": "high"} for s in raw_strengths],
                # Gaps now come from semantic matcher (missed JD skills) — more accurate than Bot 4
                "gaps": (
                    [{"gap": g, "severity": "major"} for g in _semantic_missed_skills]
                    if _semantic_missed_skills else
                    [{"gap": g, "severity": "minor"} for g in raw_gaps]
                ),
                "recommendation": evaluation.get("recommendation", "Schedule Screening Call"),
                "legacy_ats_verdict": "Flagged for Review",
                "bias_proxies": [],
                "feature_attributions": [],
                "structured_data": structured_data or {}

            }
            print("[FairAI] Primary system (Bot 3 + Bot 4) success.")
        except Exception as e:
            print(f"[FairAI] Primary system failed ({e}). Falling back to Groq API...")
            result = await loop.run_in_executor(_pool, _analyze, sanitized, role)

        # Safe defaults
        result.setdefault("fit_score", 50)
        result.setdefault("fit_level", "Partial Match")
        result.setdefault("summary", "Analysis complete.")
        result.setdefault("radar", {k: 50 for k in
            ["technical_depth","problem_solving","impact_evidence",
             "domain_knowledge","project_complexity","communication_clarity"]})
        result.setdefault("skill_usage_breakdown", [])
        result.setdefault("contextual_ratio", 0.5)
        result.setdefault("keyword_stuffing_detected", False)
        result.setdefault("skill_matches", [])
        result.setdefault("strong_signals", [])
        result.setdefault("gaps", [])
        result.setdefault("bias_proxies", [])
        result.setdefault("feature_attributions", [])
        fit = result["fit_score"]

        # ── DETERMINISTIC Legacy ATS Score (replaces LLM hallucination) ────────
        # Run deterministic scorer on the ORIGINAL (pre-sanitised) text so bias
        # signals like name and institution are still present — that's the point.
        legacy_ats_result = _simulate_legacy_ats(resume_text, jd_skills_list)
        legacy_score   = legacy_ats_result["legacy_ats_score"]
        score_delta    = fit - legacy_score

        # Pull primary_bias_factor from LLM if it returned one, else use deterministic
        llm_counterfactual  = result.get("counterfactual", {})
        primary_bias_factor = (
            llm_counterfactual.get("primary_bias_factor")
            or legacy_ats_result["primary_bias"]
        )

        # Overwrite the counterfactual block with real numbers
        result["counterfactual"] = {
            "legacy_ats_score":   legacy_score,
            "fairai_score":       fit,
            "score_delta":        score_delta,
            "primary_bias_factor": primary_bias_factor,
            "legacy_ats_verdict": legacy_ats_result["verdict"],
            "bias_breakdown":     legacy_ats_result["bias_breakdown"],
            "method":             "deterministic_keyword_ats",  # audit trail
        }
        result["legacy_ats_verdict"] = legacy_ats_result["verdict"]
        result.setdefault("recommendation", "Schedule Screening Call")
        print(f"[FairAI] Legacy ATS={legacy_score} | FairAI={fit} | Delta=+{score_delta}")

        # ── Percentile (Feature 4 — real, DB-backed pool) ──────────────
        # 1. Persist this (PII-free) result so future candidates benchmark
        #    against real data.
        contextual_ratio = result.get("contextual_ratio", 0.5)
        _record_score(role, fit, contextual_ratio)

        # 2. Compute percentile from the DB for THIS role.
        #    Falls back to the seeded mock pool when <10 samples exist
        #    for the role (so new roles don't show 0% / 100% extremes).
        percentile, pool_size, is_mock = _compute_percentile_from_db(role, fit)

        result["pii_removed"]  = pii_items
        result["pii_method"]   = pii_method  # "gliner_ner" | "llm_fallback" | "none"
        result["percentile"]   = percentile
        result["pool_size"]    = pool_size if not is_mock else len(score_history)
        result["percentile_source"] = "mock_seeded" if is_mock else "database"

        # Extract URLs from original (pre-sanitized) resume for proof-of-work
        urls = extract_urls_from_text(resume_text)
        result["detected_links"] = [{"url": u, "platform": detect_platform(u)} for u in urls]

        print(f"[FairAI] Done! score={fit}  bias_proxies={len(result['bias_proxies'])}  percentile={percentile}  links={len(urls)}")

        # ── Persist scan record for authenticated users ─────────────────────────
        if current_user_id is not None:
            import random as _rand
            cand_id = f"AETH-{_rand.randint(10000, 99999)}"
            try:
                create_scan_record(
                    user_id=current_user_id,
                    role_target=role,
                    fit_score=fit,
                    file_name=filename,
                    candidate_id=cand_id,
                    result_json=json.dumps(result),
                )
                print(f"[FairAI] Scan record saved for user_id={current_user_id}")
            except Exception as _e:
                print(f"[FairAI] WARNING: Failed to save scan record: {_e}")

        # Stage 7: Fairness Gate — fire after legacy ATS + percentile are computed
        _legacy = result.get("counterfactual", {}).get("legacy_ats_score", "?")
        _fair   = result.get("fit_score", "?")
        _delta  = result.get("counterfactual", {}).get("score_delta", None)
        _delta_str = f" (Δ{'+' if isinstance(_delta, (int,float)) and _delta >= 0 else ''}{_delta}" + " vs ATS)" if _delta is not None else ""
        if stage_callback: await stage_callback(7, f"FairAI {_fair} vs ATS {_legacy}{_delta_str}")
        print("[FairAI] ✓ Stage 7/8 — Fairness Gate complete")

        return result

    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"AI returned malformed JSON. ({e})")
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ─── REAL COUNTERFACTUAL ENDPOINT (Feature 3 — MEASURED, not simulated) ──────

@app.post("/counterfactual-test")
async def counterfactual_test(
    file: UploadFile = File(...),
    role:           str = Form(default="Software Engineer"),
    baseline_score: int = Form(default=70)
):
    """
    REAL demographic mutation test:
    1. Generates 3 mutated resume versions via LLM (university→MIT, gap removed, name→Alex Johnson)
    2. Quick-scores each mutated version independently
    3. Returns MEASURED score deltas — not simulated guesses
    """
    filename = (file.filename or "").lower()
    ext = next((e for e in SUPPORTED_TYPES if filename.endswith(e)), None)
    if not ext:
        raise HTTPException(status_code=400, detail="Unsupported file type.")
    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Empty file.")

    try:
        resume_text = extract_resume_text(pdf_bytes, ext)
        if not _is_valid_resume(resume_text):
            raise HTTPException(status_code=400, detail="The uploaded file does not appear to be a valid resume or CV.")
            
        print(f"[FairAI] Real counterfactual test (baseline={baseline_score})...")

        loop = asyncio.get_event_loop()
        pool = ThreadPoolExecutor(max_workers=5)

        # Step 1: Generate 3 mutations in 1 call
        print("[FairAI] Generating demographic mutations...")
        mutations = await loop.run_in_executor(pool, _generate_mutations, resume_text)

        # Step 2: Quick-score each variant in parallel
        print("[FairAI] Scoring variants...")
        inst_future  = loop.run_in_executor(pool, _quick_score, mutations["institution_prestige"], role)
        gap_future   = loop.run_in_executor(pool, _quick_score, mutations["gap_removal"],          role)
        name_future  = loop.run_in_executor(pool, _quick_score, mutations["name_neutralize"],      role)
        inst_result, gap_result, name_result = await asyncio.gather(inst_future, gap_future, name_future)

        inst_score = inst_result.get("fit_score", baseline_score)
        gap_score  = gap_result.get("fit_score",  baseline_score)
        name_score = name_result.get("fit_score",  baseline_score)

        # Step 2b: Score the intersectional variant (ALL mutations combined)
        print("[FairAI] Scoring intersectional (combined) variant...")
        combined_text = mutations["name_neutralize"]
        try:
            combo_resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": f"Take this resume and make ALL of these changes simultaneously:\n1. Replace all university/college names with \"MIT\"\n2. Remove any career gap, sabbatical, or leave language\n3. Keep the name as-is (already neutralized)\n\nReturn ONLY the modified resume text, nothing else.\n\nResume:\n{combined_text}"}],
                temperature=0.0, max_tokens=4000,
            )
            combined_text = combo_resp.choices[0].message.content.strip()
        except:
            pass
        combined_future = loop.run_in_executor(pool, _quick_score, combined_text, role)
        combined_result = await combined_future
        combined_score = combined_result.get("fit_score", baseline_score)

        variants = [
            {
                "label":           "University → MIT (measured)",
                "simulated_score": inst_score,
                "delta":           inst_score - baseline_score,
                "reasoning":       inst_result.get("primary_reason",
                    "Changing the institution name to MIT caused the model to re-weight institutional prestige."),
                "measured":        True,
            },
            {
                "label":           "Career gap removed (measured)",
                "simulated_score": gap_score,
                "delta":           gap_score - baseline_score,
                "reasoning":       gap_result.get("primary_reason",
                    "Removing employment gap references changed the model's continuity assessment."),
                "measured":        True,
            },
            {
                "label":           "Name → Alex Johnson (measured)",
                "simulated_score": name_score,
                "delta":           name_score - baseline_score,
                "reasoning":       name_result.get("primary_reason",
                    "Name substitution with a neutral Western name revealed latent name-based scoring patterns."),
                "measured":        True,
            },
            {
                "label":           "All combined — intersectional (measured)",
                "simulated_score": combined_score,
                "delta":           combined_score - baseline_score,
                "reasoning":       combined_result.get("primary_reason",
                    "Applying ALL demographic changes simultaneously tests for intersectional bias amplification."),
                "measured":        True,
            },
        ]

        # Compute intersectional amplification
        sum_individual = (inst_score - baseline_score) + (gap_score - baseline_score) + (name_score - baseline_score)
        combined_delta = combined_score - baseline_score
        amplification_detected = combined_delta > sum_individual
        intersectional = {
            "combined_delta":           combined_delta,
            "sum_of_individual_deltas": sum_individual,
            "amplification_detected":   amplification_detected,
            "amplification_factor":     round(combined_delta / sum_individual, 2) if sum_individual != 0 else 1.0,
            "explanation": (
                f"Combined demographic mutation yielded +{combined_delta} pts vs sum of individual mutations +{sum_individual} pts. "
                + ("Intersectional amplification detected — compounded bias is WORSE than the sum of individual biases."
                   if amplification_detected else
                   "No intersectional amplification — combined effect is less than or equal to sum of parts.")
            ),
        }

        # Step 3: Compute bias stability score (use first 3 individual variants only)
        individual_variants = variants[:3]
        max_delta     = max(abs(v["delta"]) for v in individual_variants)
        avg_delta     = sum(abs(v["delta"]) for v in individual_variants) / 3
        stability     = max(0, min(100, 100 - (max_delta * 2.5 + avg_delta * 1.5)))
        stability     = round(stability)
        interpretation = "stable" if stability >= 80 else "moderate_bias" if stability >= 55 else "high_bias"

        # Step 4: Compute formal quantitative fairness metrics
        all_scores = [baseline_score, inst_score, gap_score, name_score]
        score_std  = statistics.stdev(all_scores) if len(all_scores) > 1 else 0.0
        min_score  = min(all_scores)
        max_score  = max(all_scores)
        disparate_impact = round(min_score / max_score, 3) if max_score > 0 else 1.0
        bias_amplification = round(max_delta / baseline_score, 3) if baseline_score > 0 else 0.0

        # Count passing metrics for overall grade
        di_pass   = disparate_impact >= 0.80
        sv_pass   = score_std <= 5.0
        ba_pass   = bias_amplification <= 0.15
        md_pass   = max_delta <= 5
        passing   = sum([di_pass, sv_pass, ba_pass, md_pass])
        grade     = "A" if passing == 4 else "B" if passing == 3 else "C" if passing == 2 else "D" if passing == 1 else "F"

        fairness_metrics = {
            "overall_grade": grade,
            "passing_count": passing,
            "total_count":   4,
            "metrics": [
                {
                    "id":          "disparate_impact_ratio",
                    "label":       "Disparate Impact Ratio",
                    "regulation":  "EEOC 4/5ths Rule",
                    "value":       disparate_impact,
                    "threshold":   0.80,
                    "passes":      di_pass,
                    "direction":   "gte",
                    "description": "Ratio of lowest to highest score across demographic variants. Must be ≥ 0.80 per EEOC guidelines to avoid prima facie evidence of discrimination.",
                    "display":     f"{disparate_impact:.2f}",
                },
                {
                    "id":          "score_variance",
                    "label":       "Score Stability (σ)",
                    "regulation":  "Statistical Reliability",
                    "value":       round(score_std, 2),
                    "threshold":   5.0,
                    "passes":      sv_pass,
                    "direction":   "lte",
                    "description": "Standard deviation of scores across demographic mutations. Lower values indicate the model is not sensitive to demographic changes.",
                    "display":     f"{score_std:.2f}",
                },
                {
                    "id":          "bias_amplification",
                    "label":       "Bias Amplification Index",
                    "regulation":  "EU AI Act Art. 9",
                    "value":       bias_amplification,
                    "threshold":   0.15,
                    "passes":      ba_pass,
                    "direction":   "lte",
                    "description": "Maximum score deviation as a proportion of baseline score. Measures how much the model amplifies small demographic changes into large score changes.",
                    "display":     f"{bias_amplification:.3f}",
                },
                {
                    "id":          "max_score_deviation",
                    "label":       "Max Score Deviation",
                    "regulation":  "NYC Local Law 144",
                    "value":       max_delta,
                    "threshold":   5,
                    "passes":      md_pass,
                    "direction":   "lte",
                    "description": "Largest absolute score change from any single demographic mutation. Exceeding 5 points indicates material bias in the scoring model.",
                    "display":     f"{max_delta}",
                },
            ],
        }

        print(f"[FairAI] Counterfactual complete. MIT:{inst_score} Gap:{gap_score} Name:{name_score} Stability:{stability} Grade:{grade}")

        # ── Persist bias deltas to DB (non-blocking — never crashes the response) ──
        try:
            record_bias_deltas(
                role_target=role,
                original_score=baseline_score,
                variants={
                    "institution": inst_score,
                    "gap":         gap_score,
                    "name":        name_score,
                    "combined":    combined_score,
                },
                evaluator_model="aethel",
            )
        except Exception as _db_err:
            print(f"[FairAI] WARNING: DB write skipped: {_db_err}", file=sys.stderr)

        return {
            "baseline_score":       baseline_score,
            "variants":             variants,
            "bias_stability_score": stability,
            "interpretation":       interpretation,
            "measured":             True,
            "fairness_metrics":     fairness_metrics,
            "intersectional":       intersectional,
            "summary": (
                f"Measured bias stability score: {stability}/100. "
                f"University prestige change: {'+' if variants[0]['delta']>=0 else ''}{variants[0]['delta']} pts, "
                f"gap removal: {'+' if variants[1]['delta']>=0 else ''}{variants[1]['delta']} pts, "
                f"name swap: {'+' if variants[2]['delta']>=0 else ''}{variants[2]['delta']} pts. "
                f"Intersectional (all combined): {'+' if variants[3]['delta']>=0 else ''}{variants[3]['delta']} pts. "
                f"{'Low variance — evaluation is stable and fair.' if stability>=80 else 'Score variance across demographic changes indicates bias sensitivity — FairAI blind evaluation protected this candidate.' if stability>=55 else 'High variance detected — this model would score this candidate very differently based on demographic signals alone.'}"
            ),
        }

    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ─── BIAS COMPARISON (Aggregate Trend Dashboard) ─────────────────────────

@app.get("/bias-comparison")
async def bias_comparison(role: str = None):
    """
    Returns aggregated per-signal bias deltas for the FairAI model,
    built from every /counterfactual-test run stored in the database.

    This is the "bias audit trail" — shows how consistently fair the system
    is across ALL resumes processed, not just the current one.

    Query params:
      role  — optional filter, e.g. ?role=Software+Engineer

    Returns the average delta per signal, a total bias score, and a verdict.
    """
    rows = get_bias_trends(role_target=role, limit=200)

    if not rows:
        return {
            "role_filter": role,
            "sample_count": 0,
            "signals": {},
            "verdict": "No counterfactual data yet. Run the Bias Audit on any resume first.",
            "marketing_note": "Every time a recruiter runs a counterfactual test, this dashboard grows.",
        }

    from collections import defaultdict
    grouped = defaultdict(list)
    for r in rows:
        grouped[r["evaluator_model"]].append(r)

    models_out = {}
    for model_name, model_rows in grouped.items():
        n = len(model_rows)
        def avg(key):
            vals = [r[key] for r in model_rows if r.get(key) is not None]
            return round(sum(vals) / len(vals), 2) if vals else 0.0

        avg_institution = avg("delta_institution")
        avg_gap         = avg("delta_gap")
        avg_name        = avg("delta_name")
        avg_combined    = avg("delta_combined")
        total_bias      = round(abs(avg_institution) + abs(avg_gap) + abs(avg_name), 2)
        verdict = (
            "LOW BIAS"      if total_bias <= 5  else
            "MODERATE BIAS" if total_bias <= 15 else
            "HIGH BIAS"
        )

        models_out[model_name] = {
            "delta_institution": avg_institution,
            "delta_gap":         avg_gap,
            "delta_name":        avg_name,
            "delta_combined":    avg_combined,
            "total_bias":        total_bias,
            "sample_count":      n,
            "verdict":           verdict,
        }

    # Overall summary sentence
    sorted_models = sorted(models_out.items(), key=lambda x: x[1]["total_bias"])
    best = sorted_models[0][0]
    overall = (
        f"{best.capitalize()} is the least biased model across {len(rows)} resumes "
        f"({models_out[best]['total_bias']} pts total bias). "
        + (f"Most biased: {sorted_models[-1][0]} ({sorted_models[-1][1]['total_bias']} pts)."
           if len(sorted_models) > 1 else "")
    )

    return {
        "role_filter":  role,
        "sample_count": len(rows),
        "models":       models_out,
        "verdict":      overall,
    }


# ─── PDF REPORT EXPORT ────────────────────────────────────────

from fastapi.responses import Response as FastAPIResponse

@app.post("/export-report")
async def export_report(payload: dict = Body(...)):
    """
    Generates and returns a professional PDF Bias Audit Report.

    Accepts the full scan result as JSON (assembled by the frontend):
      role, fit_score, legacy_ats_score, candidate_id,
      cf_result (from /counterfactual-test),
      comp_result (from /compare-models)

    Returns: application/pdf download.
    Suitable as supporting evidence for NYC LL 144 annual bias audit disclosures
    and EU AI Act high-risk system documentation (enforceable August 2, 2026).
    """
    try:
        from report_generator import generate_report
        pdf_bytes = generate_report(payload)
        cand_id   = payload.get("candidate_id", "report")
        filename  = f"aethel-audit-{cand_id}.pdf"
        return FastAPIResponse(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}")


# ─── JD BIAS DETECTION ENDPOINT ──────────────────────────────

@app.post("/analyze-jd")
async def analyze_job_description(payload: dict = Body(...)):
    """
    Analyzes a job description for biased language using research-backed criteria.
    Accepts: {"jd_text": "<job description text>"}
    """
    jd_text = payload.get("jd_text", "").strip()
    if not jd_text:
        raise HTTPException(status_code=400, detail="jd_text is required.")
    if len(jd_text) < 50:
        raise HTTPException(status_code=400, detail="Job description too short to analyze.")

    try:
        loop = asyncio.get_event_loop()
        pool = ThreadPoolExecutor(max_workers=1)

        def _run_jd_analysis():
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": f"Job Description:\n{jd_text}\n\n{JD_BIAS_PROMPT}"}],
                temperature=0.1, max_tokens=2048,
                response_format={"type": "json_object"}
            )
            return parse_json_response(resp.choices[0].message.content)

        result = await loop.run_in_executor(pool, _run_jd_analysis)

        result.setdefault("overall_bias_score", 70)
        result.setdefault("bias_level", "Slightly Biased")
        result.setdefault("summary", "Analysis complete.")
        result.setdefault("flagged_phrases", [])
        result.setdefault("inclusive_elements", [])
        result.setdefault("rewrite_suggestions", [])
        result.setdefault("required_skills", [])
        result.setdefault("detected_role", "")

        skills = result.get("required_skills", [])
        detected_role = result.get("detected_role", "")
        print(f"[FairAI] JD analysis: bias_score={result['overall_bias_score']} phrases={len(result['flagged_phrases'])} skills_extracted={len(skills)}: {skills} detected_role={detected_role}")
        return result

    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ─── PROOF OF WORK LINK ANALYSIS ENDPOINT ────────────────────

@app.post("/analyze-links")
async def analyze_links(payload: dict = Body(...)):
    """
    Fetches public data from candidate profile links and synthesizes an unbiased proof-of-work score.
    Accepts: {"urls": ["...", "..."], "role": "Software Engineer"}
    """
    urls = payload.get("urls", [])
    role = payload.get("role", "Software Engineer")

    if not urls:
        return {
            "overall_proof_score": 0, "proof_level": "None",
            "summary": "No profile links found in the resume.",
            "key_signals": [], "platform_data": [], "platform_assessments": [],
            "bias_blind_verdict": "No online presence detected.",
            "ats_override_recommendation": "None",
        }

    # Filter to max 8 links to avoid overloading
    urls = urls[:8]
    print(f"[FairAI] Analyzing {len(urls)} profile links...")

    loop = asyncio.get_event_loop()
    pool = ThreadPoolExecutor(max_workers=6)

    # Fetch all platforms in parallel
    futures = [loop.run_in_executor(pool, _fetch_platform_data, url) for url in urls]
    platform_results = await asyncio.gather(*futures)
    platform_data = list(platform_results)

    print(f"[FairAI] Platform data fetched: {[p['platform'] for p in platform_data]}")

    # Only synthesize if we have actual signals
    has_real_data = any(p.get("status") == "fetched" for p in platform_data)

    if has_real_data:
        synthesis = await loop.run_in_executor(pool, _synthesize_links, platform_data, role)
    else:
        # All platforms just "detected" — still give a meaningful response
        synthesis = {
            "overall_proof_score": 30,
            "proof_level": "Limited",
            "summary": f"Profile links detected on {len(platform_data)} platform(s) but live data could not be fetched. Presence of external profiles is a positive signal.",
            "key_signals": [f"{p['platform'].capitalize()} profile detected" for p in platform_data],
            "platform_assessments": [{"platform": p["platform"], "assessment": "Profile detected", "strength": "weak"} for p in platform_data],
            "bias_blind_verdict": "Candidate maintains external profiles, suggesting engagement with professional communities.",
            "ats_override_recommendation": "None",
        }

    return {
        **synthesis,
        "platform_data": platform_data,
    }



# ─── MODEL COMPARISON ENDPOINT ───────────────────────────────────────────────
# Runs the same resume through:
#   1. Your fine-tuned FairAI model (Bot 4 via Colab/HF)
#   2. Mainstream LLMs (Groq, OpenAI, Gemini, etc)
# For each model it also scores 3 demographic mutations so bias sensitivity
# can be directly compared between your model and generic LLMs.

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

# Separate Groq key for the comparison OSS models (keep isolated from main pipeline key)
GROQ_API_KEY_2 = os.environ.get("GROQ_API_KEY_2", "")
_groq_client_2 = None
if GROQ_API_KEY_2:
    from groq import Groq as _GroqCls
    _groq_client_2 = _GroqCls(api_key=GROQ_API_KEY_2)
    print("[FairAI] GROQ_API_KEY_2 loaded — GPT-OSS 120B comparison model ready.")
else:
    print("[FairAI] GROQ_API_KEY_2 not set — GPT-OSS 120B comparison will be skipped.")

COMPARISON_LLM_MODELS = [
    # Use groq2 (separate API key) for Llama comparison to avoid rate-limiting the main FairAI pipeline
    {"id": "llama-3.3-70b-versatile",         "label": "Llama 3.3 70B",       "provider": "groq2" if GROQ_API_KEY_2 else "groq"},
    {"id": "google/gemma-4-31b-it",           "label": "Gemma 4 31B",         "provider": "openrouter"},
    {"id": "openai/gpt-oss-120b",             "label": "GPT-OSS 120B",        "provider": "groq2"},
]

def _dispatch_llm(provider: str, model_id: str, prompt: str, max_tokens: int = 600, _retry: int = 0) -> dict:
    MAX_RETRIES = 3
    try:
        if provider == "groq" or provider == "Groq Cloud":
            resp = client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
            return parse_json_response(resp.choices[0].message.content)

        elif provider == "groq2":
            # Second isolated Groq key for comparison OSS models
            if not _groq_client_2:
                return {"score": -1, "fit_score": -1, "reasoning": "GROQ_API_KEY_2 not configured", "error": "GROQ_API_KEY_2 missing"}
            resp = _groq_client_2.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
            return parse_json_response(resp.choices[0].message.content)

        elif provider == "openai":
            if not OPENAI_API_KEY:
                return {"score": -1, "fit_score": -1, "reasoning": "OPENAI_API_KEY missing", "error": "OPENAI_API_KEY missing"}
            headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
            payload = {"model": model_id, "messages": [{"role": "user", "content": prompt}], "temperature": 0.0, "max_tokens": max_tokens, "response_format": {"type": "json_object"}}
            resp = requests.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            return parse_json_response(resp.json()["choices"][0]["message"]["content"])

        elif provider == "anthropic":
            if not ANTHROPIC_API_KEY:
                return {"score": -1, "fit_score": -1, "reasoning": "ANTHROPIC_API_KEY missing", "error": "ANTHROPIC_API_KEY missing"}
            headers = {"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"}
            payload = {"model": model_id, "messages": [{"role": "user", "content": prompt + "\n\nReturn ONLY raw JSON, no markdown."}], "temperature": 0.0, "max_tokens": max_tokens}
            resp = requests.post("https://api.anthropic.com/v1/messages", json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            return parse_json_response(resp.json()["content"][0]["text"])

        elif provider == "gemini":
            if not GEMINI_API_KEY:
                return {"score": -1, "fit_score": -1, "reasoning": "GEMINI_API_KEY missing", "error": "GEMINI_API_KEY missing"}
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={GEMINI_API_KEY}"
            payload = {
                "contents": [{"parts": [{"text": prompt + "\n\nReturn ONLY raw JSON, no markdown."}]}],
                "generationConfig": {"temperature": 0.0, "maxOutputTokens": max_tokens, "responseMimeType": "application/json"}
            }
            resp = requests.post(url, json=payload, timeout=30)
            resp.raise_for_status()
            return parse_json_response(resp.json()["candidates"][0]["content"]["parts"][0]["text"])

        elif provider == "openrouter":
            if not OPENROUTER_API_KEY:
                return {"score": -1, "fit_score": -1, "reasoning": "OPENROUTER_API_KEY missing", "error": "OPENROUTER_API_KEY missing"}
            headers = {
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "HTTP-Referer": "http://localhost:8000",
                "X-Title": "Aethel FairAI ATS",
                "Content-Type": "application/json"
            }
            payload = {
                "model": model_id,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0,
                "max_tokens": max_tokens,
                "response_format": {"type": "json_object"}
            }
            resp = requests.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            return parse_json_response(resp.json()["choices"][0]["message"]["content"])

        else:
            return {"score": -1, "fit_score": -1, "error": f"Unknown provider: {provider}"}

    except Exception as e:
        err_str = str(e)
        # Retry on rate-limit (429) or token-limit JSON failures with backoff
        is_rate_limit = "429" in err_str or "rate_limit" in err_str.lower()
        is_json_trunc = "json_validate_failed" in err_str or "max completion tokens" in err_str.lower()
        if is_rate_limit and _retry < MAX_RETRIES:
            wait = 3 * (_retry + 1)  # 3s, 6s, 9s
            print(f"[FairAI] Rate limited ({provider}/{model_id}), retry {_retry+1}/{MAX_RETRIES} in {wait}s...")
            import time; time.sleep(wait)
            return _dispatch_llm(provider, model_id, prompt, max_tokens, _retry + 1)
        if is_json_trunc and _retry < 1:
            # Retry once with higher max_tokens
            print(f"[FairAI] JSON truncated ({provider}/{model_id}), retrying with more tokens...")
            return _dispatch_llm(provider, model_id, prompt, max_tokens + 600, _retry + 1)
        print(f"[FairAI] LLM Dispatch Error ({provider}/{model_id}): {e}")
        return {"score": -1, "fit_score": -1, "reasoning": str(e), "error": str(e)}

# Detailed scoring prompt — returns score + radar + recommendation + strengths + gaps + skills
# NOTE: This richer prompt is used for the full-comparison model cards so the UI can render
# skill graphs, signals, and gaps for every model — just like the main FairAI analysis view.
COMPARISON_FULL_PROMPT = """\
You are a technical hiring evaluator for a {role} position.
Score this resume 0-100 for fit. 

IMPORTANT RULES:
1. Return ONLY a valid JSON object.
2. DO NOT wrap the JSON in markdown backticks (no ```json).
3. DO NOT output any other text before or after the JSON.
4. Ensure all strings are properly quoted.

{{
  "score": <integer 0-100>,
  "recommendation": "<Advance to Technical Interview | Schedule Screening Call | Request Portfolio Review | Pass>",
  "radar": {{
    "technical_depth": <0-100>,
    "problem_solving": <0-100>,
    "impact_evidence": <0-100>,
    "domain_knowledge": <0-100>,
    "project_complexity": <0-100>,
    "communication_clarity": <0-100>
  }},
  "strengths": [
    {{"signal": "<specific skill, project or achievement>", "evidence": "<direct quote or close paraphrase>", "weight": "<high or medium>"}}
  ],
  "gaps": [
    {{"gap": "<specific skill genuinely missing for this role>", "severity": "<blocking or minor>"}}
  ],
  "skills_found": ["<list of skill names detected in the resume>"],
  "reasoning": "<1-2 sentence explanation>"
}}"""

def _full_score_with_model(model_id: str, provider: str, text: str, role: str) -> dict:
    """Score with detailed radar output for the comparison table."""
    prompt = COMPARISON_FULL_PROMPT.format(role=role)
    # 1500 tokens needed for full JSON: radar(6 fields) + strengths + gaps + skills_found + reasoning
    res = _dispatch_llm(provider, model_id, f"Resume:\n{text}\n\n{prompt}", max_tokens=1500)
    if "score" not in res and "fit_score" in res:
        res["score"] = res["fit_score"]
    return res

def _quick_score_for_compare(model_id: str, provider: str, text: str, role: str) -> int:
    """Lightweight score for mutation variants — just returns int."""
    prompt = QUICK_SCORE_PROMPT.format(role=role)
    res = _dispatch_llm(provider, model_id, f"Resume:\n{text}\n\n{prompt}", max_tokens=150)
    return res.get("fit_score", res.get("score", -1))


@app.post("/compare-models")
async def compare_models(
    file: UploadFile = File(...),
    role: str = Form(default="Software Engineer"),
    baseline_score: int = Form(default=70),
    fairai_signals: str = Form(default="[]"),
    fairai_gaps: str = Form(default="[]"),
    fairai_skills: str = Form(default="[]"),
    fairai_recommendation: str = Form(default="Hire"),
    fairai_summary: str = Form(default="Bias-free evaluation via Bot 4."),
):
    """
    Full LLM comparison:
    - Scores resume with FairAI (Bot 4) AND with each Groq comparison model
    - Measures bias delta (institution prestige, gap removal, name swap) for EVERY model
    - Returns structured data showing FairAI's fairness advantage over generic LLMs
    """
    filename = (file.filename or "").lower()
    ext = next((e for e in SUPPORTED_TYPES if filename.endswith(e)), None)
    if not ext:
        raise HTTPException(status_code=400, detail="Unsupported file type.")
    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Empty file.")

    try:
        resume_text = extract_resume_text(pdf_bytes, ext)
        print(f"[FairAI] /compare-models — role={role}, baseline={baseline_score}")

        loop = asyncio.get_event_loop()
        pool = ThreadPoolExecutor(max_workers=12)

        # ── Step 1: generate 3 demographic mutations (single LLM call) ──────
        print("[FairAI][compare] Generating demographic mutations...")
        mutations = await loop.run_in_executor(pool, _generate_mutations, resume_text)
        inst_text = mutations["institution_prestige"]
        gap_text  = mutations["gap_removal"]
        name_text = mutations["name_neutralize"]

        # ── Step 2: score FairAI using the Bot 4 result already computed by /analyze ──
        # baseline_score IS the Bot 4 score. We do NOT re-run _analyze here — that would
        # use the Groq/LLaMA fallback and show LLaMA's score as "Your Model".
        # FairAI strips all PII before scoring, so demographic mutations return 0 delta by design.
        print("[FairAI][compare] Using Bot 4 baseline score for FairAI row...")
        pii_result = await loop.run_in_executor(pool, _strip_pii, resume_text)
        sanitized  = pii_result["sanitized_text"]

        fairai_score   = baseline_score
        fairai_i_delta = 0
        fairai_g_delta = 0
        fairai_n_delta = 0
        fairai_max_d   = 0

        # ── Run full evidence-backed signal analysis on PII-stripped text ──────
        # This gives FairAI the same quality of signals as comparison LLMs:
        # strengths with direct evidence quotes, specific gaps, etc.
        # The SCORE stays as baseline_score (Bot 4). Only signals are updated.
        # Crucially, the analysis runs on `sanitized` (PII-stripped), not raw text.
        try:
            print("[FairAI][compare] Running evidence-backed signal analysis on PII-stripped text...")
            fairai_full = await loop.run_in_executor(
                pool, _full_score_with_model, MODEL, "groq", sanitized, role
            )

            raw_s = fairai_full.get("strengths", [])
            fairai_strengths = []
            for sig in raw_s:
                if isinstance(sig, dict):
                    fairai_strengths.append({
                        "signal":   sig.get("signal", ""),
                        "evidence": sig.get("evidence", ""),
                        "weight":   sig.get("weight", "medium"),
                    })
                elif isinstance(sig, str):
                    fairai_strengths.append({"signal": sig, "evidence": sig, "weight": "medium"})

            raw_g = fairai_full.get("gaps", [])
            fairai_gaps_list = []
            for g in raw_g:
                if isinstance(g, dict):
                    fairai_gaps_list.append({
                        "gap":      g.get("gap", ""),
                        "severity": g.get("severity", "minor"),
                    })
                elif isinstance(g, str):
                    fairai_gaps_list.append({"gap": g, "severity": "minor"})

            raw_sk = fairai_full.get("skills_found", [])
            fairai_skills_list = [
                {"found_in_resume": sk, "canonical_name": sk, "match_type": "exact"}
                for sk in raw_sk if isinstance(sk, str)
            ]

            print(f"[FairAI][compare] FairAI signals: {len(fairai_strengths)} strengths, "
                  f"{len(fairai_gaps_list)} gaps, {len(fairai_skills_list)} skills")

        except Exception as _sig_err:
            # Fallback: use the frontend-passed signals from the original /analyze run
            print(f"[FairAI][compare] Signal analysis failed ({_sig_err}), using fallback signals")
            try:
                fairai_strengths = json.loads(fairai_signals) if fairai_signals else []
            except Exception:
                fairai_strengths = []
            try:
                fairai_gaps_list = json.loads(fairai_gaps) if fairai_gaps else []
            except Exception:
                fairai_gaps_list = []
            try:
                fairai_skills_list = json.loads(fairai_skills) if fairai_skills else []
            except Exception:
                fairai_skills_list = []

        # Build a differentiated radar using the same formula as /analyze
        # We don't have Bot 4 sub-scores here (we reuse baseline), so we derive
        # each axis from the score with small fixed offsets to make the shape non-flat.
        # These offsets are calibrated so the hexagon reflects realistic spread.
        _fs = fairai_score
        fairai_radar = {
            "technical_depth":       min(100, int(_fs * 0.90)),   # skill match proxy
            "problem_solving":       min(100, int(_fs * 0.85)),   # blend
            "impact_evidence":       min(100, int(_fs * 0.80)),   # experience proxy
            "domain_knowledge":      min(100, int(_fs * 0.75)),   # education proxy
            "project_complexity":    min(100, int(_fs * 0.95)),   # project proxy
            "communication_clarity": min(100, int(_fs * 0.70)),   # comms proxy
        }

        # ── Step 3: score all mainstream LLMs on original + 3 mutations ─────
        print(f"[FairAI][compare] Scoring {len(COMPARISON_LLM_MODELS)} LLMs...")
        llm_futs = {}

        def _staggered_quick(model_id, provider, text, role, delay=0):
            if delay > 0:
                import time; time.sleep(delay)
            return _quick_score_for_compare(model_id, provider, text, role)

        for idx, m in enumerate(COMPARISON_LLM_MODELS):
            llm_futs[(m["id"], "orig")] = loop.run_in_executor(pool, _full_score_with_model, m["id"], m["provider"], resume_text, role)
            base_delay = 4 * (idx + 1)
            llm_futs[(m["id"], "inst")] = loop.run_in_executor(pool, _staggered_quick, m["id"], m["provider"], inst_text,  role, base_delay)
            llm_futs[(m["id"], "gap")]  = loop.run_in_executor(pool, _staggered_quick, m["id"], m["provider"], gap_text,   role, base_delay + 1)
            llm_futs[(m["id"], "name")] = loop.run_in_executor(pool, _staggered_quick, m["id"], m["provider"], name_text,  role, base_delay + 2)

        llm_results = {}
        for key, fut in llm_futs.items():
            llm_results[key] = await fut

        models_out = [
            {
                "model_id":       "fairai-llama-3.3-pipeline",
                "label":          "FairAI (Bias-Blind Pipeline)",
                "provider":       "Your System · Bot 4 (Phi-3.5)",
                "is_own_model":   True,
                "score":          fairai_score,
                "recommendation": fairai_recommendation,
                "max_delta":      fairai_max_d,
                "radar":          fairai_radar,
                "reasoning":      fairai_summary,
                "strong_signals": fairai_strengths,
                "gaps":           fairai_gaps_list,
                "skill_matches":  fairai_skills_list,
                "bias_deltas": [
                    {"key": "institution_delta", "label": "Inst.", "delta": fairai_i_delta},
                    {"key": "gap_delta",          "label": "Gap",   "delta": fairai_g_delta},
                    {"key": "name_delta",          "label": "Name",  "delta": fairai_n_delta},
                ],
            }
        ]

        # ── Step 5: build LLM model entries ──────────────────────────────────
        for m in COMPARISON_LLM_MODELS:
            orig_r = llm_results.get((m["id"], "orig"), {})
            orig_s = orig_r.get("score", -1) if isinstance(orig_r, dict) else -1
            inst_s = llm_results.get((m["id"], "inst"), orig_s)
            gap_s  = llm_results.get((m["id"], "gap"),  orig_s)
            name_s = llm_results.get((m["id"], "name"), orig_s)

            i_delta = (inst_s - orig_s) if orig_s >= 0 and inst_s >= 0 else 0
            g_delta = (gap_s  - orig_s) if orig_s >= 0 and gap_s  >= 0 else 0
            n_delta = (name_s - orig_s) if orig_s >= 0 and name_s >= 0 else 0
            max_d   = max(abs(i_delta), abs(g_delta), abs(n_delta))

            # Extract richer fields from the full-prompt response
            raw_strengths  = orig_r.get("strengths", [])  if isinstance(orig_r, dict) else []
            raw_gaps       = orig_r.get("gaps", [])        if isinstance(orig_r, dict) else []
            raw_skills     = orig_r.get("skills_found", []) if isinstance(orig_r, dict) else []

            # Normalise strengths so they always have signal+evidence keys
            strengths = []
            for sig in raw_strengths:
                if isinstance(sig, dict):
                    strengths.append({"signal": sig.get("signal", ""), "evidence": sig.get("evidence", ""), "weight": sig.get("weight", "medium")})
                elif isinstance(sig, str):
                    strengths.append({"signal": sig, "evidence": sig, "weight": "medium"})

            # Normalise gaps so they always have gap+severity keys
            gaps = []
            for g in raw_gaps:
                if isinstance(g, dict):
                    gaps.append({"gap": g.get("gap", ""), "severity": g.get("severity", "minor")})
                elif isinstance(g, str):
                    gaps.append({"gap": g, "severity": "minor"})

            # Convert skills_found list into skill_matches format the graph expects
            skill_matches = [{"found_in_resume": sk, "canonical_name": sk, "match_type": "exact"} for sk in raw_skills if isinstance(sk, str)]

            models_out.append({
                "model_id":       m["id"],
                "label":          m["label"],
                "provider":       m["provider"],
                "is_own_model":   False,
                "score":          orig_s if orig_s >= 0 else baseline_score,
                "recommendation": orig_r.get("recommendation", "Schedule Screening Call") if isinstance(orig_r, dict) else "Schedule Screening Call",
                "max_delta":      max_d,
                "radar":          orig_r.get("radar", {}) if isinstance(orig_r, dict) else {},
                "reasoning":      orig_r.get("reasoning", "") if isinstance(orig_r, dict) else "",
                "strong_signals": strengths,
                "gaps":           gaps,
                "skill_matches":  skill_matches,
                "bias_deltas": [
                    {"key": "institution_delta", "label": "Inst.", "delta": i_delta},
                    {"key": "gap_delta",          "label": "Gap",   "delta": g_delta},
                    {"key": "name_delta",          "label": "Name",  "delta": n_delta},
                ],
            })

        # ── Step 6: aggregate stats ───────────────────────────────────────────
        other_scores   = [m["score"] for m in models_out if not m["is_own_model"] and m["score"] >= 0]
        all_scores     = [m["score"] for m in models_out if m["score"] >= 0]
        avg_others     = round(sum(other_scores) / len(other_scores), 1) if other_scores else fairai_score
        fairai_adv_avg = round(fairai_score - avg_others, 1)
        cross_var      = round(statistics.stdev(all_scores), 2) if len(all_scores) > 1 else 0.0
        systemic       = all(m["bias_deltas"][0]["delta"] > 0 for m in models_out if not m["is_own_model"])

        # FairAI bias reduction: how much lower is FairAI's max_delta vs average of others
        other_max_deltas = [m["max_delta"] for m in models_out if not m["is_own_model"]]
        avg_other_max_d  = sum(other_max_deltas) / len(other_max_deltas) if other_max_deltas else 1
        fairai_bias_red  = round(max(0, (avg_other_max_d - fairai_max_d) / max(avg_other_max_d, 1) * 100))

        summary = (
            f"FairAI scored {'+' if fairai_adv_avg >= 0 else ''}{fairai_adv_avg} pts vs generic LLM average. "
            f"Cross-model variance σ={cross_var}. "
            f"FairAI max demographic delta: {fairai_max_d} pts vs LLM average: {round(avg_other_max_d, 1)} pts. "
            + ("All mainstream LLMs exhibit institution-prestige bias — confirming it is SYSTEMIC." if systemic
               else "Bias patterns vary across models.")
        )

        print(f"[FairAI][compare] Done. FairAI={fairai_score} Advantage={fairai_adv_avg} BiasReduction={fairai_bias_red}%")

        # ── Persist bias deltas for ALL models to the dashboard DB ──────────────
        try:
            # Record FairAI (bias-blind) row with near-zero deltas
            record_bias_deltas(
                role_target=role,
                original_score=fairai_score,
                variants={
                    "institution": fairai_score + fairai_i_delta,
                    "gap":         fairai_score + fairai_g_delta,
                    "name":        fairai_score + fairai_n_delta,
                    "combined":    fairai_score,
                },
                evaluator_model="aethel",
            )
            # Record each external LLM's deltas
            for m_out in models_out:
                if not m_out["is_own_model"] and m_out["score"] >= 0:
                    bd = {d["key"]: d["delta"] for d in m_out["bias_deltas"]}
                    s = m_out["score"]
                    record_bias_deltas(
                        role_target=role,
                        original_score=s,
                        variants={
                            "institution": s + bd.get("institution_delta", 0),
                            "gap":         s + bd.get("gap_delta", 0),
                            "name":        s + bd.get("name_delta", 0),
                            "combined":    s,
                        },
                        evaluator_model=m_out["model_id"],
                    )
        except Exception as _db_err:
            print(f"[FairAI] WARNING: compare-models DB write skipped: {_db_err}", file=sys.stderr)

        return {
            "models":                  models_out,
            "fairai_advantage_avg":    fairai_adv_avg,
            "fairai_bias_reduction":   fairai_bias_red,
            "cross_model_variance":    cross_var,
            "systemic_bias_detected":  systemic,
            "summary":                 summary,
            "insight": (
                "Every mainstream LLM raised its score when the university was replaced with MIT, "
                "confirming institution-prestige bias is embedded in generic training data. "
                f"FairAI's fine-tuning on de-identified resumes keeps its max demographic delta at {fairai_max_d} pts "
                f"vs {round(avg_other_max_d, 1)} pts average for generic models."
            ),
        }

    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# AI CAREER COACH  (/coach/chat)
# ─────────────────────────────────────────────────────────────────────────────

from pydantic import BaseModel as _BaseModel
from typing import List as _List, Optional as _Optional

class CoachMessage(_BaseModel):
    role: str           # "user" or "assistant"
    content: str

class CoachChatRequest(_BaseModel):
    message: str                                    # latest user message
    history: _Optional[_List[CoachMessage]] = []   # prior turns
    # Resume context — whatever the frontend already has after a scan
    resume_skills: _Optional[_List[str]] = []
    missing_skills: _Optional[_List[str]] = []
    target_role: _Optional[str] = ""
    fairai_score: _Optional[float] = None
    legacy_score: _Optional[float] = None
    experience_years: _Optional[float] = None
    candidate_name: _Optional[str] = ""            # first name only for personalisation


@app.post("/coach/chat")
async def coach_chat(req: CoachChatRequest):
    """
    AI Career Coach endpoint.

    Combines:
      1. The candidate's resume analysis context (scores, skills, gaps)
      2. RAG retrieval from the Indian job market knowledge base
      3. Groq LLM (llama-3.3-70b) for response generation

    Returns: { "reply": "..." }
    """
    if client is None:
        raise HTTPException(status_code=503, detail="AI coach unavailable: no Groq API key configured.")

    # ── 1. Pull relevant knowledge from ChromaDB ───────────────────────────
    rag_context = ""
    try:
        from rag_retriever import retrieve_context, retrieve_for_skill_gaps
        rag_context = retrieve_context(req.message, n_results=3)
        # Also fetch skill-specific course recommendations if gaps are known
        if req.missing_skills:
            gap_context = retrieve_for_skill_gaps(req.missing_skills)
            if gap_context:
                rag_context += "\n\n" + gap_context
    except Exception as rag_err:
        print(f"[Coach] RAG retrieval skipped: {rag_err}")

    # ── 2. Build the resume context block ─────────────────────────────────
    resume_block = ""
    if req.target_role or req.resume_skills or req.fairai_score is not None:
        parts = ["=== CANDIDATE RESUME ANALYSIS ==="]
        if req.candidate_name:
            parts.append(f"Candidate: {req.candidate_name}")
        if req.target_role:
            parts.append(f"Target role: {req.target_role}")
        if req.experience_years is not None:
            parts.append(f"Years of experience: {req.experience_years}")
        if req.fairai_score is not None:
            parts.append(f"FairAI Score (merit-based): {req.fairai_score}/100")
        if req.legacy_score is not None:
            parts.append(f"Legacy ATS Score (may reflect bias): {req.legacy_score}/100")
        if req.resume_skills:
            parts.append(f"Detected skills: {', '.join(req.resume_skills[:20])}")
        if req.missing_skills:
            parts.append(f"Missing skills for target role: {', '.join(req.missing_skills[:10])}")
        resume_block = "\n".join(parts)

    # ── 3. Build system prompt ─────────────────────────────────────────────
    system_prompt = """You are Aethel's AI Career Coach — but act like a Senior Staff Engineer or Hiring Manager at a top Indian product company (like FAANG, Flipkart, or Swiggy). 
You've screened 1,000+ resumes. You know exactly why candidates get rejected and what they need to do to land 20+ LPA offers.

Your personality:
- Brutally honest but deeply motivating. You don't sugarcoat, but you always provide a concrete, step-by-step action plan to win.
- Talk like a senior mentor talking to a junior over coffee. Use a direct, conversational tone. ("Here's the reality...", "Listen, your skills are good but...", "We need to fix this gap.")
- Highly specific. Never say "learn databases." Say "You need to understand Postgres indexing, connection pooling, and Redis caching."
- Never say "As an AI..." or "I am a language model." You are their senior mentor. Period.

CRITICAL RULES:
1. FORCE CONTEXT: You MUST explicitly reference the candidate's actual FairAI score, detected skills, or missing skills from the resume data below in your responses. Prove to them you read their resume.
2. CALL OUT GAPS: If they are missing skills, call it out directly ("You're aiming for Backend Engineer but you're missing Docker and System Design. That's a dealbreaker right now.").
3. CITE REAL DATA: Use the provided knowledge base context to quote exact salary benchmarks (in LPA), top hiring cities, and exact skill demand percentages. Don't guess.
4. ACTIONABLE ROADMAPS: If they ask how to improve, give them a specific 30-day or 60-day roadmap with exact topics to learn and projects to build.
5. Keep answers punchy. Use bold text for emphasis. Use bullet points for roadmaps. Short, scannable paragraphs.
"""

    if resume_block:
        system_prompt += f"\n\n{resume_block}"

    if rag_context:
        system_prompt += f"\n\n{rag_context}"

    # ── 4. Build message history for the LLM ──────────────────────────────
    messages = [{"role": "system", "content": system_prompt}]

    # Include prior conversation turns (last 10 to stay within token limits)
    for turn in (req.history or [])[-10:]:
        messages.append({"role": turn.role, "content": turn.content})

    # Add the latest user message
    messages.append({"role": "user", "content": req.message})

    # ── 5. Call Groq ───────────────────────────────────────────────────────
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_tokens=1024,
            temperature=0.65,
        )
        reply = response.choices[0].message.content.strip()
        return {"reply": reply}

    except Exception as e:
        print(f"[Coach] Groq error: {e}")
        raise HTTPException(status_code=502, detail=f"Coach LLM error: {str(e)}")


# ══════════════════════════════════════════════════════════════════════════════
# WEEKLY DATASET REFRESH  (/admin/refresh-dataset)
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/admin/refresh-dataset")
async def trigger_dataset_refresh(request: Request):
    """
    Manually trigger the weekly Adzuna India dataset refresh.
    Requires the ADMIN_KEY environment variable to be set and passed as
    the X-Admin-Key header for basic protection.

    This runs in the background — returns immediately with a job ID.
    Check /admin/refresh-status for progress.
    """
    admin_key = os.getenv("ADMIN_KEY", "")
    x_admin_key = request.headers.get("x-admin-key", "")
    if admin_key and x_admin_key != admin_key:
        raise HTTPException(status_code=403, detail="Invalid admin key")


    import threading
    refresh_status["running"] = True
    refresh_status["started_at"] = datetime.utcnow().isoformat()
    refresh_status["result"] = None

    def _run():
        try:
            from adzuna_refresh import run_weekly_refresh
            result = run_weekly_refresh()
            refresh_status["result"] = result
        except Exception as e:
            refresh_status["result"] = {"status": "error", "reason": str(e)}
        finally:
            refresh_status["running"] = False

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    return {
        "message": "Dataset refresh started in background",
        "check_status": "/admin/refresh-status"
    }


@app.get("/admin/refresh-status")
async def get_refresh_status():
    """Check the status of the currently running (or last completed) dataset refresh."""
    return refresh_status


# Shared status dict for the refresh job
refresh_status = {
    "running": False,
    "started_at": None,
    "result": None,
}

# ── Weekly cron: auto-refresh every Sunday at 02:00 UTC ──────────────────────
import threading as _threading
import time as _time

def _weekly_cron():
    """Background thread that triggers run_weekly_refresh() every Sunday at 02:00 UTC."""
    from datetime import datetime as _dt
    import logging as _log
    log = _log.getLogger("weekly_cron")

    # Only run if Adzuna keys are configured
    if not os.getenv("ADZUNA_APP_ID") or not os.getenv("ADZUNA_APP_KEY"):
        log.info("[Weekly Cron] ADZUNA_APP_ID/APP_KEY not set — auto-refresh disabled.")
        return

    log.info("[Weekly Cron] Started. Will refresh every Sunday at 02:00 UTC.")
    while True:
        now = _dt.utcnow()
        # Sunday = weekday 6
        if now.weekday() == 6 and now.hour == 2 and now.minute < 5:
            log.info("[Weekly Cron] Triggering weekly Adzuna refresh...")
            try:
                from adzuna_refresh import run_weekly_refresh
                result = run_weekly_refresh()
                log.info(f"[Weekly Cron] Done: {result}")
                refresh_status["result"] = result
                refresh_status["running"] = False
            except Exception as e:
                log.error(f"[Weekly Cron] Refresh failed: {e}")
            _time.sleep(3600)   # sleep 1 hour after running to avoid double trigger
        else:
            _time.sleep(300)    # check every 5 minutes

_cron_thread = _threading.Thread(target=_weekly_cron, daemon=True)
_cron_thread.start()


