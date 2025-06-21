import time
import random

app: "AppProxy" # type: ignore

class State:
    NONE = 0
    TESTING = 1
    ACTIVE = 2
    INVALID = 3


# -------------------------
# BFSNode Class
# -------------------------
class BFSNode:
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
        The edge connecting this node to its parent.
    parent: Node
        The parent node in the tree.
    """

    def __init__(self, vertex, edge=None, parent=None):
        """
        Constructor method of Node to create a new BFSNode.

        Parameters
        ----------
        vertex: Vertex
            The vertex associated with this node.
        edge: Edge, optional
            The edge connecting this node to its parent. Defaults to None.
        parent: BFSNode, optional
            The parent node in the tree. Defaults to None.
        """
        self.vertex = vertex
        self.edge = edge
        self.parent = parent


# -------------------------
# BFS Class
# -------------------------
class BFS:
    """
    BFS Breadth First Search Class

    Attributes
    ----------
    origin_pos: integer
        ID of initial vertex in graph
    destination_pos: integer
        ID of end vertex in graph
    queue: list
        List of leaves of current level
    visited: list
        List of visited nodes
    found: boolean
        Flag to inform if we have reached the destination
    origin: BFSNode
        initial node with initial vertex
    destination: BFSNode
        destination node with end vertex
    """
    
    def __init__(self, origin_pos, destination_pos):
        """
        Constructor method of BFS

        Parameters
        ----------
        origin_pos: integer
            The ID of the initial vertex in the graph.
        destination_pos: integer
            The ID of the end vertex in the graph.
        """
        self.origin_pos = origin_pos
        self.destination_pos = destination_pos
        self.origin_id = app.get_vertex(self.origin_pos).get_id()
        self.destination_id = app.get_vertex(self.destination_pos).get_id()
        self.queue = []
        self.visited = []
        self.found = False
        self.origin = BFSNode(app.get_vertex(self.origin_pos))
        self.destination = None
        self.queue.append(self.origin)

    def run(self):
        """Executes the Breadth First Search algorithm"""
        app.log(f"$Algorithm Breadth First Search (BFS)")
        app.log(f"$Trying find a way from {self.origin_id} to {self.destination_id}")
        start_time = time.perf_counter()

        while self.queue and not self.found:
            current = self.queue.pop(0)  # Remove the first in the queue
            self.visited.append(current)

            current.vertex.set_state(State.TESTING)
            if current.edge:
                current.edge.set_state(State.TESTING)

            if current.vertex.get_id() == self.destination_id:
                self.found = True
                app.log("$Destination found!")
                app.set_solved(True)
                self.destination = current
                break

            edge_size = current.vertex.get_edge_size()
            for i in range(edge_size):
                edge = current.vertex.get_edge(i)
                neighbor = current.vertex.get_adjacent(edge)
                if neighbor.get_state() != State.TESTING:
                    node = BFSNode(neighbor, edge, current)
                    self.queue.append(node)

            app.step()
            if app.is_stopped():
                app.set_solved(False)
                return

        if not self.found:
            app.log("$Destination not found.")
            app.set_solved(False)
            return

        end_time = time.perf_counter()
        elapsed_time = end_time - start_time

        self.mark_path_as_active()
        app.log(f"$Algorithm:run Elapsed time: {elapsed_time:.6f} seconds")

    def mark_path_as_active(self):
        """Marks the path from origin to destination as active"""
        path = ""
        current = self.destination
        while current is not None:
            path = f"{current.vertex.get_id()} {path}"
            current.vertex.set_state(State.ACTIVE)
            if current.edge:
                current.edge.set_state(State.ACTIVE)
            current = current.parent
        app.log(f"$path [ {path.strip()} ]")


# -------------------------
# Main Execution
# -------------------------
"""
This script implements a Breadth First Search (BFS) algorithm to
find a path in a graph. It initializes a BFS instance with a
random starting and random destination vertex.
"""
random.seed(time.time())
vertex_size = app.get_vertex_size()
orig = random.randint(0, vertex_size-1)
dest = random.randint(0, vertex_size-1)
BFS(orig, dest).run()
