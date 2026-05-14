"""
Athlete Performance Fueling Plan — PDF Template Generator
Covers all intake form fields: bio stats, sport/schedule, training load,
goals, food preferences, supplements, sleep, and medical background.
"""

from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    KeepTogether, HRFlowable
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus.flowables import Flowable
import math

# ── PALETTE ──────────────────────────────────────────────────────────────────
BLACK      = colors.HexColor("#0a0a0a")
WHITE      = colors.HexColor("#f5f3ee")
GOLD       = colors.HexColor("#c9a84c")
GOLD_LIGHT = colors.HexColor("#e8cc7a")
DARK_GREY  = colors.HexColor("#1a1a1a")
MID_GREY   = colors.HexColor("#2a2a2a")
DIM        = colors.HexColor("#888888")
GREEN      = colors.HexColor("#4caf7a")
RED        = colors.HexColor("#e05555")

PAGE_W, PAGE_H = letter
MARGIN_SIDE = 1.0 * inch
MARGIN_TB   = 0.5 * inch
CONTENT_W   = PAGE_W - 2 * MARGIN_SIDE

# ── STYLES ───────────────────────────────────────────────────────────────────
def make_styles():
    base = lambda name, **kw: ParagraphStyle(name, **kw)
    return {
        "name_hero": base("name_hero",
            fontName="Helvetica-Bold", fontSize=28,
            textColor=WHITE, leading=30, spaceAfter=2),
        "subtitle": base("subtitle",
            fontName="Helvetica", fontSize=11,
            textColor=GOLD, leading=14, spaceAfter=0),
        "section_label": base("section_label",
            fontName="Helvetica-Bold", fontSize=8,
            textColor=GOLD, leading=10, spaceAfter=4,
            letterSpacing=1.5),
        "section_title": base("section_title",
            fontName="Helvetica-Bold", fontSize=17,
            textColor=WHITE, leading=20, spaceBefore=12, spaceAfter=6),
        "body": base("body",
            fontName="Helvetica", fontSize=11,
            textColor=WHITE, leading=15, spaceAfter=4),
        "body_dim": base("body_dim",
            fontName="Helvetica", fontSize=10,
            textColor=DIM, leading=14, spaceAfter=3),
        "card_title": base("card_title",
            fontName="Helvetica-Bold", fontSize=12,
            textColor=WHITE, leading=15, spaceAfter=2),
        "card_time": base("card_time",
            fontName="Helvetica-Bold", fontSize=10,
            textColor=GOLD, leading=12, spaceAfter=1),
        "card_macros": base("card_macros",
            fontName="Helvetica", fontSize=9,
            textColor=DIM, leading=12, spaceAfter=4),
        "bullet": base("bullet",
            fontName="Helvetica", fontSize=10,
            textColor=WHITE, leading=14, spaceAfter=1,
            leftIndent=10, firstLineIndent=-10),
        "bullet_dim": base("bullet_dim",
            fontName="Helvetica", fontSize=10,
            textColor=DIM, leading=14, spaceAfter=1,
            leftIndent=10, firstLineIndent=-10),
        "supp_name": base("supp_name",
            fontName="Helvetica-Bold", fontSize=12,
            textColor=WHITE, leading=15, spaceAfter=2),
        "supp_evidence": base("supp_evidence",
            fontName="Helvetica-Bold", fontSize=9,
            textColor=GOLD, leading=11, spaceAfter=3),
        "notice": base("notice",
            fontName="Helvetica", fontSize=8.5,
            textColor=DIM, leading=12, spaceAfter=3),
        "stat_val": base("stat_val",
            fontName="Helvetica-Bold", fontSize=20,
            textColor=WHITE, leading=22, alignment=TA_CENTER),
        "stat_label": base("stat_label",
            fontName="Helvetica", fontSize=8,
            textColor=GOLD, leading=10, alignment=TA_CENTER,
            letterSpacing=0.8),
        "table_header": base("table_header",
            fontName="Helvetica-Bold", fontSize=8.5,
            textColor=GOLD, leading=11, alignment=TA_CENTER),
        "table_cell": base("table_cell",
            fontName="Helvetica", fontSize=9,
            textColor=WHITE, leading=12, alignment=TA_LEFT),
        "table_cell_c": base("table_cell_c",
            fontName="Helvetica", fontSize=9,
            textColor=WHITE, leading=12, alignment=TA_CENTER),
        "goal_tag": base("goal_tag",
            fontName="Helvetica-Bold", fontSize=10,
            textColor=BLACK, leading=12, alignment=TA_CENTER),
    }

S = make_styles()

# ── HELPERS ──────────────────────────────────────────────────────────────────
class GoldLine(Flowable):
    def __init__(self, width=CONTENT_W, thickness=1.5):
        Flowable.__init__(self)
        self.width = width
        self.thickness = thickness
    def draw(self):
        self.canv.setStrokeColor(GOLD)
        self.canv.setLineWidth(self.thickness)
        self.canv.line(0, 0, self.width, 0)

def section_header(label, title):
    return [
        Spacer(1, 18),
        Paragraph(label.upper(), S["section_label"]),
        Paragraph(title, S["section_title"]),
        GoldLine(CONTENT_W, 0.5),
        Spacer(1, 10),
    ]

def bullet(text, dim=False):
    style = S["bullet_dim"] if dim else S["bullet"]
    return Paragraph(f"&bull;  {text}", style)

def do_bullets(items, dim=False):
    return [bullet(i, dim) for i in items]

def meal_card(time, title, macros, items):
    """Renders a single meal card as a bordered table cell."""
    inner = [
        Paragraph(time, S["card_time"]),
        Paragraph(title, S["card_title"]),
        Paragraph(macros, S["card_macros"]),
    ] + [Paragraph(f"&bull;  {i}", S["bullet"]) for i in items]

    inner_table = Table([[inner]], colWidths=[CONTENT_W - 32])
    inner_table.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,-1), DARK_GREY),
        ("LEFTPADDING",  (0,0), (-1,-1), 14),
        ("RIGHTPADDING", (0,0), (-1,-1), 14),
        ("TOPPADDING",   (0,0), (-1,-1), 12),
        ("BOTTOMPADDING",(0,0), (-1,-1), 12),
        ("LINEBELOW",    (0,0), (-1,-1), 1, GOLD),
        ("LINEABOVE",    (0,0), (0,0),  0.5, MID_GREY),
        ("LINEBEFORE",   (0,0), (-1,-1), 0.5, MID_GREY),
        ("LINEAFTER",    (0,0), (-1,-1), 0.5, MID_GREY),
    ]))
    return KeepTogether(inner_table)

