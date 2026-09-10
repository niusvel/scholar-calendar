from dataclasses import replace
from datetime import time
from unittest.mock import patch

import pytest
from ortools.sat.python import cp_model

from scholar_calendar.generation_diagnostics import DiagnosticRules
from scholar_calendar.models import (
    AvailabilityBlock,
    Classroom,
    PlanningInput,
    Subject,
    Teacher,
    build_slots,
)
from scholar_calendar.solver import ScheduleError, _build_model, solve


@pytest.fixture
def planning():
    return PlanningInput(
        weeks=1,
        subjects=(Subject("B", 1),),
        teachers=(Teacher("A"),),
        classrooms=(Classroom("C"),),
        slots=build_slots(
            weeks=1, days=1, daily_periods=((time(8), time(8, 45)), (time(8, 50), time(9, 35)))
        ),
        teacher_subjects={"A": frozenset({"B"})},
        teacher_classrooms={},
    )


def failure(planning):
    with pytest.raises(ScheduleError) as caught:
        solve(planning)
    assert caught.value.conflicts
    assert all(conflict.section for conflict in caught.value.conflicts)
    return str(caught.value)


def test_missing_association_and_excluded_classroom_have_different_guidance(planning):
    assert "Ningún profesor está asociado" in failure(replace(planning, teacher_subjects={}))
    restricted = replace(planning, teacher_subject_classrooms={"A": {"B": frozenset()}})
    message = failure(restricted)
    assert "No hay profesor elegible para B en C" in message
    assert "Los profesores asociados (A) no tienen permitida esta aula" in message


def test_frequency_exceeds_available_turns_identifies_week_room_and_counts(planning):
    message = failure(replace(planning, subjects=(Subject("B", 3),)))
    assert "B · C · semana 1" in message
    assert "Sesiones exigidas: 3" in message
    assert "Turnos de la semana: 2; días con clase: 1" in message


def test_single_period_distribution_conflict(planning):
    message = failure(replace(planning, subjects=(Subject("B", 2),)))
    assert "Modo sencillo" in message
    assert "Sesiones exigidas: 2" in message


def test_double_distribution_conflict_requires_consecutive_slots(planning):
    slots = tuple(
        replace(slot, day=index + 1, period=1) for index, slot in enumerate(planning.slots)
    )
    restricted = replace(planning, subjects=(Subject("B", 2, True),), slots=slots)
    assert "Modo doble" in failure(restricted)
    assert len(solve(replace(restricted, subjects=(Subject("B", 2),))).lessons) == 2


def test_shared_teacher_conflict_names_teacher_and_both_rooms(planning):
    restricted = replace(
        planning, classrooms=(Classroom("C"), Classroom("D")), slots=planning.slots[:1]
    )
    message = failure(restricted)
    assert "Profesor compartido: A" in message
    assert "B · C · semana 1" in message
    assert "B · D · semana 1" in message


def test_room_capacity_conflict_names_subjects_and_jornada(planning):
    restricted = replace(
        planning,
        subjects=(Subject("B", 1), Subject("Otra", 1)),
        teachers=(Teacher("A"), Teacher("Otro")),
        teacher_subjects={"A": frozenset({"B"}), "Otro": frozenset({"Otra"})},
        slots=planning.slots[:1],
    )
    message = failure(restricted)
    assert "Capacidad del aula C" in message
    assert "B · C" in message and "Otra · C" in message
    assert "semana 1: 1" in message


@pytest.mark.parametrize(
    "target", [{"teacher": "A"}, {"subject": "B"}, {"teacher": "A", "subject": "B"}]
)
def test_block_conflict_includes_day_turn_room_and_omits_irrelevant_blocks(planning, target):
    blocked = AvailabilityBlock(day=1, period=1, classroom="C", **target)
    restricted = replace(
        planning,
        slots=planning.slots[:1],
        availability_blocks=frozenset({blocked, AvailabilityBlock(day=5, teacher="A")}),
    )
    message = failure(restricted)
    assert "Lunes · turno 1 · aula C" in message
    assert "Viernes" not in message
    assert len(solve(replace(restricted, availability_blocks=frozenset())).lessons) == 1


