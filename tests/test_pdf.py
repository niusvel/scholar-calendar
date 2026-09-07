import re
from dataclasses import replace
from datetime import time

from scholar_calendar.defaults import default_planning
from scholar_calendar.models import Classroom, build_daily_periods, build_slots
from scholar_calendar.pdf import export_schedule_pdf
from scholar_calendar.solver import Schedule


def test_pdf_keeps_one_page_per_day_even_for_long_days(tmp_path):
    periods = build_daily_periods(
        start=time(6), period_count=20, duration_minutes=30, transition_minutes=0
    )
    planning = replace(
        default_planning(),
        weeks=2,
        classrooms=(Classroom("Aula <1> & laboratorio"), Classroom("Aula 2")),
        slots=build_slots(weeks=2, days=5, daily_periods=periods),
    )
    path = tmp_path / "days.pdf"
    export_schedule_pdf(planning, Schedule(()), path)
    data = path.read_bytes()
    assert data.startswith(b"%PDF-")
    assert len(re.findall(rb"/Type\s*/Page\b", data)) == 10
