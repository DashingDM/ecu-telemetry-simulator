#!/usr/bin/env python3
"""Generate academic PDF: two-column body, no cover page."""

import os, re
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame,
    Paragraph, Spacer, Image, Table, TableStyle,
    HRFlowable, PageBreak, NextPageTemplate
)
from reportlab.platypus.flowables import Preformatted
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPORT_MD = os.path.join(BASE_DIR, "REPORT.md")
OUTPUT_PDF = os.path.join(BASE_DIR, "ECU_Telemetry_Report.pdf")

IMAGE_MAP = {
    "system_architecture.png":         "report_assets/diagrams/system_architecture.png",
    "ipc_diagram.png":                 "report_assets/diagrams/ipc_diagram.png",
    "memory_map.png":                  "report_assets/diagrams/memory_map.png",
    "task_priority_chart.png":         "report_assets/diagrams/task_priority_chart.png",
    "main_flow.png":                   "report_assets/flowcharts/main_flow.png",
    "sensor_task_flow.png":            "report_assets/flowcharts/sensor_task_flow.png",
    "watchdog_flow.png":               "report_assets/flowcharts/watchdog_flow.png",
    "fault_injection_flow.png":        "report_assets/flowcharts/fault_injection_flow.png",
    "sensor_dashboard.png":            "report_assets/graphs/sensor_dashboard.png",
    "rpm_throttle.png":                "report_assets/graphs/rpm_throttle.png",
    "temperature_comparison.png":      "report_assets/graphs/temperature_comparison.png",
    "speed_comparison.png":            "report_assets/graphs/speed_comparison.png",
    "host_acceleration_3axis.png":     "report_assets/graphs/host_acceleration_3axis.png",
    "firmware_acceleration_3axis.png": "report_assets/graphs/firmware_acceleration_3axis.png",
    "watchdog_health.png":             "report_assets/graphs/watchdog_health.png",
    "fault_demo.png":                  "report_assets/graphs/fault_demo.png",
}


# ── geometry ───────────────────────────────────────────────────────────────────
PW, PH  = letter
LM = RM = 0.75 * inch
TM      = 1.0  * inch
BM      = 0.85 * inch
COL_GAP = 0.25 * inch
COL_W   = (PW - LM - RM - COL_GAP) / 2   # ≈ 3.375 in
FULL_W  = PW - LM - RM                    # ≈ 7.0 in

# characters that fit in a column at 7pt Courier (≈ 56 chars)
CODE_COLS = 56

# ── styles ─────────────────────────────────────────────────────────────────────
def S(name, **kw):
    return ParagraphStyle(name, **kw)

BODY   = S("Body",   fontName="Times-Roman",      fontSize=9,  leading=12,
           alignment=TA_JUSTIFY, spaceAfter=5)
ABST_H = S("AbstH",  fontName="Times-Bold",       fontSize=10, leading=13,
           alignment=TA_CENTER, spaceBefore=8, spaceAfter=4)
ABST   = S("Abst",   fontName="Times-Italic",     fontSize=9,  leading=12,
           alignment=TA_JUSTIFY, spaceAfter=5)
SEC    = S("Sec",    fontName="Times-Bold",        fontSize=10, leading=13,
           spaceBefore=10, spaceAfter=3, alignment=TA_CENTER)
SSEC   = S("SSec",   fontName="Times-BoldItalic", fontSize=9,  leading=12,
           spaceBefore=7, spaceAfter=2)
SSSEC  = S("SSSec",  fontName="Times-Italic",     fontSize=9,  leading=12,
           spaceBefore=4, spaceAfter=2)
CODE   = S("Code",   fontName="Courier",           fontSize=7,  leading=9,
           backColor=colors.HexColor("#f6f6f6"),
           borderColor=colors.HexColor("#cccccc"), borderWidth=0.4,
           borderPadding=4, spaceBefore=3, spaceAfter=5)
