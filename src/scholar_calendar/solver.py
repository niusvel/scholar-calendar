from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from itertools import pairwise

from ortools.sat.python import cp_model

from .availability import all_blocks, availability_index, block_key, block_time, is_blocked
from .generation_diagnostics import ConfigurationConflict, DiagnosticRules
from .models import PlanningInput
from .validation import validate_planning


class ScheduleError(ValueError):
    """Generation failure, optionally with proven configuration conflicts."""

    def __init__(self, message: str, conflicts: tuple[ConfigurationConflict, ...] = ()) -> None:
        self.summary = message
        self.conflicts = conflicts
        details = "\n\n".join(
            f"{item.title}\n{item.detail}\nRevisar: {item.section}." for item in conflicts
        )
        super().__init__(message + ("\n\n" + details if details else ""))


@dataclass(frozen=True)
class ScheduledLesson:
    week: int
    day: int
    period: int
    classroom: str
    subject: str
    teacher: str
    start: str
    end: str


@dataclass(frozen=True)
class Schedule:
    lessons: tuple[ScheduledLesson, ...]


def _build_model(planning: PlanningInput, *, diagnostic: bool = False):
    model = cp_model.CpModel()
    rules = DiagnosticRules(model, diagnostic)
    penalties = []
    subjects = {subject.name: subject for subject in planning.subjects}
    teachers = sorted(teacher.name for teacher in planning.teachers)
    classrooms = sorted(classroom.name for classroom in planning.classrooms)
    slots = planning.slots
    unavailable = availability_index(planning)

    candidates: dict[tuple[str, str, str, int], cp_model.IntVar] = {}
    for classroom in classrooms:
        for subject in subjects.values():
            eligible = [
                teacher
                for teacher in teachers
                if planning.teacher_can_teach(teacher, subject.name, classroom)
            ]
            for teacher in eligible:
                for slot_index in range(len(slots)):
                    slot = slots[slot_index]
                    if not diagnostic and is_blocked(
                        unavailable, teacher, subject.name, slot.day, slot.period, classroom
                    ):
                        continue
                    candidates[(classroom, subject.name, teacher, slot_index)] = model.NewBoolVar(
                        f"lesson_{classroom}_{subject.name}_{teacher}_{slot_index}"
                    )

    if diagnostic:
        for block in sorted(all_blocks(planning), key=block_key):
            target = " · ".join(value for value in (block.teacher, block.subject) if value)
            scope = "" if block.classroom is not None else " · todas las aulas"
            literal = rules.literal(
                ("availability", block),
                f"Disponibilidad: {target}",
                f"No disponible: {block_time(block)}{scope}. Se repite cada semana.",
                "Profesores → Disponibilidad" if block.teacher else "Asignaturas → Disponibilidad",
            )
            for (room, subject, teacher, index), variable in candidates.items():
                slot = slots[index]
                if (
                    block.teacher in (None, teacher)
                    and block.subject in (None, subject)
                    and block.classroom in (None, room)
                    and block.day == slot.day
                    and block.period in (None, slot.period)
                ):
                    model.Add(variable == 0).OnlyEnforceIf(literal)

    # Index candidates once instead of scanning every assignment for each rule.
    by_room_subject_slot = defaultdict(list)
    by_room_subject_week = defaultdict(list)
    by_room_slot = defaultdict(list)
    by_teacher_slot = defaultdict(list)
    by_subject_slot = defaultdict(list)
    for (room, subject, teacher, index), variable in candidates.items():
        by_room_subject_slot[room, subject, index].append(variable)
        by_room_subject_week[room, subject, slots[index].week].append(variable)
        by_room_slot[room, index].append(variable)
        by_teacher_slot[teacher, index].append(variable)
        by_subject_slot[subject, index].append(variable)

    day_slots = defaultdict(list)
    for index, slot in enumerate(slots):
        day_slots[slot.week, slot.day].append(index)
    for indexes in day_slots.values():
        indexes.sort(key=lambda index: slots[index].period)
    consecutive_slots = [
        (left, right)
        for indexes in day_slots.values()
        for left, right in pairwise(indexes)
        if slots[right].period == slots[left].period + 1
    ]
    presence: dict[tuple[str, str, int], cp_model.IntVar] = {}
    for classroom in classrooms:
        for subject in subjects.values():
            for slot_index in range(len(slots)):
                lesson_presence = model.NewBoolVar(
                    f"presence_{classroom}_{subject.name}_{slot_index}"
                )
                lesson_variables = by_room_subject_slot[classroom, subject.name, slot_index]
                model.Add(lesson_presence == sum(lesson_variables))
                presence[(classroom, subject.name, slot_index)] = lesson_presence

    for classroom in classrooms:
        for subject in subjects.values():
            for week in range(1, planning.weeks + 1):
                weekly_variables = by_room_subject_week[classroom, subject.name, week]
                week_slots = [slot for slot in slots if slot.week == week]
                eligible_names = ", ".join(
                    teacher
                    for teacher in teachers
                    if planning.teacher_can_teach(teacher, subject.name, classroom)
                )
                rules.enforce(
                    model.Add(sum(weekly_variables) == subject.lessons_per_cycle),
                    ("frequency", classroom, subject.name, week),
                    f"{subject.name} · {classroom} · semana {week}",
                    f"Sesiones exigidas: {subject.lessons_per_cycle}. Turnos de la semana: {len(week_slots)}; días con clase: {len({slot.day for slot in week_slots})} (antes de aplicar bloqueos). Profesores habilitados en esta aula: {eligible_names}.",
                    "Asignaturas → Frecuencia; Profesores → Asignaturas y aulas / Aulas generales",
                )
                if not diagnostic and subject.lessons_per_cycle > 0:
                    outside_late_periods = [
                        presence[classroom, subject.name, index]
                        for index, slot in enumerate(slots)
                        if slot.week == week and slot.period not in (5, 6)
                    ]
                    always_late = model.NewBoolVar(f"always_late_{classroom}_{subject.name}_{week}")
                    model.Add(sum(outside_late_periods) == 0).OnlyEnforceIf(always_late)
                    model.Add(sum(outside_late_periods) >= 1).OnlyEnforceIf(always_late.Not())
                    penalties.append(always_late)

    counts = "; ".join(
        f"semana {week}: {sum(slot.week == week for slot in slots)}"
        for week in range(1, planning.weeks + 1)
    )
    for slot_index in range(len(slots)):
        for classroom in classrooms:
            rules.enforce(
                model.Add(sum(by_room_slot[classroom, slot_index]) <= 1),
                ("room_capacity", classroom),
                f"Capacidad del aula {classroom}",
                f"Solo cabe una clase por turno. Turnos por semana según la jornada: {counts}.",
                "Jornada → Días y turnos; Asignaturas → Frecuencia",
            )
        for teacher in teachers:
            rules.enforce(
                model.Add(sum(by_teacher_slot[teacher, slot_index]) <= 1),
                ("teacher_capacity", teacher),
                f"Profesor compartido: {teacher}",
                "No puede impartir dos clases a la vez, aunque sean asignaturas o aulas distintas.",
                "Profesores → Asignaturas y aulas / Disponibilidad; Jornada → Días y turnos",
            )

    # A subject may appear once per day, except for an explicitly double subject.
    for classroom in classrooms:
        for subject in subjects.values():
            daily_rule = (
                ("daily_distribution", classroom, subject.name),
                f"Distribución de {subject.name} en {classroom}",
                (
                    "Modo doble: máximo dos sesiones al día, consecutivas, y como máximo una sesión suelta por semana."
                    if subject.is_double_in(classroom)
                    else "Modo sencillo: como máximo una sesión por día."
                ),
                "Asignaturas → Frecuencia / Dobles por aula; Jornada → Días y turnos",
            )
            for week in range(1, planning.weeks + 1):
                weekly_singletons = []
                for day in range(1, 7):
                    day_indexes = day_slots[week, day]
                    day_presence = [
                        presence[(classroom, subject.name, index)] for index in day_indexes
                    ]
                    if not subject.is_double_in(classroom):
                        rules.enforce(model.Add(sum(day_presence) <= 1), *daily_rule)
                        continue
                    rules.enforce(model.Add(sum(day_presence) <= 2), *daily_rule)

                    pairs_by_slot = defaultdict(list)
                    for left_index, right_index in pairwise(day_indexes):
                        left_slot = slots[left_index]
                        right_slot = slots[right_index]
                        if (
                            right_slot.week != left_slot.week
                            or right_slot.day != left_slot.day
                            or right_slot.period != left_slot.period + 1
                        ):
                            continue
                        pair = model.NewBoolVar(
                            f"double_pair_{classroom}_{subject.name}_{left_index}"
                        )
                        left_presence = presence[(classroom, subject.name, left_index)]
                        right_presence = presence[(classroom, subject.name, right_index)]
                        model.Add(pair <= left_presence)
                        model.Add(pair <= right_presence)
                        model.Add(pair >= left_presence + right_presence - 1)
                        pairs_by_slot[left_index].append(pair)
                        pairs_by_slot[right_index].append(pair)
                        if (
                            planning.break_start is not None
                            and planning.break_end is not None
                            and left_slot.end
                            <= planning.break_start
                            < planning.break_end
                            <= right_slot.start
                        ):
                            penalties.append(pair)

                    singleton_variables = []
                    for index in day_indexes:
                        singleton = model.NewBoolVar(
                            f"double_single_{classroom}_{subject.name}_{index}"
                        )
                        rules.enforce(
                            model.Add(
                                presence[(classroom, subject.name, index)]
                                == sum(pairs_by_slot[index]) + singleton
                            ),
                            *daily_rule,
                        )
                        singleton_variables.append(singleton)
                    weekly_singletons.extend(singleton_variables)
                if subject.is_double_in(classroom):
                    rules.enforce(model.Add(sum(weekly_singletons) <= 1), *daily_rule)
    for pair in sorted(planning.forbidden_parallel, key=lambda pair: sorted(pair)):
        first, second = sorted(pair)
        for slot_index in range(len(slots)):
            first_vars = by_subject_slot[first, slot_index]
            second_vars = by_subject_slot[second, slot_index]
            first_present = model.NewBoolVar(f"parallel_{first}_{second}_{slot_index}")
            for variables, literal in (
                (first_vars, first_present.Not()),
                (second_vars, first_present),
            ):
                constraint = model.Add(sum(variables) == 0)
                constraint.OnlyEnforceIf(literal)
                rules.enforce(
                    constraint,
                    ("parallel", first, second),
                    f"No simultáneas: {first} y {second}",
                    "No pueden coincidir en el mismo turno, ni siquiera en aulas distintas.",
                    "Asignaturas → Incompatibilidades",
                )

    for classroom in classrooms:
        for pair in sorted(planning.forbidden_consecutive, key=lambda pair: sorted(pair)):
            first_subject, second_subject = sorted(pair)
            for left_subject, right_subject in (
                (first_subject, second_subject),
                (second_subject, first_subject),
            ):
                for left_index, right_index in consecutive_slots:
                    left_vars = by_room_subject_slot[classroom, left_subject, left_index]
                    right_vars = by_room_subject_slot[classroom, right_subject, right_index]
                    rules.enforce(
                        model.Add(sum(left_vars) + sum(right_vars) <= 1),
                        ("consecutive", classroom, first_subject, second_subject),
                        f"No consecutivas: {first_subject} y {second_subject} · {classroom}",
                        "No pueden ocupar turnos consecutivos del mismo día en esta aula.",
                        "Asignaturas → Incompatibilidades",
                    )

    if not diagnostic:
        model.Minimize(sum(penalties))
    return model, candidates, rules


