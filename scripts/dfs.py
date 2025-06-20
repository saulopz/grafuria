import time
import random

app: "AppProxy" # type: ignore

class State:
    NONE = 0
    TESTING = 1
    ACTIVE = 2
    INVALID = 3

# -------------------------
# DFSNode Class
# -------------------------
class DFSNode:
    """
    Represents a node in a tree structure.

    A Node is used to store a reference to a vertex and the edge
    that connects it to its parent node. This is particularly
    useful in graph traversal algorithms or tree representations.

    Attributes
    ----------
    vertex: Vertex
        The vertex associated with this node.
    edge: Edge
        The edge connecting this node to its previous vertex.
    """

    def __init__(self, vertex, edge=None):
        """
        Constructor method of Node to create a new DFSNode.

        Parameters
        ----------
        vertex: Vertex
            The current vertex associated with this node.
        edge: Edge, optional
            The edge connecting this node to its previous vertex.
        """
        self.vertex = vertex
        self.edge = edge


# -------------------------
# DFS Class
# -------------------------
class DFS:
    """
    DFS Depth-First Search Class

    Attributes
    ----------
    origin_pos: integer
        ID of initial vertex in graph.
    destination_pos: integer
        ID of end vertex in graph.
    found: boolean
        Flag to inform if we have reached the destination.
    origin: DFSNode
        Initial node with initial vertex.
    path: string
        Creates the path with vertex id from origin to destination.
    """

    def __init__(self, origin_pos, destination_pos):
        """
        Constructor method of DFS.

        Parameters
        ----------
        origin_pos: integer
            The ID of the initial vertex in the graph.
        destination_pos: integer
            The ID of the end vertex in the graph.
        """
        self.origin_pos = origin_pos
        self.destination_pos = destination_pos
        self.found = False
        self.origin = DFSNode(app.get_vertex(self.origin_pos))
        self.path = ""

    def run(self):
        """Executes the Depth-First Search algorithm."""
        app.log(f"$Algorithm Depth-First Search (DFS)")
        app.log(f"$Trying find a way from {self.origin_pos} to {self.destination_pos}")
        start_time = time.perf_counter()

        if self.origin:
            self.visit(self.origin)

        end_time = time.perf_counter()
        elapsed_time = end_time - start_time

        app.log(f"$PATH: [{self.path.strip()} ]")
        app.log(f"$Algorithm:run Elapsed time: {elapsed_time:.6f} seconds")

    def visit(self, current: DFSNode):
        """
        Recursive method thats open a node to continue searching for
        the path of solution.

        Parameters
        ----------
        current: DFSNode
            Current node to open children.
        """
        if current is None:
            app.log("$Error: Input node is None.")
            return

        current.vertex.set_state(State.TESTING)
        app.step()
        if app.is_stopped():
            return

        edge_size = current.vertex.get_edge_size()
        for i in range(edge_size):
            edge = current.vertex.get_edge(i)
            neighbor = current.vertex.get_adjacent(edge)
            if neighbor and neighbor.get_state() == State.NONE:
                edge.set_state(State.TESTING)
                neighbor.set_state(State.TESTING)

                if neighbor.get_id() == self.destination_pos:
                    self.found = True
                    app.set_solved(True)
                    neighbor.set_state(State.ACTIVE)
                    edge.set_state(State.ACTIVE)
                    self.path = f" {neighbor.get_id()}{self.path}"
                    break

                node = DFSNode(neighbor, edge)
                self.visit(node)

                if self.found:
                    break

                app.step()
                if app.is_stopped():
                    app.set_solved(False)
                    return

        app.step()
        if self.found:
            current.vertex.set_state(State.ACTIVE)
            self.path = f" {current.vertex.get_id()}{self.path}"
            if current.edge:
                current.edge.set_state(State.ACTIVE)


# -------------------------
# Main Execution
# -------------------------
"""
This script implements a Depth-First Search (DFS) algorithm to
find a path in a graph. It initializes a BFS instance with a
random starting and random destination vertex.
"""
random.seed(time.time())
vertex_size = app.get_vertex_size()
orig = app.get_vertex(random.randint(0, vertex_size-1)).get_id()
dest = app.get_vertex(random.randint(0, vertex_size-1)).get_id()
DFS(orig, dest).run()
