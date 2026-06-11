#!/usr/bin/env python3
"""Generate IEEE-format two-column PDF from REPORT.md."""

import os, re
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer,
    Image, Table, TableStyle, HRFlowable, Preformatted, KeepTogether,
    NextPageTemplate, PageBreak
)
from reportlab.platypus.flowables import Flowable
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY, TA_RIGHT

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPORT_MD = os.path.join(BASE_DIR, "REPORT.md")
OUTPUT_PDF = os.path.join(BASE_DIR, "ECU_Telemetry_Report.pdf")

IMAGE_MAP = {
    "system_architecture.png":        "report_assets/diagrams/system_architecture.png",
    "ipc_diagram.png":                "report_assets/diagrams/ipc_diagram.png",
    "memory_map.png":                 "report_assets/diagrams/memory_map.png",
    "task_priority_chart.png":        "report_assets/diagrams/task_priority_chart.png",
    "main_flow.png":                  "report_assets/flowcharts/main_flow.png",
    "sensor_task_flow.png":           "report_assets/flowcharts/sensor_task_flow.png",
    "watchdog_flow.png":              "report_assets/flowcharts/watchdog_flow.png",
    "fault_injection_flow.png":       "report_assets/flowcharts/fault_injection_flow.png",
    "sensor_dashboard.png":           "report_assets/graphs/sensor_dashboard.png",
    "rpm_throttle.png":               "report_assets/graphs/rpm_throttle.png",
    "temperature_comparison.png":     "report_assets/graphs/temperature_comparison.png",
    "speed_comparison.png":           "report_assets/graphs/speed_comparison.png",
    "host_acceleration_3axis.png":    "report_assets/graphs/host_acceleration_3axis.png",
    "firmware_acceleration_3axis.png":"report_assets/graphs/firmware_acceleration_3axis.png",
    "watchdog_health.png":            "report_assets/graphs/watchdog_health.png",
    "fault_demo.png":                 "report_assets/graphs/fault_demo.png",
}

# ── page geometry ──────────────────────────────────────────────────────────────
PW, PH     = letter                     # 8.5 × 11 in
LM = RM    = 0.625 * inch
TM         = 1.0   * inch
BM         = 0.875 * inch
COL_GAP    = 0.25  * inch
COL_W      = (PW - LM - RM - COL_GAP) / 2   # ≈ 3.4375 in

# ── styles (IEEE uses Times-Roman body, Helvetica headings) ───────────────────
def _s(name, **kw):
    s = ParagraphStyle(name, **kw)
    return s

BODY   = _s("IEEEBody",   fontName="Times-Roman",  fontSize=9,  leading=11,
            alignment=TA_JUSTIFY, spaceAfter=4)
BODY_C = _s("IEEEBodyC",  fontName="Times-Roman",  fontSize=9,  leading=11,
            alignment=TA_CENTER,  spaceAfter=4)
SEC    = _s("IEEESec",    fontName="Helvetica-Bold",fontSize=9,  leading=12,
            spaceBefore=8, spaceAfter=3, alignment=TA_CENTER)
SSEC   = _s("IEEESSec",   fontName="Times-BoldItalic", fontSize=9, leading=11,
            spaceBefore=6, spaceAfter=2)
SSSEC  = _s("IEEESSSec",  fontName="Times-Italic",  fontSize=9,  leading=11,
            spaceBefore=4, spaceAfter=2)
CODE   = _s("IEEECode",   fontName="Courier",       fontSize=7,  leading=9,
            backColor=colors.HexColor("#f8f8f8"),
            borderColor=colors.HexColor("#cccccc"), borderWidth=0.4,
            borderPadding=4, spaceBefore=3, spaceAfter=4)
BULLET = _s("IEEEBullet", fontName="Times-Roman",   fontSize=9,  leading=11,
            leftIndent=10, bulletIndent=0, spaceAfter=2)
CAPTION= _s("IEEECaption",fontName="Times-Italic",  fontSize=8,  leading=10,
            alignment=TA_CENTER, spaceAfter=6, spaceBefore=2)
