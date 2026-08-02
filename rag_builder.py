"""
rag_builder.py — Builds the Aethel AI Coach knowledge base
============================================================
Run this script to populate the RAG knowledge base with:
  1. Career path guides (role descriptions, skill ladders)
  2. Skill-to-course mappings (free + paid resources)
  3. Indian job market context (Naukri/LinkedIn skill trends)
  4. Salary benchmarks by role + city + experience
  5. Your existing skill_graph.json

Run:
    python backend/rag_builder.py

Outputs → backend/rag_kb/  (a folder of .txt documents)
These are then picked up by rag_store.py to embed + index.
"""

import json
import os
from pathlib import Path

KB_DIR = Path(__file__).parent / "rag_kb"
KB_DIR.mkdir(exist_ok=True)


# ─── 1. Career Path Guides ────────────────────────────────────────────────────

CAREER_PATHS = {
    "Software Development Engineer (SDE)": {
        "levels": ["SDE-1 (0-2 yrs)", "SDE-2 (2-5 yrs)", "SDE-3 / Senior (5-8 yrs)", "Staff Engineer (8+ yrs)"],
        "core_skills": ["Data Structures & Algorithms", "System Design", "Git", "SQL", "REST APIs"],
        "entry_skills": ["Python or Java or C++", "LeetCode (Easy-Medium)", "Basic SQL", "Git basics"],
        "mid_skills": ["System Design (HLD/LLD)", "Distributed Systems", "Docker", "CI/CD"],
        "senior_skills": ["Architecture", "Kubernetes", "Mentoring", "Tech leadership"],
        "top_companies_india": ["Google", "Microsoft", "Amazon", "Flipkart", "PhonePe", "Razorpay", "Swiggy", "Zepto"],
        "salary_india_inr": {
            "SDE-1 fresher": "8-18 LPA",
            "SDE-1 experienced": "12-25 LPA",
            "SDE-2": "20-45 LPA",
            "SDE-3 Senior": "35-80 LPA",
            "Staff Engineer": "60-150 LPA"
        },
        "leetcode_target": {"SDE-1": "100+ problems (50% medium)", "SDE-2": "200+ problems (30% hard)"},
        "typical_interview": "3-5 rounds: DSA (2 rounds), System Design, Behavioral, Hiring Manager"
    },
    "Machine Learning Engineer": {
        "levels": ["MLE-1 (0-2 yrs)", "MLE-2 (2-5 yrs)", "Senior MLE (5-8 yrs)", "Staff MLE (8+ yrs)"],
        "core_skills": ["Python", "Machine Learning fundamentals", "SQL", "Statistics", "Git"],
        "entry_skills": ["Python", "scikit-learn", "Pandas", "NumPy", "Basic ML (regression, classification, clustering)", "Kaggle competitions"],
        "mid_skills": ["PyTorch or TensorFlow", "MLflow", "Docker", "Feature Engineering", "Model deployment (FastAPI + Docker)", "Spark basics"],
        "senior_skills": ["MLOps (Kubeflow/Airflow)", "System Design for ML", "LLMs", "Research reading", "A/B testing"],
        "top_companies_india": ["Google DeepMind", "Microsoft Research", "Amazon Science", "Meesho", "Juspay", "Sarvam AI", "Krutrim"],
        "salary_india_inr": {
            "MLE-1 fresher": "10-20 LPA",
            "MLE-2": "18-40 LPA",
            "Senior MLE": "35-80 LPA"
        },
        "key_projects": [
            "End-to-end ML pipeline: data ingestion → training → deployment → monitoring",
            "Kaggle Top 10% in a structured data competition",
            "Fine-tune an open-source LLM on a custom dataset",
            "Deploy a model as a REST API with FastAPI + Docker"
        ]
    },
    "Data Engineer": {
        "levels": ["Junior DE (0-2 yrs)", "Data Engineer (2-5 yrs)", "Senior DE (5-8 yrs)", "Principal DE (8+ yrs)"],
        "core_skills": ["SQL", "Python", "Apache Spark", "Data Warehousing", "ETL pipelines"],
        "entry_skills": ["SQL (advanced: window functions, CTEs)", "Python", "Basic ETL", "Cloud basics (AWS S3, GCP GCS)"],
        "mid_skills": ["Apache Spark / PySpark", "Apache Airflow", "dbt", "Kafka", "Snowflake or BigQuery", "Docker"],
        "senior_skills": ["Data architecture", "Real-time streaming", "Data governance", "Cost optimization", "Team leadership"],
        "top_companies_india": ["Walmart Global Tech", "Target", "Razorpay", "Dunzo", "Navi Technologies"],
        "salary_india_inr": {
            "Junior DE fresher": "6-15 LPA",
            "Data Engineer": "15-35 LPA",
            "Senior DE": "30-70 LPA"
        }
    },
    "Full Stack Developer": {
        "levels": ["Junior (0-2 yrs)", "Mid-level (2-5 yrs)", "Senior (5+ yrs)"],
        "core_skills": ["HTML/CSS", "JavaScript", "React or Vue", "Node.js or Python backend", "SQL", "Git"],
        "entry_skills": ["HTML, CSS, JavaScript fundamentals", "React basics", "REST API integration", "Basic SQL", "Git"],
        "mid_skills": ["TypeScript", "Next.js", "FastAPI or Express", "PostgreSQL", "Docker", "Redis"],
        "senior_skills": ["System design", "WebSockets", "Microservices", "Performance optimization", "CI/CD"],
        "top_companies_india": ["Startups", "Razorpay", "BrowserStack", "Postman", "Freshworks"],
        "salary_india_inr": {
            "Junior fresher": "5-12 LPA",
            "Mid-level": "12-30 LPA",
            "Senior": "25-60 LPA"
        }
    },
    "DevOps / Platform Engineer": {
        "levels": ["Junior DevOps (0-2 yrs)", "DevOps Engineer (2-5 yrs)", "Senior / SRE (5+ yrs)"],
        "core_skills": ["Linux", "Docker", "Kubernetes", "CI/CD", "Cloud (AWS/GCP/Azure)", "Terraform"],
        "entry_skills": ["Linux command line", "Docker basics", "Git", "Basic scripting (Bash/Python)", "One cloud provider basics"],
        "mid_skills": ["Kubernetes", "Terraform", "GitHub Actions or Jenkins", "Monitoring (Prometheus, Grafana)", "Helm"],
        "senior_skills": ["Multi-cloud architecture", "SRE practices (SLO/SLA/SLI)", "Cost optimization", "Security (IAM, secrets management)"],
        "salary_india_inr": {
            "Junior": "6-14 LPA",
            "Mid": "14-35 LPA",
            "Senior SRE": "30-75 LPA"
        }
    }
}


