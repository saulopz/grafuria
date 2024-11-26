from typing import Dict, List, Tuple, Union
import tkinter as tk
from state import State
from edge import Edge


class Vertex:
    id: int = 0  # id auto increment
    radius: int = 5
    width: int = 2

    def __init__(self, name: str, x: int, y: int, app, id=-1):
        self.type: int = app.VERTEX
        self.app = app
        self.canvas: tk.Canvas = self.app.canvas
        self.edge: List[Edge] = []
        self.name: str = name
        self.x: int = x
        self.y: int = y
        self.state: int = State.NONE
        self.name = name
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
            tag="vertex",
        )
        self.text_id = self.canvas.create_text(
            self.x,
            self.y - 15,
            text=self.name,
            anchor="center",
            font=("Arial", 12),
            tag="text",
        )
        self.canvas.tag_raise(self.canvas_id)
        self.canvas.tag_bind(self.canvas_id, "<Button-1>", self.mouseDown)
        self.canvas.tag_bind(self.canvas_id, "<Button-3>", self.connect)
        self.canvas.tag_bind(self.canvas_id, "<B1-Motion>", self.mouseMove)
        self.canvas.tag_bind(self.canvas_id, "<Any-Enter>", self.mouseEnter)
        self.canvas.tag_bind(self.canvas_id, "<Any-Leave>", self.mouseLeave)

    def get_json(self) -> Dict[str, int]:
        """Returns vertex information in JSON format."""
        return {
            "name": self.name,
            "id": self.id,
            "x": self.x,
            "y": self.y,
        }

    def get_id(self):
        """Returns the object ID."""
        return self.id

    def get_name(self):
        return self.name

    def get_edge_size(self):
        """Returns the number of vertex connections."""
        return len(self.edge)

    def get_edge(self, index: int):
        """Returns the edge at position index."""
        if index < 0 or index >= len(self.edge):
            return None
        return self.edge[index]

    def get_adjacent(self, edge: Edge):
        if not edge:
            return None
        if edge.get_a().get_id() == self.get_id():
            return edge.get_b()
        return edge.get_a()

    def get_edge_to(self, other: "Vertex") -> Union[Edge, None]:
        for e in self.edge:
            v = self.get_adjacent(e)
            if other.id == v.id:
                return e
        return None

    # Return size of active connections of this vertex
    def get_active_edge_size(self):
        conn = 0
        for e in self.edge:
            if e.get_state() == State.ACTIVE:
                conn += 1
        return conn

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
        if self.app.selected != None and self.app.selected == self:
            return
        self.canvas.itemconfig(self.canvas_id, fill=self.app.COLOR_OVER)

    def mouseLeave(self, event: tk.Event) -> None:
        if not self.app.editing:
            return
        if self.app.selected != None and self.app.selected == self:
            self.canvas.itemconfig(self.canvas_id, fill=self.app.COLOR_SELECTED)
        else:
            self.canvas.itemconfig(self.canvas_id, fill=self.app.COLOR_NONE)

    def mouseMove(self, event: tk.Event) -> None:
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

    def get_coords(self) -> Tuple[int, int]:
        coords = self.canvas.coords(self.canvas_id)
        x = coords[0] + (Vertex.radius * self.app.scale)
        y = coords[1] + (Vertex.radius * self.app.scale)
        return x, y

    def mouseDown(self, event: tk.Event) -> None:
        if not self.app.editing:
            self.app.set_statusbar(f"Vertex: {self.id}")
            return
        if self.app.selected != None:
            self.app.selected.unselect()
        if self.app.selected_edge != None:
            self.app.selected_edge.unselect()
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
        self.app.vertex_name.insert(
            0, self.name
        )  # Assume que o vértice tem um atributo 'name'
        self.app.show_config_frame(self.app.vertex_config_frame)

    def connect(self, event: tk.Event) -> None:
        if self == self.app.selected:
            return
        if self.app.selected != None and self.app.selected.type == self.app.VERTEX:
            if not self.is_connected(self.app.selected):
                e = Edge(self.app.selected, self, 1, self.app)
                e.a = self
                e.b = self.app.selected
                self.edge.append(e)
                self.app.selected.edge.append(e)
                self.app.edge.append(e)

    def is_connected(self, other) -> bool:
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

    def select(self) -> None:
        self.canvas.itemconfig(self.canvas_id, fill=self.app.COLOR_SELECTED)

    def unselect(self) -> None:
        self.canvas.itemconfig(self.canvas_id, fill=self.app.COLOR_NONE)

    def delete(self) -> None:
        """
        Removes a Vertex. But it is necessary to delete all Edges connected
        to it. The function has an auxiliary list, copied from the Edges
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
        self.app.vertex.remove(self)
        self.canvas.delete(str(self.canvas_id))  # Remove from canvas.
        self.canvas.delete(str(self.text_id))
