# reports/pdf_report.py
# PDF generation using ReportLab
# Produces individual player reports and roster summary reports

import io
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors as rl_colors
from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                 Paragraph, Spacer, HRFlowable, PageBreak)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from modules.engine import rank_label, draft_label
from config.settings import HOUSE_CAP, APP_NAME, APP_VERSION

# ── Color palette ─────────────────────────────────────────────────────────────
BLUE   = rl_colors.HexColor("#185FA5")
LBLUE  = rl_colors.HexColor("#E6F1FB")
LGRAY  = rl_colors.HexColor("#F1EFE8")
DGRAY  = rl_colors.HexColor("#D3D1C7")
DARK   = rl_colors.HexColor("#1a1a1a")
MID    = rl_colors.HexColor("#555555")
PURP   = rl_colors.HexColor("#6b21a8")
GREEN  = rl_colors.HexColor("#059669")
AMBER  = rl_colors.HexColor("#d97706")
RED    = rl_colors.HexColor("#dc2626")

TIER_COLORS = {
    "Blue Chip":   PURP,
    "Elite":       GREEN,
    "High Value":  BLUE,
    "Developing":  AMBER,
    "Entry Level": RED,
}

REC_COLORS = {
    "Increase Investment": GREEN,
    "Retain":              BLUE,
    "Monitor":             AMBER,
    "High Transfer Risk":  RED,
    "Draft Risk":          PURP,
}


def _header_banner(W):
    banner_data = [[Paragraph(
        f'<font color="white" size="14"><b>{APP_NAME} — Athlete Value Report</b></font><br/>'
        f'<font color="#B5D4F4" size="8">v{APP_VERSION}  ·  Generated {datetime.now().strftime("%B %d, %Y")}  ·  Confidential — For Internal AD Use Only</font>',
        ParagraphStyle("banner", fontSize=14, fontName="Helvetica-Bold",
                       textColor=rl_colors.white, alignment=TA_LEFT)
    )]]
    t = Table(banner_data, colWidths=[W])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), BLUE),
        ("TOPPADDING",    (0,0),(-1,-1), 12),
        ("BOTTOMPADDING", (0,0),(-1,-1), 12),
        ("LEFTPADDING",   (0,0),(-1,-1), 16),
    ]))
    return t


def _footer_note():
    return ParagraphStyle("foot", fontSize=8, textColor=MID, alignment=TA_CENTER)


