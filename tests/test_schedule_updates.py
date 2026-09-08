from dataclasses import replace
from datetime import time

import pytest

from scholar_calendar.defaults import default_planning
from scholar_calendar.models import Classroom, Subject, Teacher
from scholar_calendar.schedule_updates import (
    ResourceRename,
    requires_regeneration,
    update_schedule_metadata,
)
from scholar_calendar.solver import Schedule, ScheduledLesson


@pytest.fixture
def generated():
    planning = replace(
        default_planning(),
        subjects=(Subject("A", 1), Subject("B", 1)),
        teachers=(Teacher("Ana"),),
        classrooms=(Classroom("1"),),
        teacher_subjects={"Ana": frozenset({"A", "B"})},
        teacher_unavailable_days={"Ana": frozenset({5})},
        subject_unavailable_days={"A": frozenset({2})},
        forbidden_parallel=frozenset({frozenset({"A", "B"})}),
    )
    return planning, Schedule((ScheduledLesson(1, 1, 1, "1", "A", "Ana", "08:30", "09:15"),))


def test_cosmetic_changes_update_names_references_and_course_without_moving_lessons(generated):
    planning, schedule = generated
    current = replace(
        planning,
        course_name="Curso nuevo",
        subjects=(Subject("Álgebra", 1), Subject("B", 1)),
        teachers=(Teacher("Ana María"),),
        classrooms=(Classroom("Grupo 1"),),
        teacher_subjects={"Ana María": frozenset({"Álgebra", "B"})},
        teacher_unavailable_days={"Ana María": frozenset({5})},
        subject_unavailable_days={"Álgebra": frozenset({2})},
        forbidden_parallel=frozenset({frozenset({"Álgebra", "B"})}),
    )
    renames = (
        ResourceRename("subject", "A", "Álgebra"),
        ResourceRename("teacher", "Ana", "Ana María"),
        ResourceRename("classroom", "1", "Grupo 1"),
    )
    updated, result = update_schedule_metadata(current, planning, schedule, renames)
    assert not requires_regeneration(current, updated)
    assert result.lessons == (
        replace(schedule.lessons[0], subject="Álgebra", teacher="Ana María", classroom="Grupo 1"),
    )
    assert updated == current


@pytest.mark.parametrize(
    "change",
    [
        {"subjects": (Subject("A", 2), Subject("B", 1))},
        {"subjects": (Subject("A", 1, True), Subject("B", 1))},
        {"teachers": (Teacher("Ana"), Teacher("Luis"))},
        {"teacher_subjects": {"Ana": frozenset({"A"})}},
        {"teacher_unavailable_days": {}},
        {"forbidden_parallel": frozenset()},
        {"class_start": time(9)},
        {"break_end": time(10, 30)},
        {"weeks": 2},
    ],
)
def test_generation_changes_are_not_applied_to_the_existing_schedule(generated, change):
    planning, schedule = generated
    current = replace(planning, **change)
    updated, result = update_schedule_metadata(current, planning, schedule)
    assert requires_regeneration(current, updated)
    assert updated is planning and result is schedule


def test_mixed_rename_and_frequency_change_stays_pending(generated):
    planning, schedule = generated
    current = replace(planning, subjects=(Subject("Álgebra", 2), Subject("B", 1)))
    updated, result = update_schedule_metadata(
        current, planning, schedule, (ResourceRename("subject", "A", "Álgebra"),)
    )
    assert requires_regeneration(current, updated)
    assert result is schedule and updated is planning


def test_empty_metadata_and_zero_day_counts_do_not_require_regeneration(generated):
    planning, _ = generated
    current = replace(
        planning,
        day_period_counts={**planning.day_period_counts, 6: 0},
        teacher_classrooms={"Ana": frozenset()},
    )
    assert not requires_regeneration(current, planning)


def test_renames_are_not_guessed_from_a_file(generated):
    planning, schedule = generated
    current = replace(
        planning,
        teachers=(Teacher("Eva"),),
        teacher_subjects={"Eva": frozenset({"A", "B"})},
        teacher_unavailable_days={"Eva": frozenset({5})},
    )
    updated, result = update_schedule_metadata(current, planning, schedule)
    assert requires_regeneration(current, updated)
    assert result is schedule