REF    = _s("IEEERef",    fontName="Times-Roman",   fontSize=8,  leading=10,
            leftIndent=14, firstLineIndent=-14, spaceAfter=2)
TCELL  = _s("IEEETC",     fontName="Times-Roman",   fontSize=8,  leading=10)
TCELLB = _s("IEEETCB",    fontName="Times-Bold",    fontSize=8,  leading=10)
ABST   = _s("IEEEAbst",   fontName="Times-Italic",  fontSize=9,  leading=11,
            leftIndent=8, rightIndent=8, alignment=TA_JUSTIFY, spaceAfter=4)
TITLE  = _s("IEEETitle",  fontName="Times-Bold",    fontSize=20, leading=24,
            alignment=TA_CENTER, spaceAfter=6)
AUTH   = _s("IEEEAuth",   fontName="Times-Roman",   fontSize=11, leading=14,
            alignment=TA_CENTER, spaceAfter=2)
AFF    = _s("IEEEAff",    fontName="Times-Italic",  fontSize=9,  leading=11,
            alignment=TA_CENTER, spaceAfter=6)

# roman numerals for sections
_ROMAN = ["","I","II","III","IV","V","VI","VII","VIII","IX","X","XI","XII","XIII"]
_sec_counter   = [0]
_ssec_counter  = [0]
_fig_counter   = [0]
_tab_counter   = [0]

def _esc(t):
    t = t.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
    return t

def _inline(text):
    placeholders = {}
    def _save(m):
        k = f"\x00C{len(placeholders)}\x00"
        placeholders[k] = '<font name="Courier" size="8" color="#b00000">%s</font>' % _esc(m.group(1))
        return k
    text = re.sub(r"`([^`]+)`", _save, text)
    text = _esc(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\*(.+?)\*",     r"<i>\1</i>", text)
    for k,v in placeholders.items():
        text = text.replace(_esc(k), v)
    return text

def _resolve(fname):
    base = os.path.basename(fname)
    if base in IMAGE_MAP:
        return os.path.join(BASE_DIR, IMAGE_MAP[base])
    p = os.path.join(BASE_DIR, fname)
    return p if os.path.exists(p) else None

def _make_image(path, caption=None, max_h=2.6):
    p = _resolve(path)
    if not p or not os.path.exists(p):
        return []
    try:
        img = Image(p)
        iw, ih = img.imageWidth, img.imageHeight
        scale  = min(COL_W / iw, max_h * inch / ih, 1.0)
        img.drawWidth  = iw * scale
        img.drawHeight = ih * scale
        img.hAlign = "CENTER"
        items = [Spacer(1,4), img]
        if caption:
            items.append(Paragraph(caption, CAPTION))
        else:
            items.append(Spacer(1,4))
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
        while len(r) < ncols: r.append("")
    cw = COL_W / ncols
    data = []
    for ri, r in enumerate(rows):
        st = TCELLB if ri == 0 else TCELL
        data.append([Paragraph(_inline(c), st) for c in r])
    t = Table(data, colWidths=[cw]*ncols, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0), colors.HexColor("#dde3ee")),
        ("GRID",(0,0),(-1,-1),0.3, colors.HexColor("#aaaaaa")),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white, colors.HexColor("#f4f6fb")]),
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("TOPPADDING",(0,0),(-1,-1),2),
        ("BOTTOMPADDING",(0,0),(-1,-1),2),
        ("LEFTPADDING",(0,0),(-1,-1),4),
    ]))
    return t

# ── header / footer callbacks ──────────────────────────────────────────────────
def _header_footer(canvas, doc):
    canvas.saveState()
    # header rule
    canvas.setStrokeColor(colors.black)
    canvas.setLineWidth(0.5)
    canvas.line(LM, PH - TM + 6, PW - RM, PH - TM + 6)
    # footer
    canvas.setFont("Times-Roman", 8)
    canvas.drawCentredString(PW/2, BM/2, f"— {doc.page} —")
    canvas.restoreState()

