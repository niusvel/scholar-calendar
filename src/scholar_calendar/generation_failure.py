"""Readable, scrollable explanation of conflicting scheduling settings."""

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

from .generation_diagnostics import ConfigurationConflict
from .theme import INK, MUTED, PAPER, TEAL


class GenerationFailure(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Tk,
        summary: str,
        conflicts: tuple[ConfigurationConflict, ...],
        on_review: Callable[[], None],
    ) -> None:
        super().__init__(parent)
        self.withdraw()
        self.transient(parent)
        self.title("Revisar configuración · Scholar Calendar")
        self.configure(background=PAPER)
        self.minsize(600, 400)
        header = ttk.Frame(self, padding=(24, 20))
        header.pack(fill=tk.X)
        ttk.Label(header, text="No se puede generar este horario", style="Section.TLabel").pack(
            anchor=tk.W
        )
        footer = ttk.Frame(self, padding=(24, 16))
        footer.pack(side=tk.BOTTOM, fill=tk.X)
        ttk.Button(footer, text="Cerrar", command=self.destroy).pack(side=tk.RIGHT)

        def review():
            self.destroy()
            on_review()

        self.review_button = ttk.Button(
            footer, text="Revisar configuración", style="Accent.TButton", command=review
        )
        self.review_button.pack(side=tk.LEFT)
        body = ttk.Frame(self)
        body.pack(fill=tk.BOTH, expand=True, padx=24)
        self.content = tk.Text(
            body,
            wrap=tk.WORD,
            background="white",
            foreground=INK,
            font=("Helvetica", 12),
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            padx=20,
            pady=18,
            cursor="arrow",
        )
        scrollbar = ttk.Scrollbar(body, command=self.content.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.content.configure(yscrollcommand=scrollbar.set)
        self.content.pack(fill=tk.BOTH, expand=True)
        self.content.tag_configure("intro", foreground=MUTED, spacing3=18)
        self.content.tag_configure(
            "heading", foreground=TEAL, font=("Helvetica", 12, "bold"), spacing1=8, spacing3=6
        )
        self.content.tag_configure("body", spacing3=6)
        self.content.tag_configure("section", foreground=MUTED, spacing3=18)
        self.content.insert(tk.END, summary + "\n", "intro")
        for index, conflict in enumerate(conflicts, start=1):
            self.content.insert(tk.END, f"{index}. {conflict.title}\n", "heading")
            self.content.insert(tk.END, conflict.detail + "\n", "body")
            self.content.insert(tk.END, "Revisar: " + conflict.section + ".\n", "section")
        self.content.configure(state=tk.DISABLED)
        self.bind("<Escape>", lambda _event: self.destroy())
        width = min(840, parent.winfo_screenwidth() - 80)
        height = min(700, parent.winfo_screenheight() - 100)
        x = max(0, (parent.winfo_screenwidth() - width) // 2)
        y = max(0, (parent.winfo_screenheight() - height) // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.deiconify()
        self.grab_set()
        self.focus_set()
