from datetime import time

from scholar_calendar.models import Classroom, PlanningInput, Subject, Teacher, build_slots
from scholar_calendar.solver import solve


def test_solver_respects_parallel_conflict_and_assigns_every_lesson():
    subjects = (Subject("Matemáticas", 2), Subject("Lengua", 2))
    teachers = (Teacher("Ana"), Teacher("Luis"))
    classrooms = (Classroom("Aula 1"), Classroom("Aula 2"))
    slots = build_slots(
        weeks=1,
        days=2,
        daily_periods=(
            (time(8, 0), time(9, 0)),
            (time(9, 0), time(10, 0)),
            (time(10, 30), time(11, 30)),
            (time(11, 30), time(12, 30)),
            (time(14, 0), time(15, 0)),
            (time(15, 0), time(16, 0)),
            (time(16, 0), time(17, 0)),
            (time(17, 0), time(18, 0)),
        ),
    )
    rooms = frozenset({"Aula 1", "Aula 2"})
    planning = PlanningInput(
        weeks=1,
        subjects=subjects,
        teachers=teachers,
        classrooms=classrooms,
        slots=slots,
        teacher_subjects={"Ana": frozenset({"Matemáticas"}), "Luis": frozenset({"Lengua"})},
        teacher_classrooms={"Ana": rooms, "Luis": rooms},
        forbidden_parallel=frozenset({frozenset(("Matemáticas", "Lengua"))}),
    )

    schedule = solve(planning)

    assert len(schedule.lessons) == 8
    assert (
        len(
            {
                (lesson.classroom, lesson.week, lesson.day, lesson.period)
                for lesson in schedule.lessons
            }
        )
        == 8
    )
    assert (
        len(
            {
                (lesson.teacher, lesson.week, lesson.day, lesson.period)
                for lesson in schedule.lessons
            }
        )
        == 8
    )
    for slot in {(lesson.week, lesson.day, lesson.period) for lesson in schedule.lessons}:
        subjects_in_slot = {
            lesson.subject
            for lesson in schedule.lessons
            if (lesson.week, lesson.day, lesson.period) == slot
        }
        assert not {"Matemáticas", "Lengua"}.issubset(subjects_in_slot)


def test_consecutive_conflict_applies_in_both_directions():
    subjects = (Subject("A", 1), Subject("B", 1))
    teacher = Teacher("Profesor")
    classroom = Classroom("Aula")
    planning = PlanningInput(
        weeks=1,
        subjects=subjects,
        teachers=(teacher,),
        classrooms=(classroom,),
        slots=build_slots(
            weeks=1,
            days=3,
            daily_periods=(
                (time(8, 0), time(9, 0)),
                (time(9, 0), time(10, 0)),
                (time(10, 30), time(11, 30)),
            ),
        ),
        teacher_subjects={"Profesor": frozenset({"A", "B"})},
        teacher_classrooms={"Profesor": frozenset({"Aula"})},
        forbidden_consecutive=frozenset({frozenset(("A", "B"))}),
    )

    schedule = solve(planning)

    assert [lesson.subject for lesson in schedule.lessons] in (["A", "B"], ["B", "A"])
    assert schedule.lessons[0].period != schedule.lessons[1].period


def test_double_subject_prefers_consecutive_periods_and_respects_unavailable_days():
    subject = Subject("Laboratorio", 2, double_period=True)
    teacher = Teacher("Profesor")
    classroom = Classroom("Aula")
    planning = PlanningInput(
        weeks=1,
        subjects=(subject,),
        teachers=(teacher,),
        classrooms=(classroom,),
        slots=build_slots(
            weeks=1,
            days=2,
            daily_periods=(
                (time(8, 0), time(9, 0)),
                (time(9, 0), time(10, 0)),
            ),
        ),
        teacher_subjects={"Profesor": frozenset({"Laboratorio"})},
        teacher_classrooms={"Profesor": frozenset({"Aula"})},
        teacher_unavailable_days={"Profesor": frozenset({2})},
    )

    schedule = solve(planning)

    assert [(lesson.day, lesson.period) for lesson in schedule.lessons] == [(1, 1), (1, 2)]


def test_regular_subject_is_not_repeated_on_the_same_day():
    planning = PlanningInput(
        weeks=1,
        subjects=(Subject("Historia", 2),),
        teachers=(Teacher("Profesor"),),
        classrooms=(Classroom("Aula"),),
        slots=build_slots(
            weeks=1,
            days=2,
            daily_periods=((time(8, 0), time(9, 0)), (time(9, 0), time(10, 0))),
        ),
        teacher_subjects={"Profesor": frozenset({"Historia"})},
        teacher_classrooms={"Profesor": frozenset({"Aula"})},
    )

    schedule = solve(planning)

    assert {lesson.day for lesson in schedule.lessons} == {1, 2}


