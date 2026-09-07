"""Run on a desktop with SCHOLAR_CALENDAR_GUI_TESTS=1."""

import os
from dataclasses import replace
from datetime import time
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from scholar_calendar.models import Classroom, PlanningInput, Subject, Teacher, build_slots
from scholar_calendar.solver import Schedule, ScheduledLesson

pytestmark = pytest.mark.skipif(
    os.environ.get("SCHOLAR_CALENDAR_GUI_TESTS") != "1", reason="Requires a desktop session"
)


@pytest.fixture
def app():
    from scholar_calendar.desktop import CalendarApp

    root = CalendarApp()
    root.geometry("980x650")
    root.report_callback_exception = lambda *args: pytest.fail(str(args))
    planning = PlanningInput(
        weeks=2,
        class_start=time(8),
        subjects=(Subject("Matemáticas", 1), Subject("Lengua", 1)),
        classrooms=tuple(Classroom(f"Aula {i}") for i in range(1, 7)),
        teachers=(Teacher("Ana"), Teacher("Luis")),
        teacher_subjects={
            "Ana": frozenset({"Matemáticas", "Lengua"}),
            "Luis": frozenset({"Matemáticas"}),
        },
        teacher_classrooms={},
        slots=build_slots(
            weeks=2, days=1, daily_periods=((time(8), time(8, 45)), (time(8, 50), time(9, 35)))
        ),
    )
    schedule = Schedule(
        (
            ScheduledLesson(1, 1, 1, "Aula 1", "Matemáticas", "Ana", "08:00", "08:45"),
            ScheduledLesson(1, 1, 1, "Aula 6", "Matemáticas", "Luis", "08:00", "08:45"),
            ScheduledLesson(1, 1, 2, "Aula 2", "Lengua", "Ana", "08:50", "09:35"),
            ScheduledLesson(2, 1, 1, "Aula 2", "Matemáticas", "Luis", "08:00", "08:45"),
        )
    )
    root._set_planning(planning)
    root.schedule_planning, root.schedule = planning, schedule
    root._render()
    root.notebook.select(root.schedule_tab)
    root.update()
    yield root
    root.destroy()


def click_cell(app, subject, *, last=False):
    grid = app.table
    cells = [cell for cell in grid.cells if cell[2] == subject]
    rectangle = (cells[-1] if last else cells[0])[0]
    x1, y1, x2, y2 = grid.body.coords(rectangle)
    x = (x1 + x2) / 2 - grid.body.canvasx(0)
    y = (y1 + y2) / 2 - grid.body.canvasy(0)
    assert 0 <= x <= grid.body.winfo_width()
    grid._double_click(SimpleNamespace(x=x, y=y))


def test_double_click_highlights_only_matching_cells_and_survives_week_changes(app):
    click_cell(app, "Matemáticas")
    assert app.selected_subject == "Matemáticas"
    assert "2 sesiones esta semana" in app.subject_highlight_var.get()
    for rectangle, _, subject, background in app.table.cells:
        assert app.table.body.itemcget(rectangle, "fill") == (
            "#ffedab" if subject == "Matemáticas" else background
        )
    app._change_week(1)
    assert app.selected_subject == "Matemáticas"
    assert "1 sesiones esta semana" in app.subject_highlight_var.get()
    assert (
        sum(app.table.body.itemcget(cell[0], "fill") == "#ffedab" for cell in app.table.cells) == 1
    )
    app.table.body.focus_force()
    app.table.body.event_generate("<Escape>")
    app.update()
    assert app.selected_subject is None
    assert all(app.table.body.itemcget(cell[0], "fill") == cell[3] for cell in app.table.cells)


def test_hit_detection_works_after_horizontal_scroll_and_empty_click_clears(app):
    app.table.body.xview_moveto(1)
    app.update()
    click_cell(app, "Matemáticas", last=True)
    assert app.selected_subject == "Matemáticas"
    app.table._click(SimpleNamespace(x=10, y=10))  # Day header.
    assert app.selected_subject is None