def _first_page(canvas, doc):
    _header_footer(canvas, doc)

def _later_pages(canvas, doc):
    canvas.saveState()
    canvas.setFont("Times-Italic", 8)
    canvas.drawString(LM, PH - TM + 10,
        "Real-Time Vehicle Telemetry ECU Simulator")
    canvas.drawRightString(PW - RM, PH - TM + 10,
        "Mehta — Northeastern University — August 2025")
    canvas.restoreState()
    _header_footer(canvas, doc)

# ── document ───────────────────────────────────────────────────────────────────
def _build_doc():
    doc = BaseDocTemplate(
        OUTPUT_PDF, pagesize=letter,
        leftMargin=LM, rightMargin=RM,
        topMargin=TM,  bottomMargin=BM,
        title="Real-Time Vehicle Telemetry ECU Simulator",
        author="Dharm Mehta",
    )

    # title frame spans full width
    title_frame = Frame(LM, BM, PW-LM-RM, PH-TM-BM,
                        id="title", showBoundary=0)
    # two-column frames
    col1 = Frame(LM,           BM, COL_W, PH-TM-BM, id="col1", showBoundary=0)
    col2 = Frame(LM+COL_W+COL_GAP, BM, COL_W, PH-TM-BM, id="col2", showBoundary=0)

    doc.addPageTemplates([
        PageTemplate(id="TitlePage",  frames=[title_frame],
                     onPage=_first_page),
        PageTemplate(id="TwoColumn",  frames=[col1, col2],
                     onPageEnd=_later_pages),
    ])
    return doc

# ── markdown parser ────────────────────────────────────────────────────────────
_SKIP_SECTIONS = {"table of contents"}

