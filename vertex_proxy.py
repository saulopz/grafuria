class VertexProxy:
    def __init__(self, app, vertex):
        self._app = app
        self._vertex = vertex

    get_id = lambda self: self._vertex.get_id()

    get_name = lambda self: self._vertex.get_name()

    get_x = lambda self: self._vertex.get_x()

    get_y = lambda self: self._vertex.get_y()

    get_coords = lambda self: self._vertex.get_coords()

    get_state = lambda self: self._vertex.get_state()

    set_state = lambda self, state: self._vertex.set_state(state)

    is_connected = lambda self, other: self._vertex.is_connected(other._other)

    get_edge_size = lambda self: self._vertex.get_edge_size()

    get_active_edge_size = lambda self: self._vertex.get_active_edge_size()

    def get_edge(self, index):
        from edge_proxy import EdgeProxy

        return EdgeProxy(self._app, self._vertex.get_edge(index - 1))

    def get_adjacent(self, edge):
        adjacent = self._vertex.get_adjacent(
            edge._edge
        )  # Gets real object from wrapper
        return VertexProxy(self._app, adjacent)  # returns wrapper object

    def get_edge_to(self, other):
        from edge_proxy import EdgeProxy

        return EdgeProxy(self._app, self._vertex.get_edge_to(other._vertex))