def test_ui_saves_generated_snapshot_and_loads_without_solving(app, tmp_path):
    generated_planning, generated_schedule = app.schedule_planning, app.schedule
    app.course_var.set("Configuración editada")
    path = tmp_path / "saved.horario.json"
    with patch("scholar_calendar.desktop.filedialog.asksaveasfilename", return_value=str(path)):
        app._save()
    app.schedule = None
    with patch("scholar_calendar.desktop.solve", side_effect=AssertionError("Must not solve")):
        app._load(path)
    assert app.schedule == generated_schedule
    assert app.schedule_planning == generated_planning
    assert app.course_var.get() == "Configuración editada"
    assert app.week_var.get() == "1"
    assert app.file_menu.entrycget("Exportar PDF", "state") == "normal"
    click_cell(app, "Matemáticas")
    assert app.selected_subject == "Matemáticas"
    with patch(
        "scholar_calendar.desktop.filedialog.asksaveasfilename",
        return_value=str(tmp_path / "loaded.pdf"),
    ):
        app._export_pdf()
    assert (tmp_path / "loaded.pdf").read_bytes().startswith(b"%PDF-")


def test_invalid_file_does_not_replace_open_schedule(app, tmp_path):
    original = app.schedule
    path = tmp_path / "broken.json"
    path.write_text('{"type": "invalid"}')
    with patch("scholar_calendar.desktop.messagebox.showerror") as show_error:
        app._load(path)
    show_error.assert_called_once()
    assert app.schedule is original


def test_restriction_note_uses_schedule_snapshot_and_clears_with_selection(app):
    app.schedule_planning = replace(
        app.schedule_planning,
        subject_unavailable_days={"Matemáticas": frozenset({3})},
        teacher_unavailable_days={"Ana": frozenset({5}), "Luis": frozenset({2})},
        teacher_classrooms={"Ana": frozenset({"Aula 1"})},
        forbidden_parallel=frozenset({frozenset({"Matemáticas", "Lengua"})}),
    )
    # Edits to the configuration must not replace the generated schedule's rules.
    app.planning = replace(app.planning, subject_unavailable_days={"Matemáticas": frozenset({6})})
    click_cell(app, "Matemáticas")
    app.update()
    note = app.restriction_note
    text = note.content.get("1.0", "end-1c")
    assert note.winfo_ismapped()
    assert "Miércoles" in text and "Sábado" not in text
    assert "Ana (en este horario): no disponible Viernes; solo puede impartir en Aula 1." in text
    assert "Luis (en este horario): no disponible Martes." in text
    assert "No simultánea entre aulas con: Lengua." in text
    assert note.border.itemcget(note.outline, "dash")
    assert note.content.cget("background") == "#fff8dc"
    assert note.content.cget("state") == "disabled"
    assert app.table.body.winfo_height() >= 54
    app._change_week(1)
    updated = note.content.get("1.0", "end-1c")
    assert "1 sesiones esta semana" in updated
    assert updated.split("\n", 1)[1] == text.split("\n", 1)[1]
    app.update()
    note.content.yview_moveto(1)
    app.update()
    assert note.content.yview()[1] == 1.0
    app._select_schedule_subject("Lengua")
    assert "Ana (en este horario)" in note.content.get("1.0", "end-1c")
    assert "Luis" not in note.content.get("1.0", "end-1c")
    app.table.body.focus_force()
    app.table.body.event_generate("<Escape>")
    app.update()
    assert not note.winfo_ismapped()


def test_configuration_has_one_overview_and_focused_modal_pages(app):
    assert [app.notebook.tab(tab, "text") for tab in app.notebook.tabs()] == [
        "Configuración del centro",
        "Horario",
    ]
    assert app.editor_window.state() == "withdrawn"
    for section in ("clock", "subjects", "teachers", "classrooms", "associations", "rules"):
        app._open_editor(section)
        app.update()
        assert app.editor_window.winfo_ismapped()
        assert app.editor_pages[section].winfo_ismapped()
        assert app.grab_current() == app.editor_window
        assert not any(
            page.winfo_ismapped() for key, page in app.editor_pages.items() if key != section
        )
        content = app.editor_content[section]
        assert content.winfo_reqwidth() <= content.winfo_width()
        app._cancel_editor()
        assert app.editor_window.state() == "withdrawn"
        assert app.grab_current() is None


