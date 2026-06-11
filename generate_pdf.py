#!/usr/bin/env python3
"""Generate PDF report from REPORT.md with all embedded images."""

import os
import re
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle,
    PageBreak, HRFlowable, Preformatted
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPORT_MD = os.path.join(BASE_DIR, "REPORT.md")
OUTPUT_PDF = os.path.join(BASE_DIR, "ECU_Telemetry_Report.pdf")

IMAGE_MAP = {
    "system_architecture.png":      "report_assets/diagrams/system_architecture.png",
    "ipc_diagram.png":              "report_assets/diagrams/ipc_diagram.png",
    "memory_map.png":               "report_assets/diagrams/memory_map.png",
    "task_priority_chart.png":      "report_assets/diagrams/task_priority_chart.png",
    "main_flow.png":                "report_assets/flowcharts/main_flow.png",
    "sensor_task_flow.png":         "report_assets/flowcharts/sensor_task_flow.png",
    "watchdog_flow.png":            "report_assets/flowcharts/watchdog_flow.png",
    "fault_injection_flow.png":     "report_assets/flowcharts/fault_injection_flow.png",
    "sensor_dashboard.png":         "report_assets/graphs/sensor_dashboard.png",
    "rpm_throttle.png":             "report_assets/graphs/rpm_throttle.png",
    "temperature_comparison.png":   "report_assets/graphs/temperature_comparison.png",
    "speed_comparison.png":         "report_assets/graphs/speed_comparison.png",
    "host_acceleration_3axis.png":  "report_assets/graphs/host_acceleration_3axis.png",
    "firmware_acceleration_3axis.png": "report_assets/graphs/firmware_acceleration_3axis.png",
    "watchdog_health.png":          "report_assets/graphs/watchdog_health.png",
    "fault_demo.png":               "report_assets/graphs/fault_demo.png",
}

PAGE_W = letter[0] - 1.4 * inch

styles = getSampleStyleSheet()

style_normal = ParagraphStyle(
    "Normal2",
    parent=styles["Normal"],
    fontSize=10,
    leading=15,
    spaceAfter=6,
    alignment=TA_JUSTIFY,
)
style_h1 = ParagraphStyle(
    "H1", parent=styles["Heading1"],
    fontSize=18, leading=22, spaceBefore=18, spaceAfter=10,
    textColor=colors.HexColor("#1a1a2e"),
)
style_h2 = ParagraphStyle(
    "H2", parent=styles["Heading2"],
    fontSize=14, leading=18, spaceBefore=14, spaceAfter=6,
    textColor=colors.HexColor("#16213e"),
)
style_h3 = ParagraphStyle(
    "H3", parent=styles["Heading3"],
    fontSize=11, leading=15, spaceBefore=10, spaceAfter=4,
    textColor=colors.HexColor("#0f3460"),
)
style_code = ParagraphStyle(
    "Code", parent=styles["Code"],
    fontSize=8, leading=11, fontName="Courier",
    backColor=colors.HexColor("#f4f4f4"),
    borderColor=colors.HexColor("#cccccc"),
    borderWidth=0.5,
    borderPadding=6,
    spaceAfter=8,
    spaceBefore=4,
)
style_bullet = ParagraphStyle(
    "Bullet", parent=style_normal,
    leftIndent=20, bulletIndent=10,
    spaceAfter=3,
)
style_caption = ParagraphStyle(
    "Caption", parent=styles["Normal"],
    fontSize=9, leading=12, alignment=TA_CENTER,
    textColor=colors.HexColor("#555555"),
    spaceAfter=12,
)
style_title = ParagraphStyle(
    "Title2", parent=styles["Title"],
    fontSize=22, leading=28, alignment=TA_CENTER,
    textColor=colors.HexColor("#1a1a2e"),
    spaceAfter=6,
)
style_meta = ParagraphStyle(
    "Meta", parent=styles["Normal"],
    fontSize=11, leading=16, alignment=TA_CENTER,
    textColor=colors.HexColor("#333333"),
    spaceAfter=4,
)
style_abstract = ParagraphStyle(
    "Abstract", parent=style_normal,
    fontSize=10, leading=15,
    leftIndent=30, rightIndent=30,
    spaceAfter=8,
    alignment=TA_JUSTIFY,
)
style_table_cell = ParagraphStyle(
    "TC", parent=styles["Normal"],
    fontSize=9, leading=12,
)


def escape(text):
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    return text


def inline_fmt(text):
    # Extract backtick spans first, replace with placeholders to protect underscores
    placeholders = {}
    def save_code(m):
        key = f"\x00CODE{len(placeholders)}\x00"
        placeholders[key] = f'<font name="Courier" size="9" color="#c0392b">{escape(m.group(1))}</font>'
        return key
    text = re.sub(r"`([^`]+)`", save_code, text)
    text = escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)
    for key, val in placeholders.items():
        text = text.replace(escape(key), val)
    return text


def resolve_image(filename):
    name = os.path.basename(filename)
    if name in IMAGE_MAP:
        return os.path.join(BASE_DIR, IMAGE_MAP[name])
    full = os.path.join(BASE_DIR, filename)
    if os.path.exists(full):
        return full
    return None


def add_image(story, path, caption=None):
    img_path = resolve_image(path)
    if img_path and os.path.exists(img_path):
        try:
            img = Image(img_path)
            iw, ih = img.imageWidth, img.imageHeight
            max_w = PAGE_W
            max_h = 3.5 * inch
            scale = min(max_w / iw, max_h / ih, 1.0)
            img.drawWidth = iw * scale
            img.drawHeight = ih * scale
            img.hAlign = "CENTER"
            story.append(Spacer(1, 4))
            story.append(img)
            if caption:
                story.append(Paragraph(caption, style_caption))
            else:
                story.append(Spacer(1, 8))
        except Exception as e:
            story.append(Paragraph(f"[Image: {os.path.basename(path)}]", style_caption))


