# modules/database.py
# SQLAlchemy ORM models + session factory
# Supports PostgreSQL (production) and SQLite (demo/local fallback)

from sqlalchemy import (create_engine, Column, Integer, String, Float,
                        Text, DateTime, Boolean, ForeignKey)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.pool import StaticPool
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config.settings import get_database_url

Base = declarative_base()

# ─────────────────────────────────────────────────────────────────────────────
# MODELS
# ─────────────────────────────────────────────────────────────────────────────

class Athlete(Base):
    __tablename__ = "athletes"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    name            = Column(String(120), nullable=False)
    school          = Column(String(120))
    sport           = Column(String(60))
    position        = Column(String(60))
    year            = Column(String(30))
    conference      = Column(String(60))

    # Athletic performance
    games_played    = Column(Integer, default=0)
    starts          = Column(Integer, default=0)
    recruiting_stars= Column(Integer, default=3)
    awards          = Column(String(60), default="None")
    injury_history  = Column(Text, default="None")
    stats_notes     = Column(Text, default="")

    # Social media
    ig_followers    = Column(Integer, default=0)
    tt_followers    = Column(Integer, default=0)
    x_followers     = Column(Integer, default=0)
    engagement_pct  = Column(Float, default=2.0)

    # Market
    school_size     = Column(String(30), default="8,000–20,000")
    tv_exposure     = Column(String(40), default="Regional network")
    market_size     = Column(String(30), default="Mid-size market")

    # Risk
    transfer_risk   = Column(String(40), default="Low — committed")
    draft_risk      = Column(String(40), default="0 — Not projected")
    eligibility_remaining = Column(Integer, default=2)

    # Blue chip
    national_recruit_rank = Column(String(20), default="Unranked")
    draft_projection      = Column(String(40), default="0 — Not projected")

    # Meta
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active       = Column(Boolean, default=True)

    # Relationship to scores
    scores          = relationship("AthleteScore", back_populates="athlete",
                                   cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Athlete {self.name} — {self.school}>"


class AthleteScore(Base):
    __tablename__ = "athlete_scores"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    athlete_id      = Column(Integer, ForeignKey("athletes.id"), nullable=False)

    # Dimension scores
    athletic_score  = Column(Integer, default=0)
    social_score    = Column(Integer, default=0)
    market_score    = Column(Integer, default=0)
    retention_risk  = Column(Integer, default=0)
    overall_score   = Column(Integer, default=0)

    # NIL estimates
    nil_low         = Column(Integer, default=0)
    nil_high        = Column(Integer, default=0)

    # Tier & recommendation
    tier            = Column(String(20), default="Entry Level")
    recommendation  = Column(String(40), default="Monitor")

    scored_at       = Column(DateTime, default=datetime.utcnow)

    athlete         = relationship("Athlete", back_populates="scores")

    def __repr__(self):
        return f"<Score athlete_id={self.athlete_id} overall={self.overall_score}>"


# ─────────────────────────────────────────────────────────────────────────────
# SESSION FACTORY
# ─────────────────────────────────────────────────────────────────────────────

_engine  = None
_Session = None


def get_engine():
    global _engine
    if _engine is None:
        db_url = get_database_url()
        if db_url.startswith("sqlite"):
            _engine = create_engine(
                db_url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )
        else:
            _engine = create_engine(db_url, pool_pre_ping=True)
    return _engine


def get_session():
    global _Session
    if _Session is None:
        _Session = sessionmaker(bind=get_engine())
    return _Session()


def init_db():
    """Create all tables if they don't exist."""
    Base.metadata.create_all(get_engine())


def db_mode() -> str:
    """Return 'postgresql', 'sqlite', or 'unknown'."""
    url = get_database_url()
    if "postgresql" in url:
        return "postgresql"
    if "sqlite" in url:
        return "sqlite"
    return "unknown"
