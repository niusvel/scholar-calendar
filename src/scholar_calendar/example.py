from datetime import time

from .models import Classroom, PlanningInput, Subject, Teacher, build_slots
from .solver import solve


def main() -> None:
    subjects = tuple(Subject(f"Asignatura {index}", 1) for index in range(1, 11))
    teachers = tuple(Teacher(f"Profesor {index}") for index in range(1, 8))
    classrooms = tuple(Classroom(f"Aula {index}") for index in range(1, 5))
    slots = build_slots(
        weeks=2,
        days=5,
        daily_periods=(
            (time(8, 0), time(9, 0)),
            (time(9, 0), time(10, 0)),
            (time(10, 30), time(11, 30)),
            (time(11, 30), time(12, 30)),
            (time(14, 0), time(15, 0)),
            (time(15, 0), time(16, 0)),
        ),
    )
    subject_names = frozenset(subject.name for subject in subjects)
    classroom_names = frozenset(classroom.name for classroom in classrooms)
    planning = PlanningInput(
        weeks=2,
        subjects=subjects,
        teachers=teachers,
        classrooms=classrooms,
        slots=slots,
        teacher_subjects={teacher.name: subject_names for teacher in teachers},
        teacher_classrooms={teacher.name: classroom_names for teacher in teachers},
        forbidden_consecutive=frozenset({frozenset(("Asignatura 1", "Asignatura 2"))}),
        forbidden_parallel=frozenset({frozenset(("Asignatura 3", "Asignatura 4"))}),
    )

    schedule = solve(planning)
    for lesson in schedule.lessons:
        print(
            f"Semana {lesson.week}, día {lesson.day}, {lesson.start}-{lesson.end} | "
            f"{lesson.classroom}: {lesson.subject} ({lesson.teacher})"
        )


if __name__ == "__main__":
    main()
