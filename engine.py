# modules/engine.py
# Pure valuation engine — no Streamlit, no database imports
# All functions are stateless and independently testable

import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config.settings import (
    WEIGHTS, NIL_BASE_SCALE, NIL_EXP_DIVISOR, NIL_HI_MULT,
    RECRUIT_MULTIPLIERS, DRAFT_MULTIPLIERS, HOUSE_CAP,
    CONF_TIER_MAP, AWARD_MAP, SIZE_MAP, TV_MAP, MKT_MAP,
    TRANSFER_MAP, DRAFT_RISK_MAP, RECRUIT_MAP,
)


# ─────────────────────────────────────────────────────────────────────────────
# DIMENSION SCORES
# ─────────────────────────────────────────────────────────────────────────────

def calc_athletic_score(games: int, starts: int, stars: int,
                         awards_val: int, conf_val: int) -> int:
    """
    0–100 score based on:
    - Start rate (max 30 pts)
    - Recruiting stars (max 40 pts)
    - Awards (max 26 pts)
    - Conference tier (max 10 pts)
    """
    sc = 0
    if games > 0:
        sc += min((starts / games) * 30, 30)
    sc += min((max(int(stars), 1) - 1) * 10, 40)
    sc += [0, 8, 16, 26][min(int(awards_val), 3)]
    sc += [10, 5, 2][min(int(conf_val) - 1, 2)]
    return round(min(max(sc, 0), 100))


def calc_social_score(ig: int, tt: int, xf: int, eng_pct: float) -> int:
    """
    Log-scaled score — engagement rate matters more than raw followers.
    20K engaged fans outscores 200K passive ones.
    """
    total = ig + tt + xf
    if total == 0:
        return 0
    eff = total * (eng_pct / 100 + 1)
    raw = math.log10(max(eff, 1)) / 7 * 100
    return round(min(max(raw, 0), 100))


def calc_market_score(size_val: int, tv_val: int, mkt_val: int) -> int:
    """
    Market opportunity score based on school size, TV deal, and local DMA.
    """
    raw = ((size_val - 1) + (tv_val - 1) + (mkt_val - 1)) / 6 * 100
    return round(min(max(raw + 5, 0), 100))


def calc_retention_risk(transfer_val: int, draft_val: int) -> int:
    """
    Risk score 0–100. Higher = more likely to leave.
    Used as inverse weight in overall score.
    """
    raw = (transfer_val + draft_val) / 4 * 100
    return round(min(max(raw, 0), 100))


def calc_overall_score(ath: int, soc: int, mkt: int, risk: int) -> int:
    """
    Weighted composite using config weights.
    Retention is used inverted — low risk = good.
    """
    return round(
        ath  * WEIGHTS["athletic"]  +
        soc  * WEIGHTS["social"]    +
        mkt  * WEIGHTS["market"]    +
        (100 - risk) * WEIGHTS["retention"]
    )


# ─────────────────────────────────────────────────────────────────────────────
# NIL VALUATION
# ─────────────────────────────────────────────────────────────────────────────

def _recruit_multiplier(recruit_rank: int) -> float:
    if recruit_rank <= 0:
        return RECRUIT_MULTIPLIERS["unranked"]
    if recruit_rank <= 10:
        return RECRUIT_MULTIPLIERS["top10"]
    if recruit_rank <= 30:
        return RECRUIT_MULTIPLIERS["top30"]
    if recruit_rank <= 100:
        return RECRUIT_MULTIPLIERS["top100"]
    return RECRUIT_MULTIPLIERS["top300"]


def _draft_multiplier(draft_round: int) -> float:
    return DRAFT_MULTIPLIERS.get(int(draft_round), 1.0)


def calc_nil_range(ath: int, soc: int, mkt: int, risk: int,
                   recruit_rank: int = 0, draft_round: int = 0) -> tuple[int, int]:
    """
    Returns (nil_low, nil_high) as integer dollar amounts.

    Base scale produces realistic D1 ranges:
      Entry level:  $1–3K
      Developing:   $4–12K
      High Value:   $12–80K
      Elite:        $50–200K
      Blue Chip:    $300K–$2M+

    Blue chip multipliers activate for top-30 recruits or lottery picks.
    """
    base = (ath * WEIGHTS["athletic"] +
            soc * WEIGHTS["social"]   +
            mkt * WEIGHTS["market"])  * (1 - risk / 200)

    lo = max(1000, round(
        (math.exp(base / NIL_EXP_DIVISOR) - 1) * NIL_BASE_SCALE / 1000
    ) * 1000)

    r_mult = _recruit_multiplier(recruit_rank)
    d_mult = _draft_multiplier(draft_round)
    primary   = max(r_mult, d_mult)
    secondary = min(r_mult, d_mult)
    combined  = 1 + (primary - 1) + (secondary - 1) * 0.35

    lo = round(lo * combined / 1000) * 1000
    hi = round(lo * NIL_HI_MULT / 1000) * 1000
    return lo, hi


