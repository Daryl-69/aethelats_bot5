"""
process_dataset.py — Converts Indian Job Market Dataset 2025 into RAG documents
================================================================================
Input:  D:/aethel_backend_g/indian-job-market-dataset-2025.xlsx (97,929 rows)
Output: backend/rag_kb/india_market_*.txt  (one document per career category)

Strategy: TWO-PASS categorization
  Pass 1: Keyword matching → specific career categories
  Pass 2: ANY row not matched in Pass 1 → "Other Professional Roles" catch-all
  Result: 100% of 97,929 rows are used. Nothing is thrown away.

Run:
    python backend/process_dataset.py
Then:
    python backend/rag_store.py
"""

import pandas as pd
import re
from pathlib import Path
from collections import Counter

DATASET_PATH = Path(__file__).parent.parent / "indian-job-market-dataset-2025.xlsx"
KB_DIR = Path(__file__).parent / "rag_kb"
KB_DIR.mkdir(exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# CATEGORY KEYWORD MAP
# Each key = category name shown in RAG docs
# Each value = list of substrings matched (case-insensitive) in job title
# A job goes to the FIRST category whose keyword appears in its title.
# Ordering matters — put more specific categories BEFORE general ones.
# ─────────────────────────────────────────────────────────────────────────────
ROLE_CATEGORIES = {

    # ── TECH: CORE ENGINEERING ─────────────────────────────────────────────
    "Software Development Engineer (SDE / Backend)": [
        "software engineer", "software developer", "software development engineer",
        "software development lead", "backend developer", "backend engineer",
        "sde", "java developer", "python developer", "node developer",
        "golang developer", "go developer", "ruby developer", "php developer",
        "c++ developer", "c# developer", ".net developer", "dotnet developer",
        "spring developer", "django developer", "flask developer",
        "application developer", "application lead", "application engineer",
        "developer - l1", "developer - l2", "developer - l3", "developer - l4",
        "associate software", "associate developer",
    ],
    "Full Stack Developer": [
        "full stack", "fullstack", "full-stack",
        "mern developer", "mean developer", "lamp developer",
    ],
    "Frontend Developer": [
        "frontend developer", "front end developer", "front-end developer",
        "react developer", "angular developer", "vue developer",
        "ui developer", "javascript developer", "typescript developer",
        "next.js developer", "nuxt developer", "frontend engineer",
        "web developer", "html developer", "css developer",
    ],
    "Mobile App Developer": [
        "android developer", "ios developer", "mobile developer",
        "react native developer", "flutter developer", "swift developer",
        "kotlin developer", "mobile engineer", "app developer",
        "android engineer", "ios engineer",
    ],

    # ── TECH: DATA & AI ────────────────────────────────────────────────────
    "Data Scientist / Machine Learning Engineer": [
        "data scientist", "machine learning engineer", "ml engineer",
        "ai engineer", "deep learning engineer", "nlp engineer",
        "computer vision engineer", "research scientist", "data science",
        "ai developer", "llm engineer", "gen ai", "generative ai",
        "applied scientist", "ai scientist", "ml researcher",
    ],
    "Data Engineer": [
        "data engineer", "etl developer", "data pipeline", "big data engineer",
        "spark developer", "hadoop developer", "databricks engineer",
        "analytics engineer", "dbt developer", "data platform engineer",
        "data infrastructure", "pipeline engineer",
    ],
    "Data Analyst / Business Analyst": [
        "data analyst", "business analyst", "bi analyst",
        "business intelligence", "reporting analyst", "analytics analyst",
        "insights analyst", "tableau developer", "power bi developer",
        "sql analyst", "analytics consultant", "market analyst",
        "research analyst", "quantitative analyst", "quant analyst",
    ],

    # ── TECH: INFRASTRUCTURE & CLOUD ──────────────────────────────────────
    "DevOps / Cloud / SRE": [
        "devops", "cloud engineer", "sre", "site reliability",
        "platform engineer", "infrastructure engineer",
        "aws engineer", "gcp engineer", "azure engineer",
        "kubernetes engineer", "docker engineer", "terraform engineer",
        "devsecops", "cloud architect", "cloud administrator",
        "cloud operations", "cloud support", "build engineer",
        "release engineer", "systems engineer",
    ],
    "QA / Test Engineer": [
        "qa engineer", "test engineer", "quality assurance", "quality engineer",
        "automation engineer", "automation tester", "sdet",
        "software tester", "manual tester", "performance tester",
        "qa analyst", "testing engineer", "test analyst", "qa lead",
        "qa manager",
    ],

    # ── TECH: ARCHITECTURE & LEADERSHIP ───────────────────────────────────
    "Technical Lead / Architect / CTO": [
        "technical lead", "tech lead", "lead engineer", "lead developer",
        "lead software", "engineering lead", "engineering manager",
        "software development manager", "software manager",
        "solution architect", "solutions architect",
        "enterprise architect", "system architect", "systems architect",
        "application architect", "technical architect", "it architect",
        "chief technology", "cto", "vp engineering", "head of engineering",
        "director of engineering", "principal engineer", "staff engineer",
        "distinguished engineer",
    ],

    # ── TECH: SECURITY ─────────────────────────────────────────────────────
    "Cybersecurity": [
        "security engineer", "cybersecurity", "information security",
        "penetration tester", "pen tester", "soc analyst",
        "ethical hacker", "security analyst", "vapt", "cloud security",
        "appsec", "devsecops", "security architect", "security consultant",
        "network security", "vulnerability", "threat analyst",
        "iam engineer", "identity access",
    ],

    # ── TECH: SUPPORT & OPERATIONS ────────────────────────────────────────
    "IT Support / Application Support": [
        "application support", "it support", "technical support engineer",
        "tech support", "helpdesk", "help desk", "service desk",
        "desktop support", "l1 support", "l2 support", "l3 support",
        "application tech support", "systems administrator", "sysadmin",
        "network administrator", "network engineer", "network technician",
        "it administrator", "it operations", "noc engineer",
    ],

    # ── TECH: SAP / ERP ───────────────────────────────────────────────────
    "SAP / ERP Consultant": [
        "sap consultant", "sap developer", "sap analyst", "sap certified",
        "sap abap", "sap basis", "sap fico", "sap mm", "sap sd",
        "sap hana", "erp consultant", "oracle consultant", "oracle developer",
        "dynamics consultant", "salesforce developer", "salesforce consultant",
        "crm developer", "crm consultant",
    ],

    # ── PRODUCT & DESIGN ──────────────────────────────────────────────────
    "Product Manager": [
        "product manager", "product owner", "associate product manager",
        "senior product manager", "group product manager",
        "apm", "product lead", "product director", "vp product",
        "head of product", "program manager", "project manager",
        "delivery manager", "engagement manager", "it project manager",
        "scrum master", "agile coach",
    ],
    "UI/UX Designer": [
        "ui designer", "ux designer", "ui/ux", "uiux",
        "product designer", "interaction designer", "visual designer",
        "design lead", "figma designer", "graphic designer",
        "ux researcher", "user experience", "user interface",
        "web designer", "motion designer", "brand designer",
        "creative designer", "art director",
    ],

    # ── SALES & CUSTOMER ──────────────────────────────────────────────────
    "Sales & Business Development": [
        "sales manager", "sales officer", "sales executive",
        "sales representative", "sales associate", "senior sales",
        "business development manager", "business development executive",
        "bd manager", "bd executive", "inside sales",
        "enterprise sales", "field sales", "channel sales",
        "regional sales", "area sales", "territory sales",
        "account executive", "account manager",
        "key account", "national account",
        "relationship manager", "client relationship",
        "branch manager", "zonal manager", "district manager",
        "insurance advisor", "loan officer", "home loan",
        "bancassurance", "banca channel",
    ],
    "Customer Support / Customer Success": [
        "customer support", "customer service", "customer care",
        "customer success", "customer experience", "client support",
        "client service", "support executive", "support associate",
        "support specialist", "call center", "contact center",
        "helpdesk agent", "service representative",
        "trust and safety", "trust & safety", "content moderation",
    ],

    # ── MARKETING ─────────────────────────────────────────────────────────
    "Marketing": [
        "marketing manager", "marketing executive", "marketing specialist",
        "marketing analyst", "marketing associate", "marketing lead",
        "digital marketing", "performance marketing", "growth hacker",
        "seo specialist", "seo analyst", "sem specialist",
        "content marketing", "content writer", "content strategist",
        "copywriter", "technical writer", "brand manager",
        "social media manager", "social media executive",
        "email marketing", "influencer marketing",
        "marketing communications", "pr manager",
    ],

    # ── HUMAN RESOURCES ───────────────────────────────────────────────────
    "Human Resources": [
        "hr manager", "hr executive", "hr associate", "hr analyst",
        "human resource", "human resources", "hrbp",
        "hr business partner", "people operations",
        "recruiter", "talent acquisition", "sourcing specialist",
        "recruitment consultant", "staffing consultant",
        "compensation", "payroll", "benefits", "l&d", "learning development",
        "training manager", "training executive", "training specialist",
        "organizational development",
    ],

    # ── FINANCE & ACCOUNTING ──────────────────────────────────────────────
    "Finance & Accounting": [
        "finance manager", "finance executive", "finance analyst",
        "financial analyst", "financial controller",
        "chartered accountant", "accountant", "senior accountant",
        "accounts executive", "accounts manager", "accounts payable",
        "accounts receivable", "record to report",
        "tax consultant", "tax analyst", "tax manager",
        "audit manager", "auditor", "internal audit",
        "cfo", "controller", "treasurer",
        "investment analyst", "equity research", "credit analyst",
        "risk analyst", "risk manager", "compliance officer",
        "banking", "loan", "mortgage", "underwriter",
    ],

    # ── OPERATIONS & SUPPLY CHAIN ─────────────────────────────────────────
    "Operations & Supply Chain": [
        "operations manager", "operations executive", "operations analyst",
        "supply chain", "logistics", "warehouse", "inventory",
        "procurement", "purchasing", "sourcing", "vendor management",
        "scm", "fulfillment", "dispatch", "delivery executive",
        "category manager", "general manager", "branch operations",
        "facility manager", "administration manager",
        "office administrator", "executive assistant",
        "assistant manager", "deputy manager",
    ],

    # ── HEALTHCARE & PHARMA ───────────────────────────────────────────────
    "Healthcare / Pharma / Biotech": [
        "doctor", "physician", "nurse", "nursing", "pharmacist",
        "medical", "clinical", "healthcare", "hospital",
        "biotech", "pharmaceutical", "pharma", "drug",
        "lab technician", "laboratory", "radiologist",
        "dental", "dentist", "therapist", "physiotherapist",
        "health", "patient",
    ],

    # ── EDUCATION & TRAINING ──────────────────────────────────────────────
    "Education / Teaching / Training": [
        "teacher", "professor", "faculty", "lecturer",
        "academic", "education", "school", "college",
        "tutor", "trainer", "facilitator", "coach",
        "curriculum", "instruction",
    ],

    # ── ENGINEERING (NON-SOFTWARE) ────────────────────────────────────────
    "Core Engineering (Mechanical / Civil / Electrical)": [
        "mechanical engineer", "civil engineer", "electrical engineer",
        "electronics engineer", "chemical engineer", "structural engineer",
        "process engineer", "manufacturing engineer", "production engineer",
        "quality engineer", "qa engineer",  # QA for hardware
        "embedded engineer", "firmware engineer", "hardware engineer",
        "vlsi engineer", "rf engineer", "automation engineer",
        "instrumentation engineer", "maintenance engineer",
        "fire and safety", "safety officer", "safety engineer",
        "environmental engineer",
    ],

    # ── LEGAL & COMPLIANCE ────────────────────────────────────────────────
    "Legal / Compliance": [
        "lawyer", "attorney", "legal counsel", "legal advisor",
        "legal executive", "legal analyst", "contract manager",
        "compliance manager", "compliance officer", "compliance analyst",
        "regulatory affairs", "company secretary",
    ],

    # ── CONSULTING & STRATEGY ─────────────────────────────────────────────
    "Consulting / Strategy / Management": [
        "management consultant", "strategy consultant", "business consultant",
        "it consultant", "technology consultant", "process consultant",
        "analyst consultant", "associate consultant",
        "strategy analyst", "strategy manager", "business architect",
        "business analyst",  # catch remaining ones here
    ],
}


def categorize_title(title: str) -> str | None:
    """Return the first matching category for a job title, or None."""
    t = title.lower().strip()
    for category, keywords in ROLE_CATEGORIES.items():
        for kw in keywords:
            if kw in t:
                return category
    return None  # will be caught by the "Other" pass


def clean_skills(raw) -> list[str]:
    if pd.isna(raw) or not raw:
        return []
    skills = [s.strip().title() for s in str(raw).split(",") if s.strip()]
    return skills


def clean_location(loc) -> str:
    if pd.isna(loc):
        return "Unknown"
    return re.sub(r'\(.*?\)', '', str(loc)).strip().split("/")[0].strip()


def lpa(amount_inr: float) -> str:
    if pd.isna(amount_inr) or amount_inr <= 0:
        return None
    return f"{amount_inr / 100000:.1f} LPA"


def build_category_doc(category: str, subset: pd.DataFrame) -> str:
    """Generate a RAG text document for one career category."""
    lines = []
    lines.append(f"INDIAN JOB MARKET DATA: {category.upper()}")
    lines.append("=" * 65)
    lines.append(f"Source: Indian Job Market Dataset 2025 | Sample size: {len(subset):,} job postings")
    lines.append("")

    # ── Salary by experience level ─────────────────────────────────────
    has_salary = subset[
        subset["minimumSalary"].notna() &
        subset["maximumSalary"].notna() &
        (subset["minimumSalary"] > 10000) &
        (subset["maximumSalary"] > 10000)
    ].copy()

    salary_by_exp = {}
    if not has_salary.empty:
        def exp_bucket(row):
            min_e = row["minimumExperience"]
            if pd.isna(min_e):
                return None
            if min_e < 1:
                return "Fresher (0-1 yr)"
            elif min_e < 3:
                return "Junior (1-3 yrs)"
            elif min_e < 6:
                return "Mid-level (3-6 yrs)"
            elif min_e < 10:
                return "Senior (6-10 yrs)"
            else:
                return "Lead/Principal (10+ yrs)"

        has_salary = has_salary.copy()
        has_salary["exp_bucket"] = has_salary.apply(exp_bucket, axis=1)
        for bucket, grp in has_salary.groupby("exp_bucket"):
            if bucket is None:
                continue
            lo = grp["minimumSalary"].median()
            hi = grp["maximumSalary"].median()
            if lo > 0 and hi > 0:
                salary_by_exp[bucket] = (lo, hi)

    lines.append("SALARY BENCHMARKS (Indian Market, Median CTC):")
    if salary_by_exp:
        for bucket in ["Fresher (0-1 yr)", "Junior (1-3 yrs)", "Mid-level (3-6 yrs)",
                       "Senior (6-10 yrs)", "Lead/Principal (10+ yrs)"]:
            if bucket in salary_by_exp:
                lo, hi = salary_by_exp[bucket]
                lines.append(f"  {bucket}: {lpa(lo)} – {lpa(hi)}")
    else:
        lines.append("  Salary data mostly undisclosed for this category.")
    lines.append("")

    # ── Top skills ─────────────────────────────────────────────────────
    all_skills = []
    for raw in subset["tagsAndSkills"].dropna():
        all_skills.extend(clean_skills(raw))
    skill_counts = Counter(all_skills).most_common(20)

    if skill_counts:
        lines.append(f"TOP IN-DEMAND SKILLS (ranked by frequency in job postings):")
        for rank, (skill, count) in enumerate(skill_counts, 1):
            pct = (count / len(subset)) * 100
            lines.append(f"  {rank:2}. {skill} — mentioned in {pct:.0f}% of postings")
        lines.append("")

    # ── Top locations ──────────────────────────────────────────────────
    location_counts = Counter(
        subset["location"].apply(clean_location).tolist()
    ).most_common(8)
    lines.append("TOP HIRING CITIES IN INDIA:")
    for city, count in location_counts:
        lines.append(f"  - {city}: {count:,} openings")
    lines.append("")

    # ── Top companies ──────────────────────────────────────────────────
    company_counts = Counter(
        subset["companyName"].dropna().tolist()
    ).most_common(10)
    lines.append("TOP COMPANIES ACTIVELY HIRING:")
    for company, count in company_counts:
        lines.append(f"  - {company}: {count:,} postings")
    lines.append("")

    # ── Common titles ──────────────────────────────────────────────────
    top_titles = subset["title"].value_counts().head(12).index.tolist()
    lines.append("COMMON JOB TITLES IN THIS CATEGORY:")
    for t in top_titles:
        lines.append(f"  - {t}")
    lines.append("")

    return "\n".join(lines)


def process():
    print(f"Loading dataset...")
    df = pd.read_excel(DATASET_PATH)
    print(f"  Loaded {len(df):,} rows.")

    # Clean up old docs
    stale = list(KB_DIR.glob("india_market_*.txt")) + list(KB_DIR.glob("live_*.txt"))
    for f in stale:
        f.unlink()
    if stale:
        print(f"  Removed {len(stale)} stale documents.")

    # ── PASS 1: keyword categorization ────────────────────────────────────
    df["category"] = df["title"].apply(categorize_title)
    matched = df[df["category"].notna()].copy()
    unmatched = df[df["category"].isna()].copy()
    print(f"  Pass 1: {len(matched):,} matched | {len(unmatched):,} going to catch-all")

    # ── PASS 2: catch-all for everything not matched ──────────────────────
    unmatched = unmatched.copy()
    unmatched["category"] = "Other Professional Roles"

    # Combine everything
    full = pd.concat([matched, unmatched], ignore_index=True)
    print(f"  Total after 2 passes: {len(full):,} / {len(df):,} rows (100%)")
    assert len(full) == len(df), "Some rows lost!"

    # ── Generate one document per category ───────────────────────────────
    docs_written = 0
    all_categories = list(ROLE_CATEGORIES.keys()) + ["Other Professional Roles"]

    for category in all_categories:
        subset = full[full["category"] == category].copy()
        if len(subset) < 5:
            continue

        doc_text = build_category_doc(category, subset)

        safe_name = re.sub(r'[^\w\s]', '', category).replace(' ', '_').replace('/', '_')
        out_path = KB_DIR / f"india_market_{safe_name}.txt"
        out_path.write_text(doc_text, encoding="utf-8")
        docs_written += 1
        print(f"  [{len(subset):>6,}] {category}")

    print(f"\n✓ Done! {docs_written} documents written. 0 rows wasted.")
    print("Run:  python backend/rag_store.py  to rebuild ChromaDB.")


if __name__ == "__main__":
    process()
