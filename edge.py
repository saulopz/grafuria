import tkinter as tk
from typing import Dict
from state import State
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vertex import Vertex


class Edge:
    """
    This class represents a Edge on algorithm and it's representation
    on application to draw on canvas.

    Attributes
    ----------
    id : int
        Static attribute that represents an element identification

    type (int):
        Identify element type in application.
    app (App):
        Context of interface application.
    canvas (tk.Canvas):
        Canvas to draw it element.
    a (Vertex):
        First vertex connection.
    b (Vertex):
        Second vertex connection.
    state (int):
        State of edge while execution.
    """

    id: int = 0  # Element identification (static)

    def __init__(self, a, b, w, app, id: int = -1):
        """
        Constructor to create a edge object. A edge object is aways
        connect with two vertex.

        Args:
            a (Vertex): first edge connection
            b (Vertex): second edge connection
            id (int):
        """
        self.type: int = app.EDGE  # Identify element type in application
        self.app = app  # Context of interface application
        self.canvas: tk.Canvas = app.canvas  # Canvas to draw it
        self.a = a  # First vertex connection
        self.b = b  # Second vertex connection
        self.weight: float = w  # Connection weight
        self.state: int = State.NONE  # State of edge while execution
        if id == -1:  # Apply an autoincrement id if
            Edge.id = Edge.id + 1  #   we not pass id as parameter
            self.id = Edge.id
        else:  # Or an existing ID if application is
            if Edge.id <= id:  #   loading a graph file
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
                arrowshape=(10 * self.scale, 10 * self.scale, 5 * self.scale),
                width=2,
                fill=self.app.COLOR_NONE,
                tags="edge",
            )
        else:
            self.canvas_id = self.canvas.create_line(
                a.x, a.y, b.x, b.y, width=2, fill=self.app.COLOR_NONE, tags="edge"
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
        self.canvas.tag_bind(self.canvas_id, "<Button-1>", self.mouseDown)
        self.canvas.tag_bind(self.canvas_id, "<Any-Enter>", self.mouseEnter)
        self.canvas.tag_bind(self.canvas_id, "<Any-Leave>", self.mouseLeave)

    def get_json(self) -> Dict[str, int]:
        return {
            "id": self.id,
            "a": self.a.id,
            "b": self.b.id,
            "weight": self.weight,
        }

    def get_id(self):
        return self.id

    def get_a(self):
        return self.a

    def get_b(self):
        return self.b

    def set_weight(self, w: int) -> None:
        self.weight = w

    def get_weight(self) -> int:
        return self.weight

    def get_state(self):
        return self.state

    def set_state(self, state: int) -> None:
        self.state = state
        if self.app.animation:
            self.draw()

    def draw(self) -> None:
        if self.state == State.NONE:
            self.canvas.itemconfig(self.canvas_id, fill=self.app.COLOR_NONE)
        elif self.state == State.TESTING:
            self.canvas.itemconfig(self.canvas_id, fill=self.app.COLOR_OVER)
        elif self.state == State.ACTIVE:
            self.canvas.itemconfig(self.canvas_id, fill=self.app.COLOR_SELECTED)
        elif self.state == State.INVALID:
            self.canvas.itemconfig(self.canvas.id, fill=self.app.COLOR_INVALID)

    # HANDLERS OF INTERFACE EVENTS ---------------------------------------------

    def mouseEnter(self, event: tk.Event) -> None:
        if not self.app.editing:
            return
        if self.app.selected_edge != None and self.app.selected_edge == self:
            return
        self.canvas.itemconfig(self.canvas_id, fill=self.app.COLOR_OVER)

    def mouseLeave(self, event: tk.Event) -> None:
        if not self.app.editing:
            return
        if self.app.selected_edge != None and self.app.selected_edge == self:
            self.canvas.itemconfig(self.canvas_id, fill=self.app.COLOR_SELECTED)
        else:
            self.canvas.itemconfig(self.canvas_id, fill=self.app.COLOR_NONE)

    def mouseDown(self, event: tk.Event) -> None:
        if not self.app.editing:
            self.app.set_statusbar("Edge: " + str(self.id))
            return
        if self.app.selected_edge != None:
            self.app.selected_edge.unselect()
        if self.app.selected != None:
            self.app.selected.unselect()
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

    def refresh(self) -> None:
        ax, ay = self.a.get_coords()
        bx, by = self.b.get_coords()
        self.canvas.coords(self.canvas_id, ax, ay, bx, by)
        x_middle = (ax + bx) / 2
        y_middle = (ay + by) / 2
        self.canvas.coords(self.text_id, x_middle, y_middle)

    def select(self) -> None:
        self.canvas.itemconfig(self.canvas_id, fill=self.app.COLOR_SELECTED)

    def unselect(self) -> None:
        self.canvas.itemconfig(self.canvas_id, fill=self.app.COLOR_NONE)

    def delete(self) -> None:
        """
        Removes the Edge by also removing its connection to the
        Vertices to which it is connected.
        """
        if not self.app.editing:
            return
        self.b.edge.remove(self)
        self.a.edge.remove(self)
        self.app.edge.remove(self)
        self.canvas.delete(str(self.canvas_id))  # Remove line from canvas.
        self.canvas.delete(str(self.text_id)) # Remove text from canvas.