def test_cancel_editor_restores_resources_rules_and_invalid_clock_text(app):
    original = app.planning
    app._open_editor("subjects")
    app.subject_name_var.set("Nueva")
    app._add_subject()
    app.teacher_subjects["Ana"].add("Nueva")
    app._add_rule("Matemáticas", "Lengua", "parallel")
    app.class_start_var.set("incorrecto")
    app.editor_window.event_generate("<Escape>")
    app.update()
    assert app._editor_snapshot is None
    assert app.planning == original
    assert "Nueva" not in {name for name, _, _ in app.subjects}
    assert "Nueva" not in app.teacher_subjects["Ana"]
    assert app.class_start_var.get() == "08:00"


def test_apply_editor_updates_overview_without_changing_generated_schedule(app, tmp_path):
    from scholar_calendar.project_file import load_project

    schedule, generated_planning = app.schedule, app.schedule_planning
    app.week_var.set("2")
    app._open_editor("subjects")
    app.subject_name_var.set("Nueva")
    app.subject_lessons_var.set(3)
    app._add_subject()
    app._apply_editor()
    app.update()
    assert app.editor_window.state() == "withdrawn"
    assert any(subject.name == "Nueva" for subject in app.planning.subjects)
    assert "3 asignaturas" in app.overview.summary.cget("text")
    assert app.schedule == schedule
    assert app.schedule_planning == generated_planning
    assert app.week_var.get() == "2"
    path = tmp_path / "changed.json"
    with patch("scholar_calendar.desktop.filedialog.asksaveasfilename", return_value=str(path)):
        app._save()
    assert any(subject.name == "Nueva" for subject in load_project(path).planning.subjects)


def test_invalid_modal_input_keeps_dialog_open_until_corrected(app):
    app._open_editor("clock")
    app.class_start_var.set("hora inválida")
    with patch("scholar_calendar.desktop.messagebox.showerror") as error:
        app._apply_editor()
    error.assert_called_once()
    assert app._editor_snapshot is not None
    assert app.grab_current() == app.editor_window
    app.class_start_var.set("08:30")
    app._apply_editor()
    assert app.planning.class_start == time(8, 30)
    assert app._editor_snapshot is None


def test_window_close_discards_modal_changes(app):
    original = app.planning
    app._open_editor("teachers")
    app.teacher_name_var.set("Nuevo profesor")
    app._add_teacher()
    app.tk.eval(app.editor_window.protocol("WM_DELETE_WINDOW"))
    assert app.planning == original
    assert "Nuevo profesor" not in app.teachers


def test_modal_is_centered_on_screen_and_file_actions_are_disabled(app):
    app.geometry("980x650+10+35")
    app.update()
    app._open_editor("clock")
    app.update()
    dialog = app.editor_window
    assert abs(dialog.winfo_x() - (app.winfo_screenwidth() - dialog.winfo_width()) / 2) <= 2
    assert abs(dialog.winfo_y() - (app.winfo_screenheight() - dialog.winfo_height()) / 2) <= 2
    for action in ("Guardar", "Cargar", "Exportar PDF", "Limpiar", "Salir"):
        assert app.file_menu.entrycget(action, "state") == "disabled"
    app._cancel_editor()
    assert app.file_menu.entrycget("Guardar", "state") == "normal"
    assert app.file_menu.entrycget("Exportar PDF", "state") == "normal"


def test_file_menu_clears_everything_and_reloads_saved_document(app, tmp_path):
    path = tmp_path / "centro.json"
    with patch("scholar_calendar.desktop.filedialog.asksaveasfilename", return_value=str(path)):
        app.file_menu.invoke("Guardar")
    original = path.read_bytes()
    schedule = app.schedule
    click_cell(app, "Matemáticas")
    app.subject_name_var.set("Borrador")
    app.subject_double_var.set(True)
    for variable in app.unavailable_day_vars.values():
        variable.set(True)
    app.file_menu.invoke("Limpiar")
    app.update()
    assert app.planning == app._blank_planning()
    defaults = app._blank_planning()
    assert app._sync_planning() == replace(
        defaults, day_period_counts={**defaults.day_period_counts, 6: 0}
    )
    assert app.schedule is None and app.schedule_planning is None
    assert app.document_path is None and app.selected_subject is None
    assert not app.restriction_note.winfo_ismapped()
    assert not app.subject_name_var.get() and not app.subject_double_var.get()
    assert not any(variable.get() for variable in app.unavailable_day_vars.values())
    assert app.class_start_var.get() == "08:30"
    assert app.notebook.select() == str(app.setup_tab)
    assert app.file_menu.entrycget("Exportar PDF", "state") == "disabled"
    assert path.read_bytes() == original
    tree = app.overview.period_tree
    rows = [tree.item(item, "values") for item in tree.get_children()]
    assert rows[0][1:] == ("08:30 – 09:15", "45 min")
    assert any(row[1:] == ("09:20 – 10:05", "45 min") for row in rows)
    assert any(row[0] == "Merienda" and row[1] == "10:05 – 10:25" for row in rows)
    with patch("scholar_calendar.desktop.filedialog.askopenfilename", return_value=str(path)):
        app.file_menu.invoke("Cargar")
    assert app.schedule == schedule
    assert app.file_menu.entrycget("Exportar PDF", "state") == "normal"


