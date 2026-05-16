import time
import random

app: "AppProxy" # type: ignore

class State:
    NONE = 0
    TESTING = 1
    ACTIVE = 2
    INVALID = 3
    
# NODE --------------------------------------------------------------------------

class Node:
    def __init__(self, vertex):
        self.vertex = vertex
        self.parent = None
        self.edge = None
        self.children = []

    def add_child(self, vertex):
        child = Node(vertex)
        child.parent = self
        child.edge = self.vertex.get_edge_to(vertex)
        self.children.append(child)
        return child

    def destroy(self):
        if self.parent and self.edge and self.edge.get_state() != State.ACTIVE:
            self.edge.set_state(State.NONE)

        if self.vertex.get_state() != State.ACTIVE:
            self.vertex.set_state(State.NONE)

        self.parent = None
        self.children = None

# NBFS --------------------------------------------------------------------------

class NBFS:

    def __init__(self, vertex, first):
        self.root = Node(vertex)
        self.first = first
        self.level = 0
        self.leaves = [self.root]
        self.found = False
        self.node = None
        self.new_vertices = 0

    def run(self):
        root = self.root
        first = self.first

        while self.leaves and not self.found and self.level < app.get_var("deep"):
            new_level = []
            for leaf in self.leaves:
                app.step()
                edge_size = leaf.vertex.get_edge_size()

                for i in range(edge_size):
                    app.step()
                    edge = leaf.vertex.get_edge(i)
                    child, self.found = self.select_child(root, leaf, edge, first)

                    if self.found:
                        self.node = child
                        break
                    elif child:
                        new_level.append(child)

                if app.is_stopped() or self.found:
                    break

            if not self.found:
                self.level += 1
                self.leaves = new_level

            if app.is_stopped():
                return

        if self.found:
            self.make_path(self.node)

        self.destroy(self.root)
        return self.new_vertices

    def select_child(self, root, node, edge, first):
        # Caso 1: Aresta já ativa - ignora
        if edge.get_state() == State.ACTIVE:
            return None, False

        adjacent = node.vertex.get_adjacent(edge)

        # Caso 2: Só na primeira iteração pode visitar vértices TESTING
        if not first and adjacent.get_state() == State.TESTING:
            return None, False

        # Caso 3: Ignora voltar para o pai
        if node.parent and adjacent.get_id() == node.parent.vertex.get_id():
            return None, False

        # Caso 4: Se é raiz sem conexões ativas ainda
        if adjacent.get_id() == root.vertex.get_id() and root.vertex.get_active_edge_size() == 0:
            return node.add_child(adjacent), True

        # Caso 5 e 6: Se vértice está ativo e é vizinho da raiz, caminho encontrado ou ignora
        if adjacent.get_state() == State.ACTIVE:
            edge_to_root = adjacent.get_edge_to(root.vertex)
            if edge_to_root and edge_to_root.get_state() == State.ACTIVE:
                return node.add_child(adjacent), True
            return None, False

        # Caso 7: Vértice livre, adiciona como filho
        edge.set_state(State.TESTING)
        adjacent.set_state(State.TESTING)
        return node.add_child(adjacent), False

    def make_path(self, node):
        # Se existir conexão ativa com raiz, desconecta para abrir caminho novo
        if node.vertex.get_state() == State.ACTIVE:
            edge = self.root.vertex.get_edge_to(node.vertex)
            if edge and edge.get_state() == State.ACTIVE:
                edge.set_state(State.NONE)
        # faz o caminho de volta para a raiz e ativa os vértices e arestas   
        n = node
        while n.parent:
            if n.vertex.get_state() != State.ACTIVE:
                self.new_vertices += 1
            n.vertex.set_state(State.ACTIVE)
            n.edge.set_state(State.ACTIVE)
            n = n.parent

    def destroy(self, node):
        if not node.children:
            return
        for child in node.children:
            if child:
                self.destroy(child)
                child.destroy()
        node.children = None


# NEMERTEA --------------------------------------------------------------------------

def nemertea():
    app.log("#Nemertea starting...")
    prev = None  # Vértice anterior ao atual
    path_size = 1  # Número de vértices no caminho
    vertex_size = app.get_vertex_size()  # Número de vértices no grafo

    # Seleciona um vértice aleatório para começar
    first_vertex = app.get_vertex(random.randint(0, vertex_size-1))
    current = first_vertex
    start_time = time.time()
    current.set_state(State.ACTIVE)  # Define o estado do vértice atual como ativo

    # Se é caminho Hamiltoniano (não ciclo), cria o primeiro caminho a partir do vértice inicial
    if not app.get_var("cycle"):
        path_size += first_path(current)

    first = True
    while True:
        while True:
            size = NBFS(current, first).run()
            path_size += size

            if app.is_stopped():
                return 0

            if size == 0:
                break
            first = False

        next = next_vertex(prev, current)
        prev = current
        current = next

        if app.is_stopped():
            return 0

        if current is None or current.get_id() == first_vertex.get_id() or path_size == vertex_size:
            break

    end_time = time.time()
    execution_time = end_time - start_time
    app.set_execution_time(execution_time)
    app.log(f"#Execution time: {execution_time} seconds")
    return path_size


def next_vertex(prev, current):
    edge_size = current.get_edge_size()
    for i in range(edge_size):
        e = current.get_edge(i)
        if e.get_state() == State.ACTIVE:
            adjacent = current.get_adjacent(e)
            if prev is None or adjacent.get_id() != prev.get_id():
                return adjacent
    return None


def first_path(root):
    root.set_state(State.ACTIVE)
    edge_size = root.get_edge_size()
    for i in range(edge_size):
        app.step()
        edge = root.get_edge(i)
        if edge.get_state() != State.ACTIVE:
            adjacent = root.get_adjacent(edge)
            if adjacent.get_state() != State.ACTIVE:
                edge.set_state(State.ACTIVE)
                return first_path(adjacent) + 1
        if app.is_stopped():
            return 0
    return 0


def evaluate(path_size):
    vertex_size = app.get_vertex_size()
    remaining_vertices = vertex_size - path_size
    if vertex_size == path_size:
        app.set_solved(True)
        app.log("#The algorithm nemertea solves the Hamiltonian path problem for this graph.")
    else:
        app.set_solved(False)
        app.log("#The algorithm nemertea did not solve the Hamiltonian path problem for this graph.")
        app.log(f"#Vertex on path: {path_size} of {vertex_size}, {remaining_vertices} left.")


# Inicialização do algoritmo

random.seed(time.time())
path_size = nemertea()
evaluate(path_size)
