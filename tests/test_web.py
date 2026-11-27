"""Tests of the web interface server (no browser needed)."""

import os
import sys
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
