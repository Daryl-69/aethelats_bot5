"""
skill_matcher.py  —  Semantic Skill Matching + Role-Aware Score Weights
========================================================================
1. Replaces naive string-match skill scoring with sentence-embeddings + cosine
   similarity so that "Machine Learning" ↔ "ML Engineering", "React.js" ↔ "React",
   "LLMs" ↔ "Large Language Models" etc all count as matches.

2. Maps any free-text job role ("Senior Golang Backend Engineer") to one of
   8 industry categories and returns the right scoring weight profile so that
   skill, experience, education, and impact are weighted correctly per role type.

Usage:
    from skill_matcher import semantic_skill_score, detect_role_category, get_role_weights
    result = semantic_skill_score(
        resume_skills=["Python", "Machine Learning", "TensorFlow"],
        jd_skills=["Python", "ML Engineering", "Deep Learning", "Docker"],
    )
    category = detect_role_category("Senior Golang Backend Engineer")
    weights  = get_role_weights(category)
    # weights = {"skill": 0.45, "exp": 0.28, "edu": 0.12, "impact": 0.15}
"""

from __future__ import annotations
import logging
from functools import lru_cache
from typing import Optional

import numpy as np

log = logging.getLogger("skill_matcher")

# ── thresholds ────────────────────────────────────────────────────────────────
MATCH_THRESHOLD   = 0.72   # cosine similarity >= this → matched
PARTIAL_THRESHOLD = 0.55   # between these → partial credit (0.5 weight)
MODEL_NAME        = "all-MiniLM-L6-v2"   # 90 MB, CPU-fast, great quality

# ── Role category weight profiles ─────────────────────────────────────────────
# Weights: skill (JD skill match), exp (experience relevance),
#          edu (education importance), impact (metric bullets / proof of work)
# All four weights MUST sum to 1.0
ROLE_WEIGHTS: dict[str, dict[str, float]] = {
    "ENGINEERING": {"skill": 0.45, "exp": 0.28, "edu": 0.12, "impact": 0.15},
    "DATA_SCIENCE": {"skill": 0.40, "exp": 0.25, "edu": 0.20, "impact": 0.15},
    "PRODUCT":     {"skill": 0.30, "exp": 0.35, "edu": 0.15, "impact": 0.20},
    "DESIGN":      {"skill": 0.35, "exp": 0.28, "edu": 0.10, "impact": 0.27},
    "SALES":       {"skill": 0.20, "exp": 0.40, "edu": 0.05, "impact": 0.35},
    "MARKETING":   {"skill": 0.25, "exp": 0.35, "edu": 0.10, "impact": 0.30},
    "FINANCE":     {"skill": 0.30, "exp": 0.30, "edu": 0.25, "impact": 0.15},
    "HEALTHCARE":  {"skill": 0.30, "exp": 0.25, "edu": 0.35, "impact": 0.10},
    "DEFAULT":     {"skill": 0.40, "exp": 0.30, "edu": 0.15, "impact": 0.15},
}

# ── Category anchor descriptions (rich sentences that embed well) ─────────────
# Each is a descriptive sentence — the model understands context better than
# a single word. More tokens = richer embedding = better classification.
CATEGORY_DESCRIPTIONS: dict[str, str] = {
    "ENGINEERING": (
        "Software engineer, backend developer, frontend developer, full stack engineer, "
        "mobile developer, iOS, Android, DevOps, SRE, platform engineer, cloud engineer, "
        "systems engineer, QA, SDET, embedded engineer, firmware, Go, Java, Python, C++, "
        "Rust, Kubernetes, Docker, microservices, APIs, infrastructure"
    ),
    "DATA_SCIENCE": (
        "Data scientist, machine learning engineer, AI engineer, NLP engineer, "
        "deep learning, MLOps, data analyst, business intelligence, data engineer, "
        "data pipeline, analytics engineer, research scientist, computer vision, "
        "LLM, generative AI, statistics, TensorFlow, PyTorch, Spark, SQL, Tableau"
    ),
    "PRODUCT": (
        "Product manager, product owner, program manager, scrum master, agile coach, "
        "product lead, head of product, associate product manager, APM, growth product, "
        "B2B product, SaaS product, roadmap, user stories, PRD, stakeholder management"
    ),
    "DESIGN": (
        "UX designer, UI designer, product designer, visual designer, interaction designer, "
        "graphic designer, motion designer, brand designer, design lead, Figma, Adobe XD, "
        "user research, usability testing, design systems, typography, illustration"
    ),
    "SALES": (
        "Sales executive, account executive, business development, BDR, SDR, "
        "enterprise sales, inside sales, field sales, sales manager, VP of sales, "
        "revenue, CRM, Salesforce, quota, pipeline, prospecting, B2B sales, SaaS sales"
    ),
    "MARKETING": (
        "Marketing manager, digital marketing, growth hacker, SEO specialist, "
        "content marketer, social media manager, performance marketing, brand manager, "
        "email marketing, demand generation, CMO, paid ads, Google Ads, Meta Ads"
    ),
    "FINANCE": (
        "Chartered accountant, financial analyst, investment banker, CFO, controller, "
        "audit, taxation, FP&A, treasury, risk analyst, compliance officer, CFA, CPA, "
        "financial modeling, valuation, private equity, venture capital, accounting"
    ),
    "HEALTHCARE": (
        "Doctor, nurse, pharmacist, physiotherapist, radiologist, medical officer, "
        "clinical researcher, healthcare administrator, MBBS, MD, paramedic, dentist, "
        "veterinarian, lab technician, hospital management, public health, epidemiology"
    ),
}

