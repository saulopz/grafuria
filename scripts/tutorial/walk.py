# Greedy walk (Grafuria tutorial), Python version of walk.lua
#
# Starts at a vertex and keeps moving to a neighbour that was not
# visited yet. Stops when the current vertex has no such neighbour.
# If it visits every vertex, it found a Hamiltonian path.

State: "State"  # type: ignore  (injected by Grafuria)
app: "AppProxy"  # type: ignore  (injected by Grafuria)

import random

# Parameter "start" (walk.json): a vertex id, or -1 for a random vertex.
if app.get_var("start") == -1:
    start = app.get_vertex(random.randint(0, app.get_vertex_size() - 1))  # Python: 0..n-1
else:
    start = app.get_vertex_by_id(app.get_var("start"))
if start is None:
    app.log("#Start vertex not found: check the 'start' parameter.")
else:
    current = start
    current.set_state(State.ACTIVE)
    visited = 1
    app.log(f"#Starting at vertex {current.get_id()}")

    while not app.is_stopped():
        next_vertex, next_edge = None, None

        # Look at the edges of the current vertex (Python counts from 0).
        for i in range(current.get_edge_size()):
            edge = current.get_edge(i)
            neighbour = current.get_adjacent(edge)
            if neighbour.get_state() == State.NONE:
                neighbour.set_state(State.TESTING)  # show the candidate
                app.step()                          # pause, as the speed says
                next_vertex, next_edge = neighbour, edge
                break

        if next_vertex is None:
            break  # stuck: every neighbour was visited

        next_edge.set_state(State.ACTIVE)
        next_vertex.set_state(State.ACTIVE)
        current = next_vertex
        visited += 1
        app.log(f"$Moved to vertex {current.get_id()}")

    total = app.get_vertex_size()
    app.log(f"#Visited {visited} of {total} vertices.")
    app.set_solved(visited == total)
