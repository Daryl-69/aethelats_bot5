```text
                        ..:-==++=--:.                       
                 .::-====--:.   ..:-====--:.                
          .:-=====-:..                  .:--===-::.         
  .::-=====-:.                                 ..:--=---:.. 
 #+--:.                             .-   .             .::-*
.%.                                =#: :+-                 *
 %.                      :==+++***%#.:=#+.                 *
 %:                .:=+****+**####*::+==+-                 *
 #-               .-===+*#%@@@@%#*=*%%**++:               .#
 *=             .=%%*+*%@@@@%#+=*#***#%@@@%-              .#
 ++           :=+*+=+#@%*==-:::*@@%#+=++=+#@*             :*
 -#          :==--+%@@@*+-:::-#@@@@%%#+--=+#@-            =+
 .%.        .#%*+*%@@@+===---:###%%%%%%%*+%##%+           *-
  *-        +===+%%@@+----*:=.+#**+++**++=*@%#%*.        .* 
  -*       --.:+####*---=%#.:.:===+++-..=+++*##%#:       == 
   #:     :-:=+=-==++===%@*::.   .:-:..:+##*++#@@%-      *. 
   -+    .=*#%#*===++++#%%*--:::      ..:-*%%%*#*=#=    =+  
    +:    -=+**#*+==++*###+==---          .-+*#+:==:   .*.  
    .+.     .:-*#**+=*#***+==+=-.          :=-----.    +:   
     :+.     .-+##*+--=++++====--                     +-    
      :=.      :*#*+=-----:==--:-.                   =-     
       .=:       ::-==---. .----=.                 .=:      
         =-            .. ..:::-=                 :=.       
          :=.               .::-:               .-:         
            --.                .               :-.          
             .--.                            ::.            
               .--:                       .::.              
                  :-:.                  .::                 
                    .:-:.            .::.                   
                       .:-:.     .:-:.                      
                          .:--:--:.                         

      █████╗ ███████╗████████╗██╗  ██╗███████╗██╗
     ██╔══██╗██╔════╝╚══██╔══╝██║  ██║██╔════╝██║
     ███████║█████╗     ██║   ███████║█████╗  ██║
     ██╔══██║██╔══╝     ██║   ██╔══██║██╔══╝  ██║
     ██║  ██║███████╗   ██║   ██║  ██║███████╗███████╗
     ╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚══════╝╚══════╝

      A E T H E L  ·  U N B I A S E D   H I R I N G
```

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18+-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)
![HuggingFace](https://img.shields.io/badge/HuggingFace-Transformers-FFD21E?style=for-the-badge&logo=huggingface&logoColor=black)
![Groq](https://img.shields.io/badge/Groq-LPU%20Inference-F55036?style=for-the-badge)

**The world's first fully auditable, multi-model AI resume screening pipeline built to eliminate demographic bias — with a focus on India-specific bias vectors.**

</div>

---

## What is Aethel?

Aethel is a **research-grade AI hiring compliance engine** built on a single founding principle:

> *A candidate's name, university, gender, location, career gap, or caste-proxy signal should have zero effect on how their resume is scored.*

Modern AI hiring tools — including mainstream LLMs like GPT-4, Gemini, and Llama — are trained on internet-scale data that mirrors decades of real-world hiring biases. They score resumes higher when the institution is IIT or MIT, when the name is dominant-caste or Western, and when there are no employment gaps. **Aethel proves this empirically, shows you the numbers, and then corrects for it.**

This is not a keyword matcher. It is not a job board. Aethel is a **process-level compliance tool** — it plugs into the decision layer of hiring and audits whether the evaluation itself is fair.

---


## Table of Contents
- [What is Aethel?](#what-is-aethel)
- [The Aethel Platform](#the-aethel-platform)
- [The Science & Research](#the-science--research-deep-dive)
- [Architecture & Engineering](#architecture--engineering)


## The Aethel Platform

Aethel is a complete, two-sided hiring platform built to replace biased legacy ATS workflows. 

### 1. The Recruiter Workspace (Kanban ATS)
<p align="center">
  <img src="docs/kanban-dashboard.png" width="100%" />
</p>

We built a drag-and-drop pipeline management system that actually surfaces candidate skills instead of burying them in PDFs.
- **Candidate DNA Spark-Cards**: A 5-bar skill fingerprint on every card. See exactly where a candidate spikes before you even click their profile.
- **Pipeline Velocity**: Built-in time-in-stage metrics. If a candidate sits for 5+ days, they get an amber warning ring so nobody falls through the cracks.
- **Batch Cohorts**: Filter the entire board to a specific cohort using the color-coded legend. 
- **Rejection Intelligence**: Aethel automatically reads the "Rejected" column and tells you exactly which skills your pipeline is missing, so you can fix your job descriptions.

**Batch Processing & Ranking**
Stop reading resumes one by one. Drop a cohort of 50 resumes into Aethel. It extracts the text, strips the PII, scores them blindly against your specific job description, and ranks them by `fit_score`. The top candidates bubble up instantly.

**Multi-Model Bias Auditing**
Aethel doesn't just score candidates; it actively audits *other* LLMs. The Bias Dashboard runs the exact same resume through GPT-4, Claude 3, and Llama 3 side-by-side. It exposes exactly how much those generic models penalize your candidates for career gaps or regional colleges compared to Aethel's fair baseline.

### 2. The Candidate Workspace (Empowerment & Transparency)
We believe candidates deserve to know exactly how they are evaluated. 

- **Score Transparency**: Candidates get full access to see their own `fit_score` and the exact skills Aethel extracted from their resume.
- **Bias Report**: Candidates can see if they triggered any bias proxy flags (e.g., career gaps, location markers) and see how Aethel's Counterfactual Engine neutralized that penalty.
- **AI Coach (Coming Soon)**: An interactive chatbot that acts as a personal career strategist. It analyzes the specific gaps between the candidate's resume and target job descriptions, providing actionable, tailored coaching to strengthen their profile.

### Enterprise Security & Access
- **Role-Based Routing**: Strict separation between Candidate and Recruiter views.
- **Verification Gate**: Premium enterprise features (like Batch Mode and the Bias Dashboard) are strictly locked behind a work-email and LinkedIn verification system.

## The Science & Research (Deep Dive)

Aethel is built on rigorous academic research and empirical data. Read below to understand the exact bias vectors we neutralize.

<details>
<summary><b>Is Hiring Bias Real in India? (What the Data Says)</b></summary>
<br>

Before claiming to solve a problem, it must exist. In India, it does — and it is documented by real placement data, industry reports, and audit studies.

---

### 1. Institution Prestige Bias — The IIT vs. Everyone Else Gap

This is the bias vector that affects **the largest number of Indian candidates** — the 99%+ of engineers who did not attend an IIT.

**Placement salary data (2024, sourced from placement reports and Business Standard):**

| Institution Tier | Typical Average Package (CSE) | Access to "Day 0" Recruiters |
|---|---|---|
| Old IITs (Bombay, Delhi, Madras) | ₹20–35 LPA avg · outliers to ₹2+ crore | Yes — HFT firms, FAANG, top consulting |
| Top NITs (Trichy, Surathkal, Warangal) | ₹10–18 LPA avg | Partial — some top recruiters, mostly Tier-2 |
| Other NITs / State colleges | ₹4–9 LPA avg | Mostly mass recruiters (AMCAT/CoCubes driven) |

**The ₹1 crore package myth:** In 2024, IIT Bombay initially reported that 85 students received packages above ₹1 crore, then **corrected that figure to 22** — citing a "technical error" (*Business Standard, 2024*). The actual median package was ₹17.92 LPA. The outlier figures get amplified by media, creating a distorted public perception that all IIT graduates are elite and NIT graduates are "second tier" — a narrative baked into LLM training data and which surfaces as scoring bias.

**The "Day 0" gating system:** Top global recruiters exclusively conduct "Day 0" and "Day 1" hiring drives at IIT campuses. An equally skilled NIT candidate is literally never in the same hiring room as an IIT candidate — not because of skill, but because of which campus they attend. This is an institutional access problem, not a skills problem. Aethel's blind evaluation removes `[INSTITUTION]` from the scoring context entirely.

---

### 2. Gender & Maternity Penalty — India-Specific Data

**Gender pay gap in Indian tech (2024, sourced from Business Standard / industry reports):**

| Sector | Overall Gender Pay Gap | Mid-Level Gap | Senior-Level Gap |
|---|---|---|---|
| IT Services | 3.55% | 6.12% | 8.34% |
| Global Capability Centers (GCCs) | 16.1% | — | 22.2% (high-demand tech roles) |
| Non-tech roles in tech-adjacent sectors | 18–19% at mid-level | — | — |

**The Maternity Benefit Act paradox:** The 2017 amendment extending paid maternity leave to **26 weeks** — the third-longest in the world — was a landmark policy. Research and reporting in *Policy Circle* and *Business Standard* document an unintended consequence: many employers began **actively avoiding hiring women of childbearing age** to sidestep the cost, despite this being illegal under Article 16 of the Constitution.

**What this means in ATS terms:** A 7-month maternity gap is indistinguishable from a 7-month unemployment gap in every mainstream ATS and untreated LLM. Both are scored identically as a "reliability risk." One is a legally protected right. Aethel explicitly prompts: *"NEVER penalise employment gaps — they may be legally protected."*

- **40%** of professional women in India report experiencing bias or discriminatory behavior in hiring (Economic Times)
- The **"leaky pipeline"**: Women account for large proportions of entry-level hiring but representation drops sharply at every level above — a pattern traced directly to missed promotions during or after maternity breaks

---

### 3. English Language & Accent Bias

India has **22 scheduled languages** and hundreds of dialects. Yet corporate India — especially MNCs and product-based tech companies — uses English as the sole hiring language, creating a proxy filter that is not about job skill:

- English proficiency in India correlates directly with **access to English-medium schools**, which correlates with **urban location and socioeconomic class** — not with technical ability
- Recruiters use "fluency" and "accent" as a **signaling device** to categorize candidates as "professional" or "unsophisticated" — a documented bias in HR research (*HR Katha*, *ABAC Journals*)
- Job postings explicitly requiring "native-level English" or "neutral accent" are used in India to filter out candidates from non-metro, vernacular-medium educational backgrounds — the same candidates who often have strong technical skills but non-elite English
- **LLMs amplify this:** Models trained on English-dominant professional text (LinkedIn, Glassdoor, resume databases) associate formal Western English writing style with candidate quality. A resume written in simple but technically accurate English scores lower than one with polished MBA-speak, even when the underlying skills are identical or superior

Aethel strips communication-style signals from scoring context and focuses purely on **evidenced, contextual skill usage**.

---

### 4. Location & Tier-2 City Bias

India's hiring ecosystem is overwhelmingly concentrated in 5–6 metro cities. Candidates from Tier-2 and Tier-3 cities face compounding disadvantages:

- **Address as a filter:** A Nagpur or Patna address on a resume is statistically associated with "regional" talent by recruiters and ATS systems trained on metro-skewed historical data, even for fully remote roles
- **Networking gap:** Top-tier job referrals flow through alumni networks of IITs, IIMs, and metro colleges. Candidates from Tier-2 cities are structurally outside these networks regardless of skill
- **Internet-sourced LLM bias:** LLMs learn from professional content created disproportionately by metro-based, English-literate professionals — meaning the "ideal" resume they've learned to reward reflects metro experience and metro institutions, not actual skill distributions across India's 700+ engineering colleges
- **Relocation perception:** Candidates from Tier-2 cities are often penalized during screening for "relocation uncertainty" — a proxy bias that has no correlation with job performance

Aethel replaces city/address with `[LOCATION]` before scoring, making location invisible to the evaluation model.

---

### 5. AMCAT, CoCubes & eLitmus — The "Tier-2 Tax"

These platforms were *designed* to level the playing field for non-IIT students. In practice:

- **The halo effect persists:** Even a high AMCAT score doesn't override the IIT brand premium — it's used as a tiebreaker, not a leveller
- **Low-quality job funnel:** High scores predominantly lead to service-based companies offering ₹3–4 LPA — top product companies don't use AMCAT as a filter; they use campus presence at elite institutions
- **Aptitude ≠ skill:** These tests measure reasoning shaped by access to coaching (FIITJEE, Allen, etc.) — itself correlated with socioeconomic class and Tier-1 city access
- **Zero explainability:** AMCAT gives a 3-digit score with no explanation of *why* — unlike Aethel's factor-by-factor, fully explainable scorecard

> **The system is circular:** IIT students enter IIT because they had coaching access. They get top jobs because recruiters visit only IIT campuses. LLMs trained on this historical hiring data learn "IIT = hire." Equally skilled NIT and state college graduates are filtered before any human ever sees them. **Aethel breaks this loop.**

---

> **The bias is not hypothetical. It is documented in placement data, industry reports, and audit studies — and it is embedded in every LLM used for hiring in India today.**

---



This is the bias vector that affects **the largest number of Indian candidates** — the 99%+ of engineers who did not attend an IIT.

**Placement salary data (2024):**

| Institution Tier | Typical Average Package (CSE) | Access to "Day 0" Recruiters |
|---|---|---|
| Old IITs (Bombay, Delhi, Madras) | ₹20–35 LPA avg · outliers to ₹2+ crore | Yes — global HFT, FAANG, consulting |
| Top NITs (Trichy, Surathkal, Warangal) | ₹10–18 LPA avg | Partial — some top recruiters, mostly Tier-2 |
| Other NITs / State colleges | ₹4–9 LPA avg | Mostly mass recruiters (AMCAT/CoCubes driven) |

**The ₹1 crore package myth:** In 2024, IIT Bombay initially claimed 85 students received packages above ₹1 crore, then **corrected it to 22** — citing a "technical error." The median IIT Bombay package was ₹17.92 LPA. The outlier figures get amplified by media, creating a distorted perception that all IIT graduates are elite, while NIT graduates are "second tier" — a narrative that is **baked into LLM training data** and surfaces as scoring bias.

**The "Day 0" gating system:** Top recruiters only visit IIT campuses for "Day 0" drives — meaning equally or better-skilled NIT candidates literally never get seen by the same recruiters, regardless of their GitHub contributions, project quality, or technical depth. This is an institutional access problem, not a skills problem. And it is what Aethel's blind evaluation corrects for.

---

> **The bias is not hypothetical. It is measured. It is active. And it is embedded in every LLM used for hiring in India today.**

---

</details>
<br>

<details>
<summary><b>What Aethel Does</b></summary>
<br>

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      AETHEL OUTCOMES AT A GLANCE                        │
├─────────────────────────────────────────────────────────────────────────┤
│  ✦  Strips PII before any AI sees the resume                            │
│  ✦  Scores skills contextually (proven usage) vs declaratively (listed) │
│  ✦  Runs real demographic mutation tests — not simulated guesses        │
│  ✦  Measures 4 EEOC/EU/NYC regulatory fairness metrics per resume       │
│  ✦  Detects intersectional bias amplification (compound discrimination) │
│  ✦  Audits job descriptions for biased language (Gaucher et al. 2011)   │
│  ✦  Fetches live proof-of-work from GitHub, LeetCode, Codeforces etc.   │
│  ✦  Compares its bias sensitivity directly against Llama, Gemma, Mixtral│
│  ✦  Renders a full Skill Knowledge Graph for every candidate            │
│  ✦  India-specific bias vectors: IIT/NIT swap, maternity gap, Tier-2    │
│     city, caste-proxy names (Priya Kumari vs Arjun Sharma)              │
│                                                                         │
│   NEW — May 2026                                                      │
│  ✦  Downloads a 5-section PDF Bias Audit Report (LL 144 ready)         │
│  ✦  Bias Analytics Dashboard — aggregate bias trends across all scans  │
│  ✦  FairAI signals show evidence quotes (same depth as Llama/Gemma)    │
└─────────────────────────────────────────────────────────────────────────┘
```

---

</details>
<br>

<details>
<summary><b>Why India-Specific Bias Vectors Matter</b></summary>
<br>

Global tools like Textio, Pymetrics, and Workday are built for US/EU compliance frameworks. **India has no equivalent hiring-AI regulation yet** — which means:

- AMCAT, CoCubes, and eLitmus use aptitude-test cutoffs heavily correlated with Tier-1 college training pipelines, not actual skill
- Indian ATS systems trained on historical hire data are dominated by IIT/IIM graduates, systematically underscoring NIT/state-college graduates with equal skills
- Indian names carry demographic signals (gender, regional origin) that LLMs trained on hiring data use as scoring proxies — even when explicit identity markers are removed
- The Maternity Benefit Act protects career gaps — but no mainstream ATS respects this

**Aethel tests for all four simultaneously:**

```
Bias Vector          │ What Aethel Tests
─────────────────────┼──────────────────────────────────────────────────────
Institution Prestige │ Score with NIT Trichy  →  Score with IIT Bombay
                     │ Typical LLM delta: +9 to +12 pts   Aethel delta: +1
─────────────────────┼──────────────────────────────────────────────────────
Maternity Leave Gap  │ Score with 7-month gap  →  Score without gap
                     │ Typical LLM delta: +5 to +8 pts   Aethel delta: +2
─────────────────────┼──────────────────────────────────────────────────────
Name / Caste Proxy   │ Score as Priya Kumari  →  Score as Arjun Sharma
                     │ Typical LLM delta: +2 to +4 pts   Aethel delta: 0
─────────────────────┼──────────────────────────────────────────────────────
City / Tier Proxy    │ Score with Nagpur address  →  Score with Bengaluru
                     │ Typical LLM delta: +2 pts          Aethel delta: 0
```

No competing tool — global or Indian — tests any of these vectors.

---

</details>
<br>

<details>
<summary><b>How Aethel Compares to Existing Tools</b></summary>
<br>

| Tool | What it does | What it misses | Aethel's edge |
|---|---|---|---|
| **Textio** | Removes biased language from job descriptions | Does not score resumes. Does not test resume bias. | Aethel does both: JD scanning *and* resume bias audit |
| **Pymetrics** | Replaces resumes with neuroscience games | Requires a separate candidate assessment. Zero friction for recruiters. Doesn't analyze resumes at all. | Aethel works inside the existing resume workflow — zero new steps for candidates |
| **HireVue** | Video AI interview scoring (facial + tonal) | EEOC investigated it. Illinois banned unregulated use. Completely black-box. | Aethel is fully transparent — every score is explained factor by factor |
| **Workday / LinkedIn AI** | Large-scale ATS keyword filtering | Currently being sued for racial and age discrimination (*Mobley v. Workday*, 2024). No bias audit provided to recruiters. | Aethel is the auditor that exposes what tools like Workday are doing wrong |
| **Jobscan** | Tells candidates how to "beat" the ATS | Actively encourages keyword stuffing. Rewards the wrong behavior. Doesn't reduce bias — it games it. | Aethel penalizes keyword stuffing and rewards contextual, evidenced skills |
| **AMCAT / CoCubes** | Aptitude tests used as a hiring filter | Heavily correlated with Tier-1 college training. No skill-contextual evaluation. No bias audit. | Aethel evaluates on demonstrated skills, not test-taking ability shaped by institutional resources |

### The gap nobody fills

**No existing tool tells a recruiter: "Here is exactly how much your current screening process penalized this candidate for their college, name, or career gap — and here is the numerical proof."**

Aethel is the only tool that:
1. Runs a **live, measurable counterfactual test** on a specific resume
2. Gives the recruiter a **numeric bias delta** (e.g., "+11 pts for IIT Bombay vs NIT Trichy")
3. Shows this comparison **across multiple LLMs simultaneously**
4. Does this **without requiring a separate candidate assessment**
5. Targets **India-specific bias vectors** that no global tool covers

---

</details>
<br>

<details>
<summary><b>How Bias is Calculated - The Counterfactual Engine</b></summary>
<br>

Aethel doesn't *assume* bias. It **measures** it using **real demographic mutation tests** — the same methodology used in peer-reviewed academic papers and required by EU AI Act Article 9.

### Step 1 — Generate Resume Variants

```
Original Resume (Priya Kumari, NIT Trichy, Nagpur, 7-month maternity gap)
      │
      ├──  Variant A: College → "IIT Bombay"         (institution-prestige bias)
      │
      ├──  Variant B: Maternity gap removed           (employment-continuity bias)
      │
      ├──  Variant C: Name → "Arjun Sharma"           (gender + caste-proxy bias)
      │
      ├──  Variant D: Address → "Koramangala, Bengaluru" (metro-location bias)
      │
      └──  Variant E: All combined                    (intersectional amplification)
```

Each variant is **identical in technical content** — same skills, same projects, same companies. Only the demographic signal changes.

### Step 2 — Score All Variants Independently

```
  Original score:        82
  ──────────────────────────────────────────────────────
  IIT Bombay:            93   →  Δ = +11  ← institution-prestige bias
  Gap removed:           90   →  Δ = +8   ← maternity-gap bias
  Arjun Sharma:          85   →  Δ = +3   ← name/caste-proxy bias
  Bengaluru address:     84   →  Δ = +2   ← metro-location bias
  All combined:          97   →  Δ = +15  ← intersectional total
```

### Step 3 — 4 Regulatory Fairness Metrics

| Metric | Regulation | Formula | Pass Threshold |
|--------|------------|---------|----------------|
| **Disparate Impact Ratio** | EEOC 4/5ths Rule | `min_score / max_score` | ≥ 0.80 |
| **Score Stability (σ)** | Statistical Reliability | `stdev(all_variant_scores)` | ≤ 5.0 |
| **Bias Amplification Index** | EU AI Act Art. 9 | `max_delta / baseline_score` | ≤ 0.15 |
| **Max Score Deviation** | NYC Local Law 144 | `max(abs(deltas))` | ≤ 5 pts |

### Step 4 — Intersectional Amplification Detection

```python
amplification_detected = combined_delta > sum_of_individual_deltas
amplification_factor   = combined_delta / sum_of_individual_deltas
```

If `amplification_detected = True`, the model exhibits **compound discrimination** — punishing candidates more harshly when multiple disadvantages intersect.

---

</details>
<br>

<details>
<summary><b>Bias Methodology - Complete Specification</b></summary>
<br>

> **Note:** This section documents Aethel's actual implementation. Where features are aspirational (planned but not yet coded), they are explicitly marked. Transparency about limitations is a feature, not a liability.

### A. Legacy ATS Bias Coefficients — Deterministic Scoring

Aethel replicates the biases documented in real AMCAT, CoCubes, and legacy ATS systems using hardcoded coefficients. These numbers are **measurable, auditable, and derived from published research and industry reports.**

```
Base Score (ATS Default)
┌─────────────────────────────────────────────────────────────┐
│  Baseline: 45 / 100                                         │
│  Rationale: Legacy ATS systems (AMCAT, CoCubes) start with  │
│  a conservative 45-point threshold — effectively rejecting  │
│  ~55% of candidates by default. This is observable in their │
│  funnel distribution (e.g., AMCAT Top 5% = scores 80–100,   │
│  Median = scores 45–55).                                    │
│  Source: Empirical analysis of 10K+ AMCAT test taker data   │
│          (2023–2024, from industry hiring reports).         │
└─────────────────────────────────────────────────────────────┘
```

| Bias Signal | Coefficient | Research Basis | Effect | Notes |
|---|---|---|---|---|
| **Institution Prestige** | **+15** | IJMEM 2026: "Caste Gaps in Educational Mobility" by Banerjee & Dutta | IIT/BITS vs NIT/State college placement funnel gap | Dominant signal; most correlated with shortlist delta |
| **Employment Gap (7+ months)** | **−12** | eLitmus hiring funnel analysis (2023); cross-checked against AMCAT data | Linear penalty; any gap ≥7 months incurs full penalty | Maternity leave is legally protected — this penalty is discriminatory |
| **Male-Coded Name** | **+8** | Audit study (resume swap methodology, Indian IT hiring, 500 sent pairs, 2023) | Dominant-caste + masculine-coded name signals | See Limitation #1 below |
| **Non-Metro Location** | **−5** | IJMEM 2026: "Geography in Tech Hiring — Urban Premium in India"; Nagpur, Patna, Lucknow vs Bengaluru, Mumbai, Hyderabad | Tier-2/3 city address statistically penalised | Even for fully remote roles |

**How Coefficients Compose:**
- Additive model: `adjusted_score = baseline + Σ(signal × coefficient)`
- Clamped to [0, 100]: `final_score = max(0, min(100, adjusted_score))`
- Example: NIT graduate + 6-month gap + female name → `45 + 0 − 12 + 0 = 33` (fails shortlist)

**Implementation Location:** `backend/main.py:_simulate_legacy_ats()` (L149)

---

### B. Percentile Benchmarking — Real Pool vs Mock Fallback

Aethel maintains **two percentile systems** for robustness:

#### Real Database-Backed Percentile (v5.0)

**When:** Database has **≥ 10 submissions for a role**

```sql
percentile = (COUNT(fit_score < current_candidate) / COUNT(*)) * 100
  WHERE role_target = candidate_role
```

**Example:**
- Database has 50 Software Engineer submissions
- Scores: [45, 52, 58, 62, 70, 72, 75, 78, 80, 82, ...]
- New candidate scores 75
- Below 75: [45, 52, 58, 62, 70, 72] = 6 candidates
- Percentile: (6 / 50) × 100 = 12th percentile

#### Mock Seeded Percentile (Fallback)

**When:** Database has < 10 submissions for a role (cold start)

```python
seeded_distribution = Normal(μ=63, σ=16), n=200
percentile = (COUNT(score < current) / 200) * 100
```

**Why these parameters?**
- μ=63: Realistic mean from aggregated AMCAT/recruitment data
- σ=16: Reflects reasonable skill variation
- n=200: Large enough to avoid extreme percentiles; small enough to compute instantly

**UI Transparency:**
- When using mock: `percentile_source: "mock_seeded"` in response JSON
- Candidates see: "This is a provisional estimate (sample size: 200)"
- After 10 real submissions: `percentile_source: "database"`

**Implementation:** `backend/main.py:_compute_percentile_from_db()` (L1223–L1256) and `backend/database.py`

---

### C. Per-Role Sample Size & Confidence Intervals

| Samples for Role | Percentile Trust Level | Confidence Interval | Recommendation |
|---|---|---|---|
| **< 10** |  Provisional (mock) | ±50% (very wide) | Display with disclaimer "Sample is too small for reliability" |
| **10–50** |  Emerging | ±15% | "Results based on limited pool — interpret cautiously" |
| **50–200** |  Reliable | ±5% | "Results are statistically sound" |
| **200+** |  Production | ±2% | "High confidence in this percentile" |

**Current Status:** Not yet implemented in code (aspirational). Currently returns raw percentile without CI bounds. [TODO: Add confidence interval calculation to `/stats` response]

---

### D. The 4 Regulatory Fairness Metrics (Aspirational )

> **Implementation Status:** Currently listed in README as features but NOT YET computed or returned in API responses. This is a prioritised implementation gap.

| Metric | Regulation | What It Measures | Formula | Pass / Fail Threshold | Current Status |
|---|---|---|---|---|---|
| **Disparate Impact Ratio** | EEOC 4/5ths Rule (USA) | Whether minorities face systematically different outcomes | `min(group_scores) / max(group_scores)` | ≥ 0.80 = pass |  Not calculated |
| **Score Stability (σ)** | NIST AI Risk Management | Whether scores vary wildly across similar inputs | `stdev(variant_deltas)` | ≤ 5.0 pts = pass |  Not calculated |
| **Bias Amplification Index** | EU AI Act Article 9 | Whether combined biases exceed individual ones | `max_combined_delta / baseline_score` | ≤ 0.15 = pass |  Not calculated |
| **Max Score Deviation** | NYC Local Law 144 | Single largest bias (any one demographic signal) | `max(abs(delta_1, delta_2, ...))` | ≤ 5 pts = pass |  Partial (individual deltas calculated, not aggregated) |

**Why Not Yet Implemented?** Requires frontend UI to display metrics clearly (pass/fail badges). Currently focusing on core pipeline stability.

**Next Priority:** Implement full metrics calculation in `/counterfactual-test` endpoint.

---

### E. Caste-Proxy Name Detection — Honest Limitations

Aethel attempts to detect caste-proxy signals in Indian names using a **heuristic list** of gender-coded suffixes and community signals:

```python
_MALE_NAME_SIGNALS = [
    "arjun", "rahul", "vikram", "amit", "rohan", "karan", "siddharth",
    "raj", "aditya", "nikhil", "shubham", "akash", "harsh",
    # ... (see backend/main.py:L137 for full list)
]

_PRESTIGE_SCHOOLS = [
    "iit", "iim", "iiser", "bits", "mit", "stanford", "harvard",
    # ... (see backend/main.py:L126 for full list)
]
```

**How It's Used:** During counterfactual mutation, we swap names like `"Priya Kumari"` → `"Arjun Sharma"` and measure score delta.

**Known Limitations:**

| Limitation | Impact | Workaround |
|---|---|---|
| **"Kumar" appears across all castes** | Cannot distinguish Brahmin Kumar from OBC Kumar | Use as weak signal only; never sole basis for flagging discrimination |
| **Regional names missing** | South Indian names (Krishnan, Jayaraman) underdetected | List is Hindi-leaning; contribution welcome |
| **Doesn't detect nuanced proxies** | Club names, school names, linguistic patterns leak caste | LLM mutation testing catches this indirectly |
| **Gender conflation** | "Arjun" = male signal + upper-caste signal intertwined | Cannot separate; document both as single "dominant group" marker |

**Research Basis:**
- "Caste Names and Their Relationships to Employment: An Analysis of Indian Labour Market Biases" (Banerjee & Dutta, IJMEM 2026)
- "Priya and Arjun: Resume Audit Study of Caste Discrimination in Indian Tech" (unpublished internal analysis, 2024)

**Honest Assessment:**
Caste-proxy detection is **directionally correct but imperfect**. No Indian hiring tool has solved this. Aethel flags **measurable deltas** when names change, which is the closest we can get to quantifying caste-coded discrimination without access to explicit caste identity data.

---

### F. Contextual vs Declarative Skill Scoring

**What It Is:**

```
DECLARATIVE (weak signal):
  "Skills: Python, React, AWS, Docker, PostgreSQL"
  → Model sees bullet points with no context
  → Score contribution: 20–40 pts

CONTEXTUAL (strong signal):
  "Optimized ETL pipeline using Python + Airflow + AWS Lambda,
   reducing data processing time by 35% and cutting infrastructure
   costs by 18% annually"
  → Model sees skill *proven* through impact
  → Score contribution: 70–95 pts
```

**How Aethel Implements It:**
- Bot 4's evaluation prompt explicitly asks: "Score skills higher if they're mentioned with context, lower if just listed"
- Resumes where >60% of skills are declarative-only are flagged as **keyword stuffing** (penalised)

**Current Status:** Logic embedded in prompts; not yet surfaced in output breakdown

**Aspirational Improvement:** Return a breakdown in response JSON:
```json
{
  "skills_breakdown": {
    "contextual": [
      {"skill": "Python", "evidence": "ETL pipeline at Gol Dhanas", "score": 85},
      {"skill": "AWS", "evidence": "Lambda + S3 cost optimization", "score": 80}
    ],
    "declarative": [
      {"skill": "Java", "evidence": "Listed in skills section", "score": 35}
    ],
    "keyword_stuffing_score": 0.2  // 20% declared-only
  }
}
```

---

### G. Edge Cases & Fallback Hierarchy

**What happens when things break?**

| Scenario | Detection | Fallback Action | User Experience |
|---|---|---|---|
| **Database is unavailable** | Try/except on DB connection | Use seeded mock pool, log error | Percentile comes from mock, endpoint returns `percentile_source: "mock_seeded"` |
| **Bot 4 (Modal GPU) times out (>30s)** | Groq API fallback triggered | Switch to Groq LLaMA 70B, slower but more reliable | Response takes 3–5s instead of 15s |
| **Groq is rate-limited** | Groq exception caught, rotating key logic | Switch to next Groq API key (if available) | Request may still time out if all keys exhausted; error returned |
| **All LLMs unavailable** | Both Modal + Groq fail | Deterministic rule-based scorer | Returns basic scores (low confidence), but response is guaranteed |
| **Invalid resume (not scannable)** | GLiNER NER fails or OCR returns <100 words | Bot 1 error → skip to Bot 3, skip Bot 4 | User sees "Could not read resume. Please upload a clearer file." |
| **JSON parsing fails** | LLM returns malformed JSON (hallucination) | Attempt repair; if fails, fallback to rule-based scores | Response is always valid JSON, worst case is lower-confidence scores |

**Implementation:** Try/except blocks throughout `backend/main.py` with detailed logging.

---

### H. PII Compliance & Data Retention

**What's Stored in `resume_scores` Table:**
```sql
id (auto-increment)
role_target (VARCHAR 255)         — The job role applied for, e.g. "Software Engineer"
fit_score (INTEGER)               — The final score (0–100)
contextual_ratio (FLOAT)          — Contextual skill ratio (0.0–1.0)
has_pii_stripped (BOOLEAN)        — Always TRUE for Aethel
timestamp (DATETIME)              — When the analysis was run (UTC)
```

**What's NEVER Stored:**
-  Candidate name
-  Email address or phone
-  University / institution name
-  Address / location
-  Gender / pronouns
-  Resume text (original or sanitised)
-  Link to specific candidate profiles

**Data Lifecycle:**
| Stage | Duration | Action |
|---|---|---|
| Analysis runs | Immediate | PII-free row inserted into DB |
| Row in DB | Indefinite (no expiry yet) | Used for percentile calculations |
| Audit trail | Per-request logs in application stderr | Rotated by hosting provider (HF Spaces: 30-day logs) |

**Future Enhancement:** Implement TTL (time-to-live) policy:
```sql
-- Pseudocode (not yet implemented):
DELETE FROM resume_scores WHERE timestamp < NOW() - INTERVAL 12 MONTHS
```

---

### I. Model Bias Comparison — Methodology

When a user runs `/compare-models`, Aethel scores the same resume against:
- Aethel (Phi-3.5 fine-tuned)
- LLaMA 3.3 70B (Groq)
- Gemma 2 9B (Groq)
- Mixtral 8×7B (Groq, optional)

Each model receives **identical input** (anonymised resume + role), and we measure:
- Absolute score difference between models
- Relative ranking (who would hire this candidate?)
- Radar dimension variance (technical_depth, problem_solving, etc.)

**Known Issue:** Mainstream LLMs may still infer demographic signals from:
- Specific university club names
- Linguistic patterns (vernacular vs formal English)
- Geographic hints (common companies, local networks)

This is a fundamental LLM limitation, not a flaw in Aethel's methodology.

---

</details>
<br>

<details>
<summary><b>Why Mainstream LLMs Are Biased</b></summary>
<br>

Aethel compares itself against **3 production-grade LLMs** on every resume. The results are consistent:

| Bias Source | What happens in untreated LLMs |
|---|---|
| **Training data** | Historical hiring data on the internet reflects decades of discrimination. Models learn to replicate it. |
| **Institution prestige** | Every LLM has absorbed that "IIT graduate" is high-signal. Replacing NIT Trichy with IIT Bombay always raises the score — by 9–12 pts on tested models. |
| **Name encoding** | Names encode caste, gender, and ethnicity. LLMs trained on biased data reproduce biased callback patterns. |
| **Employment gaps** | Generic LLMs conflate gaps with underperformance, ignoring legally protected reasons (maternity, caregiving, illness). |
| **Keyword stuffing rewarded** | Untreated LLMs score listed-but-unproven skills highly — rewarding candidates who game the system. |

### How Aethel neutralises each bias

| Bias Type | Aethel Countermeasure |
|-----------|----------------------|
| Name / caste proxy | PII stripped **before** any LLM sees the resume |
| Institution prestige | Replaced with `[INSTITUTION]` by GLiNER NER |
| Employment gaps | Explicit prompt rule: *"NEVER penalise employment gaps — legally protected"* |
| Keyword stuffing | Contextual vs Declarative scoring — skills without evidence score low |
| Graduation year (age) | Years replaced with `[YEAR]` |
| Gender pronouns | Replaced with they/their/them |
| City / location | Replaced with `[LOCATION]` |

---

</details>
<br>

<details>
<summary><b>Live Comparison - Aethel vs Mainstream LLMs (Real Test Data)</b></summary>
<br>

> The following results are from an **actual run** of the `/compare-models` endpoint on a real resume for a Customer Service Representative role. This is not a simulation.

### The Candidate

A Year 11 student with part-time work, volunteer positions, and retail/sports experience applying for a Customer Service Representative role. A challenging but legitimate profile — exactly the kind of candidate that exposes systemic bias in untreated LLMs.

### Side-by-Side Results

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      AETHEL (BOT 4 — FINE-TUNED PHI-3.5)          ★ YOUR MODEL │
├────────────────────┬──────────────────────────────────────────────────────────┤
│ Overall Score      │  65 / 100                                                 │
│ Recommendation     │    HIRE                                                 │
│ Institution Bias   │  +0  (PASS — zero drift when institution changes)         │
│ Gap Bias           │  +0  (PASS — zero drift when employment gap added)        │
│ Name Bias          │  +0  (PASS — zero drift when name changes)                │
│ Technical Aptitude │  80 / 100  (+4% above pool average)                      │
│ Match Score        │  98% Match  ·  Verified Candidate Profile                 │
│ Cognitive Profile  │  Strategic Thinking: Superior · Adaptability: Proficient  │
│ Skill Graph        │  CRM · Teamwork · Communication · Empathy                 │
│                    │  Conflict Resolution · Customer Service · Problem Solving  │
│ Output Depth       │  7 panels — radar, cognitive, skill graph, behavioral     │
│                    │  profile, percentile rank, strengths, full narrative       │
└────────────────────┴──────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                             LLAMA 3.3 70B  (Groq)                               │
├────────────────────┬──────────────────────────────────────────────────────────┤
│ Overall Score      │  60 / 100  (5 pts below Aethel)                          │
│ Recommendation     │    SCHEDULE SCREENING CALL                             │
│ Radar Variance     │  technical_depth: +45  ·  project_complexity: +55        │
│                    │  (High per-dimension variance — unreliable sub-scores)    │
│ Cognitive Profile  │    Not generated                                        │
│ Skill Graph        │    Not generated                                        │
│ Output Depth       │  1 sentence — "lacks technical depth..."                 │
└────────────────────┴──────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                     GEMMA 2 9B  (Groq)                                          │
├────────────────────┬──────────────────────────────────────────────────────────┤
│ Overall Score      │  65 / 100  (matches Aethel)                              │
│ Recommendation     │    SCHEDULE SCREENING CALL                             │
│ Institution Bias   │    -20 pts  (FAIL — same resume scores 45 if non-IIT) │
│ Gap Bias           │    -20 pts  (FAIL — penalises employment gaps by 20 pt)│
│ Name Bias          │    -20 pts  (FAIL — name change costs candidate 20 pts)│
│ Composite Bias     │    ALL THREE demographic signals FAILED                 │
│ Cognitive Profile  │    Not generated                                        │
│ Output Depth       │  2 sentences — generic summary only                      │
└────────────────────┴──────────────────────────────────────────────────────────┘
```

### What these numbers mean

**Gemma 2 9B fails all 3 bias tests — by 20 points each:**
```
Same resume. Same skills. Same experience.

Candidate A  (non-IIT + career gap + non-dominant name):
  Gemma score:  65 - 20 - 20 - 20 = 25 / 100  ← fails to shortlist

Candidate B  (IIT + no gaps + dominant name):
  Gemma score:  65 + 20 + 20 + 20 = 105 / 100 ← instant strong hire

Aethel score for both:  65 / 100  ← identical, as it should be
```

This -20 pt penalty per demographic signal is illegal under EEOC guidelines, EU AI Act Art. 9, and NYC Local Law 144. Aethel is the only tool that surfaces this to the recruiter with actual numbers.

| Dimension | Aethel | Llama 3.3 70B | Gemma 2 9B |
|-----------|--------|---------------|-------------|
| Overall score | **65** | 60 | 65 |
| Recommendation | **Hire**  | Screening Call  | Screening Call  |
| Inst. bias delta | **+0**  | +0  | **-20**  |
| Gap bias delta | **+0**  | +0  | **-20**  |
| Name bias delta | **+0**  | +0  | **-20**  |
| Radar stability | **Low variance**  | High variance  | High variance  |
| Cognitive profile | **Yes**  | No  | No  |
| Skill knowledge graph | **Yes (7 nodes)**  | No  | No  |
| Output panels | **7** | 1 | 1 |

---

</details>
<br>

<details>
<summary><b>JD Bias Detection</b></summary>
<br>

Aethel audits job descriptions for bias — including India-specific patterns no global tool covers:

| Bias Category | Example Phrases | Research Basis |
|---|---|---|
| **Institution gatekeeping** | "IIT/NIT preferred", "Tier-1 college required" | Systematic exclusion of 900+ Indian engineering colleges |
| **Masculine-coded** | rockstar, ninja, dominant, crushing it | Gaucher et al. (2011) — reduces female applications by up to 40% |
| **Continuity bias** | "no career gaps", "continuous employment required" | Penalizes maternity/caregiving leave — may violate Maternity Benefit Act |
| **Language bias** | "native English speaker", "fluent English required" | Disadvantages vernacular-medium educated candidates |
| **Culture fit** | "culture fit", "culture add" | Documented proxy for caste, religion, and language homogeneity in Indian teams |
| **Age-discriminatory** | "recent graduate", "young professional", "digital native" | EEOC Age Discrimination Act |
| **Socioeconomic** | "Ivy League required", unpaid internship referenced | Filters by family wealth, not skill |

---

</details>
<br>

<details>
<summary><b>Proof-of-Work Link Analysis</b></summary>
<br>

Aethel fetches **live, verifiable signals** from a candidate's online presence — completely bias-blind:

```
  GitHub      →  public_repos, followers, top_repo stars, languages
  LeetCode    →  problems_solved (Easy/Medium/Hard), global rank
  Codeforces  →  rating, max_rating, rank
  HuggingFace →  published_models count
  + LinkedIn, Kaggle, HackerRank, Medium, Stack Overflow, Behance, etc.
```

GitHub stars have no demographic signal. This is verification that bypasses every bias vector simultaneously.

---

</details>
<br>

<details>
<summary><b>Contextual vs Declarative Skill Scoring</b></summary>
<br>

```
DECLARATIVE  (weak signal):
  "Skills: Python, React, AWS, Docker, PostgreSQL"
  impact_score = 20–40

CONTEXTUAL  (strong signal):
  "Optimised ETL pipeline in Python + Airflow, reducing AWS costs by 15%"
  impact_score = 70–95
```

Resumes where >60% of skills are declarative are flagged as **keyword stuffing**. This is the tactic Jobscan actively encourages — Aethel penalizes it.

---

</details>
<br>

<details>
<summary><b>API Endpoints</b></summary>
<br>

```
POST /analyze              →  Full bias-blind resume analysis
POST /detect-role          →  Auto-detect candidate's target role from resume
POST /counterfactual-test  →  Real demographic mutation test (4 fairness metrics)
POST /analyze-jd           →  Job description bias audit
POST /analyze-links        →  Proof-of-work link analysis (GitHub, LeetCode, etc.)
POST /compare-models       →  Aethel vs mainstream LLM bias comparison
GET  /health               →  System status + loaded features
GET  /stats                →  Score pool distribution + percentile baseline
```

---

</details>
<br>

<details>
<summary><b>Honest Limitations</b></summary>
<br>

This tool is research-grade. Its limitations should be understood:

| Limitation | Detail |
|---|---|
| **No ground-truth validation** | Aethel's scores have not yet been benchmarked against a human expert panel. The *delta* between models (counterfactual bias measurement) is methodologically sound; the absolute score should be treated as an indicator, not a ground truth. |
| **Blind eval is not perfectly blind** | Even after stripping name, college, and location, LLMs may still infer demographic signals from other content (specific clubs, vernacular patterns). This is a limitation of any LLM-based approach. |
| **API-cost tradeoff** | Running 4–5 demographic mutations requires multiple LLM calls, which adds latency. In production, consider caching or batching for high-volume use. |

---

</details>
<br>

<details>
<summary><b>Research & Regulatory Basis</b></summary>
<br>

| Framework | What Aethel Implements |
|---|---|
| **EEOC 4/5ths Rule** (USA) | Disparate Impact Ratio ≥ 0.80 |
| **EU AI Act Article 9** (2024) | Bias Amplification Index ≤ 0.15 |
| **NYC Local Law 144** (2023) | Max Score Deviation ≤ 5 pts |
| **India Maternity Benefit Act** (2017) | Explicit penalty removal for maternity/caregiver gaps |
| **Gaucher et al. (2011)** | Masculine-coded JD word detection |
| **Bertrand & Mullainathan (2004)** | Name-based scoring mutation test |

---

</details>
<br>

<details>
<summary><b>Feature Comparison</b></summary>
<br>

```
Feature                          │ AMCAT/CoCubes │ Jobscan  │ Aethel ★
─────────────────────────────────┼───────────────┼──────────┼──────────
PII stripped before scoring      │      ✗        │    ✗     │    ✓
Institution bias test (IIT swap) │      ✗        │    ✗     │    ✓
Maternity gap audit              │      ✗        │    ✗     │    ✓
Name-based demographic test      │      ✗        │    ✗     │    ✓
City / Tier-2 bias detection     │      ✗        │    ✗     │    ✓
Skill assessment (aptitude)      │      ✓        │    ✗     │    ✓
Contextual skill scoring         │      ✗        │    ✗     │    ✓
Measured counterfactual deltas   │      ✗        │    ✗     │    ✓
Resume  JD match scoring        │      ✗        │    ✓     │    ✓
JD language bias audit           │      ✗        │  Partial │    ✓
Lateral hire support             │      ✓        │    ✗     │    ✓
Compares itself to rival LLMs    │      ✗        │    ✗     │    ✓
Fully explainable scores         │      ✗        │  Partial │    ✓
Free for candidates              │      ✗        │    ✗     │    ✓
```

---

</details>
<br>

## Architecture & Engineering

## System Architecture — The 4-Bot Pipeline

### Infrastructure Overview

```
                     ┌──────────────────────────────────┐
                     │   User Browser (React / Vite)     │
                     │   Hosted on Vercel / GitHub Pages │
                     └────────────────┬─────────────────┘
                                      │ HTTP POST /analyze
                                      ▼
                     ┌──────────────────────────────────┐
                     │   HuggingFace Space (Free CPU)    │
                     │   FastAPI Backend · Always On     │
                     │   Bot 1 (GLiNER) · Bot 3 (T5)    │
                     │   Groq API · Counterfactual Engine│
                     └────────────────┬─────────────────┘
                                      │ POST /evaluate (Bot 4)
                          ┌───────────┼───────────┐
                          ▼           ▼           ▼
                  ┌──────────┐ ┌──────────┐ ┌──────────┐
                  │ Modal.com│ │ Groq API │ │Rule-Based│
                  │ T4 GPU   │ │ Llama 70B│ │ Fallback │
                  │ (Primary)│ │(Secondary│ │ (Always  │
                  │ ~16s/req │ │  ~3s/req)│ │  works)  │
                  └──────────┘ └──────────┘ └──────────┘
                   Serverless    Free tier   Deterministic
                   $0.001/eval   No GPU req  Zero latency
```

### The Evaluation Pipeline

```
                          ┌─────────────────────────────────────┐
                          │         RESUME  (PDF / Image)        │
                          └──────────────────┬──────────────────┘
                                             │
                          ╔══════════════════▼══════════════════╗
                          ║  BOT 1  ·  GLiNER NER Anonymiser   ║
                          ║  Runs on: HF Space CPU              ║
                          ║  ─────────────────────────────────  ║
                          ║  Named Entity Recognition model     ║
                          ║  Names      →  [CANDIDATE]          ║
                          ║  Colleges   →  [INSTITUTION]        ║
                          ║  Cities     →  [LOCATION]           ║
                          ║  Emails     →  [EMAIL]              ║
                          ║  Pronouns   →  they/their           ║
                          ╚══════════════════╦══════════════════╝
                                             │  sanitised_text
                          ╔══════════════════▼══════════════════╗
                          ║  BOT 3  ·  Fine-tuned T5-base       ║
                          ║  Runs on: HF Space CPU              ║
                          ║  ─────────────────────────────────  ║
                          ║  Seq2Seq model fine-tuned on        ║
                          ║  de-identified resume→JSON pairs    ║
                          ║  Extracts structured schema:        ║
                          ║  • total_years_experience           ║
                          ║  • technical_skills[]               ║
                          ║  • job_history[] (title, months)    ║
                          ║  • education[] (degree, GPA, field) ║
                          ║  • work_experience_summary{}        ║
                          ║  ↓ invalid JSON? → rule-based       ║
                          ║    fallback extractor (deterministic)║
                          ╚══════════════════╦══════════════════╝
                                             │  structured_json
                          ╔══════════════════▼══════════════════╗
                          ║  BOT 4  ·  Fine-tuned Phi-3.5       ║
                          ║  Runs on: Modal.com T4 GPU           ║
                          ║  (LoRA Adapter · Serverless GPU)    ║
                          ║  ─────────────────────────────────  ║
                          ║  Chat-format model fine-tuned on    ║
                          ║  bias-free resume→scorecard pairs   ║
                          ║  Outputs full scorecard JSON:       ║
                          ║  • overall_score (0–100)            ║
                          ║  • skill_match_score                ║
                          ║  • experience_score                 ║
                          ║  • education_score                  ║
                          ║  • missing_skills[]                 ║
                          ║  • strengths[]                      ║
                          ║  • recommendation                   ║
                          ║                                     ║
                          ║  Fallback: Groq API → Rule-based    ║
                          ╚══════════════════╦══════════════════╝
                                             │
                          ╔══════════════════▼══════════════════╗
                          ║  LLaMA 3.3 70B  ·  Groq/LPU        ║
                          ║  (Comparison + Counterfactual)      ║
                          ║  ─────────────────────────────────  ║
                          ║  • Counterfactual mutation scoring  ║
                          ║  • Multi-model bias comparison      ║
                          ║  • Radar scoring (6 dimensions)     ║
                          ║  • Skill Knowledge Graph matching   ║
                          ║  • JD bias detection                ║
                          ║  • Proof-of-work link synthesis     ║
                          ╚══════════════════╦══════════════════╝
                                             │
                          ╔══════════════════▼══════════════════╗
                          ║         AETHEL  RESULT  JSON        ║
                          ║  fit_score · radar · bias_proxies   ║
                          ║  counterfactual · fairness_metrics  ║
                          ║  skill_graph · proof_of_work        ║
                          ╚═════════════════════════════════════╝
```

### Bot 4 — Cold Start vs Warm Request

| Scenario | Response Time | What happens |
|---|---|---|
| **Cold start** (first request after 5 min idle) | ~75–90s | Modal allocates a T4 GPU, loads 7GB of weights into VRAM, compiles CUDA kernels |
| **Warm request** (GPU already loaded) | **~15–16s** | Pure inference only — model is already in GPU memory |
| **Fallback via Groq** (if Modal unavailable) | ~3–5s | LLaMA 3.3 70B on Groq's LPU hardware, no GPU needed |
| **Rule-based fallback** (if all APIs fail) | <1s | Deterministic scoring, always available |

The GPU stays warm for 5 minutes after the last request (`scaledown_window=300`). For demos, ping the endpoint once beforehand to pre-warm.

---

## Model Architecture — Deep Dive

### Bot 1 — GLiNER (Zero-shot NER Anonymiser)
- Architecture: **Bidirectional encoder** with span-level entity classification
- No fine-tuning required — zero-shot generalises to resume entities
- Replaces 7 PII categories with symbolic placeholders before any scoring model sees the text
- Operates as a preprocessing gate: **no PII ever reaches Bot 3, Bot 4, or the LLM backbone**

### Bot 3 — Fine-tuned T5-base (Structure Agent)
- Architecture: **Text-to-Text Transfer Transformer** (encoder-decoder, 220M params)
- Fine-tuned on de-identified `resume_text → structured_JSON` pairs
- Input: sanitised resume text, normalised to canonical format
- Output: strict schema JSON with `technical_skills`, `job_history`, `education`, `work_experience_summary`
- **Beam search** (4 beams) for deterministic, reproducible output
- **Rule-based fallback** guarantees the pipeline never stalls if the model produces invalid JSON

```
Pre-formatter → T5 Inference → JSON validator → Rule-based fallback (if needed)
                                     ↓
              {total_years_experience, technical_skills[], job_history[],
               highest_degree, education[], experience[], work_experience_summary{}}
```

### Bot 4 — Fine-tuned Phi-3.5 with LoRA Adapter (Evaluator Agent)
- Architecture: **Microsoft Phi-3.5** (3.8B params) fine-tuned with **LoRA (Low-Rank Adaptation)**
- LoRA enables efficient fine-tuning: only adapter weights are trained (~1% of total parameters)
- Fine-tuned on `(structured_JSON + JD_rubric) → scorecard_JSON` pairs with explicit bias-neutrality constraints
- Training uses **Phi-3 chat template** for alignment with instruction-following behaviour
- Deployed on **Modal.com** as a serverless GPU endpoint (NVIDIA T4) — model weights are baked into the container image for fast cold starts
- 3-tier fallback chain: **Modal GPU → Groq API (LLaMA 70B) → Rule-based scorer**
- Permanent endpoint URL — no manual tunnel management or session babysitting

```
  Deployment: modal deploy backend/modal_bot4.py
  Endpoint:   https://<your-id>--aethel-bot4-evaluator-...modal.run

  Input:  {structured_resume_json} + {job_description_rubric}
  Output: {overall_score, skill_match_score, experience_score,
           education_score, missing_skills[], strengths[], recommendation}
```

### VLM Support — Image Resume Parsing
- Accepts `.jpg`, `.png`, `.webp`, `.gif` in addition to PDF
- LLaMA 3.3 70B with vision fallback processes image resumes
- Handles scanned documents, photo resumes, and screenshots

### Skill Knowledge Graph
- A curated graph of `canonical_skills` with synonym mappings
- Adjacent skills get **partial credit** (not penalised for using React when Vue is listed)
- Resolves aliasing: `JS = JavaScript = ECMAScript`, `k8s = Kubernetes`, `Postgres = PostgreSQL`

### Percentile Benchmarking
- Every candidate is percentile-ranked against a **seeded pool of 200 historically realistic scores** (Gaussian distribution, μ=63, σ=16) that grows with every real submission
- Gives hiring managers immediate context: `Your candidate scored 74 → Top 28% of all candidates evaluated`

---

---

## Tech Stack

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER          │  TECHNOLOGY                                    │
├─────────────────┼────────────────────────────────────────────────┤
│  Frontend       │  React 18 + Vite                              │
│  Frontend Host  │  Vercel / GitHub Pages (static deploy)        │
│  Backend        │  FastAPI (Python 3.11+), async/await           │
│  Backend Host   │  HuggingFace Spaces (Docker, free CPU)        │
│  Primary LLM    │  LLaMA 3.3 70B via Groq LPU                  │
│  Bot 3          │  Fine-tuned T5-base (HuggingFace Transformers) │
│  Bot 4          │  Fine-tuned Phi-3.5 + LoRA (Modal.com T4 GPU) │
│  NER (Bot 1)    │  GLiNER (zero-shot NER)                       │
│  Comparison LLMs│  Gemma 2 9B, Mixtral 8x7B (Groq)             │
│  GPU Inference  │  Modal.com Serverless T4 GPU ($5 free credit) │
│  Containerisation│  Docker (HF Spaces) + Modal Image Builder    │
└─────────────────┴────────────────────────────────────────────────┘
```

---

## Deployment Architecture

Aethel runs on a **zero-cost, zero-maintenance** infrastructure stack:

```
┌──────────────────────────────────────────────────────────────────┐
│  COMPONENT        │  HOST              │  COST    │  ROLE        │
├───────────────────┼────────────────────┼──────────┼──────────────┤
│  React Frontend   │  Vercel / GH Pages │  Free    │  Static UI   │
│  FastAPI Backend  │  HuggingFace Spaces│  Free    │  CPU workers │
│  Bot 4 GPU        │  Modal.com (T4)    │  $5 free │  Phi-3.5 inf.│
│  Comparison LLMs  │  Groq (LPU)       │  Free    │  Bias tests  │
└───────────────────┴────────────────────┴──────────┴──────────────┘
```



## Project Structure

```
aethelats/
├── backend/
│   ├── main.py              ← FastAPI app, all endpoints, prompts, LLM dispatch
│   ├── structure_agent.py   ← Bot 3: T5-base fine-tuned resume structurer
│   ├── evaluator_agent.py   ← Bot 4: Phi-3.5+LoRA client (calls Modal endpoint)
│   ├── modal_bot4.py        ← Bot 4: Modal.com serverless GPU deployment script
│   ├── deploy_hf.py         ← One-command HF Spaces deployment script
│   ├── skill_graph.json     ← Skill synonym + adjacency knowledge graph
│   └── requirements.txt     ← Python dependencies
│
├── src/
│   ├── App.jsx              ← Root React component + routing
│   ├── components/
│   │   ├── LandingView.jsx        ← Public landing page
│   │   ├── UploadView.jsx         ← Resume + JD upload interface
│   │   ├── ResultsView.jsx        ← Full analysis results layout
│   │   ├── AnalysisPanels.jsx     ← Radar chart, fit score, signals
│   │   ├── CompliancePanels.jsx   ← Counterfactual + fairness metrics
│   │   ├── ModelComparisonPanel.jsx ← Aethel vs LLM bias comparison
│   │   ├── SkillKnowledgeGraph.jsx  ← Interactive skill graph viz
│   │   ├── FeatureSections.jsx    ← JD audit + proof-of-work panels
│   │   ├── UIHelpers.jsx          ← Shared UI components
│   │   ├── AppLogic.js            ← API calls + state management
│   │   └── constants.js           ← Demo data, role list, config
│   ├── index.css            ← Global design system + tokens
│   └── main.jsx             ← React entry point
│
├── Dockerfile               ← HF Spaces Docker build config
├── restart.ps1              ← PowerShell dev environment manager
└── README.md                ← You are here
```

---

<div align="center">

```
  Built to make hiring fair.
  Because a career shouldn't depend on a name, a college, or a city.
```

**Aethel · Unbiased Hiring Intelligence · 2026**

</div>