def solve(planning: PlanningInput) -> Schedule:
    """Respect mandatory rules, minimize preferences, and explain proven failures."""
    validate_planning(planning)
    missing = []
    for room in planning.classrooms:
        for subject in planning.subjects:
            if subject.lessons_per_cycle and not any(
                planning.teacher_can_teach(teacher.name, subject.name, room.name)
                for teacher in planning.teachers
            ):
                associated = [
                    teacher.name
                    for teacher in planning.teachers
                    if subject.name in planning.teacher_subjects.get(teacher.name, ())
                ]
                detail = (
                    f"Los profesores asociados ({', '.join(associated)}) no tienen permitida esta aula. Revisa sus aulas generales y las de esta asignatura."
                    if associated
                    else "Ningún profesor está asociado a esta asignatura. Crea o asocia un profesor que pueda impartirla en esta aula."
                )
                missing.append(
                    ConfigurationConflict(
                        f"No hay profesor elegible para {subject.name} en {room.name}.",
                        detail,
                        "Profesores → Asignaturas y aulas / Aulas generales",
                    )
                )
    if missing:
        raise ScheduleError("Faltan profesores habilitados para estas clases.", tuple(missing))
    model, candidates, _ = _build_model(planning)
    slots = planning.slots
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10
    solver.parameters.num_search_workers = 8
    status = solver.Solve(model)
    if status == cp_model.UNKNOWN:
        raise ScheduleError(
            "Se agotó el tiempo de búsqueda sin encontrar un horario. "
            "Prueba de nuevo o simplifica la configuración; no se ha demostrado que sea imposible."
        )
    if status == cp_model.INFEASIBLE:
        _, _, rules = _build_model(planning, diagnostic=True)
        conflicts = rules.explain()
        message = (
            "Estas condiciones de la configuración no se pueden cumplir a la vez. "
            "Revisa al menos una de ellas y vuelve a generar. Puede haber otros conflictos."
            if conflicts
            else "Se ha demostrado que el horario es imposible, pero no se ha podido aislar "
            "el conflicto dentro del tiempo de diagnóstico. Revisa las frecuencias, la jornada, "
            "las asociaciones, la disponibilidad y las incompatibilidades."
        )
        raise ScheduleError(message, conflicts)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise ScheduleError(
            "El motor no pudo procesar el modelo de planificación. "
            "No se ha demostrado que la configuración sea imposible."
        )

    lessons = []
    for (classroom, subject, teacher, slot_index), variable in candidates.items():
        if solver.Value(variable):
            slot = slots[slot_index]
            lessons.append(
                ScheduledLesson(
                    week=slot.week,
                    day=slot.day,
                    period=slot.period,
                    classroom=classroom,
                    subject=subject,
                    teacher=teacher,
                    start=slot.start.strftime("%H:%M"),
                    end=slot.end.strftime("%H:%M"),
                )
            )
    return Schedule(
        tuple(
            sorted(
                lessons,
                key=lambda lesson: (lesson.week, lesson.day, lesson.period, lesson.classroom),
            )
        )
    )
