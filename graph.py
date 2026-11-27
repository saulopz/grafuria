"""
Graph model of Grafuria.

This module is the core of the application and must not depend on any
user interface toolkit. A Graph can be loaded, edited, saved and used by
scripts with or without a graphical interface (see headless.py).

The user interface observes changes through Graph.listener: every time
the state of a vertex or edge changes, the listener receives the
element. Each element has a `view` attribute that the interface may
use to attach its own visual representation.
"""

import json
import random
from typing import Callable, Dict, List, Optional

from state import State


# -------------------------
# Vertex Class
# -------------------------
class Vertex:
    """
    A vertex of the graph.

    Attributes
    ----------
    id: int
        Vertex identification, unique in its graph.
    name: str
        Name of the vertex (may be empty).
    x, y: float
        Position of the vertex (graph coordinates).
    state: int
        State of the vertex during an execution (see State).
    edge: list[Edge]
        Edges connected to this vertex.
    neighbor: dict[int, Edge]
        Edge to each adjacent vertex, indexed by the adjacent vertex id.
    vars: dict
        Free variables that scripts may attach to the vertex.
    view: object
        Visual representation, owned by the user interface (or None).
    """

    def __init__(self, graph: "Graph", vertex_id: int, name: str, x: float, y: float):
        self.graph = graph
        self.id = vertex_id
        self.name = name
        self.x = x
        self.y = y
        self.state = State.NONE
        self.edge: List["Edge"] = []
        self.neighbor: Dict[int, "Edge"] = {}
        self.active_edges = 0
        self.vars: dict = {}
        self.view = None

    def __repr__(self) -> str:
        return f"Vertex(id={self.id}, name={self.name!r})"

    def get_type(self) -> str:
        return "Vertex"

    def get_id(self) -> int:
        return self.id

    def get_name(self) -> str:
        return self.name

    def get_x(self) -> float:
        return self.x

    def get_y(self) -> float:
        return self.y

    def get_coords(self):
        return self.x, self.y

    def set_var(self, name, value) -> None:
        self.vars[name] = value

    def get_var(self, name):
        return self.vars.get(name)

    def get_state(self) -> int:
        return self.state

    def set_state(self, state: int) -> None:
        self.state = state
        self.graph.notify(self)

    def get_edge_size(self) -> int:
        return len(self.edge)

    def get_edge(self, index: int) -> Optional["Edge"]:
        """Returns the edge at position index (0-based) or None."""
        if index < 0 or index >= len(self.edge):
            return None
        return self.edge[index]

    def get_adjacent(self, edge: "Edge") -> Optional["Vertex"]:
        """Returns the vertex at the other end of edge."""
        if edge is None:
            return None
        return edge.get_adjacent(self)

    def get_edge_to(self, other: "Vertex") -> Optional["Edge"]:
        """Returns the edge connecting this vertex to other, or None."""
        return self.neighbor.get(other.id)

    def is_connected(self, other: "Vertex") -> bool:
        return other.id in self.neighbor

    def get_active_edge_size(self) -> int:
        """Returns how many connected edges are in State.ACTIVE."""
        return self.active_edges

    def shuffle_edges(self, rng: Optional[random.Random] = None) -> None:
        (rng or random).shuffle(self.edge)

    def to_dict(self) -> dict:
        return {"name": self.name, "id": self.id, "x": self.x, "y": self.y}


# -------------------------
# Edge Class
# -------------------------
class Edge:
    """
    A connection between vertices a and b.

    Edges are stored in the edge lists of both vertices, so scripts can
    traverse them from either end. In a directed graph (bidirectional
    False) the direction a -> b is only drawn by the interface.
    """

    def __init__(self, graph: "Graph", edge_id: int, a: Vertex, b: Vertex, weight: float = 1):
        self.graph = graph
        self.id = edge_id
        self.a = a
        self.b = b
        self.weight = weight
        self.state = State.NONE
        self.view = None

    def __repr__(self) -> str:
        return f"Edge(id={self.id}, {self.a.id}-{self.b.id})"

    def get_type(self) -> str:
        return "Edge"

    def get_id(self) -> int:
        return self.id

    def get_a(self) -> Vertex:
        return self.a

    def get_b(self) -> Vertex:
        return self.b

    def get_adjacent(self, vertex: Vertex) -> Optional[Vertex]:
        """Returns the other end of this edge, or None if vertex is not an end."""
        if vertex is self.a:
            return self.b
        if vertex is self.b:
            return self.a
        return None

    def get_weight(self) -> float:
        return self.weight

    def set_weight(self, weight: float) -> None:
        self.weight = weight

    def get_state(self) -> int:
        return self.state

    def set_state(self, state: int) -> None:
        # Keeps the active edge counter of both ends up to date, so
        # Vertex.get_active_edge_size() does not need to loop.
        was_active = self.state == State.ACTIVE
        is_active = state == State.ACTIVE
        if is_active and not was_active:
            self.a.active_edges += 1
            self.b.active_edges += 1
        elif was_active and not is_active:
            self.a.active_edges -= 1
            self.b.active_edges -= 1
        self.state = state
        self.graph.notify(self)

    def to_dict(self) -> dict:
        return {"id": self.id, "a": self.a.id, "b": self.b.id, "weight": self.weight}


