"""Right panel: execution buttons, options, script parameters and selection details."""

import os
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk

from . import theme

ICONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")


def _icon(name: str) -> ImageTk.PhotoImage:
    return ImageTk.PhotoImage(Image.open(os.path.join(ICONS_DIR, name)).resize((20, 20)))


class Sidebar:
    def __init__(self, parent, app):
        self.app = app
        settings = app.settings
        self.frame = ttk.Frame(parent, width=200, relief=tk.SUNKEN)

        self._build_buttons()
        ttk.Separator(self.frame, orient=tk.HORIZONTAL).pack(fill="x")

        self.graph_label = self._file_field("Graph:", app.open_graph_file)
        self.script_label = self._file_field("Script:", app.open_script_file)

        self.var_show_weight = tk.BooleanVar(value=settings.show_weight)
        self.var_animation = tk.BooleanVar(value=settings.animation)
        self.var_execution_time_log = tk.BooleanVar(value=settings.execution_time_log)
        self.var_bidirectional = tk.BooleanVar(value=True)
        self._checkbox("Show Weight:", self.var_show_weight, self._on_show_weight)
        self._checkbox("Animation:", self.var_animation, self._on_animation)
        self._checkbox("Exec time log:", self.var_execution_time_log, self._on_execution_time_log)
        self._checkbox("Bidirectional:", self.var_bidirectional, app.on_bidirectional_change)
        self._build_speed()
        self._build_log_symbols()

        ttk.Separator(self.frame, orient=tk.HORIZONTAL).pack(fill="x")
        bottom = ttk.Frame(self.frame)
        bottom.pack(fill="both", expand=True, padx=2)
        self.script_properties_frame = ttk.Frame(bottom)
        self.script_properties_frame.pack(fill="x", anchor="nw", padx=5, pady=(0, 5))
        ttk.Separator(bottom, orient=tk.HORIZONTAL).pack(fill="x")
        details = ttk.Frame(bottom)
        details.pack(fill="both", anchor="nw", expand=True, padx=2)
        self._build_vertex_details(details)
        self._build_edge_details(details)
        self.hide_details()

    # -------------------------
    # Building blocks
    # -------------------------
    def _build_buttons(self) -> None:
        bar = tk.Frame(self.frame)
        bar.pack(fill=tk.X, padx=2)
        app = self.app
        # Keep references to the images, or Tk discards them.
        self.icons = {
            "play": _icon("circle-play-regular.png"),
            "pause": _icon("circle-pause-regular.png"),
            "stop": _icon("circle-stop-regular.png"),
            "clear": _icon("rotate-solid.png"),
            "debug": _icon("circle-debug-regular.png"),
        }
        actions = [
            ("play", app.event_play),
            ("pause", app.event_pause),
            ("stop", app.event_stop),
            ("clear", app.event_clear),
            ("debug", app.event_debug),
        ]
        for name, command in actions:
            ttk.Button(bar, image=self.icons[name], command=command).pack(
                side=tk.LEFT, padx=5, pady=5
            )

    def _row(self, label: str, pady=0) -> ttk.Frame:
        row = ttk.Frame(self.frame)
        row.pack(fill="x", padx=10, pady=pady)
        tk.Label(row, text=label).pack(side="left")
        return row

    def _file_field(self, label: str, on_click) -> tk.Label:
        row = self._row(label, pady=5)
        field = tk.Label(row, text="Click here", relief="sunken", width=20, anchor="w")
        field.pack(side="right", fill="x")
        field.bind("<Button-1>", lambda event: on_click())
        return field

    def _checkbox(self, label: str, variable, command) -> None:
        row = self._row(label)
        tk.Checkbutton(row, variable=variable, onvalue=True, offvalue=False,
                       command=command).pack(side="right")

    def _build_speed(self) -> None:
        row = self._row("Speed:")
        self.var_speed = tk.IntVar(value=self.app.settings.speed)
        self.scale_speed = tk.Scale(
            row, from_=1, to=10, variable=self.var_speed, orient="horizontal",
            length=150, showvalue=False, command=self._on_speed,
        )
        self.scale_speed.pack(side="right", fill="x")
        self.speed_value = tk.Label(row, text=str(self.var_speed.get()))
        self.speed_value.pack(side="right", padx=1)

    def _build_log_symbols(self) -> None:
        row = self._row("Logs Symbols:", pady=5)
        self.var_logs_symbols = tk.StringVar(value=self.app.settings.logs_symbols)
        entry = ttk.Entry(row, textvariable=self.var_logs_symbols)
        entry.bind("<KeyRelease>", self._on_log_symbols)
        entry.pack(side="right", fill="x")

    def _detail_field(self, parent, label: str, readonly: bool) -> ttk.Entry:
        row = ttk.Frame(parent)
        row.pack(fill="x", padx=5, pady=2)
        tk.Label(row, text=label).pack(side="left")
        entry = ttk.Entry(row, state="readonly" if readonly else "normal")
        entry.pack(side="right", fill="x")
        return entry

    def _build_vertex_details(self, parent) -> None:
        self.vertex_frame = ttk.Frame(parent)
        tk.Label(self.vertex_frame, text="Vertex Settings", font=theme.FONT_TITLE,
                 anchor="w").pack(anchor="w", pady=2)
        self.vertex_id = self._detail_field(self.vertex_frame, "ID:", readonly=True)
        self.vertex_name = self._detail_field(self.vertex_frame, "Name:", readonly=False)
        self.vertex_name.bind("<KeyRelease>", self._on_vertex_name)

    def _build_edge_details(self, parent) -> None:
        self.edge_frame = ttk.Frame(parent)
        tk.Label(self.edge_frame, text="Edge Settings", font=theme.FONT_TITLE,
                 anchor="w").pack(anchor="w", pady=2)
        self.edge_id = self._detail_field(self.edge_frame, "ID:", readonly=True)
        self.edge_weight = self._detail_field(self.edge_frame, "Weight:", readonly=False)
        self.edge_weight.bind("<KeyRelease>", self._on_edge_weight)

    # -------------------------
    # Selection details
    # -------------------------
    @staticmethod
    def _set_entry(entry: ttk.Entry, value, readonly: bool) -> None:
        entry.config(state="normal")
        entry.delete(0, tk.END)
        entry.insert(0, value)
        if readonly:
            entry.config(state="readonly")

    def hide_details(self) -> None:
        self.vertex_frame.pack_forget()
        self.edge_frame.pack_forget()

    def show_vertex(self, view) -> None:
        self.hide_details()
        self._set_entry(self.vertex_id, view.id, readonly=True)
        self._set_entry(self.vertex_name, view.model.name, readonly=False)
        self.vertex_frame.pack(fill="x", padx=10, pady=5)

    def show_edge(self, view) -> None:
        self.hide_details()
        self._set_entry(self.edge_id, view.id, readonly=True)
        self._set_entry(self.edge_weight, view.model.weight, readonly=False)
        self.edge_frame.pack(fill="x", padx=10, pady=5)

    def set_graph_name(self, name: str) -> None:
        self.graph_label.config(text=name)

    def set_script_name(self, name: str) -> None:
        self.script_label.config(text=name)

    # -------------------------
    # Events
    # -------------------------
    def _on_vertex_name(self, event) -> None:
        if self.app.selected:
            self.app.selected.set_name(self.vertex_name.get())

    def _on_edge_weight(self, event) -> None:
        text = self.edge_weight.get()
        if not self.app.selected_edge:
            return
        try:
            self.app.selected_edge.set_weight(float(text), text)
        except ValueError:
            pass  # incomplete number while typing; keep the old weight

    def _on_show_weight(self) -> None:
        self.app.settings.show_weight = self.var_show_weight.get()
        self.app.save_settings()
        self.app.draw()

    def _on_animation(self) -> None:
        self.app.settings.animation = self.var_animation.get()
        self.app.save_settings()

    def _on_execution_time_log(self) -> None:
        self.app.settings.execution_time_log = self.var_execution_time_log.get()
        self.app.save_settings()

    def _on_speed(self, value) -> None:
        self.app.settings.speed = int(value)
        self.speed_value.config(text=str(int(value)))
        self.app.save_settings()

    def _on_log_symbols(self, event) -> None:
        self.app.settings.logs_symbols = self.var_logs_symbols.get()
        self.app.save_settings()
