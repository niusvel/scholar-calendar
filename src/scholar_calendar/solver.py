from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from itertools import pairwise

from ortools.sat.python import cp_model

from .models import PlanningInput
from .validation import validate_planning


class ScheduleError(ValueError):
    """Raised when the requested rules cannot produce a schedule."""


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


def solve(planning: PlanningInput) -> Schedule:
    """Respect mandatory rules and minimize violations of the scheduling preferences."""
    validate_planning(planning)
    model = cp_model.CpModel()
    penalties = []
    subjects = {subject.name: subject for subject in planning.subjects}
    teachers = {teacher.name for teacher in planning.teachers}
    classrooms = {classroom.name for classroom in planning.classrooms}
    slots = planning.slots

    candidates: dict[tuple[str, str, str, int], cp_model.IntVar] = {}
    for classroom in classrooms:
        for subject in subjects.values():
            eligible = {
                teacher
                for teacher in teachers
                if subject.name in planning.teacher_subjects.get(teacher, frozenset())
                and (
                    not planning.teacher_classrooms.get(teacher)
                    or classroom in planning.teacher_classrooms[teacher]
                )
            }
            if not eligible and subject.lessons_per_cycle:
                raise ScheduleError(f"No hay profesor elegible para {subject.name} en {classroom}.")
            for teacher in eligible:
                for slot_index in range(len(slots)):
                    slot = slots[slot_index]
                    if slot.day in (planning.teacher_unavailable_days or {}).get(
                        teacher, frozenset()
                    ):
                        continue
                    if slot.day in (planning.subject_unavailable_days or {}).get(
                        subject.name, frozenset()
                    ):
                        continue
                    candidates[(classroom, subject.name, teacher, slot_index)] = model.NewBoolVar(
                        f"lesson_{classroom}_{subject.name}_{teacher}_{slot_index}"
                    )

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
                model.Add(sum(weekly_variables) == subject.lessons_per_cycle)
                if subject.lessons_per_cycle > 0:
                    outside_late_periods = [
                        presence[classroom, subject.name, index]
                        for index, slot in enumerate(slots)
                        if slot.week == week and slot.period not in (5, 6)
                    ]
                    always_late = model.NewBoolVar(f"always_late_{classroom}_{subject.name}_{week}")
                    model.Add(sum(outside_late_periods) == 0).OnlyEnforceIf(always_late)
                    model.Add(sum(outside_late_periods) >= 1).OnlyEnforceIf(always_late.Not())
                    penalties.append(always_late)

    for slot_index in range(len(slots)):
        for classroom in classrooms:
            model.Add(sum(by_room_slot[classroom, slot_index]) <= 1)
        for teacher in teachers:
            model.Add(sum(by_teacher_slot[teacher, slot_index]) <= 1)

    # A subject may appear once per day, except for an explicitly double subject.
    for classroom in classrooms:
        for subject in subjects.values():
            for week in range(1, planning.weeks + 1):
                weekly_singletons = []
                for day in range(1, 7):
                    day_indexes = day_slots[week, day]
                    day_presence = [
                        presence[(classroom, subject.name, index)] for index in day_indexes
                    ]
                    if not subject.double_period:
                        model.Add(sum(day_presence) <= 1)
                        continue
                    model.Add(sum(day_presence) <= 2)

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
                        model.Add(
                            presence[(classroom, subject.name, index)]
                            == sum(pairs_by_slot[index]) + singleton
                        )
                        singleton_variables.append(singleton)
                    weekly_singletons.extend(singleton_variables)
                if subject.double_period:
                    model.Add(sum(weekly_singletons) <= 1)
    for pair in planning.forbidden_parallel:
        first, second = tuple(pair)
        for slot_index in range(len(slots)):
            first_vars = by_subject_slot[first, slot_index]
            second_vars = by_subject_slot[second, slot_index]
            first_present = model.NewBoolVar(f"parallel_{first}_{second}_{slot_index}")
            model.Add(sum(first_vars) == 0).OnlyEnforceIf(first_present.Not())
            model.Add(sum(second_vars) == 0).OnlyEnforceIf(first_present)

    for classroom in classrooms:
        for pair in planning.forbidden_consecutive:
            first_subject, second_subject = tuple(pair)
            for left_subject, right_subject in (
                (first_subject, second_subject),
                (second_subject, first_subject),
            ):
                for left_index, right_index in consecutive_slots:
                    left_vars = by_room_subject_slot[classroom, left_subject, left_index]
                    right_vars = by_room_subject_slot[classroom, right_subject, right_index]
                    model.Add(sum(left_vars) + sum(right_vars) <= 1)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10
    solver.parameters.num_search_workers = 8
    model.Minimize(sum(penalties))
    status = solver.Solve(model)
    if status == cp_model.UNKNOWN:
        raise ScheduleError(
            "Se agotó el tiempo de búsqueda sin encontrar un horario. "
            "Prueba de nuevo o simplifica la configuración; no se ha demostrado que sea imposible."
        )
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise ScheduleError("No existe una planificación que cumpla todas las reglas.")

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
