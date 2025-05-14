class EdgeProxy:
    def __init__(self, app, edge):
        self._app = app
        self._edge = edge

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
        return self._edge.get_adjacent(vertex.get_raw_vertex())

    def get_a(self):
        from vertex_proxy import VertexProxy

        return VertexProxy(self._app, self._edge.get_a())

    def get_b(self):
        from vertex_proxy import VertexProxy

        return VertexProxy(self._app, self._edge.get_b())
