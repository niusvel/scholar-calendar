"""Readable daily rows shared by the clock preview, timetable and PDF."""

from dataclasses import dataclass
from datetime import time
from itertools import pairwise

from .clock import minutes_since_midnight
from .models import PlanningInput

DAY_NAMES = {1: "Lunes", 2: "Martes", 3: "Miércoles", 4: "Jueves", 5: "Viernes", 6: "Sábado"}


@dataclass(frozen=True)
class TimelineRow:
    start: time
    end: time
    label: str
    period: int | None = None

    @property
    def hours(self) -> str:
        return f"{self.start:%H:%M} – {self.end:%H:%M}"


def daily_rows(planning: PlanningInput, week: int, day: int) -> tuple[TimelineRow, ...]:
    slots = sorted(
        (slot for slot in planning.slots if slot.week == week and slot.day == day),
        key=lambda slot: slot.period,
    )
    rows = []
    previous = planning.class_start
    pauses = [
        (start, end, label)
        for start, end, label in (
            (planning.break_start, planning.break_end, "Merienda"),
            (planning.lunch_start, planning.lunch_end, "Comida"),
        )
        if start is not None and end is not None
    ]
    for slot in slots:
        if previous < slot.start:
            boundaries = {previous, slot.start}
            has_previous_lesson = bool(rows)
            transition_end = min(
                minutes_since_midnight(previous) + planning.transition_minutes,
                minutes_since_midnight(slot.start),
            )
            if has_previous_lesson and transition_end > minutes_since_midnight(previous):
                boundaries.add(time(*divmod(transition_end, 60)))
            for start, end, _ in pauses:
                boundaries.update(value for value in (start, end) if previous < value < slot.start)
            ordered = sorted(boundaries)
            for start, end in pairwise(ordered):
                label = next(
                    (
                        label
                        for beginning, ending, label in pauses
                        if beginning <= start and end <= ending
                    ),
                    None,
                )
                if label is None:
                    label = (
                        "Cambio de clase"
                        if has_previous_lesson and minutes_since_midnight(end) <= transition_end
                        else "Tiempo libre"
                    )
                if (
                    rows
                    and rows[-1].period is None
                    and rows[-1].label == label
                    and rows[-1].end == start
                ):
                    rows[-1] = TimelineRow(rows[-1].start, end, label)
                else:
                    rows.append(TimelineRow(start, end, label))
        rows.append(TimelineRow(slot.start, slot.end, f"Turno {slot.period:02d}", slot.period))
        previous = slot.end
    return tuple(rows)
