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
    with patch("scholar_calendar.desktop.ask_project_path", return_value=str(path)):
        app._save()
    app.schedule = None
    with patch("scholar_calendar.desktop.solve", side_effect=AssertionError("Must not solve")):
        app._load(path)
    assert app.schedule == generated_schedule
    assert app.schedule_planning == replace(generated_planning, course_name="Configuración editada")
    assert app.course_var.get() == "Configuración editada"
    assert app.week_var.get() == "1"
    assert app.export_button.instate(["!disabled"])
    click_cell(app, "Matemáticas")
    assert app.selected_subject == "Matemáticas"
    with patch(
        "scholar_calendar.desktop.filedialog.asksaveasfilename",
        return_value=str(tmp_path / "loaded.pdf"),
    ):
        app.export_button.invoke()
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
    for section in ("classrooms", "subjects", "teachers", "clock"):
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
    with patch("scholar_calendar.desktop.ask_project_path", return_value=str(path)):
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
    assert app.export_button.instate(["disabled"])
    for action in ("Guardar", "Cargar", "Limpiar", "Reglas de generación", "Salir"):
        assert app.file_menu.entrycget(action, "state") == "disabled"
    app._cancel_editor()
    assert app.file_menu.entrycget("Guardar", "state") == "normal"
    assert app.export_button.instate(["!disabled"])


def test_file_menu_clears_everything_and_reloads_saved_document(app, tmp_path):
    path = tmp_path / "centro.json"
    with patch("scholar_calendar.desktop.ask_project_path", return_value=str(path)):
        app.file_menu.invoke("Guardar")
    original = path.read_bytes()
    schedule = app.schedule
    click_cell(app, "Matemáticas")
    app.subject_name_var.set("Borrador")
    app.subject_double_var.set(True)
    for days in app.unavailable_day_vars.values():
        for variable in days.values():
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
    assert not any(
        variable.get() for days in app.unavailable_day_vars.values() for variable in days.values()
    )
    assert app.class_start_var.get() == "07:40"
    assert app.notebook.select() == str(app.setup_tab)
    assert app.export_button.instate(["disabled"])
    assert path.read_bytes() == original
    tree = app.overview.period_tree
    rows = [tree.item(item, "values") for item in tree.get_children()]
    assert rows[0][1:] == ("07:40 – 08:25", "45 min")
    assert any(row[1:] == ("09:20 – 10:05", "45 min") for row in rows)
    assert any(row[0] == "Merienda" and row[1] == "10:05 – 10:25" for row in rows)
    with patch("scholar_calendar.desktop.ask_project_path", return_value=str(path)):
        app.file_menu.invoke("Cargar")
    assert app.schedule == schedule
    assert app.export_button.instate(["!disabled"])


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
    with patch("scholar_calendar.desktop.ask_project_path", return_value=str(path)):
        app._save()
    restored = load_project(path).planning
    assert restored.slots == planning.slots
    assert restored.classrooms == planning.classrooms
    assert restored.teacher_classrooms == {}


def test_loaded_schedule_receives_cosmetic_edits_without_solving(app, tmp_path):
    from scholar_calendar.project_file import CalendarProject, load_project, save_project

    path = tmp_path / "renamed.json"
    original = app.schedule
    save_project(CalendarProject(app.planning, app.schedule_planning, app.schedule), path)
    with patch("scholar_calendar.desktop.solve", side_effect=AssertionError("Must not regenerate")):
        app._load(path)
        click_cell(app, "Matemáticas")
        app._change_week(1)
        app._open_editor("subjects")
        app.subject_tree.selection_set(app.subject_tree.get_children()[0])
        app._select_subject(None)
        app.subject_name_var.set("Álgebra")
        app._edit_subject()
        app._apply_editor()
        app.update()
        assert app.selected_subject == "Álgebra"
        assert app.week_var.get() == "2"
        assert "Álgebra" in app.restriction_note.content.get("1.0", "end-1c")
        app._open_editor("teachers")
        app.teacher_list.selection_set(0)
        app.teacher_name_var.set("Ana María")
        app._edit_teacher()
        app._apply_editor()
        app._open_editor("classrooms")
        app.classroom_list.selection_set(0)
        app.classroom_name_var.set("Grupo A")
        app._edit_classroom()
        app._apply_editor()
        app._open_editor("clock")
        app.course_var.set("Curso actualizado")
        app._apply_editor()
        assert not app.schedule_needs_regeneration
        assert not app.schedule_notice.winfo_ismapped()
        expected = tuple(
            replace(
                lesson,
                subject="Álgebra" if lesson.subject == "Matemáticas" else lesson.subject,
                teacher="Ana María" if lesson.teacher == "Ana" else lesson.teacher,
                classroom="Grupo A" if lesson.classroom == "Aula 1" else lesson.classroom,
            )
            for lesson in original.lessons
        )
        assert app.schedule.lessons == expected
        with patch("scholar_calendar.desktop.ask_project_path", return_value=str(path)):
            app._save()
        assert load_project(path).schedule.lessons == expected
        app._load(path)
        assert app.schedule.lessons == expected
        assert not app.schedule_needs_regeneration
        with (
            patch(
                "scholar_calendar.desktop.filedialog.asksaveasfilename",
                return_value=str(tmp_path / "renamed.pdf"),
            ),
            patch("scholar_calendar.pdf.export_schedule_pdf") as export,
        ):
            app.export_button.invoke()
        assert export.call_args.args[0].course_name == "Curso actualizado"
        assert export.call_args.args[1].lessons == expected


