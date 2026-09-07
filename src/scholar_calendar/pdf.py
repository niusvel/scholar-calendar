"""PDF export with exactly one page for each teaching day."""

from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepInFrame,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .models import PlanningInput
from .solver import Schedule
from .timeline import DAY_NAMES, daily_rows


def export_schedule_pdf(planning: PlanningInput, schedule: Schedule, path: str | Path) -> None:
    navy = colors.HexColor("#172a3a")
    teal = colors.HexColor("#1f8a89")
    document = SimpleDocTemplate(
        str(path),
        pagesize=landscape(A4),
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=14 * mm,
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "CalendarTitle", parent=styles["Title"], alignment=0, fontSize=20, textColor=navy
    )
    heading = ParagraphStyle(
        "CalendarHeading", fontName="Helvetica-Bold", fontSize=9, leading=12, textColor=colors.white
    )
    cell = ParagraphStyle(
        "CalendarCell", fontName="Helvetica", fontSize=8, leading=11, textColor=navy
    )
    muted = ParagraphStyle("CalendarMuted", parent=cell, textColor=colors.HexColor("#60727d"))
    rooms = [room.name for room in planning.classrooms]
    lessons = {
        (lesson.week, lesson.day, lesson.period, lesson.classroom): lesson
        for lesson in schedule.lessons
    }
    story = []
    for week in range(1, planning.weeks + 1):
        days = sorted({slot.day for slot in planning.slots if slot.week == week})
        for day in days:
            if story:
                story.append(PageBreak())
            page = [
                Paragraph("Scholar Calendar", title),
                Paragraph(
                    escape(planning.course_name or "Planificación escolar"), styles["Normal"]
                ),
                Paragraph(f"Semana {week} de {planning.weeks}", styles["Heading2"]),
                Spacer(1, 8),
            ]
            rows = [
                [Paragraph(DAY_NAMES[day].upper(), heading)] + [""] * len(rooms),
                [
                    Paragraph("Horario / turno", cell),
                    *[Paragraph(escape(room), cell) for room in rooms],
                ],
            ]
            commands = [
                ("SPAN", (0, 0), (-1, 0)),
                ("BACKGROUND", (0, 0), (-1, 0), teal),
                ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#e9eff3")),
                ("GRID", (0, 1), (-1, -1), 0.35, colors.HexColor("#d5dfe3")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
            for row in daily_rows(planning, week, day):
                if row.label == "Cambio de clase":
                    continue
                row_number = len(rows)
                if row.period is None:
                    values = [Paragraph(row.hours, muted)] + [
                        Paragraph(escape(row.label), muted) for _ in rooms
                    ]
                    if len(rooms) > 1:
                        commands.append(("SPAN", (1, row_number), (-1, row_number)))
                    background = "#fff4dc" if row.label == "Tiempo libre" else "#e5f3f2"
                    commands.append(
                        (
                            "BACKGROUND",
                            (0, row_number),
                            (-1, row_number),
                            colors.HexColor(background),
                        )
                    )
                else:
                    values = [
                        Paragraph(f"{row.hours}<br/><font color='#60727d'>{row.label}</font>", cell)
                    ]
                    for room in rooms:
                        lesson = lessons.get((week, day, row.period, room))
                        values.append(
                            Paragraph(
                                f"<b>{escape(lesson.subject)}</b><br/>{escape(lesson.teacher)}",
                                cell,
                            )
                            if lesson
                            else Paragraph("—", muted)
                        )
                rows.append(values)
            widths = (
                [35 * mm] + [(document.width - 35 * mm) / len(rooms)] * len(rooms)
                if rooms
                else [document.width]
            )
            table = Table(rows, repeatRows=2, colWidths=widths, hAlign="LEFT")
            table.setStyle(TableStyle(commands))
            page.append(table)
            # Scale unusually long days to fit rather than splitting their rows.
            story.append(
                KeepInFrame(
                    document.width,
                    document.height,
                    page,
                    mode="shrink",
                    hAlign="LEFT",
                    vAlign="TOP",
                )
            )

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#60727d"))
        canvas.drawString(12 * mm, 7 * mm, "Scholar Calendar")
        canvas.drawRightString(landscape(A4)[0] - 12 * mm, 7 * mm, f"Página {doc.page}")
        canvas.restoreState()

    document.build(story, onFirstPage=footer, onLaterPages=footer)