def parse_table(lines):
    rows = []
    for line in lines:
        line = line.strip().strip("|")
        if re.match(r"^[-| :]+$", line):
            continue
        cells = [c.strip() for c in line.split("|")]
        rows.append(cells)
    if not rows:
        return None
    col_count = max(len(r) for r in rows)
    for r in rows:
        while len(r) < col_count:
            r.append("")
    col_w = PAGE_W / col_count
    table_data = []
    for r in rows:
        table_data.append([Paragraph(inline_fmt(c), style_table_cell) for c in r])
    t = Table(table_data, colWidths=[col_w] * col_count, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, 0), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f4f8")]),
        ("GRID",       (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
        ("VALIGN",     (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def build_story(md_text):
    story = []
    lines = md_text.splitlines()
    i = 0
    in_code = False
    code_lines = []
    in_table = False
    table_lines = []
    in_abstract = False

    while i < len(lines):
        line = lines[i]

        # Code block
        if line.strip().startswith("```"):
            if not in_code:
                in_code = True
                code_lines = []
            else:
                in_code = False
                code_text = "\n".join(code_lines)
                story.append(Preformatted(code_text, style_code))
            i += 1
            continue

        if in_code:
            code_lines.append(line)
            i += 1
            continue

        # Table detection
        if "|" in line and line.strip().startswith("|"):
            if not in_table:
                in_table = True
                table_lines = []
            table_lines.append(line)
            i += 1
            continue
        else:
            if in_table:
                t = parse_table(table_lines)
                if t:
                    story.append(t)
                    story.append(Spacer(1, 8))
                in_table = False
                table_lines = []

        stripped = line.strip()

        # HR
        if stripped in ("---", "***", "___"):
            story.append(HRFlowable(width="100%", thickness=0.5,
                                    color=colors.HexColor("#cccccc"),
                                    spaceAfter=6, spaceBefore=6))
            i += 1
            continue

        # Headings
        if stripped.startswith("#### "):
            story.append(Paragraph(inline_fmt(stripped[5:]), style_h3))
            i += 1
            continue
        if stripped.startswith("### "):
            story.append(Paragraph(inline_fmt(stripped[4:]), style_h3))
            i += 1
            continue
        if stripped.startswith("## "):
            story.append(Paragraph(inline_fmt(stripped[3:]), style_h2))
            i += 1
            continue
        if stripped.startswith("# "):
            story.append(Paragraph(inline_fmt(stripped[2:]), style_h1))
            i += 1
            continue

        # Image
        img_match = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", stripped)
        if img_match:
            caption_text = img_match.group(1)
            img_path = img_match.group(2)
            add_image(story, img_path, caption_text if caption_text else None)
            i += 1
            continue

        # Bullet
        if stripped.startswith("- ") or stripped.startswith("* "):
            story.append(Paragraph("• " + inline_fmt(stripped[2:]), style_bullet))
            i += 1
            continue

        if re.match(r"^\d+\.\s", stripped):
            text = re.sub(r"^\d+\.\s+", "", stripped)
            story.append(Paragraph("  " + inline_fmt(text), style_bullet))
            i += 1
            continue

        # Bold-only line (metadata like **Student:** ...)
        if stripped.startswith("**") and stripped.endswith("**") and stripped.count("**") == 2:
            story.append(Paragraph(inline_fmt(stripped), style_meta))
            i += 1
            continue

        # Key: value meta lines
        if re.match(r"^\*\*.+\*\*\s+.+", stripped):
            story.append(Paragraph(inline_fmt(stripped), style_meta))
            i += 1
            continue

        # Empty line
        if not stripped:
            story.append(Spacer(1, 6))
            i += 1
            continue

        # Normal paragraph — check for inline figure references and insert images
        story.append(Paragraph(inline_fmt(stripped), style_normal))
        for fig_match in re.finditer(r"Figure\s+\d+\s*\(`?([^`)]+\.png)`?\)", stripped):
            img_ref = fig_match.group(1)
            add_image(story, img_ref, f"Figure: {os.path.basename(img_ref)}")
        i += 1

    # flush table if file ends in one
    if in_table and table_lines:
        t = parse_table(table_lines)
        if t:
            story.append(t)

    return story


def first_page(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(colors.HexColor("#1a1a2e"))
    canvas.rect(0, letter[1] - 1.1 * inch, letter[0], 1.1 * inch, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawCentredString(letter[0] / 2, letter[1] - 0.65 * inch,
                              "ECU Telemetry Simulator — Technical Report")
    canvas.restoreState()
    later_page(canvas, doc)


def later_page(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(colors.HexColor("#1a1a2e"))
    canvas.rect(0, 0, letter[0], 0.45 * inch, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(0.7 * inch, 0.17 * inch, "Dharm Mehta — Northeastern University — August 2025")
    canvas.drawRightString(letter[0] - 0.7 * inch, 0.17 * inch, f"Page {doc.page}")
    canvas.restoreState()


def main():
    with open(REPORT_MD, "r") as f:
        md_text = f.read()

    doc = SimpleDocTemplate(
        OUTPUT_PDF,
        pagesize=letter,
        leftMargin=0.7 * inch,
        rightMargin=0.7 * inch,
        topMargin=1.3 * inch,
        bottomMargin=0.7 * inch,
    )

    story = build_story(md_text)
    doc.build(story, onFirstPage=first_page, onLaterPages=later_page)
    print(f"PDF written: {OUTPUT_PDF}")


if __name__ == "__main__":
    main()
