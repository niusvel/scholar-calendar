"""Shared application palette and ttk styles."""

import tkinter as tk
from tkinter import ttk

NAVY = "#172a3a"
INK = "#20313d"
TEAL = "#1f8a89"
PALE_TEAL = "#e5f3f2"
PAPER = "#f3f6f9"
MUTED = "#60727d"
LINE = "#d5dfe3"


def configure_styles(root: tk.Tk) -> None:
    style = ttk.Style(root)
    style.theme_use("clam")
    root.option_add("*Listbox.font", ("Helvetica", 11))
    root.option_add("*Listbox.exportSelection", False)
    style.configure(".", font=("Helvetica", 11), foreground=INK)
    style.configure("TFrame", background="white")
    style.configure("TLabel", background="white")
    style.configure("App.TFrame", background=PAPER)
    style.configure("Warning.TFrame", background="#fff4dc")
    style.configure("Warning.TLabel", background="#fff4dc", foreground="#805d19")
    style.configure("Card.TFrame", background="white")
    style.configure("Header.TFrame", background="white")
    style.configure(
        "Title.TLabel", background="white", foreground=NAVY, font=("Helvetica", 20, "bold")
    )
    style.configure("Subtitle.TLabel", background="white", foreground=MUTED, font=("Helvetica", 11))
    style.configure(
        "Section.TLabel", background="white", foreground=INK, font=("Helvetica", 14, "bold")
    )
    style.configure("Muted.TLabel", background="white", foreground=MUTED, font=("Helvetica", 11))
    style.configure("Status.TLabel", background=PAPER, foreground=MUTED, font=("Helvetica", 11))
    style.configure("TButton", background="white", foreground=INK, padding=(12, 8), borderwidth=0)
    style.configure(
        "TMenubutton", background="white", foreground=INK, padding=(12, 8), borderwidth=0
    )
    style.configure(
        "Accent.TButton",
        background="white",
        foreground="white",
        padding=(18, 10),
        font=("Helvetica", 11, "bold"),
    )
    style.configure("Danger.TButton", background="white", foreground="#a13b34", padding=(12, 8))
    style.configure(
        "TCheckbutton",
        background="white",
        padding=(4, 5),
        indicatorbackground="white",
        upperbordercolor=LINE,
        lowerbordercolor=LINE,
    )
    style.map(
        "TCheckbutton",
        indicatorbackground=[("selected", TEAL)],
        indicatorforeground=[("selected", "white")],
        upperbordercolor=[("focus", TEAL)],
        lowerbordercolor=[("focus", TEAL)],
    )
    style.configure("TNotebook", background=PAPER, borderwidth=0, tabmargins=(0, 0, 0, 14))
    style.configure(
        "TNotebook.Tab",
        background=PAPER,
        foreground=MUTED,
        padding=(18, 10),
        borderwidth=0,
        font=("Helvetica", 11, "bold"),
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", "white"), ("active", PALE_TEAL)],
        foreground=[("selected", TEAL)],
        padding=[("selected", (18, 10)), ("!selected", (18, 10))],
        expand=[("selected", (0, 0, 0, 0))],
        lightcolor=[("selected", "white"), ("!selected", PAPER)],
        darkcolor=[("selected", "white"), ("!selected", PAPER)],
    )
    style.configure(
        "Treeview",
        background="white",
        fieldbackground="white",
        foreground=INK,
        rowheight=34,
        bordercolor=LINE,
        borderwidth=0,
    )
    style.configure(
        "Treeview.Heading",
        background="#f0f5f8",
        foreground=INK,
        font=("Helvetica", 10, "bold"),
        padding=(10, 8),
        relief="flat",
    )
    style.map("Treeview", background=[("selected", "#d8eeed")], foreground=[("selected", INK)])
    style.map("Treeview.Heading", background=[("active", "#dae5eb")])
    for widget in ("TEntry", "TSpinbox", "TCombobox"):
        style.configure(
            widget,
            padding=7,
            borderwidth=1,
            relief="flat",
            bordercolor=LINE,
            lightcolor="white",
            darkcolor="white",
            fieldbackground="white",
            background="#edf2f5",
            arrowcolor=MUTED,
            arrowsize=13,
            insertcolor=INK,
            insertwidth=2,
        )
        style.map(
            widget,
            bordercolor=[("focus", TEAL), ("!focus", LINE)],
            lightcolor=[("focus", TEAL), ("!focus", "white")],
            darkcolor=[("focus", TEAL), ("!focus", "white")],
        )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", "white")],
        selectbackground=[("readonly", "white")],
        selectforeground=[("readonly", INK)],
    )

    style.configure("TSeparator", background="#e6edf1")
    style.configure("Treeview.Heading", borderwidth=0, lightcolor="#f0f5f8", darkcolor="#f0f5f8")
    root.option_add("*Listbox.highlightThickness", 1)
    root.option_add("*Listbox.highlightBackground", LINE)
    root.option_add("*Listbox.highlightColor", TEAL)
    root.option_add("*Listbox.selectBorderWidth", 0)
    root.option_add("*Listbox.activeStyle", "none")
    _modern_surfaces(root, style)
    style.layout(
        "Icon.TMenubutton",
        [
            (
                "Modern.button",
                {
                    "sticky": "nsew",
                    "children": [
                        (
                            "Menubutton.padding",
                            {
                                "sticky": "nsew",
                                "children": [("Menubutton.label", {"sticky": "nsew"})],
                            },
                        )
                    ],
                },
            )
        ],
    )


