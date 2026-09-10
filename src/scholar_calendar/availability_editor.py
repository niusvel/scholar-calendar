"""Availability editor for a subject, a teacher, or a teacher–subject pair."""

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

from .availability import all_blocks, block_key, block_time
from .models import AvailabilityBlock, PlanningInput
from .timeline import DAY_NAMES


class AvailabilityEditor(ttk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        kind: str,
        resource: tk.StringVar,
        on_change: Callable[[frozenset[AvailabilityBlock]], None],
    ) -> None:
        super().__init__(parent, style="Surface.TFrame", padding=20)
        self.kind = kind
        self.resource = resource
        self.on_change = on_change
        self.blocks: frozenset[AvailabilityBlock] = frozenset()
        self.rows: dict[str, AvailabilityBlock] = {}
        self.links: dict[str, frozenset[str]] = {}
        self.subject_options: list[str | None] = [None]
        self.classroom_options: list[str | None] = [None]
        self.days = {day: tk.BooleanVar(value=False) for day in DAY_NAMES}
        self.period = tk.StringVar(value="Todo el día")
        self.error = tk.StringVar()
        label = "Profesor" if kind == "teacher" else "Asignatura"
        ttk.Label(self, text="Disponibilidad · " + label.lower(), style="Section.TLabel").pack(
            anchor=tk.W
        )
        ttk.Label(
            self,
            text="Bloquea días completos o turnos concretos, en todas las aulas o en una específica. Se repite cada semana.",
            style="Muted.TLabel",
            wraplength=800,
        ).pack(anchor=tk.W, pady=(6, 14))
        table = ttk.Frame(self)
        table.pack(fill=tk.X)
        self.tree = ttk.Treeview(
            table,
            columns=("resource", "scope", "when"),
            show="headings",
            height=3,
            selectmode="browse",
        )
        for key, title, width in (
            ("resource", label, 200),
            ("scope", "Alcance", 250),
            ("when", "Bloqueo", 250),
        ):
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, minwidth=100)
        self.tree.pack(side=tk.LEFT, fill=tk.X, expand=True)
        scrollbar = ttk.Scrollbar(table, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.bind("<<TreeviewSelect>>", self._select)
        form = ttk.Frame(self)
        form.pack(fill=tk.X, pady=(14, 10))
        form.columnconfigure((0, 1, 2), weight=1, uniform="availability")
        ttk.Label(form, text=label, style="Muted.TLabel").grid(row=0, column=0, sticky=tk.W)
        self.resource_combo = ttk.Combobox(form, textvariable=resource, state="readonly", width=18)
        self.resource_combo.grid(row=1, column=0, sticky="ew", padx=(0, 12), pady=(4, 0))
        self.resource_combo.bind(
            "<<ComboboxSelected>>", lambda _event: self.focus_resource(self.resource.get())
        )
        self.subject_combo = None
        if kind == "teacher":
            ttk.Label(form, text="Cuando imparte", style="Muted.TLabel").grid(
                row=0, column=1, sticky=tk.W
            )
            self.subject_combo = ttk.Combobox(form, state="readonly", width=18)
            self.subject_combo.grid(row=1, column=1, sticky="ew", padx=(0, 12), pady=(4, 0))
        else:
            ttk.Label(form, text="Con cualquier profesor", style="Muted.TLabel").grid(
                row=1, column=1, sticky=tk.W
            )
        ttk.Label(form, text="Aula / grupo", style="Muted.TLabel").grid(
            row=0, column=2, sticky=tk.W
        )
        self.classroom_combo = ttk.Combobox(form, state="readonly", width=18)
        self.classroom_combo.grid(row=1, column=2, sticky="ew", pady=(4, 0))
        day_row = ttk.Frame(self)
        day_row.pack(fill=tk.X, pady=(4, 10))
        for day, title in DAY_NAMES.items():
            ttk.Checkbutton(day_row, text=title, variable=self.days[day]).pack(
                side=tk.LEFT, padx=(0, 8)
            )
        turn_row = ttk.Frame(self)
        turn_row.pack(fill=tk.X)
        ttk.Label(turn_row, text="Turno que no se puede utilizar", style="Muted.TLabel").pack(
            side=tk.LEFT, padx=(0, 12)
        )
        self.period_combo = ttk.Combobox(
            turn_row, textvariable=self.period, state="readonly", width=18
        )
        self.period_combo.pack(side=tk.LEFT)
        ttk.Label(
            self,
            text="Para bloquear varios turnos, añade un bloqueo por turno. Los bloqueos se suman.",
            style="Muted.TLabel",
            wraplength=800,
        ).pack(anchor=tk.W, pady=(8, 0))
        ttk.Label(self, textvariable=self.error, foreground="#a13b34", wraplength=800).pack(
            anchor=tk.W, pady=(6, 0)
        )
        actions = ttk.Frame(self)
        actions.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(actions, text="Añadir bloqueo", command=self.add).pack(side=tk.LEFT)
        ttk.Button(
            actions, text="Actualizar seleccionado", command=lambda: self.add(edit=True)
        ).pack(side=tk.LEFT, padx=8)
        ttk.Button(
            actions, text="Eliminar seleccionado", style="Danger.TButton", command=self.remove
        ).pack(side=tk.RIGHT)

    def show(self, planning: PlanningInput) -> None:
        previous_classroom = (
            self.classroom_options[self.classroom_combo.current()]
            if self.classroom_combo.current() >= 0
            else None
        )
        self.classroom_options = [None, *(room.name for room in planning.classrooms)]
        self.classroom_combo["values"] = ["Todas las aulas", *self.classroom_options[1:]]
        self.classroom_combo.current(
            self.classroom_options.index(previous_classroom)
            if previous_classroom in self.classroom_options
            else 0
        )
        previous_subject = (
            self.subject_options[self.subject_combo.current()]
            if self.subject_combo is not None and self.subject_combo.current() >= 0
            else None
        )
        self.blocks = all_blocks(planning)
        self.links = planning.teacher_subjects
        names = [
            item.name
            for item in (planning.teachers if self.kind == "teacher" else planning.subjects)
        ]
        self.resource_combo["values"] = names
        if self.resource.get() not in names:
            self.resource.set(names[0] if names else "")
        self._refresh_subjects(previous_subject)
        periods = {slot.period for slot in planning.slots}
        periods.update(range(1, max((planning.day_period_counts or {}).values(), default=0) + 1))
        periods.update(block.period for block in self.blocks if block.period is not None)
        self.period_combo["values"] = ["Todo el día", *(str(period) for period in sorted(periods))]
        if self.period.get() not in self.period_combo["values"]:
            self.period.set("Todo el día")
        self.tree.delete(*self.tree.get_children())
        self.rows.clear()
        for block in sorted(self.blocks, key=block_key):
            if self.kind == "teacher" and block.teacher is not None:
                resource, scope = block.teacher, block.subject or "Todas las asignaturas"
            elif self.kind == "subject" and block.teacher is None:
                resource, scope = block.subject, "Cualquier profesor"
            else:
                continue
            item = self.tree.insert("", tk.END, values=(resource, scope, block_time(block)))
            self.rows[item] = block

    def _refresh_subjects(self, subject: str | None = None) -> None:
        if self.subject_combo is None:
            return
        self.subject_options = [None, *sorted(self.links.get(self.resource.get(), ()))]
        self.subject_combo["values"] = ["Todas las asignaturas", *self.subject_options[1:]]
        self.subject_combo.current(
            self.subject_options.index(subject) if subject in self.subject_options else 0
        )

    def focus_resource(self, name: str) -> None:
        self.resource.set(name)
        self.tree.selection_remove(*self.tree.selection())
        self._refresh_subjects()
        self.classroom_combo.current(0)
        self.period.set("Todo el día")
        self.error.set("")
        for variable in self.days.values():
            variable.set(False)

    def _select(self, _event=None) -> None:
        selection = self.tree.selection()
        block = self.rows.get(selection[0]) if selection else None
        if block is None:
            return
        self.resource.set(block.teacher if self.kind == "teacher" else block.subject)
        self._refresh_subjects(block.subject if self.kind == "teacher" else None)
        self.classroom_combo.current(self.classroom_options.index(block.classroom))
        self.period.set(str(block.period) if block.period is not None else "Todo el día")
        for day, variable in self.days.items():
            variable.set(day == block.day)
        self.error.set("")

    def add(self, *, edit: bool = False) -> None:
        name = self.resource.get()
        if not name or name not in self.resource_combo["values"]:
            self.error.set("Selecciona un recurso existente.")
            return
        days = [day for day, variable in self.days.items() if variable.get()]
        if not days:
            self.error.set("Selecciona al menos un día.")
            return
        if self.period.get() not in self.period_combo["values"]:
            self.error.set("Selecciona un turno o Todo el día.")
            return
        if self.classroom_combo.current() < 0:
            self.error.set("Selecciona un aula o Todas las aulas.")
            return
        classroom = self.classroom_options[self.classroom_combo.current()]
        period = None if self.period.get() == "Todo el día" else int(self.period.get())
        selection = self.tree.selection()
        old = self.rows.get(selection[0]) if selection else None
        if edit and old is None:
            self.error.set("Selecciona primero el bloqueo que quieres actualizar.")
            return
        teacher = name if self.kind == "teacher" else None
        subject = (
            name if self.kind == "subject" else self.subject_options[self.subject_combo.current()]
        )
        blocks = set(self.blocks)
        if edit:
            blocks.discard(old)
        blocks.update(
            AvailabilityBlock(
                day=day, period=period, teacher=teacher, subject=subject, classroom=classroom
            )
            for day in days
        )
        self.error.set("")
        self.on_change(frozenset(blocks))

    def remove(self) -> None:
        selection = self.tree.selection()
        block = self.rows.get(selection[0]) if selection else None
        if block is None:
            self.error.set("Selecciona el bloqueo que quieres eliminar.")
            return
        self.error.set("")
        self.on_change(self.blocks - {block})