def build_career_path_docs():
    """Write one document per career path."""
    for role, data in CAREER_PATHS.items():
        lines = [f"CAREER PATH: {role}", "=" * 60, ""]
        lines.append(f"Career levels: {' → '.join(data['levels'])}")
        lines.append("")
        lines.append(f"Core skills required: {', '.join(data['core_skills'])}")
        lines.append(f"Entry-level skills: {', '.join(data['entry_skills'])}")
        lines.append(f"Mid-level skills: {', '.join(data['mid_skills'])}")
        lines.append(f"Senior-level skills: {', '.join(data['senior_skills'])}")
        lines.append("")
        lines.append("Salary benchmarks (India, CTC):")
        for level, sal in data["salary_india_inr"].items():
            lines.append(f"  - {level}: {sal}")
        lines.append("")
        if "top_companies_india" in data:
            lines.append(f"Top companies hiring in India: {', '.join(data['top_companies_india'])}")
        if "key_projects" in data:
            lines.append("Recommended portfolio projects:")
            for p in data["key_projects"]:
                lines.append(f"  - {p}")
        if "typical_interview" in data:
            lines.append(f"Interview process: {data['typical_interview']}")

        filename = role.replace("/", "_").replace(" ", "_").replace("(", "").replace(")", "") + ".txt"
        (KB_DIR / filename).write_text("\n".join(lines), encoding="utf-8")
        print(f"  ✓ Written: {filename}")


# ─── 2. Skill-to-Course Mappings ─────────────────────────────────────────────

