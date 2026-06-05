# data/seeder.py
# Seeds the database with 50 sample athletes
# Also exports a CSV template for the Streamlit upload feature

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from data.sample_athletes import SAMPLE_ATHLETES
from modules.engine import score_athlete
from config.settings import CONF_TIER_MAP, AWARD_MAP, SIZE_MAP, TV_MAP, MKT_MAP, TRANSFER_MAP, DRAFT_RISK_MAP, RECRUIT_MAP
import pandas as pd


def _map_athlete_to_engine(a: dict) -> dict:
    """Convert sample athlete dict keys to engine scoring keys."""
    return {
        "name":       a["name"],
        "school":     a["school"],
        "sport":      a["sport"],
        "pos":        a.get("pos", ""),
        "year":       a.get("year", ""),
        "games":      a.get("games", 10),
        "starts":     a.get("starts", 8),
        "stars":      a.get("stars", 3),
        "awards_val": AWARD_MAP.get(a.get("awards", "None"), 0),
        "conf_val":   CONF_TIER_MAP.get(a.get("conference", "Mid-Major"), 2),
        "ig":         a.get("ig", 0),
        "tt":         a.get("tt", 0),
        "xf":         a.get("xf", 0),
        "eng":        a.get("eng", 2.0),
        "mSize":      SIZE_MAP.get(a.get("school_size", "8,000–20,000"), 2),
        "mTV":        TV_MAP.get(a.get("tv_exposure", "Regional network"), 2),
        "mMkt":       MKT_MAP.get(a.get("market_size", "Mid-size market"), 2),
        "rTransfer":  TRANSFER_MAP.get(a.get("transfer_risk", "Low — committed"), 0),
        "rDraft":     DRAFT_RISK_MAP.get(a.get("draft_risk", "0 — Not projected"), 0),
        "recruit_rank": RECRUIT_MAP.get(a.get("recruit_rank", "Unranked"), 0),
        "draft_round":  DRAFT_RISK_MAP.get(a.get("draft_projection", "0 — Not projected"), 0),
        "injury_history": a.get("injury_history", "None"),
        "eligibility_remaining": a.get("eligibility_remaining", 2),
        "conference":  a.get("conference", "Mid-Major"),
        "school_size": a.get("school_size", "8,000–20,000"),
        "tv_exposure": a.get("tv_exposure", "Regional network"),
        "market_size": a.get("market_size", "Mid-size market"),
        "transfer_risk": a.get("transfer_risk", "Low — committed"),
        "draft_risk":   a.get("draft_risk", "0 — Not projected"),
        "national_recruit_rank": a.get("recruit_rank", "Unranked"),
        "draft_projection":     a.get("draft_projection", "0 — Not projected"),
    }


def get_scored_sample() -> list[dict]:
    """Return all 50 athletes scored and ready to use."""
    results = []
    for a in SAMPLE_ATHLETES:
        mapped = _map_athlete_to_engine(a)
        scored = score_athlete(mapped)
        results.append(scored)
    return results


def seed_database():
    """Write all 50 athletes and their scores to the database."""
    from modules.database import init_db, get_session, Athlete, AthleteScore

    init_db()
    session = get_session()

    try:
        # Clear existing sample data
        existing = session.query(Athlete).all()
        if existing:
            print(f"Found {len(existing)} existing athletes — skipping seed.")
            return len(existing)

        athletes_added = 0
        for a in SAMPLE_ATHLETES:
            mapped = _map_athlete_to_engine(a)
            scored = score_athlete(mapped)

            athlete = Athlete(
                name=a["name"], school=a["school"], sport=a["sport"],
                position=a.get("pos", ""), year=a.get("year", ""),
                conference=a.get("conference", ""),
                games_played=a.get("games", 0), starts=a.get("starts", 0),
                recruiting_stars=a.get("stars", 3),
                awards=a.get("awards", "None"),
                injury_history=a.get("injury_history", "None"),
                ig_followers=a.get("ig", 0), tt_followers=a.get("tt", 0),
                x_followers=a.get("xf", 0), engagement_pct=a.get("eng", 2.0),
                school_size=a.get("school_size", ""),
                tv_exposure=a.get("tv_exposure", ""),
                market_size=a.get("market_size", ""),
                transfer_risk=a.get("transfer_risk", "Low — committed"),
                draft_risk=a.get("draft_risk", "0 — Not projected"),
                eligibility_remaining=a.get("eligibility_remaining", 2),
                national_recruit_rank=a.get("recruit_rank", "Unranked"),
                draft_projection=a.get("draft_projection", "0 — Not projected"),
            )
            session.add(athlete)
            session.flush()

            score = AthleteScore(
                athlete_id=athlete.id,
                athletic_score=scored["ath"],
                social_score=scored["soc"],
                market_score=scored["mkt"],
                retention_risk=scored["risk"],
                overall_score=scored["overall"],
                nil_low=scored["nil_lo"],
                nil_high=scored["nil_hi"],
                tier=scored["tier"],
                recommendation=scored["recommendation"],
            )
            session.add(score)
            athletes_added += 1

        session.commit()
        print(f"✅ Seeded {athletes_added} athletes successfully.")
        return athletes_added

    except Exception as e:
        session.rollback()
        print(f"❌ Seed failed: {e}")
        raise
    finally:
        session.close()


def export_csv_template(path: str = "rosteriq_template.csv") -> str:
    """Export the 50-athlete dataset as a CSV for upload testing."""
    scored = get_scored_sample()
    rows = []
    for p in scored:
        rows.append({
            "name":                    p["name"],
            "school":                  p["school"],
            "sport":                   p["sport"],
            "position":                p.get("pos", ""),
            "year":                    p.get("year", ""),
            "games":                   p.get("games", 0),
            "starts":                  p.get("starts", 0),
            "stars":                   p.get("stars", 3),
            "awards":                  p.get("awards", "None") if "awards" in p else
                                       {0:"None",1:"Team Award",2:"Conference Award",3:"All-American / National"}.get(p.get("awards_val",0),"None"),
            "conference":              p.get("conference", ""),
            "ig_followers":            p.get("ig", 0),
            "tiktok_followers":        p.get("tt", 0),
            "twitter_followers":       p.get("xf", 0),
            "engagement_pct":          p.get("eng", 2.0),
            "school_size":             p.get("school_size", ""),
            "tv_exposure":             p.get("tv_exposure", ""),
            "market_size":             p.get("market_size", ""),
            "transfer_risk":           p.get("transfer_risk", "Low — committed"),
            "draft_risk":              p.get("draft_risk", "0 — Not projected"),
            "national_recruiting_rank":p.get("national_recruit_rank", "Unranked"),
            "draft_projection":        p.get("draft_projection", "0 — Not projected"),
            "injury_history":          p.get("injury_history", "None"),
            "eligibility_remaining":   p.get("eligibility_remaining", 2),
            # Computed scores (for reference)
            "overall_score":           p["overall"],
            "tier":                    p["tier"],
            "nil_low":                 p["nil_lo"],
            "nil_high":                p["nil_hi"],
            "recommendation":          p["recommendation"],
        })
    df = pd.DataFrame(rows)
    df.to_csv(path, index=False)
    print(f"✅ CSV exported to {path}")
    return path


if __name__ == "__main__":
    print("Seeding database...")
    seed_database()
    print("Exporting CSV template...")
    export_csv_template("rosteriq_50_athletes.csv")
