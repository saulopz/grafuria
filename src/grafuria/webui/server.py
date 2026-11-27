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
                     editing (refused while a script runs):
                     {"cmd": "new_graph", "directed": bool}
                     {"cmd": "add_vertex", "x", "y"}   {"cmd": "add_edge", "a", "b"}
                     {"cmd": "move_vertex", "id", "x", "y"}
                     {"cmd": "rename_vertex", "id", "name"}
                     {"cmd": "set_weight", "id", "weight"}
                     {"cmd": "delete_vertex" | "delete_edge", "id"}
                     {"cmd": "set_directed", "directed": bool}
                     {"cmd": "save_graph", "name": "my_graph.json"}
  server -> browser  {"type": "files", "graphs": [...], "scripts": [...]}
                     {"type": "graph", "name", "graph": {...}}
                     {"type": "script", "name", "params": {...}}
                     {"type": "states", "v": {id: state}, "e": {id: state}}
                     {"type": "log", "lines": [{"text", "system"}]}
                     {"type": "area", "points": [[x, y], ...]}
                     {"type": "status", "running", "paused", "speed"}
                     {"type": "finished", "solved", "time"}
                     {"type": "vertex_added", "vertex"}  {"type": "edge_added", "edge"}
                     {"type": "vertex_moved" | "vertex_renamed" | "edge_weight", ...}
                     {"type": "vertex_removed", "id", "edges"}  {"type": "edge_removed", "id"}
                     {"type": "saved", "name"}
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
        return [self.script_message()]

    def script_message(self) -> dict:
        params = scripting.load_script_parameters(self.script)
        return {"type": "script", "name": self.script_name, "params": params}

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

    # --- editing (event loop) ----------------------------------------------
    @staticmethod
    def _vertex_json(v: Vertex) -> dict:
        return v.to_dict()

    @staticmethod
    def _edge_json(e: Edge) -> dict:
        return e.to_dict()

    def _editable(self) -> Optional[list]:
        """Returns an error message list if the graph cannot be edited now."""
        if self.running:
            return [{"type": "error", "message": "Stop the script before editing the graph."}]
        if self.graph is None:
            return [{"type": "error", "message": "No graph: choose one or create a new graph."}]
        return None

    def _vertex(self, command: dict) -> Optional[Vertex]:
        try:
            return self.graph.get_vertex_by_id(int(command.get("id")))
        except (TypeError, ValueError):
            return None

    def _edge(self, command: dict) -> Optional[Edge]:
        try:
            return self.graph.get_edge_by_id(int(command.get("id")))
        except (TypeError, ValueError):
            return None

    def new_graph(self, bidirectional: bool = True) -> list:
        self.stop()
        self.join(2)
        graph = Graph(bidirectional=bidirectional)
        graph.listener = self._on_model_change
        self.graph, self.graph_name = graph, ""
        self.take_updates()
        return [self.graph_message(), self.status()]

    def add_vertex(self, command: dict) -> list:
        x, y = float(command.get("x", 0)), float(command.get("y", 0))
        vertex = self.graph.add_vertex(str(command.get("name", "")), x, y)
        return [{"type": "vertex_added", "vertex": self._vertex_json(vertex)}]

    def add_edge(self, command: dict) -> list:
        try:
            a = self.graph.get_vertex_by_id(int(command.get("a")))
            b = self.graph.get_vertex_by_id(int(command.get("b")))
            weight = float(command.get("weight", 1))
        except (TypeError, ValueError):
            a = b = None
        if a is None or b is None:
            return [{"type": "error", "message": "Edge needs two existing vertices."}]
        try:
            edge = self.graph.add_edge(a, b, weight)
        except ValueError as e:
            return [{"type": "error", "message": str(e)}]
        return [{"type": "edge_added", "edge": self._edge_json(edge)}]

    def move_vertex(self, command: dict) -> list:
        vertex = self._vertex(command)
        if vertex is None:
            return [{"type": "error", "message": "Vertex not found."}]
        vertex.x, vertex.y = float(command.get("x", vertex.x)), float(command.get("y", vertex.y))
        return [{"type": "vertex_moved", "id": vertex.id, "x": vertex.x, "y": vertex.y}]

    def rename_vertex(self, command: dict) -> list:
        vertex = self._vertex(command)
        if vertex is None:
            return [{"type": "error", "message": "Vertex not found."}]
        vertex.name = str(command.get("name", ""))
        return [{"type": "vertex_renamed", "id": vertex.id, "name": vertex.name}]

    def set_weight(self, command: dict) -> list:
        edge = self._edge(command)
        if edge is None:
            return [{"type": "error", "message": "Edge not found."}]
        try:
            edge.weight = float(command.get("weight"))
        except (TypeError, ValueError):
            return [{"type": "error", "message": "The weight must be a number."}]
        return [{"type": "edge_weight", "id": edge.id, "weight": edge.weight}]

    def delete_vertex(self, command: dict) -> list:
        vertex = self._vertex(command)
        if vertex is None:
            return [{"type": "error", "message": "Vertex not found."}]
        edges = [e.id for e in vertex.edge]
        self.graph.remove_vertex(vertex)
        return [{"type": "vertex_removed", "id": vertex.id, "edges": edges}]

    def delete_edge(self, command: dict) -> list:
        edge = self._edge(command)
        if edge is None:
            return [{"type": "error", "message": "Edge not found."}]
        self.graph.remove_edge(edge)
        return [{"type": "edge_removed", "id": edge.id}]

    def set_directed(self, command: dict) -> list:
        self.graph.bidirectional = not bool(command.get("directed"))
        return [self.graph_message()]

    def save_graph(self, command: dict) -> list:
        """Saves into graphs/ under a plain file name (no folders)."""
        name = str(command.get("name", "")).strip()
        if not name.endswith(".json"):
            name += ".json"
        stem = name[:-5]
        if not stem or os.path.basename(name) != name or name.startswith("."):
            return [{"type": "error", "message": "Use a plain file name, e.g. my_graph.json."}]
        path = os.path.join(self.graphs_dir, name)
        try:
            self.graph.save(path)
        except OSError as e:
            return [{"type": "error", "message": f"Could not save: {e}"}]
        self.graph_name = name
        return [self.files(), {"type": "saved", "name": name}]

    # --- dispatch ------------------------------------------------------------
    EDIT_COMMANDS = {
        "add_vertex", "add_edge", "move_vertex", "rename_vertex", "set_weight",
        "delete_vertex", "delete_edge", "set_directed", "save_graph",
    }

    def handle(self, command: dict) -> list:
        cmd = command.get("cmd")
        if cmd in self.EDIT_COMMANDS:
            refused = self._editable()
            if refused:
                return refused
            return getattr(self, cmd)(command)
        if cmd == "new_graph":
            return self.new_graph(not bool(command.get("directed")))
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


