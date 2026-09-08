"""Read-only configuration overview with entry points to focused editors."""

import tkinter as tk
from collections import Counter
from collections.abc import Callable
from tkinter import ttk

from .clock import minutes_since_midnight
from .models import PlanningInput
from .timeline import DAY_NAMES, daily_rows


def configuration_sections(planning: PlanningInput) -> dict[str, tuple[tuple[str, str], ...]]:
    def hours(start, end):
        return f"{start:%H:%M} – {end:%H:%M}" if start and end else "Sin pausa"

    def days(values):
        return ", ".join(DAY_NAMES[day] for day in sorted(values)) or "Ninguno"

    counts = planning.day_period_counts or {
        day: max((slot.period for slot in planning.slots if slot.day == day), default=0)
        for day in DAY_NAMES
    }
    periods = sorted({(slot.period, slot.start, slot.end) for slot in planning.slots})
    clock = (
        ("Curso", planning.course_name or "Sin nombre"),
        ("Ciclo", f"{planning.weeks} semanas"),
        ("Inicio", f"{planning.class_start:%H:%M}"),
        (
            "Clases y cambios",
            f"{planning.period_duration_minutes} min por turno · {planning.transition_minutes} min entre clases",
        ),
        ("Merienda", hours(planning.break_start, planning.break_end)),
        (
            "Comida",
            hours(planning.lunch_start, planning.lunch_end)
            + (
                f" · después del turno {planning.lunch_after_period}"
                if planning.lunch_start
                else ""
            ),
        ),
        (
            "Franjas de clase",
            "\n".join(f"{period:02d}: {start:%H:%M}–{end:%H:%M}" for period, start, end in periods)
            or "Sin turnos",
        ),
    )
    teaching_days = tuple(
        (name, f"{counts.get(day, 0)} turnos" if counts.get(day) else "No lectivo")
        for day, name in DAY_NAMES.items()
    ) + (
        (
            "Sábados activos",
            ", ".join(f"Semana {week}" for week in sorted(planning.saturday_weeks)) or "Ninguno",
        ),
        ("Domingo", "No lectivo"),
    )
    subjects = []
    for subject in planning.subjects:
        teachers = sorted(
            name for name, names in planning.teacher_subjects.items() if subject.name in names
        )
        detail = f"{subject.lessons_per_cycle} sesiones / semana / aula · " + (
            "Turnos dobles" if subject.double_period else "Una sesión al día como máximo"
        )
        detail += "\nProfesores: " + (", ".join(teachers) or "Sin profesor asociado")
        detail += "\nDías bloqueados: " + days(
            (planning.subject_unavailable_days or {}).get(subject.name, ())
        )
        subjects.append((subject.name, detail))
    teachers = []
    for teacher in planning.teachers:
        subjects_for_teacher = (
            ", ".join(sorted(planning.teacher_subjects.get(teacher.name, ())))
            or "Sin asignaturas asociadas"
        )
        rooms = (
            ", ".join(sorted(planning.teacher_classrooms.get(teacher.name, ())))
            or "Todas las aulas"
        )
        blocked = days((planning.teacher_unavailable_days or {}).get(teacher.name, ()))
        teachers.append(
            (
                teacher.name,
                f"Asignaturas: {subjects_for_teacher}\nAulas: {rooms}\nDías bloqueados: {blocked}",
            )
        )
    classrooms = []
    for room in planning.classrooms:
        allowed = sorted(
            teacher.name
            for teacher in planning.teachers
            if not planning.teacher_classrooms.get(teacher.name)
            or room.name in planning.teacher_classrooms[teacher.name]
        )
        classrooms.append(
            (room.name, "Profesores con acceso: " + (", ".join(allowed) or "Sin profesores"))
        )
    rules = tuple(
        (
            label,
            "\n".join(
                " ↔ ".join(sorted(pair)) for pair in sorted(pairs, key=lambda pair: sorted(pair))
            )
            or "Sin restricciones",
        )
        for label, pairs in (
            ("No consecutivas", planning.forbidden_consecutive),
            ("No simultáneas", planning.forbidden_parallel),
        )
    ) + (
        (
            "Preferencia de distribución",
            "Intentar que cada asignatura tenga alguna sesión fuera de los turnos 5.º y 6.º, por aula y semana.",
        ),
        (
            "Preferencia en dobles",
            "Intentar que la merienda no quede entre los dos turnos. Estas preferencias pueden ceder ante las reglas obligatorias.",
        ),
    )
    return {
        "clock": clock,
        "days": teaching_days,
        "subjects": tuple(subjects),
        "teachers": tuple(teachers),
        "classrooms": tuple(classrooms),
        "rules": rules,
    }