def supplement_card(name, evidence, dose, timing, description):
    badge_color = GREEN if "STRONG" in evidence else GOLD if "GOOD" in evidence else DIM
    inner = [
        Table(
            [[Paragraph(name, S["supp_name"]),
              Paragraph(evidence, ParagraphStyle("ev",
                  fontName="Helvetica-Bold", fontSize=8,
                  textColor=BLACK, leading=10, alignment=TA_CENTER))]],
            colWidths=[CONTENT_W - 180, 110],
            style=TableStyle([
                ("BACKGROUND",   (1,0),(1,0), badge_color),
                ("LEFTPADDING",  (0,0),(-1,-1), 0),
                ("RIGHTPADDING", (0,0),(-1,-1), 4),
                ("TOPPADDING",   (0,0),(-1,-1), 0),
                ("BOTTOMPADDING",(0,0),(-1,-1), 4),
                ("VALIGN",       (0,0),(-1,-1), "MIDDLE"),
            ])
        ),
        Paragraph(f"<b>Dose:</b> {dose} &nbsp;&nbsp;&nbsp; <b>When:</b> {timing}",
                  ParagraphStyle("dose", fontName="Helvetica", fontSize=9,
                                 textColor=GOLD, leading=12, spaceAfter=4)),
        Paragraph(description, S["body_dim"]),
    ]
    inner_table = Table([[inner]], colWidths=[CONTENT_W - 28])
    inner_table.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(-1,-1), DARK_GREY),
        ("LEFTPADDING",  (0,0),(-1,-1), 14),
        ("RIGHTPADDING", (0,0),(-1,-1), 14),
        ("TOPPADDING",   (0,0),(-1,-1), 12),
        ("BOTTOMPADDING",(0,0),(-1,-1), 12),
        ("LINEBEFORE",   (0,0),(-1,-1), 3, GOLD),
        ("LINEAFTER",    (0,0),(-1,-1), 0.5, MID_GREY),
        ("LINEABOVE",    (0,0),(-1,-1), 0.5, MID_GREY),
        ("LINEBELOW",    (0,0),(-1,-1), 0.5, MID_GREY),
    ]))
    return KeepTogether([inner_table, Spacer(1, 6)])

