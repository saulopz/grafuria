"""
Web interface of Grafuria: a local server and the browser as the screen.

    python3 main.py --web

SECURITY: scripts run arbitrary Lua/Python code. This server is meant
for the user's own machine only: it listens on 127.0.0.1, accepts
WebSocket connections only from its own page (Origin check), and only
opens files inside graphs/ and scripts/. Do not expose it to a network.

Protocol (JSON over one WebSocket, /ws)

  browser -> server  {"cmd": "load_graph", "name": "cube.json"}
                     {"cmd": "load_script", "name": "nemertea/nemertea.lua"}
                     {"cmd": "play" | "pause" | "stop" | "clear"}
                     {"cmd": "speed", "value": 1..10}
  server -> browser  {"type": "files", "graphs": [...], "scripts": [...]}
                     {"type": "graph", "name", "graph": {...}}
                     {"type": "script", "name", "params": {...}}
                     {"type": "states", "v": {id: state}, "e": {id: state}}
                     {"type": "log", "lines": [{"text", "system"}]}
                     {"type": "area", "points": [[x, y], ...]}
                     {"type": "status", "running", "paused", "speed"}
                     {"type": "finished", "solved", "time"}
                     {"type": "error", "message"}
"""

import asyncio
import os
import threading
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from ..core import scripting
from ..core.execution import ScriptHost
from ..core.graph import Edge, Graph, Vertex

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
FLUSH_SECONDS = 0.016  # ~60 updates per second while a script runs


def safe_path(base_dir: str, name: str) -> Optional[str]:
    """Returns base_dir/name only if it stays inside base_dir."""
    base = os.path.realpath(base_dir)
    path = os.path.realpath(os.path.join(base, name))
    if path.startswith(base + os.sep) and os.path.isfile(path):
        return path
    return None


def list_files(base_dir: str, extensions: tuple) -> list:
    """Files under base_dir with the given extensions, as relative paths."""
    found = []
    for root, _, files in os.walk(base_dir):
        for name in files:
            if name.endswith(extensions):
                found.append(os.path.relpath(os.path.join(root, name), base_dir))
    return sorted(found)


class WebSession(ScriptHost):
    """
    State of the (single, local) user session and script host.

    The script thread only records what changed (under a lock); an
    asyncio task in the server sends the changes in batches.
    """

    def __init__(self, graphs_dir: str = "graphs", scripts_dir: str = "scripts"):
        super().__init__()
        self.graphs_dir = graphs_dir
        self.scripts_dir = scripts_dir
        self.graph: Optional[Graph] = None
        self.graph_name = ""
        self.script = ""
        self.script_name = ""
        self.speed = self.SPEED_MAX
        self._lock = threading.Lock()
        self._dirty_vertices: set = set()
        self._dirty_edges: set = set()
        self._outbox: list = []  # messages produced outside the event loop

    # --- model observation (any thread) ---------------------------------
    def _on_model_change(self, element) -> None:
        with self._lock:
            if isinstance(element, Vertex):
                self._dirty_vertices.add(element)
            elif isinstance(element, Edge):
                self._dirty_edges.add(element)

    def _post(self, message: dict) -> None:
        with self._lock:
            self._outbox.append(message)

    def take_updates(self) -> list:
        """Messages to send now: state changes first, then the rest in order."""
        with self._lock:
            vertices, self._dirty_vertices = self._dirty_vertices, set()
            edges, self._dirty_edges = self._dirty_edges, set()
            outbox, self._outbox = self._outbox, []
        messages = []
        if vertices or edges:
            messages.append({
                "type": "states",
                "v": {v.id: v.state for v in vertices},
                "e": {e.id: e.state for e in edges},
            })
        # Consecutive log messages become one.
        for message in outbox:
            if message["type"] == "log" and messages and messages[-1]["type"] == "log":
                messages[-1]["lines"].extend(message["lines"])
            else:
                messages.append(message)
        return messages

    # --- ScriptHost hooks (script thread) --------------------------------
    def get_speed(self) -> int:
        return self.speed

    def show_log(self, text: str, system: bool = False) -> None:
        self._post({"type": "log", "lines": [{"text": text, "system": system}]})

    def show_area(self, points: list) -> None:
        self._post({"type": "area", "points": [list(p) for p in points]})

    def on_finished(self, script, graph_file, error) -> None:
        self._post({"type": "finished", "solved": self.solved, "time": self.execution_time})
        # This runs inside the script thread, which is still alive here:
        # report it as finished explicitly.
        status = self.status()
        status["running"] = False
        status["paused"] = False
        self._post(status)

    # --- commands (event loop) -------------------------------------------
    def status(self) -> dict:
        return {"type": "status", "running": self.running, "paused": self.paused,
                "speed": self.speed}

    def files(self) -> dict:
        return {
            "type": "files",
            "graphs": list_files(self.graphs_dir, (".json",)),
            "scripts": list_files(self.scripts_dir, (".lua", ".py")),
        }

    def graph_message(self) -> dict:
        data = self.graph.to_dict(reindex=False) if self.graph else None
        return {"type": "graph", "name": self.graph_name, "graph": data}

    def load_graph(self, name: str) -> list:
        path = safe_path(self.graphs_dir, name)
        if path is None:
            return [{"type": "error", "message": f"Graph not found: {name}"}]
        self.stop()
        self.join(2)
        graph = Graph.load(path)
        graph.shuffle_edges()  # varies the traversal order, as the desktop does
        graph.listener = self._on_model_change
        self.graph, self.graph_name = graph, name
        self.take_updates()  # discard changes of the previous graph
        return [self.graph_message(), self.status()]

    def load_script(self, name: str) -> list:
        path = safe_path(self.scripts_dir, name)
        if path is None or scripting.script_language(path) is None:
            return [{"type": "error", "message": f"Script not found: {name}"}]
        self.script, self.script_name = path, name
        params = scripting.load_script_parameters(path)
        return [{"type": "script", "name": name, "params": params}]

    def play(self) -> list:
        if self.running:
            self.resume()
            return [self.status()]
        if self.graph is None or not self.script:
            return [{"type": "error", "message": "Choose a graph and a script first."}]
        self.graph.reset_states()
        params = scripting.load_script_parameters(self.script)
        self.start(self.script, self.graph, self.graph_name, params)
        return [self.status()]

    def clear(self) -> list:
        self.stop()
        self.join(2)
        if self.graph is not None:
            self.graph.reset_states()
        return [self.status()]

    def handle(self, command: dict) -> list:
        cmd = command.get("cmd")
        if cmd == "load_graph":
            return self.load_graph(str(command.get("name", "")))
        if cmd == "load_script":
            return self.load_script(str(command.get("name", "")))
        if cmd == "play":
            return self.play()
        if cmd == "pause":
            self.pause()
            return [self.status()]
        if cmd == "stop":
            self.stop()
            return [self.status()]
        if cmd == "clear":
            return self.clear()
        if cmd == "speed":
            self.speed = max(1, min(self.SPEED_MAX, int(command.get("value", self.SPEED_MAX))))
            return [self.status()]
        return [{"type": "error", "message": f"Unknown command: {cmd}"}]


