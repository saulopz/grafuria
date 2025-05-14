import tkinter as tk
from typing import Dict
from state import State
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vertex import Vertex


# -------------------------
# Edge Class
# -------------------------
class Edge:
    """
    This class represents a Edge on algorithm and it's representation
    on application to draw on canvas.

    Attributes
    ----------
    type int:
        Identify element type in application.
    id: int
        Edge identification ID.
    app: App
        Context of interface application.
    canvas: tk.Canvas
        Canvas to draw it element.
    a: Vertex
        First vertex connection.
    b: Vertex
        Second vertex connection.
    weight: float
        Weight of connection between a and b.
    state: int
        State of edge while execution.
    """

    id: int = 0  # Element autoincrement identification (static)

    # -------------------------
    # Edge Constructor
    # -------------------------
    def __init__(self, a, b, w: float, app, id: int = -1):
        """
        Constructor to create a edge object. A edge object is aways
        connect with two vertex.

        Parameters
        ----------
        a: Vertex
            First edge connection.
        b: Vertex
            Second edge connection.
        w: float
            Weight of connection between a and b.
        app: App
            Context of graphic application.
        id: int
            Edge id if exists. It's necessary on graph load from disk.
        """
        self.type: int = app.EDGE  # Identify element type in application
        self.app = app  # Context of interface application
        self.canvas: tk.Canvas = app.canvas  # Canvas to draw it
        self.a = a  # First vertex connection
        self.b = b  # Second vertex connection
        self.weight: float = w  # Connection weight
        self.state: int = State.NONE  # State of edge while execution
        if id == -1:  # Apply an autoincrement id if
            Edge.id = Edge.id + 1  # we not pass id as parameter
            self.id = Edge.id
        else:  # Or an existing ID if application is
            if Edge.id <= id:  # loading a graph file
                Edge.id = id + 1
            self.id = id
        # Graphic representation of edge in application
        if not app.bidirectional:
            self.canvas_id = self.canvas.create_line(
                a.x,
                a.y,
                b.x,
                b.y,
                arrow="last",
                arrowshape=(
                    10 * self.app.scale,
                    10 * self.app.scale,
                    5 * self.app.scale,
                ),
                width=2,
                fill=self.app.COLOR_NONE,
                tags="edge",
            )
        else:
            self.canvas_id = self.canvas.create_line(
                a.x,
                a.y,
                b.x,
                b.y,
                width=2,
                fill=self.app.COLOR_NONE,
                tags="edge",
            )
        x_middle = (a.x + b.x) / 2
        y_middle = (a.y + b.y) / 2
        self.text_id = self.canvas.create_text(
            x_middle,
            y_middle,
            text=str(self.weight),
            anchor="center",
            font=("Arial", 10),
            fill="black",
            tags="text",
        )

        self.canvas.tag_lower(self.canvas_id)
        self.canvas.tag_bind(self.canvas_id, "<Button-1>", self.mouse_down)
        self.canvas.tag_bind(self.canvas_id, "<Any-Enter>", self.mouse_enter)
        self.canvas.tag_bind(self.canvas_id, "<Any-Leave>", self.mouse_leave)

    # -------------------------
    # Get JSON
    # -------------------------
    def get_json(self) -> Dict[str, int]:
        """
        Returns the JSON object representing this edge. Useful for
        recording edge information into the graph file.
        """
        return {
            "id": self.id,
            "a": self.a.id,
            "b": self.b.id,
            "weight": self.weight,
        }

    # -------------------------
    # Get ID
    # -------------------------
    def get_id(self):
        """Returns the edge ID."""
        return self.id

    # -------------------------
    # Get Adjacent
    # -------------------------
    def get_adjacent(self, vertex: "Vertex"):
        """
        Returns the adjacent vertex of this edge. If the vertex
        passed as parameter is not connected to this edge, it returns None.
        """
        if self.a == vertex:
            return self.b
        elif self.b == vertex:
            return self.a
        else:
            return None

    # -------------------------
    # Get A
    # -------------------------
    def get_a(self):
        """Returns one of Vertex of this connection."""
        return self.a

    # -------------------------
    # Get B
    # -------------------------
    def get_b(self):
        """Returns the other Vertex of this connection."""
        return self.b

    # -------------------------
    # Set Weight
    # -------------------------
    def set_weight(self, w: float) -> None:
        """Changes the weight of connection between a and b vertices."""
        self.weight = w

    # -------------------------
    # Set Weight
    # -------------------------
    def get_weight(self) -> float:
        """Returns the weight of connection between a and b vertices."""
        return self.weight

    # -------------------------
    # Get State
    # -------------------------
    def get_state(self):
        """Returns the state of this edge."""
        return self.state

    # -------------------------
    # Set State
    # -------------------------
    def set_state(self, state: int) -> None:
        """Changes the state of this edge."""
        self.a.change_active_edge(self, state)
        self.b.change_active_edge(self, state)
        self.state = state
        if self.app.animation:  # draws if animation checkbox is true
            self.draw()

    # -------------------------
    # Draw
    # -------------------------
    def draw(self) -> None:
        """
        Draws the element on the screen. It is important when the
        state has changed.
        """
        if self.state == State.NONE:
            self.canvas.itemconfig(
                self.canvas_id,
                fill=self.app.COLOR_NONE,
                width=2,
            )
        elif self.state == State.TESTING:
            self.canvas.itemconfig(
                self.canvas_id,
                fill=self.app.COLOR_OVER,
                width=2,
            )
        elif self.state == State.ACTIVE:
            self.canvas.itemconfig(
                self.canvas_id,
                fill=self.app.COLOR_SELECTED,
                width=4,
            )
        elif self.state == State.INVALID:
            self.canvas.itemconfig(
                self.canvas.id,
                fill=self.app.COLOR_INVALID,
                width=2,
            )

    # -------------------------
    # On Mouse Enter
    # -------------------------
    def mouse_enter(self, event: tk.Event) -> None:
        """
        Event called when mouse is over edge line, changing the edge color.
        """
        selected = self.app.selected_edge
        if not self.app.editing:
            return
        if selected is not None and selected == self:
            return
        self.canvas.itemconfig(self.canvas_id, fill=self.app.COLOR_OVER)

    # -------------------------
    # On Mouse Leave
    # -------------------------
    def mouse_leave(self, event: tk.Event) -> None:
        """
        Event called when mouse is out of edge line, changing the edge color.
        """
        selected = self.app.selected_edge
        if not self.app.editing:
            return
        if selected is not None and selected == self:
            self.canvas.itemconfig(
                self.canvas_id,
                fill=self.app.COLOR_SELECTED,
            )
        else:
            self.canvas.itemconfig(
                self.canvas_id,
                fill=self.app.COLOR_NONE,
            )

    # -------------------------
    # On Mouse Down
    # -------------------------
    def mouse_down(self, event: tk.Event) -> None:
        """Event called when mouse was clicked over this edge."""
        if not self.app.editing:
            self.app.set_statusbar("Edge: " + str(self.id))
            return
        if self.app.selected_edge is not None:
            self.app.selected_edge.unselect()
            self.app.selected_edge = None
        if self.app.selected is not None:
            self.app.selected.unselect()
            self.app.selected = None
        self.select()
        self.app.selected_edge = self
        self.app.set_statusbar("Edge selected: " + str(self.id))
        self.app.edge_id.config(state="normal")
        self.app.edge_id.delete(0, tk.END)
        self.app.edge_id.insert(0, self.id)
        self.app.edge_id.config(state="readonly")
        self.app.edge_weight.delete(0, tk.END)
        self.app.edge_weight.insert(0, self.weight)
        self.app.show_config_frame(self.app.edge_config_frame)

    # -------------------------
    # Refresh
    # -------------------------
    def refresh(self) -> None:
        """
        Changes edge coordinates as vertices are moved around on the canvas.
        """
        ax, ay = self.a.get_coords()
        bx, by = self.b.get_coords()
        self.canvas.coords(self.canvas_id, ax, ay, bx, by)
        x_middle = (ax + bx) / 2
        y_middle = (ay + by) / 2
        self.canvas.coords(self.text_id, x_middle, y_middle)

    # -------------------------
    # Select
    # -------------------------
    def select(self) -> None:
        """Set this edge as selected."""
        self.canvas.itemconfig(self.canvas_id, fill=self.app.COLOR_SELECTED)

    # -------------------------
    # Unselect
    # -------------------------
    def unselect(self) -> None:
        """Unselect this edge."""
        self.canvas.itemconfig(self.canvas_id, fill=self.app.COLOR_NONE)

    # -------------------------
    # Delete
    # -------------------------
    def delete(self) -> None:
        """
        Removes the Edge by also removing its connection to the
        Vertices to which it is connected.
        """

        print(f"removing edge {self.id}")
        if not self.app.editing:
            return
        if self not in self.a.edge or self not in self.b.edge:
            return
        self.a.edge.remove(self)
        self.a.neighbor.pop(b.get_id(), None)
        self.b.edge.remove(self)
        self.b.neighbor.pop(a.get_id(), None)
        self.canvas.delete(str(self.canvas_id))  # Remove line from canvas.
        self.canvas.delete(str(self.text_id))  # Remove text from canvas.
        self.app.edge.remove(self)
