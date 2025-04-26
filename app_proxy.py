from vertex_proxy import VertexProxy


class AppProxy:
    def __init__(self, app):
        self._app = app

    log = lambda self, text: self._app.log(text)

    area_add = lambda self, x, y: self._app.area_add(x, y)

    area_close = lambda self: self._app.area_close()

    set_solved = lambda self, solved: self._app.set_solved(solved)

    is_stopped = lambda self: self._app.is_stopped()

    get_vertex_size = lambda self: self._app.get_vertex_size()

    get_deep = lambda self: self._app.get_deep()

    step = lambda self: self._app.step()

    get_vertex = lambda self, index: VertexProxy(
        self._app, self._app.get_vertex(index - 1)
    )
