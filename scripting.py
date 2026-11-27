"""
Script execution for Grafuria (Lua and Python).

Scripts never receive internal objects. They see the graph through
proxies (AppProxy, VertexProxy, EdgeProxy), which expose a stable and
limited API. This module does not depend on any user interface.

Everything the script asks from the application (log, step, stop,
parameters, ...) goes to a *host*. The graphical interface is one host
(App); headless.HeadlessHost is another. A host must provide:

    log(text)                  step()
    is_stopped() -> bool       get_var(name)
    set_solved(bool)           set_execution_time(seconds)
    area_add(x, y)             area_close()
"""

import json
import os
import random
from typing import Optional

from graph import Graph, Vertex, Edge
from state import State

LUA = "lua"
PYTHON = "python"

STATE_VALUES = {
    "NONE": State.NONE,
    "TESTING": State.TESTING,
    "ACTIVE": State.ACTIVE,
    "INVALID": State.INVALID,
}


def script_language(path: str) -> Optional[str]:
    ext = os.path.splitext(path)[1].lower()
    return {".lua": LUA, ".py": PYTHON}.get(ext)


def load_script_parameters(script: str) -> dict:
    """Reads the script parameters (script name with .json), without _min/_max."""
    path = os.path.splitext(script)[0] + ".json"
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {k: v for k, v in data.items() if not k.endswith(("_min", "_max"))}



# -------------------------
# Proxies
# -------------------------
class AppProxy:
    """The `app` object seen by scripts."""

    def __init__(self, host, graph: Graph, lua: bool):
        self._host = host
        self._graph = graph
        self._base = 1 if lua else 0  # Lua indexes start at 1

    def log(self, text):
        self._host.log(text)

    def area_add(self, x, y):
        self._host.area_add(x, y)

    def area_close(self):
        self._host.area_close()

    def set_execution_time(self, time):
        self._host.set_execution_time(time)

    def set_solved(self, solved):
        self._host.set_solved(solved)

    def is_stopped(self):
        return self._host.is_stopped()

    def step(self):
        self._host.step()

    def get_var(self, var_name):
        return self._host.get_var(var_name)

    def get_vertex_size(self):
        return self._graph.get_vertex_size()

    def get_vertex(self, index):
        return self._vertex(self._graph.get_vertex(index - self._base))

    def get_vertex_by_id(self, vertex_id):
        return self._vertex(self._graph.get_vertex_by_id(vertex_id))

    # Wrapping helpers (shared by the other proxies) ---------------------
    def _vertex(self, vertex: Optional[Vertex]):
        return None if vertex is None else VertexProxy(self, vertex)

    def _edge(self, edge: Optional[Edge]):
        return None if edge is None else EdgeProxy(self, edge)


class VertexProxy:
    """A vertex as seen by scripts."""

    def __init__(self, app: AppProxy, vertex: Vertex):
        self._app = app
        self._vertex = vertex

    def __eq__(self, other):
        return isinstance(other, VertexProxy) and other._vertex is self._vertex

    def __hash__(self):
        return hash(self._vertex.id)

    def get_type(self):
        return self._vertex.get_type()

    def get_raw_vertex(self):
        return self._vertex

    def get_id(self):
        return self._vertex.get_id()

    def get_name(self):
        return self._vertex.get_name()

    def get_x(self):
        return self._vertex.get_x()

    def get_y(self):
        return self._vertex.get_y()

    def get_coords(self):
        return self._vertex.get_coords()

    def get_state(self):
        return self._vertex.get_state()

    def set_state(self, state):
        self._vertex.set_state(state)

    def set_var(self, name, value):
        self._vertex.set_var(name, value)

    def get_var(self, name):
        return self._vertex.get_var(name)

    def is_connected(self, other):
        return self._vertex.is_connected(other._vertex)

    def get_edge_size(self):
        return self._vertex.get_edge_size()

    def get_active_edge_size(self):
        return self._vertex.get_active_edge_size()

    def get_edge(self, index):
        return self._app._edge(self._vertex.get_edge(index - self._app._base))

    def get_adjacent(self, edge):
        if edge is None:
            return None
        return self._app._vertex(self._vertex.get_adjacent(edge._edge))

    def get_edge_to(self, other):
        return self._app._edge(self._vertex.get_edge_to(other._vertex))


class EdgeProxy:
    """An edge as seen by scripts."""

    def __init__(self, app: AppProxy, edge: Edge):
        self._app = app
        self._edge = edge

    def __eq__(self, other):
        return isinstance(other, EdgeProxy) and other._edge is self._edge

    def __hash__(self):
        return hash(self._edge.id)

    def get_type(self):
        return self._edge.get_type()

    def get_raw_edge(self):
        return self._edge

    def get_id(self):
        return self._edge.get_id()

    def set_weight(self, weight):
        self._edge.set_weight(weight)

    def get_weight(self):
        return self._edge.get_weight()

    def get_state(self):
        return self._edge.get_state()

    def set_state(self, state):
        self._edge.set_state(state)

    def get_adjacent(self, vertex):
        if vertex is None:
            return None
        return self._app._vertex(self._edge.get_adjacent(vertex._vertex))

    def get_a(self):
        return self._app._vertex(self._edge.get_a())

    def get_b(self):
        return self._app._vertex(self._edge.get_b())


# -------------------------
# Execution
# -------------------------
def run_script(path: str, graph: Graph, host, seed: Optional[int] = None) -> None:
    """
    Runs the script at path over graph, talking to host. Exceptions
    raised by the script propagate to the caller.

    With seed, Python's `random` and Lua's `math.random` are seeded,
    so runs can be reproduced (unless the script reseeds itself).
    """
    language = script_language(path)
    if language is None:
        raise ValueError(f"Unsupported script extension: {path}")
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()

    if seed is not None:
        random.seed(seed)

    if language == LUA:
        from lupa import LuaRuntime  # imported here: Python scripts do not need it

        lua = LuaRuntime(unpack_returned_tuples=True)  # type: ignore
        lua.globals().app = AppProxy(host, graph, lua=True)
        lua.globals().State = lua.table_from(STATE_VALUES)
        if seed is not None:
            lua.execute(f"math.randomseed({int(seed)})")
        lua.execute(source)
    else:
        exec_globals = {
            "__name__": "__grafuria__",
            "app": AppProxy(host, graph, lua=False),
            # Same State used internally and by Lua. Scripts must not
            # redefine it.
            "State": State,
        }
        exec(compile(source, path, "exec"), exec_globals)
