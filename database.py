"""
FairAI — Database layer
────────────────────────────────────────────────────────────────
Persists anonymised resume-scoring results for real percentile
benchmarking. No PII (name, email, phone, institution, etc.)
ever touches this table — only the role, the score, and a few
analytic flags.

Connection priority:
  1. DATABASE_URL env var (Render Postgres, e.g.
     postgres://user:pass@host:port/db)
  2. Fallback: local SQLite file (sqlite:///./local_scores.db)

Render note: Render exposes the legacy "postgres://" scheme, but
SQLAlchemy 2.x requires "postgresql://". We auto-normalise it.
"""
from __future__ import annotations

import os
import sys

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    func,
    text,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker


# ─── Connection string ────────────────────────────────────────
_DEFAULT_SQLITE_URL = "sqlite:///./local_scores.db"
DATABASE_URL = os.environ.get("DATABASE_URL", _DEFAULT_SQLITE_URL).strip()

# Render (and Heroku) hand out "postgres://..." — SQLAlchemy 2.x
# only accepts "postgresql://...". Normalise silently.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

_is_sqlite = DATABASE_URL.startswith("sqlite")

# SQLite needs a flag to be safe across FastAPI's threadpool
_engine_kwargs: dict = {"pool_pre_ping": True}
if _is_sqlite:
    _engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **_engine_kwargs)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)

Base = declarative_base()


# ─── Model ────────────────────────────────────────────────────
class ResumeScore(Base):
    """
    One row per completed /analyze OR /counterfactual-test invocation.

    PII-free by design: we store the role the candidate was
    scored against, the fit_score Bot 4 produced, and a couple
    of analytical flags used for trend reporting.

    Bias delta columns (nullable) are populated when /counterfactual-test
    is run, enabling the /bias-comparison aggregate dashboard.
    """

    __tablename__ = "resume_scores"

    id               = Column(Integer, primary_key=True, index=True, autoincrement=True)
    role_target      = Column(String(255), nullable=False, index=True)
    fit_score        = Column(Integer, nullable=False, index=True)
    contextual_ratio = Column(Float, nullable=False, default=0.5)
    has_pii_stripped = Column(Boolean, nullable=False, default=True)
    timestamp        = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # ── Bias delta columns (None if counterfactual was not run) ──
    delta_institution = Column(Float, nullable=True)   # inst_score - original_score
    delta_gap         = Column(Float, nullable=True)   # gap_score  - original_score
    delta_name        = Column(Float, nullable=True)   # name_score - original_score
    delta_combined    = Column(Float, nullable=True)   # all-combined - original_score
    evaluator_model   = Column(String(64), nullable=True)  # "aethel" | "llama" | etc.

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<ResumeScore id={self.id} role={self.role_target!r} "
            f"fit={self.fit_score} ratio={self.contextual_ratio:.2f}>"
        )


# ─── User model ─────────────────────────────────────────────
class User(Base):
    """
    One row per registered user.
    Passwords are stored as bcrypt hashes — never plaintext.
    role: 'recruiter' | 'candidate'
    """
    __tablename__ = "users"

    id           = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email        = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name         = Column(String(255), nullable=False)
    org          = Column(String(255), nullable=True)
    role         = Column(String(32), nullable=False, default="recruiter")  # recruiter | candidate
    is_verified  = Column(Boolean, nullable=False, default=False)  # True after OTP verified
    is_recruiter_verified = Column(Boolean, nullable=False, default=False)  # True after company email verified (recruiters only)
    linkedin_url = Column(String(512), nullable=True)   # Optional LinkedIn profile URL (unverified display)
    created_at   = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    scans = relationship("ScanRecord", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} role={self.role}>"


# ─── Scan record model ────────────────────────────────────────
class ScanRecord(Base):
    """
    One row per resume analysis run, linked to an authenticated user.
    result_json stores the full /analyze response for retrieval in History view.
    file_name is the original upload filename (display only — no file is stored).
    """
    __tablename__ = "scan_records"

    id           = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id      = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    role_target  = Column(String(255), nullable=False)
    fit_score    = Column(Integer, nullable=False)
    file_name    = Column(String(512), nullable=True)
    candidate_id = Column(String(64), nullable=True)   # AETH-XXXXX display ID
    result_json  = Column(Text, nullable=True)          # full JSON blob from /analyze
    timestamp    = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    kanban_stage = Column(String(32), nullable=False, default="Sourced")

    user = relationship("User", back_populates="scans")

    def __repr__(self) -> str:
        return f"<ScanRecord id={self.id} user_id={self.user_id} role={self.role_target!r} score={self.fit_score}>"