def test_cancel_preserves_names_and_stale_warning_survives_save_load_and_failed_generation(
    app, tmp_path
):
    from scholar_calendar.solver import ScheduleError

    original = app.schedule
    app._open_editor("subjects")
    app.subject_tree.selection_set(app.subject_tree.get_children()[0])
    app._select_subject(None)
    app.subject_name_var.set("Nombre descartado")
    app._edit_subject()
    app._cancel_editor()
    assert app.schedule is original
    assert not app.schedule_needs_regeneration
    app._open_editor("subjects")
    app.subject_tree.selection_set(app.subject_tree.get_children()[0])
    app._select_subject(None)
    app.subject_lessons_var.set(2)
    app._edit_subject()
    app._apply_editor()
    app.update()
    assert app.schedule_needs_regeneration
    assert app.schedule_notice.winfo_ismapped()
    assert app.schedule is original
    path = tmp_path / "stale.json"
    with patch("scholar_calendar.desktop.ask_project_path", return_value=str(path)):
        app._save()
    app._load(path)
    app.update()
    assert app.schedule_needs_regeneration and app.schedule_notice.winfo_ismapped()
    with (
        patch("scholar_calendar.desktop.solve", side_effect=ScheduleError("No cabe")),
        patch("scholar_calendar.desktop.messagebox.showerror"),
    ):
        app._generate()
    assert app.schedule_needs_regeneration
    assert app.schedule == original
    app._open_editor("subjects")
    app.subject_tree.selection_set(app.subject_tree.get_children()[0])
    app._select_subject(None)
    app.subject_lessons_var.set(1)
    app._edit_subject()
    app._apply_editor()
    app.update()
    assert not app.schedule_needs_regeneration and not app.schedule_notice.winfo_ismapped()


def test_mixed_rename_and_generation_change_requires_new_schedule(app):
    original = app.schedule
    app._open_editor("subjects")
    app.subject_tree.selection_set(app.subject_tree.get_children()[0])
    app._select_subject(None)
    app.subject_name_var.set("Álgebra")
    app.subject_lessons_var.set(2)
    app._edit_subject()
    app._apply_editor()
    assert app.schedule_needs_regeneration
    assert app.schedule is original
    with patch("scholar_calendar.desktop.solve", return_value=Schedule(())) as generate:
        app._generate()
    generate.assert_called_once()
    assert not app.schedule_needs_regeneration
    assert app.schedule_planning == app.planning


