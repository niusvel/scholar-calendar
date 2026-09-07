import json
from dataclasses import replace

import pytest

from scholar_calendar.config import load_planning, save_planning
from scholar_calendar.project_file import CalendarProject, load_project, save_project
from scholar_calendar.schedule_file import save_schedule
from scholar_calendar.solver import solve


@pytest.fixture(scope="module")
def generated():
    planning = load_planning("examples/cycle.json")
    return planning, solve(planning)


def test_project_roundtrip_without_schedule(tmp_path, generated):
    project = CalendarProject(generated[0])
    path = tmp_path / "centro.json"
    save_project(project, path)
    assert load_project(path) == project


def test_project_preserves_current_edits_and_original_schedule(tmp_path, generated):
    planning, schedule = generated
    edited = replace(planning, course_name="Curso nuevo", forbidden_parallel=frozenset())
    project = CalendarProject(edited, planning, schedule)
    path = tmp_path / "centro.json"
    save_project(project, path)
    assert load_project(path) == project


def test_load_accepts_legacy_configuration_and_schedule(tmp_path, generated):
    planning, schedule = generated
    path = tmp_path / "anterior.json"
    save_planning(planning, path)
    assert load_project(path) == CalendarProject(planning)
    save_schedule(planning, schedule, path)
    assert load_project(path) == CalendarProject(planning, planning, schedule)


@pytest.mark.parametrize(
    "change",
    [
        lambda data: data.update(version=2),
        lambda data: data.update(version=True),
        lambda data: data.update(configuration=[]),
        lambda data: data.pop("generated"),
        lambda data: data["generated"]["lessons"][0].update(subject="Inexistente"),
    ],
)
def test_invalid_project_is_rejected(tmp_path, generated, change):
    planning, schedule = generated
    path = tmp_path / "centro.json"
    save_project(CalendarProject(planning, planning, schedule), path)
    data = json.loads(path.read_text())
    change(data)
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        load_project(path)


def test_schedule_requires_its_configuration_before_writing(tmp_path, generated):
    path = tmp_path / "centro.json"
    path.write_text("contenido anterior")
    with pytest.raises(ValueError, match="configuración del horario"):
        save_project(CalendarProject(generated[0], schedule=generated[1]), path)
    assert path.read_text() == "contenido anterior"


def test_project_preserves_irregular_configuration_slots_without_a_schedule(tmp_path, generated):
    from datetime import time

    planning = generated[0]
    planning = replace(
        planning,
        slots=tuple(
            replace(slot, start=time(7, 45)) if slot.week == 2 and slot.period == 1 else slot
            for slot in planning.slots
        ),
        teacher_unavailable_days=None,
    )
    path = tmp_path / "irregular.json"
    save_project(CalendarProject(planning), path)
    assert load_project(path).planning == planning


@pytest.mark.parametrize(
    "change",
    [
        lambda data: data.update(weeks=0),
        lambda data: data["subjects"].append(data["subjects"][0]),
        lambda data: data.update(subject_unavailable_days={"Asignatura 1": [7]}),
        lambda data: data.update(forbidden_parallel=[["Asignatura 1"]]),
        lambda data: data.update(teacher_subjects={"Profesor inexistente": ["Asignatura 1"]}),
        lambda data: data["slots"][1].update(start="08:30"),
    ],
)
def test_invalid_configuration_is_rejected_before_loading(tmp_path, generated, change):
    path = tmp_path / "invalid.json"
    save_project(CalendarProject(generated[0]), path)
    data = json.loads(path.read_text())
    change(data["configuration"])
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        load_project(path)
