from dataclasses import replace
from datetime import time

import pytest

from scholar_calendar.availability import all_blocks, availability_index, is_blocked, with_blocks
from scholar_calendar.config import planning_from_dict, planning_to_dict
from scholar_calendar.defaults import default_planning
from scholar_calendar.models import AvailabilityBlock, Classroom, PlanningSlot, Subject, Teacher
from scholar_calendar.project_file import CalendarProject, load_project, save_project
from scholar_calendar.schedule_updates import (
    ResourceRename,
    requires_regeneration,
    update_schedule_metadata,
)
from scholar_calendar.solver import ScheduleError, solve
from scholar_calendar.subject_details import subject_restrictions
from scholar_calendar.validation import validate_planning


@pytest.fixture
def planning():
    return replace(
        default_planning(),
        weeks=2,
        subjects=(Subject("B", 1), Subject("C", 1)),
        teachers=(Teacher("A"), Teacher("Otro")),
        classrooms=(Classroom("1"), Classroom("2")),
        teacher_subjects={"A": frozenset({"B", "C"}), "Otro": frozenset({"B"})},
        slots=tuple(
            PlanningSlot(week, 2, period, start, end)
            for week in (1, 2)
            for period, start, end in ((4, time(10, 25), time(11, 10)), (5, time(11, 15), time(12)))
        ),
    )


def test_pair_block_allows_other_subjects_and_teachers_in_same_period_every_week(planning):
    restricted = replace(
        planning,
        availability_blocks=frozenset(
            {AvailabilityBlock(day=2, period=4, teacher="A", subject="B")}
        ),
    )
    result = solve(restricted)
    assert len(result.lessons) == 8
    assert not any(
        item.teacher == "A" and item.subject == "B" and item.day == 2 and item.period == 4
        for item in result.lessons
    )
    for week in (1, 2):
        assert any(
            item.week == week and item.teacher == "A" and item.subject == "C" and item.period == 4
            for item in result.lessons
        )
        assert any(
            item.week == week
            and item.teacher == "Otro"
            and item.subject == "B"
            and item.period == 4
            for item in result.lessons
        )
    index = availability_index(restricted)
    assert not is_blocked(index, "A", "B", 2, 5)
    assert not is_blocked(index, "A", "B", 3, 4)


@pytest.mark.parametrize("target", [{"teacher": "A"}, {"subject": "B"}])
def test_general_period_blocks_apply_to_all_subjects_or_teachers(planning, target):
    restricted = replace(
        planning, availability_blocks=frozenset({AvailabilityBlock(day=2, period=4, **target)})
    )
    # Both rooms need C with A and B; losing either resource in period 4 makes this impossible.
    with pytest.raises(ScheduleError):
        solve(restricted)


def test_legacy_and_granular_blocks_accumulate_and_do_not_override_each_other(planning):
    restricted = replace(
        planning,
        teacher_unavailable_days={"A": frozenset({1})},
        subject_unavailable_days={"C": frozenset({3})},
        availability_blocks=frozenset(
            {
                AvailabilityBlock(day=2, period=4, teacher="A", subject="B"),
                AvailabilityBlock(day=5, teacher="A", subject="C"),
            }
        ),
    )
    index = availability_index(restricted)
    assert is_blocked(index, "A", "B", 1, 5)
    assert is_blocked(index, "A", "C", 3, 4)
    assert is_blocked(index, "A", "B", 2, 4)
    assert is_blocked(index, "A", "C", 5, 100)
    assert not is_blocked(index, "A", "B", 5, 4)
    assert not is_blocked(index, "Otro", "B", 2, 4)
    assert all_blocks(with_blocks(restricted, all_blocks(restricted))) == all_blocks(restricted)


@pytest.mark.parametrize(
    "block",
    [
        AvailabilityBlock(day=2, period=4),
        AvailabilityBlock(day=7, teacher="A"),
        AvailabilityBlock(day=True, teacher="A"),
        AvailabilityBlock(day=2, period=0, teacher="A"),
        AvailabilityBlock(day=2, period=-1, teacher="A"),
        AvailabilityBlock(day=2, period=True, teacher="A"),
        AvailabilityBlock(day=2, teacher="Desconocido"),
        AvailabilityBlock(day=2, subject="Desconocida"),
        AvailabilityBlock(day=2, teacher="Otro", subject="C"),
    ],
)
def test_invalid_blocks_are_rejected(planning, block):
    with pytest.raises(ValueError):
        validate_planning(replace(planning, availability_blocks=frozenset({block})))


def test_project_round_trip_preserves_current_and_generated_rules(planning, tmp_path):
    generated = replace(
        planning,
        availability_blocks=frozenset(
            {AvailabilityBlock(day=2, period=4, teacher="A", subject="B")}
        ),
    )
    current = replace(
        generated,
        availability_blocks=generated.availability_blocks
        | {AvailabilityBlock(day=6, period=9, subject="C")},
    )
    path = tmp_path / "availability.json"
    project = CalendarProject(current, generated, solve(generated))
    save_project(project, path)
    assert load_project(path) == project
    assert requires_regeneration(current, generated)
    assert requires_regeneration(generated, planning)
    legacy = planning_to_dict(planning, include_slots=True)
    legacy.pop("availability_blocks")
    assert planning_from_dict(legacy).availability_blocks == frozenset()
    # Rules for a currently absent period remain available if the school day grows later.
    assert planning_from_dict(planning_to_dict(current, include_slots=True)) == current


