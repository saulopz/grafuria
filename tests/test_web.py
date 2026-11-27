"""Tests of the web interface server (no browser needed)."""

import json
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

try:
    from fastapi.testclient import TestClient
    from starlette.websockets import WebSocketDisconnect

    from grafuria.webui.server import WebSession, create_app
    HAS_WEB = True
except ImportError:  # fastapi/httpx not installed
    HAS_WEB = False


def receive_until(ws, message_type: str, limit: int = 2000) -> list:
    """Receives messages until one of message_type arrives; returns all of them."""
    received = []
    for _ in range(limit):
        message = ws.receive_json()
        received.append(message)
        if message["type"] == message_type:
            return received
    raise AssertionError(f"no '{message_type}' message")


@unittest.skipUnless(HAS_WEB, "fastapi/httpx not installed")
class TestWebServer(unittest.TestCase):
    def setUp(self):
        os.chdir(ROOT)  # Lua scripts use dofile("scripts/...")
        self.session = WebSession(os.path.join(ROOT, "graphs"), os.path.join(ROOT, "scripts"))
        self.client = TestClient(create_app(self.session))
        self.client.__enter__()  # runs the lifespan (update flusher)

    def tearDown(self):
        self.session.stop()
        self.session.join(5)
        self.client.__exit__(None, None, None)

    def test_page_and_library_are_served(self):
        self.assertIn("Grafuria", self.client.get("/").text)
        self.assertEqual(self.client.get("/static/vendor/cytoscape.min.js").status_code, 200)

    def test_run_nemertea_and_receive_states(self):
        with self.client.websocket_connect("/ws") as ws:
            files = ws.receive_json()
            self.assertIn("dodecahedron.json", files["graphs"])
            self.assertIn("nemertea/nemertea.lua", files["scripts"])
            ws.send_json({"cmd": "load_graph", "name": "dodecahedron.json"})
            graph = receive_until(ws, "graph")[-1]
            self.assertEqual(len(graph["graph"]["vertex"]), 20)
            ws.send_json({"cmd": "load_script", "name": "nemertea/nemertea.lua"})
            script = receive_until(ws, "script")[-1]
            self.assertEqual(script["params"]["deep"], 7)
            ws.send_json({"cmd": "play"})
            messages = receive_until(ws, "finished")
            # Regression: the status after the end still said "running".
            after = receive_until(ws, "status")[-1]
            self.assertFalse(after["running"])
        self.assertTrue(messages[-1]["solved"])
        # The browser saw the final state: every vertex active.
        vertex_states = {}
        for m in messages:
            if m["type"] == "states":
                vertex_states.update(m["v"])
        self.assertEqual(len(vertex_states), 20)
        self.assertTrue(all(state == 1 for state in vertex_states.values()))
        self.assertTrue(any(m["type"] == "log" for m in messages))

    def test_files_outside_the_folders_are_refused(self):
        with self.client.websocket_connect("/ws") as ws:
            ws.receive_json()
            for name in ["../README.md", "/etc/passwd", "../src/grafuria/cli.py"]:
                ws.send_json({"cmd": "load_graph", "name": name})
                self.assertEqual(receive_until(ws, "error")[-1]["type"], "error")
                ws.send_json({"cmd": "load_script", "name": name})
                self.assertEqual(receive_until(ws, "error")[-1]["type"], "error")

    def test_play_without_graph_is_an_error(self):
        with self.client.websocket_connect("/ws") as ws:
            ws.receive_json()
            ws.send_json({"cmd": "play"})
            self.assertIn("graph", receive_until(ws, "error")[-1]["message"])


