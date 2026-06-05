# app.py — RosterIQ main entry point
# Thin UI layer only — all logic lives in modules/

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import sys, os

sys.path.insert(0, os.path.dirname(__file__))

from config.settings import (
    APP_NAME, APP_VERSION, CONF_TIER_MAP, AWARD_MAP, SIZE_MAP, TV_MAP,
    MKT_MAP, TRANSFER_MAP, DRAFT_RISK_MAP, RECRUIT_MAP, HOUSE_CAP, SPORTS, YEARS
)
from modules.engine import score_athlete, rank_label, draft_label
from modules.database import init_db, get_session, Athlete, AthleteScore, db_mode
from data.seeder import get_scored_sample, seed_database, export_csv_template
from reports.pdf_report import build_player_pdf, build_roster_pdf

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title=f"{APP_NAME} — Athlete Value Intelligence",
    page_icon="🏆", layout="wide", initial_sidebar_state="expanded",
)

st.markdown("""
<style>
  .main .block-container{padding-top:1.5rem;padding-bottom:2rem}
  .tier-blue  {background:#f3e8ff;color:#6b21a8;padding:3px 10px;border-radius:99px;font-weight:600;font-size:12px}
  .tier-elite {background:#d1fae5;color:#065f46;padding:3px 10px;border-radius:99px;font-weight:600;font-size:12px}
  .tier-high  {background:#dbeafe;color:#1e40af;padding:3px 10px;border-radius:99px;font-weight:600;font-size:12px}
  .tier-dev   {background:#fef3c7;color:#92400e;padding:3px 10px;border-radius:99px;font-weight:600;font-size:12px}
  .tier-entry {background:#fee2e2;color:#991b1b;padding:3px 10px;border-radius:99px;font-weight:600;font-size:12px}
  .rec-green  {background:#d1fae5;color:#065f46;padding:3px 10px;border-radius:99px;font-size:12px}
  .rec-blue   {background:#dbeafe;color:#1e40af;padding:3px 10px;border-radius:99px;font-size:12px}
  .rec-amber  {background:#fef3c7;color:#92400e;padding:3px 10px;border-radius:99px;font-size:12px}
  .rec-red    {background:#fee2e2;color:#991b1b;padding:3px 10px;border-radius:99px;font-size:12px}
</style>
""", unsafe_allow_html=True)

TIER_HTML = {
    "Blue Chip":   '<span class="tier-blue">💎 Blue Chip</span>',
    "Elite":       '<span class="tier-elite">🏆 Elite</span>',
    "High Value":  '<span class="tier-high">⭐ High Value</span>',
    "Developing":  '<span class="tier-dev">📈 Developing</span>',
    "Entry Level": '<span class="tier-entry">🌱 Entry Level</span>',
}
REC_HTML = {
    "Increase Investment": '<span class="rec-green">💰 Increase Investment</span>',
    "Retain":              '<span class="rec-blue">✅ Retain</span>',
    "Monitor":             '<span class="rec-amber">👁 Monitor</span>',
    "High Transfer Risk":  '<span class="rec-red">🚨 High Transfer Risk</span>',
    "Draft Risk":          '<span class="rec-amber">⚠️ Draft Risk</span>',
}

# ─────────────────────────────────────────────────────────────────────────────
# DATABASE INIT
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_resource
def initialize():
    try:
        init_db()
        seed_database()
        return True, db_mode()
    except Exception as e:
        return False, str(e)

db_ok, db_info = initialize()

