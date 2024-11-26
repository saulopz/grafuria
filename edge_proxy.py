class EdgeProxy:
    def __init__(self, app, edge):
        self._app = app
        self._edge = edge

    get_id = lambda self: self._edge.get_id()

    set_weight = lambda self, w: self._edge.set_weight(w)

    get_weight = lambda self: self._edge.get_weight()

    get_state = lambda self: self._edge.get_state()

    set_state = lambda self, state: self._edge.set_state(state)

    def get_a(self):
        from vertex_proxy import VertexProxy

        return VertexProxy(self._app, self._edge.get_a())

    def get_b(self):
        from vertex_proxy import VertexProxy

        return VertexProxy(self._app, self._edge.get_b())
