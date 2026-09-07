"""A bounded, scrollable note that leaves space for the timetable."""

import tkinter as tk
from tkinter import font, ttk

NOTE_BACKGROUND = "#fff8dc"
NOTE_BORDER = "#c6a752"
NOTE_INK = "#665321"


class RestrictionNote(ttk.Frame):
    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, style="Card.TFrame")
        self.border = tk.Canvas(self, background="white", highlightthickness=0, height=92)
        self.border.pack(fill=tk.X)
        self.outline = self.border.create_rectangle(
            2, 2, 10, 10, fill=NOTE_BACKGROUND, outline=NOTE_BORDER, width=1, dash=(5, 3)
        )
        self.content = tk.Text(
            self.border,
            wrap="word",
            background=NOTE_BACKGROUND,
            foreground=NOTE_INK,
            font=("Helvetica", 11),
            relief=tk.FLAT,
            borderwidth=0,
            highlightthickness=0,
            padx=0,
            pady=0,
            state="disabled",
            cursor="arrow",
            takefocus=False,
        )
        self.scrollbar = ttk.Scrollbar(self.border, orient=tk.VERTICAL, command=self.content.yview)
        self.content.configure(yscrollcommand=self.scrollbar.set)
        self.border.bind("<Configure>", self._layout)

    def _layout(self, event: tk.Event) -> None:
        self.border.coords(self.outline, 2, 2, event.width - 2, event.height - 2)
        self.content.place(x=14, y=10, width=max(1, event.width - 46), height=event.height - 20)
        self.scrollbar.place(x=event.width - 26, y=10, width=14, height=event.height - 20)

    def set_lines(self, lines: tuple[str, ...], *, title: str) -> None:
        text = title + "\n" + "\n".join(f"• {line}" for line in lines)
        self.content.configure(state="normal")
        self.content.delete("1.0", tk.END)
        self.content.insert("1.0", text)
        self.content.tag_configure("title", font=("Helvetica", 11, "bold"))
        self.content.tag_add("title", "1.0", "1.end")
        self.content.configure(state="disabled")
        self.content.yview_moveto(0)
        line_height = font.Font(font=self.content.cget("font")).metrics("linespace")
        self.border.configure(height=min(5, max(3, len(lines) + 1)) * line_height + 24)