# Pre-compute category embeddings once at module level (populated lazily)
_CATEGORY_EMBEDDINGS: dict[str, np.ndarray] = {}


def _get_category_embeddings() -> dict[str, np.ndarray]:
    """Return (or compute) fixed embeddings for the 8 category descriptions."""
    global _CATEGORY_EMBEDDINGS
    if _CATEGORY_EMBEDDINGS:
        return _CATEGORY_EMBEDDINGS
    model = _get_model()
    if model is None:
        return {}
    try:
        texts = list(CATEGORY_DESCRIPTIONS.values())
        keys  = list(CATEGORY_DESCRIPTIONS.keys())
        embs  = model.encode(texts, batch_size=16, show_progress_bar=False)
        _CATEGORY_EMBEDDINGS = dict(zip(keys, embs))
        log.info(f"[SkillMatcher] Category embeddings computed for {len(keys)} categories.")
    except Exception as e:
        log.warning(f"[SkillMatcher] Category embedding failed: {e}")
    return _CATEGORY_EMBEDDINGS


def detect_role_category(role: str) -> str:
    """
    Map any free-text role string to one of the 8 category keys.

    Uses cosine similarity between the role embedding and each category
    description embedding. Falls back to 'DEFAULT' if the model isn't
    available or the best similarity is too low.

    Examples:
        "Senior Golang Backend Engineer"  → "ENGINEERING"
        "ML Research Scientist"           → "DATA_SCIENCE"
        "VP of Enterprise Sales"          → "SALES"
        "Chartered Accountant Mumbai"     → "FINANCE"
    """
    if not role or not role.strip():
        return "DEFAULT"

    cat_embs = _get_category_embeddings()
    if not cat_embs:
        return "DEFAULT"

    model = _get_model()
    if model is None:
        return "DEFAULT"

    try:
        role_emb = model.encode([role.strip()], show_progress_bar=False)[0]
        best_cat  = "DEFAULT"
        best_sim  = 0.0
        for cat, cat_emb in cat_embs.items():
            sim = _cosine_similarity(role_emb, cat_emb)
            if sim > best_sim:
                best_sim = sim
                best_cat = cat
        # If nothing is a decent match, fall back to DEFAULT
        if best_sim < 0.20:
            best_cat = "DEFAULT"
        log.info(f"[SkillMatcher] Role '{role}' → {best_cat} (sim={best_sim:.3f})")
        return best_cat
    except Exception as e:
        log.warning(f"[SkillMatcher] Role detection failed: {e}")
        return "DEFAULT"


def get_role_weights(category: str) -> dict[str, float]:
    """Return the scoring weight profile for a given category key."""
    return ROLE_WEIGHTS.get(category, ROLE_WEIGHTS["DEFAULT"])



