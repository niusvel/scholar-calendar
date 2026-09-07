from dataclasses import replace

from scholar_calendar.config import load_planning
from scholar_calendar.configuration_overview import configuration_sections


def test_overview_exposes_values_and_relationships():
    planning = load_planning("examples/cycle.json")
    sections = configuration_sections(planning)
    assert dict(sections["clock"])["Curso"] == planning.course_name
    assert "08:00" in dict(sections["clock"])["Franjas de clase"]
    assert dict(sections["days"])["Sábados activos"] == "Semana 2"
    assert len(sections["subjects"]) == len(planning.subjects)
    assert len(sections["teachers"]) == len(planning.teachers)
    assert len(sections["classrooms"]) == len(planning.classrooms)
    assert "Profesor 1" in dict(sections["subjects"])["Asignatura 1"]
    assert "Asignatura 1" in dict(sections["teachers"])["Profesor 1"]
    assert "Profesor 1" in dict(sections["classrooms"])["Aula 1"]
    assert "Asignatura 1 ↔ Asignatura 2" in dict(sections["rules"])["No consecutivas"]


def test_overview_exposes_blocked_days_and_unrestricted_classroom_access():
    planning = replace(
        load_planning("examples/cycle.json"),
        teacher_classrooms={},
        teacher_unavailable_days={"Profesor 1": frozenset({3})},
        subject_unavailable_days={"Asignatura 1": frozenset({5})},
    )
    sections = configuration_sections(planning)
    assert "Miércoles" in dict(sections["teachers"])["Profesor 1"]
    assert "Todas las aulas" in dict(sections["teachers"])["Profesor 1"]
    assert "Viernes" in dict(sections["subjects"])["Asignatura 1"]
