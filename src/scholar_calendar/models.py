from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from itertools import pairwise

from .clock import DEFAULT_CLASS_START, minutes_since_midnight


@dataclass(frozen=True)
class Subject:
    name: str
    # Historical attribute name; this value is the weekly frequency per classroom.
    lessons_per_cycle: int
    double_period: bool = False


@dataclass(frozen=True)
class Teacher:
    name: str


@dataclass(frozen=True)
class Classroom:
    name: str


@dataclass(frozen=True)
class PlanningSlot:
    week: int
    day: int
    period: int
    start: time
    end: time


@dataclass(frozen=True)
class PlanningInput:
    weeks: int
    subjects: tuple[Subject, ...]
    teachers: tuple[Teacher, ...]
    classrooms: tuple[Classroom, ...]
    slots: tuple[PlanningSlot, ...]
    teacher_subjects: dict[str, frozenset[str]]
    teacher_classrooms: dict[str, frozenset[str]]
    forbidden_consecutive: frozenset[frozenset[str]] = frozenset()
    forbidden_parallel: frozenset[frozenset[str]] = frozenset()
    course_name: str = ""
    day_period_counts: dict[int, int] | None = None
    saturday_weeks: frozenset[int] = frozenset()
    period_duration_minutes: int = 45
    transition_minutes: int = 5
    break_start: time | None = time(10, 5)
    break_end: time | None = time(10, 25)
    lunch_start: time | None = None
    lunch_end: time | None = None
    lunch_after_period: int = 6
    teacher_unavailable_days: dict[str, frozenset[int]] | None = None
    subject_unavailable_days: dict[str, frozenset[int]] | None = None
    class_start: time = DEFAULT_CLASS_START


def build_slots(
    *,
    weeks: int,
    days: int,
    daily_periods: tuple[tuple[time, time], ...],
    day_period_counts: dict[int, int] | None = None,
    saturday_weeks: frozenset[int] = frozenset(),
) -> tuple[PlanningSlot, ...]:
    """Build available slots; omitted intervals naturally represent breaks."""
    counts = day_period_counts or {day: len(daily_periods) for day in range(1, days + 1)}
    return tuple(
        PlanningSlot(
            week=week,
            day=day,
            period=period,
            start=start,
            end=end,
        )
        for week in range(1, weeks + 1)
        for day in range(1, min(days, 6) + 1)
        if day != 6 or week in saturday_weeks
        for period, (start, end) in enumerate(daily_periods[: max(0, counts.get(day, 0))], start=1)
    )


def build_daily_periods(
    *,
    period_count: int = 6,
    duration_minutes: int = 45,
    transition_minutes: int = 5,
    start: time = DEFAULT_CLASS_START,
    break_start: time | None = time(10, 5),
    break_end: time | None = time(10, 25),
    lunch_start: time | None = None,
    lunch_end: time | None = None,
    lunch_after_period: int = 6,
) -> tuple[tuple[time, time], ...]:
    """Keep full lessons outside pauses, without moving the clock backwards."""
    if period_count < 0 or duration_minutes <= 0 or transition_minutes < 0:
        raise ValueError(
            "La duración debe ser positiva; los turnos y el cambio no pueden ser negativos."
        )
    if lunch_after_period < 0:
        raise ValueError("El turno anterior a la comida no puede ser negativo.")
    pauses = []
    for label, beginning, ending in (
        ("la merienda", break_start, break_end),
        ("la comida", lunch_start, lunch_end),
    ):
        if (beginning is None) != (ending is None):
            raise ValueError(f"Indica el inicio y el final de {label}, o deja ambos vacíos.")
        if beginning is not None and ending is not None:
            if beginning >= ending:
                raise ValueError(f"El final de {label} debe ser posterior al inicio.")
            pauses.append((minutes_since_midnight(beginning), minutes_since_midnight(ending)))
    pauses.sort()
    if any(left[1] > right[0] for left, right in pairwise(pauses)):
        raise ValueError("La merienda y la comida no pueden solaparse.")
    current = minutes_since_midnight(start)
    periods: list[tuple[time, time]] = []
    for period in range(1, period_count + 1):
        if lunch_end is not None and period == lunch_after_period + 1:
            current = max(current, minutes_since_midnight(lunch_end))
        for pause_start, pause_end in pauses:
            if current < pause_end and current + duration_minutes > pause_start:
                current = pause_end
        end = current + duration_minutes
        if end >= 24 * 60:
            raise ValueError(
                "La jornada debe terminar antes de medianoche. Reduce los turnos o su duración."
            )
        periods.append((time(*divmod(current, 60)), time(*divmod(end, 60))))
        current = end + transition_minutes
    return tuple(periods)
