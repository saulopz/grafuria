import os
import locale
from datetime import datetime
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter.filedialog import asksaveasfile, askopenfilename
from PIL import Image, ImageTk
from vertex import Vertex, Edge
import json
import time
import webbrowser
from threading import Thread
from state import State
from about import About
from lupa import LuaRuntime
from app_proxy import AppProxy
from properties import Properties


# -------------------------
# App Class
# -------------------------
class App(tk.Frame):
    """Defines the application class of graphic interface using Tkinter."""

    VERTEX = 0
    EDGE = 1
    SPEED_MAX = 10

    COLOR_BG = "white"
    COLOR_BG_SOLVED = "#f5f5dc"  # "#ffffee"
    COLOR_BG_FAILED = "#ffaaaa"
    COLOR_BG_RUNNING = "#e8f0ff"  # "cyan"

    COLOR_NONE = "gold"  # "black" #"yellow"
    COLOR_OVER = "blue"  # "red"
    COLOR_SELECTED = "black"  # "blue"  # "gold3"
    COLOR_INVALID = "DarkOrange1"

    # -------------------------
    # App Constructor
    # -------------------------
    def __init__(self, master=None, filename: str = "", script_lua: str = ""):
        """
        Defines the class constructor to initialize the graphic interface and
        canvas visual elements.

        Parameters
        ----------
        filename: str
            Path and file name of the graph.
        script_lua: str
            Path and file name of the algorithm in lua programming language.
        """
        super().__init__(master)
        self.script_lua = script_lua
        self.script_properties = None
        self.script_properties_frame = None
        self.config_file = "settings.json"
        self.var_log_symbols = ""
        self.title = "Grafuria"
        self.editing: bool = True
        self.var_animation = tk.BooleanVar(value=True)
        self.var_execution_time_log = tk.BooleanVar(value=True)
        self.load_configuration()
        self.bidirectional = False
        self.execution_time = 0
        self.solved = False
        self.vertex = []
        self.edge = []
        self.area = []
        self.master = master
        self.scale = 1.0
        self.master.title(f"{self.title}")
        self.create_window()
        self.selected = None
        self.selected_edge = None
        self.initial_time = time.time()
        self.final_time = time.time()
        self.stopped = True
        self.filename: str = ""
        if filename != "":
            self.load_graph_file(filename)
        if self.script_lua != "":
            self.script_properties = Properties(
                self.script_properties_frame, self.script_lua
            )
            name = os.path.splitext(os.path.basename(self.script_lua))[0]
            self.script_label.config(text=name)

    # -------------------------
    # Get Vertex Size
    # -------------------------
    def get_vertex_size(self):
        """Returns how many vertices there are in the graph's vertex list."""
        return len(self.vertex)

    # -------------------------
    # Get Speed
    # -------------------------
    def get_speed(self):
        """Returns the speed of algorithm execution."""
        return self.speed

    # -------------------------
    # Set Execution Time
    # -------------------------
    def set_execution_time(self, time):
        """Set the execution time of algorithm."""
        self.execution_time = time

    # -------------------------
    # Set Solved
    # -------------------------
    def set_solved(self, solved):
        """Inform application if algorithm solved graph or not."""
        self.solved = solved

    # -------------------------
    # Get Vertex
    # -------------------------
    def get_vertex(self, index):
        """
        Returns a specific vertex from graph vertices.

        Parameters
        ----------
        index: int
            Position of vertex on vertex list.
        """
        if index < 0 or index >= self.get_vertex_size():
            return None
        return self.vertex[index]

    # -------------------------
    # Area Add
    # -------------------------
    def area_add(self, x, y):
        """
        Add a new point in a area to create a poligonon.

        Parameters
        ----------
        x, y: int
            Position x, y of new point in area.
        """
        self.area.append((x, y))

    # -------------------------
    # Area Close
    # -------------------------
    def area_close(self):
        """
        Close the area poligon and create it.
        """
        area = self.area
        self.canvas.create_polygon(
            *area, fill="lemon chiffon", outline="black", tag="area"
        )
        self.area = []

    # -------------------------
    # Draw
    # -------------------------
    def draw(self) -> None:
        """Draw all edges and vertices"""
        for edge in self.edge:
            edge.draw()
        for vertex in self.vertex:
            vertex.draw()
        self.canvas.tag_lower("edge")
        self.canvas.tag_raise("vertex")
        self.canvas.tag_raise("text")

    # -------------------------
    # Create Window
    # -------------------------
    def create_window(self) -> None:
        """Create the graphic interface of this software using tkinter."""
        root = self.master
        self.root = root
        self.root.geometry("1200x700")

        # Main Menu
        self.menu_bar = tk.Menu(root)
        root.config(menu=self.menu_bar)

        # Drop-down menus (File, Help)
        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        file_menu.add_command(label="New", command=self.reset_canvas)
        file_menu.add_command(label="Save", command=self.save_graph_file_dialog)
        file_menu.add_command(label="Save Log", command=self.save_log_file)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=root.quit)

        help_menu = tk.Menu(self.menu_bar, tearoff=0)
        help_menu.add_command(label="Documentation", command=self.open_documentation)
        help_menu.add_command(label="About", command=lambda: About(root))

        # Adding menus to the main menu
        self.menu_bar.add_cascade(label="File", menu=file_menu)
        self.menu_bar.add_cascade(label="Help", menu=help_menu)

        # Main horizontal PanedWindow to organize the canvas and settings
        main_paned_window = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
        main_paned_window.pack(fill=tk.BOTH, expand=True)

        # Canvas
        canvas_frame = ttk.Frame(main_paned_window)
        self.canvas = tk.Canvas(canvas_frame, bg="white")

        # Scrollbars for Canvas
        self.scroll_y = tk.Scrollbar(
            canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview
        )
        self.scroll_x = tk.Scrollbar(
            canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview
        )
        self.canvas.configure(
            yscrollcommand=self.scroll_y.set, xscrollcommand=self.scroll_x.set
        )

        # Positioning the Canvas and Scrollbars
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scroll_y.grid(row=0, column=1, sticky="ns")
        self.scroll_x.grid(row=1, column=0, sticky="ew")

        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)

        self.canvas.bind("<Button-2>", self.canvas_button2_event)
        self.master.bind("<Delete>", self.delete_canvas_object)

        self.canvas.bind("<MouseWheel>", self.zoom)  # Windows/Linux
        self.canvas.bind("<Button-4>", self.zoom)  # Mac zoom in
        self.canvas.bind("<Button-5>", self.zoom)  # Mac zoom out

        # Adding canvas_frame to PanedWindow
        main_paned_window.add(canvas_frame, weight=3)

        # Configuration frame on the right of the Canvas (fixed)
        self.config_frame = ttk.Frame(main_paned_window, width=200, relief=tk.SUNKEN)
        main_paned_window.add(self.config_frame, weight=0)  # Weight 0 prevents resizing

        # Action button frame below the menu
        button_frame = tk.Frame(self.config_frame)
        button_frame.pack(fill=tk.X)

        # Loading button icons
        self.icon_play = ImageTk.PhotoImage(
            Image.open("res/circle-play-regular.png").resize((20, 20))
        )
        self.icon_stop = ImageTk.PhotoImage(
            Image.open("res/circle-stop-regular.png").resize((20, 20))
        )
        self.icon_clear = ImageTk.PhotoImage(
            Image.open("res/rotate-solid.png").resize((20, 20))
        )
        self.icon_min = ImageTk.PhotoImage(
            Image.open("res/down-long-solid.png").resize((20, 20))
        )
        self.icon_minus = ImageTk.PhotoImage(
            Image.open("res/minus-solid.png").resize((20, 20))
        )
        self.icon_plus = ImageTk.PhotoImage(
            Image.open("res/plus-solid.png").resize((20, 20))
        )
        self.icon_max = ImageTk.PhotoImage(
            Image.open("res/up-long-solid.png").resize((20, 20))
        )

        # Adding buttons
        self.bt_play = ttk.Button(
            button_frame, image=self.icon_play, command=self.event_play
        )
        self.bt_stop = ttk.Button(
            button_frame, image=self.icon_stop, command=self.event_stop
        )
        self.bt_clear = ttk.Button(
            button_frame, image=self.icon_clear, command=self.event_clear
        )

        # Packing buttons
        for widget in [self.bt_play, self.bt_stop, self.bt_clear]:
            widget.pack(side=tk.LEFT, padx=5, pady=5)

        # Control for "Graph"
        graph_frame = ttk.Frame(self.config_frame)
        graph_frame.pack(fill="x", padx=10, pady=5)
        tk.Label(graph_frame, text="Graph:").pack(side="left")
        self.graph_label = tk.Label(
            graph_frame, text="Click here", relief="sunken", width=20, anchor="w"
        )
        self.graph_label.pack(side="right", fill="x")
        self.graph_label.bind("<Button-1>", self.on_graph_click)

        # Control for "Script"
        script_frame = ttk.Frame(self.config_frame)
        script_frame.pack(fill="x", padx=10, pady=5)
        tk.Label(script_frame, text="Script:").pack(side="left")
        self.script_label = tk.Label(
            script_frame, text="Click here", relief="sunken", width=20, anchor="w"
        )
        self.script_label.pack(side="right", fill="x")
        self.script_label.bind("<Button-1>", self.on_script_click)

        # Control for "Animation"
        animation_frame = ttk.Frame(self.config_frame)
        animation_frame.pack(fill="x", padx=10, pady=0)
        tk.Label(animation_frame, text="Animation:").pack(side="left", pady=0)
        self.animation = tk.Checkbutton(
            animation_frame,
            variable=self.var_animation,
            onvalue=True,
            offvalue=False,
            command=self.on_animation_change,
        )
        self.animation.pack(side="right")

        # Control for "Execution Time Log"
        execution_time_log_frame = ttk.Frame(self.config_frame)
        execution_time_log_frame.pack(fill="x", padx=10, pady=0)
        tk.Label(execution_time_log_frame, text="Exec time log:").pack(
            side="left", pady=0
        )
        self.execution_time_log = tk.Checkbutton(
            execution_time_log_frame,
            variable=self.var_execution_time_log,
            onvalue=True,
            offvalue=False,
            command=self.on_execution_time_log_change,
        )
        self.execution_time_log.pack(side="right")

        # Control for "Bidirectional"
        bidirectional_frame = ttk.Frame(self.config_frame)
        bidirectional_frame.pack(fill="x", padx=10, pady=0)
        tk.Label(bidirectional_frame, text="Bidirectional:").pack(side="left", pady=0)
        self.var_bidirectional = tk.BooleanVar(value=True)
        self.chk_bidirectional = tk.Checkbutton(
            bidirectional_frame,
            variable=self.var_bidirectional,
            onvalue=True,
            offvalue=False,
            command=self.on_bidirectional_change,
        )
        self.chk_bidirectional.pack(side="right")

        # Control for "Speed"
        speed_frame = ttk.Frame(self.config_frame)
        speed_frame.pack(fill="x", padx=10, pady=0)
        tk.Label(speed_frame, text="Speed:").pack(side="left", pady=0)
        self.var_speed = tk.IntVar(value=self.speed)
        self.scale_speed = tk.Scale(
            speed_frame,
            from_=1,
            to=10,
            variable=self.var_speed,
            orient="horizontal",
            length=150,
            command=lambda value: self.on_speed_change(value),
        )
        self.scale_speed.pack(side="right", fill="x")

        logs_frame = ttk.Frame(self.config_frame)
        logs_frame.pack(fill="x", padx=10, pady=5)
        tk.Label(logs_frame, text="Logs Symbols:").pack(side="left")
        self.var_logs_field = tk.StringVar(value=self.var_log_symbols)
        self.entry_logs = ttk.Entry(logs_frame, textvariable=self.var_logs_field)
        self.entry_logs.bind("<KeyRelease>", self.on_log_symbols_change)
        self.entry_logs.pack(side="right", fill="x")
        self.config_file = "settings.json"

        self.load_configuration()

        # Separator -----------------------------------------------------------

        ttk.Separator(self.config_frame, orient=tk.HORIZONTAL).pack(fill="x", pady=(0, 0))

        self.script_properties_frame = ttk.Frame(self.config_frame)
        self.script_properties_frame.pack(fill="x", anchor="nw", expand=True, padx=5, pady=0)

        # Separator -----------------------------------------------------------
        ttk.Separator(self.config_frame, orient=tk.HORIZONTAL).pack(fill="x", pady=0)

        self.dynamic_config_frame = ttk.Frame(self.config_frame)
        self.dynamic_config_frame.pack(padx=0, pady=0)

        # Frame for vertex settings
        self.vertex_config_frame = ttk.Frame(self.dynamic_config_frame)

        # Title
        tk.Label(self.vertex_config_frame, text="Vertex Settings").pack(
            anchor="w", pady=2
        )

        # Line for vertex "ID"
        vertex_id_frame = ttk.Frame(self.vertex_config_frame)
        vertex_id_frame.pack(fill="x", padx=5, pady=2)
        tk.Label(vertex_id_frame, text="ID:").pack(side="left")
        self.vertex_id = ttk.Entry(vertex_id_frame, state="readonly")
        self.vertex_id.pack(side="right", fill="x")

        # Line for vertex "Name"
        vertex_name_frame = ttk.Frame(self.vertex_config_frame)
        vertex_name_frame.pack(fill="x", padx=5, pady=2)
        tk.Label(vertex_name_frame, text="Name:").pack(side="left")
        self.vertex_name = ttk.Entry(vertex_name_frame)
        self.vertex_name.pack(side="right", fill="x")
        self.vertex_name.bind("<KeyRelease>", self.on_vertex_name_change)

        # Pack the vertex configuration frame
        self.vertex_config_frame.pack(fill="x", pady=5)

        # Frame for edge settings
        self.edge_config_frame = ttk.Frame(self.dynamic_config_frame)

        # Title
        tk.Label(self.edge_config_frame, text="Edge Settings").pack(anchor="w", pady=2)

        # Line for edge "ID"
        edge_id_frame = ttk.Frame(self.edge_config_frame)
        edge_id_frame.pack(fill="x", padx=5, pady=2)
        tk.Label(edge_id_frame, text="ID:").pack(side="left")
        self.edge_id = ttk.Entry(edge_id_frame, state="readonly")
        self.edge_id.pack(side="right", fill="x")

        # Line for edge "Weight"
        edge_weight_frame = ttk.Frame(self.edge_config_frame)
        edge_weight_frame.pack(fill="x", padx=5, pady=2)
        tk.Label(edge_weight_frame, text="Weight:").pack(side="left")
        self.edge_weight = ttk.Entry(edge_weight_frame)
        self.edge_weight.pack(side="right", fill="x")
        self.edge_weight.bind("<KeyRelease>", self.on_edge_weight_change)

        # Pack the edge configuration frame
        self.edge_config_frame.pack(fill="x", pady=5)

        self.show_config_frame(None)

        # Vertical PanedWindow for logs area and status bar
        bottom_frame = ttk.Frame(root)
        bottom_frame.pack(fill=tk.X)

        # Log area with vertical scroll bar (adjustable)
        self.log_text = tk.Text(bottom_frame, wrap="word", state="disabled", height=5)
        self.log_scroll = tk.Scrollbar(bottom_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=self.log_scroll.set)

        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.log_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Status bar below the logs area
        self.status_frame = ttk.Frame(root)
        self.status_frame.pack(fill=tk.X)

        # Status information
        # self.line_count_label = ttk.Label(self.status_frame, text="Lines: 0")
        self.status_bar_info = ttk.Label(self.status_frame, text="Info: ")

        # self.line_count_label.pack(side=tk.LEFT, padx=10)
        self.status_bar_info.pack(side=tk.LEFT, padx=10)

    # -------------------------
    # On Vertex Name Change
    # -------------------------
    def on_vertex_name_change(self, event):
        """
        When the name of a vertex is changed, the vertex attribute and
        the text that appears on the canvas also change.
        """
        name = self.vertex_name.get()
        if self.selected:
            self.selected.name = name
            self.canvas.itemconfig(self.selected.text_id, text=name)

    # -------------------------
    # Open Documentation Dialog
    # -------------------------
    def open_documentation(self):
        """Open the GitHub project link after user confirmation."""
        result = messagebox.askyesno(
            "Open Documentation",
            "This will open the project's GitHub page in your browser. Do you want to continue?",
        )
        if result:  # I fuser click "Yes"
            webbrowser.open("https://github.com/saulopz/grafuria")

    # -------------------------
    # Show Config Frame
    # -------------------------
    def show_config_frame(self, frame_to_show=None):
        """
        Hides dynamic frames and shows a specific one if applicable. This
        is used when selecting an object on the canvas, such as a vertex
        or an edge.
        """
        # Hides all dynamic frames
        for frame in [self.vertex_config_frame, self.edge_config_frame]:
            frame.pack_forget()
        # Shows the selected frame, if any
        if frame_to_show:
            frame_to_show.pack(fill="x", padx=10, pady=5)

    # -------------------------
    # On Graph Clicked
    # -------------------------
    def on_graph_click(self, event):
        """
        When you click on the graph text field, a window opens to
        choose a JSON format file that represents a graph.
        """
        self.open_graph_file()

    # -------------------------
    # Zoom
    # -------------------------
    def zoom(self, event):
        """When you roll the mouse wheel, it zooms in or zooms out."""
        if event.delta > 0 or event.num == 4:  # Roll up (zoom in)
            factor = 1.1
        elif event.delta < 0 or event.num == 5:  # Roll down (zoom out)
            factor = 0.9
        else:
            return
        self.scale *= factor  # update scale
        # Center zoom on mouse position
        self.canvas.scale(
            "all",
            self.canvas.canvasx(event.x),
            self.canvas.canvasy(event.y),
            factor,
            factor,
        )
        # Adjust your view to stay focused
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

        # Atualizar o tamanho das setas das arestas
        for e in self.edge:
            self.canvas.itemconfig(
                e.canvas_id,  # Update the element on the Canvas
                arrowshape=(
                    10 * self.scale,
                    10 * self.scale,
                    5 * self.scale,
                ),
            )

    # -------------------------
    # On Script Click
    # -------------------------
    def on_script_click(self, event):
        """
        When script field is clicked, open a dialog window to select the
        script file in Lua programming language.
        """
        self.open_script_file()
        name = os.path.splitext(os.path.basename(self.script_lua))[0]
        self.script_label.config(text=name)

    # -------------------------
    # Om Animation Change
    # -------------------------
    def on_animation_change(self):
        """Changes variable that controls animation."""
        self.save_configuration()
        self.animation = self.var_animation.get()

    # -------------------------
    # On Execution Time Log
    # -------------------------
    def on_execution_time_log_change(self):
        self.save_configuration()
        self.execution_time_log = self.var_execution_time_log.get()

    # -------------------------
    # On Edge Weight Change
    # -------------------------
    def on_edge_weight_change(self, event):
        """Changes the weith of a selected edge."""
        weight = self.edge_weight.get()
        try:
            if self.selected_edge:
                self.selected_edge.weight = float(weight)
                self.canvas.itemconfig(self.selected_edge.text_id, text=weight)
        except ValueError:
            print("Invalid value, ignoring update.")

    # -------------------------
    # On Bidirectional Change
    # -------------------------
    def on_bidirectional_change(self):
        """
        When the chart style is changed between two-way and one-way,
        it is necessary to recreate the edges on the canvas.
        """
        self.bidirectional = self.var_bidirectional.get()
        # Redraw all edges
        for e in self.edge:
            ax, ay = e.a.get_coords()
            bx, by = e.b.get_coords()

            # Removes current edge from canvas
            self.canvas.delete(e.canvas_id)

            # Redraw edge with or without arrows
            if self.bidirectional:
                e.canvas_id = self.canvas.create_line(
                    ax, ay, bx, by, width=2, fill=self.COLOR_NONE, tags="edge"
                )
            else:
                e.canvas_id = self.canvas.create_line(
                    ax,
                    ay,
                    bx,
                    by,
                    arrow="last",
                    arrowshape=(10 * self.scale, 10 * self.scale, 5 * self.scale),
                    width=2,
                    fill=self.COLOR_NONE,
                    tags="edge",
                )
        self.draw()

    # -------------------------
    # On Speed Change
    # -------------------------
    def on_speed_change(self, value):
        """When change speed, salve configuration file."""
        self.save_configuration()
        self.speed = int(value)

    # -------------------------
    # On Log Symbols Change
    # -------------------------
    def on_log_symbols_change(self, event):
        """When change log symbols, save configuration file."""
        self.save_configuration()
        self.var_log_symbols = self.var_logs_field.get()

    # -------------------------
    # Set Statusbar
    # -------------------------
    def set_statusbar(self, text: any):
        """Changes the statusbar information."""
        self.status_bar_info.config(text=f"Info: {text}")

    # -------------------------
    # Event Play
    # -------------------------
    def event_play(self) -> None:
        """
        It is executed when the play button is pressed, starting the
        execution of an algorithm on a graph.
        """
        if not self.script_lua:
            self.show_error_alert("You need a graph and an algorithm to run.")
            return
        self.clear_log()
        self.event_clear()
        self.canvas.configure(bg=App.COLOR_BG_RUNNING)
        self.editing = False
        if self.selected is not None:
            self.selected.unselect()
        if self.selected_edge is not None:
            self.selected_edge.unselect()
        self.stopped = False
        a = Thread(target=self.lua_execute)
        a.daemon = True
        a.start()

    # -------------------------
    # Lua Execute
    # -------------------------
    def lua_execute(self):
        """Executes a script lua if loaded"""
        try:
            lua = LuaRuntime(unpack_returned_tuples=True)
            app_proxy = AppProxy(self)
            lua.globals().State = {
                "NONE": State.NONE,
                "TESTING": State.TESTING,
                "ACTIVE": State.ACTIVE,
                "INVALID": State.INVALID,
            }
            lua.globals().app = app_proxy
            with open(self.script_lua, "r") as file:
                lua_script = file.read()
            lua.execute(lua_script)
            self.save_execution_history()
        except Exception as e:
            self.log(str(e), True)
        if self.solved:
            self.canvas.configure(bg=App.COLOR_BG_SOLVED)
        else:
            self.canvas.configure(bg=App.COLOR_BG_FAILED)
        if not self.animation:
            self.draw()

    # -------------------------
    # Get Var
    # -------------------------
    def get_var(self, var_name):
        """Returns a configuration variable to lua script."""
        if self.script_properties:
            return self.script_properties.get_attr(var_name)
        return None

    # -------------------------
    # Save Execution History
    # -------------------------
    def save_execution_history(self):
        if not self.var_execution_time_log.get():
            return
        try:
            file_path = "execution_history.cvs"
            graph = os.path.basename(self.filename)
            script = os.path.basename(self.script_lua)
            # locale.setlocale(locale.LC_NUMERIC, "pt_BR.UTF-8")
            timestamp = datetime.now().strftime("%Y-%m-%d\t%H:%M:%S")
            execution_time = locale.format_string(
                "%.4f", self.execution_time, grouping=True
            )

            with open(file_path, "a") as f:
                f.write(
                    f"{timestamp}\t{graph}\t{script}\t{execution_time}\t{self.solved}\n"
                )
        except Exception as e:
            self.status_bar_info.config(text=f"Error saving execution history: {e}")

    # -------------------------
    # Show Error Alert
    # -------------------------
    def show_error_alert(self, message):
        """Show a 'message' dialog with some error"""
        root = tk.Tk()
        root.withdraw()  # Hide main window
        messagebox.showerror("Erro Lua", message)

    # -------------------------
    # Step
    # -------------------------
    def step(self) -> None:
        """
        This method must be called internally in the lua script
        at some loop points to perform brief pauses and slow down
        the algorithm's execution for a more refined observation
        of how the execution is occurring. The value ranges from
        0 to 10, with the value 10 having no SLEEP. This value is
        adjusted in the graphical interface.
        """
        speed = self.get_speed()
        if speed < 10:
            t = (self.get_speed_max() - speed) ** 2 / 100
            time.sleep(t)

    # -------------------------
    # Event Stop
    # -------------------------
    def event_stop(self) -> None:
        """Stop the algorithm execution."""
        self.stopped = True

    # -------------------------
    # Is Stopped
    # -------------------------
    def is_stopped(self):
        """Returns if algorithm was stopped."""
        return self.stopped

    # -------------------------
    # Event Clear
    # -------------------------
    def event_clear(self) -> None:
        """Change state of all edges and vertices of graph to NONE."""
        self.stopped = True
        self.clear_log()
        self.canvas.configure(bg=App.COLOR_BG)
        self.editing = True
        for v in self.vertex:
            v.set_state(State.NONE)
        for e in self.edge:
            e.set_state(State.NONE)
        self.canvas.delete("area")
        self.draw()

    # -------------------------
    # Update Entry Speed
    # -------------------------
    def update_entry_speed(self, text):
        """
        Update text on speed entry.

        Parameters
        ----------
        text: txt
            information.
        """
        self.entry_speed.config(state="normal")
        self.entry_speed.delete(0, tk.END)
        self.entry_speed.insert(0, f"{text}")
        self.entry_speed.config(state="readonly")

    # -------------------------
    # Get Speed Max
    # -------------------------
    def get_speed_max(self):
        """Returns the speed max."""
        return App.SPEED_MAX

    # -------------------------
    # Log
    # -------------------------
    def log(self, text, system_log: bool = False):
        """
        Add a log line on log text field.

        Parameters
        ----------
        text: str
            Text to be added to the log. The first character
            is an identifier of the type of log information.
            The user can define in the lua script what type
            of information the log is and choose in the
            interface those that he wants to be displayed.
        """
        if not text:
            return
        msg = f"{text}\n"
        if not system_log:
            msg = msg[1:]
        if system_log or text[0] in self.var_log_symbols:
            self.log_text.config(state="normal")
            self.log_text.insert(tk.END, msg)
            self.log_text.yview(tk.END)
            self.log_text.config(state="disabled")

    # -------------------------
    # Clear Log
    # -------------------------
    def clear_log(self):
        """Clear log graphic field."""
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state="disabled")

    # -------------------------
    # Canvas Button 2 Event
    # -------------------------
    def canvas_button2_event(self, event) -> None:
        """When click with mouse button 2, create a vertex in mouse position."""
        if not self.editing:
            return
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        self.vertex.append(Vertex("", x, y, self))

    # -------------------------
    # Delete Canvas Object
    # -------------------------
    def delete_canvas_object(self, event) -> None:
        """Delete a graph object of canvas"""
        if not self.editing:
            return
        if self.selected is not None:
            self.selected.delete()
            self.selected = None
        if self.selected_edge is not None:
            self.selected_edge.delete()
            self.selected_edge = None

    # -------------------------
    # About
    # -------------------------
    def about(self) -> None:
        """Open the about dialog window."""
        tk.messagebox.askquestion("About", "Hemiltonian Path", icon="info")

    # -------------------------
    # Get Graph
    # -------------------------
    def get_graph(self) -> str:
        """Create a string with graph information in JSON format."""
        vertex: Vertex = []
        for v in self.vertex:
            vertex.append(v.get_json())
        edge: Edge = []
        for e in self.edge:
            edge.append(e.get_json())
        self.log(f"$bidirectional {self.bidirectional}")
        obj = {"bidirectional": self.bidirectional, "vertex": vertex, "edge": edge}
        return json.dumps(obj)

    # -------------------------
    # Save Graph File Dialog
    # -------------------------
    def save_graph_file_dialog(self) -> None:
        """Save graph file dialog"""
        path = asksaveasfile(
            initialfile=self.filename,
            defaultextension=".json",
            filetypes=[("json files", "*.json")],
        )
        if path is None:
            return

        graph_data = self.get_graph()
        try:
            graph_object = json.loads(graph_data)
            with open(path.name, "w") as f:
                json.dump(graph_object, f, indent=4)
            self.filename = path.name
            self.set_statusbar(self.filename)
        except json.JSONDecodeError as e:
            self.set_statusbar(f"Error trying to save file: {e}")

    # -------------------------
    # Save Log File
    # -------------------------
    def save_log_file(self) -> None:
        """Save a log file"""
        filename: str = os.path.basename(self.filename)
        filename = os.path.splitext(filename)[0] + ".log"
        path = asksaveasfile(
            initialfile=filename,
            defaultextension=".json",
            filetypes=[("log files", "*.log")],
        )
        if path is None:
            return
        with open(path.name, "w") as f:
            f.write(self.log_text.get("1.0", "end"))

    # -------------------------
    # Open Graph File Dialog
    # -------------------------
    def open_graph_file(self) -> None:
        """Open graph file dialog."""
        self.event_stop()
        filename = askopenfilename(
            title="Open a graph file",
            initialdir="graph",
            filetypes=[("json files", "*.json")],
        )
        if filename != "":
            self.reset_canvas()
            self.set_statusbar(filename)
            self.load_graph_file(filename)
            name = os.path.splitext(os.path.basename(self.filename))[0]
            self.graph_label.config(text=name)

    # -------------------------
    # Open Script File Dialog
    # -------------------------
    def open_script_file(self) -> None:
        """Open the algorithm file dialog (in Lua language)."""
        self.event_stop()
        filename = askopenfilename(  # Opening the file selection window.
            title="Open an algorithm file",
            initialdir="lua",
            filetypes=[("lua files", "*.lua")],
        )
        if filename:
            if os.path.isfile(filename):
                self.script_lua = filename  # Atualiza o caminho do script
                self.script_properties = Properties(
                    self.script_properties_frame, self.script_lua
                )
            else:
                print("Error: File not found.")
        else:
            print("No file selected.")

    # -------------------------
    # Load Graph File
    # -------------------------
    def load_graph_file(self, filename) -> None:
        """
        Load a graph file.

        Parameters
        ----------
        filename: str
            Name and path of graph file in format JSON.
        """
        try:
            self.filename = filename
            f = open(filename)
            data = json.load(f)
            f.close()
            self.canvas.delete("all")
            self.bidirectional = data.get("bidirectional", True)
            self.var_bidirectional.set(self.bidirectional)
            for v in data["vertex"]:
                self.vertex.append(
                    Vertex(v.get("name", ""), v["x"], v["y"], self, v["id"])
                )
            for e in data["edge"]:
                a = None
                b = None
                for v in self.vertex:
                    if e["a"] == v.id:
                        a = v
                    if e["b"] == v.id:
                        b = v
                    if a != None and b != None:
                        break
                weight = e.get("weight", 1)
                edge = Edge(a, b, weight, self, id=e["id"])
                self.edge.append(edge)
                a.edge.append(edge)
                b.edge.append(edge)
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

            name = os.path.splitext(os.path.basename(self.filename))[0]
            self.master.title(f"{self.title} : {name}")
            self.graph_label.config(text=name)
        except Exception as e:
            messagebox.showinfo(
                "Alert", f"File {filename} is corrupted or invalid. {e}"
            )
            self.filename = ""
            self.set_statusbar("")

    # -------------------------
    # Save Configuration
    # -------------------------
    def save_configuration(self):
        """Save configuration file."""
        config = {
            "animation": self.var_animation.get(),
            "speed": self.var_speed.get(),
            "logs_symbols": self.var_logs_field.get(),
            "execution_time_log": self.var_execution_time_log.get(),
        }
        with open(self.config_file, "w") as f:
            json.dump(config, f, indent=4)

    # -------------------------
    # Load Configuration
    # -------------------------
    def load_configuration(self):
        """Load configuration file."""
        if os.path.exists(self.config_file):
            with open(self.config_file, "r") as f:
                j = json.load(f)
                self.var_animation.set(j.get("animation", True))
                self.animation = self.var_animation.get()
                self.speed = j.get("speed", 10)
                self.var_execution_time_log.set(j.get("execution_time_log", False))
                self.execution_time_log = self.var_execution_time_log.get()
                self.var_log_symbols = j.get("logs_symbols", "")
        else:
            self.bidirectional = True
            self.animation = True
            self.speed = 10
            self.execution_time_log = False
            self.var_log_symbols = ""

    # -------------------------
    # Reset Canvas
    # -------------------------
    def reset_canvas(self) -> None:
        """Reset canvas to create a new graph."""
        self.clear_log()
        self.event_clear()
        self.filename = ""
        self.master.title(f"{self.title}")
        self.vertex.clear()
        Vertex.id = 0
        self.edge.clear()
        Edge.id = 0
        self.canvas.delete("all")
        self.graph_label.config(text="Clique aqui")