SKILL_COURSES = {
    "Python": [
        {"title": "Python for Everybody", "platform": "Coursera", "url": "https://www.coursera.org/specializations/python", "level": "Beginner", "free": True},
        {"title": "Automate the Boring Stuff with Python", "platform": "Book/Online", "url": "https://automatetheboringstuff.com", "level": "Beginner", "free": True},
        {"title": "Python Bootcamp", "platform": "Udemy (Jose Portilla)", "url": "https://www.udemy.com/course/complete-python-bootcamp/", "level": "Beginner-Intermediate", "free": False},
    ],
    "Data Structures & Algorithms": [
        {"title": "Striver's A-Z DSA Sheet", "platform": "takeUforward", "url": "https://takeuforward.org/strivers-a2z-dsa-course/", "level": "All levels", "free": True},
        {"title": "NeetCode 150", "platform": "LeetCode/NeetCode", "url": "https://neetcode.io", "level": "Intermediate", "free": True},
        {"title": "Data Structures and Algorithms Specialization", "platform": "Coursera (UCSD)", "url": "https://www.coursera.org/specializations/data-structures-algorithms", "level": "Intermediate", "free": False},
    ],
    "System Design": [
        {"title": "System Design Primer", "platform": "GitHub", "url": "https://github.com/donnemartin/system-design-primer", "level": "Intermediate-Senior", "free": True},
        {"title": "Grokking the System Design Interview", "platform": "DesignGurus", "url": "https://www.designgurus.io/course/grokking-the-system-design-interview", "level": "Intermediate", "free": False},
        {"title": "ByteByteGo", "platform": "bytebytego.com", "url": "https://bytebytego.com", "level": "All", "free": False},
    ],
    "Machine Learning": [
        {"title": "Machine Learning Specialization", "platform": "Coursera (Andrew Ng)", "url": "https://www.coursera.org/specializations/machine-learning-introduction", "level": "Beginner", "free": False},
        {"title": "fast.ai Practical Deep Learning", "platform": "fast.ai", "url": "https://course.fast.ai", "level": "Intermediate", "free": True},
        {"title": "Kaggle ML Courses", "platform": "Kaggle", "url": "https://www.kaggle.com/learn", "level": "Beginner-Intermediate", "free": True},
    ],
    "PyTorch": [
        {"title": "Deep Learning with PyTorch: Zero to Mastery", "platform": "ZeroToMastery", "url": "https://www.learnpytorch.io", "level": "Beginner-Intermediate", "free": True},
        {"title": "PyTorch Official Tutorials", "platform": "pytorch.org", "url": "https://pytorch.org/tutorials/", "level": "All", "free": True},
    ],
    "SQL": [
        {"title": "SQLZoo", "platform": "sqlzoo.net", "url": "https://sqlzoo.net", "level": "Beginner", "free": True},
        {"title": "Mode SQL Tutorial", "platform": "Mode Analytics", "url": "https://mode.com/sql-tutorial/", "level": "Beginner-Intermediate", "free": True},
        {"title": "Advanced SQL for Data Scientists", "platform": "Coursera", "url": "https://www.coursera.org/learn/advanced-sql", "level": "Advanced", "free": False},
    ],
    "Docker": [
        {"title": "Docker Official Get Started", "platform": "docs.docker.com", "url": "https://docs.docker.com/get-started/", "level": "Beginner", "free": True},
        {"title": "Docker & Kubernetes: The Practical Guide", "platform": "Udemy", "url": "https://www.udemy.com/course/docker-kubernetes-the-practical-guide/", "level": "Intermediate", "free": False},
    ],
    "Kubernetes": [
        {"title": "Kubernetes Official Tutorial", "platform": "kubernetes.io", "url": "https://kubernetes.io/docs/tutorials/", "level": "Intermediate", "free": True},
        {"title": "CKA with Practice Tests", "platform": "Udemy (Mumshad Mannambeth)", "url": "https://www.udemy.com/course/certified-kubernetes-administrator-with-practice-tests/", "level": "Intermediate-Advanced", "free": False},
    ],
    "AWS": [
        {"title": "AWS Cloud Practitioner Essentials", "platform": "AWS Training", "url": "https://aws.amazon.com/training/", "level": "Beginner", "free": True},
        {"title": "AWS Solutions Architect Associate", "platform": "Udemy (Stephane Maarek)", "url": "https://www.udemy.com/course/aws-certified-solutions-architect-associate-saa-c03/", "level": "Intermediate", "free": False},
    ],
    "React": [
        {"title": "React Official Docs (react.dev)", "platform": "react.dev", "url": "https://react.dev/learn", "level": "Beginner", "free": True},
        {"title": "The Odin Project - Full Stack", "platform": "theodinproject.com", "url": "https://www.theodinproject.com", "level": "Beginner-Intermediate", "free": True},
    ],
    "Apache Kafka": [
        {"title": "Kafka: The Definitive Guide", "platform": "O'Reilly (free PDF)", "url": "https://www.confluent.io/resources/kafka-the-definitive-guide-v2/", "level": "Intermediate", "free": True},
        {"title": "Apache Kafka Series", "platform": "Udemy (Stephane Maarek)", "url": "https://www.udemy.com/course/apache-kafka/", "level": "Intermediate", "free": False},
    ],
    "Large Language Models / LLMs": [
        {"title": "Hugging Face NLP Course", "platform": "huggingface.co", "url": "https://huggingface.co/learn/nlp-course", "level": "Intermediate", "free": True},
        {"title": "LLM University", "platform": "Cohere", "url": "https://docs.cohere.com/docs/llmu", "level": "Beginner-Intermediate", "free": True},
        {"title": "Building LLM-Powered Applications", "platform": "deeplearning.ai", "url": "https://www.deeplearning.ai/short-courses/", "level": "Intermediate", "free": True},
    ],
}