# ── Singleton model loader ────────────────────────────────────────────────────
@lru_cache(maxsize=1)
def _get_model():
    """Load SentenceTransformer once and cache it for the process lifetime."""
    try:
        from sentence_transformers import SentenceTransformer
        log.info(f"[SkillMatcher] Loading {MODEL_NAME}...")
        model = SentenceTransformer(MODEL_NAME)
        log.info("[SkillMatcher] Model ready.")
        return model
    except Exception as e:
        log.error(f"[SkillMatcher] Failed to load model: {e}")
        return None


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two 1-D vectors."""
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def semantic_skill_score(
    resume_skills: list[str],
    jd_skills: list[str],
    threshold: float = MATCH_THRESHOLD,
    partial_threshold: float = PARTIAL_THRESHOLD,
) -> dict:
    """
    Compute a semantic skill match score between resume and JD skills.

    Returns a dict with:
      - skill_match_score (int 0-100): percentage of JD skills covered
      - matched_pairs: list of (jd_skill, resume_skill, similarity) for full matches
      - partial_pairs: list of (jd_skill, resume_skill, similarity) for partial matches
      - missed_jd_skills: JD skills with no close resume match
      - matched_resume_skills: resume skills that matched something in JD
      - method: "semantic" | "string_fallback"
    """
    # ── Sanitise inputs ────────────────────────────────────────────────────────
    resume_skills = [s.strip() for s in (resume_skills or []) if s and len(s.strip()) > 1]
    jd_skills     = [s.strip() for s in (jd_skills or []) if s and len(s.strip()) > 1]

    if not jd_skills:
        return {
            "skill_match_score": 50,   # can't score without JD — neutral
            "matched_pairs": [],
            "partial_pairs": [],
            "missed_jd_skills": [],
            "matched_resume_skills": resume_skills,
            "method": "no_jd_skills",
        }

    if not resume_skills:
        return {
            "skill_match_score": 0,
            "matched_pairs": [],
            "partial_pairs": [],
            "missed_jd_skills": jd_skills,
            "matched_resume_skills": [],
            "method": "no_resume_skills",
        }

    # ── String-match fast path (exact / lower-case) ───────────────────────────
    resume_lower = {s.lower() for s in resume_skills}
    jd_lower     = {s.lower() for s in jd_skills}
    exact_hits   = jd_lower & resume_lower
    needs_embed  = [s for s in jd_skills if s.lower() not in exact_hits]
    resume_for_embed = [s for s in resume_skills if s.lower() not in exact_hits]

    matched_pairs:   list[tuple] = [(s, s, 1.0) for s in jd_skills if s.lower() in exact_hits]
    partial_pairs:   list[tuple] = []
    missed_jd_skills: list[str]  = []

    # ── Semantic matching for non-exact skills ─────────────────────────────────
    model = _get_model()
    if model is None or not needs_embed or not resume_for_embed:
        # Fallback: treat non-exact as missed
        missed_jd_skills = needs_embed
        method = "string_fallback"
    else:
        try:
            all_texts   = needs_embed + resume_for_embed
            embeddings  = model.encode(all_texts, batch_size=32, show_progress_bar=False)
            jd_embs     = embeddings[:len(needs_embed)]
            res_embs    = embeddings[len(needs_embed):]

            for i, jd_skill in enumerate(needs_embed):
                best_sim   = 0.0
                best_match = ""
                for j, res_skill in enumerate(resume_for_embed):
                    sim = _cosine_similarity(jd_embs[i], res_embs[j])
                    if sim > best_sim:
                        best_sim   = sim
                        best_match = res_skill

                if best_sim >= threshold:
                    matched_pairs.append((jd_skill, best_match, round(best_sim, 3)))
                elif best_sim >= partial_threshold:
                    partial_pairs.append((jd_skill, best_match, round(best_sim, 3)))
                else:
                    missed_jd_skills.append(jd_skill)

            method = "semantic"
        except Exception as e:
            log.warning(f"[SkillMatcher] Semantic encode failed ({e}), falling back to string match.")
            missed_jd_skills = needs_embed
            method = "string_fallback"

    # ── Final score ────────────────────────────────────────────────────────────
    # Full matches count as 1.0, partial matches count as 0.5
    weighted_hits = len(matched_pairs) + 0.5 * len(partial_pairs)
    raw_ratio     = weighted_hits / len(jd_skills)
    skill_match_score = int(round(raw_ratio * 100))

    # Collect all resume skills that contributed to a match
    matched_resume_skills = list({pair[1] for pair in matched_pairs + partial_pairs})

    log.info(
        f"[SkillMatcher] {method}: {len(matched_pairs)} full + {len(partial_pairs)} partial "
        f"/ {len(jd_skills)} JD skills → {skill_match_score}/100"
    )

    return {
        "skill_match_score":   skill_match_score,
        "matched_pairs":       matched_pairs,
        "partial_pairs":       partial_pairs,
        "missed_jd_skills":    missed_jd_skills,
        "matched_resume_skills": matched_resume_skills,
        "method":              method,
    }
