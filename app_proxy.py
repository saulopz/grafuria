from vertex_proxy import VertexProxy


class AppProxy:
    def __init__(self, app):
        self._app = app

    def log(self, text):
        self._app.log(text)

    def area_add(self, x, y):
        self._app.area_add(x, y)

    def area_close(self):
        self._app.area_close()

    def set_execution_time(self, time):
        self._app.set_execution_time(time)

    def set_solved(self, solved):
        self._app.set_solved(solved)

    def is_stopped(self):
        return self._app.is_stopped()

    def get_vertex_size(self):
        return self._app.get_vertex_size()

    def get_var(self, var_name):
        return self._app.get_var(var_name)

    def step(self):
        self._app.step()

    def get_vertex(self, index):
        return VertexProxy(self._app, self._app.get_vertex(index - 1))
