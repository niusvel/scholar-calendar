"""Distinguish cosmetic edits from changes that require a new allocation."""

from dataclasses import dataclass, replace
from typing import Literal

from .availability import all_blocks
from .models import PlanningInput
from .solver import Schedule


@dataclass(frozen=True)
class ResourceRename:
    kind: Literal["subject", "teacher", "classroom"]
    before: str
    after: str


def generation_signature(planning: PlanningInput) -> tuple:
    """Compare generation inputs, ignoring course title, ordering and empty metadata."""
    counts = planning.day_period_counts
    if counts is None:
        counts = {
            day: max((slot.period for slot in planning.slots if slot.day == day), default=0)
            for day in range(1, 7)
        }
    return (
        planning.weeks,
        tuple(
            sorted(
                (
                    subject.name,
                    subject.lessons_per_cycle,
                    subject.double_period,
                    subject.double_classrooms if subject.double_period else None,
                )
                for subject in planning.subjects
            )
        ),
        frozenset(teacher.name for teacher in planning.teachers),
        frozenset(room.name for room in planning.classrooms),
        frozenset(planning.slots),
        frozenset(
            (name, frozenset(values))
            for name, values in planning.teacher_subjects.items()
            if values
        ),
        frozenset(
            (name, frozenset(values))
            for name, values in planning.teacher_classrooms.items()
            if values
        ),
        planning.forbidden_consecutive,
        frozenset(
            (teacher, subject, frozenset(rooms))
            for teacher, subjects in planning.teacher_subject_classrooms.items()
            for subject, rooms in subjects.items()
        ),
        planning.forbidden_parallel,
        frozenset((day, count) for day, count in counts.items() if count),
        planning.saturday_weeks,
        planning.class_start,
        planning.period_duration_minutes,
        planning.transition_minutes,
        planning.break_start,
        planning.break_end,
        planning.lunch_start,
        planning.lunch_end,
        planning.lunch_after_period,
        all_blocks(planning),
    )


def requires_regeneration(current: PlanningInput, generated: PlanningInput) -> bool:
    return generation_signature(current) != generation_signature(generated)


def _rename_planning(planning: PlanningInput, rename: ResourceRename) -> PlanningInput:
    def name(value):
        return rename.after if value == rename.before else value

    def keys(mapping):
        return {name(key): value for key, value in (mapping or {}).items()}

    def values(mapping):
        return {key: frozenset(name(value) for value in items) for key, items in mapping.items()}

    planning = replace(
        planning,
        availability_blocks=frozenset(
            replace(block, **{rename.kind: name(getattr(block, rename.kind))})
            for block in planning.availability_blocks
        ),
    )

    if rename.kind == "subject":
        return replace(
            planning,
            subjects=tuple(replace(item, name=name(item.name)) for item in planning.subjects),
            teacher_subjects=values(planning.teacher_subjects),
            teacher_subject_classrooms={
                teacher: keys(subjects)
                for teacher, subjects in planning.teacher_subject_classrooms.items()
            },
            subject_unavailable_days=keys(planning.subject_unavailable_days),
            forbidden_consecutive=frozenset(
                frozenset(name(value) for value in pair) for pair in planning.forbidden_consecutive
            ),
            forbidden_parallel=frozenset(
                frozenset(name(value) for value in pair) for pair in planning.forbidden_parallel
            ),
        )
    if rename.kind == "teacher":
        return replace(
            planning,
            teachers=tuple(replace(item, name=name(item.name)) for item in planning.teachers),
            teacher_subjects=keys(planning.teacher_subjects),
            teacher_classrooms=keys(planning.teacher_classrooms),
            teacher_subject_classrooms=keys(planning.teacher_subject_classrooms),
            teacher_unavailable_days=keys(planning.teacher_unavailable_days),
        )
    return replace(
        planning,
        classrooms=tuple(replace(item, name=name(item.name)) for item in planning.classrooms),
        teacher_classrooms=values(planning.teacher_classrooms),
        teacher_subject_classrooms={
            teacher: values(subjects)
            for teacher, subjects in planning.teacher_subject_classrooms.items()
        },
        subjects=tuple(
            replace(
                subject,
                double_classrooms=frozenset(name(room) for room in subject.double_classrooms),
            )
            if subject.double_classrooms is not None
            else subject
            for subject in planning.subjects
        ),
    )


def update_schedule_metadata(
    current: PlanningInput,
    generated: PlanningInput,
    schedule: Schedule,
    renames: tuple[ResourceRename, ...] = (),
) -> tuple[PlanningInput, Schedule]:
    """Apply recorded renames only when the resulting generation inputs still match.

    Mixed edits keep the old allocation and its original rules for consultation.
    Renames are never guessed from the relative positions of resources in a file.
    """
    candidate = generated
    for rename in renames:
        candidate = _rename_planning(candidate, rename)
    if requires_regeneration(current, candidate):
        return (
            generated
            if generated.course_name == current.course_name
            else replace(generated, course_name=current.course_name),
            schedule,
        )
    lessons = list(schedule.lessons)
    for rename in renames:
        lessons = [
            replace(lesson, **{rename.kind: rename.after})
            if getattr(lesson, rename.kind) == rename.before
            else lesson
            for lesson in lessons
        ]
    return (
        candidate
        if candidate.course_name == current.course_name
        else replace(candidate, course_name=current.course_name),
        schedule
        if tuple(lessons) == schedule.lessons
        else replace(schedule, lessons=tuple(lessons)),
    )