BULLET = S("Bullet", fontName="Times-Roman",       fontSize=9,  leading=12,
           leftIndent=10, spaceAfter=2)
CAPTION= S("Caption",fontName="Times-Italic",      fontSize=8,  leading=10,
           alignment=TA_CENTER, spaceBefore=2, spaceAfter=8)
TAB_CAP= S("TabCap", fontName="Times-Bold",        fontSize=8,  leading=10,
           alignment=TA_CENTER, spaceBefore=6, spaceAfter=2)
REF    = S("Ref",    fontName="Times-Roman",        fontSize=8,  leading=10,
           leftIndent=12, firstLineIndent=-12, spaceAfter=2)
TCELL  = S("TC",     fontName="Times-Roman",        fontSize=8,  leading=10)
TCELLH = S("TCH",    fontName="Times-Bold",         fontSize=8,  leading=10)

# Title block styles (replaces cover page — sits at top of first body page)
HDR_TITLE = S("HdrTitle", fontName="Times-Bold",  fontSize=18, leading=22,
               alignment=TA_CENTER, spaceAfter=6)
HDR_AUTH  = S("HdrAuth",  fontName="Times-Roman", fontSize=11, leading=14,
               alignment=TA_CENTER, spaceAfter=2)
HDR_AFF   = S("HdrAff",   fontName="Times-Italic",fontSize=9,  leading=12,
               alignment=TA_CENTER, spaceAfter=10)

_fig_counter = [0]
_sec_num     = [0]

# ── helpers ────────────────────────────────────────────────────────────────────
def _esc(t):
    return t.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def _inline(text):
    placeholders = {}
    def _save(m):
        k = f"\x00C{len(placeholders)}\x00"
        placeholders[k] = '<font name="Courier" size="8" color="#8b0000">%s</font>' % _esc(m.group(1))
        return k
    text = re.sub(r"`([^`]+)`", _save, text)
    text = _esc(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\*(.+?)\*",     r"<i>\1</i>", text)
    for k, v in placeholders.items():
        text = text.replace(_esc(k), v)
    return text

def _wrap_code(lines):
    """Truncate lines that exceed column width to prevent overflow."""
    out = []
    for line in lines:
        if len(line) > CODE_COLS:
            out.append(line[:CODE_COLS - 1] + "↩")
        else:
            out.append(line)
    return out

def _resolve(fname):
    base = os.path.basename(fname)
    if base in IMAGE_MAP:
        return os.path.join(BASE_DIR, IMAGE_MAP[base])
    p = os.path.join(BASE_DIR, fname)
    return p if os.path.exists(p) else None

def _make_image(path, caption=None):
    base = os.path.basename(path)
    p = _resolve(path)
    if not p or not os.path.exists(p):
        return []
    max_w = COL_W
    max_h = 3.2 * inch
    try:
        img = Image(p)
        iw, ih = img.imageWidth, img.imageHeight
        scale  = min(max_w / iw, max_h / ih, 1.0)
        img.drawWidth  = iw * scale
        img.drawHeight = ih * scale
        img.hAlign = "CENTER"
        items = [Spacer(1, 4), img]
        if caption:
            items.append(Paragraph(caption, CAPTION))
        else:
            items.append(Spacer(1, 4))
        return items
    except Exception:
        return [Paragraph(f"[{os.path.basename(path)}]", CAPTION)]

def _make_table(lines, width=COL_W):
    rows = []
    for line in lines:
        line = line.strip().strip("|")
        if re.match(r"^[-| :]+$", line):
            continue
        rows.append([c.strip() for c in line.split("|")])
    if not rows:
        return None
    ncols = max(len(r) for r in rows)
    for r in rows:
        while len(r) < ncols:
            r.append("")
    cw = width / ncols
    data = []
    for ri, r in enumerate(rows):
        st = TCELLH if ri == 0 else TCELL
        data.append([Paragraph(_inline(c), st) for c in r])
    t = Table(data, colWidths=[cw]*ncols, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  colors.HexColor("#d0d8e8")),
        ("GRID",          (0,0), (-1,-1), 0.3, colors.HexColor("#aaaaaa")),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.white, colors.HexColor("#f2f4f9")]),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ("TOPPADDING",    (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ("LEFTPADDING",   (0,0), (-1,-1), 4),
    ]))
    return t