def test_scoped_associations_and_double_rooms_apply_cancel_and_round_trip(app, tmp_path):
    app._open_editor("associations")
    row = next(
        item
        for item in app.association_tree.get_children()
        if app.association_tree.item(item, "values")[:2] == ("Ana", "Matemáticas")
    )
    app.association_tree.selection_set(row)
    app._select_association(None)
    assert app.association_scope.get_scope() is None
    app.association_scope.set_scope(frozenset({"Aula 1"}))
    app._edit_association()
    app._cancel_editor()
    assert app.planning.teacher_subject_classrooms == {}
    app._open_editor("associations")
    row = next(
        item
        for item in app.association_tree.get_children()
        if app.association_tree.item(item, "values")[:2] == ("Ana", "Matemáticas")
    )
    app.association_tree.selection_set(row)
    app._select_association(None)
    app.association_scope.set_scope(frozenset({"Aula 1"}))
    app._edit_association()
    app._apply_editor()
    assert app.schedule_needs_regeneration
    assert app.planning.teacher_subject_classrooms["Ana"]["Matemáticas"] == frozenset({"Aula 1"})
    app._open_editor("subjects")
    app.subject_tree.selection_set(app.subject_tree.get_children()[0])
    app._select_subject(None)
    app.subject_double_var.set(True)
    assert app.subject_scope.all_check.instate(["!disabled"])
    app.subject_scope.set_scope(frozenset({"Aula 1", "Aula 2"}))
    app._edit_subject()
    app._apply_editor()
    assert app.planning.subjects[0].is_double_in("Aula 1")
    assert not app.planning.subjects[0].is_double_in("Aula 3")
    expected = app.planning
    path = tmp_path / "scopes.json"
    with patch("scholar_calendar.desktop.ask_project_path", return_value=str(path)):
        app._save()
    app._clear_project()
    app._load(path)
    assert app.planning == expected
    assert app.schedule_needs_regeneration
    app._open_editor("subjects")
    app.subject_tree.selection_set(app.subject_tree.get_children()[0])
    app._select_subject(None)
    assert app.subject_scope.get_scope() == frozenset({"Aula 1", "Aula 2"})
    app._cancel_editor()


def test_scopes_follow_ui_renames_and_last_room_deletion_stays_empty(app):
    planning = replace(
        app.planning,
        subjects=(
            replace(
                app.planning.subjects[0],
                double_period=True,
                double_classrooms=frozenset({"Aula 1"}),
            ),
            app.planning.subjects[1],
        ),
        teacher_subject_classrooms={"Ana": {"Matemáticas": frozenset({"Aula 1"})}},
    )
    app._set_planning(planning)
    app.schedule_planning = planning
    app._open_editor("classrooms")
    app.classroom_list.selection_set(0)
    app.classroom_name_var.set("Grupo 1, A")
    app._edit_classroom()
    app._apply_editor()
    assert not app.schedule_needs_regeneration
    assert app.planning.subjects[0].double_classrooms == frozenset({"Grupo 1, A"})
    app._open_editor("teachers")
    app.teacher_list.selection_set(0)
    app.teacher_name_var.set("Ana María")
    app._edit_teacher()
    app._apply_editor()
    assert not app.schedule_needs_regeneration
    app._open_editor("subjects")
    app.subject_tree.selection_set(app.subject_tree.get_children()[0])
    app._select_subject(None)
    assert app.subject_scope.get_scope() == frozenset({"Grupo 1, A"})
    app.subject_name_var.set("Álgebra")
    app._edit_subject()
    app._apply_editor()
    assert not app.schedule_needs_regeneration
    assert app.planning.teacher_subject_classrooms == {
        "Ana María": {"Álgebra": frozenset({"Grupo 1, A"})}
    }
    app._open_editor("classrooms")
    app.classroom_list.selection_set(0)
    app._remove_classroom()
    app._apply_editor()
    assert app.schedule_needs_regeneration
    assert app.planning.subjects[0].double_classrooms == frozenset()
    assert app.planning.teacher_subject_classrooms["Ana María"]["Álgebra"] == frozenset()
    app._open_editor("subjects")
    app.subject_tree.selection_set(app.subject_tree.get_children()[0])
    app._remove_subject()
    app._apply_editor()
    assert "Álgebra" not in app.subject_double_classrooms
    assert "Álgebra" not in app.planning.teacher_subject_classrooms["Ana María"]