# ── ATHLETE DATA ─────────────────────────────────────────────────────────────
def generate_plan(athlete, output_path=None):
    """
    athlete: dict of all intake form fields.
    All string values — insert exactly what the AI model produces per field.
    output_path: optional custom path for the PDF output file.
    """
    a = athlete  # shorthand

    if output_path:
        out_path = output_path
    else:
        out_path = f"/mnt/user-data/outputs/{a['name'].replace(' ','_')}_Fueling_Plan.pdf"

    doc = SimpleDocTemplate(
        out_path,
        pagesize=letter,
        leftMargin=MARGIN_SIDE, rightMargin=MARGIN_SIDE,
        topMargin=MARGIN_TB, bottomMargin=MARGIN_TB,
    )

    def on_page(canvas, doc):
        canvas.setFillColor(BLACK)
        canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    story = []

    # ── PAGE 1: COVER ─────────────────────────────────────────────────────────

    # Header bar
    story += [
        Paragraph(a["name"].upper(), S["name_hero"]),
        Paragraph(
            f"{a['plan_title']}  &middot;  {a['sport']} {a['position']}  &middot;  {a['club']}",
            S["subtitle"]
        ),
        Spacer(1, 12),
        GoldLine(CONTENT_W, 1.5),
        Spacer(1, 14),
    ]

    # Athlete Snapshot stat block
    stats = [
        (a["age"], "years\nAge"),
        (a["height"], "Height"),
        (a["weight_lbs"], "lbs\nWeight"),
        (a["training_kcal"], "kcal\nTraining Day"),
        (a["rest_kcal"], "kcal\nRest Day"),
        (a["protein_range"], "g/day\nDaily Protein"),
    ]

    def stat_cell(val, lbl):
        return Table(
            [[Paragraph(val, S["stat_val"])],
             [Paragraph(lbl, S["stat_label"])]],
            style=TableStyle([
                ("LEFTPADDING",  (0,0),(-1,-1), 0),
                ("RIGHTPADDING", (0,0),(-1,-1), 0),
                ("TOPPADDING",   (0,0),(-1,-1), 0),
                ("BOTTOMPADDING",(0,0),(-1,-1), 0),
                ("VALIGN",       (0,0),(-1,-1), "BOTTOM"),
            ])
        )

    stat_col_w = CONTENT_W / 6
    snapshot = Table(
        [[stat_cell(v, l) for v, l in stats]],
        colWidths=[stat_col_w] * 6
    )
    snapshot.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(-1,-1), MID_GREY),
        ("LEFTPADDING",  (0,0),(-1,-1), 8),
        ("RIGHTPADDING", (0,0),(-1,-1), 8),
        ("TOPPADDING",   (0,0),(-1,-1), 12),
        ("BOTTOMPADDING",(0,0),(-1,-1), 12),
        ("LINEAFTER",    (0,0),(-2,-1), 0.5, colors.HexColor("#333333")),
        ("VALIGN",       (0,0),(-1,-1), "MIDDLE"),
    ]))
    story.append(snapshot)
    story.append(Spacer(1, 8))

    # Profile details row
    profile_data = [
        [Paragraph("Position", S["table_header"]),
         Paragraph("Club", S["table_header"]),
         Paragraph("Phase", S["table_header"]),
         Paragraph("Schedule", S["table_header"]),
         Paragraph("Goal", S["table_header"]),
         Paragraph("Restrictions", S["table_header"])],
        [Paragraph(a["position"], S["table_cell_c"]),
         Paragraph(a["club"], S["table_cell_c"]),
         Paragraph(a["season_phase"], S["table_cell_c"]),
         Paragraph(a["schedule_summary"], S["table_cell_c"]),
         Paragraph(a["primary_goal"], S["table_cell_c"]),
         Paragraph(a["restrictions"], S["table_cell_c"])],
    ]
    profile_tbl = Table(profile_data, colWidths=[CONTENT_W/6]*6)
    profile_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(-1,0), colors.HexColor("#111111")),
        ("BACKGROUND",   (0,1),(-1,1), DARK_GREY),
        ("LEFTPADDING",  (0,0),(-1,-1), 6),
        ("RIGHTPADDING", (0,0),(-1,-1), 6),
        ("TOPPADDING",   (0,0),(-1,-1), 6),
        ("BOTTOMPADDING",(0,0),(-1,-1), 6),
        ("LINEAFTER",    (0,0),(-2,-1), 0.5, colors.HexColor("#333333")),
    ]))
    story.append(profile_tbl)

    # Science block
    story += section_header("The Science", "Behind the Numbers")
    story.append(Paragraph(a["science_blurb"], S["body_dim"]))
    story.append(Spacer(1, 10))

    # Macro table — 3 columns (training / rest / lift)
    macro_headers = ["Macronutrient", "Training Day", "Rest / Light Day",
                     "Lift Day (+300-400 kcal)", "Key Sources"]
    macro_rows = a["macro_table"]  # list of 4-item lists
    macro_data = [[Paragraph(h, S["table_header"]) for h in macro_headers]]
    for row in macro_rows:
        macro_data.append([Paragraph(str(c), S["table_cell"]) for c in row])

    macro_col_w = [1.2*inch, 1.2*inch, 1.2*inch, 1.4*inch, CONTENT_W - 5.0*inch]
    macro_tbl = Table(macro_data, colWidths=macro_col_w)
    macro_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(-1,0), colors.HexColor("#111111")),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [DARK_GREY, MID_GREY]),
        ("LEFTPADDING",  (0,0),(-1,-1), 6),
        ("RIGHTPADDING", (0,0),(-1,-1), 6),
        ("TOPPADDING",   (0,0),(-1,-1), 5),
        ("BOTTOMPADDING",(0,0),(-1,-1), 5),
        ("LINEBELOW",    (0,0),(-1,0), 0.5, GOLD),
        ("GRID",         (0,0),(-1,-1), 0.3, colors.HexColor("#333333")),
    ]))
    story.append(macro_tbl)

    # ── TRAINING DAY SCHEDULE ──────────────────────────────────────────────────
    story += section_header("Daily Fueling Schedule", "Training Day")
    for meal in a["training_day_meals"]:
        story.append(meal_card(**meal))
        story.append(Spacer(1, 5))

    # ── REST DAY SCHEDULE ─────────────────────────────────────────────────────
    story += section_header("Daily Fueling Schedule", "Rest / Recovery Day")
    story.append(Paragraph(a["rest_day_intro"], S["body_dim"]))
    story.append(Spacer(1, 6))
    for meal in a["rest_day_meals"]:
        story.append(meal_card(**meal))
        story.append(Spacer(1, 5))

    # ── LIFT DAY SCHEDULE ─────────────────────────────────────────────────────
    story += section_header("Daily Fueling Schedule", "Lift Day")
    story.append(Paragraph(a["lift_day_intro"], S["body_dim"]))
    story.append(Spacer(1, 6))

    # Dos and don'ts table
    dos_donts_data = [
        [Paragraph("DO on Lift Days", ParagraphStyle("dh", fontName="Helvetica-Bold",
                    fontSize=9, textColor=GREEN, leading=11)),
         Paragraph("AVOID on Lift Days", ParagraphStyle("dh", fontName="Helvetica-Bold",
                    fontSize=9, textColor=RED, leading=11))],
    ]
    dos = a["lift_dos"]
    donts = a["lift_donts"]
    max_rows = max(len(dos), len(donts))
    for i in range(max_rows):
        d = Paragraph(f"&bull;  {dos[i]}", S["bullet"]) if i < len(dos) else Paragraph("", S["body"])
        x = Paragraph(f"&bull;  {donts[i]}", S["bullet"]) if i < len(donts) else Paragraph("", S["body"])
        dos_donts_data.append([d, x])

    dos_tbl = Table(dos_donts_data, colWidths=[CONTENT_W/2 - 4, CONTENT_W/2 - 4])
    dos_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(0,-1), colors.HexColor("#102218")),
        ("BACKGROUND",   (1,0),(1,-1), colors.HexColor("#221010")),
        ("LEFTPADDING",  (0,0),(-1,-1), 10),
        ("RIGHTPADDING", (0,0),(-1,-1), 10),
        ("TOPPADDING",   (0,0),(-1,-1), 6),
        ("BOTTOMPADDING",(0,0),(-1,-1), 6),
        ("LINEBELOW",    (0,0),(-1,0), 0.5, GOLD),
        ("LINEAFTER",    (0,0),(0,-1), 0.5, MID_GREY),
    ]))
    story.append(dos_tbl)
    story.append(Spacer(1, 8))

    # ── GAME DAY PROTOCOL ────────────────────────────────────────────────────
    story += section_header("Competition Protocol", "Game Day")
    gd_headers = ["Timing", "What to Eat", "Why It Matters"]
    gd_data = [[Paragraph(h, S["table_header"]) for h in gd_headers]]
    for row in a["game_day_rows"]:
        gd_data.append([Paragraph(str(c), S["table_cell"]) for c in row])

    gd_tbl = Table(gd_data, colWidths=[1.1*inch, 2.2*inch, CONTENT_W - 3.3*inch])
    gd_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(-1,0), colors.HexColor("#111111")),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [DARK_GREY, MID_GREY]),
        ("LEFTPADDING",  (0,0),(-1,-1), 6),
        ("RIGHTPADDING", (0,0),(-1,-1), 6),
        ("TOPPADDING",   (0,0),(-1,-1), 5),
        ("BOTTOMPADDING",(0,0),(-1,-1), 5),
        ("LINEBELOW",    (0,0),(-1,0), 0.5, GOLD),
        ("GRID",         (0,0),(-1,-1), 0.3, colors.HexColor("#333333")),
        ("VALIGN",       (0,0),(-1,-1), "TOP"),
    ]))
    story.append(gd_tbl)

    # ── HYDRATION ─────────────────────────────────────────────────────────────
    story += section_header("Hydration", "The Non-Negotiable")
    story.append(Paragraph(a["hydration_blurb"], S["body_dim"]))
    story.append(Spacer(1, 6))

    hyd_headers = ["Time of Day", "Target Intake", "Notes"]
    hyd_data = [[Paragraph(h, S["table_header"]) for h in hyd_headers]]
    for row in a["hydration_rows"]:
        hyd_data.append([Paragraph(str(c), S["table_cell"]) for c in row])

    hyd_tbl = Table(hyd_data, colWidths=[1.4*inch, 1.2*inch, CONTENT_W - 2.6*inch])
    hyd_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(-1,0), colors.HexColor("#111111")),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [DARK_GREY, MID_GREY]),
        ("LEFTPADDING",  (0,0),(-1,-1), 6),
        ("RIGHTPADDING", (0,0),(-1,-1), 6),
        ("TOPPADDING",   (0,0),(-1,-1), 5),
        ("BOTTOMPADDING",(0,0),(-1,-1), 5),
        ("LINEBELOW",    (0,0),(-1,0), 0.5, GOLD),
        ("GRID",         (0,0),(-1,-1), 0.3, colors.HexColor("#333333")),
        ("VALIGN",       (0,0),(-1,-1), "TOP"),
    ]))
    story.append(hyd_tbl)

    # ── SUPPLEMENT STACK ──────────────────────────────────────────────────────
    story += section_header("Evidence-Graded", "Supplement Stack")
    story.append(Paragraph(a["supplement_intro"], S["body_dim"]))
    story.append(Spacer(1, 8))
    for s in a["supplements"]:
        story.append(supplement_card(**s))

    # Avoid box
    avoid_inner = Table([[
        [Paragraph("SUPPLEMENTS TO AVOID", ParagraphStyle("av",
             fontName="Helvetica-Bold", fontSize=9, textColor=RED,
             leading=11, spaceAfter=4)),
         Paragraph(a["supplements_avoid"], S["body_dim"])]
    ]], colWidths=[CONTENT_W - 28])
    avoid_inner.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(-1,-1), colors.HexColor("#221010")),
        ("LEFTPADDING",  (0,0),(-1,-1), 14),
        ("RIGHTPADDING", (0,0),(-1,-1), 14),
        ("TOPPADDING",   (0,0),(-1,-1), 10),
        ("BOTTOMPADDING",(0,0),(-1,-1), 10),
        ("LINEBEFORE",   (0,0),(-1,-1), 3, RED),
        ("LINEAFTER",    (0,0),(-1,-1), 0.5, MID_GREY),
        ("LINEABOVE",    (0,0),(-1,-1), 0.5, MID_GREY),
        ("LINEBELOW",    (0,0),(-1,-1), 0.5, MID_GREY),
    ]))
    story.append(avoid_inner)

    # ── GOAL-SPECIFIC SECTION ────────────────────────────────────────────────
    story += section_header("Your Goal", a["primary_goal"])
    story.append(Paragraph(a["goal_blurb"], S["body_dim"]))
    story.append(Spacer(1, 6))
    for point in a["goal_points"]:
        story.append(bullet(point))
    story.append(Spacer(1, 6))

    # ── SLEEP & RECOVERY ─────────────────────────────────────────────────────
    story += section_header("Sleep & Recovery", "Overnight Nutrition Protocol")
    story.append(Paragraph(a["sleep_blurb"], S["body_dim"]))
    story.append(Spacer(1, 6))
    sleep_data = [
        [Paragraph(h, S["table_header"]) for h in ["Nutrient / Strategy", "Dose / Timing", "Purpose"]],
    ]
    for row in a["sleep_rows"]:
        sleep_data.append([Paragraph(str(c), S["table_cell"]) for c in row])
    sleep_tbl = Table(sleep_data, colWidths=[1.8*inch, 1.8*inch, CONTENT_W - 3.6*inch])
    sleep_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(-1,0), colors.HexColor("#111111")),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [DARK_GREY, MID_GREY]),
        ("LEFTPADDING",  (0,0),(-1,-1), 6),
        ("RIGHTPADDING", (0,0),(-1,-1), 6),
        ("TOPPADDING",   (0,0),(-1,-1), 5),
        ("BOTTOMPADDING",(0,0),(-1,-1), 5),
        ("LINEBELOW",    (0,0),(-1,0), 0.5, GOLD),
        ("GRID",         (0,0),(-1,-1), 0.3, colors.HexColor("#333333")),
        ("VALIGN",       (0,0),(-1,-1), "TOP"),
    ]))
    story.append(sleep_tbl)

    # ── INJURY PREVENTION ────────────────────────────────────────────────────
    if a.get("show_injury_section", True):
        story += section_header("Injury Prevention", "Nutrition for Resilience")
        story.append(Paragraph(a["injury_blurb"], S["body_dim"]))
        story.append(Spacer(1, 6))
        inj_headers = ["Nutrient", "Dose / Source", "Timing", "Why It Matters"]
        inj_data = [[Paragraph(h, S["table_header"]) for h in inj_headers]]
        for row in a["injury_rows"]:
            inj_data.append([Paragraph(str(c), S["table_cell"]) for c in row])
        inj_tbl = Table(inj_data,
            colWidths=[1.2*inch, 1.4*inch, 1.1*inch, CONTENT_W - 3.7*inch])
        inj_tbl.setStyle(TableStyle([
            ("BACKGROUND",   (0,0),(-1,0), colors.HexColor("#111111")),
            ("ROWBACKGROUNDS",(0,1),(-1,-1), [DARK_GREY, MID_GREY]),
            ("LEFTPADDING",  (0,0),(-1,-1), 6),
            ("RIGHTPADDING", (0,0),(-1,-1), 6),
            ("TOPPADDING",   (0,0),(-1,-1), 5),
            ("BOTTOMPADDING",(0,0),(-1,-1), 5),
            ("LINEBELOW",    (0,0),(-1,0), 0.5, GOLD),
            ("GRID",         (0,0),(-1,-1), 0.3, colors.HexColor("#333333")),
            ("VALIGN",       (0,0),(-1,-1), "TOP"),
        ]))
        story.append(inj_tbl)

    # ── DIET GAP ANALYSIS ────────────────────────────────────────────────────
    story += section_header("Current Diet", "Gap Analysis")
    story.append(Paragraph(
        "Based on your typical day of eating, here is what your diet is doing well and where the plan makes targeted adjustments.",
        S["body_dim"]
    ))
    story.append(Spacer(1, 6))

    gap_data = [
        [Paragraph("What's Working", ParagraphStyle("gw",
              fontName="Helvetica-Bold", fontSize=9, textColor=GREEN, leading=11)),
         Paragraph("Gaps Addressed by This Plan", ParagraphStyle("gg",
              fontName="Helvetica-Bold", fontSize=9, textColor=GOLD, leading=11))],
    ]
    strengths = a["diet_strengths"]
    gaps = a["diet_gaps"]
    max_rows = max(len(strengths), len(gaps))
    for i in range(max_rows):
        s_p = Paragraph(f"&bull;  {strengths[i]}", S["bullet"]) if i < len(strengths) else Paragraph("", S["body"])
        g_p = Paragraph(f"&bull;  {gaps[i]}", S["bullet"]) if i < len(gaps) else Paragraph("", S["body"])
        gap_data.append([s_p, g_p])

    gap_tbl = Table(gap_data, colWidths=[CONTENT_W/2 - 4, CONTENT_W/2 - 4])
    gap_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(0,-1), colors.HexColor("#102218")),
        ("BACKGROUND",   (1,0),(1,-1), colors.HexColor("#1a1608")),
        ("LEFTPADDING",  (0,0),(-1,-1), 10),
        ("RIGHTPADDING", (0,0),(-1,-1), 10),
        ("TOPPADDING",   (0,0),(-1,-1), 6),
        ("BOTTOMPADDING",(0,0),(-1,-1), 6),
        ("LINEBELOW",    (0,0),(-1,0), 0.5, GOLD),
        ("LINEAFTER",    (0,0),(0,-1), 0.5, MID_GREY),
    ]))
    story.append(gap_tbl)

    # ── WEEKLY OVERVIEW ──────────────────────────────────────────────────────
    story += section_header("Weekly Overview", "At a Glance")
    week_days = a["week_days"]          # list of day-label strings, e.g. ["MON", "TUE", ...]
    week_rows = a["week_overview_rows"] # list of row lists: [["Calories","~3,400","~3,200",...], ...]

    wk_headers = [""] + week_days
    wk_data = [[Paragraph(h, S["table_header"]) for h in wk_headers]]
    for row in week_rows:
        wk_data.append([Paragraph(str(c), S["table_cell_c"]) for c in row])

    wk_col_w = [1.1*inch] + [(CONTENT_W - 1.1*inch) / len(week_days)] * len(week_days)
    wk_tbl = Table(wk_data, colWidths=wk_col_w)
    wk_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(-1,0), colors.HexColor("#111111")),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [DARK_GREY, MID_GREY]),
        ("LEFTPADDING",  (0,0),(-1,-1), 4),
        ("RIGHTPADDING", (0,0),(-1,-1), 4),
        ("TOPPADDING",   (0,0),(-1,-1), 5),
        ("BOTTOMPADDING",(0,0),(-1,-1), 5),
        ("LINEBELOW",    (0,0),(-1,0), 0.5, GOLD),
        ("GRID",         (0,0),(-1,-1), 0.3, colors.HexColor("#333333")),
        ("ALIGN",        (0,0),(0,-1), "LEFT"),
    ]))
    story.append(wk_tbl)

    # ── DISCLAIMER ───────────────────────────────────────────────────────────
    story.append(Spacer(1, 20))
    story.append(GoldLine(CONTENT_W, 0.5))
    story.append(Spacer(1, 8))
    story.append(Paragraph(a["disclaimer"], S["notice"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph(a["sources_line"], S["notice"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f"Generated for {a['name']} by AI-powered youth athlete nutrition system &middot; May 2026",
        S["notice"]
    ))

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print(f"PDF generated: {out_path}")
    return out_path


# ── SAMPLE DATA (Brady) ───────────────────────────────────────────────────────
brady = {
    # Identity
    "name": "Brady Stepp",
    "plan_title": "Pre-Season Performance Fueling Plan",
    "sport": "Soccer",
    "position": "CDM / CM",
    "club": "Queen City Mutiny — MLS Next",
    "age": "17",
    "height": "5'9\"",
    "weight_lbs": "165",
    "training_kcal": "~3,300",
    "rest_kcal": "~2,700",
    "protein_range": "165-180",
    "season_phase": "Pre-Season — High Intensity",
    "schedule_summary": "School 7:15-2:15 / Practice 3:00-6:00 PM / Lift 3x/wk",
    "primary_goal": "Peak Conditioning + Injury Prevention",
    "restrictions": "None",

    # Science
    "science_blurb": (
        "Calorie targets are calculated using Harris-Benedict BMR (1,843 kcal) multiplied by sport-specific "
        "activity multipliers per ACSM guidelines. A CDM covers 8-12 km per session at mixed aerobic and "
        "anaerobic intensities, creating an estimated net energy expenditure of 800-1,100 kcal during a 2-3 "
        "hour training block. Protein is set at 1.6-1.8 g/kg body weight (75 kg) per the ISSN Position Stand "
        "for high-volume adolescent athletes in pre-season. Carbohydrates are periodized -- higher on training "
        "days to fuel glycolytic demands, lower on rest days to match reduced expenditure."
    ),

    # Macro table rows: [Macro, Training, Rest, Lift, Sources]
    "macro_table": [
        ["Carbohydrates", "6-7 g/kg | 450-520 g", "4-5 g/kg | 300-375 g", "7-8 g/kg | 520-600 g",
         "Rice, pasta, oats, fruit, bread, potatoes"],
        ["Protein", "1.7 g/kg | ~128 g", "1.6 g/kg | ~120 g", "2.0 g/kg | ~150 g",
         "Chicken, eggs, Greek yogurt, milk, fish"],
        ["Fat", "1.2 g/kg | ~90 g", "1.0 g/kg | ~75 g", "1.0 g/kg | ~75 g",
         "Avocado, olive oil, nuts, salmon"],
        ["Hydration", "3.0-3.5 L total", "2.5 L total", "3.5-4.0 L total",
         "Water + electrolytes during practice"],
    ],

    # Training day meals
    "training_day_meals": [
        {"time": "6:45-7:00 AM  --  Pre-School Breakfast",
         "title": "Breakfast",
         "macros": "~700 kcal  /  35g protein  /  95g carbs",
         "items": [
             "2 scrambled eggs + 2 slices whole-grain toast",
             "1 cup oatmeal with banana and honey",
             "1 cup whole milk or 2% milk",
             "8 oz water",
         ]},
        {"time": "10:00 AM  --  Mid-Morning Snack",
         "title": "Mid-Morning Snack",
         "macros": "~400 kcal  /  20g protein  /  45g carbs",
         "items": [
             "6 oz plain full-fat Greek yogurt",
             "1 handful mixed nuts (almonds and cashews)",
             "1 piece of fruit -- apple or orange",
         ]},
        {"time": "12:15 PM  --  School Lunch (critical pre-practice meal)",
         "title": "School Lunch",
         "macros": "~850 kcal  /  55g protein  /  100g carbs",
         "items": [
             "1.5-2 cups cooked rice or pasta",
             "6 oz grilled chicken breast or ground beef",
             "1 cup vegetables -- broccoli, carrots, or corn",
             "1 dinner roll or extra bread",
             "16 oz water",
         ]},
        {"time": "2:30-2:45 PM  --  Pre-Practice Snack (70-90 min before training)",
         "title": "Pre-Practice Snack",
         "macros": "~350 kcal  /  12g protein  /  55g carbs",
         "items": [
             "1-2 slices toast with peanut butter and banana",
             "OR: granola bar + piece of fruit + string cheese",
             "12 oz water or diluted sports drink",
             "Keep fat low -- slows gastric emptying",
         ]},
        {"time": "3:00-6:00 PM  --  During Practice / Lift",
         "title": "During Practice",
         "macros": "Hydration priority -- carbs if >75 min",
         "items": [
             "6-8 oz water every 15-20 minutes throughout session",
             "If practice exceeds 75 min: 16-32 oz sports drink (Gatorade or Powerade)",
             "If lift is included: banana or energy chews at the practice-to-lift transition",
             "Goal: replace 80% of sweat loss -- weigh before and after if possible",
         ]},
        {"time": "6:00-6:30 PM  --  Post-Practice Recovery Window (within 30 min -- do not skip)",
         "title": "Recovery Window",
         "macros": "~450 kcal  /  40g protein  /  60g carbs  /  fast-absorbing",
         "items": [
             "Protein shake: 25-30g whey protein mixed in whole milk",
             "1 large banana or 8 oz chocolate milk (excellent recovery drink)",
             "OR: Greek yogurt + granola + berries",
             "16-24 oz water immediately after practice ends",
         ]},
        {"time": "7:30-8:30 PM  --  Dinner",
         "title": "Dinner",
         "macros": "~750 kcal  /  55g protein  /  80g carbs",
         "items": [
             "8 oz lean protein -- chicken, salmon, lean beef, or pork",
             "1.5 cups rice, pasta, or potatoes",
             "2 cups vegetables -- any variety",
             "Drizzle olive oil or add sliced avocado for healthy fat",
             "16 oz water",
         ]},
        {"time": "9:30-10:00 PM  --  Pre-Sleep Snack (recommended on training days)",
         "title": "Pre-Sleep Snack",
         "macros": "~250 kcal  /  25g protein  /  20g carbs",
         "items": [
             "1 cup cottage cheese OR a casein protein shake",
             "OR: 2 tbsp peanut butter on one slice of toast",
             "Supports overnight muscle protein synthesis during sleep",
         ]},
    ],

    # Rest day
    "rest_day_intro": (
        "On rest days, total calorie needs drop by 500-600 kcal. Carbohydrates are reduced to match lower "
        "energy demand -- there is no glycogen to top off for training. Protein stays high to support "
        "tissue repair and adaptation. Fat can increase slightly to fill the calorie gap with nutrient-dense foods."
    ),
    "rest_day_meals": [
        {"time": "7:30-8:00 AM  --  Breakfast",
         "title": "Relaxed Breakfast",
         "macros": "~550 kcal  /  35g protein  /  55g carbs",
         "items": [
             "3-egg omelet with spinach, peppers, and cheese",
             "1 slice whole-grain toast with avocado",
             "1 cup whole milk or 2% milk",
             "8 oz water",
         ]},
        {"time": "11:00 AM  --  Mid-Morning",
         "title": "Mid-Morning Snack",
         "macros": "~300 kcal  /  20g protein  /  25g carbs",
         "items": [
             "6 oz Greek yogurt with berries",
             "1 handful almonds or walnuts",
         ]},
        {"time": "1:00 PM  --  Lunch",
         "title": "Lunch",
         "macros": "~650 kcal  /  50g protein  /  60g carbs",
         "items": [
             "Large salad with 6-8 oz grilled chicken or salmon",
             "Quinoa or 1 cup rice base",
             "Olive oil dressing -- healthy fats fill the calorie gap on rest days",
             "16 oz water",
         ]},
        {"time": "3:30 PM  --  Afternoon Snack",
         "title": "Afternoon Snack",
         "macros": "~250 kcal  /  15g protein  /  20g carbs",
         "items": [
             "Apple slices with 2 tbsp peanut or almond butter",
             "String cheese or 1 oz nuts",
         ]},
        {"time": "6:30-7:30 PM  --  Dinner",
         "title": "Dinner",
         "macros": "~700 kcal  /  55g protein  /  55g carbs",
         "items": [
             "8 oz lean protein -- salmon, turkey, chicken thighs",
             "Roasted sweet potato or 1 cup rice",
             "2 cups roasted or steamed vegetables with olive oil",
             "Prioritize anti-inflammatory foods: salmon, leafy greens, olive oil",
         ]},
        {"time": "9:30 PM  --  Optional Pre-Sleep",
         "title": "Pre-Sleep (Optional on Rest Days)",
         "macros": "~200 kcal  /  20g protein  /  10g carbs",
         "items": [
             "1 cup cottage cheese with a few berries",
             "OR: casein protein shake",
             "Still beneficial on rest days -- overnight MPS continues regardless of activity",
         ]},
    ],

    # Lift day
    "lift_day_intro": (
        "On days that include a strength session, total calorie needs increase by approximately 300-400 kcal "
        "above standard training day targets. The primary adjustment is protein -- target the high end (150g+). "
        "Ensure the post-practice recovery shake is consumed within 30 minutes. Muscle protein synthesis peaks "
        "in the 30-minute post-lift window and declines significantly after 2 hours."
    ),
    "lift_dos": [
        "Add 1 extra scoop protein to post-practice shake",
        "Increase dinner protein portion to 10 oz",
        "Add extra cup of rice or bread at dinner",
        "Do NOT skip the pre-sleep snack on lift days",
        "Take creatine within 1 hour post-lift",
        "Eat at least 200 kcal within 2 hours before the lift",
    ],
    "lift_donts": [
        "High-fat foods in the pre-practice snack",
        "High-fiber foods within 2 hours before training",
        "Excess dairy immediately before lifting",
        "Training on an empty stomach -- always eat breakfast",
        "Caffeine after 4 PM -- protects sleep quality",
        "Skip the recovery window -- 30 min matters",
    ],

    # Game day
    "game_day_rows": [
        ["3-4 hrs before kickoff",
         "Large carb-dominant meal: pasta, rice, or potatoes with lean protein. Low fat and low fiber.",
         "Maximizes liver and muscle glycogen. Low fat and fiber prevents GI distress during sprint efforts."],
        ["60-90 min before",
         "Banana + peanut butter on toast, or a granola bar + water. Target 200-300 kcal.",
         "Tops off blood glucose without GI burden. Prevents an energy crash in the first 20 minutes."],
        ["Warm-up / tunnel",
         "8-12 oz water. Optional energy gel if game follows a long travel day.",
         "Hydration status is the #1 controllable performance variable on match day."],
        ["Halftime",
         "4-8 oz sports drink + orange slices or banana. Avoid solid food if stomach is unsettled.",
         "Replaces electrolytes lost in the first half. Quick carbs restore second-half intensity."],
        ["Within 30 min post-game",
         "Protein shake + banana, or 16 oz chocolate milk. Start water immediately.",
         "Recovery window is identical to training days. Glycogen replenishment begins now."],
        ["Post-game meal (1-2 hrs later)",
         "Full meal: protein + carbs + vegetables. Prioritize sleep-supporting foods: fish, turkey, tart cherry juice.",
         "Full recovery begins at dinner. Sleep is the ultimate recovery tool -- protect it."],
    ],

    # Hydration
    "hydration_blurb": (
        "At 165 lbs (75 kg), Brady's baseline hydration need is 2.5-3.0 L/day at rest. Pre-season training "
        "in Charlotte's summer heat adds 0.5-1.5 L of sweat loss per hour outdoors. A 2% drop in body weight "
        "from dehydration reduces sprint performance by 5-8% and cognitive decision-making by 15-20% -- "
        "critical for a CDM reading the game. Monitor urine color: pale yellow means well hydrated; dark "
        "yellow or amber means underhydrated."
    ),
    "hydration_rows": [
        ["Wake up", "16 oz water immediately", "Rehydrates overnight losses"],
        ["With breakfast", "8 oz water or milk", ""],
        ["During school", "16-24 oz across the school day", "Keep a water bottle at your desk"],
        ["Pre-practice (2:30 PM)", "16 oz water", "Start hydrated -- do not play catch-up"],
        ["During practice", "6-8 oz every 15-20 minutes", "Sports drink if session exceeds 75 min or in heat"],
        ["Post-practice", "24 oz water immediately", "Continue 16-24 oz more with dinner"],
        ["Evening", "8-16 oz before bed", "Sip steadily -- do not chug"],
        ["TOTAL (training day)", "3.0-3.5 L (100-120 oz)", "Increase in high heat or high humidity"],
    ],

    # Supplements
    "supplement_intro": (
        "The following supplements are evidence-graded per ISSN Position Stands and the American Academy "
        "of Pediatrics guidelines for adolescent athletes. Only supplements with strong safety profiles "
        "and meaningful performance evidence are included."
    ),
    "supplements": [
        {"name": "Creatine Monohydrate",
         "evidence": "STRONG EVIDENCE",
         "dose": "5g/day -- no loading phase needed",
         "timing": "Post-lift, with protein shake and carbs",
         "description": (
             "Most researched supplement in sports science. Increases phosphocreatine stores, improving "
             "repeated sprint capacity and recovery between high-intensity efforts -- exactly what a CDM needs "
             "late in a match. Safe in adolescents at standard doses. Micronized form reduces GI discomfort. "
             "Source: ISSN Position Stand on Creatine, 2021."
         )},
        {"name": "Whey Protein",
         "evidence": "STRONG EVIDENCE",
         "dose": "25-30g per serving, 1-2x daily",
         "timing": "Within 30 min post-practice; optionally at breakfast",
         "description": (
             "Fills the gap between dietary intake and the 165-180g/day protein target during high-volume "
             "training. Whey is the fastest-digesting protein and most effective at stimulating muscle protein "
             "synthesis post-exercise. Mix in whole milk to add carbs and additional protein. "
             "Source: ISSN Position Stand on Protein and Exercise, 2017."
         )},
        {"name": "Vitamin D3 + K2",
         "evidence": "STRONG EVIDENCE",
         "dose": "2,000-3,000 IU D3 + 100 mcg K2 daily",
         "timing": "With the highest-fat meal of the day",
         "description": (
             "Adolescent athletes training in morning hours or indoors are frequently deficient. Vitamin D "
             "supports muscle function, bone density, immune response, and testosterone production. K2 directs "
             "calcium to bone rather than soft tissue. Especially important during pre-season when stress fracture "
             "risk is elevated. Source: Endocrine Society Guidelines, 2024."
         )},
        {"name": "Magnesium Glycinate",
         "evidence": "GOOD EVIDENCE",
         "dose": "300-400 mg elemental magnesium",
         "timing": "Before bed",
         "description": (
             "Pre-season sweat losses significantly deplete magnesium, which is involved in over 300 enzymatic "
             "reactions including muscle contraction, nerve function, and glucose metabolism. Glycinate form is "
             "best absorbed and has the strongest sleep-quality data. Source: ACSM Exercise and Sport Sciences "
             "Reviews, 2019."
         )},
        {"name": "Omega-3 Fish Oil",
         "evidence": "GOOD EVIDENCE",
         "dose": "2-3g combined EPA+DHA daily",
         "timing": "With any meal",
         "description": (
             "Reduces exercise-induced inflammation, supports joint health, and emerging data shows benefits "
             "for cognitive function under fatigue -- meaningful for a midfielder making rapid decisions in the "
             "80th minute. Choose triglyceride-form fish oil for best absorption. Recommended brands: Thorne, "
             "Nordic Naturals. Source: ISSN Position Stand on Omega-3, 2019."
         )},
        {"name": "Electrolyte Supplement (hot weather and game days)",
         "evidence": "SITUATIONAL",
         "dose": "1 serving per 60-90 min of outdoor training",
         "timing": "During practice in heat, or mixed into water bottle",
         "description": (
             "Charlotte pre-season heat creates significant sodium, potassium, and magnesium losses that plain "
             "water cannot replace. LMNT, Liquid IV, or Precision Hydration are solid options. Gatorade works "
             "for shorter sessions. Critical for heat acclimation in the first 2-3 weeks of pre-season. "
             "Source: NATA Position Statement on Exertional Heat Illness, 2015."
         )},
    ],
    "supplements_avoid": (
        "Pre-workout stimulants with high caffeine, fat burners, testosterone boosters, HGH supplements, "
        "DMAA or proprietary blends, and any supplement not third-party tested (look for NSF Certified for "
        "Sport or Informed Sport seal). At 17, Brady's endocrine system is in a critical developmental "
        "window -- stimulants and hormonal supplements carry real risk and offer no benefit over proper nutrition."
    ),

    # Goal-specific section
    "goal_blurb": (
        "Brady's goals are peak conditioning and injury prevention during a high-intensity pre-season phase. "
        "This means the plan is built to support lean mass preservation -- not weight loss -- while maximizing "
        "fuel availability for 2-3 hour sessions. The calorie surplus on training and lift days is intentional: "
        "underfueling a pre-season block is the #1 cause of soft tissue injury and performance regression."
    ),
    "goal_points": [
        "Calorie surplus on training days (~300 kcal above maintenance) supports lean mass preservation during high volume",
        "High carbohydrate periodization (6-7 g/kg on training days) maintains glycogen for repeat sprint capacity",
        "Protein at the upper end of ISSN guidelines (1.7-2.0 g/kg) protects muscle during high-load weeks",
        "Rest day calorie reduction matches actual energy expenditure -- not a diet, just an accurate calculation",
        "Injury prevention nutrition stack (collagen, omega-3, tart cherry) is non-negotiable during pre-season",
    ],

    # Sleep & recovery
    "sleep_blurb": (
        "Sleep is the most undervalued performance and recovery tool in youth athletics. Brady's training "
        "volume requires 8-10 hours per night. Specific nutrients around sleep timing can meaningfully "
        "extend the overnight muscle protein synthesis window and reduce next-day soreness."
    ),
    "sleep_rows": [
        ["Casein Protein", "25-40g, 30-60 min before bed",
         "Slow-digesting -- sustains amino acid availability for 6-8 hrs of MPS during sleep"],
        ["Magnesium Glycinate", "300-400 mg, 30 min before bed",
         "Improves sleep quality and duration. Reduces overnight muscle cramp risk from sweat losses"],
        ["Tart Cherry Juice", "8-12 oz concentrate, nightly",
         "Natural melatonin supports sleep onset. Reduces EIMD markers by 20-30% vs placebo"],
        ["Temperature & Darkness", "Room 65-68 F, blackout curtains",
         "Core temperature drop triggers sleep onset and maximizes GH release in first sleep cycle"],
        ["No caffeine after 4 PM", "Especially on training days",
         "Half-life of caffeine is 5-7 hours. Evening caffeine delays sleep onset and reduces REM"],
    ],

    # Injury prevention
    "show_injury_section": True,
    "injury_blurb": (
        "Pre-season is the highest injury-risk phase of the training year. The following nutritional strategies "
        "are evidence-based for reducing soft tissue injury risk and supporting connective tissue integrity in "
        "adolescent soccer players."
    ),
    "injury_rows": [
        ["Collagen + Vitamin C",
         "15g collagen peptides + 50 mg Vitamin C",
         "45-60 min before practice",
         "Stimulates collagen synthesis in tendons and ligaments. Timed before loading to maximize tissue uptake."],
        ["Tart Cherry Juice",
         "8-12 oz concentrate or 480 mg capsule",
         "Nightly during pre-season",
         "Reduces exercise-induced muscle damage markers by 20-30% vs placebo. Supports sleep via natural melatonin."],
        ["Anti-inflammatory foods",
         "Turmeric, ginger, berries, fatty fish, olive oil",
         "At meals daily",
         "Chronic low-grade inflammation from repeated high-load training drives overuse injury."],
        ["Iron monitoring",
         "Red meat 3-4x/week + vitamin C with each meal",
         "At meals",
         "Iron deficiency causes fatigue and reduced VO2max before anemia develops. Blood panel recommended at start and end of pre-season."],
    ],

    # Diet gap analysis
    "diet_strengths": [
        "Regular breakfast habit -- critical for school and practice performance",
        "Adequate protein sources (chicken, eggs) already in rotation",
        "Consistent practice and school schedule enables precise meal timing",
    ],
    "diet_gaps": [
        "Pre-practice meal timing and composition needs calibration",
        "Post-practice recovery window likely being missed -- 30-minute rule is non-negotiable",
        "Hydration is likely insufficient on high-heat training days without electrolytes",
        "Pre-sleep protein not currently part of routine -- significant MPS opportunity being left unrealized",
        "Supplement stack not yet in place -- creatine and D3+K2 are highest priority to add",
    ],

    # Weekly overview
    "week_days": ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"],
    "week_overview_rows": [
        ["Training", "Practice+Lift", "Practice", "Practice+Lift", "Practice", "Practice+Lift", "Game", "Rest"],
        ["Calories", "~3,400", "~3,200", "~3,400", "~3,200", "~3,400", "~3,300", "~2,700"],
        ["Protein", "180g", "165g", "180g", "165g", "180g", "170g", "150g"],
        ["Carbs", "500g", "460g", "500g", "460g", "500g", "480g", "300g"],
        ["Creatine", "post", "post", "post", "--", "post", "--", "morning"],
        ["Tart Cherry", "nightly", "nightly", "nightly", "nightly", "nightly", "nightly", "nightly"],
        ["Collagen", "pre-train", "pre-train", "pre-train", "pre-train", "pre-train", "pre-game", "--"],
    ],

    # Legal
    "disclaimer": (
        "IMPORTANT NOTICE -- This performance fueling plan is an AI-generated document based on published "
        "guidelines from ISSN, ACSM, AAP, and the Dietary Guidelines for Americans 2020-2025. It is designed "
        "as a general evidence-based framework for performance nutrition education and is not a substitute for "
        "individualized medical or dietetic advice. Specific caloric needs, supplement tolerances, and health "
        "status should be reviewed by a licensed Registered Dietitian (RD) with Certified Specialist in Sports "
        "Dietetics (CSSD) credential and a primary care physician before implementing any supplement protocol."
    ),
    "sources_line": (
        "Key Sources: ISSN Position Stand: Protein and Exercise (2017) - ISSN Position Stand: Creatine (2021) "
        "- ISSN Position Stand: Omega-3 (2019) - ACSM Nutrition and Athletic Performance Joint Position "
        "Statement (2016) - Dietary Guidelines for Americans 2020-2025 - AAP Council on Sports Medicine and "
        "Fitness (2018) - Shaw et al., AJSM (2017) - Howatson et al., Scand J Med Sci Sports (2010) - "
        "Endocrine Society Vitamin D Guidelines (2024) - NATA Position Statement: Exertional Heat Illness (2015)"
    ),
}

if __name__ == "__main__":
    generate_plan(brady)
