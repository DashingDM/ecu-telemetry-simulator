#!/usr/bin/env python3
"""Generate a single-column academic PDF matching the HPC report style."""

import os, re
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle,
    HRFlowable, Preformatted, PageBreak, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY, TA_RIGHT

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

# ── page geometry ──────────────────────────────────────────────────────────────
PW, PH  = letter
LM = RM = 1.25 * inch
TM      = 1.0  * inch
BM      = 1.0  * inch
BODY_W  = PW - LM - RM   # ~6 in

# ── styles (Times-Roman throughout — closest to Computer Modern) ───────────────
def S(name, **kw):
    return ParagraphStyle(name, **kw)

TITLE  = S("Title",  fontName="Times-Bold",       fontSize=22, leading=28,
           alignment=TA_CENTER, spaceAfter=12)
SUBM   = S("Subm",   fontName="Times-Roman",       fontSize=12, leading=16,
           alignment=TA_CENTER, spaceAfter=4)
SUBM_B = S("SubmB",  fontName="Times-Bold",        fontSize=12, leading=16,
           alignment=TA_CENTER, spaceAfter=4)
ABST_H = S("AbstH",  fontName="Times-Bold",        fontSize=12, leading=16,
           alignment=TA_CENTER, spaceAfter=6, spaceBefore=12)
ABST   = S("Abst",   fontName="Times-Italic",      fontSize=11, leading=15,
           alignment=TA_JUSTIFY, leftIndent=0.4*inch, rightIndent=0.4*inch,
           spaceAfter=6)
SEC    = S("Sec",    fontName="Times-Bold",         fontSize=13, leading=17,
           spaceBefore=14, spaceAfter=4)
SSEC   = S("SSec",   fontName="Times-BoldItalic",  fontSize=11, leading=15,
           spaceBefore=10, spaceAfter=3)
SSSEC  = S("SSSec",  fontName="Times-Italic",      fontSize=11, leading=15,
           spaceBefore=6, spaceAfter=2)
BODY   = S("Body",   fontName="Times-Roman",        fontSize=11, leading=15,
           alignment=TA_JUSTIFY, spaceAfter=6)
BULLET = S("Bullet", fontName="Times-Roman",        fontSize=11, leading=15,
           leftIndent=0.3*inch, spaceAfter=3)
CODE   = S("Code",   fontName="Courier",            fontSize=9,  leading=12,
           backColor=colors.HexColor("#f6f6f6"),
           borderColor=colors.HexColor("#cccccc"), borderWidth=0.5,
           borderPadding=6, spaceBefore=4, spaceAfter=6)
CAPTION= S("Caption",fontName="Times-Italic",       fontSize=10, leading=13,
           alignment=TA_CENTER, spaceBefore=3, spaceAfter=10)
TAB_CAP= S("TabCap", fontName="Times-Bold",         fontSize=10, leading=13,
           alignment=TA_CENTER, spaceBefore=8, spaceAfter=3)
REF    = S("Ref",    fontName="Times-Roman",         fontSize=10, leading=14,
           leftIndent=0.3*inch, firstLineIndent=-0.3*inch, spaceAfter=3)
TCELL  = S("TC",     fontName="Times-Roman",         fontSize=10, leading=13)
TCELLH = S("TCH",    fontName="Times-Bold",          fontSize=10, leading=13)
PAGE_N = S("PN",     fontName="Times-Roman",         fontSize=10, leading=13,
           alignment=TA_CENTER)

_fig_counter = [0]

def _esc(t):
    return t.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def _inline(text):
    placeholders = {}
    def _save(m):
        k = f"\x00C{len(placeholders)}\x00"
        placeholders[k] = '<font name="Courier" size="10" color="#8b0000">%s</font>' % _esc(m.group(1))
        return k
    text = re.sub(r"`([^`]+)`", _save, text)
    text = _esc(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\*(.+?)\*",     r"<i>\1</i>", text)
    for k, v in placeholders.items():
        text = text.replace(_esc(k), v)
    return text

def _resolve(fname):
    base = os.path.basename(fname)
    if base in IMAGE_MAP:
        return os.path.join(BASE_DIR, IMAGE_MAP[base])
    p = os.path.join(BASE_DIR, fname)
    return p if os.path.exists(p) else None

def _make_image(path, caption=None):
    p = _resolve(path)
    if not p or not os.path.exists(p):
        return []
    try:
        img = Image(p)
        iw, ih = img.imageWidth, img.imageHeight
        scale  = min(BODY_W / iw, 4.5 * inch / ih, 1.0)
        img.drawWidth  = iw * scale
        img.drawHeight = ih * scale
        img.hAlign = "CENTER"
        items = [Spacer(1, 6), img]
        if caption:
            items.append(Paragraph(caption, CAPTION))
        else:
            items.append(Spacer(1, 6))
        return items
    except Exception:
        return [Paragraph(f"[{os.path.basename(path)}]", CAPTION)]

def _make_table(lines):
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
    cw = BODY_W / ncols
    data = []
    for ri, r in enumerate(rows):
        st = TCELLH if ri == 0 else TCELL
        data.append([Paragraph(_inline(c), st) for c in r])
    t = Table(data, colWidths=[cw]*ncols, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  colors.HexColor("#d0d8e8")),
        ("GRID",          (0,0), (-1,-1), 0.4, colors.HexColor("#999999")),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.white, colors.HexColor("#f4f6fb")]),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ("TOPPADDING",    (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
    ]))
    return t