def test_configuration_orders_resources_and_keeps_restrictions_in_their_context(app):
    assert list(app.overview.cards) == ["classrooms", "subjects", "teachers", "clock", "days"]
    app._open_editor("subjects")
    notebook = app.editor_notebooks["subjects"]
    assert [notebook.tab(tab, "text") for tab in notebook.tabs()] == [
        "Asignaturas y aulas",
        "Disponibilidad",
        "Incompatibilidades",
    ]
    app.subject_tree.selection_set(app.subject_tree.get_children()[0])
    app._select_subject(None)
    notebook.select(app.editor_tab_pages["subject_days"])
    app.update()
    assert app.unavailable_subject_var.get() == "Matemáticas"
    app.unavailable_day_vars["subject"][3].set(True)
    app._add_unavailable("subject")
    assert app.planning.subject_unavailable_days == {"Matemáticas": frozenset({3})}
    app._cancel_editor()
    assert not app.planning.subject_unavailable_days
    app._open_editor("teachers")
    app.teacher_list.selection_set(0)
    app._select_teacher(None)
    notebook = app.editor_notebooks["teachers"]
    assert [notebook.tab(tab, "text") for tab in notebook.tabs()] == [
        "Profesores",
        "Asignaturas y aulas",
        "Aulas generales",
        "Disponibilidad",
    ]
    notebook.select(app.editor_tab_pages["teacher_days"])
    app.update()
    assert app.unavailable_teacher_var.get() == "Ana"
    assert not any(variable.get() for variable in app.unavailable_day_vars["teacher"].values())
    app.unavailable_day_vars["teacher"][2].set(True)
    app._add_unavailable("teacher")
    app._apply_editor()
    assert app.planning.teacher_unavailable_days == {"Ana": frozenset({2})}
    assert not app.planning.subject_unavailable_days
    app._clear_project()
    assert (
        app.editor_notebooks["teachers"].tab(app.editor_tab_pages["associations"], "state")
        == "disabled"
    )
    app._open_editor("teachers")
    app.teacher_name_var.set("Nueva profesora")
    app._add_teacher()
    assert (
        app.editor_notebooks["teachers"].tab(app.editor_tab_pages["teacher_days"], "state")
        == "normal"
    )
    app._cancel_editor()


def test_project_picker_previews_valid_projects_and_rejects_invalid_files(app, tmp_path):
    from scholar_calendar.project_dialog import ProjectDialog
    from scholar_calendar.project_file import CalendarProject, save_project

    folder = tmp_path / "horarios"
    folder.mkdir()
    saved = folder / "centro.json"
    save_project(CalendarProject(app.planning, app.schedule_planning, app.schedule), saved)
    (folder / "roto.json").write_text("[]")
    (folder / "nota.txt").write_text("no es un proyecto")
    dialog = ProjectDialog(app, save=False, initial_path=tmp_path / "previo.json")
    app.update()
    assert abs(dialog.winfo_x() - (app.winfo_screenwidth() - dialog.winfo_width()) / 2) <= 2
    row = next(item for item, path in dialog.paths.items() if path == folder)
    dialog.tree.selection_set(row)
    dialog._activate()
    assert dialog.folder == folder
    assert {path.name for path in dialog.paths.values()} == {"centro.json", "roto.json"}
    row = next(item for item, path in dialog.paths.items() if path.name == "roto.json")
    dialog.tree.selection_set(row)
    dialog._selected()
    dialog._accept()
    assert dialog.result is None and dialog.accept_button.instate(["disabled"])
    dialog.search.set("CENTRO")
    assert len(dialog.paths) == 1
    dialog.tree.selection_set(next(iter(dialog.paths)))
    dialog._selected()
    assert "Incluye horario generado" in dialog.info.get()
    assert dialog.accept_button.instate(["!disabled"])
    dialog._accept()
    assert dialog.result == str(saved)
    assert saved.exists()


def test_project_picker_save_cancel_and_overwrite_do_not_write_files(app, tmp_path):
    from scholar_calendar.project_dialog import ProjectDialog

    existing = tmp_path / "centro.json"
    existing.write_text("contenido original")
    dialog = ProjectDialog(app, save=True, initial_path=existing)
    app.update()
    assert dialog.name_entry.winfo_ismapped() and dialog.name_entry.winfo_height() > 10
    assert dialog.info_label.winfo_ismapped() and dialog.info_label.winfo_height() > 10
    with patch("scholar_calendar.project_dialog.messagebox.askyesno", return_value=False):
        dialog._accept()
    assert dialog.result is None and dialog.winfo_exists()
    assert existing.read_text() == "contenido original"
    dialog.filename.set("../fuera.json")
    dialog._accept()
    assert dialog.result is None and dialog.error.get()
    dialog.filename.set("nuevo")
    dialog._accept()
    assert dialog.result == str(tmp_path / "nuevo.json")
    assert not (tmp_path / "nuevo.json").exists()
    dialog = ProjectDialog(app, save=False, initial_path=existing)
    dialog.destroy()
    assert dialog.result is None


