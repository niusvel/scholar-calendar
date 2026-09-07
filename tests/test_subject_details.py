from dataclasses import replace
from datetime import time

from scholar_calendar.models import Classroom, PlanningInput, Subject, Teacher, build_slots
from scholar_calendar.solver import Schedule, ScheduledLesson
from scholar_calendar.subject_details import subject_restrictions


def sample():
    planning = PlanningInput(
        weeks=2,
        subjects=(Subject("Física", 3, True), Subject("Química", 1), Subject("Lengua", 1)),
        teachers=tuple(Teacher(name) for name in ("Ana", "Luis", "Marta", "Otro")),
        classrooms=(Classroom("Aula 1"), Classroom("Laboratorio")),
        teacher_subjects={
            "Ana": frozenset({"Física"}),
            "Luis": frozenset({"Física"}),
            "Marta": frozenset({"Física"}),
            "Otro": frozenset({"Lengua"}),
        },
        teacher_classrooms={"Ana": frozenset({"Laboratorio"}), "Luis": frozenset()},
        teacher_unavailable_days={
            "Ana": frozenset({3, 1}),
            "Luis": frozenset({5}),
            "Marta": frozenset({2}),
            "Otro": frozenset({4}),
        },
        subject_unavailable_days={"Física": frozenset({6}), "Lengua": frozenset({1})},
        forbidden_consecutive=frozenset({frozenset({"Física", "Química"})}),
        forbidden_parallel=frozenset({frozenset({"Lengua", "Física"})}),
        slots=build_slots(weeks=2, days=1, daily_periods=((time(8), time(8, 45)),)),
    )
    schedule = Schedule(
        (
            ScheduledLesson(1, 1, 1, "Laboratorio", "Física", "Ana", "08:00", "08:45"),
            ScheduledLesson(2, 1, 1, "Aula 1", "Física", "Luis", "08:00", "08:45"),
        )
    )
    return planning, schedule


def test_note_includes_subject_rules_and_all_relevant_teachers():
    planning, schedule = sample()
    lines = subject_restrictions(planning, schedule, "Física")
    assert "Por aula: 3 sesiones semanales." in lines
    assert any("Turnos dobles" in line for line in lines)
    assert "Asignatura no disponible: Sábado." in lines
    assert "No consecutiva en un aula con: Química." in lines
    assert "No simultánea entre aulas con: Lengua." in lines
    assert (
        "Ana (en este horario): no disponible Lunes, Miércoles; solo puede impartir en Laboratorio."
        in lines
    )
    assert "Luis (en este horario): no disponible Viernes." in lines
    assert "Marta (habilitado, sin clases en este ciclo): no disponible Martes." in lines
    assert not any("Otro" in line for line in lines)
    assert not any("Luis" in line and "solo puede impartir" in line for line in lines)


def test_regular_subject_without_optional_restrictions_shows_only_its_basic_rules():
    planning, schedule = sample()
    planning = replace(
        planning,
        subjects=(Subject("Física", 1),),
        forbidden_parallel=frozenset(),
        forbidden_consecutive=frozenset(),
        teacher_unavailable_days=None,
        subject_unavailable_days=None,
        teacher_classrooms={},
    )
    assert subject_restrictions(planning, schedule, "Física") == (
        "Por aula: 1 sesión semanal.",
        "Máximo una sesión al día en cada aula.",
    )
    assert subject_restrictions(planning, schedule, "Desconocida") == ()
