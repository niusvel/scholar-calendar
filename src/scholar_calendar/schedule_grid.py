"""Scrollable timetable with subject highlighting at cell level."""

import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass
from tkinter import ttk


@dataclass(frozen=True)
class GridRow:
    """One display row; span_from merges that column through the last column."""

    values: tuple[str, ...]
    kind: str = "day_even"
    subjects: tuple[str | None, ...] = ()
    span_from: int | None = None


class ScheduleGrid(ttk.Frame):
    def __init__(self, parent, on_subject: Callable[[str | None], None]):
        super().__init__(parent, style="Card.TFrame")
        self.on_subject = on_subject
        self.selected_subject: str | None = None
        self.cells: list[tuple[int, int, str | None, str]] = []
        self._subjects_by_item: dict[int, str] = {}
        self.header = tk.Canvas(self, height=46, background="#172a3a", highlightthickness=0)
        self.body = tk.Canvas(self, background="white", highlightthickness=0, takefocus=True)
        self.header.grid(row=0, column=0, sticky="ew")
        self.body.grid(row=1, column=0, sticky="nsew")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.y_scroll = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.body.yview)
        self.x_scroll = ttk.Scrollbar(self, orient=tk.HORIZONTAL, command=self._xview)
        self.y_scroll.grid(row=1, column=1, sticky="ns")
        self.x_scroll.grid(row=2, column=0, sticky="ew")
        self.body.configure(yscrollcommand=self.y_scroll.set, xscrollcommand=self._sync_horizontal)
        self.body.bind("<Double-Button-1>", self._double_click)
        self.body.bind("<Button-1>", self._click)
        self.body.bind("<MouseWheel>", self._wheel)
        self.body.bind("<Button-4>", lambda _event: self.body.yview_scroll(-1, "units"))
        self.body.bind("<Button-5>", lambda _event: self.body.yview_scroll(1, "units"))

    def _xview(self, *args):
        self.body.xview(*args)

    def _sync_horizontal(self, first, last):
        self.x_scroll.set(first, last)
        self.header.xview_moveto(first)

    def _wheel(self, event):
        delta = (
            -int(event.delta / 120)
            if abs(event.delta) >= 120
            else (-1 if event.delta > 0 else 1 if event.delta < 0 else 0)
        )
        if event.state & 1:
            self.body.xview_scroll(delta, "units")
        else:
            self.body.yview_scroll(delta, "units")
        return "break"

    def _subject_at(self, event) -> str | None:
        x, y = self.body.canvasx(event.x), self.body.canvasy(event.y)
        return next(
            (
                self._subjects_by_item[item]
                for item in reversed(self.body.find_overlapping(x, y, x, y))
                if item in self._subjects_by_item
            ),
            None,
        )

    def _click(self, event):
        self.body.focus_set()
        if self._subject_at(event) is None:
            self.on_subject(None)

    def _double_click(self, event):
        self.body.focus_set()
        self.on_subject(self._subject_at(event))
        return "break"

    def set_subject(self, subject: str | None) -> None:
        self.selected_subject = subject
        for rectangle, text, cell_subject, background in self.cells:
            selected = subject is not None and cell_subject == subject
            self.body.itemconfigure(
                rectangle,
                fill="#ffedab" if selected else background,
                outline="#bc850d" if selected else "#d5dfe3",
                width=2 if selected else 1,
            )
            self.body.itemconfigure(text, fill="#624400" if selected else "#20313d")

    def set_rows(self, columns: list[tuple[str, int]], rows: list[GridRow]) -> None:
        self.header.delete("all")
        self.body.delete("all")
        self.cells.clear()
        self._subjects_by_item.clear()
        width = sum(size for _, size in columns)
        x = 0
        for title, size in columns:
            self.header.create_text(
                x + 12,
                23,
                text=title,
                fill="white",
                font=("Helvetica", 11, "bold"),
                anchor="w",
                width=size - 24,
            )
            x += size
        y = 0
        backgrounds = {
            "day_even": "white",
            "day_odd": "#edf4f8",
            "pause": "#e5f3f2",
            "gap": "#fff4dc",
        }
        for row in rows:
            if row.kind == "day":
                self.body.create_rectangle(0, y, width, y + 44, fill="#1f8a89", outline="")
                self.body.create_text(
                    12,
                    y + 22,
                    text=" · ".join(row.values[:2]),
                    fill="white",
                    font=("Helvetica", 12, "bold"),
                    anchor="w",
                )
                y += 44
                continue
            background = backgrounds.get(row.kind, "white")
            texts = []
            x, height = 0, 54
            for index, (value, (_, size)) in enumerate(zip(row.values, columns)):
                if row.span_from is not None and index > row.span_from:
                    break
                merged = index == row.span_from
                if merged:
                    size = sum(column_width for _, column_width in columns[index:])
                item = self.body.create_text(
                    x + size / 2 if merged else x + 12,
                    y + 12,
                    text=value,
                    width=size - 24,
                    anchor="n" if merged else "nw",
                    justify="center" if merged else "left",
                    font=("Helvetica", 11),
                    fill="#20313d",
                )
                bounds = self.body.bbox(item)
                height = max(height, bounds[3] - y + 12)
                subject = row.subjects[index] if index < len(row.subjects) else None
                texts.append((item, x, size, subject))
                x += size
            for item, x, size, subject in texts:
                rectangle = self.body.create_rectangle(
                    x, y, x + size, y + height, fill=background, outline="#d5dfe3"
                )
                self.body.tag_lower(rectangle, item)
                self.cells.append((rectangle, item, subject, background))
                if subject is not None:
                    self._subjects_by_item[rectangle] = subject
                    self._subjects_by_item[item] = subject
            y += height
        self.header.configure(scrollregion=(0, 0, width, 46))
        self.body.configure(scrollregion=(0, 0, width, y))
        self.body.yview_moveto(0)
        self.set_subject(self.selected_subject)