def test_period_pair_editor_add_edit_cancel_and_round_trip(app, tmp_path):
    from scholar_calendar.models import AvailabilityBlock

    app._set_planning(replace(app.planning, day_period_counts={1: 4, 2: 4}))
    original = app.planning
    app._open_editor("teachers")
    app.editor_notebooks["teachers"].select(app.editor_tab_pages["teacher_days"])
    app.update()
    editor = app.availability_editors["teacher"]
    editor.focus_resource("Ana")
    editor.subject_combo.current(editor.subject_options.index("Matemáticas"))
    editor.days[2].set(True)
    editor.period.set("4")
    editor.add()
    block = AvailabilityBlock(day=2, period=4, teacher="Ana", subject="Matemáticas")
    assert app.planning.availability_blocks == frozenset({block})
    assert editor.subject_options[editor.subject_combo.current()] == "Matemáticas"
    editor.period.set("2")
    editor.add()
    assert app.planning.availability_blocks == frozenset({block, replace(block, period=2)})
    row = next(item for item, rule in editor.rows.items() if rule == block)
    editor.tree.selection_set(row)
    editor._select()
    editor.period.set("3")
    editor.add(edit=True)
    assert app.planning.availability_blocks == frozenset(
        {replace(block, period=2), replace(block, period=3)}
    )
    app._cancel_editor()
    assert app.planning == original
    app._open_editor("teachers")
    editor.focus_resource("Ana")
    editor.subject_combo.current(editor.subject_options.index("Matemáticas"))
    editor.days[2].set(True)
    editor.period.set("4")
    editor.add()
    app._apply_editor()
    assert app.schedule_needs_regeneration
    path = tmp_path / "blocked-turn.json"
    with patch("scholar_calendar.desktop.ask_project_path", return_value=str(path)):
        app._save()
    app._clear_project()
    app._load(path)
    assert app.planning.availability_blocks == frozenset({block})
    assert app.schedule_needs_regeneration
    app._open_editor("teachers")
    assert block in editor.rows.values()
    row = next(item for item, rule in editor.rows.items() if rule == block)
    editor.tree.selection_set(row)
    editor._select()
    assert editor.period.get() == "4"
    assert editor.days[2].get()
    editor.remove()
    app._apply_editor()
    assert app.planning.availability_blocks == frozenset()


def test_pair_blocks_follow_renames_and_association_deletion_preserves_general_blocks(app):
    from scholar_calendar.models import AvailabilityBlock

    pair = AvailabilityBlock(day=2, period=2, teacher="Ana", subject="Matemáticas")
    general = AvailabilityBlock(day=3, period=1, teacher="Ana")
    app._set_planning(replace(app.planning, availability_blocks=frozenset({pair, general})))
    app.schedule_planning = app.planning
    app._open_editor("teachers")
    app.teacher_list.selection_set(0)
    app.teacher_name_var.set("Ana María")
    app._edit_teacher()
    app._apply_editor()
    assert not app.schedule_needs_regeneration
    app._open_editor("subjects")
    app.subject_tree.selection_set(app.subject_tree.get_children()[0])
    app._select_subject(None)
    app.subject_name_var.set("Álgebra")
    app._edit_subject()
    app._apply_editor()
    assert not app.schedule_needs_regeneration
    renamed_pair = replace(pair, teacher="Ana María", subject="Álgebra")
    renamed_general = replace(general, teacher="Ana María")
    assert app.planning.availability_blocks == frozenset({renamed_pair, renamed_general})
    app._open_editor("associations")
    row = next(
        item
        for item in app.association_tree.get_children()
        if app.association_tree.item(item, "values")[:2] == ("Ana María", "Álgebra")
    )
    app.association_tree.selection_set(row)
    app._remove_association()
    app._apply_editor()
    assert app.planning.availability_blocks == frozenset({renamed_general})
    assert app.schedule_needs_regeneration