def nil_expected(lo: int, hi: int) -> int:
    """Mid-point expected value estimate."""
    return round((lo + hi) / 2 / 1000) * 1000


# ─────────────────────────────────────────────────────────────────────────────
# TIER & RECOMMENDATION
# ─────────────────────────────────────────────────────────────────────────────

def calc_tier(overall: int, recruit_rank: int = 0, draft_round: int = 0) -> str:
    if (0 < recruit_rank <= 30) or draft_round == 1:
        return "Blue Chip"
    if overall >= 80:
        return "Elite"
    if overall >= 60:
        return "High Value"
    if overall >= 40:
        return "Developing"
    return "Entry Level"


def calc_recommendation(tier: str, transfer_val: int, draft_val: int,
                         overall: int) -> str:
    """
    Auto-generate a single primary recommendation for the AD:
      - Retain
      - Increase Investment
      - Monitor
      - High Transfer Risk
      - Draft Risk
    """
    if transfer_val == 2:
        return "High Transfer Risk"
    if draft_val == 1:
        return "Draft Risk"
    if tier in ("Blue Chip", "Elite"):
        return "Increase Investment"
    if tier == "High Value":
        return "Retain"
    if transfer_val == 1 or overall < 45:
        return "Monitor"
    return "Retain"


# ─────────────────────────────────────────────────────────────────────────────
# MAIN SCORER — takes a dict, returns a dict
# ─────────────────────────────────────────────────────────────────────────────

def score_athlete(p: dict) -> dict:
    """
    Master function. Accepts a player dict, returns the same dict
    enriched with all scores, tier, NIL range, and recommendation.

    Input keys (all optional with sensible defaults):
        games, starts, stars, awards_val, conf_val
        ig, tt, xf, eng
        mSize, mTV, mMkt
        rTransfer, rDraft
        recruit_rank, draft_round
    """
    ath  = calc_athletic_score(
        p.get("games", 10), p.get("starts", 8),
        p.get("stars", 3),  p.get("awards_val", 0), p.get("conf_val", 1)
    )
    soc  = calc_social_score(
        p.get("ig", 0), p.get("tt", 0), p.get("xf", 0), p.get("eng", 2.0)
    )
    mkt  = calc_market_score(
        p.get("mSize", 2), p.get("mTV", 2), p.get("mMkt", 2)
    )
    risk = calc_retention_risk(p.get("rTransfer", 0), p.get("rDraft", 0))
    ovr  = calc_overall_score(ath, soc, mkt, risk)

    rrank  = p.get("recruit_rank", 0)
    dround = p.get("draft_round", 0)

    lo, hi = calc_nil_range(ath, soc, mkt, risk, rrank, dround)
    exp    = nil_expected(lo, hi)
    tier   = calc_tier(ovr, rrank, dround)
    rec    = calc_recommendation(tier, p.get("rTransfer", 0),
                                  p.get("rDraft", 0), ovr)

    return {
        **p,
        "ath": ath, "soc": soc, "mkt": mkt, "risk": risk,
        "overall": ovr,
        "nil_lo": lo, "nil_exp": exp, "nil_hi": hi,
        "tier": tier,
        "recommendation": rec,
        "cap_pct": round(hi / HOUSE_CAP * 100, 3),
    }


# ─────────────────────────────────────────────────────────────────────────────
# LABEL HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def rank_label(r: int) -> str:
    if r <= 0:      return "Unranked"
    if r <= 10:     return f"Top 10 (#{r})"
    if r <= 30:     return f"Top 30 (#{r})"
    if r <= 100:    return f"Top 100 (#{r})"
    return f"Top 300 (#{r})"


def draft_label(d: int) -> str:
    return ["Not projected", "Lottery pick (1–14)",
            "Late 1st round (15–30)", "2nd round"][min(d, 3)]
