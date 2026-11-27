"""Visual representation of a graph edge on the Tkinter canvas."""

import tkinter as tk

from ..core.graph import Edge
from ..core.state import State
from . import theme


class EdgeView:
    """
    Draws an Edge (model) on the canvas and handles its mouse events.
    Must only be used from the Tkinter (main) thread.
    """

    def __init__(self, app, model: Edge):
        self.type: int = app.EDGE
        self.app = app
        self.canvas: tk.Canvas = app.canvas
        self.model = model
        model.view = self
        # Canvas coordinates of the ends (they differ from the model
        # coordinates after zooming).
        ax, ay = model.a.view.get_coords()
        bx, by = model.b.view.get_coords()
        self.canvas_id = self._create_line(ax, ay, bx, by)
        self.text_id = self.canvas.create_text(
            (ax + bx) / 2, (ay + by) / 2,
            text=str(model.weight),
            anchor="center",
            font=("Arial", 10),
            fill="black",
            tags="text",
        )
        if not self.app.settings.show_weight:
            self.canvas.itemconfig(self.text_id, state="hidden")

    @property
    def id(self) -> int:
        return self.model.id

    def _create_line(self, ax, ay, bx, by) -> int:
        """Creates the line, with an arrow when the graph is directed."""
        options = dict(width=2, fill=theme.NONE, tags="edge")
        if not self.app.graph.bidirectional:
            s = self.app.scale
            options.update(arrow="last", arrowshape=(10 * s, 10 * s, 5 * s))
        line = self.canvas.create_line(ax, ay, bx, by, **options)
        self.canvas.tag_lower(line)
        self.canvas.tag_bind(line, "<Button-1>", self.mouse_down)
        self.canvas.tag_bind(line, "<Any-Enter>", self.mouse_enter)
        self.canvas.tag_bind(line, "<Any-Leave>", self.mouse_leave)
        return line

    def rebuild_line(self) -> None:
        """Recreates the line (e.g. after changing directed/undirected)."""
        ax, ay = self.model.a.view.get_coords()
        bx, by = self.model.b.view.get_coords()
        self.canvas.delete(self.canvas_id)
        self.canvas_id = self._create_line(ax, ay, bx, by)

    def set_weight(self, weight: float, text: str) -> None:
        self.model.weight = weight
        self.canvas.itemconfig(self.text_id, text=text)

    def draw(self) -> None:
        """Updates colour, width and weight label according to the model."""
        styles = {
            State.NONE: (theme.NONE, 2),
            State.TESTING: (theme.OVER, 2),
            State.ACTIVE: (theme.SELECTED, 4),
            State.INVALID: (theme.INVALID, 2),
        }
        style = styles.get(self.model.state)
        if style is not None:
            self.canvas.itemconfig(self.canvas_id, fill=style[0], width=style[1])
        self.canvas.itemconfig(
            self.text_id, state="normal" if self.app.settings.show_weight else "hidden"
        )

    def refresh(self) -> None:
        """Follows the vertices when they are moved."""
        ax, ay = self.model.a.view.get_coords()
        bx, by = self.model.b.view.get_coords()
        self.canvas.coords(self.canvas_id, ax, ay, bx, by)
        self.canvas.coords(self.text_id, (ax + bx) / 2, (ay + by) / 2)

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
        if not self.app.editing or self.app.selected_edge is self:
            return
        self.canvas.itemconfig(self.canvas_id, fill=theme.OVER)

    def mouse_leave(self, event: tk.Event) -> None:
        if not self.app.editing:
            return
        if self.app.selected_edge is self:
            self.select()
        else:
            self.unselect()

    def mouse_down(self, event: tk.Event) -> None:
        if not self.app.editing:
            if self.app.debug:
                toggled = State.NONE if self.model.state == State.ACTIVE else State.ACTIVE
                self.model.set_state(toggled)
                self.app.draw()
                return
            self.app.status.set(f"Edge: {self.id}")
            return
        self.app.select_edge(self)