# ─── OTP token model ───────────────────────────────────────────
class OTPToken(Base):
    """
    Short-lived 6-digit OTP for email verification.
    One row per OTP issued. Rows are invalidated (used=True) on
    successful verification or replaced when a new one is requested.

    Expiry is checked application-side (not via DB trigger) so this
    works identically on SQLite and PostgreSQL.
    """
    __tablename__ = "otp_tokens"

    id         = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email      = Column(String(255), nullable=False, index=True)
    otp_code   = Column(String(6), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used       = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<OTPToken id={self.id} email={self.email!r} used={self.used}>"


# ─── Helpers ──────────────────────────────────────────────────
def _run_migration(table: str, col_name: str, col_def: str) -> None:
    """
    Safely add a single column to an existing table.
    Uses IF NOT EXISTS for PostgreSQL; falls back to try/except for SQLite.
    Each migration runs in its own connection to avoid aborted-transaction issues.
    """
    try:
        with engine.connect() as conn:
            if _is_sqlite:
                # SQLite doesn't support IF NOT EXISTS on ALTER TABLE
                try:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_def}"))
                    conn.commit()
                    print(f"[FairAI] Migration: added {table}.{col_name}")
                except Exception:
                    pass  # column already exists
            else:
                # PostgreSQL supports IF NOT EXISTS — safe and idempotent
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col_name} {col_def}"))
                conn.commit()
                print(f"[FairAI] Migration: ensured {table}.{col_name}")
    except Exception as e:
        print(f"[FairAI] WARNING: migration {table}.{col_name} failed: {e}", file=sys.stderr)


def init_db() -> None:
    """Create tables if they don't already exist, then run column migrations."""
    try:
        Base.metadata.create_all(bind=engine)

        # --- Column migrations ---
        # Each runs in its own connection to avoid PostgreSQL aborted-transaction issues.
        _run_migration("resume_scores", "delta_institution", "FLOAT")
        _run_migration("resume_scores", "delta_gap",         "FLOAT")
        _run_migration("resume_scores", "delta_name",        "FLOAT")
        _run_migration("resume_scores", "delta_combined",    "FLOAT")
        _run_migration("resume_scores", "evaluator_model",   "VARCHAR(64)")
        _run_migration("users", "is_recruiter_verified", "BOOLEAN DEFAULT FALSE")
        _run_migration("users", "linkedin_url",          "VARCHAR(512)")
        _run_migration("scan_records", "kanban_stage", "VARCHAR(32) DEFAULT 'Sourced'")

        backend = "SQLite" if _is_sqlite else "PostgreSQL"
        print(f"[FairAI] DB ready ({backend}) \u2014 tables 'resume_scores', 'users', 'scan_records', 'otp_tokens' ensured.")
    except Exception as e:  # noqa: BLE001
        # Never crash the app just because stats persistence is down.
        print(f"[FairAI] WARNING: could not initialise DB: {e}", file=sys.stderr)


def record_bias_deltas(
    role_target: str,
    original_score: float,
    variants: dict,          # {"institution": 93, "gap": 90, "name": 88, "combined": 95}
    evaluator_model: str = "aethel",
) -> None:
    """
    Write per-signal bias deltas to the resume_scores table after a
    /counterfactual-test run.

    Fails silently so it NEVER blocks the API response.

    Args:
        variants: keys must include institution, gap, name, combined.
                  Values are absolute scores (not deltas) — we compute
                  the delta here as variant_score - original_score.
    """
    try:
        with SessionLocal() as db:
            row = ResumeScore(
                role_target=role_target,
                fit_score=int(original_score),
                contextual_ratio=0.5,
                has_pii_stripped=True,
                delta_institution=variants.get("institution", original_score) - original_score,
                delta_gap=variants.get("gap", original_score) - original_score,
                delta_name=variants.get("name", original_score) - original_score,
                delta_combined=variants.get("combined", original_score) - original_score,
                evaluator_model=evaluator_model,
            )
            db.add(row)
            db.commit()
            print(f"[FairAI] Bias deltas recorded — role={role_target}, model={evaluator_model}, "
                  f"\u0394inst={row.delta_institution:+.1f} \u0394gap={row.delta_gap:+.1f} "
                  f"\u0394name={row.delta_name:+.1f}")
    except Exception as e:
        print(f"[FairAI] WARNING: Failed to record bias deltas: {e}", file=sys.stderr)