# ── page callbacks ─────────────────────────────────────────────────────────────
def _on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont("Times-Roman", 8)
    canvas.setFillColor(colors.HexColor("#444444"))
    canvas.setStrokeColor(colors.HexColor("#888888"))
    canvas.setLineWidth(0.4)
    canvas.line(LM, PH - TM + 10, PW - RM, PH - TM + 10)
    canvas.drawString(LM, PH - TM + 13, "Real-Time Vehicle Telemetry ECU Simulator")
    canvas.drawRightString(PW - RM, PH - TM + 13, "Dharm Mehta")
    canvas.line(LM, BM - 8, PW - RM, BM - 8)
    canvas.drawCentredString(PW / 2, BM - 18, str(doc.page))
    canvas.restoreState()

# ── document setup ─────────────────────────────────────────────────────────────
def _build_doc():
    doc = BaseDocTemplate(
        OUTPUT_PDF, pagesize=letter,
        leftMargin=LM, rightMargin=RM,
        topMargin=TM,  bottomMargin=BM,
        title="Real-Time Vehicle Telemetry ECU Simulator",
        author="Dharm Mehta",
    )
    # First page: full-width title block + two columns below
    title_frame = Frame(LM, PH - TM - 1.4*inch, FULL_W, 1.3*inch, id="title_band")
    col1_p1 = Frame(LM,                    BM, COL_W, PH - TM - BM - 1.4*inch, id="col1_p1")
    col2_p1 = Frame(LM + COL_W + COL_GAP, BM, COL_W, PH - TM - BM - 1.4*inch, id="col2_p1")
    # Remaining pages: two full-height columns
    col1 = Frame(LM,                    BM, COL_W, PH - TM - BM, id="col1")
    col2 = Frame(LM + COL_W + COL_GAP, BM, COL_W, PH - TM - BM, id="col2")

    doc.addPageTemplates([
        PageTemplate(id="FirstPage",  frames=[title_frame, col1_p1, col2_p1], onPage=_on_page),
        PageTemplate(id="TwoColumn",  frames=[col1, col2],                    onPage=_on_page),
    ])
    return doc

# ── title block (top of page 1, full width) ────────────────────────────────────
def title_block():
    return [
        Paragraph("Real-Time Vehicle Telemetry ECU Simulator", HDR_TITLE),
        Paragraph("Dharm Mehta", HDR_AUTH),
        Paragraph("Northeastern University &nbsp;·&nbsp; mehta.dhar@northeastern.edu", HDR_AFF),
        HRFlowable(width="100%", thickness=0.5, color=colors.black,
                   spaceAfter=0, spaceBefore=0),
        NextPageTemplate("TwoColumn"),
    ]

# ── markdown parser ────────────────────────────────────────────────────────────
_SKIP = {"table of contents"}

