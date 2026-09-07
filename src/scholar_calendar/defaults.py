"""Default empty center, shared by desktop initialization and programmatic examples."""

from datetime import time

from .models import PlanningInput, build_daily_periods, build_slots


def default_planning() -> PlanningInput:
    day_period_counts = {day: 6 for day in range(1, 6)}
    periods = build_daily_periods(
        period_count=6,
        duration_minutes=45,
        transition_minutes=5,
        break_start=time(10, 5),
        break_end=time(10, 25),
        lunch_start=time(13, 40),
        lunch_end=time(15, 0),
        lunch_after_period=6,
    )
    return PlanningInput(
        weeks=1,
        subjects=(),
        teachers=(),
        classrooms=(),
        slots=build_slots(
            weeks=1, days=5, daily_periods=periods, day_period_counts=day_period_counts
        ),
        teacher_subjects={},
        teacher_classrooms={},
        course_name="",
        day_period_counts=day_period_counts,
        period_duration_minutes=45,
        transition_minutes=5,
        break_start=time(10, 5),
        break_end=time(10, 25),
        lunch_start=time(13, 40),
        lunch_end=time(15, 0),
        lunch_after_period=6,
        teacher_unavailable_days={},
        subject_unavailable_days={},
    )
