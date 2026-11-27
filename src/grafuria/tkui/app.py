"""
Main window of the Tkinter interface.

The App connects the pieces: the graph model (core.graph), the canvas
views (VertexView, EdgeView), the side panel (Sidebar), the log
(LogPanel), and the script execution (ScriptRunner).
"""

import json
import os
import tkinter as tk
import webbrowser
from tkinter import messagebox, ttk
from tkinter.filedialog import askopenfilename, asksaveasfilename

from .. import __version__
from ..core import scripting
from ..core.graph import Graph
from ..core.settings import Settings
from . import theme
from .about import About
from .bridge import UiBridge
from .edge_view import EdgeView
from .log_panel import LogPanel, StatusBar
from .properties import Properties
from .runner import ScriptRunner
from .sidebar import Sidebar
from .vertex_view import VertexView

SETTINGS_FILE = "settings.json"
PROJECT_URL = "https://github.com/saulopz/grafuria"


class App(tk.Frame):
    """Main window: canvas with the graph, side panel and log."""

    VERTEX = 0
    EDGE = 1
    TITLE = "Grafuria"

    def __init__(self, master=None, filename: str = "", script: str = "",
                 settings_file: str = SETTINGS_FILE):
        super().__init__(master)
        self.settings_file = settings_file
        self.settings = Settings.load(settings_file)
        self.bridge = UiBridge(self)
        self.runner = ScriptRunner(self)
        self.graph = self._observe(Graph())
        self.filename = ""
        self.script = ""
        self.script_properties = None
        self.editing = True
        self.debug = False
        self.scale = 1.0
        self.selected = None  # selected VertexView
        self.selected_edge = None  # selected EdgeView

        self._build_window()
        self.bridge.start()

        if filename:
            self.load_graph_file(filename)
        if script:
            self.set_script(script)

    def destroy(self) -> None:
        """Stops the bridge and the script before the widgets go away."""
        self.runner.stop()
        self.bridge.stop()
        super().destroy()

    # -------------------------
    # Window
    # -------------------------
    def _build_window(self) -> None:
        root = self.master
        root.title(self.TITLE)
        root.geometry("1200x700")
        self._build_menu(root)

        paned = ttk.PanedWindow(root, orient="horizontal")
        paned.pack(fill="both", expand=True)
        paned.add(self._build_canvas(paned), weight=3)
        self.sidebar = Sidebar(paned, self)
        paned.add(self.sidebar.frame, weight=0)

        self.log_panel = LogPanel(root)
        self.status = StatusBar(root)

    def _build_menu(self, root) -> None:
        menu_bar = tk.Menu(root)
        root.config(menu=menu_bar)
        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="New", command=self.reset_canvas)
        file_menu.add_command(label="Open...", command=self.open_graph_file)
        file_menu.add_command(label="Save...", command=self.save_graph_file_dialog)
        file_menu.add_command(label="Save Log...", command=self.save_log_file)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=root.quit)
        help_menu = tk.Menu(menu_bar, tearoff=0)
        help_menu.add_command(label="Documentation", command=self.open_documentation)
        help_menu.add_command(label="About", command=lambda: About(root, __version__))
        menu_bar.add_cascade(label="File", menu=file_menu)
        menu_bar.add_cascade(label="Help", menu=help_menu)

    def _build_canvas(self, parent) -> ttk.Frame:
        frame = ttk.Frame(parent)
        self.canvas = tk.Canvas(frame, bg=theme.BG)
        scroll_y = tk.Scrollbar(frame, orient="vertical", command=self.canvas.yview)
        scroll_x = tk.Scrollbar(frame, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x.grid(row=1, column=0, sticky="ew")
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        self.canvas.bind("<Button-2>", self.on_canvas_middle_click)
        self.master.bind("<Delete>", self.delete_selected)
        self.canvas.bind("<MouseWheel>", self.zoom)  # Windows/macOS
        self.canvas.bind("<Button-4>", self.zoom)  # X11 wheel up
        self.canvas.bind("<Button-5>", self.zoom)  # X11 wheel down
        return frame

    def set_title(self, name: str = "") -> None:
        self.master.title(f"{self.TITLE} : {name}" if name else self.TITLE)

    # -------------------------
    # Settings
    # -------------------------
    def save_settings(self) -> None:
        try:
            self.settings.save(self.settings_file)
        except OSError as e:
            self.status.set(f"Could not save settings: {e}")

    # -------------------------
    # Graph model and views
    # -------------------------
    def _observe(self, graph: Graph) -> Graph:
        graph.listener = self._on_model_change
        return graph

    def _on_model_change(self, element) -> None:
        """Called by the model (any thread) when a state changes."""
        if self.settings.animation and element.view is not None:
            self.bridge.mark_dirty(element.view)

    @property
    def vertex(self) -> list:
        """Views of the vertices, in model order."""
        return [v.view for v in self.graph.vertex]

    @property
    def edge(self) -> list:
        """Views of the edges, in model order."""
        return [e.view for e in self.graph.edge]

    def _show_graph(self, graph: Graph) -> None:
        """Replaces the graph on the canvas."""
        self.clear_selection()
        self.canvas.delete("all")
        self.graph = self._observe(graph)
        self.sidebar.var_bidirectional.set(graph.bidirectional)
        for v in graph.vertex:
            VertexView(self, v)
        for e in graph.edge:
            EdgeView(self, e)
        self._raise_layers()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _raise_layers(self) -> None:
        self.canvas.tag_lower("edge")
        self.canvas.tag_raise("vertex")
        self.canvas.tag_raise("text")

    def draw(self) -> None:
        """Redraws every element from the model state."""
        for edge in self.edge:
            edge.draw()
        for vertex in self.vertex:
            vertex.draw()
        self._raise_layers()

    def draw_area(self, area) -> None:
        """Draws a closed polygon requested by a script (UI thread)."""
        if len(area) >= 3:
            self.canvas.create_polygon(
                *area, fill=theme.AREA_FILL, outline="black", tags="area"
            )
            self._raise_layers()

    # -------------------------
    # Editing
    # -------------------------
    def create_vertex(self, name: str, x: float, y: float) -> VertexView:
        return VertexView(self, self.graph.add_vertex(name, x, y))

    def create_edge(self, a, b, weight: float = 1) -> EdgeView:
        view = EdgeView(self, self.graph.add_edge(a, b, weight))
        self._raise_layers()
        return view

    def delete_vertex(self, view: VertexView) -> None:
        for edge in list(view.model.edge):
            self.delete_edge(edge.view)
        self.graph.remove_vertex(view.model)
        view.destroy()

    def delete_edge(self, view: EdgeView) -> None:
        self.graph.remove_edge(view.model)
        view.destroy()

    def select_vertex(self, view: VertexView) -> None:
        self.clear_selection()
        self.selected = view
        view.select()
        self.status.set(f"Vertex selected: {view.id}")
        self.sidebar.show_vertex(view)

    def select_edge(self, view: EdgeView) -> None:
        self.clear_selection()
        self.selected_edge = view
        view.select()
        self.status.set(f"Edge selected: {view.id}")
        self.sidebar.show_edge(view)

    def clear_selection(self) -> None:
        if self.selected is not None:
            self.selected.unselect()
            self.selected = None
        if self.selected_edge is not None:
            self.selected_edge.unselect()
            self.selected_edge = None
        self.sidebar.hide_details()

    def on_canvas_middle_click(self, event) -> None:
        """Middle click creates a vertex at the mouse position."""
        if self.editing:
            self.create_vertex("", self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))

    def delete_selected(self, event=None) -> None:
        """Delete key removes the selected vertex or edge."""
        if not self.editing:
            return
        if self.selected is not None:
            view, self.selected = self.selected, None
            self.delete_vertex(view)
        if self.selected_edge is not None:
            view, self.selected_edge = self.selected_edge, None
            self.delete_edge(view)
        self.sidebar.hide_details()

    def zoom(self, event) -> None:
        """Mouse wheel zooms around the pointer."""
        if event.num == 4 or getattr(event, "delta", 0) > 0:
            factor = 1.1
        elif event.num == 5 or getattr(event, "delta", 0) < 0:
            factor = 0.9
        else:
            return
        self.scale *= factor
        self.canvas.scale(
            "all", self.canvas.canvasx(event.x), self.canvas.canvasy(event.y), factor, factor
        )
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        s = self.scale
        for e in self.edge:
            self.canvas.itemconfig(e.canvas_id, arrowshape=(10 * s, 10 * s, 5 * s))

    def on_bidirectional_change(self) -> None:
        """Switches between directed and undirected drawing."""
        self.graph.bidirectional = self.sidebar.var_bidirectional.get()
        for e in self.edge:
            e.rebuild_line()
        self.draw()

    # -------------------------
    # Execution
    # -------------------------
    def event_play(self) -> None:
        if self.runner.running and self.runner.paused:
            self.runner.resume()
            return
        if self.runner.running:
            return
        if not self.script:
            self.show_error("You need a graph and an algorithm to run.")
            return
        self.event_clear()
        self.canvas.configure(bg=theme.BG_RUNNING)
        self.editing = False
        self.debug = False
        self.clear_selection()
        self.runner.start(self.script, self.graph, self.filename, self._script_parameters())

    def event_pause(self) -> None:
        self.runner.pause()

    def event_stop(self) -> None:
        self.runner.stop()

    def event_clear(self) -> None:
        """Stops the script and puts the graph back in edit mode."""
        self.runner.stop()
        self.log_panel.clear()
        self.canvas.configure(bg=theme.BG)
        self.editing = True
        self.debug = False
        self.graph.reset_states()
        self.canvas.delete("area")
        self.draw()

    def event_debug(self) -> None:
        """After a run, lets the user toggle elements by clicking."""
        if not self.editing:
            self.debug = True
            self.canvas.configure(bg=theme.BG_DEBUG)
            self.draw()

    def on_script_finished(self) -> None:
        """Called in the UI thread when the script ends."""
        self.canvas.configure(bg=theme.BG_SOLVED if self.runner.solved else theme.BG_FAILED)
        if not self.settings.animation:
            self.draw()

    def _script_parameters(self) -> dict:
        """Current script parameters as plain values (UI thread)."""
        if not self.script_properties:
            return scripting.load_script_parameters(self.script)
        props = self.script_properties
        return {name: props.get_attr(name) for name in props.attr}

    # -------------------------
    # Log
    # -------------------------
    def log(self, text, system_log: bool = False) -> None:
        """
        Adds a line to the log (any thread). The first character of a
        script message is a symbol; only symbols listed in the interface
        are shown, without the symbol. System messages always show.
        """
        if not text:
            return
        text = str(text)
        if system_log:
            self.bridge.run_in_ui(self.log_panel.append, text)
        elif text[0] in self.settings.logs_symbols:
            self.bridge.run_in_ui(self.log_panel.append, text[1:])

    def show_error(self, message: str) -> None:
        messagebox.showerror("Grafuria", message, parent=self.master)

    # -------------------------
    # Files
    # -------------------------
    def reset_canvas(self) -> None:
        """File > New."""
        self.event_clear()
        self.filename = ""
        self.scale = 1.0
        self._show_graph(Graph(self.sidebar.var_bidirectional.get()))
        self.set_title()
        self.sidebar.set_graph_name("Click here")

    def load_graph_file(self, filename: str) -> None:
        try:
            graph = Graph.load(filename)
        except Exception as e:
            messagebox.showinfo("Alert", f"File {filename} is corrupted or invalid. {e}")
            return
        graph.shuffle_edges()  # varies the traversal order between loads
        self.event_clear()
        self.scale = 1.0
        self._show_graph(graph)
        self.filename = filename
        name = os.path.splitext(os.path.basename(filename))[0]
        self.set_title(name)
        self.sidebar.set_graph_name(name)
        self.status.set(filename)

    def open_graph_file(self) -> None:
        self.runner.stop()
        filename = askopenfilename(
            title="Open a graph file", initialdir="graphs",
            filetypes=[("json files", "*.json")],
        )
        if filename:
            self.load_graph_file(filename)

    def get_graph(self) -> str:
        """Returns the graph as JSON (ids renumbered 0..n-1)."""
        return json.dumps(self.graph.to_dict(), indent=4)

    def save_graph_file_dialog(self) -> None:
        filename = asksaveasfilename(
            initialfile=os.path.basename(self.filename) or "graph.json",
            initialdir=os.path.dirname(self.filename) or "graphs",
            defaultextension=".json",
            filetypes=[("json files", "*.json")],
        )
        if not filename:
            return
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(self.get_graph())
        except OSError as e:
            self.status.set(f"Error trying to save file: {e}")
            return
        self.log(f"$bidirectional {self.graph.bidirectional} (reindexed for benchmark)")
        self.filename = filename
        name = os.path.splitext(os.path.basename(filename))[0]
        self.set_title(name)
        self.sidebar.set_graph_name(name)
        self.status.set(filename)

    def save_log_file(self) -> None:
        name = os.path.splitext(os.path.basename(self.filename))[0] or "grafuria"
        filename = asksaveasfilename(
            initialfile=name + ".log",
            defaultextension=".log",
            filetypes=[("log files", "*.log")],
        )
        if not filename:
            return
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(self.log_panel.get_text())
        except OSError as e:
            self.status.set(f"Error trying to save log: {e}")

    def set_script(self, filename: str) -> None:
        self.script = filename
        self.script_properties = Properties(self.sidebar.script_properties_frame, filename)
        self.sidebar.set_script_name(os.path.splitext(os.path.basename(filename))[0])

    def open_script_file(self) -> None:
        self.runner.stop()
        filename = askopenfilename(
            title="Open an algorithm file",
            initialdir="scripts",
            filetypes=[
                ("Algorithm Scripts", "*.lua *.py"),
                ("Lua Scripts", "*.lua"),
                ("Python Scripts", "*.py"),
            ],
        )
        if not filename:
            return
        # Scripts may use dofile("scripts/..."), so they must live there.
        scripts_dir = os.path.abspath("scripts") + os.sep
        if not os.path.abspath(filename).startswith(scripts_dir):
            self.show_error("Only scripts inside the 'scripts/' folder can be opened.")
            return
        self.set_script(filename)

    def open_documentation(self) -> None:
        if messagebox.askyesno(
            "Open Documentation",
            "This will open the project's page in your browser. Do you want to continue?",
        ):
            webbrowser.open(PROJECT_URL)