def test_renames_update_pair_blocks_and_notes_without_regenerating(planning):
    planning = replace(
        planning,
        availability_blocks=frozenset(
            {AvailabilityBlock(day=2, period=4, teacher="A", subject="B")}
        ),
    )
    schedule = solve(planning)
    current = replace(
        planning,
        teachers=(Teacher("Ana"), Teacher("Otro")),
        subjects=(Subject("Biología", 1), Subject("C", 1)),
        teacher_subjects={"Ana": frozenset({"Biología", "C"}), "Otro": frozenset({"Biología"})},
        availability_blocks=frozenset(
            {AvailabilityBlock(day=2, period=4, teacher="Ana", subject="Biología")}
        ),
    )
    updated, renamed = update_schedule_metadata(
        current,
        planning,
        schedule,
        (ResourceRename("teacher", "A", "Ana"), ResourceRename("subject", "B", "Biología")),
    )
    assert updated == current
    assert not requires_regeneration(current, updated)
    note = "\n".join(subject_restrictions(updated, renamed, "Biología"))
    assert "al impartir Biología, no disponible Martes · turno 4" in note
    assert "al impartir Biología" not in "\n".join(subject_restrictions(updated, renamed, "C"))


@pytest.mark.parametrize(
    "target", [{"teacher": "A"}, {"subject": "B"}, {"teacher": "A", "subject": "B"}]
)
@pytest.mark.parametrize("period", [4, None])
def test_classroom_blocks_preserve_other_rooms_and_full_day_scope(planning, target, period):
    block = AvailabilityBlock(day=2, period=period, classroom="1", **target)
    restricted = with_blocks(planning, frozenset({block}))
    assert restricted.availability_blocks == frozenset({block})
    assert not restricted.teacher_unavailable_days
    assert not restricted.subject_unavailable_days
    index = availability_index(restricted)
    assert is_blocked(index, "A", "B", 2, 4, "1")
    assert not is_blocked(index, "A", "B", 2, 4, "2")
    assert is_blocked(index, "A", "B", 2, 5, "1") == (period is None)
    assert all_blocks(with_blocks(restricted, all_blocks(restricted))) == frozenset({block})
    assert planning_from_dict(planning_to_dict(restricted, include_slots=True)) == restricted


@pytest.mark.parametrize(
    "target", [{"teacher": "A"}, {"subject": "B"}, {"teacher": "A", "subject": "B"}]
)
def test_solver_applies_room_blocks_without_excluding_other_rooms(planning, target):
    restricted = replace(
        planning,
        subjects=(Subject("B", 1),),
        teachers=(Teacher("A"),),
        teacher_subjects={"A": frozenset({"B"})},
        availability_blocks=frozenset(
            {AvailabilityBlock(day=2, period=4, classroom="1", **target)}
        ),
    )
    result = solve(restricted)
    for week in (1, 2):
        assert {
            (lesson.classroom, lesson.period) for lesson in result.lessons if lesson.week == week
        } == {("1", 5), ("2", 4)}


def test_different_periods_by_day_and_room_accumulate_with_global_rules(planning):
    blocks = frozenset(
        AvailabilityBlock(day=day, period=period, teacher="A", subject="B", classroom="1")
        for day, period in ((1, 4), (1, 5), (2, 4), (2, 5), (4, 5))
    )
    restricted = replace(
        planning, availability_blocks=blocks | {AvailabilityBlock(day=5, teacher="A")}
    )
    index = availability_index(restricted)
    for day in (1, 2, 4):
        for period in (4, 5):
            assert is_blocked(index, "A", "B", day, period, "1") == (day != 4 or period == 5)
            assert not is_blocked(index, "A", "B", day, period, "2")
            assert not is_blocked(index, "A", "C", day, period, "1")
            assert not is_blocked(index, "Otro", "B", day, period, "1")
    assert is_blocked(index, "A", "B", 5, 4, "1")
    assert is_blocked(index, "A", "B", 5, 4, "2")
    with pytest.raises(ValueError):
        validate_planning(
            replace(
                planning,
                availability_blocks=frozenset(
                    {AvailabilityBlock(day=1, teacher="A", classroom="Desconocida")}
                ),
            )
        )


def test_room_rename_updates_blocks_notes_and_generated_snapshot(planning, tmp_path):
    block = AvailabilityBlock(day=2, period=4, teacher="A", subject="B", classroom="1")
    planning = replace(planning, availability_blocks=frozenset({block}))
    schedule = solve(planning)
    current = replace(
        planning,
        classrooms=(Classroom("Nueva"), Classroom("2")),
        availability_blocks=frozenset({replace(block, classroom="Nueva")}),
    )
    updated, renamed = update_schedule_metadata(
        current, planning, schedule, (ResourceRename("classroom", "1", "Nueva"),)
    )
    assert not requires_regeneration(current, updated)
    assert "Martes · turno 4 · aula Nueva" in "\n".join(subject_restrictions(updated, renamed, "B"))
    assert requires_regeneration(
        replace(current, availability_blocks=frozenset({replace(block, classroom="2")})), updated
    )
    path = tmp_path / "aulas.json"
    project = CalendarProject(current, updated, renamed)
    save_project(project, path)
    assert load_project(path) == project
    legacy = planning_to_dict(planning, include_slots=True)
    del legacy["availability_blocks"][0]["classroom"]
    assert planning_from_dict(legacy).availability_blocks == frozenset(
        {replace(block, classroom=None)}
    )
