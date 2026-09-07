from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from itertools import pairwise

from ortools.sat.python import cp_model

from .models import PlanningInput


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
    model = cp_model.CpModel()
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
    consecutive_slots = [
        (left, right)
        for indexes in day_slots.values()
        for left in indexes
        for right in indexes
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

                    pair_by_left_index: dict[int, cp_model.IntVar] = {}
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
                        pair_by_left_index[left_index] = pair

                    singleton_variables = []
                    for index in day_indexes:
                        singleton = model.NewBoolVar(
                            f"double_single_{classroom}_{subject.name}_{index}"
                        )
                        adjacent_pairs = []
                        if index in pair_by_left_index:
                            adjacent_pairs.append(pair_by_left_index[index])
                        if index - 1 in pair_by_left_index:
                            adjacent_pairs.append(pair_by_left_index[index - 1])
                        model.Add(
                            presence[(classroom, subject.name, index)]
                            == sum(adjacent_pairs) + singleton
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
            model.Add(sum(first_vars) + sum(second_vars) <= 1)

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

    double_pairs = []
    for classroom in classrooms:
        for subject in subjects.values():
            if not subject.double_period:
                continue
            for left_index, right_index in consecutive_slots:
                pair = model.NewBoolVar(f"double_{classroom}_{subject.name}_{left_index}")
                model.Add(pair <= presence[classroom, subject.name, left_index])
                model.Add(pair <= presence[classroom, subject.name, right_index])
                double_pairs.append(pair)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10
    solver.parameters.num_search_workers = 8
    if double_pairs:
        model.Maximize(sum(double_pairs))
    status = solver.Solve(model)
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
