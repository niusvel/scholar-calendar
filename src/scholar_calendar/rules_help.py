"""User-facing explanation of the rules implemented in solver.py and the school clock."""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .rules_catalog import RULE_SECTIONS
from .theme import INK, MUTED, PAPER, TEAL


class RulesHelp(tk.Toplevel):
    def __init__(self, parent: tk.Tk) -> None:
        super().__init__(parent)
        self.withdraw()
        self.transient(parent)
        self.title("Reglas de generación · Scholar Calendar")
        self.configure(background=PAPER)
        self.minsize(620, 460)
        header = ttk.Frame(self, padding=(24, 18))
        header.pack(fill=tk.X)
        ttk.Label(header, text="Cómo se genera el horario", style="Section.TLabel").pack(
            anchor=tk.W
        )
        ttk.Label(
            header, text="Consulta las reglas del motor y cuándo se aplican.", style="Muted.TLabel"
        ).pack(anchor=tk.W, pady=(6, 0))
        footer = ttk.Frame(self, padding=(24, 12))
        footer.pack(side=tk.BOTTOM, fill=tk.X)
        ttk.Button(footer, text="Cerrar", command=self.destroy).pack(side=tk.RIGHT)
        self.export_button = ttk.Button(
            footer, text="Exportar PDF", style="Accent.TButton", command=self._export_pdf
        )
        self.export_button.pack(side=tk.LEFT)
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=24, pady=16)
        for title, introduction, rules in RULE_SECTIONS:
            page = ttk.Frame(self.notebook)
            self.notebook.add(page, text=title)
            content = tk.Text(
                page,
                wrap=tk.WORD,
                background="white",
                foreground=INK,
                font=("Helvetica", 12),
                relief="flat",
                borderwidth=0,
                highlightthickness=0,
                padx=18,
                pady=16,
                cursor="arrow",
            )
            scrollbar = ttk.Scrollbar(page, command=content.yview)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            content.configure(yscrollcommand=scrollbar.set)
            content.pack(fill=tk.BOTH, expand=True)
            content.tag_configure("intro", foreground=MUTED, spacing3=16)
            content.tag_configure(
                "heading", foreground=TEAL, font=("Helvetica", 12, "bold"), spacing1=8, spacing3=4
            )
            content.tag_configure("body", spacing3=12)
            content.insert(tk.END, introduction + "\n", "intro")
            for heading, body in rules:
                content.insert(tk.END, heading + "\n", "heading")
                content.insert(tk.END, body + "\n", "body")
            content.configure(state=tk.DISABLED)
        self.bind("<Escape>", lambda _event: self.destroy())
        width = min(860, parent.winfo_screenwidth() - 80)
        height = min(740, parent.winfo_screenheight() - 100)
        x = max(0, (parent.winfo_screenwidth() - width) // 2)
        y = max(0, (parent.winfo_screenheight() - height) // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _export_pdf(self) -> None:
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Exportar reglas a PDF",
            initialfile="reglas-de-generacion.pdf",
            defaultextension=".pdf",
            filetypes=(("Documento PDF", "*.pdf"),),
        )
        if not path:
            return
        try:
            from .rules_pdf import export_rules_pdf

            export_rules_pdf(path)
        except (ImportError, OSError, ValueError) as error:
            messagebox.showerror("No se pudieron exportar las reglas", str(error), parent=self)
            return
        messagebox.showinfo(
            "Reglas exportadas", "El PDF de las reglas se ha guardado.", parent=self
        )
