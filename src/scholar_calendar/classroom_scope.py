"""Select all classrooms or an explicit subset without parsing their names."""

import tkinter as tk
from tkinter import ttk

from .theme import INK, PALE_TEAL


class ClassroomScope(ttk.Frame):
    def __init__(self, parent: tk.Misc, title: str) -> None:
        super().__init__(parent)
        self.all_rooms = tk.BooleanVar(value=True)
        self.enabled = True
        ttk.Label(self, text=title, style="Muted.TLabel").pack(anchor=tk.W)
        self.all_check = ttk.Checkbutton(
            self,
            text="Todas las aulas / grupos",
            variable=self.all_rooms,
            command=self._update_state,
        )
        self.all_check.pack(anchor=tk.W)
        row = ttk.Frame(self)
        row.pack(fill=tk.X)
        self.listbox = tk.Listbox(
            row,
            selectmode=tk.MULTIPLE,
            exportselection=False,
            height=3,
            background="white",
            foreground=INK,
            selectbackground=PALE_TEAL,
            selectforeground=INK,
            relief=tk.FLAT,
            borderwidth=0,
        )
        self.listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)
        scrollbar = ttk.Scrollbar(row, orient=tk.VERTICAL, command=self.listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.configure(yscrollcommand=scrollbar.set)
        ttk.Label(
            self,
            text="Desmarca «Todas» y pulsa las aulas para seleccionarlas. Sin selección: ninguna aula.",
            style="Muted.TLabel",
            wraplength=800,
        ).pack(anchor=tk.W, pady=(4, 0))
        self._update_state()

    def set_rooms(self, rooms: tuple[str, ...]) -> None:
        scope = self.get_scope()
        self.listbox.configure(state=tk.NORMAL)
        self.listbox.delete(0, tk.END)
        for room in rooms:
            self.listbox.insert(tk.END, room)
        self.set_scope(scope)

    def get_scope(self) -> frozenset[str] | None:
        if self.all_rooms.get():
            return None
        return frozenset(self.listbox.get(index) for index in self.listbox.curselection())

    def set_scope(self, scope: frozenset[str] | None) -> None:
        self.all_rooms.set(scope is None)
        self.listbox.configure(state=tk.NORMAL)
        self.listbox.selection_clear(0, tk.END)
        for index, room in enumerate(self.listbox.get(0, tk.END)):
            if scope is not None and room in scope:
                self.listbox.selection_set(index)
        self._update_state()

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        self._update_state()

    def _update_state(self) -> None:
        self.all_check.state(["!disabled" if self.enabled else "disabled"])
        self.listbox.configure(
            state=tk.NORMAL if self.enabled and not self.all_rooms.get() else tk.DISABLED
        )


def scope_description(scope: frozenset[str] | None) -> str:
    return "Todas las aulas" if scope is None else ", ".join(sorted(scope)) or "Ninguna aula"