def test_legacy_full_day_conflict(planning):
    assert "Lunes · todo el día · todas las aulas" in failure(
        replace(planning, teacher_unavailable_days={"A": frozenset({1})})
    )


def test_non_consecutive_conflict_is_named(planning):
    restricted = replace(
        planning,
        subjects=(Subject("B", 1), Subject("Otra", 1)),
        teacher_subjects={"A": frozenset({"B", "Otra"})},
        forbidden_consecutive=frozenset({frozenset({"B", "Otra"})}),
    )
    assert "No consecutivas: B y Otra · C" in failure(restricted)
    assert len(solve(replace(restricted, forbidden_consecutive=frozenset())).lessons) == 2


def test_parallel_conflict_across_rooms_is_named(planning):
    restricted = replace(
        planning,
        subjects=(Subject("B", 1), Subject("Otra", 1)),
        classrooms=(Classroom("C"), Classroom("D")),
        teachers=(Teacher("A"), Teacher("Otro")),
        teacher_subjects={"A": frozenset({"B", "Otra"}), "Otro": frozenset({"B", "Otra"})},
        availability_blocks=frozenset(
            AvailabilityBlock(day=1, period=period, subject=subject, classroom=room)
            for subject, room, period in (
                ("B", "C", 2),
                ("B", "D", 1),
                ("Otra", "C", 1),
                ("Otra", "D", 2),
            )
        ),
        forbidden_parallel=frozenset({frozenset({"B", "Otra"})}),
    )
    assert "No simultáneas: B y Otra" in failure(restricted)
    assert len(solve(replace(restricted, forbidden_parallel=frozenset())).lessons) == 4


def test_diagnostic_model_accepts_valid_schedule_even_if_preferences_are_violated(planning):
    restricted = replace(
        planning,
        subjects=(Subject("B", 2, True),),
        slots=tuple(replace(slot, period=slot.period + 4) for slot in planning.slots),
    )
    assert len(solve(restricted).lessons) == 2
    model, _, rules = _build_model(restricted, diagnostic=True)
    assert cp_model.CpSolver().Solve(model) in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert rules.explain() == ()


def test_diagnostic_timeout_does_not_invent_causes(planning):
    with (
        patch.object(DiagnosticRules, "explain", return_value=()),
        pytest.raises(ScheduleError) as caught,
    ):
        solve(replace(planning, subjects=(Subject("B", 3),)))
    assert "no se ha podido aislar" in str(caught.value)
    assert not caught.value.conflicts


def test_unknown_and_invalid_statuses_never_claim_a_proven_conflict(planning):
    for status in (cp_model.UNKNOWN, cp_model.MODEL_INVALID):
        with (
            patch.object(cp_model.CpSolver, "Solve", return_value=status),
            patch.object(DiagnosticRules, "explain") as explain,
            pytest.raises(ScheduleError) as caught,
        ):
            solve(planning)
        assert "no se ha demostrado" in str(caught.value).lower()
        assert not caught.value.conflicts
        explain.assert_not_called()


def test_core_reduction_keeps_rules_if_a_trial_times_out():
    model = cp_model.CpModel()
    rules = DiagnosticRules(model, enabled=True)
    x = model.NewBoolVar("x")
    rules.enforce(model.Add(x == 0), ("a",), "Cero", "x = 0", "A")
    rules.enforce(model.Add(x == 1), ("b",), "Uno", "x = 1", "B")
    original_solve = cp_model.CpSolver.Solve
    calls = 0

    def first_then_timeout(solver, *args, **kwargs):
        nonlocal calls
        calls += 1
        return original_solve(solver, *args, **kwargs) if calls == 1 else cp_model.UNKNOWN

    with patch.object(cp_model.CpSolver, "Solve", first_then_timeout):
        assert {item.title for item in rules.explain()} == {"Cero", "Uno"}
