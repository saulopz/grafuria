app: "AppProxy" # type: ignore
class State:
    NONE = 0
    TESTING = 1
    ACTIVE = 2
    INVALID = 3

def show_connections(vertex):
    edge_size = vertex.get_edge_size()
    for i in range(edge_size):
        edge = vertex.get_edge(i)
        adjacent = vertex.get_adjacent(edge)
        edge.set_state(State.TESTING)
        adjacent.set_state(State.TESTING)
        app.log(f"#Edge ({edge.get_id()}): connects to Vertex {adjacent.get_id()} ({adjacent.get_name()}) at position ({adjacent.get_x()}, {adjacent.get_y()})")

def main():
    id = app.get_var("id")
    app.log(f"#Starting vertex retrieval... {id}")
    vertex = app.get_vertex_by_id(id)

    if vertex:
        vertex.set_state(State.ACTIVE)
        app.log(f"#Vertex found: {vertex.get_id()}")
        app.log(f"#Vertex Name: {vertex.get_name()}")
        app.log(f"#Vertex Position: {vertex.get_x()} , {vertex.get_y()}")

        show_connections(vertex)

        app.set_solved(True)
    else:
        app.log(f"#Vertex {id} not found")
        app.set_solved(False)

main()