"""Portable, versioned snapshots of a generated schedule and its configuration."""

import json
from dataclasses import asdict, replace
from pathlib import Path

from .config import NULLABLE_FIELDS, planning_from_dict, planning_to_dict, slots_to_dict
from .models import PlanningInput
from .solver import Schedule, ScheduledLesson
from .storage import write_json

FILE_TYPE = "scholar-calendar-schedule"
FILE_VERSION = 1


def _validate(planning: PlanningInput, schedule: Schedule) -> None:
    if not 1 <= planning.weeks <= 52:
        raise ValueError("El número de semanas del horario no es válido.")
    names = []
    for resources in (planning.classrooms, planning.subjects, planning.teachers):
        values = {item.name for item in resources}
        if (
            not values
            or len(values) != len(resources)
            or any(not isinstance(name, str) or not name.strip() for name in values)
        ):
            raise ValueError("El horario contiene recursos vacíos o duplicados.")
        names.append(values)
    rooms, subjects, teachers = names
    slots = {}
    for slot in planning.slots:
        key = (slot.week, slot.day, slot.period)
        if (
            any(type(value) is not int for value in key)
            or not (1 <= slot.week <= planning.weeks and 1 <= slot.day <= 6 and slot.period >= 1)
            or slot.start >= slot.end
            or key in slots
        ):
            raise ValueError("El horario contiene una franja inválida o duplicada.")
        slots[key] = (slot.start.strftime("%H:%M"), slot.end.strftime("%H:%M"))
    occupied_rooms, occupied_teachers = set(), set()
    for lesson in schedule.lessons:
        key = (lesson.week, lesson.day, lesson.period)
        if (
            any(type(value) is not int for value in key)
            or key not in slots
            or (lesson.start, lesson.end) != slots[key]
        ):
            raise ValueError("Una clase no coincide con las franjas del horario.")
        if (
            lesson.classroom not in rooms
            or lesson.subject not in subjects
            or lesson.teacher not in teachers
        ):
            raise ValueError(
                "Una clase hace referencia a un aula, asignatura o profesor desconocido."
            )
        room_key, teacher_key = (*key, lesson.classroom), (*key, lesson.teacher)
        if room_key in occupied_rooms or teacher_key in occupied_teachers:
            raise ValueError("El horario contiene clases duplicadas o solapadas.")
        occupied_rooms.add(room_key)
        occupied_teachers.add(teacher_key)


def schedule_to_dict(planning: PlanningInput, schedule: Schedule) -> dict:
    _validate(planning, schedule)
    data = {
        "type": FILE_TYPE,
        "version": FILE_VERSION,
        "planning": planning_to_dict(planning),
        # Preserve exact slots, including cycles whose weeks have different days.
        "slots": slots_to_dict(planning.slots),
        "lessons": [asdict(lesson) for lesson in schedule.lessons],
    }
    for field in NULLABLE_FIELDS:
        if getattr(planning, field) is None:
            data["planning"][field] = None
    return data


def save_schedule(planning: PlanningInput, schedule: Schedule, path: str | Path) -> None:
    write_json(schedule_to_dict(planning, schedule), path)


def load_schedule(path: str | Path) -> tuple[PlanningInput, Schedule]:
    return schedule_from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def schedule_from_dict(data: dict) -> tuple[PlanningInput, Schedule]:
    if not isinstance(data, dict) or data.get("type") != FILE_TYPE:
        raise ValueError(
            "Este archivo no es un horario guardado. Para cargar una configuración, usa Archivo → Cargar."
        )
    if type(data.get("version")) is not int or data["version"] != FILE_VERSION:
        raise ValueError("La versión de este archivo de horario no es compatible.")
    try:
        planning_data = dict(data["planning"])
        unset_fields = {
            field: None
            for field in NULLABLE_FIELDS
            if field in planning_data and planning_data[field] is None
        }
        planning_data.update({field: {} for field in unset_fields})
        planning_data["slots"] = data["slots"]
        planning = replace(planning_from_dict(planning_data), **unset_fields)
        schedule = Schedule(tuple(ScheduledLesson(**item) for item in data["lessons"]))
        _validate(planning, schedule)
    except (KeyError, TypeError, AttributeError, ValueError) as error:
        raise ValueError(f"El archivo de horario no es válido: {error}") from error
    return planning, schedule
