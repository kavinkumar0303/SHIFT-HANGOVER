"""
publisher.py - Single PDF Handover Note Document Publisher

Renders a standardized, executive-grade Shift Handover Note PDF using ReportLab:
- Metadata Header: 'SHIFT HANDOVER REPORT' with Shift Window & Generation Timestamp
- Summary KPI Block: Total Activities, Completed, In Progress, Blockers, Watch-list
- 4 Structured Sections:
    1. COMPLETED
    2. IN PROGRESS
    3. BLOCKERS / ESCALATIONS
    4. WATCH-LIST
- Every item includes: Summary, Source, Record ID, Timestamp, Status & Progression
- Empty section displays: 'Nothing to report.'
- Running 'Page X of Y' dynamic footer
"""

import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute and print total page count: 'Page X of Y'.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        
        # Header rule & title on subsequent pages
        if self._pageNumber > 1:
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(36, letter[1] - 30, letter[0] - 36, letter[1] - 30)
            self.drawString(36, letter[1] - 25, "SHIFT HANDOVER REPORT - AUTOMATED SHIFT INTELLIGENCE")
            self.drawRightString(letter[0] - 36, letter[1] - 25, datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))

        # Footer rule & page numbers
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(36, 35, letter[0] - 36, 35)
        self.drawString(36, 24, "CONFIDENTIAL // OFFICIAL SHIFT HANDOVER NOTE")
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(letter[0] - 36, 24, page_text)
        self.restoreState()


SECTION_THEMES = {
    "COMPLETED": {
        "color": colors.HexColor("#00875A"),
        "bg": colors.HexColor("#E3FCEF"),
        "border": colors.HexColor("#57D9A3"),
        "badge": colors.HexColor("#006644"),
        "icon": "[COMPLETED]"
    },
    "IN PROGRESS": {
        "color": colors.HexColor("#0052CC"),
        "bg": colors.HexColor("#DEEBFF"),
        "border": colors.HexColor("#4C9AFF"),
        "badge": colors.HexColor("#0747A6"),
        "icon": "[IN PROGRESS]"
    },
    "BLOCKERS / ESCALATIONS": {
        "color": colors.HexColor("#DE350B"),
        "bg": colors.HexColor("#FFEBE6"),
        "border": colors.HexColor("#FF8F73"),
        "badge": colors.HexColor("#BF2600"),
        "icon": "[BLOCKERS / ESCALATIONS]"
    },
    "WATCH-LIST": {
        "color": colors.HexColor("#FF8B00"),
        "bg": colors.HexColor("#FFFAE6"),
        "border": colors.HexColor("#FFE380"),
        "badge": colors.HexColor("#172B4D"),
        "icon": "[WATCH-LIST]"
    }
}