def build_course_docs():
    """Write one document per skill covering course recommendations."""
    lines_all = ["SKILL-TO-COURSE MAPPING FOR CAREER COACHING", "=" * 60, ""]
    for skill, courses in SKILL_COURSES.items():
        lines_all.append(f"\n--- {skill} ---")
        for c in courses:
            free_tag = "[FREE]" if c["free"] else "[PAID]"
            lines_all.append(f"  {free_tag} {c['title']} — {c['platform']}")
            lines_all.append(f"    Level: {c['level']} | URL: {c['url']}")
    (KB_DIR / "skill_courses.txt").write_text("\n".join(lines_all), encoding="utf-8")
    print("  ✓ Written: skill_courses.txt")


# ─── 3. Skill Graph → Document ────────────────────────────────────────────────

def build_skill_graph_doc():
    """Convert your existing skill_graph.json into a readable RAG document."""
    graph_path = Path(__file__).parent / "skill_graph.json"
    if not graph_path.exists():
        print("  ⚠ skill_graph.json not found, skipping.")
        return

    data = json.loads(graph_path.read_text())
    lines = ["SKILL ADJACENCY MAP (for career transition advice)", "=" * 60, ""]
    lines.append("If a candidate has skill X, they can naturally learn skill Y next.")
    lines.append("")
    for domain, skills in data.get("adjacencies", {}).items():
        lines.append(f"{domain}:")
        lines.append(f"  Related skills: {', '.join(skills)}")
        lines.append("")
    (KB_DIR / "skill_graph.txt").write_text("\n".join(lines), encoding="utf-8")
    print("  ✓ Written: skill_graph.txt")


# ─── 4. Common Interview Advice ───────────────────────────────────────────────

INTERVIEW_ADVICE = """
INTERVIEW PREPARATION GUIDE FOR INDIAN TECH MARKET
===================================================

DSA / Coding Rounds:
- Practice on LeetCode. Use Striver's A-Z sheet as your curriculum.
- Target: 150+ problems before appearing for product companies (FAANG/Flipkart/Razorpay).
- Focus areas by role:
  - SDE: Arrays, Strings, Trees, Graphs, DP, Sliding Window
  - MLE: Same as SDE + Statistics, Probability basics
  - Data Engineer: SQL (heavy), Python scripting, basic DS
- Time yourself: aim for 20-25 minutes per medium problem.

System Design (for 2+ years experience):
- Study: Grokking System Design, ByteByteGo, Gaurav Sen YouTube
- Practiced topics: URL shortener, Twitter feed, WhatsApp, Uber surge pricing
- Draw diagrams, discuss trade-offs, ask clarifying questions

Behavioral Rounds:
- Use STAR format: Situation, Task, Action, Result
- Prepare 5-6 stories: a conflict, a failure, a success, a leadership moment
- Know why you want to join that company specifically

Resume Tips for India:
- Keep to 1 page for under 5 years experience
- Quantify: "Reduced API latency by 40%" not "improved performance"
- List GitHub profile, LeetCode handle, and any Kaggle ranking
- Put CGPA only if above 7.5; omit if lower
- For freshers: lead with projects, not education

Salary Negotiation:
- Always give a range, not a number. Upper range = your target.
- Don't reveal current salary (banned in some states in the US, but common in India)
- Use competing offers if you have them
- Joining bonus is often negotiable even when base is fixed

Cold Outreach on LinkedIn:
- Connect with SDEs at target companies, not HR
- Message: "Hi, I'm a [role] with [X years] experience. I noticed [company] is hiring for [role]. 
  I'd love a referral if you feel my profile is a good fit. Here's my resume: [link]"
- Referrals can move your application to top of queue and sometimes add a 1-2 LPA referral bonus.
"""


