app: "AppProxy" # type: ignore

class State:
    NONE = 0
    TESTING = 1
    ACTIVE = 2
    INVALID = 3

path = []
end_vertex = None
found = False

def first_path(root):
    global found

    root.set_state(State.ACTIVE)
    path.append(root.get_id())

    edge_size = root.get_edge_size()
    for i in range(edge_size):
        edge = root.get_edge(i)
        if edge.get_state() != State.ACTIVE:
            adjacent = root.get_adjacent(edge)
            if adjacent.get_state() != State.ACTIVE:
                edge.set_state(State.ACTIVE)
                if end_vertex and adjacent.get_id() == end_vertex:
                    found = True
                    return 0
                app.step()
                return first_path(adjacent) + 1
    return 0

# --------------------------
# MAIN
# --------------------------

vertex_size = app.get_vertex_size()

# Escolhe vértice inicial
begin = None
begin_var = app.get_var("begin")
if begin_var == -1:
    import random, time
    random.seed(time.time())
    begin = app.get_vertex(random.randint(1, vertex_size))
else:
    begin = app.get_vertex(begin_var)

# Define vértice final, se existir
end_var = app.get_var("end")
if end_var > -1:
    end_vertex = end_var

path_size = first_path(begin) + 1
path_str = ", ".join(path)

app.log(f"#Path: {path_str}")
app.log(f"#Vertex on path: {path_size} of {vertex_size}")
app.set_solved(True)
