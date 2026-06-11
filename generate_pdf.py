#!/usr/bin/env python3
"""Generate academic PDF: HPC-style cover + two-column body, no date."""

import os, re
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame,
    Paragraph, Spacer, Image, Table, TableStyle,
    HRFlowable, Preformatted, PageBreak, NextPageTemplate
)
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
PW, PH   = letter
LM = RM  = 0.75 * inch
TM       = 1.0  * inch
BM       = 0.85 * inch
COL_GAP  = 0.25 * inch
COL_W    = (PW - LM - RM - COL_GAP) / 2   # ≈ 3.375 in

# ── styles ─────────────────────────────────────────────────────────────────────
def S(name, **kw):
    return ParagraphStyle(name, **kw)

# cover
CVR_TITLE = S("CvrTitle", fontName="Times-Bold",   fontSize=22, leading=28,
              alignment=TA_CENTER, spaceAfter=10)
CVR_SUB   = S("CvrSub",   fontName="Times-Roman",  fontSize=12, leading=16,
              alignment=TA_CENTER, spaceAfter=4)
CVR_SUBB  = S("CvrSubB",  fontName="Times-Bold",   fontSize=12, leading=16,
              alignment=TA_CENTER, spaceAfter=4)

# body
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
        scale  = min(COL_W / iw, 3.2 * inch / ih, 1.0)
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
    cw = COL_W / ncols
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
def _cover_cb(canvas, doc):
    pass  # no header/footer on cover

def _body_cb(canvas, doc):
    canvas.saveState()
    canvas.setFont("Times-Roman", 8)
    canvas.setFillColor(colors.HexColor("#444444"))
    canvas.setStrokeColor(colors.HexColor("#888888"))
    canvas.setLineWidth(0.4)
    # header
    canvas.line(LM, PH - TM + 10, PW - RM, PH - TM + 10)
    canvas.drawString(LM, PH - TM + 13, "Real-Time Vehicle Telemetry ECU Simulator")
    canvas.drawRightString(PW - RM, PH - TM + 13, "Dharm Mehta")
    # footer
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
    # cover: single full-width frame
    cover_frame = Frame(LM, BM, PW - LM - RM, PH - TM - BM, id="cover")
    # body: two columns
    col1 = Frame(LM,                    BM, COL_W, PH - TM - BM, id="col1")
    col2 = Frame(LM + COL_W + COL_GAP, BM, COL_W, PH - TM - BM, id="col2")

    doc.addPageTemplates([
        PageTemplate(id="Cover",     frames=[cover_frame], onPage=_cover_cb),
        PageTemplate(id="TwoColumn", frames=[col1, col2],  onPage=_body_cb),
    ])
    return doc

# ── cover page ─────────────────────────────────────────────────────────────────
def cover_page():
    items = []
    items.append(Spacer(1, 1.8 * inch))
    items.append(Paragraph("Real-Time Vehicle Telemetry ECU Simulator", CVR_TITLE))
    items.append(Spacer(1, 2.5 * inch))
    items.append(Paragraph("Submitted To:", CVR_SUB))
    items.append(Spacer(1, 0.12 * inch))
    items.append(Paragraph("Embedded Systems / Real-Time Systems", CVR_SUBB))
    items.append(Paragraph("Northeastern University", CVR_SUB))
    items.append(Spacer(1, 1.5 * inch))
    items.append(Paragraph("Submitted By:", CVR_SUB))
    items.append(Spacer(1, 0.12 * inch))
    items.append(Paragraph("Dharm Mehta", CVR_SUBB))
    items.append(Paragraph("mehta.dhar@northeastern.edu", CVR_SUB))
    items.append(NextPageTemplate("TwoColumn"))
    items.append(PageBreak())
    return items

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

        # H1 — skip (on cover)
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

        # skip meta lines (Student / Email / Course / Institution / Date)
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
    story = cover_page() + parse(md)
    doc.build(story)
    print(f"PDF written: {OUTPUT_PDF}")

if __name__ == "__main__":
    main()
