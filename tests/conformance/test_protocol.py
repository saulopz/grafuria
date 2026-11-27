"""
Conformance tests of the Grafuria web server.

They talk to the server only through HTTP and the WebSocket protocol
(see the docstring of src/grafuria/webui/server.py), so any
implementation can be checked: the Python one today, the Go one later.

The server is started as an external program:

    GRAFURIA_SERVER="./grafuria-go --web" python3 -m unittest tests/conformance/test_protocol.py

Without GRAFURIA_SERVER, the Python server is used. The command must
accept these options and print a line containing the address:

    --no-browser --graphs=DIR --scripts=DIR
    "... http://127.0.0.1:PORT/ ..."

The tests work on temporary copies of graphs/ and scripts/, so they
never write to the project folders.
"""

import json
import os
import queue
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from websockets.exceptions import ConnectionClosed, InvalidStatus
    from websockets.sync.client import connect
    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False

DEFAULT_SERVER = f"{shlex.quote(sys.executable)} {shlex.quote(os.path.join(ROOT, 'main.py'))} --web"
TIMEOUT = 20  # seconds for any single expectation

BROKEN_LUA = 'local x = 1\nlocal n = nil\nprint(n.field)\n'


class Server:
    """Starts the server under test with temporary graphs/ and scripts/."""

    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.graphs = os.path.join(self.tmp.name, "graphs")
        self.scripts = os.path.join(self.tmp.name, "scripts")
        shutil.copytree(os.path.join(ROOT, "graphs"), self.graphs)
        shutil.copytree(os.path.join(ROOT, "scripts"), self.scripts,
                        ignore=shutil.ignore_patterns("__pycache__"))
        os.makedirs(os.path.join(self.scripts, "conformance"))
        with open(os.path.join(self.scripts, "conformance", "broken.lua"), "w") as f:
            f.write(BROKEN_LUA)
        command = shlex.split(os.environ.get("GRAFURIA_SERVER", DEFAULT_SERVER))
        command += ["--no-browser", f"--graphs={self.graphs}", f"--scripts={self.scripts}"]
        # cwd is the project: Lua scripts use dofile("scripts/...").
        self.process = subprocess.Popen(
            command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        self.url = self._read_address()

    def _read_address(self) -> str:
        lines: queue.Queue = queue.Queue()

        def reader():
            for line in self.process.stdout:
                lines.put(line)

        threading.Thread(target=reader, daemon=True).start()
        deadline = time.time() + TIMEOUT
        seen = []
        while time.time() < deadline:
            try:
                line = lines.get(timeout=0.2)
            except queue.Empty:
                if self.process.poll() is not None:
                    break
                continue
            seen.append(line)
            match = re.search(r"http://127\.0\.0\.1:\d+/", line)
            if match:
                url = match.group(0)
                self._wait_until_up(url, deadline)
                return url
        self.stop()
        raise RuntimeError("server did not print its address:\n" + "".join(seen))

    @staticmethod
    def _wait_until_up(url: str, deadline: float) -> None:
        while time.time() < deadline:
            try:
                urllib.request.urlopen(url, timeout=1).read()
                return
            except OSError:
                time.sleep(0.1)
        raise RuntimeError(f"server not answering at {url}")

    def stop(self) -> None:
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        if self.process.stdout:
            self.process.stdout.close()
        self.tmp.cleanup()

    @property
    def origin(self) -> str:
        return self.url.rstrip("/")

    def get(self, path: str) -> tuple:
        try:
            with urllib.request.urlopen(self.url + path.lstrip("/"), timeout=5) as r:
                return r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            return e.code, ""

    def client(self, origin=None) -> "Client":
        return Client(self, origin or self.origin)


class Client:
    """One browser page: a WebSocket connection with helpers."""

    def __init__(self, server: Server, origin: str):
        ws_url = server.url.replace("http://", "ws://") + "ws"
        self.ws = connect(ws_url, origin=origin, open_timeout=TIMEOUT)
        self.received: list = []

    def close(self) -> None:
        self.ws.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def send(self, **command) -> None:
        self.ws.send(json.dumps(command))

    def until(self, message_type: str, timeout: float = TIMEOUT) -> list:
        """Receives until a message of message_type; returns everything received."""
        got = []
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                message = json.loads(self.ws.recv(timeout=max(0.05, deadline - time.time())))
            except TimeoutError:
                break
            got.append(message)
            self.received.append(message)
            if message.get("type") == message_type:
                return got
        raise AssertionError(f"no '{message_type}' message; got {[m.get('type') for m in got]}")

    def cmd(self, expected: str, **command) -> dict:
        self.send(**command)
        return self.until(expected)[-1]

    def stop_and_settle(self) -> None:
        """Stops any run and waits until the server reports not running."""
        self.send(cmd="stop")
        deadline = time.time() + TIMEOUT
        while time.time() < deadline:
            status = self.until("status")[-1]
            if not status["running"]:
                return
        raise AssertionError("server kept running after stop")


def final_states(messages: list) -> tuple:
    vertices, edges = {}, {}
    for m in messages:
        if m["type"] == "states":
            vertices.update(m["v"])
            edges.update(m["e"])
    return vertices, edges


@unittest.skipUnless(HAS_WEBSOCKETS, "websockets not installed")
class ConformanceBase(unittest.TestCase):
    server: Server

    @classmethod
    def setUpClass(cls):
        cls.server = Server()

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    def client(self, **kwargs) -> Client:
        c = self.server.client(**kwargs)
        self.addCleanup(c.close)
        c.until("status")  # the greeting ends with a status
        return c


class TestFreshServer(ConformanceBase):
    """Behaviour of a server that has nothing loaded yet."""

    def test_greeting_lists_files_then_status(self):
        c = self.server.client()
        self.addCleanup(c.close)
        greeting = c.until("status")
        self.assertEqual(greeting[0]["type"], "files")
        files = greeting[0]
        self.assertIn("dodecahedron.json", files["graphs"])
        self.assertIn("nemertea/nemertea.lua", files["scripts"])  # subfolders use "/"
        self.assertIn("tutorial/walk.lua", files["scripts"])
        self.assertEqual(files["graphs"], sorted(files["graphs"]))
        self.assertNotIn("graph", [m["type"] for m in greeting])
        status = greeting[-1]
        self.assertEqual((status["running"], status["paused"], status["speed"]), (False, False, 10))

    def test_play_without_graph_and_script_is_an_error(self):
        c = self.client()
        self.assertIn("graph", c.cmd("error", cmd="play")["message"])

    def test_unknown_command_is_an_error(self):
        c = self.client()
        self.assertEqual(c.cmd("error", cmd="fly")["type"], "error")


class TestHttp(ConformanceBase):
    def test_page_library_and_tutorial(self):
        status, page = self.server.get("/")
        self.assertEqual(status, 200)
        self.assertIn("Grafuria", page)
        self.assertEqual(self.server.get("/static/vendor/cytoscape.min.js")[0], 200)
        self.assertEqual(self.server.get("/static/app.js")[0], 200)
        self.assertEqual(self.server.get("/tutorial")[0], 200)
        for lang in ["pt", "en"]:
            status, md = self.server.get(f"/docs/tutorial.{lang}.md")
            self.assertEqual(status, 200)
            for image in re.findall(r"\]\((img/[^)]+)\)", md):
                self.assertEqual(self.server.get("/docs/" + image)[0], 200, image)

    def test_no_files_outside_static_and_docs(self):
        for path in ["/static/../../README.md", "/docs/../README.md", "/README.md", "/main.py"]:
            status, body = self.server.get(path)
            self.assertTrue(status == 404 or "Grafuria tutorial" not in body, path)
            self.assertNotIn("import sys", body, path)


class TestSecurity(ConformanceBase):
    def test_websocket_refuses_other_origins(self):
        try:
            c = self.server.client(origin="http://evil.example")
        except InvalidStatus:
            return  # refused in the handshake: fine
        with self.assertRaises(ConnectionClosed):
            c.ws.recv(timeout=TIMEOUT)
        c.close()

    def test_only_files_inside_graphs_and_scripts(self):
        c = self.client()
        outside = ["../README.md", "/etc/passwd", "../src/grafuria/cli.py"]
        # Each name escapes its own folder (from graphs/, ../scripts/ is outside).
        for name in outside + ["../scripts/bfs.lua"]:
            self.assertEqual(c.cmd("error", cmd="load_graph", name=name)["type"], "error", name)
        for name in outside + ["../graphs/cube.json"]:
            self.assertEqual(c.cmd("error", cmd="load_script", name=name)["type"], "error", name)

    def test_save_only_plain_names(self):
        c = self.client()
        c.cmd("graph", cmd="load_graph", name="cube.json")
        for name in ["../evil.json", "sub/evil.json", "/tmp/evil.json", ".hidden", ""]:
            self.assertEqual(c.cmd("error", cmd="save_graph", name=name)["type"], "error", name)
        self.assertFalse(os.path.exists(os.path.join(self.server.tmp.name, "evil.json")))


class TestRunning(ConformanceBase):
    def test_nemertea_solves_the_dodecahedron(self):
        c = self.client()
        graph = c.cmd("graph", cmd="load_graph", name="dodecahedron.json")
        self.assertEqual(len(graph["graph"]["vertex"]), 20)
        self.assertEqual(graph["name"], "dodecahedron.json")
        script = c.cmd("script", cmd="load_script", name="nemertea/nemertea.lua")
        self.assertEqual(script["params"], {"cycle": True, "deep": 7})  # without _min/_max
        c.send(cmd="play")
        messages = c.until("finished")
        self.assertTrue(messages[-1]["solved"])
        after = c.until("status")[-1]
        self.assertFalse(after["running"])
        vertices, edges = final_states(messages)
        self.assertEqual(len(vertices), 20)
        self.assertTrue(all(s == 1 for s in vertices.values()))
        self.assertEqual(sum(1 for s in edges.values() if s == 1), 20)  # a cycle

    def test_brute_force_on_petersen_is_not_solved(self):
        c = self.client()
        c.cmd("graph", cmd="load_graph", name="petersen.json")
        c.cmd("script", cmd="load_script", name="hamilton_brute.lua")
        c.send(cmd="play")
        self.assertFalse(c.until("finished")[-1]["solved"])
        c.until("status")

    def test_logs_carry_symbols_and_system_flag(self):
        c = self.client()
        c.cmd("graph", cmd="load_graph", name="cube.json")
        c.cmd("script", cmd="load_script", name="tutorial/walk.lua")
        c.send(cmd="play")
        messages = c.until("finished")
        lines = [line for m in messages if m["type"] == "log" for line in m["lines"]]
        self.assertTrue(any(l["text"].startswith("#Starting at vertex") and not l["system"] for l in lines))
        self.assertTrue(lines[-1]["text"].startswith("#Visited"))
        c.until("status")

    def test_script_error_is_a_system_log_with_file_and_line(self):
        c = self.client()
        c.cmd("graph", cmd="load_graph", name="cube.json")
        c.cmd("script", cmd="load_script", name="conformance/broken.lua")
        c.send(cmd="play")
        messages = c.until("finished")
        self.assertFalse(messages[-1]["solved"])
        lines = [line for m in messages if m["type"] == "log" for line in m["lines"]]
        errors = [l for l in lines if l["system"]]
        self.assertTrue(errors, "no system log for the error")
        self.assertIn("broken.lua:3:", errors[-1]["text"])
        c.until("status")

    def test_pause_resume_stop_and_speed(self):
        c = self.client()
        c.cmd("graph", cmd="load_graph", name="big_circle.json")
        c.cmd("script", cmd="load_script", name="nemertea/nemertea.lua")
        self.assertEqual(c.cmd("status", cmd="speed", value=0)["speed"], 1)  # clamped
        self.assertEqual(c.cmd("status", cmd="speed", value=99)["speed"], 10)
        self.assertEqual(c.cmd("status", cmd="speed", value=7)["speed"], 7)
        running = c.cmd("status", cmd="play")
        self.assertTrue(running["running"])
        paused = c.cmd("status", cmd="pause")
        self.assertTrue(paused["paused"])
        time.sleep(0.3)
        while True:  # drain what was produced before the pause took effect
            try:
                c.until("states", timeout=0.3)
            except AssertionError:
                break
        with self.assertRaises(AssertionError):
            c.until("states", timeout=0.6)  # nothing changes while paused
        resumed = c.cmd("status", cmd="play")
        self.assertFalse(resumed["paused"])
        c.stop_and_settle()
        c.cmd("status", cmd="speed", value=10)

    def test_clear_resets_states(self):
        c = self.client()
        c.cmd("graph", cmd="load_graph", name="cube.json")
        c.cmd("script", cmd="load_script", name="hamilton_brute.lua")
        c.send(cmd="play")
        c.until("finished")
        c.until("status")
        c.cmd("status", cmd="clear")
        # a new page sees the graph without states
        with self.server.client() as other:
            greeting = other.until("status")
        graph = next(m for m in greeting if m["type"] == "graph")
        self.assertEqual(len(graph["graph"]["vertex"]), 8)
        c.send(cmd="play")
        vertices, _ = final_states(c.until("finished"))
        self.assertTrue(vertices)  # it runs again from a clean graph
        c.until("status")

    def test_new_page_receives_current_graph_and_script(self):
        c = self.client()
        c.cmd("graph", cmd="load_graph", name="cube.json")
        c.cmd("script", cmd="load_script", name="tutorial/walk.lua")
        with self.server.client() as other:
            greeting = {m["type"]: m for m in other.until("status")}
        self.assertEqual(greeting["graph"]["name"], "cube.json")
        self.assertEqual(greeting["script"]["name"], "tutorial/walk.lua")
        self.assertEqual(greeting["script"]["params"], {"start": -1})


class TestEditing(ConformanceBase):
    def test_build_save_load_and_run_a_triangle(self):
        c = self.client()
        empty = c.cmd("graph", cmd="new_graph", directed=False)
        self.assertEqual(empty["graph"]["vertex"], [])
        self.assertTrue(empty["graph"]["bidirectional"])
        ids = [c.cmd("vertex_added", cmd="add_vertex", x=100 * i, y=50)["vertex"]["id"] for i in range(3)]
        self.assertEqual(len(set(ids)), 3)
        edge_ids = []
        for a, b in [(0, 1), (1, 2), (2, 0)]:
            edge = c.cmd("edge_added", cmd="add_edge", a=ids[a], b=ids[b])["edge"]
            self.assertEqual((edge["a"], edge["b"], edge["weight"]), (ids[a], ids[b], 1))
            edge_ids.append(edge["id"])
        self.assertEqual(c.cmd("error", cmd="add_edge", a=ids[1], b=ids[0])["type"], "error")  # duplicate
        self.assertEqual(c.cmd("error", cmd="add_edge", a=ids[0], b=ids[0])["type"], "error")  # loop
        moved = c.cmd("vertex_moved", cmd="move_vertex", id=ids[0], x=55, y=66)
        self.assertEqual((moved["x"], moved["y"]), (55, 66))
        self.assertEqual(c.cmd("vertex_renamed", cmd="rename_vertex", id=ids[0], name="alpha")["name"], "alpha")
        self.assertEqual(c.cmd("edge_weight", cmd="set_weight", id=edge_ids[0], weight="2.5")["weight"], 2.5)
        self.assertEqual(c.cmd("error", cmd="set_weight", id=edge_ids[0], weight="abc")["type"], "error")
        greeting = c.cmd("saved", cmd="save_graph", name="triangle_test")
        self.assertEqual(greeting["name"], "triangle_test.json")
        with open(os.path.join(self.server.graphs, "triangle_test.json")) as f:
            data = json.load(f)
        self.assertEqual((len(data["vertex"]), len(data["edge"])), (3, 3))
        alpha = next(v for v in data["vertex"] if v["name"] == "alpha")
        self.assertEqual((alpha["x"], alpha["y"]), (55, 66))
        self.assertIn(2.5, [e["weight"] for e in data["edge"]])
        loaded = c.cmd("graph", cmd="load_graph", name="triangle_test.json")
        self.assertEqual(len(loaded["graph"]["edge"]), 3)
        c.cmd("script", cmd="load_script", name="hamilton_brute.lua")
        c.send(cmd="play")
        self.assertTrue(c.until("finished")[-1]["solved"])
        c.until("status")

    def test_saved_file_appears_in_the_list(self):
        c = self.client()
        c.cmd("graph", cmd="load_graph", name="cube.json")
        c.send(cmd="save_graph", name="cube_copy")
        messages = c.until("saved")
        files = next(m for m in messages if m["type"] == "files")
        self.assertIn("cube_copy.json", files["graphs"])

    def test_delete_vertex_removes_its_edges(self):
        c = self.client()
        graph = c.cmd("graph", cmd="load_graph", name="cube.json")["graph"]
        vertex = graph["vertex"][0]["id"]
        touching = {e["id"] for e in graph["edge"] if vertex in (e["a"], e["b"])}
        removed = c.cmd("vertex_removed", cmd="delete_vertex", id=vertex)
        self.assertEqual(set(removed["edges"]), touching)
        other = next(e["id"] for e in graph["edge"] if e["id"] not in touching)
        self.assertEqual(c.cmd("edge_removed", cmd="delete_edge", id=other)["id"], other)
        self.assertEqual(c.cmd("error", cmd="delete_vertex", id=vertex)["type"], "error")  # already gone

    def test_directed_toggle(self):
        c = self.client()
        c.cmd("graph", cmd="load_graph", name="cube.json")
        self.assertFalse(c.cmd("graph", cmd="set_directed", directed=True)["graph"]["bidirectional"])
        self.assertTrue(c.cmd("graph", cmd="set_directed", directed=False)["graph"]["bidirectional"])

    def test_edits_reach_every_page(self):
        c = self.client()
        c.cmd("graph", cmd="load_graph", name="cube.json")
        with self.server.client() as other:
            other.until("status")
            c.send(cmd="add_vertex", x=1, y=2)
            added = other.until("vertex_added")[-1]
        self.assertEqual((added["vertex"]["x"], added["vertex"]["y"]), (1, 2))

    def test_no_editing_while_running(self):
        c = self.client()
        c.cmd("graph", cmd="load_graph", name="big_circle.json")
        c.cmd("script", cmd="load_script", name="nemertea/nemertea.lua")
        c.cmd("status", cmd="speed", value=6)
        c.cmd("status", cmd="play")
        self.assertIn("Stop the script", c.cmd("error", cmd="add_vertex", x=1, y=1)["message"])
        c.stop_and_settle()
        c.cmd("status", cmd="speed", value=10)


if __name__ == "__main__":
    unittest.main()
