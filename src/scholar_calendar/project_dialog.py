"""Project chooser styled like the app; no files are written by the dialog."""

import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk

from .project_file import load_project
from .theme import PAPER


class ProjectDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        save: bool,
        initial_path: Path | None = None,
        has_schedule: bool = False,
    ) -> None:
        super().__init__(parent)
        self.withdraw()
        self.transient(parent)
        self.save_mode = save
        self.result: str | None = None
        self.folder = Path.cwd()
        self.paths: dict[str, Path] = {}
        self.location = tk.StringVar()
        self.filename = tk.StringVar(
            value=initial_path.name if initial_path and save else "centro.json" if save else ""
        )
        self.search = tk.StringVar()
        self.info = tk.StringVar(
            value="Selecciona un archivo para consultar su contenido."
            if not save
            else "Se guardarán la configuración y el horario generado."
            if has_schedule
            else "Se guardará la configuración del centro."
        )
        self.error = tk.StringVar()
        action = "Guardar" if save else "Cargar"
        self.title(f"{action} proyecto · Scholar Calendar")
        self.configure(background=PAPER)
        self.minsize(780, 540)
        heading = ttk.Frame(self, padding=(24, 18))
        heading.pack(fill=tk.X)
        ttk.Label(heading, text=f"{action} proyecto", style="Section.TLabel").pack(anchor=tk.W)
        ttk.Label(
            heading,
            text="Configuración y horarios de tu centro, en un archivo.",
            style="Muted.TLabel",
        ).pack(anchor=tk.W, pady=(6, 0))
        footer = ttk.Frame(self, padding=(24, 14))
        footer.pack(side=tk.BOTTOM, fill=tk.X)
        ttk.Label(footer, textvariable=self.error, foreground="#a13b34", wraplength=640).pack(
            anchor=tk.W, pady=(0, 6)
        )
        self.accept_button = ttk.Button(
            footer, text=action, style="Accent.TButton", command=self._accept
        )
        self.accept_button.pack(side=tk.RIGHT)
        ttk.Button(footer, text="Cancelar", command=self.destroy).pack(side=tk.RIGHT, padx=10)
        body = ttk.Frame(self, style="App.TFrame", padding=(24, 16))
        body.pack(fill=tk.BOTH, expand=True)
        navigation = ttk.Frame(body, padding=12)
        navigation.pack(fill=tk.X, pady=(0, 12))
        ttk.Button(
            navigation, text="↑ Subir", command=lambda: self._navigate(self.folder.parent)
        ).pack(side=tk.LEFT)
        location_entry = ttk.Entry(navigation, textvariable=self.location)
        location_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        location_entry.bind(
            "<Return>", lambda _event: self._navigate(Path(self.location.get()).expanduser())
        )
        ttk.Button(
            navigation,
            text="Ir",
            command=lambda: self._navigate(Path(self.location.get()).expanduser()),
        ).pack(side=tk.RIGHT)
        browser = ttk.Frame(body)
        browser.pack(fill=tk.BOTH, expand=True)
        places = ttk.Frame(browser, padding=12)
        places.pack(side=tk.LEFT, fill=tk.Y)
        ttk.Label(places, text="Ubicaciones", style="Muted.TLabel").pack(anchor=tk.W, pady=(0, 10))
        for title, path in (
            ("Proyecto", Path.cwd()),
            ("Documentos", Path.home() / "Documents"),
            ("Inicio", Path.home()),
        ):
            ttk.Button(places, text=title, command=lambda path=path: self._navigate(path)).pack(
                fill=tk.X, pady=4
            )
        files = ttk.Frame(browser, padding=12)
        files.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        filter_row = ttk.Frame(files)
        filter_row.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(filter_row, text="Buscar", style="Muted.TLabel").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Entry(filter_row, textvariable=self.search).pack(side=tk.LEFT, fill=tk.X, expand=True)
        table = ttk.Frame(files)
        table.pack(fill=tk.BOTH, expand=True)
        self.tree = ttk.Treeview(
            table,
            columns=("name", "kind", "modified"),
            show="headings",
            selectmode="browse",
            height=8,
        )
        for key, title, width in (
            ("name", "Nombre", 240),
            ("kind", "Tipo", 90),
            ("modified", "Modificado", 135),
        ):
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, minwidth=60, stretch=key == "name")
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll = ttk.Scrollbar(table, command=self.tree.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.bind("<<TreeviewSelect>>", self._selected)
        self.tree.bind("<Double-1>", self._activate)
        self.tree.bind("<Return>", self._activate)
        self.info_label = ttk.Label(
            files, textvariable=self.info, style="Muted.TLabel", wraplength=500
        )
        self.info_label.pack(side=tk.BOTTOM, before=table, fill=tk.X, pady=(10, 0))
        files.bind("<Configure>", lambda event: self._wrap_info(event.width))
        if save:
            name_row = ttk.Frame(body, padding=12)
            name_row.pack(side=tk.BOTTOM, before=browser, fill=tk.X, pady=(12, 0))
            ttk.Label(name_row, text="Nombre del archivo", style="Muted.TLabel").pack(
                side=tk.LEFT, padx=(0, 12)
            )
            self.name_entry = ttk.Entry(name_row, textvariable=self.filename)
            self.name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.name_entry.bind("<Return>", lambda _event: self._accept())
        self.search.trace_add("write", lambda *_: self._list_files())
        self.bind("<Escape>", lambda _event: self.destroy())
        width = min(980, parent.winfo_screenwidth() - 80)
        height = min(700, parent.winfo_screenheight() - 100)
        self.geometry(
            f"{width}x{height}+{max(0, (parent.winfo_screenwidth() - width) // 2)}+{max(0, (parent.winfo_screenheight() - height) // 2)}"
        )
        initial_folder = initial_path.parent if initial_path else Path.cwd()
        self._navigate(initial_folder if initial_folder.is_dir() else Path.cwd())
        self.deiconify()

    def _wrap_info(self, width: int) -> None:
        self.info_label.configure(wraplength=max(200, width - 24))

    def _navigate(self, folder: Path) -> None:
        try:
            folder = folder.resolve()
            if not folder.is_dir():
                raise ValueError("La ubicación no es una carpeta.")
            list(folder.iterdir())  # Keep the current folder if access is denied.
        except (OSError, ValueError) as error:
            self.error.set(str(error))
            return
        self.folder = folder
        self.location.set(str(folder))
        self.error.set("")
        self.search.set("")

    def _list_files(self) -> None:
        self.tree.delete(*self.tree.get_children())
        self.paths.clear()
        query = self.search.get().casefold()
        try:
            entries = [
                path
                for path in self.folder.iterdir()
                if not path.name.startswith(".")
                and query in path.name.casefold()
                and (path.is_dir() or path.suffix.lower() == ".json")
            ]
            entries.sort(key=lambda path: (not path.is_dir(), path.name.casefold()))
            for path in entries:
                try:
                    modified = datetime.fromtimestamp(path.stat().st_mtime).strftime(
                        "%d/%m/%Y %H:%M"
                    )
                except OSError:
                    modified = "—"
                item = self.tree.insert(
                    "", tk.END, values=(path.name, "Carpeta" if path.is_dir() else "JSON", modified)
                )
                self.paths[item] = path
            if not self.save_mode:
                self.info.set(
                    "Selecciona un proyecto. Doble clic para abrir una carpeta o cargar un archivo."
                    if entries
                    else "No hay archivos JSON en esta carpeta con ese nombre."
                )
                self.accept_button.state(["disabled"])
        except OSError as error:
            self.error.set(str(error))

    def _selected_path(self) -> Path | None:
        selection = self.tree.selection()
        return self.paths.get(selection[0]) if selection else None

    def _selected(self, _event=None) -> None:
        path = self._selected_path()
        self.error.set("")
        if path is None or path.is_dir():
            if not self.save_mode:
                self.accept_button.state(["disabled"])
            return
        if self.save_mode:
            self.filename.set(path.name)
            return
        try:
            project = load_project(path)
            planning = project.planning
            self.info.set(
                f"{planning.course_name or 'Centro sin nombre'} · {len(planning.classrooms)} aulas · {len(planning.subjects)} asignaturas · {len(planning.teachers)} profesores\n"
                + (
                    "Incluye horario generado."
                    if project.schedule is not None
                    else "Solo configuración, sin horario generado."
                )
            )
            self.accept_button.state(["!disabled"])
        except (OSError, ValueError) as error:
            self.info.set(
                "Este archivo no es un proyecto o una configuración válida de Scholar Calendar."
            )
            self.error.set(str(error))
            self.accept_button.state(["disabled"])

    def _activate(self, _event=None) -> str:
        path = self._selected_path()
        if path is not None and path.is_dir():
            self._navigate(path)
        elif not self.save_mode:
            self._accept()
        return "break"

    def _accept(self) -> None:
        if self.save_mode:
            name = self.filename.get().strip()
            if not name or name in (".", "..") or "/" in name or "\\" in name:
                self.error.set(
                    "Escribe un nombre de archivo; usa la barra superior para cambiar de carpeta."
                )
                return
            if not name.lower().endswith(".json"):
                name += ".json"
            path = self.folder / name
            if path.is_dir():
                self.error.set("Ya existe una carpeta con ese nombre.")
                return
            if path.exists() and not messagebox.askyesno(
                "Reemplazar proyecto", f"Ya existe «{name}». ¿Quieres reemplazarlo?", parent=self
            ):
                return
        else:
            path = self._selected_path()
            if path is None or path.is_dir() or self.accept_button.instate(["disabled"]):
                return
        self.result = str(path)
        self.destroy()


def ask_project_path(
    parent: tk.Misc, *, save: bool, initial_path: Path | None = None, has_schedule: bool = False
) -> str | None:
    dialog = ProjectDialog(parent, save=save, initial_path=initial_path, has_schedule=has_schedule)
    dialog.wait_visibility()
    dialog.grab_set()
    dialog.focus_set()
    parent.wait_window(dialog)
    return dialog.result
