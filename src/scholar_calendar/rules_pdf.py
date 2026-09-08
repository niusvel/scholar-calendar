"""Export the shared rule catalog as a readable, paginated document."""

from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate

from .rules_catalog import RULE_SECTIONS


def export_rules_pdf(path: str | Path) -> None:
    document = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        title="Reglas de generación de horarios",
        author="Scholar Calendar",
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=20 * mm,
        bottomMargin=18 * mm,
    )
    body = ParagraphStyle(
        "RuleBody",
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#20313d"),
        spaceAfter=10,
    )
    title = ParagraphStyle(
        "RuleSection",
        parent=body,
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=26,
        spaceAfter=14,
        keepWithNext=True,
    )
    introduction = ParagraphStyle(
        "RuleIntroduction",
        parent=body,
        textColor=colors.HexColor("#60727d"),
        spaceAfter=18,
        keepWithNext=True,
    )
    heading = ParagraphStyle(
        "RuleHeading",
        parent=body,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#1f8a89"),
        spaceBefore=6,
        spaceAfter=4,
        keepWithNext=True,
    )
    story = []
    for section, description, rules in RULE_SECTIONS:
        if story:
            story.append(PageBreak())
        story.append(Paragraph(f"Reglas {escape(section.lower())}", title))
        story.append(Paragraph(escape(description), introduction))
        for label, explanation in rules:
            story.append(Paragraph(escape(label), heading))
            story.append(Paragraph(escape(explanation), body))

    def page_frame(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(colors.HexColor("#60727d"))
        canvas.setFont("Helvetica", 8)
        canvas.drawString(18 * mm, A4[1] - 12 * mm, "Scholar Calendar · Reglas de generación")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Página {doc.page}")
        canvas.restoreState()

    document.build(story, onFirstPage=page_frame, onLaterPages=page_frame)