def parse(md_text):
    story  = []
    lines  = md_text.splitlines()
    n      = len(lines)
    i      = 0

    in_code    = False
    code_buf   = []
    in_table   = False
    table_buf  = []
    in_abstract= False
    skip_toc   = False
    title_done = False
    meta_lines = []
    collecting_meta = True   # collect **Key:** Val lines before first ---

    def flush_table():
        nonlocal in_table, table_buf
        if table_buf:
            t = _make_table(table_buf)
            if t:
                _tab_counter[0] += 1
                story.append(Spacer(1,4))
                story.append(t)
                story.append(Spacer(1,4))
        in_table  = False
        table_buf = []

    while i < n:
        raw  = lines[i]
        line = raw.strip()

        # ── code fence ──
        if line.startswith("```"):
            if not in_code:
                in_code = True
                code_buf = []
            else:
                story.append(Preformatted("\n".join(code_buf), CODE))
                in_code = False
                code_buf = []
            i += 1; continue

        if in_code:
            code_buf.append(raw)
            i += 1; continue

        # ── table ──
        if "|" in line and line.startswith("|"):
            if not in_table:
                in_table = True
                table_buf = []
            table_buf.append(line)
            i += 1; continue
        else:
            if in_table:
                flush_table()

        # ── HR ──
        if line in ("---","***","___"):
            if collecting_meta and meta_lines:
                # end of title block — emit title page content
                collecting_meta = False
            else:
                story.append(HRFlowable(width="100%", thickness=0.3,
                             color=colors.HexColor("#aaaaaa"),
                             spaceAfter=4, spaceBefore=4))
            i += 1; continue

        # ── headings ──
        if line.startswith("# ") and not line.startswith("## "):
            text = line[2:]
            if not title_done:
                story.append(Paragraph(_inline(text), TITLE))
                title_done = True
                i += 1; continue
            story.append(Paragraph(_inline(text), SEC))
            i += 1; continue

        if line.startswith("## "):
            text = line[3:]
            low  = text.lower().strip()
            skip_toc = (low == "table of contents")
            if low in _SKIP_SECTIONS:
                # skip until next ##
                i += 1
                while i < n and not lines[i].startswith("## ") and not lines[i].startswith("# "):
                    i += 1
                skip_toc = False
                continue
            if low == "abstract":
                in_abstract = True
                story.append(Paragraph("A<font size='7'>BSTRACT</font>", SEC))
                i += 1; continue
            in_abstract = False
            # numbered section
            _sec_counter[0] += 1
            _ssec_counter[0]  = 0
            rnum = _ROMAN[min(_sec_counter[0], len(_ROMAN)-1)]
            story.append(Paragraph(f"{rnum}. {_inline(text).upper()}", SEC))
            i += 1; continue

        if line.startswith("### "):
            text = line[4:]
            _ssec_counter[0] += 1
            story.append(Paragraph(
                f"{_sec_counter[0]}.{_ssec_counter[0]}&nbsp;&nbsp;<i>{_inline(text)}</i>",
                SSEC))
            i += 1; continue

        if line.startswith("#### "):
            story.append(Paragraph(_inline(line[5:]), SSSEC))
            i += 1; continue

        # ── image tag ──
        img_m = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", line)
        if img_m:
            for fl in _make_image(img_m.group(2), img_m.group(1) or None):
                story.append(fl)
            i += 1; continue

        # ── blank ──
        if not line:
            if in_abstract: pass
            else: story.append(Spacer(1, 3))
            i += 1; continue

        # ── meta block (**Key:** value) ──
        if collecting_meta and re.match(r"^\*\*.+\*\*", line):
            meta_lines.append(line)
            story.append(Paragraph(_inline(line), AFF))
            i += 1; continue

        # ── numbered list ──
        num_m = re.match(r"^(\d+)\.\s+(.*)", line)
        if num_m:
            story.append(Paragraph(f"{num_m.group(1)}.&nbsp;&nbsp;{_inline(num_m.group(2))}", BULLET))
            i += 1; continue

        # ── bullet ──
        if line.startswith("- ") or line.startswith("* "):
            story.append(Paragraph("•&nbsp;&nbsp;" + _inline(line[2:]), BULLET))
            i += 1; continue

        # ── table caption bold line ──
        if re.match(r"^\*\*Table\s+\d+", line):
            _tab_counter[0] += 1
            story.append(Paragraph(_inline(line).replace("**",""), CAPTION))
            i += 1; continue

        # ── normal paragraph ──
        st = ABST if in_abstract else BODY
        story.append(Paragraph(_inline(line), st))

        # auto-insert figures referenced inline
        for fm in re.finditer(r"Figure\s+\d+\s*\(`?([^`)]+\.png)`?\)", line):
            _fig_counter[0] += 1
            fname = fm.group(1)
            cap   = f"Fig. {_fig_counter[0]}. {os.path.basename(fname).replace('_',' ').replace('.png','').title()}"
            for fl in _make_image(fname, cap, max_h=2.2):
                story.append(fl)

        i += 1

    if in_table:
        flush_table()

    return story

# ── title page cover ───────────────────────────────────────────────────────────
def title_block():
    items = []
    items.append(Spacer(1, 0.15*inch))
    items.append(HRFlowable(width="100%", thickness=1.0, color=colors.black,
                             spaceAfter=8))
    items.append(Paragraph(
        "Real-Time Vehicle Telemetry ECU Simulator",
        TITLE))
    items.append(Spacer(1, 6))
    items.append(Paragraph("Dharm Mehta", AUTH))
    items.append(Paragraph("Northeastern University, Boston, MA", AFF))
    items.append(Paragraph("mehta.dhar@northeastern.edu", AFF))
    items.append(HRFlowable(width="100%", thickness=0.5, color=colors.black,
                             spaceBefore=4, spaceAfter=6))
    return items

def main():
    with open(REPORT_MD) as f:
        md = f.read()

    doc   = _build_doc()
    story = []

    # ── title page (single column) ──
    story += title_block()
    story.append(NextPageTemplate("TwoColumn"))
    story.append(PageBreak())

    # ── body (two column) ──
    story += parse(md)

    doc.build(story)
    print(f"PDF written: {OUTPUT_PDF}")

if __name__ == "__main__":
    main()
