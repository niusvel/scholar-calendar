import json
from dataclasses import replace
from datetime import time
from unittest.mock import patch

import pytest

from scholar_calendar.config import load_planning, save_planning
from scholar_calendar.schedule_file import load_schedule, save_schedule
from scholar_calendar.solver import solve


@pytest.fixture(scope="module")
def generated():
    planning = load_planning("examples/cycle.json")
    return planning, solve(planning)


def test_saved_schedule_keeps_exact_assignments_and_configuration(tmp_path, generated):
    planning, schedule = generated
    path = tmp_path / "septiembre.horario.json"
    save_schedule(planning, schedule, path)
    with patch("scholar_calendar.solver.solve", side_effect=AssertionError("Must not regenerate")):
        restored, recovered = load_schedule(path)
    assert restored == planning
    assert recovered == schedule


def test_archive_preserves_exact_slots_even_when_weeks_have_different_times(tmp_path, generated):
    planning, schedule = generated
    slots = tuple(
        replace(slot, start=time(7, 45)) if slot.week == 2 and slot.period == 1 else slot
        for slot in planning.slots
    )
    lessons = tuple(
        replace(lesson, start="07:45") if lesson.week == 2 and lesson.period == 1 else lesson
        for lesson in schedule.lessons
    )
    planning, schedule = replace(planning, slots=slots), replace(schedule, lessons=lessons)
    path = tmp_path / "exact.horario.json"
    save_schedule(planning, schedule, path)
    restored, recovered = load_schedule(path)
    assert restored.slots == planning.slots
    assert recovered == schedule


@pytest.mark.parametrize(
    "change",
    [
        lambda data: data.update(version=99),
        lambda data: data["lessons"][0].update(subject="No existe"),
        lambda data: data["lessons"][0].update(week=99),
        lambda data: data["lessons"][0].update(start="23:59"),
        lambda data: data["lessons"].append(data["lessons"][0]),
        lambda data: data.update(planning=[]),
        lambda data: data.pop("slots"),
    ],
)
def test_invalid_archives_are_rejected(tmp_path, generated, change):
    path = tmp_path / "invalid.horario.json"
    save_schedule(*generated, path)
    data = json.loads(path.read_text())
    change(data)
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        load_schedule(path)


def test_configuration_file_is_not_mistaken_for_a_saved_schedule(tmp_path, generated):
    path = tmp_path / "config.json"
    save_planning(generated[0], path)
    with pytest.raises(ValueError, match="Abrir configuración"):
        load_schedule(path)


def test_failed_save_keeps_the_previous_file(tmp_path, generated):
    path = tmp_path / "original.horario.json"
    save_schedule(*generated, path)
    original = path.read_bytes()
    with (
        patch("scholar_calendar.schedule_file.os.replace", side_effect=OSError("Disk error")),
        pytest.raises(OSError),
    ):
        save_schedule(*generated, path)
    assert path.read_bytes() == original
    assert list(tmp_path.iterdir()) == [path]
