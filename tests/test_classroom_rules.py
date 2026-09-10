from collections import Counter
from dataclasses import replace

import pytest

from scholar_calendar.config import planning_from_dict, planning_to_dict
from scholar_calendar.defaults import default_planning
from scholar_calendar.models import Classroom, Subject, Teacher, build_daily_periods, build_slots
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
def scoped():
    return replace(
        default_planning(),
        subjects=(Subject("Matemáticas", 2, True, frozenset({"1, A"})), Subject("Lengua", 1)),
        teachers=(Teacher("Ana"), Teacher("Luis")),
        classrooms=(Classroom("1, A"), Classroom("2")),
        slots=build_slots(weeks=1, days=2, daily_periods=build_daily_periods(period_count=3)),
        teacher_subjects={
            teacher: frozenset({"Matemáticas", "Lengua"}) for teacher in ("Ana", "Luis")
        },
        teacher_subject_classrooms={
            "Ana": {"Matemáticas": frozenset({"1, A"}), "Lengua": frozenset({"2"})},
            "Luis": {"Matemáticas": frozenset({"2"}), "Lengua": frozenset({"1, A"})},
        },
    )


def test_solver_uses_different_rooms_per_subject_and_doubles_only_in_selected_room(scoped):
    schedule = solve(scoped)
    assert len(schedule.lessons) == 6
    for lesson in schedule.lessons:
        assert lesson.classroom in scoped.teacher_subject_classrooms[lesson.teacher][lesson.subject]
    math = [lesson for lesson in schedule.lessons if lesson.subject == "Matemáticas"]
    pairs = [lesson for lesson in math if lesson.classroom == "1, A"]
    singles = [lesson for lesson in math if lesson.classroom == "2"]
    assert len({lesson.day for lesson in pairs}) == 1
    assert pairs[1].period == pairs[0].period + 1
    assert len({lesson.day for lesson in singles}) == 2


def test_double_default_applies_to_all_rooms_and_empty_scope_to_none(scoped):
    for scope, expected_daily_max in ((None, 2), (frozenset(), 1)):
        planning = replace(
            scoped,
            subjects=(replace(scoped.subjects[0], double_classrooms=scope), scoped.subjects[1]),
        )
        counts = Counter(
            (lesson.classroom, lesson.day)
            for lesson in solve(planning).lessons
            if lesson.subject == "Matemáticas"
        )
        assert max(counts.values()) == expected_daily_max
        assert all(count == expected_daily_max for count in counts.values())


def test_general_room_limits_intersect_subject_limits(scoped):
    # Ana cannot teach Lengua in room 2 once her general access is limited to 1, A.
    with pytest.raises(ScheduleError, match="No hay profesor elegible para Lengua en 2"):
        solve(replace(scoped, teacher_classrooms={"Ana": frozenset({"1, A"})}))


def test_explicit_empty_pair_scope_does_not_revert_to_all_rooms(scoped):
    limits = {
        **scoped.teacher_subject_classrooms,
        "Ana": {"Matemáticas": frozenset(), "Lengua": frozenset({"2"})},
    }
    with pytest.raises(ScheduleError, match="No hay profesor elegible para Matemáticas en 1, A"):
        solve(replace(scoped, teacher_subject_classrooms=limits))


@pytest.mark.parametrize("rule", ["double", "association"])
def test_each_scope_change_requires_regeneration(scoped, rule):
    current = (
        replace(
            scoped,
            subjects=(replace(scoped.subjects[0], double_classrooms=None), scoped.subjects[1]),
        )
        if rule == "double"
        else replace(scoped, teacher_subject_classrooms={})
    )
    assert requires_regeneration(current, scoped)


@pytest.mark.parametrize(
    "change",
    [
        {"teacher_subject_classrooms": {"Desconocido": {"Matemáticas": frozenset({"2"})}}},
        {"teacher_subject_classrooms": {"Ana": {"Desconocida": frozenset({"2"})}}},
        {"teacher_subject_classrooms": {"Ana": {"Matemáticas": frozenset({"Desconocida"})}}},
        {
            "teacher_subjects": {
                "Ana": frozenset({"Lengua"}),
                "Luis": frozenset({"Matemáticas", "Lengua"}),
            }
        },
        {
            "subjects": (
                Subject("Matemáticas", 2, True, frozenset({"Desconocida"})),
                Subject("Lengua", 1),
            )
        },
    ],
)
def test_unknown_or_unassociated_references_are_rejected(scoped, change):
    with pytest.raises(ValueError):
        validate_planning(replace(scoped, **change))


def test_round_trip_preserves_scopes_in_configuration_and_generated_snapshot(scoped, tmp_path):
    schedule = solve(scoped)
    current = replace(
        scoped,
        teacher_subject_classrooms={"Ana": {"Lengua": frozenset()}},
        subjects=(replace(scoped.subjects[0], double_classrooms=frozenset()), scoped.subjects[1]),
    )
    path = tmp_path / "scoped.json"
    project = CalendarProject(current, scoped, schedule)
    save_project(project, path)
    assert load_project(path) == project
    assert requires_regeneration(current, scoped)
    legacy = planning_to_dict(scoped, include_slots=True)
    legacy.pop("teacher_subject_classrooms")
    for subject in legacy["subjects"]:
        subject.pop("double_classrooms")
    restored = planning_from_dict(legacy)
    assert restored.teacher_subject_classrooms == {}
    assert restored.subjects[0].is_double_in("2")


def test_scoped_rules_follow_all_resource_renames_without_moving_lessons(scoped):
    schedule = solve(scoped)
    current = replace(
        scoped,
        subjects=(Subject("Álgebra", 2, True, frozenset({"Grupo A"})), scoped.subjects[1]),
        teachers=(Teacher("Ana María"), Teacher("Luis")),
        classrooms=(Classroom("Grupo A"), Classroom("2")),
        teacher_subjects={
            teacher: frozenset({"Álgebra", "Lengua"}) for teacher in ("Ana María", "Luis")
        },
        teacher_subject_classrooms={
            "Ana María": {"Álgebra": frozenset({"Grupo A"}), "Lengua": frozenset({"2"})},
            "Luis": {"Álgebra": frozenset({"2"}), "Lengua": frozenset({"Grupo A"})},
        },
    )
    updated, renamed = update_schedule_metadata(
        current,
        scoped,
        schedule,
        (
            ResourceRename("subject", "Matemáticas", "Álgebra"),
            ResourceRename("teacher", "Ana", "Ana María"),
            ResourceRename("classroom", "1, A", "Grupo A"),
        ),
    )
    assert updated == current
    assert not requires_regeneration(current, updated)
    assert [(item.week, item.day, item.period) for item in renamed.lessons] == [
        (item.week, item.day, item.period) for item in schedule.lessons
    ]
    note = "\n".join(subject_restrictions(current, renamed, "Álgebra"))
    assert "Turnos dobles en Grupo A" in note
    assert "En las demás aulas: máximo una sesión al día" in note
    assert "para Álgebra, aulas permitidas: Grupo A" in note