def parse(md_text):
    story      = []
    lines      = md_text.splitlines()
    n          = len(lines)
    i          = 0
    in_code    = False
    code_buf   = []
    in_tbl     = False
    tbl_buf    = []
    in_abst    = False
    skip_block = False

    def flush_tbl():
        nonlocal in_tbl, tbl_buf
        if tbl_buf:
            t = _make_table(tbl_buf)
            if t:
                story.append(Spacer(1, 3))
                story.append(t)
                story.append(Spacer(1, 5))
        in_tbl  = False
        tbl_buf = []

    while i < n:
        raw  = lines[i]
        line = raw.strip()

        # code fence
        if line.startswith("```"):
            if not in_code:
                in_code  = True
                code_buf = []
            else:
                wrapped = _wrap_code(code_buf)
                story.append(Preformatted("\n".join(wrapped), CODE))
                in_code = False
            i += 1; continue
        if in_code:
            code_buf.append(raw)
            i += 1; continue

        # table
        if "|" in line and line.startswith("|"):
            if not in_tbl:
                in_tbl  = True
                tbl_buf = []
            tbl_buf.append(line)
            i += 1; continue
        else:
            if in_tbl:
                flush_tbl()

        # HR
        if line in ("---", "***", "___"):
            story.append(HRFlowable(width="100%", thickness=0.3,
                         color=colors.HexColor("#bbbbbb"),
                         spaceAfter=4, spaceBefore=4))
            i += 1; continue

        # skip block
        if skip_block:
            if line.startswith("## ") or line.startswith("# "):
                skip_block = False
            else:
                i += 1; continue

        # H1 — skip (in title block)
        if re.match(r"^# [^#]", line):
            i += 1; continue

        # H2
        if line.startswith("## "):
            text = line[3:].strip()
            low  = text.lower()
            if low in _SKIP:
                skip_block = True
                i += 1; continue
            in_abst = (low == "abstract")
            if in_abst:
                story.append(Paragraph("A<font size='8'>BSTRACT</font>", SEC))
                i += 1; continue
            in_abst = False
            _sec_num[0] += 1
            story.append(Paragraph(f"{_sec_num[0]}.&nbsp;&nbsp;{_inline(text).upper()}", SEC))
            i += 1; continue

        # H3
        if line.startswith("### "):
            in_abst = False
            story.append(Paragraph(_inline(line[4:]), SSEC))
            i += 1; continue

        # H4
        if line.startswith("#### "):
            story.append(Paragraph(_inline(line[5:]), SSSEC))
            i += 1; continue

        # image tag
        img_m = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", line)
        if img_m:
            for fl in _make_image(img_m.group(2), img_m.group(1) or None):
                story.append(fl)
            i += 1; continue

        # blank
        if not line:
            story.append(Spacer(1, 3))
            i += 1; continue

        # skip meta lines
        if re.match(r"^\*\*(Student|Email|Course|Institution|Date)\b", line):
            i += 1; continue

        # table caption
        if re.match(r"^\*\*Table\s+\d+", line):
            story.append(Paragraph(re.sub(r"\*\*", "", line), TAB_CAP))
            i += 1; continue

        # reference list
        if re.match(r"^\d+\.\s+", line) and _sec_num[0] >= 9:
            story.append(Paragraph(_inline(line), REF))
            i += 1; continue

        # numbered list
        num_m = re.match(r"^(\d+)\.\s+(.*)", line)
        if num_m:
            story.append(Paragraph(
                f"{num_m.group(1)}.&nbsp;&nbsp;{_inline(num_m.group(2))}", BULLET))
            i += 1; continue

        # bullet
        if line.startswith("- ") or line.startswith("* "):
            story.append(Paragraph("•&nbsp;&nbsp;" + _inline(line[2:]), BULLET))
            i += 1; continue

        # normal / abstract paragraph
        st = ABST if in_abst else BODY
        story.append(Paragraph(_inline(line), st))

        # auto-insert figures referenced inline
        for fm in re.finditer(r"Figure\s+\d+\s*\(`?([^`)]+\.png)`?\)", line):
            _fig_counter[0] += 1
            fname = fm.group(1)
            cap   = (f"Fig. {_fig_counter[0]}: "
                     f"{os.path.basename(fname).replace('_',' ').replace('.png','').title()}")
            for fl in _make_image(fname, cap):
                story.append(fl)

        i += 1

    if in_tbl:
        flush_tbl()

    return story

def main():
    with open(REPORT_MD) as f:
        md = f.read()

    doc   = _build_doc()
    story = title_block() + parse(md)
    doc.build(story)
    print(f"PDF written: {OUTPUT_PDF}")

if __name__ == "__main__":
    main()