def create_app(session: Optional[WebSession] = None, allowed_origins: Optional[set] = None,
               docs_dir: str = "docs") -> FastAPI:
    """
    Builds the web application. allowed_origins lists the page origins
    allowed to open the WebSocket (None allows any; only for tests).
    docs_dir is the documentation folder (tutorial and its images).
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

    @app.get("/tutorial")
    async def tutorial():
        return FileResponse(os.path.join(STATIC_DIR, "tutorial.html"))

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    if os.path.isdir(docs_dir):
        app.mount("/docs", StaticFiles(directory=docs_dir), name="docs")

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
            if session.script:
                await ws.send_json(session.script_message())
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


def parse_options(args: list) -> dict:
    """--graphs=DIR --scripts=DIR --port=N --no-browser"""
    options = {"graphs": "graphs", "scripts": "scripts", "port": None, "browser": True}
    for arg in args:
        if arg == "--no-browser":
            options["browser"] = False
        elif arg.startswith("--graphs="):
            options["graphs"] = arg.split("=", 1)[1]
        elif arg.startswith("--scripts="):
            options["scripts"] = arg.split("=", 1)[1]
        elif arg.startswith("--port="):
            options["port"] = int(arg.split("=", 1)[1])
        else:
            raise SystemExit(f"Unknown option: {arg}")
    return options


def main(args: list) -> int:
    """
    Starts the server on 127.0.0.1 and opens the browser.

    The first line printed is "Grafuria web: http://127.0.0.1:PORT/";
    tools (and the conformance tests) read the address from it.
    """
    import webbrowser

    import uvicorn

    options = parse_options(args)
    port = options["port"] or find_free_port()
    url = f"http://127.0.0.1:{port}/"
    origins = {f"http://127.0.0.1:{port}", f"http://localhost:{port}"}
    session = WebSession(options["graphs"], options["scripts"])
    app = create_app(session, allowed_origins=origins)
    if options["browser"]:
        threading.Timer(1.0, webbrowser.open, args=(url,)).start()
    print(f"Grafuria web: {url}  (Ctrl+C to quit)", flush=True)
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
    return 0