def get_bias_trends(role_target: str | None = None, limit: int = 100) -> list[dict]:
    """
    Fetch bias delta rows for the /bias-comparison and /bias-trends endpoints.

    Args:
        role_target: optional role filter; None returns all roles.
        limit: max rows to return (most recent first).

    Returns a list of dicts, each with:
        id, role_target, fit_score, delta_institution, delta_gap,
        delta_name, delta_combined, evaluator_model, timestamp, total_bias
    """
    try:
        with SessionLocal() as db:
            q = db.query(ResumeScore).filter(
                ResumeScore.delta_institution.isnot(None)
            )
            if role_target:
                q = q.filter(ResumeScore.role_target == role_target)
            rows = q.order_by(ResumeScore.timestamp.desc()).limit(limit).all()

            result = []
            for r in rows:
                deltas = [r.delta_institution, r.delta_gap, r.delta_name]
                total_bias = sum(abs(d) for d in deltas if d is not None)
                result.append({
                    "id":                r.id,
                    "role_target":       r.role_target,
                    "fit_score":         r.fit_score,
                    "delta_institution": r.delta_institution,
                    "delta_gap":         r.delta_gap,
                    "delta_name":        r.delta_name,
                    "delta_combined":    r.delta_combined,
                    "evaluator_model":   r.evaluator_model,
                    "timestamp":         r.timestamp.isoformat() if r.timestamp else None,
                    "total_bias":        round(total_bias, 2),
                })
            return result
    except Exception as e:
        print(f"[FairAI] WARNING: get_bias_trends failed: {e}", file=sys.stderr)
        return []


# ─── User helpers ─────────────────────────────────────────────
def create_user(email: str, password_hash: str, name: str, role: str = "recruiter", org: str | None = None) -> User | None:
    """Insert a new user row. Returns the User object or None on failure."""
    try:
        with SessionLocal() as db:
            user = User(email=email, password_hash=password_hash, name=name, role=role, org=org)
            db.add(user)
            db.commit()
            db.refresh(user)
            return user
    except Exception as e:
        print(f"[FairAI] create_user failed: {e}", file=sys.stderr)
        return None


def get_user_by_email(email: str) -> User | None:
    """Fetch user row by email. Returns None if not found."""
    try:
        with SessionLocal() as db:
            return db.query(User).filter(User.email == email).first()
    except Exception as e:
        print(f"[FairAI] get_user_by_email failed: {e}", file=sys.stderr)
        return None


def get_user_by_id(user_id: int) -> User | None:
    """Fetch user row by primary key."""
    try:
        with SessionLocal() as db:
            return db.query(User).filter(User.id == user_id).first()
    except Exception as e:
        print(f"[FairAI] get_user_by_id failed: {e}", file=sys.stderr)
        return None