class ConfigurationOverview(ttk.Frame):
    def __init__(self, parent: tk.Misc, on_edit: Callable[[str], None]) -> None:
        super().__init__(parent, style="App.TFrame")
        self.on_edit = on_edit
        self.summary = ttk.Label(self, style="Status.TLabel", padding=(2, 0, 0, 14))
        self.summary.pack(anchor=tk.W)
        top = ttk.Frame(self, style="App.TFrame")
        top.pack(fill=tk.X)
        top.columnconfigure((0, 1), weight=1, uniform="summary")
        self.cards = {}
        definitions = (
            ("clock", "Jornada escolar", "clock"),
            ("days", "Días lectivos", "clock"),
            ("subjects", "Asignaturas", "subjects"),
            ("teachers", "Profesores y asociaciones", "teachers"),
            ("classrooms", "Aulas / grupos", "classrooms"),
            ("rules", "Restricciones entre asignaturas", "rules"),
        )
        for index, (key, title, section) in enumerate(definitions):
            card = ttk.Frame(top if index < 2 else self, style="Surface.TFrame", padding=20)
            if index < 2:
                card.grid(
                    row=0,
                    column=index,
                    sticky="nsew",
                    padx=(0, 7) if index == 0 else (7, 0),
                    pady=(0, 14),
                )
            else:
                card.pack(fill=tk.X, pady=(0, 14))
            heading = ttk.Frame(card, style="Card.TFrame")
            heading.pack(fill=tk.X, pady=(0, 14))
            ttk.Label(heading, text=title, style="Section.TLabel").pack(side=tk.LEFT)
            ttk.Button(
                heading, text="Editar", command=lambda section=section: on_edit(section)
            ).pack(side=tk.RIGHT)
            if key in ("subjects", "teachers", "classrooms"):
                ttk.Button(
                    heading, text="Asociaciones", command=lambda: on_edit("associations")
                ).pack(side=tk.RIGHT, padx=6)
            if key in ("subjects", "teachers"):
                ttk.Button(heading, text="Días bloqueados", command=lambda: on_edit("rules")).pack(
                    side=tk.RIGHT
                )
            content = ttk.Frame(card, style="Card.TFrame")
            content.pack(fill=tk.X)
            self.cards[key] = content

    def show(self, planning: PlanningInput) -> None:
        self.summary.configure(
            text=f"Toda la configuración del centro · {len(planning.subjects)} asignaturas · {len(planning.teachers)} profesores · {len(planning.classrooms)} aulas"
        )
        for key, rows in configuration_sections(planning).items():
            content = self.cards[key]
            for child in content.winfo_children():
                child.destroy()
            if not rows:
                ttk.Label(
                    content,
                    text="Todavía no hay datos. Pulsa Editar para empezar.",
                    style="Muted.TLabel",
                ).pack(anchor=tk.W)
                continue
            for index, (title, details) in enumerate(rows):
                if index:
                    ttk.Separator(content).pack(fill=tk.X, pady=7)
                if key == "clock" and title == "Franjas de clase":
                    self._build_period_preview(content, planning)
                    continue
                row = ttk.Frame(content, style="Card.TFrame")
                row.pack(fill=tk.X)
                title_width = 120 if key in ("clock", "days") else 170
                row.columnconfigure(0, minsize=title_width)
                row.columnconfigure(1, weight=1)
                label = ttk.Label(
                    row,
                    text=title,
                    font=("Helvetica", 11, "bold"),
                    anchor="nw",
                    wraplength=title_width - 12,
                )
                label.grid(row=0, column=0, sticky="nw", padx=(0, 12))
                text = ttk.Label(
                    row,
                    text=details,
                    style="Muted.TLabel",
                    justify=tk.LEFT,
                    anchor="nw",
                    wraplength=250,
                )
                text.grid(row=0, column=1, sticky="ew")
                row.bind(
                    "<Configure>",
                    lambda event, text=text, title_width=title_width: text.configure(
                        wraplength=max(100, event.width - title_width)
                    ),
                )

    def _build_period_preview(self, parent: ttk.Frame, planning: PlanningInput) -> None:
        ttk.Label(parent, text="Franjas de clase", font=("Helvetica", 11, "bold")).pack(
            anchor=tk.W, pady=(0, 8)
        )
        frame = ttk.Frame(parent, style="Card.TFrame")
        frame.pack(fill=tk.X)
        self.period_tree = ttk.Treeview(
            frame, columns=("activity", "hours", "duration"), show="headings", height=5
        )
        for key, title, width, minimum in (
            ("activity", "Actividad", 125, 85),
            ("hours", "Horario", 140, 125),
            ("duration", "Duración", 70, 65),
        ):
            self.period_tree.heading(key, text=title)
            self.period_tree.column(key, width=width, minwidth=minimum, anchor=tk.W)
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.period_tree.yview)
        self.period_tree.configure(yscrollcommand=scrollbar.set)
        self.period_tree.pack(side=tk.LEFT, fill=tk.X, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.period_tree.tag_configure("pause", background="#e5f3f2", foreground="#1f8a89")
        self.period_tree.tag_configure("gap", background="#fff4dc", foreground="#805d19")
        counts = Counter((slot.week, slot.day) for slot in planning.slots)
        if not counts:
            return
        week, day = max(counts, key=counts.get)
        for row in daily_rows(planning, week, day):
            duration = minutes_since_midnight(row.end) - minutes_since_midnight(row.start)
            tag = (
                "gap"
                if row.label == "Tiempo libre"
                else "pause"
                if row.period is None
                else "lesson"
            )
            self.period_tree.insert(
                "", tk.END, values=(row.label, row.hours, f"{duration} min"), tags=(tag,)
            )
        ttk.Label(
            parent,
            text="Vista del día con más turnos. Incluye cambios y pausas.",
            style="Muted.TLabel",
            wraplength=320,
        ).pack(anchor=tk.W, pady=(6, 0))