def create_app(session: Optional[WebSession] = None, allowed_origins: Optional[set] = None) -> FastAPI:
    """
    Builds the web application. allowed_origins lists the page origins
    allowed to open the WebSocket (None allows any; only for tests).
    """
    session = session or WebSession()
    clients: set = set()

    async def broadcast(messages: list) -> None:
        for message in messages:
            for ws in list(clients):
                try:
                    await ws.send_json(message)
                except Exception:
                    clients.discard(ws)

    async def flusher() -> None:
        while True:
            await asyncio.sleep(FLUSH_SECONDS)
            if clients:
                messages = session.take_updates()
                if messages:
                    await broadcast(messages)

    @asynccontextmanager
    async def lifespan(app):
        task = asyncio.create_task(flusher())
        yield
        session.stop()
        task.cancel()

    app = FastAPI(title="Grafuria", docs_url=None, redoc_url=None, lifespan=lifespan)
    app.state.session = session

    @app.get("/")
    async def index():
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.websocket("/ws")
    async def websocket(ws: WebSocket):
        origin = ws.headers.get("origin")
        if allowed_origins is not None and origin not in allowed_origins:
            # Another website open in the browser must not drive the server.
            await ws.close(code=1008)
            return
        await ws.accept()
        clients.add(ws)
        try:
            await ws.send_json(session.files())
            if session.graph is not None:
                await ws.send_json(session.graph_message())
            await ws.send_json(session.status())
            while True:
                command = await ws.receive_json()
                await broadcast(session.handle(command))
        except WebSocketDisconnect:
            pass
        finally:
            clients.discard(ws)

    return app


def find_free_port(start: int = 8765) -> int:
    import socket

    for port in range(start, start + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("No free port found")


def main(args: list) -> int:
    """Starts the server on 127.0.0.1 and opens the browser."""
    import webbrowser

    import uvicorn

    port = find_free_port()
    url = f"http://127.0.0.1:{port}/"
    origins = {f"http://127.0.0.1:{port}", f"http://localhost:{port}"}
    app = create_app(allowed_origins=origins)
    if "--no-browser" not in args:
        threading.Timer(1.0, webbrowser.open, args=(url,)).start()
    print(f"Grafuria web: {url}  (Ctrl+C to quit)")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
    return 0