def build_pdf_document(
    sections: Dict[str, List[Dict[str, Any]]],
    output_path: str,
    shift_metadata: Dict[str, Any]
) -> str:
    """
    Renders the official Shift Handover Note PDF.
    """
    try:
        abs_output_path = os.path.abspath(output_path)
        out_dir = os.path.dirname(abs_output_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

        doc = SimpleDocTemplate(
            abs_output_path,
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=40,
            bottomMargin=45
        )

        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            textColor=colors.HexColor("#0F172A")
        )
        
        subtitle_style = ParagraphStyle(
            "DocSubTitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#475569")
        )
        
        section_title_style = ParagraphStyle(
            "SectionTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#0F172A")
        )
        
        item_header_style = ParagraphStyle(
            "ItemHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor("#0F172A")
        )
        
        item_body_style = ParagraphStyle(
            "ItemBody",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#334155")
        )
        
        item_meta_style = ParagraphStyle(
            "ItemMeta",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor("#64748B")
        )
        
        empty_note_style = ParagraphStyle(
            "EmptyNote",
            parent=styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#64748B")
        )

        story = []

        # 1. Header Title & Metadata
        header_table_data = [
            [
                Paragraph("<b>SHIFT HANDOVER REPORT</b>", title_style),
                Paragraph(f"<b>STATUS:</b> OFFICIAL REPORT<br/><b>GENERATED:</b> {shift_metadata.get('generated_at', 'N/A')}", subtitle_style)
            ]
        ]
        t_header = Table(header_table_data, colWidths=[360, 180])
        t_header.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(t_header)
        story.append(Spacer(1, 8))

        # 2. Shift Timing Box
        start_str = shift_metadata.get("shift_start", "N/A")
        end_str = shift_metadata.get("shift_end", "N/A")
        total_items = shift_metadata.get("total_items", 0)

        meta_box_data = [
            [
                Paragraph(f"<b>Shift Window:</b> {start_str}  -&gt;  {end_str}", subtitle_style),
                Paragraph(f"<b>Total Activities:</b> {total_items}", subtitle_style)
            ]
        ]
        t_meta = Table(meta_box_data, colWidths=[360, 180])
        t_meta.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(t_meta)
        story.append(Spacer(1, 10))

        # 3. Summary Section (KPI Badges)
        completed_count = len(sections.get("COMPLETED", []))
        in_prog_count = len(sections.get("IN PROGRESS", []))
        blockers_count = len(sections.get("BLOCKERS / ESCALATIONS", []))
        watch_count = len(sections.get("WATCH-LIST", []))

        kpi_cells = [
            Paragraph(f"<font size=7 color='#00875A'><b>COMPLETED</b></font><br/><font size=14 color='#00875A'><b>{completed_count}</b></font>", styles["Normal"]),
            Paragraph(f"<font size=7 color='#0052CC'><b>IN PROGRESS</b></font><br/><font size=14 color='#0052CC'><b>{in_prog_count}</b></font>", styles["Normal"]),
            Paragraph(f"<font size=7 color='#DE350B'><b>BLOCKERS / ESCALATIONS</b></font><br/><font size=14 color='#DE350B'><b>{blockers_count}</b></font>", styles["Normal"]),
            Paragraph(f"<font size=7 color='#FF8B00'><b>WATCH-LIST</b></font><br/><font size=14 color='#FF8B00'><b>{watch_count}</b></font>", styles["Normal"]),
        ]
        
        t_kpi = Table([kpi_cells], colWidths=[135, 135, 135, 135])
        t_kpi.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BACKGROUND", (0, 0), (0, 0), SECTION_THEMES["COMPLETED"]["bg"]),
            ("BACKGROUND", (1, 0), (1, 0), SECTION_THEMES["IN PROGRESS"]["bg"]),
            ("BACKGROUND", (2, 0), (2, 0), SECTION_THEMES["BLOCKERS / ESCALATIONS"]["bg"]),
            ("BACKGROUND", (3, 0), (3, 0), SECTION_THEMES["WATCH-LIST"]["bg"]),
            ("BOX", (0, 0), (0, 0), 1, SECTION_THEMES["COMPLETED"]["border"]),
            ("BOX", (1, 0), (1, 0), 1, SECTION_THEMES["IN PROGRESS"]["border"]),
            ("BOX", (2, 0), (2, 0), 1, SECTION_THEMES["BLOCKERS / ESCALATIONS"]["border"]),
            ("BOX", (3, 0), (3, 0), 1, SECTION_THEMES["WATCH-LIST"]["border"]),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t_kpi)
        story.append(Spacer(1, 14))

        # 4. Render the 4 Required Sections in Order
        order = ["COMPLETED", "IN PROGRESS", "BLOCKERS / ESCALATIONS", "WATCH-LIST"]

        for sec_name in order:
            items = sections.get(sec_name, [])
            theme = SECTION_THEMES[sec_name]
            sec_color = theme["color"]
            sec_bg = theme["bg"]
            sec_border = theme["border"]

            # Section Header Box
            sec_header_p = Paragraph(
                f"<font color='{sec_color.hexval()}'><b>{sec_name}</b></font> ({len(items)})",
                section_title_style
            )
            sec_header_table = Table([[sec_header_p]], colWidths=[540])
            sec_header_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), sec_bg),
                ("BOX", (0, 0), (-1, -1), 0.75, sec_border),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ]))
            
            section_elements = [sec_header_table, Spacer(1, 4)]

            if not items:
                # Standard requirement: Empty sections must display "Nothing to report."
                empty_p = Paragraph("<i>Nothing to report.</i>", empty_note_style)
                empty_box = Table([[empty_p]], colWidths=[540])
                empty_box.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ]))
                section_elements.append(empty_box)
                section_elements.append(Spacer(1, 8))
            else:
                for itm in items:
                    rec_id = itm.get("record_id", "N/A")
                    src = itm.get("source", "Unknown System")
                    ts = itm.get("timestamp") or itm.get("timestamp_display") or itm.get("normalized_timestamp", "N/A")
                    summary = itm.get("summary") or itm.get("title") or f"Activity on {rec_id}"
                    status = str(itm.get("status", "N/A")).replace("_", " ").title()
                    priority = itm.get("priority") or itm.get("severity") or ""
                    assignee = itm.get("assignee") or itm.get("service") or ""
                    progression = itm.get("progression", [])
                    details = itm.get("details") or itm.get("notes") or ""

                    # Top meta line with Record ID and Summary
                    meta_left = f"<b>[{rec_id}]</b> {summary}"
                    meta_right = f"<b>Source:</b> {src} | <b>Timestamp:</b> {ts}"
                    
                    status_line = f"<b>Status:</b> {status}"
                    if priority:
                        status_line += f" | <b>Priority/Severity:</b> {priority}"
                    if assignee:
                        status_line += f" | <b>Owner/Service:</b> {assignee}"

                    item_content = [
                        [Paragraph(meta_left, item_header_style), Paragraph(meta_right, item_meta_style)],
                        [Paragraph(status_line, item_meta_style), Paragraph("", item_meta_style)]
                    ]

                    # Details / progression
                    body_text = ""
                    if details and details != summary:
                        body_text += f"<b>Details:</b> {details}"
                    
                    if progression and len(progression) > 1:
                        prog_str = " -&gt; ".join(progression)
                        if body_text:
                            body_text += "<br/>"
                        body_text += f"<font color='#475569'><b>Progression:</b> {prog_str}</font>"

                    if body_text:
                        item_content.append([
                            Paragraph(body_text, item_body_style),
                            Paragraph("", item_body_style)
                        ])

                    item_table = Table(item_content, colWidths=[350, 190])
                    item_table.setStyle(TableStyle([
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                        ("SPAN", (0, 1), (1, 1)),
                        ("SPAN", (0, 2), (1, 2)) if body_text else ("SPAN", (0, 1), (1, 1)),
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFFFFF")),
                        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ]))

                    section_elements.append(item_table)
                    section_elements.append(Spacer(1, 4))
                
                section_elements.append(Spacer(1, 6))

            story.append(KeepTogether(section_elements))

        doc.build(story, canvasmaker=NumberedCanvas)
        return abs_output_path

    except Exception as e:
        err_msg = f"CRITICAL: PDF Handover Document generation failed for '{output_path}': {str(e)}"
        print(f"\n[ERROR] {err_msg}", file=sys.stderr)
        raise RuntimeError(err_msg) from e
