"""Configuration conversion, including legacy intervals and optional exact weekly slots."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import time
from itertools import pairwise
from pathlib import Path
from typing import Any

from .availability import block_key
from .clock import DEFAULT_CLASS_START, minutes_since_midnight
from .models import (
    AvailabilityBlock,
    Classroom,
    PlanningInput,
    PlanningSlot,
    Subject,
    Teacher,
    build_daily_periods,
    build_slots,
)
from .storage import write_json
from .validation import validate_planning

NULLABLE_FIELDS = ("day_period_counts", "teacher_unavailable_days", "subject_unavailable_days")


def _parse_time(value: str) -> time:
    hour, minute = (int(part) for part in value.split(":", maxsplit=1))
    return time(hour, minute)


def _optional_time(value: str | None) -> time | None:
    return _parse_time(value) if value else None


def load_planning(path: str | Path) -> PlanningInput:
    return planning_from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def planning_from_dict(data: dict[str, Any]) -> PlanningInput:
    """Read legacy daily intervals or exact slots; validate before exposing the model."""
    explicit_periods = tuple(
        (_parse_time(period["start"]), _parse_time(period["end"]))
        for period in data.get("daily_periods", [])
    )
    clock = data.get("clock", {})
    default_start = (
        explicit_periods[0][0].strftime("%H:%M")
        if explicit_periods
        else DEFAULT_CLASS_START.strftime("%H:%M")
    )
    class_start = _parse_time(clock.get("start", default_start))
    default_duration = 45
    default_transition = 5
    if explicit_periods:
        default_duration = minutes_since_midnight(explicit_periods[0][1]) - minutes_since_midnight(
            explicit_periods[0][0]
        )
        if len(explicit_periods) > 1:
            default_transition = min(
                minutes_since_midnight(right[0]) - minutes_since_midnight(left[1])
                for left, right in pairwise(explicit_periods)
            )
    pauses = {
        name: _optional_time(clock.get(name, default))
        for name, default in (
            ("break_start", "10:05"),
            ("break_end", "10:25"),
            ("lunch_start", "13:40"),
            ("lunch_end", "15:00"),
        )
    }
    daily_periods = explicit_periods or build_daily_periods(
        period_count=int(clock.get("periods_per_day", 6)),
        duration_minutes=int(clock.get("period_minutes", 45)),
        transition_minutes=int(clock.get("transition_minutes", 5)),
        start=class_start,
        **pauses,
        lunch_after_period=int(clock.get("lunch_after_period", 6)),
    )
    weeks = int(data["weeks"])
    day_period_counts = {
        int(day): int(count)
        for day, count in (data.get("day_period_counts") or {}).items()
        if int(day) != 7
    }
    if not day_period_counts:
        day_period_counts = {
            day: len(daily_periods) for day in range(1, min(6, int(data.get("days", 5))) + 1)
        }
    saturday_weeks = frozenset(int(week) for week in data.get("saturday_weeks", []))
    planning = PlanningInput(
        weeks=weeks,
        availability_blocks=frozenset(
            AvailabilityBlock(**item) for item in data.get("availability_blocks", [])
        ),
        subjects=tuple(
            Subject(
                item["name"],
                int(item.get("lessons_per_week", item.get("lessons_per_cycle", 0))),
                bool(item.get("double_period", False)),
                None
                if item.get("double_classrooms") is None
                else frozenset(item["double_classrooms"]),
            )
            for item in data["subjects"]
        ),
        teachers=tuple(Teacher(item["name"]) for item in data["teachers"]),
        classrooms=tuple(Classroom(item["name"]) for item in data["classrooms"]),
        slots=slots_from_dict(data["slots"])
        if "slots" in data
        else build_slots(
            weeks=weeks,
            days=min(6, max(day_period_counts, default=5)),
            daily_periods=daily_periods,
            day_period_counts=day_period_counts,
            saturday_weeks=saturday_weeks,
        ),
        teacher_subjects={
            name: frozenset(subjects) for name, subjects in data["teacher_subjects"].items()
        },
        teacher_classrooms={
            name: frozenset(classrooms) for name, classrooms in data["teacher_classrooms"].items()
        },
        teacher_subject_classrooms={
            teacher: {subject: frozenset(rooms) for subject, rooms in subjects.items()}
            for teacher, subjects in data.get("teacher_subject_classrooms", {}).items()
        },
        forbidden_consecutive=frozenset(
            frozenset(pair) for pair in data.get("forbidden_consecutive", [])
        ),
        forbidden_parallel=frozenset(
            frozenset(pair) for pair in data.get("forbidden_parallel", [])
        ),
        course_name=str(data.get("course_name", "")),
        class_start=class_start,
        **pauses,
        day_period_counts=None
        if "day_period_counts" in data and data["day_period_counts"] is None
        else day_period_counts,
        saturday_weeks=saturday_weeks,
        period_duration_minutes=int(clock.get("period_minutes", default_duration)),
        transition_minutes=int(clock.get("transition_minutes", default_transition)),
        lunch_after_period=int(clock.get("lunch_after_period", 6)),
        **{
            field: None
            if field in data and data[field] is None
            else {name: frozenset(days) for name, days in data.get(field, {}).items()}
            for field in ("teacher_unavailable_days", "subject_unavailable_days")
        },
    )
    validate_planning(planning)
    return planning


def planning_to_dict(planning: PlanningInput, *, include_slots: bool = False) -> dict[str, Any]:
    """Serialize configuration; include_slots preserves irregular cycles exactly."""
    periods: list[dict[str, str]] = []
    seen_periods: set[tuple[str, str]] = set()
    for slot in planning.slots:
        period = (slot.start.strftime("%H:%M"), slot.end.strftime("%H:%M"))
        if period not in seen_periods:
            seen_periods.add(period)
            periods.append({"start": period[0], "end": period[1]})

    data: dict[str, Any] = {
        "availability_blocks": [
            asdict(block) for block in sorted(planning.availability_blocks, key=block_key)
        ],
        "course_name": planning.course_name,
        "weeks": planning.weeks,
        "days": max((slot.day for slot in planning.slots), default=5),
        "daily_periods": periods,
        "clock": {
            "start": planning.class_start.strftime("%H:%M"),
            "periods_per_day": max((planning.day_period_counts or {}).values(), default=6),
            "period_minutes": planning.period_duration_minutes,
            "transition_minutes": planning.transition_minutes,
            "break_start": planning.break_start.strftime("%H:%M") if planning.break_start else None,
            "break_end": planning.break_end.strftime("%H:%M") if planning.break_end else None,
            "lunch_start": planning.lunch_start.strftime("%H:%M") if planning.lunch_start else None,
            "lunch_end": planning.lunch_end.strftime("%H:%M") if planning.lunch_end else None,
            "lunch_after_period": planning.lunch_after_period,
        },
        "day_period_counts": {
            str(day): count
            for day, count in sorted((planning.day_period_counts or {}).items())
            if day != 7
        },
        "saturday_weeks": sorted(planning.saturday_weeks),
        "subjects": [
            {
                "name": subject.name,
                "lessons_per_week": subject.lessons_per_cycle,
                "double_period": subject.double_period,
                "double_classrooms": None
                if subject.double_classrooms is None
                else sorted(subject.double_classrooms),
            }
            for subject in planning.subjects
        ],
        "teachers": [{"name": teacher.name} for teacher in planning.teachers],
        "classrooms": [{"name": classroom.name} for classroom in planning.classrooms],
        "teacher_subjects": {
            name: sorted(subjects) for name, subjects in planning.teacher_subjects.items()
        },
        "teacher_classrooms": {
            name: sorted(classrooms) for name, classrooms in planning.teacher_classrooms.items()
        },
        "teacher_subject_classrooms": {
            teacher: {subject: sorted(rooms) for subject, rooms in subjects.items()}
            for teacher, subjects in planning.teacher_subject_classrooms.items()
        },
        "forbidden_consecutive": sorted(sorted(pair) for pair in planning.forbidden_consecutive),
        "forbidden_parallel": sorted(sorted(pair) for pair in planning.forbidden_parallel),
        "teacher_unavailable_days": {
            name: sorted(days) for name, days in (planning.teacher_unavailable_days or {}).items()
        },
        "subject_unavailable_days": {
            name: sorted(days) for name, days in (planning.subject_unavailable_days or {}).items()
        },
    }
    if include_slots:
        data["slots"] = slots_to_dict(planning.slots)
        for field in NULLABLE_FIELDS:
            if getattr(planning, field) is None:
                data[field] = None
    return data


def slots_to_dict(slots: tuple[PlanningSlot, ...]) -> list[dict[str, Any]]:
    return [
        {**asdict(slot), "start": slot.start.isoformat(), "end": slot.end.isoformat()}
        for slot in slots
    ]


def slots_from_dict(data: list[dict[str, Any]]) -> tuple[PlanningSlot, ...]:
    return tuple(
        PlanningSlot(
            week=item["week"],
            day=item["day"],
            period=item["period"],
            start=time.fromisoformat(item["start"]),
            end=time.fromisoformat(item["end"]),
        )
        for item in data
    )


def save_planning(planning: PlanningInput, path: str | Path) -> None:
    """Save a standalone configuration atomically, including its exact slots."""
    validate_planning(planning)
    write_json(planning_to_dict(planning, include_slots=True), path)
