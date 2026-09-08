"""Tk application controller; edited configuration and generated snapshots stay separate."""

from __future__ import annotations

import tkinter as tk
from copy import deepcopy
from dataclasses import replace
from datetime import time
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .clock import DEFAULT_CLASS_START, minutes_since_midnight, parse_optional_time
from .configuration_overview import ConfigurationOverview
from .defaults import default_planning
from .models import Classroom, PlanningInput, Subject, Teacher, build_daily_periods, build_slots
from .project_file import CalendarProject, load_project, save_project
from .restriction_note import RestrictionNote
from .rules_help import RulesHelp
from .schedule_grid import GridRow, ScheduleGrid
from .schedule_updates import ResourceRename, requires_regeneration, update_schedule_metadata
from .solver import Schedule, ScheduleError, solve
from .subject_details import subject_restrictions
from .theme import INK, PALE_TEAL, PAPER, TEAL, configure_styles
from .timeline import DAY_NAMES, daily_rows
from .validation import validate_planning


class CalendarApp(tk.Tk):
    def __init__(self, config_path: str | None = None) -> None:
        super().__init__()
        self.withdraw()
        self.title("Scholar Calendar")
        self.geometry("1320x860")
        self.minsize(980, 650)
        self.configure(bg=PAPER)
        self.planning: PlanningInput | None = None
        self.schedule: Schedule | None = None
        self.schedule_planning: PlanningInput | None = None
        self.document_path: Path | None = None
        self.selected_subject: str | None = None
        self.subject_highlight_var = tk.StringVar(
            value="Doble clic en una clase para resaltar su asignatura. Escape para quitar el resaltado."
        )
        self.subjects: list[tuple[str, int, bool]] = []
        self.teachers: list[str] = []
        self.teacher_subjects: dict[str, set[str]] = {}
        self.teacher_classrooms: dict[str, set[str]] = {}
        self.course_var = tk.StringVar()
        self.weeks_var = tk.IntVar(value=2)
        self.classroom_name_var = tk.StringVar()
        self.day_count_vars = {day: tk.IntVar(value=6) for day in range(1, 7)}
        self.saturday_vars: dict[int, tk.BooleanVar] = {}
        self.subject_name_var = tk.StringVar()
        self.subject_lessons_var = tk.IntVar(value=1)
        self.subject_double_var = tk.BooleanVar(value=False)
        self.teacher_name_var = tk.StringVar()
        self.class_start_var = tk.StringVar(value=DEFAULT_CLASS_START.strftime("%H:%M"))
        self.period_duration_var = tk.IntVar(value=45)
        self.transition_var = tk.IntVar(value=5)
        self.break_start_var = tk.StringVar(value="10:05")
        self.break_end_var = tk.StringVar(value="10:25")
        self.lunch_start_var = tk.StringVar(value="13:40")
        self.lunch_end_var = tk.StringVar(value="15:00")
        self.lunch_after_var = tk.IntVar(value=6)
        self.classroom_teacher_var = tk.StringVar()
        self.classroom_names_var = tk.StringVar()
        self.unavailable_teacher_var = tk.StringVar()
        self.unavailable_subject_var = tk.StringVar()
        self.consecutive_first_var = tk.StringVar()
        self.consecutive_second_var = tk.StringVar()
        self.parallel_first_var = tk.StringVar()
        self.parallel_second_var = tk.StringVar()
        self.association_subject_var = tk.StringVar()
        self.association_teacher_var = tk.StringVar()
        self.week_var = tk.StringVar(value="1")
        self.status_var = tk.StringVar(
            value="Empieza por definir la jornada, las asignaturas y el equipo docente."
        )
        self.schedule_summary_var = tk.StringVar(
            value="Genera un horario para consultar la distribución semanal."
        )
        self.clock_preview_var = tk.StringVar()
        self._loaded_clock_signature = None
        self._clock_preview_job = None
        self._editor_snapshot = None
        self._editor_renames: list[ResourceRename] = []
        self.schedule_needs_regeneration = False
        self.rules_window: RulesHelp | None = None
        configure_styles(self)
        self._build_ui()
        self.bind("<Escape>", lambda _event: self._select_schedule_subject(None))
        self._set_planning(self._blank_planning())
        if config_path:
            self._load(Path(config_path))
        for variable in self._clock_variables() + tuple(self.day_count_vars.values()):
            variable.trace_add("write", self._queue_clock_preview)
        self.weeks_var.trace_add("write", lambda *_args: self._refresh_saturday_controls())
        self._update_clock_preview()
        self._center_window()
        self.deiconify()

    def _center_window(self) -> None:
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        width = min(1320, max(980, screen_width - 80))
        height = min(860, max(650, screen_height - 100))
        x = max(0, (screen_width - width) // 2)
        y = max(0, (screen_height - height) // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    _blank_planning = staticmethod(default_planning)

    def _build_ui(self) -> None:
        header = ttk.Frame(self, style="Header.TFrame", padding=(24, 16))
        header.pack(fill=tk.X)
        self._header = header
        self._build_file_menu(header)
        brand = ttk.Frame(header, style="Header.TFrame")
        brand.pack(side=tk.LEFT)
        ttk.Label(brand, text="Scholar Calendar", style="Title.TLabel").pack(anchor=tk.W)
        ttk.Label(
            brand,
            text="Planificación de tu centro",
            style="Subtitle.TLabel",
        ).pack(anchor=tk.W, pady=(5, 0))
        toolbar = ttk.Frame(header, style="Header.TFrame")
        toolbar.pack(side=tk.RIGHT)
        self.generate_button = ttk.Button(
            toolbar, text="Generar horario", style="Accent.TButton", command=self._generate
        )
        self.generate_button.pack(side=tk.RIGHT, padx=(12, 0))
        self.export_button = ttk.Button(
            toolbar, text="Exportar PDF", command=self._export_pdf, state="disabled"
        )
        self.export_button.pack(side=tk.RIGHT, padx=(12, 0))
        self.schedule_notice = ttk.Frame(self, style="Warning.TFrame", padding=(14, 6))
        notice = ttk.Label(
            self.schedule_notice,
            text="La configuración ha cambiado: debes generar un nuevo horario.",
            style="Warning.TLabel",
            wraplength=900,
        )
        notice.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.schedule_notice.bind(
            "<Configure>", lambda event: notice.configure(wraplength=max(200, event.width - 28))
        )
        ttk.Label(self, textvariable=self.status_var, style="Status.TLabel", padding=(24, 10)).pack(
            side=tk.BOTTOM, fill=tk.X
        )
        body = ttk.Frame(self, style="App.TFrame", padding=(24, 16, 24, 0))
        body.pack(fill=tk.BOTH, expand=True)
        self.notebook = ttk.Notebook(body)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        self.setup_tab = ttk.Frame(self.notebook, style="App.TFrame")
        self.schedule_tab = ttk.Frame(self.notebook, style="App.TFrame")
        for frame, title in (
            (self.setup_tab, "Configuración del centro"),
            (self.schedule_tab, "Horario"),
        ):
            self.notebook.add(frame, text=title)
        self._scroll_canvases = {}
        overview_content = self._build_scroll_page(self.setup_tab)
        self.overview = ConfigurationOverview(overview_content, self._open_editor)
        self.overview.pack(fill=tk.X)
        self._build_editor_window()
        self.bind_all("<MouseWheel>", self._scroll_setup)
        self.bind_all("<Button-4>", self._scroll_setup)
        self.bind_all("<Button-5>", self._scroll_setup)
        self._build_setup_tab()
        self._build_schedule_tab()

    def _build_editor_window(self) -> None:
        self.editor_window = tk.Toplevel(self)
        self.editor_window.withdraw()
        self.editor_window.transient(self)
        self.editor_window.configure(background=PAPER)
        self.editor_window.protocol("WM_DELETE_WINDOW", self._cancel_editor)
        self.editor_window.bind("<Escape>", self._cancel_editor)
        heading = ttk.Frame(self.editor_window, style="Card.TFrame", padding=(22, 16))
        heading.pack(fill=tk.X)
        self.editor_title = ttk.Label(heading, style="Section.TLabel")
        self.editor_title.pack(anchor=tk.W)
        ttk.Label(
            heading,
            text="Edita esta sección y guarda los cambios para aplicarlos al centro.",
            style="Muted.TLabel",
        ).pack(anchor=tk.W, pady=(5, 0))
        actions = ttk.Frame(self.editor_window, style="Card.TFrame", padding=(22, 12))
        actions.pack(side=tk.BOTTOM, fill=tk.X)
        ttk.Button(
            actions, text="Guardar cambios", style="Accent.TButton", command=self._apply_editor
        ).pack(side=tk.RIGHT)
        ttk.Button(actions, text="Cancelar", command=self._cancel_editor).pack(
            side=tk.RIGHT, padx=10
        )
        self.editor_body = ttk.Frame(self.editor_window, style="App.TFrame", padding=12)
        self.editor_body.pack(fill=tk.BOTH, expand=True)
        self.editor_pages = {}
        self.editor_content = {}
        for key in ("clock", "subjects", "teachers", "classrooms", "associations", "rules"):
            page = ttk.Frame(self.editor_body, style="App.TFrame")
            self.editor_pages[key] = page
            self.editor_content[key] = self._build_scroll_page(page)
        self.setup_content = self.editor_content["clock"]
        self.rules_content = self.editor_content["rules"]

    def _open_editor(self, section: str) -> None:
        if self.planning is None or self._editor_snapshot is not None:
            return
        self._editor_snapshot = deepcopy(self.planning)
        self._editor_renames = []
        self._editor_schedule_week = self.week_var.get()
        self._editor_section = section
        titles = {
            "clock": "Jornada escolar",
            "subjects": "Asignaturas",
            "teachers": "Profesores",
            "classrooms": "Aulas / grupos",
            "associations": "Asociaciones de profesores",
            "rules": "Restricciones",
        }
        self.editor_title.configure(text=titles[section])
        self.editor_window.title(titles[section] + " · Scholar Calendar")
        for page in self.editor_pages.values():
            page.pack_forget()
        self.editor_pages[section].pack(fill=tk.BOTH, expand=True)
        self._scroll_canvases[str(self.editor_pages[section])].yview_moveto(0)
        for variable in (
            self.subject_name_var,
            self.teacher_name_var,
            self.classroom_name_var,
            self.classroom_names_var,
        ):
            variable.set("")
        width = min(1040, max(980, self.winfo_screenwidth() - 80))
        height = min(760, self.winfo_screenheight() - 100)
        x = max(0, (self.winfo_screenwidth() - width) // 2)
        y = max(0, (self.winfo_screenheight() - height) // 2)
        self.editor_window.geometry(f"{width}x{height}+{x}+{y}")
        self.editor_window.minsize(980, 540)
        self.editor_window.deiconify()
        self.editor_window.update_idletasks()
        self.editor_window.grab_set()
        self.editor_window.focus_set()
        self._update_file_menu()

    def _apply_editor(self) -> None:
        if self._editor_snapshot is None:
            return
        try:
            planning = self._sync_planning()
        except (TypeError, ValueError, tk.TclError) as error:
            messagebox.showerror("Revisa la configuración", str(error), parent=self.editor_window)
            return
        self._update_schedule_metadata(planning, tuple(self._editor_renames))
        self._set_planning(planning)
        self._close_editor()
        self._refresh_schedule_notice()
        if self.schedule is not None:
            vertical_position = self.table.body.yview()[0]
            self._render()
            self.table.body.yview_moveto(vertical_position)
        self.status_var.set(
            "Debes generar un nuevo horario para aplicar los cambios."
            if self.schedule_needs_regeneration
            else "Cambios aplicados al horario existente. Guarda el archivo para conservarlos."
            if self.schedule is not None
            else "Configuración actualizada. Guarda el archivo para conservarla o genera el horario."
        )

    def _cancel_editor(self, _event=None) -> str:
        if self._editor_snapshot is not None:
            self._set_planning(self._editor_snapshot)
            self._close_editor()
        return "break"

    def _close_editor(self) -> None:
        self.week_var.set(self._editor_schedule_week)
        if self.schedule_planning is not None:
            self.week_combo["values"] = [
                str(week) for week in range(1, self.schedule_planning.weeks + 1)
            ]
        self._editor_snapshot = None
        self._editor_renames = []
        self.editor_window.grab_release()
        self.editor_window.withdraw()
        self._update_file_menu()
        self.focus_set()

    def _build_scroll_page(self, parent: ttk.Frame) -> ttk.Frame:
        canvas = tk.Canvas(parent, background=PAPER, highlightthickness=0, borderwidth=0)
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=canvas.yview)
        content = ttk.Frame(canvas, style="App.TFrame", padding=(0, 0, 12, 0))
        window = canvas.create_window((0, 0), window=content, anchor="nw")
        content.bind(
            "<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(window, width=event.width))
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._scroll_canvases[str(parent)] = canvas
        return content

    def _scroll_setup(self, event: tk.Event) -> None:
        if self._editor_snapshot is not None:
            canvas = self._scroll_canvases.get(str(self.editor_pages[self._editor_section]))
        else:
            canvas = self._scroll_canvases.get(self.notebook.select())
        if canvas is None or isinstance(
            event.widget, (ttk.Treeview, tk.Listbox, tk.Text, ttk.Combobox, ttk.Spinbox)
        ):
            return
        if getattr(event, "num", None) == 4:
            delta = -1
        elif getattr(event, "num", None) == 5:
            delta = 1
        else:
            raw = event.delta
            delta = -int(raw / 120) if abs(raw) >= 120 else (-1 if raw > 0 else 1 if raw < 0 else 0)
        if canvas.yview() != (0.0, 1.0):
            canvas.yview_scroll(delta, "units")

    def _build_setup_tab(self) -> None:
        parent = self.setup_content
        general = ttk.Frame(parent, style="Surface.TFrame", padding=20)
        general.pack(fill=tk.X, pady=(0, 12))
        ttk.Label(general, text="Datos del curso", style="Section.TLabel").grid(
            row=0, column=0, columnspan=6, sticky=tk.W, pady=(0, 10)
        )
        ttk.Label(general, text="Curso / año académico", style="Muted.TLabel").grid(
            row=1, column=0, sticky=tk.W
        )
        ttk.Entry(general, textvariable=self.course_var, width=28).grid(
            row=2, column=0, sticky="ew", padx=(0, 18)
        )
        ttk.Label(general, text="Semanas del ciclo", style="Muted.TLabel").grid(
            row=1, column=1, sticky=tk.W
        )
        ttk.Spinbox(
            general,
            from_=1,
            to=52,
            textvariable=self.weeks_var,
            width=8,
            command=self._refresh_saturday_controls,
        ).grid(row=2, column=1, sticky=tk.W, padx=(0, 18))
        general.columnconfigure(0, weight=1)
        general.columnconfigure(1, weight=0)

        schedule_card = ttk.Frame(parent, style="Surface.TFrame", padding=20)
        schedule_card.pack(fill=tk.X, pady=(0, 12))
        ttk.Label(schedule_card, text="Turnos y días lectivos", style="Section.TLabel").grid(
            row=0, column=0, columnspan=6, sticky=tk.W
        )
        ttk.Label(
            schedule_card,
            text="Define los turnos diarios y activa el sábado en las semanas que lo necesiten.",
            style="Muted.TLabel",
        ).grid(row=1, column=0, columnspan=6, sticky=tk.W, pady=(3, 10))
        day_names = ("Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado")
        ttk.Label(schedule_card, text="Turnos por día", style="Muted.TLabel").grid(
            row=2, column=0, columnspan=6, sticky=tk.W, pady=(0, 4)
        )
        for column, (day, name) in enumerate(zip(range(1, 7), day_names)):
            day_frame = ttk.Frame(schedule_card, style="Card.TFrame", padding=(5, 0))
            day_frame.grid(row=3, column=column, padx=4, sticky="nsew")
            schedule_card.columnconfigure(column, weight=1, uniform="days")
            ttk.Label(day_frame, text=name, style="Muted.TLabel").pack()
            ttk.Spinbox(
                day_frame,
                from_=0,
                to=20,
                textvariable=self.day_count_vars[day],
                width=7,
                justify=tk.CENTER,
            ).pack(pady=(4, 0))
        self.saturday_frame = ttk.Frame(schedule_card, style="Card.TFrame")
        self.saturday_frame.grid(row=4, column=0, columnspan=6, sticky=tk.W, pady=(10, 0))
        self._refresh_saturday_controls()

        clock_card = ttk.Frame(parent, style="Surface.TFrame", padding=20)
        clock_card.pack(fill=tk.X, pady=(0, 14))
        ttk.Label(clock_card, text="El reloj de tu centro", style="Section.TLabel").grid(
            row=0, column=0, columnspan=4, sticky=tk.W
        )
        ttk.Label(
            clock_card,
            text="Horas en formato HH:MM. Para quitar una pausa, deja vacíos su inicio y su final.",
            style="Muted.TLabel",
        ).grid(row=1, column=0, columnspan=4, sticky=tk.W, pady=(6, 18))
        clock_fields = (
            ("Inicio de las clases", self.class_start_var),
            ("Duración del turno · min", self.period_duration_var),
            ("Cambio de clase · min", self.transition_var),
            ("Comida después del turno", self.lunch_after_var),
            ("Inicio de la merienda", self.break_start_var),
            ("Fin de la merienda", self.break_end_var),
            ("Inicio de la comida", self.lunch_start_var),
            ("Fin de la comida", self.lunch_end_var),
        )
        for index, (label, variable) in enumerate(clock_fields):
            row, column = 2 + (index // 4) * 2, index % 4
            ttk.Label(clock_card, text=label, style="Muted.TLabel").grid(
                row=row, column=column, sticky=tk.W, padx=(0, 18), pady=(0, 6)
            )
            widget = (
                ttk.Spinbox(clock_card, from_=0, to=240, textvariable=variable, width=10)
                if isinstance(variable, tk.IntVar)
                else ttk.Entry(clock_card, textvariable=variable, width=10)
            )
            widget.grid(row=row + 1, column=column, sticky="ew", padx=(0, 18), pady=(0, 16))
            clock_card.columnconfigure(column, weight=1, uniform="clock")
        preview = ttk.Frame(parent, style="Surface.TFrame", padding=20)
        preview.pack(fill=tk.X, pady=(0, 14))
        ttk.Label(preview, text="Vista previa de la jornada", style="Section.TLabel").pack(
            anchor=tk.W
        )
        ttk.Label(
            preview, textvariable=self.clock_preview_var, style="Muted.TLabel", wraplength=850
        ).pack(anchor=tk.W, pady=(6, 14))
        self.clock_tree = ttk.Treeview(
            preview, columns=("activity", "hours", "duration"), show="headings", height=7
        )
        for key, title, width in (
            ("activity", "Actividad", 230),
            ("hours", "Horario", 230),
            ("duration", "Duración", 130),
        ):
            self.clock_tree.heading(key, text=title)
            self.clock_tree.column(key, width=width, anchor=tk.W)
        preview_scroll = ttk.Scrollbar(preview, orient=tk.VERTICAL, command=self.clock_tree.yview)
        self.clock_tree.configure(yscrollcommand=preview_scroll.set)
        self.clock_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        preview_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.clock_tree.tag_configure("pause", background=PALE_TEAL, foreground=TEAL)
        self.clock_tree.tag_configure("gap", background="#fff4dc", foreground="#805d19")
        self._build_resource_cards()
        parent = self.rules_content

        restrictions = ttk.Frame(parent, style="Surface.TFrame", padding=20)
        restrictions.pack(fill=tk.X, pady=(0, 12))
        ttk.Label(
            restrictions, text="Restricciones opcionales por día", style="Section.TLabel"
        ).grid(row=0, column=0, columnspan=2, sticky=tk.W)
        ttk.Label(
            restrictions,
            text="Selecciona una persona o asignatura y los días que no podrá utilizar.",
            style="Muted.TLabel",
        ).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(3, 8))
        ttk.Label(restrictions, text="Profesores no disponibles", style="Muted.TLabel").grid(
            row=2, column=0, sticky=tk.W
        )
        ttk.Label(restrictions, text="Asignaturas no disponibles", style="Muted.TLabel").grid(
            row=2, column=1, sticky=tk.W
        )
        teacher_day_table = ttk.Frame(restrictions, style="Card.TFrame")
        teacher_day_table.grid(row=3, column=0, sticky="nsew", padx=(0, 12))
        self.teacher_day_tree = ttk.Treeview(
            teacher_day_table, columns=("name", "days"), show="headings", height=3
        )
        self.teacher_day_tree.heading("name", text="Profesor")
        self.teacher_day_tree.heading("days", text="Días")
        self.teacher_day_tree.column("name", width=130)
        self.teacher_day_tree.column("days", width=100)
        self.teacher_day_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        teacher_day_scroll = ttk.Scrollbar(
            teacher_day_table, orient=tk.VERTICAL, command=self.teacher_day_tree.yview
        )
        teacher_day_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.teacher_day_tree.configure(yscrollcommand=teacher_day_scroll.set)
        subject_day_table = ttk.Frame(restrictions, style="Card.TFrame")
        subject_day_table.grid(row=3, column=1, sticky="nsew")
        self.subject_day_tree = ttk.Treeview(
            subject_day_table, columns=("name", "days"), show="headings", height=3
        )
        self.subject_day_tree.heading("name", text="Asignatura")
        self.subject_day_tree.heading("days", text="Días")
        self.subject_day_tree.column("name", width=130)
        self.subject_day_tree.column("days", width=100)
        self.subject_day_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        subject_day_scroll = ttk.Scrollbar(
            subject_day_table, orient=tk.VERTICAL, command=self.subject_day_tree.yview
        )
        subject_day_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.subject_day_tree.configure(yscrollcommand=subject_day_scroll.set)
        day_form = ttk.Frame(restrictions, style="Card.TFrame")
        day_form.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(16, 0))
        day_form.columnconfigure(1, weight=1)
        ttk.Label(day_form, text="Profesor", style="Muted.TLabel").grid(
            row=0, column=0, sticky=tk.W, padx=(0, 14)
        )
        self.unavailable_teacher_combo = ttk.Combobox(
            day_form, textvariable=self.unavailable_teacher_var, state="readonly", width=22
        )
        self.unavailable_teacher_combo.grid(row=0, column=1, sticky="ew", padx=(0, 14), pady=4)
        ttk.Button(
            day_form, text="Bloquear días del profesor", command=self._add_teacher_unavailable
        ).grid(row=0, column=2, sticky="ew")
        ttk.Label(day_form, text="Asignatura", style="Muted.TLabel").grid(
            row=1, column=0, sticky=tk.W, padx=(0, 14)
        )
        self.unavailable_subject_combo = ttk.Combobox(
            day_form, textvariable=self.unavailable_subject_var, state="readonly", width=22
        )
        self.unavailable_subject_combo.grid(row=1, column=1, sticky="ew", padx=(0, 14), pady=4)
        ttk.Button(
            day_form, text="Bloquear días de la asignatura", command=self._add_subject_unavailable
        ).grid(row=1, column=2, sticky="ew")
        days_form = ttk.Frame(day_form, style="Card.TFrame")
        days_form.grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=(10, 6))
        self.unavailable_day_vars = {day: tk.BooleanVar() for day in DAY_NAMES}
        for column, (day, name) in enumerate(DAY_NAMES.items()):
            ttk.Checkbutton(days_form, text=name, variable=self.unavailable_day_vars[day]).grid(
                row=0, column=column, padx=(0, 12)
            )
        ttk.Label(
            day_form,
            text="Marca los días y aplica el bloqueo a un profesor o una asignatura.",
            style="Muted.TLabel",
        ).grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(4, 0))
        ttk.Button(
            day_form,
            text="Eliminar selección",
            style="Danger.TButton",
            command=self._remove_unavailable,
        ).grid(row=3, column=2, sticky=tk.E)
        self._build_subject_rule_editors(restrictions)
        restrictions.columnconfigure(0, weight=1)
        restrictions.columnconfigure(1, weight=1)

    def _build_resource_cards(self) -> None:
        for key, builder in (
            ("subjects", self._build_subject_card),
            ("teachers", self._build_teacher_card),
            ("classrooms", self._build_classroom_card),
            ("associations", self._build_association_card),
            ("associations", self._build_classroom_association_card),
        ):
            card = ttk.Frame(self.editor_content[key], style="Surface.TFrame", padding=20)
            card.pack(fill=tk.X, pady=(0, 14))
            builder(card)

    def _build_subject_rule_editors(self, parent: ttk.Frame) -> None:
        rules = ttk.Frame(parent, style="Card.TFrame")
        rules.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        ttk.Label(rules, text="Restricciones entre asignaturas", style="Section.TLabel").grid(
            row=0, column=0, columnspan=2, sticky=tk.W
        )
        ttk.Label(
            rules,
            text="Estas reglas son opcionales: si no añades una pareja, no se aplica ninguna restricción.",
            style="Muted.TLabel",
        ).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(3, 8))
        consecutive_frame = ttk.Frame(rules, style="Card.TFrame")
        consecutive_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(0, 18))
        parallel_frame = ttk.Frame(rules, style="Card.TFrame")
        parallel_frame.grid(row=3, column=0, columnspan=2, sticky="nsew")
        self.consecutive_tree = self._build_rule_tree(consecutive_frame, "No consecutivas")
        self.parallel_tree = self._build_rule_tree(parallel_frame, "No paralelas")
        consecutive_form = ttk.Frame(consecutive_frame, style="Card.TFrame")
        consecutive_form.pack(fill=tk.X, pady=(6, 0))
        self.consecutive_first_combo = ttk.Combobox(
            consecutive_form, textvariable=self.consecutive_first_var, state="readonly", width=16
        )
        self.consecutive_first_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.consecutive_second_combo = ttk.Combobox(
            consecutive_form, textvariable=self.consecutive_second_var, state="readonly", width=16
        )
        self.consecutive_second_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(consecutive_form, text="Añadir", command=self._add_consecutive_rule).pack(
            side=tk.LEFT
        )
        ttk.Button(
            consecutive_form,
            text="Eliminar",
            style="Danger.TButton",
            command=lambda: self._remove_rule(self.consecutive_tree, "consecutive"),
        ).pack(side=tk.LEFT, padx=(5, 0))
        parallel_form = ttk.Frame(parallel_frame, style="Card.TFrame")
        parallel_form.pack(fill=tk.X, pady=(6, 0))
        self.parallel_first_combo = ttk.Combobox(
            parallel_form, textvariable=self.parallel_first_var, state="readonly", width=16
        )
        self.parallel_first_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.parallel_second_combo = ttk.Combobox(
            parallel_form, textvariable=self.parallel_second_var, state="readonly", width=16
        )
        self.parallel_second_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(parallel_form, text="Añadir", command=self._add_parallel_rule).pack(side=tk.LEFT)
        ttk.Button(
            parallel_form,
            text="Eliminar",
            style="Danger.TButton",
            command=lambda: self._remove_rule(self.parallel_tree, "parallel"),
        ).pack(side=tk.LEFT, padx=(5, 0))
        rules.columnconfigure(0, weight=1)
        rules.columnconfigure(1, weight=1)

    @staticmethod
    def _build_rule_tree(parent: ttk.Frame, title: str) -> ttk.Treeview:
        ttk.Label(parent, text=title, style="Muted.TLabel").pack(anchor=tk.W)
        table = ttk.Frame(parent, style="Card.TFrame")
        table.pack(fill=tk.BOTH, expand=True)
        tree = ttk.Treeview(table, columns=("first", "second"), show="headings", height=3)
        tree.heading("first", text="Asignatura 1")
        tree.heading("second", text="Asignatura 2")
        tree.column("first", width=150)
        tree.column("second", width=150)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll = ttk.Scrollbar(table, orient=tk.VERTICAL, command=tree.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        tree.configure(yscrollcommand=scroll.set)
        return tree

    def _refresh_subject_rule_editors(self) -> None:
        subjects = [name for name, _, _ in self.subjects]
        for combo in (
            self.consecutive_first_combo,
            self.consecutive_second_combo,
            self.parallel_first_combo,
            self.parallel_second_combo,
        ):
            combo["values"] = subjects
        for tree in (self.consecutive_tree, self.parallel_tree):
            tree.delete(*tree.get_children())
        if self.planning is None:
            return
        for first, second in sorted(
            self.planning.forbidden_consecutive, key=lambda pair: sorted(pair)
        ):
            values = sorted((first, second))
            self.consecutive_tree.insert("", tk.END, values=values)
        for first, second in sorted(
            self.planning.forbidden_parallel, key=lambda pair: sorted(pair)
        ):
            values = sorted((first, second))
            self.parallel_tree.insert("", tk.END, values=values)

    def _add_rule(self, first: str, second: str, kind: str) -> None:
        if not first or not second or first == second or self.planning is None:
            return
        pair = frozenset((first, second))
        rules = set(
            self.planning.forbidden_consecutive
            if kind == "consecutive"
            else self.planning.forbidden_parallel
        )
        rules.add(pair)
        if kind == "consecutive":
            self.planning = replace(self.planning, forbidden_consecutive=frozenset(rules))
        else:
            self.planning = replace(self.planning, forbidden_parallel=frozenset(rules))
        self._refresh_subject_rule_editors()

    def _add_consecutive_rule(self) -> None:
        self._add_rule(
            self.consecutive_first_var.get(), self.consecutive_second_var.get(), "consecutive"
        )

    def _add_parallel_rule(self) -> None:
        self._add_rule(self.parallel_first_var.get(), self.parallel_second_var.get(), "parallel")

    def _remove_rule(self, tree: ttk.Treeview, kind: str) -> None:
        selected = tree.selection()
        if not selected or self.planning is None:
            return
        first, second = tree.item(selected[0], "values")
        pair = frozenset((first, second))
        key = "forbidden_consecutive" if kind == "consecutive" else "forbidden_parallel"
        rules = frozenset(rule for rule in getattr(self.planning, key) if rule != pair)
        self.planning = replace(self.planning, **{key: rules})
        self._refresh_subject_rule_editors()

    def _refresh_saturday_controls(self) -> None:
        try:
            weeks = int(self.weeks_var.get())
        except (ValueError, tk.TclError):
            return
        if not 1 <= weeks <= 52:
            return
        for child in self.saturday_frame.winfo_children():
            child.destroy()
        self.saturday_vars = {
            week: self.saturday_vars[week]
            if week in self.saturday_vars
            else tk.BooleanVar(value=False)
            for week in range(1, weeks + 1)
        }
        ttk.Label(self.saturday_frame, text="Sábado activo en:", style="Muted.TLabel").grid(
            row=0, column=0, columnspan=6, sticky=tk.W
        )
        for index, (week, variable) in enumerate(self.saturday_vars.items()):
            ttk.Checkbutton(self.saturday_frame, text=f"Semana {week}", variable=variable).grid(
                row=1 + index // 6, column=index % 6, sticky=tk.W, padx=(0, 10)
            )

    def _build_subject_card(self, card: ttk.Frame) -> None:
        ttk.Label(card, text="Asignaturas", style="Section.TLabel").pack(anchor=tk.W)
        ttk.Label(
            card,
            text="Sesiones por semana en cada aula. Doble: agrupa en parejas de turnos.",
            style="Muted.TLabel",
        ).pack(anchor=tk.W, pady=(3, 10))
        subject_table = ttk.Frame(card, style="Card.TFrame")
        subject_table.pack(fill=tk.BOTH, expand=True)
        self.subject_tree = ttk.Treeview(
            subject_table, columns=("name", "lessons", "double"), show="headings", height=5
        )
        self.subject_tree.heading("name", text="Asignatura")
        self.subject_tree.heading("lessons", text="Por semana")
        self.subject_tree.heading("double", text="Doble")
        self.subject_tree.column("name", width=160)
        self.subject_tree.column("lessons", width=75, anchor=tk.CENTER)
        self.subject_tree.column("double", width=60, anchor=tk.CENTER)
        self.subject_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        subject_scroll = ttk.Scrollbar(
            subject_table, orient=tk.VERTICAL, command=self.subject_tree.yview
        )
        subject_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.subject_tree.configure(yscrollcommand=subject_scroll.set)
        self.subject_tree.bind("<<TreeviewSelect>>", self._select_subject)
        form = ttk.Frame(card, style="Card.TFrame")
        form.pack(fill=tk.X, pady=(10, 0))
        ttk.Entry(form, textvariable=self.subject_name_var).pack(
            side=tk.LEFT, fill=tk.X, expand=True
        )
        ttk.Spinbox(form, from_=1, to=99, textvariable=self.subject_lessons_var, width=7).pack(
            side=tk.LEFT, padx=6
        )
        ttk.Checkbutton(form, text="Doble", variable=self.subject_double_var).pack(
            side=tk.LEFT, padx=(0, 6)
        )
        ttk.Button(form, text="Añadir", command=self._add_subject).pack(side=tk.LEFT)
        ttk.Button(form, text="Editar", command=self._edit_subject).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(
            card, text="Eliminar seleccionada", style="Danger.TButton", command=self._remove_subject
        ).pack(anchor=tk.E, pady=(8, 0))

    def _build_teacher_card(self, card: ttk.Frame) -> None:
        ttk.Label(card, text="Profesores", style="Section.TLabel").pack(anchor=tk.W)
        ttk.Label(card, text="Personas disponibles para el horario.", style="Muted.TLabel").pack(
            anchor=tk.W, pady=(3, 10)
        )
        teacher_table = ttk.Frame(card, style="Card.TFrame")
        teacher_table.pack(fill=tk.BOTH, expand=True)
        self.teacher_list = tk.Listbox(
            teacher_table,
            height=7,
            relief=tk.FLAT,
            borderwidth=0,
            bg="white",
            fg=INK,
            selectbackground=PALE_TEAL,
            selectforeground=INK,
            font=("Helvetica", 11),
        )
        self.teacher_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        teacher_scroll = ttk.Scrollbar(
            teacher_table, orient=tk.VERTICAL, command=self.teacher_list.yview
        )
        teacher_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.teacher_list.configure(yscrollcommand=teacher_scroll.set)
        self.teacher_list.bind("<<ListboxSelect>>", self._select_teacher)
        form = ttk.Frame(card, style="Card.TFrame")
        form.pack(fill=tk.X, pady=(10, 0))
        ttk.Entry(form, textvariable=self.teacher_name_var).pack(fill=tk.X, pady=(0, 8))
        ttk.Button(form, text="Añadir", command=self._add_teacher).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(form, text="Editar", command=self._edit_teacher).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(
            card, text="Eliminar seleccionado", style="Danger.TButton", command=self._remove_teacher
        ).pack(anchor=tk.E, pady=(8, 0))

    def _build_classroom_card(self, card: ttk.Frame) -> None:
        ttk.Label(card, text="Aulas / grupos", style="Section.TLabel").pack(anchor=tk.W)
        ttk.Label(card, text="Define y edita los grupos docentes.", style="Muted.TLabel").pack(
            anchor=tk.W, pady=(3, 10)
        )
        classroom_table = ttk.Frame(card, style="Card.TFrame")
        classroom_table.pack(fill=tk.BOTH, expand=True)
        self.classroom_list = tk.Listbox(
            classroom_table,
            height=7,
            relief=tk.FLAT,
            borderwidth=0,
            bg="white",
            fg=INK,
            selectbackground=PALE_TEAL,
            selectforeground=INK,
            font=("Helvetica", 11),
        )
        self.classroom_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        classroom_scroll = ttk.Scrollbar(
            classroom_table, orient=tk.VERTICAL, command=self.classroom_list.yview
        )
        classroom_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.classroom_list.configure(yscrollcommand=classroom_scroll.set)
        self.classroom_list.bind("<<ListboxSelect>>", self._select_classroom)
        form = ttk.Frame(card, style="Card.TFrame")
        form.pack(fill=tk.X, pady=(10, 0))
        ttk.Entry(form, textvariable=self.classroom_name_var).pack(fill=tk.X, pady=(0, 8))
        ttk.Button(form, text="Añadir", command=self._add_classroom).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(form, text="Editar", command=self._edit_classroom).pack(
            side=tk.LEFT, padx=(6, 0)
        )
        ttk.Button(
            card,
            text="Eliminar seleccionado",
            style="Danger.TButton",
            command=self._remove_classroom,
        ).pack(anchor=tk.E, pady=(8, 0))

    def _build_association_card(self, card: ttk.Frame) -> None:
        ttk.Label(card, text="Asociaciones", style="Section.TLabel").pack(anchor=tk.W)
        ttk.Label(card, text="Relaciona profesor y asignatura.", style="Muted.TLabel").pack(
            anchor=tk.W, pady=(3, 10)
        )
        association_table = ttk.Frame(card, style="Card.TFrame")
        association_table.pack(fill=tk.BOTH, expand=True)
        self.association_tree = ttk.Treeview(
            association_table, columns=("teacher", "subject"), show="headings", height=5
        )
        self.association_tree.heading("teacher", text="Profesor")
        self.association_tree.heading("subject", text="Asignatura")
        self.association_tree.column("teacher", width=125)
        self.association_tree.column("subject", width=125)
        self.association_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        association_scroll = ttk.Scrollbar(
            association_table, orient=tk.VERTICAL, command=self.association_tree.yview
        )
        association_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.association_tree.configure(yscrollcommand=association_scroll.set)
        self.association_tree.bind("<<TreeviewSelect>>", self._select_association)
        form = ttk.Frame(card, style="Card.TFrame")
        form.pack(fill=tk.X, pady=(10, 0))
        self.association_teacher_combo = ttk.Combobox(
            form, textvariable=self.association_teacher_var, state="readonly", width=15
        )
        self.association_teacher_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.association_subject_combo = ttk.Combobox(
            form, textvariable=self.association_subject_var, state="readonly", width=15
        )
        self.association_subject_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)
        ttk.Button(form, text="Vincular", command=self._add_association).pack(side=tk.LEFT)
        ttk.Button(form, text="Editar", command=self._edit_association).pack(
            side=tk.LEFT, padx=(6, 0)
        )
        ttk.Button(
            card,
            text="Eliminar seleccionada",
            style="Danger.TButton",
            command=self._remove_association,
        ).pack(anchor=tk.E, pady=(8, 0))

    def _build_classroom_association_card(self, card: ttk.Frame) -> None:
        ttk.Label(card, text="Profesor ↔ aula", style="Section.TLabel").pack(anchor=tk.W)
        ttk.Label(
            card, text="Define qué aulas puede utilizar cada profesor.", style="Muted.TLabel"
        ).pack(anchor=tk.W, pady=(3, 10))
        table = ttk.Frame(card, style="Card.TFrame")
        table.pack(fill=tk.BOTH, expand=True)
        self.classroom_association_tree = ttk.Treeview(
            table, columns=("teacher", "classrooms"), show="headings", height=5
        )
        self.classroom_association_tree.heading("teacher", text="Profesor")
        self.classroom_association_tree.heading("classrooms", text="Aulas")
        self.classroom_association_tree.column("teacher", width=130)
        self.classroom_association_tree.column("classrooms", width=190)
        self.classroom_association_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll = ttk.Scrollbar(
            table, orient=tk.VERTICAL, command=self.classroom_association_tree.yview
        )
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.classroom_association_tree.configure(yscrollcommand=scroll.set)
        self.classroom_association_tree.bind(
            "<<TreeviewSelect>>", self._select_classroom_association
        )
        form = ttk.Frame(card, style="Card.TFrame")
        form.pack(fill=tk.X, pady=(10, 0))
        self.classroom_teacher_combo = ttk.Combobox(
            form, textvariable=self.classroom_teacher_var, state="readonly", width=15
        )
        self.classroom_teacher_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Entry(form, textvariable=self.classroom_names_var).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=6
        )
        ttk.Button(form, text="Vincular", command=self._add_classroom_association).pack(
            side=tk.LEFT
        )
        ttk.Button(form, text="Editar", command=self._edit_classroom_association).pack(
            side=tk.LEFT, padx=(6, 0)
        )
        ttk.Button(
            card,
            text="Eliminar seleccionada",
            style="Danger.TButton",
            command=self._remove_classroom_association,
        ).pack(anchor=tk.E, pady=(8, 0))

    def _build_schedule_tab(self) -> None:
        controls = ttk.Frame(self.schedule_tab, style="Surface.TFrame", padding=(20, 16))
        controls.pack(fill=tk.X, pady=(0, 14))
        heading = ttk.Frame(controls, style="Card.TFrame")
        heading.pack(fill=tk.X)
        ttk.Label(heading, text="Tu horario semanal", style="Section.TLabel").pack(side=tk.LEFT)
        ttk.Label(controls, textvariable=self.schedule_summary_var, style="Muted.TLabel").pack(
            anchor=tk.W, pady=(6, 14)
        )
        navigation = ttk.Frame(controls, style="Card.TFrame")
        navigation.pack(fill=tk.X)
        ttk.Label(navigation, text="Semana", style="Muted.TLabel").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(navigation, text="‹", width=3, command=lambda: self._change_week(-1)).pack(
            side=tk.LEFT
        )
        self.week_combo = ttk.Combobox(
            navigation, textvariable=self.week_var, state="readonly", width=5
        )
        self.week_combo.pack(side=tk.LEFT, padx=6)
        self.week_combo.bind("<<ComboboxSelected>>", lambda _event: self._render())
        ttk.Button(navigation, text="›", width=3, command=lambda: self._change_week(1)).pack(
            side=tk.LEFT
        )
        ttk.Label(
            navigation,
            text="Asignatura y profesor en cada celda · Desplázate para ver todas las aulas",
            style="Muted.TLabel",
        ).pack(side=tk.LEFT, padx=18)
        highlight = ttk.Frame(controls, style="Card.TFrame")
        highlight.pack(fill=tk.X, pady=(12, 0))
        self.highlight_label = ttk.Label(
            highlight, textvariable=self.subject_highlight_var, style="Muted.TLabel", wraplength=680
        )
        self.highlight_label.pack(side=tk.LEFT)
        ttk.Button(
            highlight, text="Quitar resaltado", command=lambda: self._select_schedule_subject(None)
        ).pack(side=tk.RIGHT)
        self.restriction_note = RestrictionNote(highlight)
        self.table = ScheduleGrid(self.schedule_tab, self._select_schedule_subject)
        self.table.pack(fill=tk.BOTH, expand=True)
        self._clear_table()

    def _change_week(self, direction: int) -> None:
        if self.schedule_planning is not None:
            self.week_var.set(
                str(max(1, min(self.schedule_planning.weeks, int(self.week_var.get()) + direction)))
            )
            self._render()

    def _build_file_menu(self, toolbar: ttk.Frame) -> None:
        menubar = tk.Menu(self)
        self.file_menu = tk.Menu(menubar, tearoff=False)
        self.file_menu.add_command(label="Guardar", command=self._save, accelerator="⌘S")
        self.file_menu.add_command(label="Cargar", command=self._open, accelerator="⌘O")
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Limpiar", command=self._clear_project)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Reglas de generación", command=self._show_rules)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Salir", command=self._exit, accelerator="⌘Q")
        menubar.add_cascade(label="Menú", menu=self.file_menu)
        self.configure(menu=menubar)
        self._menu_icon = tk.PhotoImage(master=self, width=20, height=20)
        for y in (4, 9, 14):
            self._menu_icon.put(INK, to=(2, y, 18, y + 2))
        self.menu_button = ttk.Menubutton(
            toolbar,
            text="Menú",
            image=self._menu_icon,
            style="Icon.TMenubutton",
            menu=self.file_menu,
            takefocus=True,
        )
        self.menu_button.pack(side=tk.LEFT, padx=(0, 18))
        self.protocol("WM_DELETE_WINDOW", self._exit)
        for key, command in (("s", self._save), ("o", self._open), ("q", self._exit)):
            self.bind(f"<Command-{key}>", lambda _event, command=command: command())

    def _update_file_menu(self) -> None:
        editing = self._editor_snapshot is not None
        for label in ("Guardar", "Cargar", "Limpiar", "Reglas de generación", "Salir"):
            self.file_menu.entryconfigure(label, state="disabled" if editing else "normal")
        self.export_button.configure(
            state="normal" if self.schedule is not None and not editing else "disabled",
        )

    def _show_rules(self) -> None:
        if self._editor_snapshot is not None:
            return
        if self.rules_window is None or not self.rules_window.winfo_exists():
            self.rules_window = RulesHelp(self)
        self.rules_window.deiconify()
        self.rules_window.lift()
        self.rules_window.focus_set()

    def _refresh_schedule_notice(self) -> None:
        self.schedule_needs_regeneration = (
            self.schedule is not None
            and self.schedule_planning is not None
            and self.planning is not None
            and requires_regeneration(self.planning, self.schedule_planning)
        )
        if self.schedule_needs_regeneration:
            self.generate_button.configure(text="Generar de nuevo")
            self.schedule_notice.pack(after=self._header, fill=tk.X, padx=24, pady=(10, 0))
        else:
            self.generate_button.configure(text="Generar horario")
            self.schedule_notice.pack_forget()

    def _update_schedule_metadata(
        self, planning: PlanningInput, renames: tuple[ResourceRename, ...] = ()
    ) -> None:
        if self.schedule is None or self.schedule_planning is None:
            return
        self.schedule_planning, updated = update_schedule_metadata(
            planning, self.schedule_planning, self.schedule, renames
        )
        if not requires_regeneration(planning, self.schedule_planning):
            for rename in renames:
                if rename.kind == "subject" and self.selected_subject == rename.before:
                    self.selected_subject = rename.after
        self.schedule = updated

    def _open(self) -> None:
        if self._editor_snapshot is not None:
            return
        path = filedialog.askopenfilename(
            title="Cargar",
            filetypes=(("Scholar Calendar", "*.json"), ("Todos los archivos", "*.*")),
            parent=self,
        )
        if path:
            self._load(Path(path))

    def _load(self, path: Path) -> None:
        try:
            project = load_project(path)
        except (OSError, ValueError) as error:
            messagebox.showerror("No se pudo cargar", str(error), parent=self)
            return
        self._set_planning(project.planning)
        self.schedule = project.schedule
        self.schedule_planning = project.schedule_planning
        self._update_schedule_metadata(project.planning)
        self.document_path = path
        self.selected_subject = None
        self._clear_table()
        if self.schedule is not None:
            self._render()
            self.notebook.select(self.schedule_tab)
        else:
            self.notebook.select(self.setup_tab)
        self._update_file_menu()
        self._refresh_schedule_notice()
        self.status_var.set(
            f"Cargado: {path.name}"
            + (
                " · Incluye horario generado"
                if self.schedule is not None
                else " · Configuración sin horario"
            )
        )

    def _clear_project(self) -> None:
        if self._editor_snapshot is not None:
            return
        self.schedule = None
        self.schedule_planning = None
        self.document_path = None
        self._reset_editor_inputs()
        self._set_planning(self._blank_planning())
        self._clear_table()
        self.table.body.xview_moveto(0)
        self._scroll_canvases[str(self.setup_tab)].yview_moveto(0)
        self.notebook.select(self.setup_tab)
        self._update_file_menu()
        self._refresh_schedule_notice()
        self.status_var.set(
            "Centro limpio. Configuración por defecto con inicio a las "
            f"{DEFAULT_CLASS_START:%H:%M}."
        )

    def _reset_editor_inputs(self) -> None:
        for variable in (
            self.subject_name_var,
            self.teacher_name_var,
            self.classroom_name_var,
            self.classroom_teacher_var,
            self.classroom_names_var,
            self.unavailable_teacher_var,
            self.unavailable_subject_var,
            self.consecutive_first_var,
            self.consecutive_second_var,
            self.parallel_first_var,
            self.parallel_second_var,
            self.association_subject_var,
            self.association_teacher_var,
        ):
            variable.set("")
        self.subject_lessons_var.set(1)
        self.subject_double_var.set(False)
        for variable in self.unavailable_day_vars.values():
            variable.set(False)

    def _exit(self) -> None:
        if self._editor_snapshot is None:
            self.destroy()

    def _set_planning(self, planning: PlanningInput) -> None:
        """Populate editors and overview without replacing the generated schedule."""
        self.planning = planning
        self.course_var.set(planning.course_name)
        self.weeks_var.set(planning.weeks)
        self.classroom_list.delete(0, tk.END)
        for classroom in planning.classrooms:
            self.classroom_list.insert(tk.END, classroom.name)
        self.subjects = [
            (subject.name, subject.lessons_per_cycle, subject.double_period)
            for subject in planning.subjects
        ]
        self.teachers = [teacher.name for teacher in planning.teachers]
        self.teacher_subjects = {
            name: set(subjects) for name, subjects in planning.teacher_subjects.items()
        }
        self.teacher_classrooms = {
            name: set(classrooms) for name, classrooms in planning.teacher_classrooms.items()
        }
        self.class_start_var.set(planning.class_start.strftime("%H:%M"))
        self.period_duration_var.set(planning.period_duration_minutes)
        self.transition_var.set(planning.transition_minutes)
        self.break_start_var.set(
            planning.break_start.strftime("%H:%M") if planning.break_start else ""
        )
        self.break_end_var.set(planning.break_end.strftime("%H:%M") if planning.break_end else "")
        self.lunch_start_var.set(
            planning.lunch_start.strftime("%H:%M") if planning.lunch_start else ""
        )
        self.lunch_end_var.set(planning.lunch_end.strftime("%H:%M") if planning.lunch_end else "")
        self.lunch_after_var.set(planning.lunch_after_period)
        counts = planning.day_period_counts or {
            day: len({(slot.start, slot.end) for slot in planning.slots if slot.day == day})
            for day in range(1, 7)
        }
        for day in range(1, 7):
            self.day_count_vars[day].set(counts.get(day, 0))
        self.saturday_vars = {
            week: tk.BooleanVar(value=week in planning.saturday_weeks)
            for week in range(1, planning.weeks + 1)
        }
        self._refresh_editors()
        self._refresh_saturday_controls()
        self.week_combo["values"] = [str(week) for week in range(1, planning.weeks + 1)]
        self.week_var.set("1")
        self._loaded_clock_signature = self._clock_signature()
        self._loaded_slot_signature = self._slot_signature()
        self._update_clock_preview()
        self.overview.show(planning)

    def _clock_variables(self) -> tuple[tk.Variable, ...]:
        return (
            self.class_start_var,
            self.period_duration_var,
            self.transition_var,
            self.break_start_var,
            self.break_end_var,
            self.lunch_start_var,
            self.lunch_end_var,
            self.lunch_after_var,
        )

    def _clock_signature(self) -> tuple[str | int, ...]:
        return tuple(variable.get() for variable in self._clock_variables())

    def _slot_signature(self) -> tuple:
        return (
            self.weeks_var.get(),
            tuple((day, variable.get()) for day, variable in self.day_count_vars.items()),
            tuple(week for week, variable in self.saturday_vars.items() if variable.get()),
        )

    def _daily_periods(self) -> tuple[tuple[time, time], ...]:
        start = parse_optional_time(self.class_start_var.get())
        if start is None:
            raise ValueError("Indica la hora de inicio de las clases (HH:MM).")
        counts = [int(variable.get()) for variable in self.day_count_vars.values()]
        if any(count < 0 for count in counts):
            raise ValueError("Los turnos por día no pueden ser negativos.")
        count = max(counts, default=0)
        periods = build_daily_periods(
            period_count=count,
            start=start,
            duration_minutes=int(self.period_duration_var.get()),
            transition_minutes=int(self.transition_var.get()),
            break_start=parse_optional_time(self.break_start_var.get()),
            break_end=parse_optional_time(self.break_end_var.get()),
            lunch_start=parse_optional_time(self.lunch_start_var.get()),
            lunch_end=parse_optional_time(self.lunch_end_var.get()),
            lunch_after_period=int(self.lunch_after_var.get()),
        )
        # Keep imported custom intervals until the user changes the clock.
        if self.planning is not None and self._loaded_clock_signature == self._clock_signature():
            existing = sorted({(slot.start, slot.end) for slot in self.planning.slots})
            if len(existing) >= count:
                return tuple(existing[:count])
        return periods

    def _queue_clock_preview(self, *_args) -> None:
        if self._clock_preview_job is not None:
            self.after_cancel(self._clock_preview_job)
        self._clock_preview_job = self.after(250, self._update_clock_preview)

    def _update_clock_preview(self) -> None:
        if self._clock_preview_job is not None:
            self.after_cancel(self._clock_preview_job)
        self._clock_preview_job = None
        self.clock_tree.delete(*self.clock_tree.get_children())
        try:
            periods = self._daily_periods()
            preview = PlanningInput(
                weeks=1,
                subjects=(),
                teachers=(),
                classrooms=(),
                teacher_subjects={},
                teacher_classrooms={},
                slots=build_slots(weeks=1, days=1, daily_periods=periods),
                class_start=time.fromisoformat(self.class_start_var.get().strip()),
                transition_minutes=int(self.transition_var.get()),
                break_start=parse_optional_time(self.break_start_var.get()),
                break_end=parse_optional_time(self.break_end_var.get()),
                lunch_start=parse_optional_time(self.lunch_start_var.get()),
                lunch_end=parse_optional_time(self.lunch_end_var.get()),
            )
            free_minutes = 0
            for row in daily_rows(preview, 1, 1):
                duration = minutes_since_midnight(row.end) - minutes_since_midnight(row.start)
                if row.label == "Tiempo libre":
                    free_minutes += duration
                tag = (
                    "gap"
                    if row.label == "Tiempo libre"
                    else "pause"
                    if row.period is None
                    else "lesson"
                )
                self.clock_tree.insert(
                    "", tk.END, values=(row.label, row.hours, f"{duration} min"), tags=(tag,)
                )
            summary = f"Día de mayor duración · {len(periods)} turnos"
            if periods:
                summary += f" · {periods[0][0]:%H:%M} – {periods[-1][1]:%H:%M}."
            if free_minutes:
                summary += f" Hay {free_minutes} min de tiempo libre entre turnos o antes del inicio efectivo. Revisa el inicio, la duración y las pausas para ajustar la jornada."
            self.clock_preview_var.set(summary)
        except (TypeError, ValueError, tk.TclError) as error:
            self.clock_preview_var.set(f"Revisa el reloj: {error}")

    def _sync_planning(self) -> PlanningInput:
        """Validate editor values, preserving imported slots until the clock or cycle changes."""
        if self.planning is None:
            raise ValueError("No hay una configuración cargada.")
        classrooms = tuple(Classroom(name) for name in self.classroom_list.get(0, tk.END))
        weeks = int(self.weeks_var.get())
        if not 1 <= weeks <= 52:
            raise ValueError("Indica entre 1 y 52 semanas para el ciclo.")
        days = 6
        day_period_counts = {
            day: max(0, int(variable.get())) for day, variable in self.day_count_vars.items()
        }
        saturday_weeks = frozenset(
            week for week, variable in self.saturday_vars.items() if variable.get()
        )
        teacher_unavailable_days = self.planning.teacher_unavailable_days or {}
        subject_unavailable_days = self.planning.subject_unavailable_days or {}
        teacher_classrooms = {
            teacher: frozenset(rooms) for teacher, rooms in self.teacher_classrooms.items() if rooms
        }
        periods = self._daily_periods()
        preserve_slots = (
            self._loaded_clock_signature == self._clock_signature()
            and self._loaded_slot_signature == self._slot_signature()
        )
        planning = PlanningInput(
            weeks=weeks,
            subjects=tuple(
                Subject(name, lessons, double) for name, lessons, double in self.subjects
            ),
            teachers=tuple(Teacher(name) for name in self.teachers),
            classrooms=classrooms,
            slots=self.planning.slots
            if preserve_slots
            else build_slots(
                weeks=weeks,
                days=days,
                daily_periods=tuple(periods),
                day_period_counts=day_period_counts,
                saturday_weeks=saturday_weeks,
            ),
            teacher_subjects={
                teacher: frozenset(self.teacher_subjects.get(teacher, set()))
                for teacher in self.teachers
            },
            teacher_classrooms=teacher_classrooms,
            forbidden_consecutive=self.planning.forbidden_consecutive,
            forbidden_parallel=self.planning.forbidden_parallel,
            course_name=self.course_var.get().strip(),
            class_start=time.fromisoformat(self.class_start_var.get().strip()),
            period_duration_minutes=max(0, int(self.period_duration_var.get())),
            transition_minutes=max(0, int(self.transition_var.get())),
            break_start=parse_optional_time(self.break_start_var.get()),
            break_end=parse_optional_time(self.break_end_var.get()),
            lunch_start=parse_optional_time(self.lunch_start_var.get()),
            lunch_end=parse_optional_time(self.lunch_end_var.get()),
            lunch_after_period=max(0, int(self.lunch_after_var.get())),
            teacher_unavailable_days=teacher_unavailable_days,
            subject_unavailable_days=subject_unavailable_days,
            day_period_counts=day_period_counts,
            saturday_weeks=saturday_weeks,
        )
        validate_planning(planning)
        return planning

    def _save(self) -> None:
        if self._editor_snapshot is not None:
            return
        try:
            planning = self._sync_planning()
        except (TypeError, ValueError, tk.TclError) as error:
            messagebox.showerror("Configuración incompleta", str(error), parent=self)
            return
        path = filedialog.asksaveasfilename(
            title="Guardar",
            defaultextension=".json",
            initialfile=self.document_path.name if self.document_path else "centro.json",
            filetypes=(("Scholar Calendar", "*.json"),),
            parent=self,
        )
        if path:
            try:
                self._update_schedule_metadata(planning)
                save_project(CalendarProject(planning, self.schedule_planning, self.schedule), path)
                self.planning = planning
                self._refresh_schedule_notice()
                if self.schedule is not None:
                    self._render()
                self.document_path = Path(path)
                self.status_var.set(
                    f"Guardado: {Path(path).name}"
                    + (
                        " · Configuración y horario"
                        if self.schedule is not None
                        else " · Configuración"
                    )
                )
            except (OSError, TypeError, ValueError) as error:
                messagebox.showerror("No se pudo guardar", str(error), parent=self)

    def _generate(self) -> None:
        try:
            self.planning = self._sync_planning()
            if (
                not self.planning.classrooms
                or not self.planning.subjects
                or not self.planning.teachers
            ):
                raise ValueError(
                    "Añade al menos un aula, una asignatura y un profesor antes de generar."
                )
            self.status_var.set("Generando el horario…")
            self.update_idletasks()
            self.schedule = solve(self.planning)
            self.schedule_planning = self.planning
            self._refresh_schedule_notice()
            self.selected_subject = None
            self._update_file_menu()
            self.week_var.set("1")
            self._refresh_saturday_controls()
            self.week_combo["values"] = [str(week) for week in range(1, self.planning.weeks + 1)]
            self._render()
            self.notebook.select(self.schedule_tab)
            self.status_var.set(f"Horario generado: {len(self.schedule.lessons)} sesiones")
        except (ScheduleError, TypeError, ValueError, tk.TclError) as error:
            self._refresh_schedule_notice()
            self.status_var.set(
                "No se pudo generar el horario. Revisa la configuración y las restricciones."
            )
            messagebox.showerror("No se pudo generar el horario", str(error))

    def _add_subject(self) -> None:
        name = self.subject_name_var.get().strip()
        if name and name not in {subject[0] for subject in self.subjects}:
            lessons = self._read_subject_frequency()
            if lessons is None:
                return
            self.subjects.append((name, lessons, self.subject_double_var.get()))
            self.subject_name_var.set("")
            self._refresh_editors()

    def _select_subject(self, _event: tk.Event) -> None:
        selected = self.subject_tree.selection()
        if selected:
            name, lessons, double = self.subject_tree.item(selected[0], "values")
            self.subject_name_var.set(name)
            self.subject_lessons_var.set(int(lessons))
            self.subject_double_var.set(double == "Sí")

    def _edit_subject(self) -> None:
        selected = self.subject_tree.selection()
        if not selected:
            return
        old_name = self.subject_tree.item(selected[0], "values")[0]
        new_name = self.subject_name_var.get().strip()
        if not new_name:
            messagebox.showinfo("Editar asignatura", "Escribe el nuevo nombre antes de editar.")
            return
        if not self._unique_name(new_name, old_name, [name for name, _, _ in self.subjects]):
            return
        frequency = self._read_subject_frequency()
        if frequency is None:
            return
        for index, (name, lessons, double) in enumerate(self.subjects):
            if name == old_name:
                self.subjects[index] = (
                    new_name,
                    frequency,
                    self.subject_double_var.get(),
                )
        for subjects in self.teacher_subjects.values():
            if old_name in subjects:
                subjects.remove(old_name)
                subjects.add(new_name)
        self._update_resource_rules("subject", old_name, new_name)
        self._editor_renames.append(ResourceRename("subject", old_name, new_name))
        self.subject_name_var.set("")
        self._refresh_editors()

    def _remove_subject(self) -> None:
        selected = self.subject_tree.selection()
        if selected:
            name = self.subject_tree.item(selected[0], "values")[0]
            self.subjects = [subject for subject in self.subjects if subject[0] != name]
            for subjects in self.teacher_subjects.values():
                subjects.discard(name)
            self._update_resource_rules("subject", name, None)
            self._refresh_editors()

    def _add_teacher(self) -> None:
        name = self.teacher_name_var.get().strip()
        if name and name not in self.teachers:
            self.teachers.append(name)
            self.teacher_subjects[name] = set()
            self.teacher_name_var.set("")
            self._refresh_editors()

    def _select_teacher(self, _event: tk.Event) -> None:
        selected = self.teacher_list.curselection()
        if selected:
            self.teacher_name_var.set(self.teacher_list.get(selected[0]))

    def _edit_teacher(self) -> None:
        selected = self.teacher_list.curselection()
        new_name = self.teacher_name_var.get().strip()
        if not selected or not new_name:
            return
        index = selected[0]
        old_name = self.teachers[index]
        if not self._unique_name(new_name, old_name, self.teachers):
            return
        self.teachers[index] = new_name
        self.teacher_subjects[new_name] = self.teacher_subjects.pop(old_name, set())
        self.teacher_classrooms[new_name] = self.teacher_classrooms.pop(old_name, set())
        self._update_resource_rules("teacher", old_name, new_name)
        self._editor_renames.append(ResourceRename("teacher", old_name, new_name))
        self.teacher_name_var.set("")
        self._refresh_editors()

    def _add_classroom(self) -> None:
        name = self.classroom_name_var.get().strip()
        classrooms = list(self.classroom_list.get(0, tk.END))
        if name and name not in classrooms:
            self.classroom_list.insert(tk.END, name)
            self.classroom_name_var.set("")
            self._refresh_editors()

    def _select_classroom(self, _event: tk.Event) -> None:
        selected = self.classroom_list.curselection()
        if selected:
            self.classroom_name_var.set(self.classroom_list.get(selected[0]))

    def _edit_classroom(self) -> None:
        selected = self.classroom_list.curselection()
        new_name = self.classroom_name_var.get().strip()
        if not selected or not new_name:
            return
        index = selected[0]
        old_name = self.classroom_list.get(index)
        if not self._unique_name(new_name, old_name, self.classroom_list.get(0, tk.END)):
            return
        self.classroom_list.delete(index)
        self.classroom_list.insert(index, new_name)
        self._editor_renames.append(ResourceRename("classroom", old_name, new_name))
        for classrooms in self.teacher_classrooms.values():
            if old_name in classrooms:
                classrooms.remove(old_name)
                classrooms.add(new_name)
        self.classroom_name_var.set("")
        self._refresh_editors()

    def _remove_classroom(self) -> None:
        selected = self.classroom_list.curselection()
        if selected:
            name = self.classroom_list.get(selected[0])
            self.classroom_list.delete(selected[0])
            for classrooms in self.teacher_classrooms.values():
                classrooms.discard(name)
            self._refresh_editors()

    def _remove_teacher(self) -> None:
        selected = self.teacher_list.curselection()
        if selected:
            name = self.teachers[selected[0]]
            self.teachers.remove(name)
            self.teacher_subjects.pop(name, None)
            self.teacher_classrooms.pop(name, None)
            self._update_resource_rules("teacher", name, None)
            self._refresh_editors()

    def _add_association(self) -> None:
        teacher = self.association_teacher_var.get()
        subject = self.association_subject_var.get()
        if teacher and subject:
            self.teacher_subjects.setdefault(teacher, set()).add(subject)
            self._refresh_editors()

    def _select_association(self, _event: tk.Event) -> None:
        selected = self.association_tree.selection()
        if selected:
            teacher, subject = self.association_tree.item(selected[0], "values")
            self.association_teacher_var.set(teacher)
            self.association_subject_var.set(subject)

    def _edit_association(self) -> None:
        selected = self.association_tree.selection()
        teacher = self.association_teacher_var.get()
        subject = self.association_subject_var.get()
        if not selected or not teacher or not subject:
            return
        old_teacher, old_subject = self.association_tree.item(selected[0], "values")
        self.teacher_subjects.get(old_teacher, set()).discard(old_subject)
        self.teacher_subjects.setdefault(teacher, set()).add(subject)
        self._refresh_editors()

    def _remove_association(self) -> None:
        selected = self.association_tree.selection()
        if selected:
            teacher, subject = self.association_tree.item(selected[0], "values")
            self.teacher_subjects.get(teacher, set()).discard(subject)
            self._refresh_editors()

    def _refresh_editors(self) -> None:
        for item in self.subject_tree.get_children():
            self.subject_tree.delete(item)
        for name, lessons, double in self.subjects:
            self.subject_tree.insert("", tk.END, values=(name, lessons, "Sí" if double else "No"))
        self.teacher_list.delete(0, tk.END)
        for teacher in self.teachers:
            self.teacher_list.insert(tk.END, teacher)
        for item in self.association_tree.get_children():
            self.association_tree.delete(item)
        for teacher in self.teachers:
            for subject in sorted(self.teacher_subjects.get(teacher, set())):
                self.association_tree.insert("", tk.END, values=(teacher, subject))
        subjects = [subject[0] for subject in self.subjects]
        self.association_subject_combo["values"] = subjects
        self.association_teacher_combo["values"] = self.teachers
        self.classroom_teacher_combo["values"] = self.teachers
        self.unavailable_teacher_combo["values"] = self.teachers
        self.unavailable_subject_combo["values"] = [name for name, _, _ in self.subjects]
        for variable, values in (
            (self.association_subject_var, subjects),
            (self.association_teacher_var, self.teachers),
            (self.classroom_teacher_var, self.teachers),
            (self.unavailable_teacher_var, self.teachers),
            (self.unavailable_subject_var, subjects),
            (self.consecutive_first_var, subjects),
            (self.consecutive_second_var, subjects),
            (self.parallel_first_var, subjects),
            (self.parallel_second_var, subjects),
        ):
            if variable.get() not in values:
                variable.set("")
        if subjects and not self.association_subject_var.get():
            self.association_subject_var.set(subjects[0])
        if self.teachers and not self.association_teacher_var.get():
            self.association_teacher_var.set(self.teachers[0])
        for item in self.classroom_association_tree.get_children():
            self.classroom_association_tree.delete(item)
        for teacher in self.teachers:
            classrooms = sorted(self.teacher_classrooms.get(teacher, set()))
            if classrooms:
                self.classroom_association_tree.insert(
                    "", tk.END, values=(teacher, ", ".join(classrooms))
                )
        if self.teachers and not self.classroom_teacher_var.get():
            self.classroom_teacher_var.set(self.teachers[0])
        self._refresh_subject_rule_editors()
        self._refresh_unavailable_editors()

    def _read_subject_frequency(self) -> int | None:
        try:
            frequency = int(self.subject_lessons_var.get())
            if frequency < 1:
                raise ValueError
            return frequency
        except (ValueError, tk.TclError):
            messagebox.showerror(
                "Frecuencia inválida",
                "Indica al menos una sesión semanal.",
                parent=self.editor_window,
            )
            return None

    def _unique_name(self, name: str, previous: str, names) -> bool:
        if name != previous and name in names:
            messagebox.showerror(
                "Nombre duplicado", f"Ya existe «{name}».", parent=self.editor_window
            )
            return False
        return True

    def _update_resource_rules(self, kind: str, previous: str, name: str | None) -> None:
        """Keep name-based restrictions attached to renamed resources and remove orphan rules."""
        if self.planning is None:
            return
        field = f"{kind}_unavailable_days"
        days = dict(getattr(self.planning, field) or {})
        blocked = days.pop(previous, None)
        if name is not None and blocked is not None:
            days[name] = blocked
        changes = {field: days}
        if kind == "subject":
            for field in ("forbidden_consecutive", "forbidden_parallel"):
                changes[field] = frozenset(
                    frozenset(name if value == previous else value for value in pair)
                    for pair in getattr(self.planning, field)
                    if name is not None or previous not in pair
                )
        self.planning = replace(self.planning, **changes)

    def _add_classroom_association(self) -> None:
        association = self._read_classroom_association()
        if association is not None:
            teacher, classrooms = association
            self.teacher_classrooms[teacher] = classrooms
            self.classroom_names_var.set("")
            self._refresh_editors()

    def _read_classroom_association(self) -> tuple[str, set[str]] | None:
        teacher = self.classroom_teacher_var.get().strip()
        classrooms = {
            room.strip() for room in self.classroom_names_var.get().split(",") if room.strip()
        }
        valid_classrooms = set(self.classroom_list.get(0, tk.END))
        unknown = classrooms - valid_classrooms
        if unknown:
            messagebox.showerror(
                "Aula desconocida",
                f"Define primero estas aulas: {', '.join(sorted(unknown))}",
                parent=self.editor_window,
            )
            return None
        return (teacher, classrooms) if teacher in self.teachers and classrooms else None

    def _remove_classroom_association(self) -> None:
        selected = self.classroom_association_tree.selection()
        if selected:
            teacher = self.classroom_association_tree.item(selected[0], "values")[0]
            self.teacher_classrooms.pop(teacher, None)
            self._refresh_editors()

    def _edit_classroom_association(self) -> None:
        selected = self.classroom_association_tree.selection()
        if not selected:
            return
        association = self._read_classroom_association()
        if association is not None:
            teacher, classrooms = association
            old_teacher = self.classroom_association_tree.item(selected[0], "values")[0]
            self.teacher_classrooms.pop(old_teacher, None)
            self.teacher_classrooms[teacher] = classrooms
            self.classroom_names_var.set("")
            self._refresh_editors()

    def _select_classroom_association(self, _event: tk.Event) -> None:
        selected = self.classroom_association_tree.selection()
        if selected:
            teacher, classrooms = self.classroom_association_tree.item(selected[0], "values")
            self.classroom_teacher_var.set(teacher)
            self.classroom_names_var.set(classrooms)

    def _refresh_unavailable_editors(self) -> None:
        for tree, rules in (
            (
                self.teacher_day_tree,
                self.planning.teacher_unavailable_days if self.planning else {},
            ),
            (
                self.subject_day_tree,
                self.planning.subject_unavailable_days if self.planning else {},
            ),
        ):
            tree.delete(*tree.get_children())
            for name, days in sorted((rules or {}).items()):
                tree.insert(
                    "", tk.END, values=(name, ", ".join(DAY_NAMES[day] for day in sorted(days)))
                )

    def _read_days(self) -> frozenset[int]:
        days = frozenset(
            day for day, variable in self.unavailable_day_vars.items() if variable.get()
        )
        if not days:
            raise ValueError("Marca al menos un día para aplicar el bloqueo.")
        return days

    def _add_teacher_unavailable(self) -> None:
        try:
            name = self.unavailable_teacher_var.get()
            if name:
                rules = dict(self.planning.teacher_unavailable_days or {}) if self.planning else {}
                rules[name] = self._read_days()
                self.planning = self._planning_with_restrictions(
                    rules, self.planning.subject_unavailable_days if self.planning else {}
                )
                self._refresh_unavailable_editors()
        except ValueError as error:
            messagebox.showerror("Días inválidos", str(error))

    def _add_subject_unavailable(self) -> None:
        try:
            name = self.unavailable_subject_var.get()
            if name:
                rules = dict(self.planning.subject_unavailable_days or {}) if self.planning else {}
                rules[name] = self._read_days()
                self.planning = self._planning_with_restrictions(
                    self.planning.teacher_unavailable_days if self.planning else {}, rules
                )
                self._refresh_unavailable_editors()
        except ValueError as error:
            messagebox.showerror("Días inválidos", str(error))

    def _remove_unavailable(self) -> None:
        selected_teacher = self.teacher_day_tree.selection()
        selected_subject = self.subject_day_tree.selection()
        if selected_teacher and self.planning:
            name = self.teacher_day_tree.item(selected_teacher[0], "values")[0]
            rules = dict(self.planning.teacher_unavailable_days or {})
            rules.pop(name, None)
            self.planning = self._planning_with_restrictions(
                rules, self.planning.subject_unavailable_days or {}
            )
        elif selected_subject and self.planning:
            name = self.subject_day_tree.item(selected_subject[0], "values")[0]
            rules = dict(self.planning.subject_unavailable_days or {})
            rules.pop(name, None)
            self.planning = self._planning_with_restrictions(
                self.planning.teacher_unavailable_days or {}, rules
            )
        self._refresh_unavailable_editors()

    def _planning_with_restrictions(
        self, teacher_rules: dict[str, frozenset[int]], subject_rules: dict[str, frozenset[int]]
    ) -> PlanningInput:
        if self.planning is None:
            return self._blank_planning()
        return replace(
            self.planning,
            teacher_unavailable_days=teacher_rules,
            subject_unavailable_days=subject_rules,
        )

    def _select_schedule_subject(self, subject: str | None) -> None:
        self.selected_subject = subject
        self.table.set_subject(subject)
        if subject is None or self.schedule is None:
            self.restriction_note.pack_forget()
            self.highlight_label.pack(side=tk.LEFT)
            self.subject_highlight_var.set(
                "Doble clic en una clase para resaltar su asignatura. Escape para quitar el resaltado."
            )
            return
        matches = [lesson for lesson in self.schedule.lessons if lesson.subject == subject]
        weekly = sum(lesson.week == int(self.week_var.get()) for lesson in matches)
        self.subject_highlight_var.set(
            f"{subject} · {weekly} sesiones esta semana · {len(matches)} en el ciclo · Escape para quitar"
        )
        if self.schedule_planning is not None:
            restrictions = subject_restrictions(self.schedule_planning, self.schedule, subject)
            if restrictions:
                self.highlight_label.pack_forget()
                title = f"{subject} · {weekly} sesiones esta semana · {len(matches)} en el ciclo"
                self.restriction_note.set_lines(restrictions, title=title)
                self.restriction_note.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 12))
            else:
                self.restriction_note.pack_forget()
                self.highlight_label.pack(side=tk.LEFT)

    def _clear_table(self) -> None:
        self.table.set_rows(
            [("Tu semana empieza aquí", 1000)],
            [
                GridRow(
                    (
                        "Define la jornada, añade asignaturas y profesores, y pulsa Generar horario. También puedes abrir un horario guardado.",
                    )
                )
            ],
        )
        self._select_schedule_subject(None)
        self.schedule_summary_var.set("Todavía no hay un horario generado.")
        self._update_file_menu()

    def _render(self) -> None:
        self._refresh_schedule_notice()
        planning = self.schedule_planning
        if planning is None or self.schedule is None:
            return
        week = max(1, min(planning.weeks, int(self.week_var.get())))
        self.week_var.set(str(week))
        self.week_combo["values"] = [str(value) for value in range(1, planning.weeks + 1)]
        classrooms = [classroom.name for classroom in planning.classrooms]
        columns = [("Día / turno", 145), ("Horario", 155), *[(room, 200) for room in classrooms]]
        lessons = {
            (lesson.day, lesson.period, lesson.classroom): lesson
            for lesson in self.schedule.lessons
            if lesson.week == week
        }
        days = sorted({slot.day for slot in planning.slots if slot.week == week})
        self.schedule_summary_var.set(
            f"{planning.course_name or 'Planificación escolar'} · Semana {week} de {planning.weeks} · {len(classrooms)} aulas · {len(lessons)} sesiones"
        )
        grid_rows = []
        for day_index, day in enumerate(days):
            rows = daily_rows(planning, week, day)
            period_count = sum(row.period is not None for row in rows)
            grid_rows.append(GridRow((DAY_NAMES[day].upper(), f"{period_count} turnos"), "day"))
            for row in rows:
                subjects = [None, None]
                if row.period is None:
                    if row.label == "Cambio de clase":
                        continue
                    values = [DAY_NAMES[day], row.hours, *[row.label for _ in classrooms]]
                    tag = "gap" if row.label == "Tiempo libre" else "pause"
                else:
                    values = [f"{DAY_NAMES[day]} · {row.period:02d}", row.hours]
                    for classroom in classrooms:
                        lesson = lessons.get((day, row.period, classroom))
                        values.append(f"{lesson.subject}\n{lesson.teacher}" if lesson else "—")
                        subjects.append(lesson.subject if lesson else None)
                    tag = "day_even" if day_index % 2 == 0 else "day_odd"
                grid_rows.append(
                    GridRow(
                        tuple(values),
                        tag,
                        tuple(subjects),
                        span_from=2 if row.label == "Merienda" else None,
                    )
                )
        self.table.set_rows(columns, grid_rows)
        self._select_schedule_subject(self.selected_subject)

    def _export_pdf(self) -> None:
        planning = self.schedule_planning
        if planning is None or self.schedule is None:
            messagebox.showinfo("Sin horario", "Genera un horario antes de exportar.")
            return
        path = filedialog.asksaveasfilename(
            title="Exportar horario a PDF",
            defaultextension=".pdf",
            filetypes=(("Documento PDF", "*.pdf"),),
        )
        if not path:
            return
        try:
            from .pdf import export_schedule_pdf

            export_schedule_pdf(planning, self.schedule, path)
            self.status_var.set(f"PDF exportado: {Path(path).name}")
        except (ImportError, OSError, ValueError) as error:
            messagebox.showerror("No se pudo exportar el PDF", str(error))


def main() -> None:
    app = CalendarApp()
    app.mainloop()


if __name__ == "__main__":
    main()