# -------------------------
# Graph Class
# -------------------------
class Graph:
    """
    A graph: vertices, edges and the bidirectional flag.

    Attributes
    ----------
    bidirectional: bool
        False means the graph is drawn as directed (a -> b).
    vertex: list[Vertex]
        Vertices in insertion order.
    edge: list[Edge]
        Edges in insertion order.
    listener: callable or None
        Called with the element whenever a state changes.
    """

    def __init__(self, bidirectional: bool = True):
        self.bidirectional = bidirectional
        self.vertex: List[Vertex] = []
        self.edge: List[Edge] = []
        self._vertex_by_id: Dict[int, Vertex] = {}
        self._edge_by_id: Dict[int, Edge] = {}
        self._next_vertex_id = 0
        self._next_edge_id = 0
        self.listener: Optional[Callable[[object], None]] = None

    def notify(self, element) -> None:
        if self.listener is not None:
            self.listener(element)

    # --- Vertices --------------------------------------------------------

    def add_vertex(self, name: str = "", x: float = 0, y: float = 0,
                   vertex_id: Optional[int] = None) -> Vertex:
        if vertex_id is None:
            vertex_id = self._next_vertex_id
        if vertex_id in self._vertex_by_id:
            raise ValueError(f"Duplicated vertex id {vertex_id}")
        self._next_vertex_id = max(self._next_vertex_id, vertex_id + 1)
        vertex = Vertex(self, vertex_id, name, x, y)
        self.vertex.append(vertex)
        self._vertex_by_id[vertex_id] = vertex
        return vertex

    def remove_vertex(self, vertex: Vertex) -> None:
        for edge in list(vertex.edge):
            self.remove_edge(edge)
        self.vertex.remove(vertex)
        del self._vertex_by_id[vertex.id]

    def get_vertex(self, index: int) -> Optional[Vertex]:
        """Returns the vertex at position index (0-based) or None."""
        if index < 0 or index >= len(self.vertex):
            return None
        return self.vertex[index]

    def get_vertex_by_id(self, vertex_id: int) -> Optional[Vertex]:
        return self._vertex_by_id.get(vertex_id)

    def get_vertex_size(self) -> int:
        return len(self.vertex)

    # --- Edges -----------------------------------------------------------

    def add_edge(self, a: Vertex, b: Vertex, weight: float = 1,
                 edge_id: Optional[int] = None) -> Edge:
        if a is b:
            raise ValueError("Loops (edges from a vertex to itself) are not supported")
        if a.is_connected(b):
            raise ValueError(f"Vertices {a.id} and {b.id} are already connected")
        if edge_id is None:
            edge_id = self._next_edge_id
        if edge_id in self._edge_by_id:
            raise ValueError(f"Duplicated edge id {edge_id}")
        self._next_edge_id = max(self._next_edge_id, edge_id + 1)
        edge = Edge(self, edge_id, a, b, weight)
        self.edge.append(edge)
        self._edge_by_id[edge_id] = edge
        a.edge.append(edge)
        b.edge.append(edge)
        a.neighbor[b.id] = edge
        b.neighbor[a.id] = edge
        return edge

    def remove_edge(self, edge: Edge) -> None:
        if edge.state == State.ACTIVE:
            edge.a.active_edges -= 1
            edge.b.active_edges -= 1
        edge.a.edge.remove(edge)
        edge.b.edge.remove(edge)
        edge.a.neighbor.pop(edge.b.id, None)
        edge.b.neighbor.pop(edge.a.id, None)
        self.edge.remove(edge)
        del self._edge_by_id[edge.id]

    def get_edge_by_id(self, edge_id: int) -> Optional[Edge]:
        return self._edge_by_id.get(edge_id)

    # --- Execution helpers -----------------------------------------------

    def reset_states(self) -> None:
        """Puts every vertex and edge back in State.NONE and clears script variables."""
        for edge in self.edge:
            edge.set_state(State.NONE)
        for vertex in self.vertex:
            vertex.set_state(State.NONE)
            vertex.vars.clear()
            vertex.active_edges = 0

    def shuffle_edges(self, rng: Optional[random.Random] = None) -> None:
        """Shuffles the edge order of every vertex (changes traversal order)."""
        for vertex in self.vertex:
            vertex.shuffle_edges(rng)

    # --- Serialization ---------------------------------------------------

    def to_dict(self, reindex: bool = True) -> dict:
        """
        Returns the graph in the Grafuria JSON format. With reindex, ids
        are renumbered 0..n-1 in list order (as Grafuria always saved).
        """
        if reindex:
            v_map = {v.id: i for i, v in enumerate(self.vertex)}
        else:
            v_map = {v.id: v.id for v in self.vertex}
        vertices = []
        for v in self.vertex:
            data = v.to_dict()
            data["id"] = v_map[v.id]
            vertices.append(data)
        edges = []
        for i, e in enumerate(self.edge):
            data = e.to_dict()
            data["id"] = i if reindex else e.id
            data["a"] = v_map[e.a.id]
            data["b"] = v_map[e.b.id]
            edges.append(data)
        return {"bidirectional": self.bidirectional, "vertex": vertices, "edge": edges}

    @classmethod
    def from_dict(cls, data: dict) -> "Graph":
        graph = cls(bidirectional=data.get("bidirectional", True))
        for v in data.get("vertex", []):
            graph.add_vertex(v.get("name", ""), v["x"], v["y"], v["id"])
        for e in data.get("edge", []):
            a = graph.get_vertex_by_id(e["a"])
            b = graph.get_vertex_by_id(e["b"])
            if a is None or b is None:
                raise ValueError(f"Edge {e.get('id')} refers to a missing vertex")
            graph.add_edge(a, b, e.get("weight", 1), e["id"])
        return graph

    @classmethod
    def load(cls, filename: str) -> "Graph":
        with open(filename, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))

    def save(self, filename: str) -> None:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f)