# ─────────────────────────────────────────────────────────────────────────────
# DATA LOADING
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=60)
def load_roster_from_db() -> list[dict]:
    """Load all athletes + latest scores from DB."""
    try:
        session = get_session()
        athletes = session.query(Athlete).filter_by(is_active=True).all()
        result = []
        for a in athletes:
            latest = (session.query(AthleteScore)
                      .filter_by(athlete_id=a.id)
                      .order_by(AthleteScore.scored_at.desc())
                      .first())
            if latest:
                result.append({
                    "name": a.name, "school": a.school, "sport": a.sport,
                    "pos": a.position, "year": a.year,
                    "overall": latest.overall_score, "ath": latest.athletic_score,
                    "soc": latest.social_score, "mkt": latest.market_score,
                    "risk": latest.retention_risk, "tier": latest.tier,
                    "nil_lo": latest.nil_low, "nil_hi": latest.nil_high,
                    "recommendation": latest.recommendation,
                    "injury_history": a.injury_history,
                    "eligibility_remaining": a.eligibility_remaining,
                    "ig": a.ig_followers, "tt": a.tt_followers,
                    "xf": a.x_followers, "eng": a.engagement_pct,
                    "rTransfer": TRANSFER_MAP.get(a.transfer_risk, 0),
                    "recruit_rank": RECRUIT_MAP.get(a.national_recruit_rank, 0),
                    "draft_round": DRAFT_RISK_MAP.get(a.draft_projection, 0),
                    "stars": a.recruiting_stars,
                    "games": a.games_played, "starts": a.starts,
                })
        session.close()
        return result
    except Exception:
        return get_scored_sample()


def load_roster() -> list[dict]:
    if db_ok:
        return load_roster_from_db()
    return get_scored_sample()


def csv_row_to_player(row) -> dict:
    def si(v, d=0):
        try: return int(float(v))
        except: return d
    def sf(v, d=0.0):
        try: return float(v)
        except: return d
    return {
        "name":       str(row.get("name","Athlete")),
        "school":     str(row.get("school","")),
        "sport":      str(row.get("sport","")),
        "pos":        str(row.get("position","")),
        "year":       str(row.get("year","")),
        "games":      si(row.get("games",10)),
        "starts":     si(row.get("starts",8)),
        "stars":      si(row.get("stars",3)),
        "awards_val": AWARD_MAP.get(str(row.get("awards","None")), 0),
        "conf_val":   CONF_TIER_MAP.get(str(row.get("conference","Mid-Major")), 2),
        "ig":         si(row.get("ig_followers",0)),
        "tt":         si(row.get("tiktok_followers",0)),
        "xf":         si(row.get("twitter_followers",0)),
        "eng":        sf(row.get("engagement_pct",2.0)),
        "mSize":      SIZE_MAP.get(str(row.get("school_size","8,000–20,000")), 2),
        "mTV":        TV_MAP.get(str(row.get("tv_exposure","Regional network")), 2),
        "mMkt":       MKT_MAP.get(str(row.get("market_size","Mid-size market")), 2),
        "rTransfer":  TRANSFER_MAP.get(str(row.get("transfer_risk","Low — committed")), 0),
        "rDraft":     DRAFT_RISK_MAP.get(str(row.get("draft_risk","0 — Not projected")), 0),
        "recruit_rank": RECRUIT_MAP.get(str(row.get("national_recruiting_rank","Unranked")), 0),
        "draft_round":  DRAFT_RISK_MAP.get(str(row.get("draft_projection","0 — Not projected")), 0),
        "injury_history": str(row.get("injury_history","None")),
        "eligibility_remaining": si(row.get("eligibility_remaining",2)),
        "conference":  str(row.get("conference","")),
        "school_size": str(row.get("school_size","")),
        "tv_exposure": str(row.get("tv_exposure","")),
        "market_size": str(row.get("market_size","")),
        "transfer_risk": str(row.get("transfer_risk","Low — committed")),
        "draft_risk":    str(row.get("draft_risk","0 — Not projected")),
        "national_recruit_rank": str(row.get("national_recruiting_rank","Unranked")),
        "draft_projection": str(row.get("draft_projection","0 — Not projected")),
    }

# ─────────────────────────────────────────────────────────────────────────────
# CHARTS
# ─────────────────────────────────────────────────────────────────────────────

def radar_chart(p):
    cats   = ["Athletic","Social","Market","Retention\n(inv)"]
    values = [p["ath"], p["soc"], p["mkt"], 100-p["risk"]]
    fig = go.Figure(go.Scatterpolar(
        r=values+[values[0]], theta=cats+[cats[0]],
        fill="toself", fillcolor="rgba(55,138,221,0.15)",
        line=dict(color="#185FA5",width=2), marker=dict(color="#185FA5",size=6),
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True,range=[0,100],tickfont=dict(size=9))),
        showlegend=False, margin=dict(l=30,r=30,t=30,b=30), height=280,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig

CMAP = {"Blue Chip":"#7c3aed","Elite":"#059669","High Value":"#2563eb",
        "Developing":"#d97706","Entry Level":"#dc2626"}