# ─── Scan record helpers ──────────────────────────────────────
def create_scan_record(
    user_id: int | None,
    role_target: str,
    fit_score: int,
    file_name: str | None = None,
    candidate_id: str | None = None,
    result_json: str | None = None,
) -> ScanRecord | None:
    """Persist one scan result linked to a user. Silent-fail."""
    try:
        with SessionLocal() as db:
            record = ScanRecord(
                user_id=user_id,
                role_target=role_target,
                fit_score=fit_score,
                file_name=file_name,
                candidate_id=candidate_id,
                result_json=result_json,
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            return record
    except Exception as e:
        print(f"[FairAI] create_scan_record failed: {e}", file=sys.stderr)
        return None


def get_user_scans(user_id: int, limit: int = 20) -> list[dict]:
    """Return the most recent scan records for a user as plain dicts."""
    try:
        with SessionLocal() as db:
            rows = (
                db.query(ScanRecord)
                .filter(ScanRecord.user_id == user_id)
                .order_by(ScanRecord.timestamp.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "id": r.id,
                    "role_target": r.role_target,
                    "fit_score": r.fit_score,
                    "file_name": r.file_name,
                    "candidate_id": r.candidate_id,
                    "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                    "has_result": r.result_json is not None,
                    "kanban_stage": r.kanban_stage or "Sourced",
                }
                for r in rows
            ]
    except Exception as e:
        print(f"[FairAI] get_user_scans failed: {e}", file=sys.stderr)
        return []


# ─── OTP helpers ──────────────────────────────────────────────
import random as _random
import string as _string
from datetime import datetime, timedelta, timezone as _tz


def _generate_otp(length: int = 6) -> str:
    """Generate a cryptographically safe numeric OTP."""
    import secrets
    return "".join(secrets.choice(_string.digits) for _ in range(length))


def create_otp(email: str, expiry_minutes: int = 10) -> str | None:
    """
    Invalidate any existing active OTPs for this email, then
    create a fresh one. Returns the new OTP code (plain string)
    or None on DB failure.
    """
    try:
        with SessionLocal() as db:
            # Invalidate all previous OTPs for this email
            db.query(OTPToken).filter(
                OTPToken.email == email,
                OTPToken.used == False,  # noqa: E712
            ).update({"used": True})
            db.commit()

            # Issue a new one
            code = _generate_otp()
            expires_at = datetime.now(_tz.utc) + timedelta(minutes=expiry_minutes)
            token = OTPToken(email=email, otp_code=code, expires_at=expires_at)
            db.add(token)
            db.commit()
            print(f"[Auth] OTP created for {email!r} — expires in {expiry_minutes}m")
            return code
    except Exception as e:
        print(f"[Auth] create_otp failed: {e}", file=sys.stderr)
        return None


def get_active_otp(email: str, code: str) -> OTPToken | None:
    """
    Return the OTPToken row if:
      - email matches
      - code matches
      - not already used
      - not expired
    Returns None otherwise.
    """
    try:
        with SessionLocal() as db:
            now = datetime.now(_tz.utc)
            return (
                db.query(OTPToken)
                .filter(
                    OTPToken.email == email,
                    OTPToken.otp_code == code,
                    OTPToken.used == False,   # noqa: E712
                    OTPToken.expires_at > now,
                )
                .first()
            )
    except Exception as e:
        print(f"[Auth] get_active_otp failed: {e}", file=sys.stderr)
        return None


def consume_otp(email: str, code: str) -> bool:
    """
    Validate + consume OTP in one transaction:
      1. Find active OTP row
      2. Mark it used=True
      3. Set User.is_verified=True
    Returns True on success, False if OTP invalid/expired.
    """
    try:
        with SessionLocal() as db:
            now = datetime.now(_tz.utc)
            token = (
                db.query(OTPToken)
                .filter(
                    OTPToken.email == email,
                    OTPToken.otp_code == code,
                    OTPToken.used == False,   # noqa: E712
                    OTPToken.expires_at > now,
                )
                .first()
            )
            if token is None:
                return False

            # Mark OTP used
            token.used = True

            # Mark user verified
            user = db.query(User).filter(User.email == email).first()
            if user:
                user.is_verified = True

            db.commit()
            print(f"[Auth] OTP consumed for {email!r} — user verified")
            return True
    except Exception as e:
        print(f"[Auth] consume_otp failed: {e}", file=sys.stderr)
        return False


def mark_user_verified(email: str) -> bool:
    """Directly mark a user as verified (used for bypass/admin flows)."""
    try:
        with SessionLocal() as db:
            user = db.query(User).filter(User.email == email).first()
            if not user:
                return False
            user.is_verified = True
            db.commit()
            return True
    except Exception as e:
        print(f"[Auth] mark_user_verified failed: {e}", file=sys.stderr)
        return False


def mark_recruiter_verified(user_id: int) -> bool:
    """Mark a recruiter as company-email-verified after OTP confirmation."""
    try:
        with SessionLocal() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            user.is_recruiter_verified = True
            db.commit()
            print(f"[Auth] Recruiter verified: user_id={user_id}")
            return True
    except Exception as e:
        print(f"[Auth] mark_recruiter_verified failed: {e}", file=sys.stderr)
        return False


def update_linkedin_url(user_id: int, linkedin_url: str) -> bool:
    """Save an optional LinkedIn profile URL for a recruiter."""
    try:
        with SessionLocal() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            user.linkedin_url = linkedin_url.strip()[:512]
            db.commit()
            return True
    except Exception as e:
        print(f"[Auth] update_linkedin_url failed: {e}", file=sys.stderr)
        return False


def update_kanban_stage(scan_id: int, user_id: int, stage: str) -> bool:
    """
    Move a candidate card to a new Kanban stage.
    Only updates if the record belongs to the given user (ownership check).
    Returns True on success, False if not found or wrong user.
    """
    VALID_STAGES = {"Sourced", "Screening", "Interview", "Offer", "Rejected"}
    if stage not in VALID_STAGES:
        return False
    try:
        with SessionLocal() as db:
            record = db.query(ScanRecord).filter(
                ScanRecord.id == scan_id,
                ScanRecord.user_id == user_id,
            ).first()
            if not record:
                return False
            record.kanban_stage = stage
            db.commit()
            print(f"[Kanban] scan_id={scan_id} moved to '{stage}' by user_id={user_id}")
            return True
    except Exception as e:
        print(f"[Kanban] update_kanban_stage failed: {e}", file=sys.stderr)
        return False
