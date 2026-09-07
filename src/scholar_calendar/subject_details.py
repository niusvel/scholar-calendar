"""Restrictions relevant to a subject in a generated schedule."""

from .models import PlanningInput
from .solver import Schedule
from .timeline import DAY_NAMES


def subject_restrictions(
    planning: PlanningInput, schedule: Schedule, subject_name: str
) -> tuple[str, ...]:
    subject = next((item for item in planning.subjects if item.name == subject_name), None)
    if subject is None:
        return ()

    frequency = subject.lessons_per_cycle
    sessions = "sesión semanal" if frequency == 1 else "sesiones semanales"
    lines = [f"Por aula: {frequency} {sessions}."]
    if subject.double_period:
        lines.append(
            "Turnos dobles: parejas consecutivas, máximo dos turnos al día y una sesión suelta por semana."
        )
    else:
        lines.append("Máximo una sesión al día en cada aula.")

    days = (planning.subject_unavailable_days or {}).get(subject_name, frozenset())
    if days:
        lines.append("Asignatura no disponible: " + _day_names(days) + ".")
    for rules, label in (
        (planning.forbidden_consecutive, "No consecutiva en un aula con"),
        (planning.forbidden_parallel, "No simultánea entre aulas con"),
    ):
        others = sorted(
            {
                name
                for pair in rules
                if subject_name in pair
                for name in pair
                if name != subject_name
            }
        )
        if others:
            lines.append(f"{label}: {', '.join(others)}.")

    assigned = {lesson.teacher for lesson in schedule.lessons if lesson.subject == subject_name}
    eligible = {
        teacher.name
        for teacher in planning.teachers
        if subject_name in planning.teacher_subjects.get(teacher.name, frozenset())
    }
    for teacher in sorted(assigned | eligible):
        restrictions = []
        days = (planning.teacher_unavailable_days or {}).get(teacher, frozenset())
        if days:
            restrictions.append("no disponible " + _day_names(days))
        rooms = planning.teacher_classrooms.get(teacher, frozenset())
        if rooms:
            restrictions.append("solo puede impartir en " + ", ".join(sorted(rooms)))
        if restrictions:
            role = (
                "en este horario" if teacher in assigned else "habilitado, sin clases en este ciclo"
            )
            lines.append(f"{teacher} ({role}): {'; '.join(restrictions)}.")
    return tuple(lines)


def _day_names(days: frozenset[int]) -> str:
    return ", ".join(DAY_NAMES[day] for day in sorted(days))