def roster_bar(df):
    df_s = df.sort_values("overall",ascending=True)
    fig = go.Figure(go.Bar(
        x=df_s["overall"], y=df_s["name"], orientation="h",
        marker_color=[CMAP.get(t,"#888") for t in df_s["tier"]],
        text=[f"{v}/100" for v in df_s["overall"]], textposition="outside",
    ))
    fig.update_layout(
        xaxis=dict(range=[0,115],title="Overall Score"), yaxis=dict(title=""),
        height=max(300,len(df_s)*34), margin=dict(l=10,r=60,t=10,b=30),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig

def nil_chart(df):
    df_s = df.sort_values("nil_hi",ascending=False).head(20)
    fig = go.Figure()
    for _, r in df_s.iterrows():
        c = CMAP.get(r["tier"],"#185FA5")
        fig.add_trace(go.Scatter(
            x=[r["nil_lo"],r["nil_hi"]], y=[r["name"],r["name"]],
            mode="lines+markers", line=dict(width=5,color=c),
            marker=dict(size=9,color=[c,c]),
            name=r["name"], showlegend=False,
        ))
    fig.update_layout(
        xaxis=dict(title="Estimated NIL Value ($)",tickformat="$,.0f"),
        yaxis=dict(autorange="reversed"),
        height=max(300,len(df_s)*40), margin=dict(l=10,r=20,t=10,b=30),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig

def scatter_chart(df):
    fig = px.scatter(
        df, x="soc", y="ath", size="overall", color="tier",
        hover_name="name",
        hover_data={"nil_hi":True,"mkt":True,"soc":False,"ath":False,"tier":False},
        color_discrete_map=CMAP,
        labels={"soc":"Social Score","ath":"Athletic Score","nil_hi":"NIL High","mkt":"Market Score"},
        size_max=28,
    )
    fig.update_layout(
        height=380, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h",yanchor="bottom",y=1.02),
    )
    return fig

def sport_bar(df):
    sport_df = (df.groupby("sport")
                  .agg(avg_score=("overall","mean"),
                       count=("name","count"),
                       total_nil=("nil_hi","sum"))
                  .reset_index()
                  .sort_values("avg_score",ascending=False))
    fig = px.bar(sport_df, x="sport", y="avg_score",
                 text=[f"{v:.0f}" for v in sport_df["avg_score"]],
                 color="avg_score", color_continuous_scale="Blues",
                 labels={"avg_score":"Avg Score","sport":"Sport"})
    fig.update_layout(
        height=280, showlegend=False, coloraxis_showscale=False,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10,r=10,t=10,b=30),
    )
    return fig

# ─────────────────────────────────────────────────────────────────────────────
# PLAYER REPORT VIEW
# ─────────────────────────────────────────────────────────────────────────────

def show_player_report(p):
    st.markdown(
        f"## {p['name']}  {TIER_HTML.get(p['tier'],'')}  {REC_HTML.get(p.get('recommendation',''),'')}",
        unsafe_allow_html=True
    )
    st.caption(f"{p.get('pos','')} · {p.get('sport','')} · {p.get('year','')} · {p.get('school','')}")

    if p["tier"] == "Blue Chip":
        st.info(f"💎 **Blue Chip** — Recruiting: {rank_label(p.get('recruit_rank',0))} · Draft: {draft_label(p.get('draft_round',0))}")

    st.markdown("---")
    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Overall",     f"{p['overall']}/100")
    c2.metric("Athletic",    f"{p['ath']}/100")
    c3.metric("Social",      f"{p['soc']}/100")
    c4.metric("Market",      f"{p['mkt']}/100")
    c5.metric("Ret. Risk",   f"{p['risk']}/100", delta="lower is better", delta_color="inverse")

    exp = (p["nil_lo"] + p["nil_hi"]) // 2
    st.markdown(f"### 💰 NIL Estimate: `${p['nil_lo']:,}` — `${exp:,}` — `${p['nil_hi']:,}` / year")
    cap_pct = p["nil_hi"] / HOUSE_CAP * 100
    st.caption(f"Low · Expected · High  ·  ~{cap_pct:.2f}% of $20.5M House cap  ·  Fair-market floor")

    col_r, col_i = st.columns([1,1])
    with col_r:
        st.plotly_chart(radar_chart(p), use_container_width=True)
    with col_i:
        st.markdown("**Insights**")
        total_soc  = p.get("ig",0)+p.get("tt",0)+p.get("xf",0)
        start_rate = round(p.get("starts",0)/max(p.get("games",1),1)*100)
        rows = [
            ("Recruiting",       rank_label(p.get("recruit_rank",0))),
            ("Draft",            draft_label(p.get("draft_round",0))),
            ("Social Reach",     f"{total_soc:,} · {p.get('eng',0):.1f}% eng."),
            ("Start Rate",       f"{start_rate}%"),
            ("Eligibility Left", f"{p.get('eligibility_remaining','?')} year(s)"),
            ("Injury History",   p.get("injury_history","None")),
            ("Transfer Risk",    ["Low ✅","Medium ⚠️","High 🚨"][p.get("rTransfer",0)]),
            ("Recommendation",   p.get("recommendation","—")),
        ]
        for label, val in rows:
            st.markdown(f"**{label}:** {val}")

    st.markdown("---")
    pdf = build_player_pdf(p)
    st.download_button("⬇️ Download PDF Report", data=pdf,
                       file_name=f"RosterIQ_{p['name'].replace(' ','_')}.pdf",
                       mime="application/pdf", use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# EXECUTIVE DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────

def show_executive_dashboard(athletes: list[dict]):
    df = pd.DataFrame(athletes)
    st.markdown("## 📊 Executive Dashboard")

    # KPI row
    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Total Athletes",       len(df))
    c2.metric("Avg Overall Score",    f"{df['overall'].mean():.1f}")
    c3.metric("Blue Chip / Elite",    len(df[df["tier"].isin(["Blue Chip","Elite"])]))
    c4.metric("High Transfer Risk",   len(df[df["rTransfer"]==2]) if "rTransfer" in df else "—")
    c5.metric("Total NIL Est. (high)",f"${df['nil_hi'].sum():,.0f}")

    # High-risk alert panel
    high_risk = [a for a in athletes if a.get("rTransfer",0)==2]
    if high_risk:
        st.warning(f"🚨 **{len(high_risk)} athlete(s) flagged as High Transfer Risk** — immediate NIL conversation recommended")
        for a in high_risk:
            st.markdown(f"- **{a['name']}** ({a.get('sport','')} · {a.get('school','')}) — Overall: {a['overall']}/100")

    tabs = st.tabs(["📊 Rankings","🎯 NIL Ranges","🔬 Athletic vs Social","⚽ By Sport","📄 Full Roster"])

    with tabs[0]:
        st.plotly_chart(roster_bar(df), use_container_width=True)
    with tabs[1]:
        st.plotly_chart(nil_chart(df), use_container_width=True)
    with tabs[2]:
        st.plotly_chart(scatter_chart(df), use_container_width=True)
        st.caption("Bubble size = overall score · Purple = Blue Chip · Hover for details")
    with tabs[3]:
        st.plotly_chart(sport_bar(df), use_container_width=True)
        sport_summary = (df.groupby("sport")
                           .agg(Athletes=("name","count"),
                                Avg_Score=("overall","mean"),
                                Total_NIL_High=("nil_hi","sum"))
                           .reset_index()
                           .sort_values("Avg_Score",ascending=False))
        sport_summary["Avg_Score"]       = sport_summary["Avg_Score"].apply(lambda x: f"{x:.1f}")
        sport_summary["Total_NIL_High"]  = sport_summary["Total_NIL_High"].apply(lambda x: f"${x:,.0f}")
        sport_summary.columns = ["Sport","Athletes","Avg Score","Total NIL (high)"]
        st.dataframe(sport_summary, use_container_width=True, hide_index=True)
    with tabs[4]:
        disp = df[["name","school","sport","tier","overall","ath","soc","mkt","risk","nil_lo","nil_hi","recommendation"]].copy()
        disp.columns = ["Name","School","Sport","Tier","Overall","Athletic","Social","Market","Risk","NIL Low","NIL High","Rec."]
        disp["NIL Low"]  = disp["NIL Low"].apply(lambda x: f"${x:,}")
        disp["NIL High"] = disp["NIL High"].apply(lambda x: f"${x:,}")
        st.dataframe(disp.sort_values("Overall",ascending=False), use_container_width=True, hide_index=True)

        c1,c2 = st.columns(2)
        with c1:
            st.download_button("⬇️ Export CSV", df.to_csv(index=False).encode(),
                               "rosteriq_export.csv","text/csv",use_container_width=True)
        with c2:
            roster_pdf = build_roster_pdf(athletes)
            st.download_button("⬇️ Download Roster PDF", data=roster_pdf,
                               file_name="RosterIQ_Roster_Report.pdf",
                               mime="application/pdf", use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# MANUAL PLAYER FORM
# ─────────────────────────────────────────────────────────────────────────────

def player_form():
    with st.form("player_form"):
        c1,c2,c3 = st.columns(3)
        with c1:
            name   = st.text_input("Player Name","Marcus Hill")
            school = st.text_input("School","Univ. of Missouri")
            sport  = st.selectbox("Sport", SPORTS)
        with c2:
            pos    = st.text_input("Position","WR")
            year   = st.selectbox("Year", YEARS)
            conf   = st.selectbox("Conference Tier", list(CONF_TIER_MAP.keys()))
        with c3:
            games  = st.number_input("Games Played",0,82,12)
            starts = st.number_input("Starts",0,82,10)
            stars  = st.slider("Recruiting Stars",1,5,4)
            injury = st.text_input("Injury History","None")
            elig   = st.number_input("Eligibility Remaining (yrs)",0,5,2)

        st.markdown("---")
        c4,c5,c6 = st.columns(3)
        with c4:
            st.markdown("**Athletic**")
            awards = st.selectbox("Awards", list(AWARD_MAP.keys()))
        with c5:
            st.markdown("**Social Media**")
            ig  = st.number_input("Instagram",0,value=18000,step=500)
            tt  = st.number_input("TikTok",   0,value=25000,step=500)
            xf  = st.number_input("Twitter/X",0,value=4500, step=500)
            eng = st.number_input("Engagement %",0.0,100.0,5.2,step=0.1)
        with c6:
            st.markdown("**Market & Risk**")
            mSize     = st.selectbox("School Enrollment",    list(SIZE_MAP.keys()))
            mTV       = st.selectbox("TV/Streaming Exposure",list(TV_MAP.keys()))
            mMkt      = st.selectbox("Local Market Size",    list(MKT_MAP.keys()))
            rTransfer = st.selectbox("Transfer Risk",        list(TRANSFER_MAP.keys()))
            rDraft    = st.selectbox("Draft Eligibility",    list(DRAFT_RISK_MAP.keys()))

        st.markdown("---")
        st.markdown("**💎 Blue Chip Factors** — leave at defaults if not applicable")
        bc1,bc2 = st.columns(2)
        with bc1:
            recruit_rank_lbl = st.selectbox("National Recruiting Rank", list(RECRUIT_MAP.keys()))
        with bc2:
            draft_proj_lbl   = st.selectbox("Draft Projection", list(DRAFT_RISK_MAP.keys()))

        submitted = st.form_submit_button("📊 Calculate Value", use_container_width=True)

    if submitted:
        return {
            "name":name,"school":school,"sport":sport,"pos":pos,"year":year,
            "games":games,"starts":starts,"stars":stars,
            "awards_val":AWARD_MAP[awards],"conf_val":CONF_TIER_MAP[conf],
            "ig":ig,"tt":tt,"xf":xf,"eng":eng,
            "mSize":SIZE_MAP[mSize],"mTV":TV_MAP[mTV],"mMkt":MKT_MAP[mMkt],
            "rTransfer":TRANSFER_MAP[rTransfer],
            "rDraft":DRAFT_RISK_MAP[rDraft],
            "recruit_rank": RECRUIT_MAP[recruit_rank_lbl],
            "draft_round":  DRAFT_RISK_MAP[draft_proj_lbl],
            "injury_history": injury,
            "eligibility_remaining": elig,
            "conference": conf,
            "school_size": mSize, "tv_exposure": mTV, "market_size": mMkt,
            "transfer_risk": rTransfer, "draft_risk": rDraft,
            "national_recruit_rank": recruit_rank_lbl,
            "draft_projection": draft_proj_lbl,
        }
    return None

# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    with st.sidebar:
        st.markdown(f"## 🏆 {APP_NAME}")
        st.caption(f"v{APP_VERSION} · Athlete Value Intelligence")
        st.markdown("---")
        mode = st.radio("View", [
            "🏠 Executive Dashboard",
            "👤 Single Player",
            "📋 Roster CSV Upload",
        ], label_visibility="collapsed")

        st.markdown("---")
        db_label = "🟢 PostgreSQL" if "postgresql" in db_info else "🟡 SQLite (local)"
        st.caption(f"DB: {db_label}")
        st.caption(
            "Decision-support platform for athletic departments and NIL collectives. "
            "Estimates athlete value, transfer risk, and recommended compensation — "
            "aligned with the $20.5M House settlement cap."
        )
        st.markdown("---")
        st.caption("For internal AD use only · Not for public distribution")

    if mode == "🏠 Executive Dashboard":
        athletes = load_roster()
        show_executive_dashboard(athletes)

        st.markdown("---")
        st.markdown("### Individual Player Reports")
        sorted_athletes = sorted(athletes, key=lambda x: x.get("overall",0), reverse=True)
        for a in sorted_athletes:
            with st.expander(f"{a['name']} — {a['tier']} ({a['overall']}/100) · {a.get('sport','')} · {a.get('school','')}"):
                show_player_report(a)

    elif mode == "👤 Single Player":
        st.title(f"🏆 {APP_NAME} — Player Valuation")
        player_input = player_form()
        if player_input:
            p = score_athlete(player_input)
            st.markdown("---")
            show_player_report(p)

    else:
        st.title(f"🏆 {APP_NAME} — Roster Upload")
        c1,c2 = st.columns([1,2])
        with c1:
            # Generate CSV from the 50-athlete sample
            import io as _io
            scored = get_scored_sample()
            rows = []
            for p in scored:
                rows.append({
                    "name": p["name"], "school": p["school"], "sport": p["sport"],
                    "position": p.get("pos",""), "year": p.get("year",""),
                    "games": p.get("games",0), "starts": p.get("starts",0),
                    "stars": p.get("stars",3),
                    "awards": {0:"None",1:"Team Award",2:"Conference Award",
                               3:"All-American / National"}.get(p.get("awards_val",0),"None"),
                    "conference": p.get("conference",""),
                    "ig_followers": p.get("ig",0), "tiktok_followers": p.get("tt",0),
                    "twitter_followers": p.get("xf",0), "engagement_pct": p.get("eng",2.0),
                    "school_size": p.get("school_size",""), "tv_exposure": p.get("tv_exposure",""),
                    "market_size": p.get("market_size",""),
                    "transfer_risk": p.get("transfer_risk","Low — committed"),
                    "draft_risk": p.get("draft_risk","0 — Not projected"),
                    "national_recruiting_rank": p.get("national_recruit_rank","Unranked"),
                    "draft_projection": p.get("draft_projection","0 — Not projected"),
                    "injury_history": p.get("injury_history","None"),
                    "eligibility_remaining": p.get("eligibility_remaining",2),
                })
            csv_bytes = pd.DataFrame(rows).to_csv(index=False).encode()
            st.download_button("⬇️ Download 50-Athlete Template",
                               data=csv_bytes, file_name="rosteriq_50_athletes.csv",
                               mime="text/csv")
        with c2:
            uploaded = st.file_uploader("Upload Roster CSV", type=["csv"])

        if uploaded:
            try:
                df_raw = pd.read_csv(uploaded)
                df_raw.columns = [c.strip().lower().replace(" ","_") for c in df_raw.columns]
                players = [csv_row_to_player(row) for _, row in df_raw.iterrows()]
                scored  = [score_athlete(p) for p in players]
                show_executive_dashboard(scored)
                st.markdown("---")
                st.markdown("### Individual Reports")
                for p in sorted(scored, key=lambda x: x.get("overall",0), reverse=True):
                    with st.expander(f"{p['name']} — {p['tier']} ({p['overall']}/100) · ${p['nil_lo']:,}–${p['nil_hi']:,}"):
                        show_player_report(p)
            except Exception as e:
                st.error(f"Error: {e}. Use the 50-athlete template as a format reference.")
        else:
            st.info("👆 Download the 50-athlete template to see the format, then upload your own roster.")


if __name__ == "__main__":
    main()