# ── header / footer ────────────────────────────────────────────────────────────
_page_num = [0]

def _on_page(canvas, doc):
    _page_num[0] = doc.page
    canvas.saveState()
    if doc.page > 1:
        canvas.setFont("Times-Roman", 9)
        canvas.setFillColor(colors.HexColor("#444444"))
        canvas.drawString(LM, PH - TM + 16,
            "Real-Time Vehicle Telemetry ECU Simulator")
        canvas.drawRightString(PW - RM, PH - TM + 16,
            "Dharm Mehta")
        canvas.setStrokeColor(colors.HexColor("#888888"))
        canvas.setLineWidth(0.4)
        canvas.line(LM, PH - TM + 12, PW - RM, PH - TM + 12)
        canvas.line(LM, BM - 10, PW - RM, BM - 10)
        canvas.setFont("Times-Roman", 9)
        canvas.drawCentredString(PW/2, BM - 20, str(doc.page))
    canvas.restoreState()

# ── cover page ─────────────────────────────────────────────────────────────────
def cover_page():
    items = []
    items.append(Spacer(1, 1.8 * inch))
    items.append(Paragraph(
        "Real-Time Vehicle Telemetry ECU Simulator",
        TITLE))
    items.append(Spacer(1, 2.5 * inch))
    items.append(Paragraph("Submitted To:", SUBM))
    items.append(Spacer(1, 0.15 * inch))
    items.append(Paragraph("Embedded Systems / Real-Time Systems", SUBM_B))
    items.append(Paragraph("Northeastern University", SUBM))
    items.append(Spacer(1, 1.5 * inch))
    items.append(Paragraph("Submitted By:", SUBM))
    items.append(Spacer(1, 0.15 * inch))
    items.append(Paragraph("Dharm Mehta", SUBM_B))
    items.append(Paragraph("mehta.dhar@northeastern.edu", SUBM))
    items.append(PageBreak())
    return items

# ── markdown parser ────────────────────────────────────────────────────────────
_SKIP = {"table of contents"}
_sec_num = [0]

def parse(md_text):
    story   = []
    lines   = md_text.splitlines()
    n       = len(lines)
    i       = 0
    in_code = False
    code_buf= []
    in_tbl  = False
    tbl_buf = []
    in_abst = False
    skip_block = False

    def flush_tbl():
        nonlocal in_tbl, tbl_buf
        if tbl_buf:
            t = _make_table(tbl_buf)
            if t:
                story.append(Spacer(1, 4))
                story.append(t)
                story.append(Spacer(1, 6))
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
                story.append(Preformatted("\n".join(code_buf), CODE))
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
            story.append(HRFlowable(width="100%", thickness=0.5,
                         color=colors.HexColor("#bbbbbb"),
                         spaceAfter=6, spaceBefore=6))
            i += 1; continue

        # skip block check
        if skip_block:
            if line.startswith("## ") or line.startswith("# "):
                skip_block = False
            else:
                i += 1; continue

        # H1 — skip the title (already on cover)
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
                story.append(Paragraph("Abstract", ABST_H))
                i += 1; continue
            in_abst = False
            _sec_num[0] += 1
            story.append(Paragraph(f"{_sec_num[0]}.&nbsp;&nbsp;{_inline(text)}", SEC))
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
            story.append(Spacer(1, 4))
            i += 1; continue

        # meta lines — skip (already on cover)
        if re.match(r"^\*\*(Student|Email|Course|Institution|Date)\b", line):
            i += 1; continue

        # table caption
        if re.match(r"^\*\*Table\s+\d+", line):
            story.append(Paragraph(re.sub(r"\*\*", "", line), TAB_CAP))
            i += 1; continue

        # reference list item (starts with number+dot)
        if re.match(r"^\d+\.\s+", line) and _sec_num[0] >= 9:
            story.append(Paragraph(_inline(line), REF))
            i += 1; continue

        # numbered list
        num_m = re.match(r"^(\d+)\.\s+(.*)", line)
        if num_m:
            story.append(Paragraph(
                f"{num_m.group(1)}.&nbsp;&nbsp;{_inline(num_m.group(2))}",
                BULLET))
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
            cap   = (f"Figure {_fig_counter[0]}: "
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

    doc = SimpleDocTemplate(
        OUTPUT_PDF,
        pagesize=letter,
        leftMargin=LM, rightMargin=RM,
        topMargin=TM,  bottomMargin=BM,
        title="Real-Time Vehicle Telemetry ECU Simulator",
        author="Dharm Mehta",
    )

    story  = cover_page()
    story += parse(md)

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    print(f"PDF written: {OUTPUT_PDF}")

if __name__ == "__main__":
    main()