def test_resource_renames_and_deletion_keep_restrictions_consistent(app):
    planning = replace(
        app.planning,
        subject_unavailable_days={"Matemáticas": frozenset({3})},
        teacher_unavailable_days={"Ana": frozenset({5})},
        forbidden_parallel=frozenset({frozenset({"Matemáticas", "Lengua"})}),
    )
    app._set_planning(planning)
    snapshot = app.schedule_planning
    app._open_editor("subjects")
    app.subject_tree.selection_set(app.subject_tree.get_children()[0])
    app.subject_name_var.set("Álgebra")
    app._edit_subject()
    app._apply_editor()
    assert app.planning.subject_unavailable_days == {"Álgebra": frozenset({3})}
    assert app.planning.forbidden_parallel == frozenset({frozenset({"Álgebra", "Lengua"})})
    assert "Álgebra" in app.planning.teacher_subjects["Ana"]
    assert app.schedule_planning is snapshot
    app._open_editor("teachers")
    app.teacher_list.selection_set(0)
    app.teacher_name_var.set("Ana María")
    app._edit_teacher()
    app._apply_editor()
    assert app.planning.teacher_unavailable_days == {"Ana María": frozenset({5})}
    app._open_editor("subjects")
    app.subject_tree.selection_set(app.subject_tree.get_children()[0])
    app._remove_subject()
    app._apply_editor()
    assert not app.planning.subject_unavailable_days
    assert not app.planning.forbidden_parallel
    assert "Álgebra" not in app.planning.teacher_subjects["Ana María"]
    app._open_editor("teachers")
    app.teacher_list.selection_set(0)
    app._remove_teacher()
    app._apply_editor()
    assert not app.planning.teacher_unavailable_days
    assert "Ana María" not in app.planning.teacher_classrooms


def test_duplicate_rename_and_invalid_subject_frequency_do_not_mutate_resources(app):
    app._open_editor("subjects")
    original = list(app.subjects)
    app.subject_tree.selection_set(app.subject_tree.get_children()[0])
    app.subject_name_var.set("Lengua")
    with patch("scholar_calendar.desktop.messagebox.showerror") as error:
        app._edit_subject()
    error.assert_called_once()
    assert app.subjects == original
    app.subject_name_var.set("Nueva")
    app.subject_lessons_var.set("incorrecto")
    with patch("scholar_calendar.desktop.messagebox.showerror") as error:
        app._add_subject()
    error.assert_called_once()
    assert app.subjects == original
    app._cancel_editor()


def test_unrestricted_teachers_and_irregular_slots_survive_saving(app, tmp_path):
    from scholar_calendar.project_file import load_project

    planning = replace(
        app.planning,
        classrooms=(Classroom("Aula 1, laboratorio"), *app.planning.classrooms[1:]),
        slots=tuple(
            replace(slot, start=time(7, 45)) if slot.week == 2 and slot.period == 1 else slot
            for slot in app.planning.slots
        ),
    )
    app._set_planning(planning)
    path = tmp_path / "exact.json"
    with patch("scholar_calendar.desktop.filedialog.asksaveasfilename", return_value=str(path)):
        app._save()
    restored = load_project(path).planning
    assert restored.slots == planning.slots
    assert restored.classrooms == planning.classrooms
    assert restored.teacher_classrooms == {}
