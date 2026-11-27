"""
Smoke tests of the Tkinter interface. They need a display; on a
machine without one, run them with: xvfb-run -a python3 -m unittest
"""

import gc
import json
import os
import sys
import tempfile
import threading
import time
import types
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

try:
    import tkinter as tk
    _root = tk.Tk()
    _root.destroy()
    HAS_DISPLAY = True
except Exception:
    HAS_DISPLAY = False

try:
    import lupa  # noqa: F401
    HAS_LUA = True
except ImportError:
    HAS_LUA = False


class TkCallCounter:
    """Wraps the Tcl interpreter and counts calls made outside the main thread."""

    def __init__(self, tkapp):
        object.__setattr__(self, "_tk", tkapp)
        object.__setattr__(self, "off_thread", 0)

    def __getattr__(self, name):
        attr = getattr(self._tk, name)
        if not callable(attr):
            return attr

        def wrapper(*args, **kwargs):
            if threading.current_thread() is not threading.main_thread():
                object.__setattr__(self, "off_thread", self.off_thread + 1)
            return attr(*args, **kwargs)

        return wrapper


@unittest.skipUnless(HAS_DISPLAY, "no display available")
class TestInterface(unittest.TestCase):
    def setUp(self):
        os.chdir(ROOT)
        self.root = tk.Tk()
        self.counter = TkCallCounter(self.root.tk)
        self.root.tk = self.counter
        from grafuria.tkui import theme
        from grafuria.tkui.app import App

        self.theme = theme
        # Never touch the user's settings.json or execution history.
        self.tmp = tempfile.TemporaryDirectory()
        self.settings_file = os.path.join(self.tmp.name, "settings.json")
        self.app = App(master=self.root, settings_file=self.settings_file)
        self.app.runner.HISTORY_FILE = os.path.join(self.tmp.name, "history.csv")
        self.app.settings.animation = True

    def tearDown(self):
        self.root.destroy()
        self.tmp.cleanup()
        gc.collect()  # finalize this test's Tk objects in the main thread

    def click(self, x=0, y=0):
        return types.SimpleNamespace(x=x, y=y)

    def test_edit_graph(self):
        app = self.app
        a = app.create_vertex("a", 100, 100)
        b = app.create_vertex("b", 200, 100)
        c = app.create_vertex("c", 150, 200)
        for first, second in [(a, b), (b, c), (c, a)]:
            first.mouse_down(self.click(first.model.x, first.model.y))
            second.connect(self.click())
        self.assertEqual(len(app.graph.edge), 3)
        b.connect(self.click())  # connecting twice does nothing
        self.assertEqual(len(app.graph.edge), 3)

        # drag a vertex: model and edges follow
        a.mouse_down(self.click(100, 100))
        a.mouse_move(self.click(130, 110))
        self.assertEqual((a.model.x, a.model.y), (130, 110))
        ab = a.model.get_edge_to(b.model).view
        line = app.canvas.coords(ab.canvas_id)
        self.assertAlmostEqual(line[0], 130, delta=1)

        # rename, weight
        a.set_name("alpha")
        ab.set_weight(3.0, "3")
        data = json.loads(app.get_graph())
        self.assertEqual(data["vertex"][0]["name"], "alpha")
        self.assertIn(3.0, [e["weight"] for e in data["edge"]])

        # delete a vertex removes its edges from model and canvas
        app.select_vertex(a)
        app.delete_selected()
        self.assertEqual(len(app.graph.vertex), 2)
        self.assertEqual(len(app.graph.edge), 1)
        self.assertEqual(len(app.canvas.find_withtag("edge")), 1)

    def test_load_save_and_toggle_direction(self):
        app = self.app
        app.load_graph_file(os.path.join(ROOT, "graphs", "cube.json"))
        self.assertEqual(len(app.canvas.find_withtag("vertex")), 8)
        self.assertEqual(len(app.canvas.find_withtag("edge")), 12)
        app.sidebar.var_bidirectional.set(False)
        app.on_bidirectional_change()
        self.assertFalse(app.graph.bidirectional)
        self.assertEqual(len(app.canvas.find_withtag("edge")), 12)
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "cube.json")
            with open(out, "w") as f:
                f.write(app.get_graph())
            app.reset_canvas()
            self.assertEqual(len(app.graph.vertex), 0)
            app.load_graph_file(out)
        self.assertEqual(len(app.graph.edge), 12)
        self.assertFalse(app.graph.bidirectional)

    def run_script(self, graph, script, timeout=30):
        app = self.app
        app.load_graph_file(os.path.join(ROOT, "graphs", graph))
        app.script = os.path.join(ROOT, script)
        app.settings.speed = 10
        app.event_play()
        start = time.time()
        while threading.active_count() > 1 and time.time() - start < timeout:
            self.root.update()
            time.sleep(0.01)
        for _ in range(5):  # let the pump finish
            self.root.update()
            time.sleep(App_PUMP)
        return app

    @unittest.skipUnless(HAS_LUA, "lupa not installed")
    def test_run_lua_script_thread_safe(self):
        app = self.run_script("dodecahedron.json", "scripts/nemertea/nemertea.lua")
        self.assertTrue(app.runner.solved)
        self.assertEqual(app.canvas.cget("bg"), self.theme.BG_SOLVED)
        self.assertEqual(self.counter.off_thread, 0)
        # the canvas shows the final state of the model
        v = app.graph.vertex[0]
        self.assertEqual(app.canvas.itemcget(v.view.canvas_id, "fill"), self.theme.SELECTED)

    def test_run_python_script_thread_safe(self):
        app = self.run_script("dodecahedron.json", "scripts/nemertea/nemertea.py")
        self.assertTrue(app.runner.solved)
        self.assertEqual(self.counter.off_thread, 0)

    def test_refresh_clears_states(self):
        app = self.run_script("cube.json", "scripts/nemertea/nemertea.py")
        app.event_clear()
        self.assertTrue(all(v.get_active_edge_size() == 0 for v in app.graph.vertex))
        self.assertEqual(app.canvas.cget("bg"), self.theme.BG)

    def test_settings_are_saved_and_history_written(self):
        app = self.app
        app.sidebar.var_animation.set(False)
        app.sidebar._on_animation()
        app.sidebar._on_speed("4")
        with open(self.settings_file) as f:
            saved = json.load(f)
        self.assertEqual((saved["animation"], saved["speed"]), (False, 4))
        app.settings.execution_time_log = True
        app.settings.speed = 10
        self.run_script("cube.json", "scripts/nemertea/nemertea.py")
        with open(app.runner.HISTORY_FILE) as f:
            line = f.read().strip().split("\t")
        self.assertEqual(line[2:4], ["cube.json", "nemertea.py"])
        self.assertEqual(line[-1], "True")

    def test_pause_resume_and_stop(self):
        app = self.app
        app.load_graph_file(os.path.join(ROOT, "graphs", "big_circle.json"))
        app.script = os.path.join(ROOT, "scripts", "nemertea", "nemertea.lua")
        app.settings.speed = 9  # small sleep at each step
        app.event_play()
        self.assertTrue(app.runner.running)
        app.event_play()  # play while running must not start a second thread
        self.assertEqual(threading.active_count(), 2)
        app.event_pause()
        time.sleep(0.3)
        self.root.update()
        changed = sum(1 for v in app.graph.vertex if v.state)
        time.sleep(0.3)
        self.assertEqual(changed, sum(1 for v in app.graph.vertex if v.state))  # paused
        app.event_play()  # resumes
        self.assertFalse(app.runner.paused)
        app.event_stop()
        start = time.time()
        while app.runner.running and time.time() - start < 10:
            self.root.update()
            time.sleep(0.01)
        self.assertFalse(app.runner.running)


App_PUMP = 0.02

if __name__ == "__main__":
    unittest.main()