def build_player_pdf(p: dict) -> bytes:
    """Generate a one-page PDF report for a single athlete."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter,
                            leftMargin=0.75*inch, rightMargin=0.75*inch,
                            topMargin=0.75*inch, bottomMargin=0.75*inch)
    styles = getSampleStyleSheet()
    W = letter[0] - 1.5*inch

    h1   = ParagraphStyle("h1",  fontSize=20, fontName="Helvetica-Bold", textColor=DARK, spaceAfter=2)
    h2   = ParagraphStyle("h2",  fontSize=13, fontName="Helvetica-Bold", textColor=BLUE, spaceBefore=12, spaceAfter=4)
    sub  = ParagraphStyle("sub", fontSize=10, textColor=MID, spaceAfter=6)
    body = ParagraphStyle("body",fontSize=9,  textColor=DARK, leading=14, spaceAfter=4)
    foot = _footer_note()

    story = [_header_banner(W), Spacer(1, 12)]

    # Player name + subheading
    story.append(Paragraph(p.get("name", "Athlete"), h1))
    sub_text = "  ·  ".join(filter(None, [
        p.get("pos",""), p.get("sport",""), p.get("year",""), p.get("school","")
    ]))
    story.append(Paragraph(sub_text, sub))

    # Overview box
    tier_color = TIER_COLORS.get(p.get("tier",""), BLUE)
    rec_color  = REC_COLORS.get(p.get("recommendation",""), BLUE)
    ovr_data = [
        [Paragraph("<b>Overall</b>", body), Paragraph("<b>Tier</b>", body),
         Paragraph("<b>Recommendation</b>", body), Paragraph("<b>Est. NIL / yr</b>", body)],
        [
            Paragraph(f'<font size="16"><b>{p.get("overall",0)}/100</b></font>',
                      ParagraphStyle("big", fontSize=16, fontName="Helvetica-Bold", textColor=BLUE)),
            Paragraph(f'<font size="12"><b>{p.get("tier","")}</b></font>',
                      ParagraphStyle("tier", fontSize=12, fontName="Helvetica-Bold", textColor=tier_color)),
            Paragraph(f'<font size="11"><b>{p.get("recommendation","")}</b></font>',
                      ParagraphStyle("rec", fontSize=11, fontName="Helvetica-Bold", textColor=rec_color)),
            Paragraph(f'<font size="12"><b>${p.get("nil_lo",0):,} – ${p.get("nil_hi",0):,}</b></font>',
                      ParagraphStyle("nil", fontSize=12, fontName="Helvetica-Bold", textColor=BLUE)),
        ],
    ]
    ovr_tbl = Table(ovr_data, colWidths=[W*0.16, W*0.20, W*0.30, W*0.34])
    ovr_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), LBLUE),
        ("GRID",       (0,0), (-1,-1), 0.5, rl_colors.HexColor("#B5D4F4")),
        ("TOPPADDING",    (0,0),(-1,-1), 8),
        ("BOTTOMPADDING", (0,0),(-1,-1), 8),
        ("LEFTPADDING",   (0,0),(-1,-1), 10),
    ]))
    story.append(ovr_tbl)
    story.append(Spacer(1, 12))

    # Score breakdown
    story.append(Paragraph("Score Breakdown", h2))
    score_rows = [
        ["Dimension", "Score", "Weight", "Key Inputs"],
        ["Athletic Performance", str(p.get("ath",0)), "35%", "Stars · Start rate · Awards · Conference"],
        ["Social Media Reach",   str(p.get("soc",0)), "30%", "Followers × engagement (log-scaled)"],
        ["Market Opportunity",   str(p.get("mkt",0)), "25%", "School size · TV exposure · DMA"],
        ["Retention (inverted)", str(100-p.get("risk",0)), "10%", "Transfer risk · Draft eligibility"],
    ]
    s_tbl = Table(score_rows, colWidths=[W*0.28, W*0.10, W*0.10, W*0.52])
    s_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), BLUE), ("TEXTCOLOR", (0,0), (-1,0), rl_colors.white),
        ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"), ("FONTSIZE", (0,0), (-1,-1), 9),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [rl_colors.white, LGRAY]),
        ("GRID",    (0,0), (-1,-1), 0.4, DGRAY),
        ("ALIGN",   (1,0), (2,-1), "CENTER"),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(-1,-1), 8),
    ]))
    story.append(s_tbl)
    story.append(Spacer(1, 12))

    # Insights
    story.append(Paragraph("Key Insights & Compliance Notes", h2))
    total_soc  = p.get("ig",0) + p.get("tt",0) + p.get("xf",0)
    games      = max(p.get("games",1), 1)
    start_rate = round(p.get("starts",0) / games * 100)
    cap_pct    = p.get("nil_hi",0) / HOUSE_CAP * 100
    rrank      = p.get("recruit_rank", 0)
    dround     = p.get("draft_round", 0)

    insights = [
        f"<b>Blue Chip Factors:</b> Recruiting: {rank_label(rrank)} · Draft: {draft_label(dround)}",
        f"<b>Social Reach:</b> {total_soc:,} total followers · {p.get('eng',0):.1f}% avg engagement",
        f"<b>Start Rate:</b> {start_rate}% ({p.get('starts',0)} of {p.get('games',0)} games)",
        f"<b>Injury History:</b> {p.get('injury_history','None')}",
        f"<b>Eligibility Remaining:</b> {p.get('eligibility_remaining','N/A')} year(s)",
        f"<b>Transfer Risk:</b> {['Low','Medium','High'][min(p.get('rTransfer',0),2)]} · {'Immediate NIL conversation recommended' if p.get('rTransfer',0)==2 else 'Engage collective proactively' if p.get('rTransfer',0)==1 else 'Prioritize retention incentives'}",
        f"<b>Rev-Share Context:</b> Estimated NIL high (~${p.get('nil_hi',0):,}) = ~{cap_pct:.2f}% of $20.5M House cap",
        f"<b>Compliance:</b> All NIL agreements must document fair market value with proof of services rendered.",
        f"<b>Note:</b> Estimates reflect fair-market floor. Bidding-war premiums in competitive recruiting may exceed this range.",
    ]
    for ins in insights:
        story.append(Paragraph(f"• {ins}", body))

    # Footer
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width=W, thickness=0.5, color=DGRAY))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        f"{APP_NAME} v{APP_VERSION}  ·  Confidential — For Internal Athletic Department Use Only  ·  Not for public distribution",
        foot
    ))

    doc.build(story)
    return buf.getvalue()


def build_roster_pdf(athletes: list[dict], title: str = "Roster Valuation Report") -> bytes:
    """Generate a multi-page PDF with roster summary + one section per athlete."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter,
                            leftMargin=0.75*inch, rightMargin=0.75*inch,
                            topMargin=0.75*inch, bottomMargin=0.75*inch)
    W = letter[0] - 1.5*inch

    h1   = ParagraphStyle("h1",  fontSize=18, fontName="Helvetica-Bold", textColor=DARK, spaceAfter=4)
    h2   = ParagraphStyle("h2",  fontSize=13, fontName="Helvetica-Bold", textColor=BLUE, spaceBefore=10, spaceAfter=4)
    body = ParagraphStyle("body",fontSize=9,  textColor=DARK, leading=14, spaceAfter=3)
    foot = _footer_note()

    story = [_header_banner(W), Spacer(1, 12)]
    story.append(Paragraph(title, h1))
    story.append(Paragraph(
        f"Generated {datetime.now().strftime('%B %d, %Y')}  ·  {len(athletes)} athletes", 
        ParagraphStyle("sub", fontSize=10, textColor=MID, spaceAfter=12)
    ))

    # Summary stats
    if athletes:
        avg_overall = round(sum(a.get("overall",0) for a in athletes) / len(athletes))
        total_nil   = sum(a.get("nil_hi",0) for a in athletes)
        blue_elite  = sum(1 for a in athletes if a.get("tier") in ("Blue Chip","Elite"))
        high_risk   = sum(1 for a in athletes if a.get("rTransfer",0) == 2)

        summary_data = [
            ["Athletes", "Avg Score", "Elite / Blue Chip", "High Transfer Risk", "Total NIL Est. (high)"],
            [str(len(athletes)), f"{avg_overall}/100", str(blue_elite),
             str(high_risk), f"${total_nil:,.0f}"],
        ]
        s_tbl = Table(summary_data, colWidths=[W*0.12, W*0.16, W*0.20, W*0.22, W*0.30])
        s_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), BLUE),
            ("TEXTCOLOR",  (0,0), (-1,0), rl_colors.white),
            ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",   (0,0), (-1,-1), 9),
            ("BACKGROUND", (0,1), (-1,1), LBLUE),
            ("GRID",       (0,0), (-1,-1), 0.4, DGRAY),
            ("ALIGN",      (0,0), (-1,-1), "CENTER"),
            ("TOPPADDING",    (0,0),(-1,-1), 6),
            ("BOTTOMPADDING", (0,0),(-1,-1), 6),
        ]))
        story.append(s_tbl)
        story.append(Spacer(1, 16))

    # Roster rankings table
    story.append(Paragraph("Roster Rankings", h2))
    sorted_athletes = sorted(athletes, key=lambda x: x.get("overall",0), reverse=True)
    rank_data = [["#", "Name", "School", "Sport", "Tier", "Overall", "NIL Range", "Rec."]]
    for i, a in enumerate(sorted_athletes, 1):
        rank_data.append([
            str(i),
            a.get("name","")[:18],
            a.get("school","")[:16],
            a.get("sport",""),
            a.get("tier",""),
            str(a.get("overall",0)),
            f"${a.get('nil_lo',0)//1000}K–${a.get('nil_hi',0)//1000}K",
            a.get("recommendation","")[:14],
        ])
    r_tbl = Table(rank_data, colWidths=[W*0.04,W*0.16,W*0.14,W*0.10,W*0.12,W*0.08,W*0.16,W*0.20])
    r_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), BLUE),
        ("TEXTCOLOR",     (0,0), (-1,0), rl_colors.white),
        ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 8),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [rl_colors.white, LGRAY]),
        ("GRID",          (0,0), (-1,-1), 0.3, DGRAY),
        ("TOPPADDING",    (0,0),(-1,-1), 4),
        ("BOTTOMPADDING", (0,0),(-1,-1), 4),
        ("LEFTPADDING",   (0,0),(-1,-1), 5),
    ]))
    story.append(r_tbl)

    # Footer on summary page
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width=W, thickness=0.5, color=DGRAY))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        f"{APP_NAME}  ·  Confidential — For Internal Athletic Department Use Only",
        foot
    ))

    doc.build(story)
    return buf.getvalue()
