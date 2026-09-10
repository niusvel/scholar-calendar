"""Combine legacy full-day blocks and recurring day/period restrictions."""

from collections import defaultdict
from dataclasses import replace

from .models import AvailabilityBlock, PlanningInput
from .timeline import DAY_NAMES


def all_blocks(planning: PlanningInput) -> frozenset[AvailabilityBlock]:
    blocks = set(planning.availability_blocks)
    for kind in ("teacher", "subject"):
        for name, days in (getattr(planning, f"{kind}_unavailable_days") or {}).items():
            blocks.update(AvailabilityBlock(day=day, **{kind: name}) for day in days)
    return frozenset(blocks)


def with_blocks(planning: PlanningInput, blocks: frozenset[AvailabilityBlock]) -> PlanningInput:
    teacher_days, subject_days = defaultdict(set), defaultdict(set)
    specific = set()
    for block in blocks:
        if (
            block.classroom is None
            and block.period is None
            and block.teacher is not None
            and block.subject is None
        ):
            teacher_days[block.teacher].add(block.day)
        elif (
            block.classroom is None
            and block.period is None
            and block.subject is not None
            and block.teacher is None
        ):
            subject_days[block.subject].add(block.day)
        else:
            specific.add(block)
    return replace(
        planning,
        teacher_unavailable_days={name: frozenset(days) for name, days in teacher_days.items()},
        subject_unavailable_days={name: frozenset(days) for name, days in subject_days.items()},
        availability_blocks=frozenset(specific),
    )


def block_key(block: AvailabilityBlock) -> tuple:
    return (
        block.teacher or "",
        block.subject or "",
        block.classroom or "",
        block.day,
        block.period or 0,
    )


def block_time(block: AvailabilityBlock) -> str:
    return (
        f"{DAY_NAMES[block.day]} · "
        + ("todo el día" if block.period is None else f"turno {block.period}")
        + (f" · aula {block.classroom}" if block.classroom is not None else "")
    )


def availability_index(planning: PlanningInput) -> dict:
    index = defaultdict(set)
    for block in all_blocks(planning):
        index[block.teacher, block.subject, block.classroom].add((block.day, block.period))
    return index


def is_blocked(
    index: dict, teacher: str, subject: str, day: int, period: int, classroom: str | None = None
) -> bool:
    return any(
        (day, None) in index.get((*key, room), ()) or (day, period) in index.get((*key, room), ())
        for key in ((teacher, None), (None, subject), (teacher, subject))
        for room in {None, classroom}
    )
