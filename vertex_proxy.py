class VertexProxy:
    def __init__(self, app, vertex):
        self._app = app
        self._vertex = vertex

    def get_raw_vertex(self):
        return self._vertex

    def get_id(self):
        return self._vertex.get_id()

    def get_name(self):
        return self._vertex.get_name()

    def get_x(self):
        return self._vertex.get_x()

    def get_y(self):
        self._vertex.get_y()

    def get_coords(self):
        return self._vertex.get_coords()

    def get_state(self):
        return self._vertex.get_state()

    def set_state(self, state):
        self._vertex.set_state(state)

    def is_connected(self, other):
        return self._vertex.is_connected(other.get_raw_vertex())

    def get_edge_size(self):
        return self._vertex.get_edge_size()

    def get_active_edge_size(self):
        return self._vertex.get_active_edge_size()

    def get_edge(self, index):
        from edge_proxy import EdgeProxy

        return EdgeProxy(self._app, self._vertex.get_edge(index - 1))

    def get_adjacent(self, edge):
        adjacent = self._vertex.get_adjacent(edge.get_raw_edge())
        return VertexProxy(self._app, adjacent)

    def get_edge_to(self, other):
        from edge_proxy import EdgeProxy

        edge = self._vertex.get_edge_to(other.get_raw_vertex())
        if edge is None:
            return None
        return EdgeProxy(self._app, edge)