def test_double_subject_with_odd_frequency_has_one_single_period():
    planning = PlanningInput(
        weeks=1,
        subjects=(Subject("Matemática", 5, double_period=True),),
        teachers=(Teacher("Profesor"),),
        classrooms=(Classroom("Aula"),),
        slots=build_slots(
            weeks=1,
            days=3,
            daily_periods=tuple((time(hour, 0), time(hour + 1, 0)) for hour in range(8, 15)),
        ),
        teacher_subjects={"Profesor": frozenset({"Matemática"})},
        teacher_classrooms={"Profesor": frozenset({"Aula"})},
    )

    schedule = solve(planning)
    by_day = {}
    for lesson in schedule.lessons:
        by_day.setdefault(lesson.day, []).append(lesson.period)

    assert sum(len(periods) for periods in by_day.values()) == 5
    assert sorted(len(periods) for periods in by_day.values()) == [1, 2, 2]
    assert all(max(periods) - min(periods) == 1 for periods in by_day.values() if len(periods) == 2)


def test_weekly_frequency_is_met_in_every_week_and_classroom():
    from collections import Counter

    planning = PlanningInput(
        weeks=3,
        subjects=(Subject("Historia", 2),),
        teachers=(Teacher("Profesor"),),
        classrooms=(Classroom("A"), Classroom("B")),
        slots=build_slots(weeks=3, days=5, daily_periods=((time(8), time(9)), (time(9), time(10)))),
        teacher_subjects={"Profesor": frozenset({"Historia"})},
        teacher_classrooms={},
    )
    schedule = solve(planning)
    counts = Counter((lesson.week, lesson.classroom) for lesson in schedule.lessons)
    assert counts == {(week, room): 2 for week in range(1, 4) for room in ("A", "B")}


def test_a_week_without_capacity_cannot_borrow_sessions_from_another_week():
    import pytest

    from scholar_calendar.solver import ScheduleError

    planning = PlanningInput(
        weeks=2,
        subjects=(Subject("Historia", 1),),
        teachers=(Teacher("Profesor"),),
        classrooms=(Classroom("A"),),
        # Two sessions fit across the cycle, but week 2 has no slots at all.
        slots=build_slots(weeks=1, days=2, daily_periods=((time(8), time(9)),)),
        teacher_subjects={"Profesor": frozenset({"Historia"})},
        teacher_classrooms={},
    )
    with pytest.raises(ScheduleError):
        solve(planning)


def test_parallel_rule_allows_same_subject_in_different_rooms():
    from collections import defaultdict

    planning = PlanningInput(
        weeks=1,
        subjects=(Subject("A", 1), Subject("B", 1)),
        teachers=(Teacher("Ana"), Teacher("Luis")),
        classrooms=(Classroom("1"), Classroom("2")),
        slots=build_slots(weeks=1, days=1, daily_periods=((time(8), time(9)), (time(9), time(10)))),
        teacher_subjects={"Ana": frozenset({"A", "B"}), "Luis": frozenset({"A", "B"})},
        teacher_classrooms={},
        forbidden_parallel=frozenset({frozenset({"A", "B"})}),
    )
    schedule = solve(planning)
    by_period = defaultdict(list)
    for lesson in schedule.lessons:
        by_period[lesson.period].append(lesson)
    assert len(schedule.lessons) == 4
    assert all(
        len(lessons) == 2 and len({item.subject for item in lessons}) == 1
        for lessons in by_period.values()
    )


def test_double_periods_accept_slots_stored_out_of_order():
    slots = build_slots(weeks=1, days=2, daily_periods=((time(8), time(9)), (time(9), time(10))))
    planning = PlanningInput(
        weeks=1,
        subjects=(Subject("A", 4, double_period=True),),
        teachers=(Teacher("Ana"),),
        classrooms=(Classroom("1"),),
        slots=tuple(reversed(slots)),
        teacher_subjects={"Ana": frozenset({"A"})},
        teacher_classrooms={},
    )
    assert len(solve(planning).lessons) == 4


def test_timeout_is_not_reported_as_proven_infeasibility():
    from unittest.mock import patch

    import pytest
    from ortools.sat.python import cp_model

    from scholar_calendar.config import load_planning
    from scholar_calendar.solver import ScheduleError

    with (
        patch.object(cp_model.CpSolver, "Solve", return_value=cp_model.UNKNOWN),
        pytest.raises(ScheduleError, match="no se ha demostrado"),
    ):
        solve(load_planning("examples/cycle.json"))