def build_interview_doc():
    (KB_DIR / "interview_advice.txt").write_text(INTERVIEW_ADVICE, encoding="utf-8")
    print("  ✓ Written: interview_advice.txt")


# ─── 5. Career Transition Guides ─────────────────────────────────────────────

TRANSITIONS = """
CAREER TRANSITION GUIDES
=========================

SERVICE COMPANY → PRODUCT COMPANY (e.g., TCS/Infosys → Flipkart/Razorpay):
  Timeline: 6-12 months of dedicated preparation
  Steps:
    1. Build DSA fundamentals: Striver's sheet, 150+ LeetCode problems
    2. Pick 1-2 strong projects (not CRUD apps — solve a real problem)
    3. Put everything on GitHub with good READMEs
    4. Apply via referrals first (LinkedIn outreach to employees)
    5. Start with mid-size product companies (Juspay, BrowserStack, Freshworks) 
       before targeting FAANG
  Common mistake: People study DSA for 2 months and apply without projects. 
  Companies want to see you can BUILD things, not just pass LeetCode.

DEVELOPER → ML ENGINEER:
  Timeline: 8-15 months
  You need: Strong Python, Linear Algebra basics, Statistics, ML theory + practice
  Steps:
    1. Andrew Ng's ML Specialization (Coursera) — 2 months
    2. Kaggle: complete 3 structured data competitions, aim for top 20%
    3. Learn PyTorch: fast.ai course (practical approach)
    4. Build 2 end-to-end projects: 
       a) Tabular ML (prediction problem with a deployed API)
       b) NLP or CV project
    5. Learn MLflow for experiment tracking, Docker for deployment
    6. Apply to companies with data science teams (not pure research labs yet)

DATA ANALYST → DATA ENGINEER:
  Timeline: 4-8 months (you already know SQL, which is 40% of the job)
  Add: Python scripting, Apache Airflow, Spark basics, cloud storage (S3/GCS)
  Steps:
    1. Master Python for data: Pandas, file I/O, API calls
    2. Build a pipeline: scrape data → store in cloud → transform with dbt → dashboard
    3. Learn Airflow for scheduling
    4. Get AWS/GCP Cloud Practitioner certification (free tier, ~2 months)

FRESHER → FIRST JOB STRATEGY:
  If CGPA < 7 AND from Tier-3 college:
    - Don't apply to mass recruiters (Wipro/Infosys/TCS off-campus) first — low response rate
    - Build 2 strong projects on GitHub with live demos
    - Apply to 50+ startups on AngelList/Wellfound and LinkedIn
    - Consider internship → PPO (Pre-placement offer) route
    - Upskill certificate from Google/Meta on Coursera adds credibility
  If CGPA > 8 AND from Tier-1/2:
    - On-campus placements are your best bet
    - Supplement with off-campus applications to product companies
    - Start DSA prep in 3rd year

INDIA → INTERNATIONAL (US/EU):
  Timeline: 2-5 years
  Route 1: FAANG India → FAANG International transfer (most common)
  Route 2: Master's degree (MS in CS) in US/Canada/Germany
  Route 3: Direct off-campus from India (rare, requires very strong profile)
  For H1-B: US job market requires strong DSA + System Design + leetcode preparation
  For EU: Germany has Blue Card, Netherlands has tech visa. Less leetcode, more practical interviews.
"""


def build_transition_doc():
    (KB_DIR / "career_transitions.txt").write_text(TRANSITIONS, encoding="utf-8")
    print("  ✓ Written: career_transitions.txt")


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"Building RAG knowledge base -> {KB_DIR}/")
    build_career_path_docs()
    build_course_docs()
    build_skill_graph_doc()
    build_interview_doc()
    build_transition_doc()
    docs = list(KB_DIR.glob("*.txt"))
    print(f"\n✓ Done! {len(docs)} documents written to {KB_DIR}")
    print("Next step: run  python backend/rag_store.py  to embed and index these.")
