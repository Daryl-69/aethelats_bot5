"""
adzuna_refresh.py — Weekly India job market refresh via Adzuna API
==================================================================
Fetches 5,000+ live job postings from India, appends to the existing
Excel dataset, re-categorises ALL rows, and rebuilds the RAG knowledge base.

Usage (manual):
    python backend/adzuna_refresh.py

Usage (automated — add to main.py as a background endpoint, or run via cron):
    POST /admin/refresh-dataset   (calls run_weekly_refresh() directly)

Requirements:
    pip install requests openpyxl pandas

Adzuna API docs: https://developer.adzuna.com/overview
Get your keys:   https://developer.adzuna.com/signup
"""

import os
import time
import logging
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime

# ─── Config ───────────────────────────────────────────────────────────────────
ADZUNA_APP_ID  = os.getenv("ADZUNA_APP_ID", "")    # Set in HF Space Secrets
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY", "")   # Set in HF Space Secrets

DATASET_PATH = Path(__file__).parent.parent / "indian-job-market-dataset-2025.xlsx"
BACKUP_DIR   = Path(__file__).parent.parent / "dataset_backups"

# Target: 5,000 jobs per run (50 results per page × 100 pages)
RESULTS_PER_PAGE = 50
TARGET_JOBS      = 5000

# India country code for Adzuna
COUNTRY = "in"

# Search queries — covers all major categories in our RAG
SEARCH_QUERIES = [
    "software engineer",
    "data scientist",
    "data engineer",
    "product manager",
    "devops",
    "machine learning",
    "frontend developer",
    "backend developer",
    "full stack developer",
    "QA engineer",
    "cybersecurity",
    "sales",
    "marketing",
    "human resources",
    "finance",
    "operations",
    "customer support",
    "healthcare",
    "education",
    "mechanical engineer",
    "civil engineer",
    "SAP consultant",
    "mobile developer",
]

BASE_URL = "https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


