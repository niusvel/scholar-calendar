from datetime import time
from itertools import pairwise

import pytest

from scholar_calendar.models import PlanningInput, build_daily_periods, build_slots
from scholar_calendar.timeline import daily_rows


def test_start_can_align_two_lessons_with_the_break():
    periods = build_daily_periods(start=time(8, 30), period_count=3)
    assert periods == (
        (time(8, 30), time(9, 15)),
        (time(9, 20), time(10, 5)),
        (time(10, 25), time(11, 10)),
    )


@pytest.mark.parametrize("start", [time(10, 5), time(10, 15)])
def test_start_at_or_inside_break_moves_to_its_end(start):
    assert build_daily_periods(start=start, period_count=1)[0] == (time(10, 25), time(11, 10))


def test_lunch_after_configured_period_works():
    periods = build_daily_periods(
        period_count=3, lunch_start=time(12), lunch_end=time(13), lunch_after_period=2
    )
    assert periods[2] == (time(13), time(13, 45))


def test_lunch_does_not_move_later_lessons_backwards():
    periods = build_daily_periods(
        period_count=8, lunch_start=time(11), lunch_end=time(12), lunch_after_period=6
    )
    assert all(left[1] < right[0] for left, right in pairwise(periods))
    assert all(not (start < time(12) and end > time(11)) for start, end in periods)


@pytest.mark.parametrize(
    "options",
    [
        {"break_end": None},
        {"break_start": time(11), "break_end": time(10)},
        {"lunch_start": time(10, 15), "lunch_end": time(11)},
        {"duration_minutes": 0},
        {"transition_minutes": -1},
        {"start": time(23, 30), "period_count": 1},
    ],
)
def test_invalid_clock_has_a_validation_error(options):
    with pytest.raises(ValueError):
        build_daily_periods(**options)


def test_preview_accounts_for_every_minute_and_distinguishes_free_time():
    planning = PlanningInput(
        weeks=1,
        subjects=(),
        teachers=(),
        classrooms=(),
        teacher_subjects={},
        teacher_classrooms={},
        class_start=time(8),
        slots=build_slots(
            weeks=1, days=1, daily_periods=build_daily_periods(start=time(8), period_count=3)
        ),
    )
    rows = daily_rows(planning, 1, 1)
    assert [(row.start, row.end, row.label) for row in rows if row.period is None] == [
        (time(8, 45), time(8, 50), "Cambio de clase"),
        (time(9, 35), time(9, 40), "Cambio de clase"),
        (time(9, 40), time(10, 5), "Tiempo libre"),
        (time(10, 5), time(10, 25), "Merienda"),
    ]
    assert all(left.end == right.start for left, right in pairwise(rows))


def test_break_is_one_row_when_transition_overlaps_it():
    planning = PlanningInput(
        weeks=1,
        subjects=(),
        teachers=(),
        classrooms=(),
        teacher_subjects={},
        teacher_classrooms={},
        class_start=time(8, 30),
        slots=build_slots(
            weeks=1, days=1, daily_periods=build_daily_periods(start=time(8, 30), period_count=3)
        ),
    )
    breaks = [row for row in daily_rows(planning, 1, 1) if row.label == "Merienda"]
    assert [(row.start, row.end) for row in breaks] == [(time(10, 5), time(10, 25))]