def _rounded_image(root: tk.Tk, fill: str, border: str, size: int = 20) -> tk.PhotoImage:
    """A stretchable Tk image keeps rounded controls native and dependency-free."""
    radius = min(7, size // 2 - 1)
    image = tk.PhotoImage(master=root, width=size, height=size)
    for y in range(size):
        pixels = []
        start = None
        for x in range(size):
            dx = max(radius - x, 0, x - (size - radius - 1))
            dy = max(radius - y, 0, y - (size - radius - 1))
            if dx * dx + dy * dy <= radius * radius:
                edge = (
                    x in (0, size - 1)
                    or y in (0, size - 1)
                    or dx * dx + dy * dy > (radius - 1) ** 2
                )
                if start is None:
                    start = x
                pixels.append(border if edge else fill)
        if pixels:
            image.put("{" + " ".join(pixels) + "}", (start, y))
    return image


def _surface_element(
    root: tk.Tk, style: ttk.Style, name: str, colors: list[tuple[str, str, str]], size: int = 32
) -> None:
    images = [_rounded_image(root, fill, border, size) for _, fill, border in colors]
    root._theme_images.extend(images)
    states = [(state, image) for (state, _, _), image in zip(colors[1:], images[1:])]
    style.element_create(
        name, "image", images[0], *states, border=min(8, size // 2 - 1), sticky="nsew"
    )


def _modern_surfaces(root: tk.Tk, style: ttk.Style) -> None:
    root._theme_images = []
    for prefix, normal, hover, pressed, foreground in (
        ("", "#edf2f5", "#e2eaef", "#d5e2e8", INK),
        ("Accent.", TEAL, "#197776", "#146563", "white"),
        ("Danger.", "#fff0ed", "#fce3df", "#f8cbc4", "#a13b34"),
    ):
        name = prefix + "Modern.button"
        _surface_element(
            root,
            style,
            name,
            [
                ("", normal, normal),
                ("disabled", "#edf1f4", "#edf1f4"),
                ("pressed", pressed, pressed),
                ("focus", normal, "#247e91"),
                ("active", hover, hover),
            ],
        )
        style.layout(
            prefix + "TButton",
            [
                (
                    name,
                    {
                        "sticky": "nsew",
                        "children": [
                            (
                                "Button.padding",
                                {
                                    "sticky": "nsew",
                                    "children": [("Button.label", {"sticky": "nsew"})],
                                },
                            )
                        ],
                    },
                )
            ],
        )
        style.map(
            prefix + "TButton",
            foreground=[("disabled", "#8997a1"), ("!disabled", foreground)],
            # Clam's inherited state colors otherwise fill the transparent corners.
            background=[("disabled", "white"), ("!disabled", "white")],
        )
    style.map("TMenubutton", background=[("disabled", "white"), ("!disabled", "white")])
    style.layout(
        "TMenubutton",
        [
            (
                "Modern.button",
                {
                    "sticky": "nsew",
                    "children": [
                        (
                            "Menubutton.padding",
                            {
                                "sticky": "nsew",
                                "children": [
                                    ("Menubutton.indicator", {"side": "right", "sticky": ""}),
                                    ("Menubutton.label", {"side": "left", "sticky": ""}),
                                ],
                            },
                        )
                    ],
                },
            )
        ],
    )
    # A large center avoids thousands of tiny image tiles on wide cards in Tk/macOS.
    _surface_element(root, style, "Modern.card", [("", "white", "#e1e8ed")], size=96)
    style.layout("Surface.TFrame", [("Modern.card", {"sticky": "nsew"})])
    style.configure("Surface.TFrame", background=PAPER)
    _surface_element(
        root,
        style,
        "Modern.tab",
        [
            ("", PAPER, PAPER),
            ("focus", "white", TEAL),
            ("selected", "white", "#dce6ea"),
            ("active", PALE_TEAL, PALE_TEAL),
        ],
    )
    style.layout(
        "TNotebook.Tab",
        [
            (
                "Modern.tab",
                {
                    "sticky": "nsew",
                    "children": [
                        (
                            "Notebook.padding",
                            {
                                "sticky": "nsew",
                                "children": [("Notebook.label", {"sticky": "nsew"})],
                            },
                        )
                    ],
                },
            )
        ],
    )
    style.layout("TNotebook", [("Notebook.client", {"sticky": "nsew"})])
    style.configure("TNotebook", bordercolor=PAPER, lightcolor=PAPER, darkcolor=PAPER)
    image = tk.PhotoImage(master=root, width=256, height=1)
    image.put("#e6edf1", (0, 0, 256, 1))
    root._theme_images.append(image)
    style.element_create("Modern.separator", "image", image, width=1, sticky="nsew")
    style.layout("TSeparator", [("Modern.separator", {"sticky": "nsew"})])
    _surface_element(
        root,
        style,
        "Modern.Scrollbar.thumb",
        [("", "#c3cfd7", "#c3cfd7"), ("pressed", TEAL, TEAL), ("active", "#91a5b2", "#91a5b2")],
        size=12,
    )
    for orientation in ("Vertical", "Horizontal"):
        style.layout(
            orientation + ".TScrollbar",
            [
                (
                    orientation + ".Scrollbar.trough",
                    {
                        "sticky": "nsew",
                        "children": [("Modern.Scrollbar.thumb", {"expand": "1", "sticky": "nsew"})],
                    },
                )
            ],
        )
        style.configure(
            orientation + ".TScrollbar",
            background=PAPER,
            troughcolor=PAPER,
            borderwidth=0,
            bordercolor=PAPER,
            lightcolor=PAPER,
            darkcolor=PAPER,
        )