def fetch_jobs_for_query(query: str, max_jobs: int = 250) -> list[dict]:
    """
    Fetch up to max_jobs listings for a single search query.
    Adzuna returns max 50 per page; we page through automatically.
    """
    jobs = []
    page = 1
    pages_needed = (max_jobs // RESULTS_PER_PAGE) + 1

    while page <= pages_needed and len(jobs) < max_jobs:
        url = BASE_URL.format(country=COUNTRY, page=page)
        params = {
            "app_id":        ADZUNA_APP_ID,
            "app_key":       ADZUNA_APP_KEY,
            "results_per_page": RESULTS_PER_PAGE,
            "what":          query,
            "where":         "india",          # restrict to India locations
            "content-type":  "application/json",
            "sort_by":       "date",           # freshest jobs first
        }

        try:
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code == 401:
                log.error("Invalid Adzuna credentials. Check ADZUNA_APP_ID / ADZUNA_APP_KEY.")
                break
            if resp.status_code == 429:
                log.warning("Rate limited — sleeping 30s")
                time.sleep(30)
                continue
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            log.warning(f"  Page {page} for '{query}' failed: {e}")
            break

        results = data.get("results", [])
        if not results:
            break   # no more pages

        for job in results:
            # Map Adzuna fields → our dataset column names
            salary_min = job.get("salary_min")
            salary_max = job.get("salary_max")
            salary_str = ""
            if salary_min and salary_max:
                # Convert annual USD → approximate INR LPA (rough: ×83/100000)
                min_lpa = round(salary_min * 83 / 100_000, 1)
                max_lpa = round(salary_max * 83 / 100_000, 1)
                salary_str = f"{min_lpa}-{max_lpa} LPA"
            elif salary_min:
                salary_str = f"{round(salary_min * 83 / 100_000, 1)} LPA"

            jobs.append({
                "Job Title":          job.get("title", ""),
                "Company":            job.get("company", {}).get("display_name", ""),
                "Location":           job.get("location", {}).get("display_name", ""),
                "Experience (Years)": "",      # not provided by Adzuna
                "Salary":             salary_str or "Not disclosed",
                "Job Description":    job.get("description", ""),
                "Source":             "Adzuna Live",
                "Fetched Date":       datetime.now().strftime("%Y-%m-%d"),
                "Query":              query,
            })

        log.info(f"  Query='{query}' page={page}: {len(results)} jobs (total so far: {len(jobs)})")
        page += 1
        time.sleep(0.5)   # be a polite API consumer

    return jobs[:max_jobs]


def fetch_all_india_jobs(target: int = TARGET_JOBS) -> pd.DataFrame:
    """
    Cycle through all search queries until we hit target number of jobs.
    Returns a DataFrame of new jobs ready to append.
    """
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        raise ValueError(
            "ADZUNA_APP_ID and ADZUNA_APP_KEY must be set as environment variables. "
            "Get keys at https://developer.adzuna.com/signup"
        )

    all_jobs = []
    jobs_per_query = max(250, target // len(SEARCH_QUERIES))

    for query in SEARCH_QUERIES:
        log.info(f"Fetching: '{query}' (up to {jobs_per_query} jobs)")
        jobs = fetch_jobs_for_query(query, max_jobs=jobs_per_query)
        all_jobs.extend(jobs)
        log.info(f"  → Total collected: {len(all_jobs)}")

        if len(all_jobs) >= target:
            break

    log.info(f"Fetch complete: {len(all_jobs)} new jobs from Adzuna India")
    return pd.DataFrame(all_jobs)


def backup_dataset():
    """Save a timestamped backup of the current dataset before modifying."""
    if not DATASET_PATH.exists():
        log.warning("No existing dataset found — skipping backup.")
        return
    BACKUP_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"dataset_backup_{stamp}.xlsx"
    import shutil
    shutil.copy2(DATASET_PATH, backup_path)
    log.info(f"Backup saved: {backup_path}")


def append_to_dataset(new_df: pd.DataFrame):
    """
    Load existing dataset, append new rows, deduplicate, save back.
    Returns total row count after merge.
    """
    if DATASET_PATH.exists():
        log.info(f"Loading existing dataset: {DATASET_PATH}")
        existing_df = pd.read_excel(DATASET_PATH, engine="openpyxl")
        log.info(f"  Existing rows: {len(existing_df):,}")
    else:
        log.warning("No existing dataset — starting fresh.")
        existing_df = pd.DataFrame()

    # Align columns (new data may have extra columns)
    combined = pd.concat([existing_df, new_df], ignore_index=True)

    # Deduplicate on Job Title + Company + Location
    before = len(combined)
    combined.drop_duplicates(
        subset=["Job Title", "Company", "Location"],
        keep="first",
        inplace=True
    )
    after = len(combined)
    log.info(f"  Deduplication: {before:,} → {after:,} rows ({before - after:,} dupes removed)")

    log.info(f"Saving updated dataset ({after:,} rows)...")
    combined.to_excel(DATASET_PATH, index=False, engine="openpyxl")
    log.info(f"✓ Dataset saved: {DATASET_PATH}")
    return after


def rebuild_rag():
    """Re-run the full RAG pipeline: categorise → build KB docs → embed into ChromaDB."""
    import subprocess, sys
    backend_dir = Path(__file__).parent

    log.info("Step 1: Re-categorising all rows & rebuilding RAG KB documents...")
    result = subprocess.run(
        [sys.executable, str(backend_dir / "process_dataset.py")],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        log.error(f"process_dataset.py failed:\n{result.stderr}")
        raise RuntimeError("Dataset processing failed")
    log.info(result.stdout)

    log.info("Step 2: Re-embedding documents into ChromaDB...")
    result = subprocess.run(
        [sys.executable, str(backend_dir / "rag_store.py")],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        log.error(f"rag_store.py failed:\n{result.stderr}")
        raise RuntimeError("ChromaDB rebuild failed")
    log.info(result.stdout)

    log.info("✓ RAG knowledge base fully updated.")


def run_weekly_refresh():
    """
    Full weekly refresh pipeline:
      1. Fetch 5,000+ live jobs from Adzuna India
      2. Backup current dataset
      3. Append new jobs (deduplicated)
      4. Rebuild RAG knowledge base
    """
    log.info("=" * 60)
    log.info("AETHEL WEEKLY DATASET REFRESH — START")
    log.info(f"Target: {TARGET_JOBS:,} new jobs from Adzuna India")
    log.info("=" * 60)

    start = time.time()

    # 1. Fetch
    new_df = fetch_all_india_jobs(target=TARGET_JOBS)
    if new_df.empty:
        log.error("No jobs fetched — aborting refresh.")
        return {"status": "error", "reason": "No jobs fetched from Adzuna"}

    # 2. Backup
    backup_dataset()

    # 3. Append
    total_rows = append_to_dataset(new_df)

    # 4. Rebuild RAG
    rebuild_rag()

    elapsed = round(time.time() - start, 1)
    log.info(f"=" * 60)
    log.info(f"WEEKLY REFRESH COMPLETE in {elapsed}s")
    log.info(f"  New jobs added: {len(new_df):,}")
    log.info(f"  Total dataset:  {total_rows:,} rows")
    log.info(f"=" * 60)

    return {
        "status":       "success",
        "new_jobs":     len(new_df),
        "total_rows":   total_rows,
        "elapsed_s":    elapsed,
        "timestamp":    datetime.now().isoformat(),
    }


if __name__ == "__main__":
    result = run_weekly_refresh()
    print(result)
