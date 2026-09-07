"""One document for the current configuration and its optional generated schedule."""

import json
from dataclasses import dataclass
from pathlib import Path

from .config import planning_from_dict, planning_to_dict
from .models import PlanningInput
from .schedule_file import FILE_TYPE as SCHEDULE_FILE_TYPE
from .schedule_file import schedule_from_dict, schedule_to_dict, write_json
from .solver import Schedule

FILE_TYPE = "scholar-calendar-project"
FILE_VERSION = 1


@dataclass(frozen=True)
class CalendarProject:
    planning: PlanningInput
    schedule_planning: PlanningInput | None = None
    schedule: Schedule | None = None


def save_project(project: CalendarProject, path: str | Path) -> None:
    generated = None
    if project.schedule is not None:
        if project.schedule_planning is None:
            raise ValueError("Falta la configuración del horario generado.")
        generated = schedule_to_dict(project.schedule_planning, project.schedule)
    write_json(
        {
            "type": FILE_TYPE,
            "version": FILE_VERSION,
            "configuration": planning_to_dict(project.planning),
            "generated": generated,
        },
        path,
    )


def load_project(path: str | Path) -> CalendarProject:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("El archivo no contiene una configuración válida.")
    try:
        if data.get("type") == SCHEDULE_FILE_TYPE:
            planning, schedule = schedule_from_dict(data)
            return CalendarProject(planning, planning, schedule)
        if "type" not in data:
            return CalendarProject(planning_from_dict(data))
        if (
            data.get("type") != FILE_TYPE
            or type(data.get("version")) is not int
            or data["version"] != FILE_VERSION
        ):
            raise ValueError("El formato o la versión del archivo no es compatible.")
        planning = planning_from_dict(data["configuration"])
        if data["generated"] is None:
            return CalendarProject(planning)
        schedule_planning, schedule = schedule_from_dict(data["generated"])
        return CalendarProject(planning, schedule_planning, schedule)
    except (KeyError, TypeError, AttributeError, ValueError) as error:
        raise ValueError(f"No se pudo leer el documento: {error}") from error
