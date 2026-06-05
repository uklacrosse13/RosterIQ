# config/settings.py
# Central configuration — all environment variables and constants live here

import os

# ── Database ──────────────────────────────────────────────────────────────────
# Reads from environment variable or Streamlit secrets
def get_database_url() -> str:
    """
    Priority:
    1. DATABASE_URL environment variable (local dev / Railway / Render)
    2. Streamlit secrets (Streamlit Cloud deployment)
    3. SQLite fallback (demo / no-DB mode)
    """
    # Direct env var
    db_url = os.environ.get("DATABASE_URL", "")
    if db_url:
        # Heroku/Railway give postgres:// but SQLAlchemy needs postgresql://
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        return db_url

    # Streamlit secrets
    try:
        import streamlit as st
        return st.secrets["database"]["url"]
    except Exception:
        pass

    # SQLite fallback — works with zero setup, stores data in a local file
    return "sqlite:///rosteriq.db"


# ── App metadata ──────────────────────────────────────────────────────────────
APP_NAME    = os.environ.get("APP_NAME", "RosterIQ")
APP_VERSION = os.environ.get("APP_VERSION", "2.0")
DEBUG       = os.environ.get("DEBUG", "false").lower() == "true"

# ── Scoring weights ───────────────────────────────────────────────────────────
WEIGHTS = {
    "athletic": 0.35,
    "social":   0.30,
    "market":   0.25,
    "retention": 0.10,
}

# ── NIL calibration ───────────────────────────────────────────────────────────
NIL_BASE_SCALE  = 600    # Base dollar multiplier
NIL_EXP_DIVISOR = 22     # Controls curve steepness
NIL_HI_MULT     = 1.75   # High estimate = low × this

# Blue chip multipliers
RECRUIT_MULTIPLIERS = {
    "top10":  25.0,
    "top30":  14.0,
    "top100":  5.0,
    "top300":  2.0,
    "unranked": 1.0,
}
DRAFT_MULTIPLIERS = {
    1: 18.0,   # Lottery (1-14)
    2:  8.0,   # Late 1st (15-30)
    3:  3.0,   # 2nd round
    0:  1.0,   # Undrafted
}

HOUSE_CAP = 20_500_000   # 2025-26 House settlement cap

# ── Lookup maps ───────────────────────────────────────────────────────────────
CONF_TIER_MAP  = {"Power 4": 1, "Mid-Major": 2, "D-II / D-III / NAIA": 3}
AWARD_MAP      = {"None": 0, "Team Award": 1, "Conference Award": 2, "All-American / National": 3}
SIZE_MAP       = {"20,000+": 3, "8,000–20,000": 2, "Under 8,000": 1}
TV_MAP         = {"National (ESPN, Fox)": 3, "Regional network": 2, "Streaming / local only": 1}
MKT_MAP        = {"Top-25 DMA": 3, "Mid-size market": 2, "Small market": 1}
TRANSFER_MAP   = {"Low — committed": 0, "Medium": 1, "High — exploring portal": 2}
DRAFT_RISK_MAP = {"0 — Not projected": 0, "3 — 2nd round proj.": 3,
                  "2 — Late 1st rd (15-30)": 2, "1 — Lottery pick (1-14)": 1}
RECRUIT_MAP    = {"Unranked": 0, "Top 300": 250, "Top 100": 75, "Top 30": 20, "Top 10": 5}

SPORTS   = ["Football", "Basketball", "Baseball", "Soccer", "Volleyball",
            "Track & Field", "Swimming", "Wrestling", "Other"]
YEARS    = ["Freshman", "Sophomore", "Junior", "Senior", "Grad Transfer"]

