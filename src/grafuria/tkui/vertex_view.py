"""Visual representation of a graph vertex on the Tkinter canvas."""

import tkinter as tk

from ..core.graph import Vertex
from ..core.state import State
from . import theme


class VertexView:
    """
    Draws a Vertex (model) on the canvas and handles its mouse events.
    All graph data lives in the model; this class only keeps canvas ids.
    Must only be used from the Tkinter (main) thread.
    """

    radius: int = 5
    width: int = 2

    def __init__(self, app, model: Vertex):
        self.type: int = app.VERTEX
        self.app = app
        self.canvas: tk.Canvas = app.canvas
        self.model = model
        model.view = self
        self._drag_x = model.x
        self._drag_y = model.y
        r = VertexView.radius
        self.canvas_id = self.canvas.create_oval(
            model.x - r, model.y - r, model.x + r, model.y + r,
            width=VertexView.width,
            fill=theme.NONE,
            tags="vertex",
        )
        self.text_id = self.canvas.create_text(
            model.x, model.y - 15,
            text=model.name,
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

    @property
    def id(self) -> int:
        return self.model.id

    def get_coords(self):
        """Returns the centre of the vertex on the canvas (after zoom)."""
        coords = self.canvas.coords(self.canvas_id)
        x = coords[0] + (VertexView.radius * self.app.scale)
        y = coords[1] + (VertexView.radius * self.app.scale)
        return x, y

    def set_name(self, name: str) -> None:
        self.model.name = name
        self.canvas.itemconfig(self.text_id, text=name)

    def draw(self) -> None:
        """Updates the colour according to the model state."""
        colors = {
            State.NONE: theme.NONE,
            State.TESTING: theme.OVER,
            State.ACTIVE: theme.SELECTED,
            State.INVALID: theme.INVALID,
        }
        color = colors.get(self.model.state)
        if color is not None:
            self.canvas.itemconfig(self.canvas_id, fill=color)

    def select(self) -> None:
        self.canvas.itemconfig(self.canvas_id, fill=theme.SELECTED)

    def unselect(self) -> None:
        self.canvas.itemconfig(self.canvas_id, fill=theme.NONE)

    def destroy(self) -> None:
        """Removes the canvas items (the model is removed by the App)."""
        self.canvas.delete(self.canvas_id)
        self.canvas.delete(self.text_id)
        self.model.view = None

    # -------------------------
    # Mouse Events
    # -------------------------
    def mouse_enter(self, event: tk.Event) -> None:
        if not self.app.editing or self.app.selected is self:
            return
        self.canvas.itemconfig(self.canvas_id, fill=theme.OVER)

    def mouse_leave(self, event: tk.Event) -> None:
        if not self.app.editing:
            return
        if self.app.selected is self:
            self.select()
        else:
            self.unselect()

    def mouse_move(self, event: tk.Event) -> None:
        """Drags the vertex."""
        if not self.app.editing:
            return
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        dx = x - self._drag_x
        dy = y - self._drag_y
        self._drag_x, self._drag_y = x, y
        self.canvas.move(self.canvas_id, dx, dy)
        self.canvas.move(self.text_id, dx, dy)
        self.model.x += dx
        self.model.y += dy
        for e in self.model.edge:
            e.view.refresh()

    def mouse_down(self, event: tk.Event) -> None:
        if not self.app.editing:
            if self.app.debug:
                toggled = State.NONE if self.model.state == State.ACTIVE else State.ACTIVE
                self.model.set_state(toggled)
                self.app.draw()
                return
            self.app.status.set(f"Vertex: {self.id}")
            return
        self._drag_x = self.canvas.canvasx(event.x)
        self._drag_y = self.canvas.canvasy(event.y)
        self.app.select_vertex(self)

    def connect(self, event: tk.Event) -> None:
        """Right click: connects the selected vertex to this one."""
        selected = self.app.selected
        if selected is None or selected is self or selected.type != self.app.VERTEX:
            return
        if not self.model.is_connected(selected.model):
            self.app.create_edge(selected.model, self.model)