def test_availability_classroom_scope_add_edit_and_resource_lifecycle(app, tmp_path):
    from scholar_calendar.models import AvailabilityBlock

    app._set_planning(replace(app.planning, day_period_counts={1: 5, 2: 5, 4: 5}))
    app._open_editor("teachers")
    editor = app.availability_editors["teacher"]
    editor.focus_resource("Ana")
    editor.subject_combo.current(editor.subject_options.index("Matemáticas"))
    editor.classroom_combo.current(editor.classroom_options.index("Aula 1"))
    for day in (1, 2):
        editor.days[day].set(True)
    for period in (4, 5):
        editor.period.set(str(period))
        editor.add()
    editor.days[1].set(False)
    editor.days[2].set(False)
    editor.days[4].set(True)
    editor.add()
    blocks = frozenset(
        AvailabilityBlock(
            day=day, period=period, teacher="Ana", subject="Matemáticas", classroom="Aula 1"
        )
        for day, period in ((1, 4), (1, 5), (2, 4), (2, 5), (4, 5))
    )
    assert app.planning.availability_blocks == blocks
    row = next(item for item, block in editor.rows.items() if block.day == 4)
    editor.tree.selection_set(row)
    editor._select()
    assert editor.classroom_options[editor.classroom_combo.current()] == "Aula 1"
    editor.classroom_combo.current(editor.classroom_options.index("Aula 2"))
    editor.add(edit=True)
    assert any(block.classroom == "Aula 2" for block in app.planning.availability_blocks)
    app._cancel_editor()
    assert not app.planning.availability_blocks

    app._set_planning(replace(app.planning, availability_blocks=blocks))
    app.schedule_planning = app.planning
    app._open_editor("classrooms")
    app.classroom_list.selection_set(0)
    app.classroom_name_var.set("Nueva")
    app._edit_classroom()
    app._apply_editor()
    assert not app.schedule_needs_regeneration
    assert all(block.classroom == "Nueva" for block in app.planning.availability_blocks)
    path = tmp_path / "bloqueos-aulas.json"
    with patch("scholar_calendar.desktop.ask_project_path", return_value=str(path)):
        app._save()
    app._clear_project()
    app._load(path)
    assert all(block.classroom == "Nueva" for block in app.planning.availability_blocks)

    app._open_editor("subjects")
    editor = app.availability_editors["subject"]
    editor.focus_resource("Lengua")
    editor.classroom_combo.current(editor.classroom_options.index("Aula 2"))
    editor.days[1].set(True)
    editor.add()
    subject_block = AvailabilityBlock(day=1, subject="Lengua", classroom="Aula 2")
    app._apply_editor()
    assert subject_block in app.planning.availability_blocks
    app._open_editor("classrooms")
    app.classroom_list.selection_set(0)
    app._remove_classroom()
    app._apply_editor()
    assert app.planning.availability_blocks == frozenset({subject_block})
    assert app.schedule_needs_regeneration


def test_generation_failure_shows_real_conflicts_and_preserves_existing_schedule(app):
    from scholar_calendar.models import AvailabilityBlock

    previous = app.schedule
    app._set_planning(
        replace(
            app.planning,
            weeks=1,
            classrooms=(Classroom("Aula 1"),),
            subjects=(Subject("Matemáticas", 1),),
            teachers=(Teacher("Ana"),),
            teacher_subjects={"Ana": frozenset({"Matemáticas"})},
            slots=app.planning.slots[:1],
            day_period_counts={1: 1},
            availability_blocks=frozenset(
                {
                    AvailabilityBlock(
                        day=1, period=1, teacher="Ana", subject="Matemáticas", classroom="Aula 1"
                    )
                }
            ),
        )
    )
    app._generate()
    app.update()
    dialog = app.generation_error_window
    content = dialog.content.get("1.0", "end")
    assert "Matemáticas · Aula 1 · semana 1" in content
    assert "Lunes · turno 1 · aula Aula 1" in content
    assert "Revisar: Profesores → Disponibilidad" in content
    assert str(dialog.content.cget("state")) == "disabled"
    assert abs(dialog.winfo_x() - (app.winfo_screenwidth() - dialog.winfo_width()) // 2) < 5
    assert abs(dialog.winfo_y() - (app.winfo_screenheight() - dialog.winfo_height()) // 2) < 5
    assert app.schedule is previous
    assert app.schedule_needs_regeneration
    dialog.review_button.invoke()
    app.update()
    assert not dialog.winfo_exists()
    assert app.notebook.select() == str(app.setup_tab)


def test_generation_timeout_shows_no_false_configuration_conflicts(app):
    from ortools.sat.python import cp_model

    previous = app.schedule
    with (
        patch.object(cp_model.CpSolver, "Solve", return_value=cp_model.UNKNOWN),
        patch("scholar_calendar.desktop.messagebox.showerror") as showerror,
    ):
        app._generate()
    assert "no se ha demostrado" in showerror.call_args.args[1]
    assert app.schedule is previous