@unittest.skipUnless(HAS_WEB, "fastapi/httpx not installed")
class TestWebEditing(unittest.TestCase):
    """Editing commands; saving goes to a temporary copy of graphs/."""

    def setUp(self):
        os.chdir(ROOT)
        self.tmp = tempfile.TemporaryDirectory()
        self.graphs = os.path.join(self.tmp.name, "graphs")
        shutil.copytree(os.path.join(ROOT, "graphs"), self.graphs)
        self.session = WebSession(self.graphs, os.path.join(ROOT, "scripts"))
        self.client = TestClient(create_app(self.session))
        self.client.__enter__()
        self.ws_context = self.client.websocket_connect("/ws")
        self.ws = self.ws_context.__enter__()
        receive_until(self.ws, "status")

    def tearDown(self):
        self.ws_context.__exit__(None, None, None)
        self.session.stop()
        self.session.join(5)
        self.client.__exit__(None, None, None)
        self.tmp.cleanup()

    def cmd(self, expected: str, **command) -> dict:
        self.ws.send_json(command)
        return receive_until(self.ws, expected)[-1]

    def test_build_edit_and_save_a_triangle(self):
        self.cmd("graph", cmd="new_graph", directed=False)
        ids = [self.cmd("vertex_added", cmd="add_vertex", x=10 * i, y=0)["vertex"]["id"]
               for i in range(3)]
        for a, b in [(0, 1), (1, 2), (2, 0)]:
            self.cmd("edge_added", cmd="add_edge", a=ids[a], b=ids[b])
        self.assertIn("already connected", self.cmd("error", cmd="add_edge", a=ids[1], b=ids[0])["message"])
        self.assertIn("Loops", self.cmd("error", cmd="add_edge", a=ids[0], b=ids[0])["message"])
        self.cmd("vertex_moved", cmd="move_vertex", id=ids[0], x=55, y=66)
        self.cmd("vertex_renamed", cmd="rename_vertex", id=ids[0], name="alpha")
        edge = self.session.graph.edge[0].id
        self.assertEqual(self.cmd("edge_weight", cmd="set_weight", id=edge, weight="2.5")["weight"], 2.5)
        self.assertEqual(self.cmd("error", cmd="set_weight", id=edge, weight="abc")["type"], "error")
        saved = self.cmd("saved", cmd="save_graph", name="triangle_test")
        self.assertEqual(saved["name"], "triangle_test.json")
        with open(os.path.join(self.graphs, "triangle_test.json")) as f:
            data = json.load(f)
        self.assertEqual((len(data["vertex"]), len(data["edge"])), (3, 3))
        self.assertEqual(data["vertex"][0]["name"], "alpha")
        self.assertEqual((data["vertex"][0]["x"], data["vertex"][0]["y"]), (55, 66))
        # and the saved file runs: a triangle has a Hamiltonian cycle
        self.cmd("graph", cmd="load_graph", name="triangle_test.json")
        self.cmd("script", cmd="load_script", name="hamilton_brute.lua")
        self.ws.send_json({"cmd": "play"})
        self.assertTrue(receive_until(self.ws, "finished")[-1]["solved"])

    def test_delete_vertex_removes_its_edges(self):
        self.cmd("graph", cmd="load_graph", name="cube.json")
        vertex = self.session.graph.vertex[0]
        degree = len(vertex.edge)
        removed = self.cmd("vertex_removed", cmd="delete_vertex", id=vertex.id)
        self.assertEqual(len(removed["edges"]), degree)
        self.assertEqual((len(self.session.graph.vertex), len(self.session.graph.edge)), (7, 12 - degree))
        edge = self.session.graph.edge[0].id
        self.cmd("edge_removed", cmd="delete_edge", id=edge)
        self.assertIsNone(self.session.graph.get_edge_by_id(edge))

    def test_directed_toggle(self):
        self.cmd("graph", cmd="load_graph", name="cube.json")
        self.assertFalse(self.cmd("graph", cmd="set_directed", directed=True)["graph"]["bidirectional"])

    def test_save_only_plain_names_inside_graphs(self):
        self.cmd("graph", cmd="load_graph", name="cube.json")
        for name in ["../evil.json", "sub/evil.json", "/tmp/evil.json", ".hidden", ""]:
            self.assertEqual(self.cmd("error", cmd="save_graph", name=name)["type"], "error")
        self.assertFalse(os.path.exists(os.path.join(self.tmp.name, "evil.json")))

    def test_no_editing_while_running(self):
        self.cmd("graph", cmd="load_graph", name="big_circle.json")
        self.cmd("script", cmd="load_script", name="nemertea/nemertea.lua")
        self.cmd("status", cmd="speed", value=8)  # slow enough to edit during the run
        self.ws.send_json({"cmd": "play"})
        receive_until(self.ws, "status")
        error = self.cmd("error", cmd="add_vertex", x=1, y=1)
        self.assertIn("Stop the script", error["message"])
        self.ws.send_json({"cmd": "stop"})


@unittest.skipUnless(HAS_WEB, "fastapi/httpx not installed")
class TestWebSocketOrigin(unittest.TestCase):
    def test_other_websites_cannot_connect(self):
        app = create_app(WebSession(), allowed_origins={"http://127.0.0.1:8765"})
        with TestClient(app) as client:
            with self.assertRaises(WebSocketDisconnect):
                with client.websocket_connect("/ws", headers={"origin": "http://evil.example"}) as ws:
                    ws.receive_json()
            with client.websocket_connect("/ws", headers={"origin": "http://127.0.0.1:8765"}) as ws:
                self.assertEqual(ws.receive_json()["type"], "files")


if __name__ == "__main__":
    unittest.main()
