from typing import Dict, List, Tuple, Union
import tkinter as tk
from state import State
from edge import Edge


# -------------------------
# Vertex Class
# -------------------------
class Vertex:
    """
    This class represents a Vertex on algorithm and it's representation
    on application to draw on canvas.

    Attributes
    ----------
    type: int
        Identify element type in application.
    id: int
        Vertex identification ID.
    app: App
        Context of interface application.
    canvas: tk.Canvas
        Canvas to draw it element.
    name: string
        Name of vertex. Starts with a void string.
    x, y: int
        Position x, y on canvas.
    state: int
        State of edge while execution.
    """

    id: int = 0  # id auto increment
    radius: int = 5
    width: int = 2

    def __init__(self, name: str, x: int, y: int, app, id=-1):
        self.type: int = app.VERTEX
        self.app = app
        self.canvas: tk.Canvas = self.app.canvas
        self.edge: List[Edge] = []
        self.neighbor = {}
        self.active_edges = 0
        self.name: str = name
        self.x: int = x
        self.y: int = y
        self.state: int = State.NONE
        if id == -1:
            Vertex.id = Vertex.id + 1
            self.id = Vertex.id
        else:
            if Vertex.id <= id:
                Vertex.id = id + 1
            self.id = id
        self.canvas_id = self.canvas.create_oval(
            self.x - Vertex.radius,
            self.y - Vertex.radius,
            self.x + Vertex.radius,
            self.y + Vertex.radius,
            width=Vertex.width,
            fill=self.app.COLOR_NONE,
            tags="vertex",
        )
        self.text_id = self.canvas.create_text(
            self.x,
            self.y - 15,
            text=self.name,
            anchor="center",
            font=("Arial", 12),
            tags="text",
        )
        self.canvas.tag_raise(self.canvas_id)
        self.canvas.tag_bind(self.canvas_id, "<Button-1>", self.mouse_down)
        self.canvas.tag_bind(self.canvas_id, "<Button-3>", self.connect)
        self.canvas.tag_bind(self.canvas_id, "<B1-Motion>", self.mouse_move)
        self.canvas.tag_bind(self.canvas_id, "<Any-Enter>", self.mouse_enter)
        self.canvas.tag_bind(self.canvas_id, "<Any-Leave>", self.mouse_leave)

    # -------------------------
    # Get JSON
    # -------------------------
    def get_json(self) -> Dict[str, int]:
        """
        Returns the JSON object representing this vertex. Useful
        for recording edge information into the graph file.
        """
        return {
            "name": self.name,
            "id": self.id,
            "x": self.x,
            "y": self.y,
        }

    # -------------------------
    # Get ID
    # -------------------------
    def get_id(self):
        """Returns the edge ID."""
        return self.id

    # -------------------------
    # Get Name
    # -------------------------
    def get_name(self):
        """Returns the name of vertex."""
        return self.name

    # -------------------------
    # Get X
    # -------------------------
    def get_x(self):
        """Returns x of position"""
        return self.x

    # -------------------------
    # Get Y
    # -------------------------
    def get_y(self):
        """Returns y of position"""
        return self.y

    # -------------------------
    # Get Coordinates
    # -------------------------
    def get_coords(self) -> Tuple[int, int]:
        """Returns the relative coordinates of this vertex on canvas."""
        coords = self.canvas.coords(self.canvas_id)
        x = coords[0] + (Vertex.radius * self.app.scale)
        y = coords[1] + (Vertex.radius * self.app.scale)
        return x, y

    # -------------------------
    # Get Edge Size
    # -------------------------
    def get_edge_size(self):
        """Returns the number of connections this vertex has."""
        return len(self.edge)

    # -------------------------
    # Get Edge
    # -------------------------
    def get_edge(self, index: int):
        """Returns the edge at position index."""
        if index < 0 or index >= len(self.edge):
            return None
        return self.edge[index]

    # -------------------------
    # Get Adjacent
    # -------------------------
    def get_adjacent(self, edge: Edge) -> "Vertex":
        """
        Returns the adjacent vertex that shares the connection
        of the edge passed as a parameter.
        """
        if not edge:
            return None
        if edge.get_a().get_id() == self.get_id():
            return edge.get_b()
        return edge.get_a()

    # -------------------------
    # Get Edge To
    # -------------------------
    def get_edge_to(self, other: "Vertex") -> Union[Edge, None]:
        """
        Returns edge that connect this vertex with other,
        passed by parameter, if exists this connection.

        Parameters
        ----------
        other : Vertex
            Other vertex to detect connection.

        Return
        ------
        edge: Edge
            Returns the edge of connection. None if not exists.
        """
        return self.neighbor.get(other.get_id())

    # -------------------------
    # Get Edge To
    # -------------------------
    def get_active_edge_size(self) -> int:
        """Return size of active connections of this vertex."""
        return self.active_edges

    # -------------------------
    # Change Active Edge
    # -------------------------
    def change_active_edge(self, edge, state):
        """
        Update active edge count if the edge state changes — avoids
        extra loops.
        Parameters
        ----------
        edge: Edge
            Edge to avaliate if is valid to change active edges.
        state: State
            New state to chage.
        """
        if edge.get_state() != State.ACTIVE and state == State.ACTIVE:
            self.active_edges += 1
        if edge.get_state() == State.ACTIVE and state != State.ACTIVE:
            self.active_edges -= 1

    # -------------------------
    # Get State
    # -------------------------
    def get_state(self):
        """Returns the state of this vertex."""
        return self.state

    # -------------------------
    # Set State
    # -------------------------
    def set_state(self, state: int) -> None:
        """Changes the state of this vertex."""
        self.state = state
        if self.app.animation:
            self.draw()

    # -------------------------
    # Draw
    # -------------------------
    def draw(self) -> None:
        """
        Draws the element on the screen. It is important when the state
        has changed.
        """
        if self.state == State.NONE:
            self.canvas.itemconfig(self.canvas_id, fill=self.app.COLOR_NONE)
        elif self.state == State.TESTING:
            self.canvas.itemconfig(self.canvas_id, fill=self.app.COLOR_OVER)
        elif self.state == State.ACTIVE:
            self.canvas.itemconfig(
                self.canvas_id,
                fill=self.app.COLOR_SELECTED,
            )
        elif self.state == State.INVALID:
            self.canvas.itemconfig(
                self.canvas.id,
                fill=self.app.COLOR_INVALID,
            )

    # -------------------------
    # On Mouse Enter
    # -------------------------
    def mouse_enter(self, event: tk.Event) -> None:
        """
        Event called when mouse is over vertex point,
        changing the vertex color.
        """
        if not self.app.editing:
            return
        if self.app.selected is not None and self.app.selected == self:
            return
        self.canvas.itemconfig(self.canvas_id, fill=self.app.COLOR_OVER)

    # -------------------------
    # On Mouse Leave
    # -------------------------
    def mouse_leave(self, event: tk.Event) -> None:
        """
        Event called when mouse is out of vertex point,
        changing the vertex color.
        """
        if not self.app.editing:
            return
        if self.app.selected is not None and self.app.selected == self:
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
    # On Mouse Move
    # -------------------------
    def mouse_move(self, event: tk.Event) -> None:
        """Event called when you are moving a vertex to other position."""
        if not self.app.editing:
            return
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        dx = x - self.x
        dy = y - self.y
        self.canvas.move(self.canvas_id, dx, dy)
        self.canvas.move(self.text_id, dx, dy)
        self.x = x
        self.y = y
        for e in self.edge:
            e.refresh()

    # -------------------------
    # On Mouse Down
    # -------------------------
    def mouse_down(self, event: tk.Event) -> None:
        """Event called when mouse was clicked over this vertex."""
        if not self.app.editing:
            self.app.set_statusbar(f"Vertex: {self.id}")
            return
        if self.app.selected is not None:
            self.app.selected.unselect()
            self.app.selected = None
        if self.app.selected_edge is not None:
            self.app.selected_edge.unselect()
            self.app.selected_edge = None
        self.select()
        self.app.selected = self
        self.x = self.canvas.canvasx(event.x)
        self.y = self.canvas.canvasy(event.y)
        self.app.set_statusbar(f"Vertex selected: {self.id}")
        self.app.vertex_id.config(state="normal")
        self.app.vertex_id.delete(0, tk.END)
        self.app.vertex_id.insert(0, self.id)
        self.app.vertex_id.config(state="readonly")
        self.app.vertex_name.delete(0, tk.END)
        self.app.vertex_name.insert(0, self.name)
        self.app.show_config_frame(self.app.vertex_config_frame)

    # -------------------------
    # Connect
    # -------------------------
    def connect(self, event: tk.Event) -> None:
        """
        When this vertex is selected and you click with Mouse Button-1
        in other vertex, you create a connection between this vertex and
        other, represented by a new edge object.
        """
        if self == self.app.selected:
            return
        selected = self.app.selected
        if selected is not None and self.app.selected.type == self.app.VERTEX:
            if not self.is_connected(self.app.selected):
                e = Edge(self.app.selected, self, 1, self.app)
                e.a = self.app.selected
                e.b = self
                e.b.neighbor[e.a.get_id()] = e
                e.a.neighbor[e.b.get_id()] = e
                self.edge.append(e)
                self.app.selected.edge.append(e)
                self.app.edge.append(e)

    # -------------------------
    # Is Connected
    # -------------------------
    def is_connected(self, other) -> bool:
        """
        Verifies if this vertex has a connection with other, passed
        by parameter.
        """
        other_id = other.get_id()
        self_id = self.get_id()

        for e in self.edge:
            a_id = e.get_a().get_id()
            b_id = e.get_b().get_id()

            if (a_id == self_id and b_id == other_id) or (
                a_id == other_id and b_id == self_id
            ):
                return True
        return False

    # -------------------------
    # Select
    # -------------------------
    def select(self) -> None:
        """Set this vertex as selected."""
        self.canvas.itemconfig(self.canvas_id, fill=self.app.COLOR_SELECTED)

    # -------------------------
    # Unselect
    # -------------------------
    def unselect(self) -> None:
        """Set this vertex as selected."""
        self.canvas.itemconfig(self.canvas_id, fill=self.app.COLOR_NONE)

    # -------------------------
    # Delete
    # -------------------------
    def delete(self) -> None:
        """
        Removes a Vertex. But it is necessary to delete all connections.
        The function has an auxiliary list, copied from the Edges
        list, to perform the iteration, because during the iteration the
        Edge can also ask the Vertex to delete it from the Vertex's Edges
        list. If this deletion is done and the iteration is being made in
        the original list, it generates a problem in the loop.
        """
        if not self.app.editing:
            return
        aux = self.edge.copy()
        for e in aux:
            e.delete()
        self.edge.clear()  # Clear the Edge list
        self.neighbor.clear()
        self.canvas.delete(str(self.canvas_id))  # Remove from canvas.
        self.canvas.delete(str(self.text_id))
        self.app.vertex.remove(self)
