"""Structural checks shared by file loading and scheduling, without a UI dependency."""

from collections import defaultdict
from itertools import pairwise

from .models import PlanningInput, build_daily_periods


def validate_planning(planning: PlanningInput) -> None:
    """Allow incomplete centers, but reject invalid clocks, references and slots."""
    if type(planning.weeks) is not int or not 1 <= planning.weeks <= 52:
        raise ValueError("Indica entre 1 y 52 semanas para el ciclo.")
    names = []
    for label, resources in (
        ("asignaturas", planning.subjects),
        ("profesores", planning.teachers),
        ("aulas", planning.classrooms),
    ):
        values = [resource.name for resource in resources]
        if any(not isinstance(name, str) or not name.strip() for name in values):
            raise ValueError(f"Los nombres de {label} no pueden estar vacíos.")
        if len(set(values)) != len(values):
            raise ValueError(f"Hay nombres de {label} duplicados.")
        names.append(set(values))
    subjects, teachers, classrooms = names
    for subject in planning.subjects:
        if type(subject.lessons_per_cycle) is not int or subject.lessons_per_cycle < 0:
            raise ValueError("La frecuencia semanal debe ser un entero no negativo.")
    for links, allowed in (
        (planning.teacher_subjects, subjects),
        (planning.teacher_classrooms, classrooms),
    ):
        if any(
            teacher not in teachers or not set(values) <= allowed
            for teacher, values in links.items()
        ):
            raise ValueError("Una asociación hace referencia a un recurso desconocido.")
    for rules, allowed in (
        (planning.teacher_unavailable_days or {}, teachers),
        (planning.subject_unavailable_days or {}, subjects),
    ):
        if any(
            name not in allowed or any(type(day) is not int or not 1 <= day <= 6 for day in days)
            for name, days in rules.items()
        ):
            raise ValueError(
                "Un bloqueo contiene un recurso desconocido o un día fuera de lunes a sábado."
            )
    for rules in (planning.forbidden_consecutive, planning.forbidden_parallel):
        if any(len(pair) != 2 or not pair <= subjects for pair in rules):
            raise ValueError(
                "Cada restricción debe contener dos asignaturas distintas y existentes."
            )
    if any(
        type(day) is not int or not 1 <= day <= 6 or type(count) is not int or count < 0
        for day, count in (planning.day_period_counts or {}).items()
    ):
        raise ValueError("Los turnos por día deben ser enteros no negativos de lunes a sábado.")
    if any(
        type(week) is not int or not 1 <= week <= planning.weeks for week in planning.saturday_weeks
    ):
        raise ValueError("Los sábados activos deben pertenecer a una semana del ciclo.")
    build_daily_periods(
        period_count=0,
        duration_minutes=planning.period_duration_minutes,
        transition_minutes=planning.transition_minutes,
        start=planning.class_start,
        break_start=planning.break_start,
        break_end=planning.break_end,
        lunch_start=planning.lunch_start,
        lunch_end=planning.lunch_end,
        lunch_after_period=planning.lunch_after_period,
    )
    keys = set()
    days = defaultdict(list)
    for slot in planning.slots:
        key = (slot.week, slot.day, slot.period)
        if (
            any(type(value) is not int for value in key)
            or not (1 <= slot.week <= planning.weeks and 1 <= slot.day <= 6 and slot.period >= 1)
            or slot.start >= slot.end
            or key in keys
        ):
            raise ValueError("Hay franjas inválidas o duplicadas.")
        keys.add(key)
        days[slot.week, slot.day].append(slot)
    for slots in days.values():
        ordered = sorted(slots, key=lambda slot: slot.period)
        if any(left.end > right.start for left, right in pairwise(ordered)):
            raise ValueError("Las franjas de un día deben estar ordenadas y no solaparse.")
