"""
Configuration for the Kopargaon Civic Resource Prioritization Platform (CRPP).

Standard library only. A .env file next to this module (backend/.env) and one at
the repository root are parsed manually if present, so no python-dotenv needed.
Real environment variables always win over .env values.
"""
from __future__ import annotations

import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_DIR.parent


def _load_dotenv(path: Path) -> None:
    """KEY=VALUE lines, '#' comments, optional surrounding quotes."""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv(BACKEND_DIR / ".env")
_load_dotenv(REPO_ROOT / ".env")


def _s(name: str, default: str) -> str:
    v = os.getenv(name)
    return default if v is None or v == "" else v


def _b(name: str, default: bool) -> bool:
    return _s(name, "true" if default else "false").strip().lower() in (
        "1", "true", "yes", "on")


def _i(name: str, default: int) -> int:
    try:
        return int(float(_s(name, str(default))))
    except ValueError:
        return default


def _f(name: str, default: float) -> float:
    try:
        return float(_s(name, str(default)))
    except ValueError:
        return default


class Settings:
    """Runtime settings. Instantiated once as ``settings`` at import time."""

    def __init__(self) -> None:
        # --- Application -------------------------------------------------
        self.APP_NAME = "Kopargaon CRPP API"
        self.APP_VERSION = "1.0.0"
        self.DEBUG = _b("DEBUG", False)
        self.BACKEND_DIR = BACKEND_DIR
        self.REPO_ROOT = REPO_ROOT
        # The council's own timezone. Every *timestamp* is stored in UTC, but a
        # dispatch date is a civic fact, not an instant: "today's work" means the
        # day the officer is standing in. Computing it from UTC files a run made
        # at 3 a.m. in Kopargaon under yesterday's date, which is wrong on the
        # manifest, wrong in the citizen SMS, and wrong in the audit trail.
        self.CIVIC_TIMEZONE = _s("CIVIC_TIMEZONE", "Asia/Kolkata")

        # --- Storage -----------------------------------------------------
        # sqlite3 file path. Kept as a plain path (not a SQLAlchemy URL) because
        # the data layer is stdlib sqlite3.
        self.DB_PATH = Path(_s("CRPP_DB_PATH",
                               str(BACKEND_DIR / "kopargaon_crpp.db")))
        self.SQL_ECHO = _b("SQL_ECHO", False)
        # WAL on a local disk; some virtualised/network mounts reject it and the
        # data layer falls back to DELETE automatically.
        self.SQLITE_JOURNAL_MODE = _s("SQLITE_JOURNAL_MODE", "WAL").upper()
        self.UPLOAD_DIR = Path(_s("UPLOAD_DIR", str(BACKEND_DIR / "uploads")))
        self.MAX_UPLOAD_SIZE_MB = _i("MAX_UPLOAD_SIZE_MB", 10)
        # Directory holding the kopargaon_*.json reference datasets.
        self.REFERENCE_DIR = Path(_s("CRPP_REFERENCE_DIR", str(REPO_ROOT)))

        # --- Security / auth ---------------------------------------------
        self.SECRET_KEY = _s("SECRET_KEY", "dev-only-change-me")
        self.JWT_ALGORITHM = "HS256"
        self.ACCESS_TOKEN_EXPIRE_MINUTES = _i("ACCESS_TOKEN_EXPIRE_MINUTES", 720)
        # When false, endpoints still accept and decode tokens but never reject
        # a request for missing/insufficient auth. Lets the frontend integrate
        # before login exists. Turn on for the demo/judging run.
        self.ENFORCE_AUTH = _b("ENFORCE_AUTH", False)
        self.PBKDF2_ITERATIONS = _i("PBKDF2_ITERATIONS", 120_000)
        self.OTP_TTL_SECONDS = _i("OTP_TTL_SECONDS", 300)
        self.SEED_ADMIN_USERNAME = _s("SEED_ADMIN_USERNAME", "admin")
        self.SEED_ADMIN_PASSWORD = _s("SEED_ADMIN_PASSWORD", "admin123")

        # --- Deduplication ------------------------------------------------
        # Hamming distance over a 64-bit pHash. Not present in any Kopargaon
        # dataset, so it is a tunable policy value, not a sourced fact.
        self.DEDUPE_HAMMING_THRESHOLD = _i("DEDUPE_HAMMING_THRESHOLD", 8)
        self.DEDUPE_RADIUS_METERS = _f("DEDUPE_RADIUS_METERS", 150.0)
        self.DEDUPE_WINDOW_HOURS = _i("DEDUPE_WINDOW_HOURS", 168)
        self.COMMUNITY_MULTIPLIER_STEP = _f("COMMUNITY_MULTIPLIER_STEP", 0.15)
        self.COMMUNITY_MULTIPLIER_CAP = _f("COMMUNITY_MULTIPLIER_CAP", 3.0)
        # Text-only reports (no photo) still cluster by category + radius.
        self.DEDUPE_TEXT_RADIUS_METERS = _f("DEDUPE_TEXT_RADIUS_METERS", 60.0)

        # --- Fuzzy AHP ----------------------------------------------------
        self.AHP_CR_THRESHOLD = _f("AHP_CR_THRESHOLD", 0.10)

        # --- Triage / allocation -----------------------------------------
        self.DEFAULT_DAILY_BUDGET = _f("DEFAULT_DAILY_BUDGET", 100_000.0)
        self.DEFAULT_DAILY_WORKFORCE_HOURS = _f(
            "DEFAULT_DAILY_WORKFORCE_HOURS", 80.0)
        # Weight of the SLA-breach penalty added to a ticket's knapsack value
        # when its operational deadline is already breached or at risk.
        self.SLA_BREACH_BONUS = _f("SLA_BREACH_BONUS", 0.35)
        self.SLA_AT_RISK_BONUS = _f("SLA_AT_RISK_BONUS", 0.15)
        # Tickets whose priority_floor is critical bypass the knapsack and are
        # always allocated (life-safety cannot be optimised away).
        self.CRITICAL_ALWAYS_ALLOCATE = _b("CRITICAL_ALWAYS_ALLOCATE", True)
        self.KNAPSACK_SOLVER = _s("KNAPSACK_SOLVER", "auto")  # auto|ortools|dp

        # --- Explainability ----------------------------------------------
        # Exact TOPSIS attribution is always available. SHAP needs sklearn+shap
        # and at least this many scored tickets to fit a surrogate model.
        self.ENABLE_SHAP = _b("ENABLE_SHAP", True)
        self.SHAP_MIN_SAMPLES = _i("SHAP_MIN_SAMPLES", 12)

        # --- Notifications (teammate owns the WhatsApp transport) ---------
        self.ENABLE_NOTIFICATIONS = _b("ENABLE_NOTIFICATIONS", False)
        self.NOTIFY_DEFAULT_LANGUAGE = _s("NOTIFY_DEFAULT_LANGUAGE", "en")
        self.WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
        self.WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
        self.WHATSAPP_WEBHOOK_VERIFY_TOKEN = os.getenv(
            "WHATSAPP_WEBHOOK_VERIFY_TOKEN")
        # HMAC signature key for inbound webhooks is the Meta *app secret*,
        # which is a different value from the verify token.
        self.WHATSAPP_APP_SECRET = os.getenv("WHATSAPP_APP_SECRET")
        self.WHATSAPP_API_VERSION = _s("WHATSAPP_API_VERSION", "v20.0")
        # --- CORS ---------------------------------------------------------
        self.CORS_ORIGINS = [
            o.strip() for o in _s("CORS_ORIGINS", "*").split(",") if o.strip()
        ]

        # --- Audit --------------------------------------------------------
        self.AUDIT_ENABLED = _b("AUDIT_ENABLED", True)

    @property
    def WHATSAPP_API_URL(self) -> str:
        return f"https://graph.facebook.com/{self.WHATSAPP_API_VERSION}"

    def as_public_dict(self) -> dict:
        """Safe-to-expose subset for GET /api/reference/config. Never includes
        SECRET_KEY, access tokens or the app secret."""
        return {
            "app_version": self.APP_VERSION,
            "enforce_auth": self.ENFORCE_AUTH,
            "notifications_enabled": self.ENABLE_NOTIFICATIONS,
            "shap_enabled": self.ENABLE_SHAP,
            # So the UI labels a dispatch date in the council's own calendar
            # rather than the browser's, which may be anywhere.
            "civic_timezone": self.CIVIC_TIMEZONE,
            "dedupe": {
                "hamming_threshold": self.DEDUPE_HAMMING_THRESHOLD,
                "radius_meters": self.DEDUPE_RADIUS_METERS,
                "window_hours": self.DEDUPE_WINDOW_HOURS,
                "community_multiplier_cap": self.COMMUNITY_MULTIPLIER_CAP,
                "provenance": "policy_value_not_sourced_from_dataset",
            },
            "ahp_cr_threshold": self.AHP_CR_THRESHOLD,
            "defaults": {
                "daily_budget_inr": self.DEFAULT_DAILY_BUDGET,
                "daily_workforce_hours": self.DEFAULT_DAILY_WORKFORCE_HOURS,
            },
            "knapsack_solver": self.KNAPSACK_SOLVER,
        }


settings = Settings()
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

