"""Tests for the graph model (no interface, no script engine)."""

import glob
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from grafuria.core.graph import Graph  # noqa: E402
from grafuria.core.state import State  # noqa: E402


def triangle() -> Graph:
    g = Graph()
    a, b, c = g.add_vertex("a"), g.add_vertex("b"), g.add_vertex("c")
    g.add_edge(a, b)
    g.add_edge(b, c)
    g.add_edge(c, a)
    return g


class TestGraphModel(unittest.TestCase):
    def test_add_and_adjacency(self):
        g = triangle()
        a, b, c = g.vertex
        self.assertEqual(g.get_vertex_size(), 3)
        self.assertEqual(len(g.edge), 3)
        self.assertTrue(a.is_connected(b) and b.is_connected(a))
        ab = a.get_edge_to(b)
        self.assertIs(ab, b.get_edge_to(a))
        self.assertIs(a.get_adjacent(ab), b)
        self.assertIs(ab.get_adjacent(b), a)
        self.assertIsNone(ab.get_adjacent(c))

    def test_ids_are_per_graph(self):
        # The old code used global class counters shared by all graphs.
        g1, g2 = triangle(), triangle()
        self.assertEqual([v.id for v in g1.vertex], [0, 1, 2])
        self.assertEqual([v.id for v in g2.vertex], [0, 1, 2])
        g3 = Graph()
        g3.add_vertex(vertex_id=10)
        self.assertEqual(g3.add_vertex().id, 11)

    def test_rejects_duplicates_and_loops(self):
        g = triangle()
        a, b, _ = g.vertex
        with self.assertRaises(ValueError):
            g.add_edge(a, b)
        with self.assertRaises(ValueError):
            g.add_edge(a, a)
        with self.assertRaises(ValueError):
            g.add_vertex(vertex_id=0)

    def test_active_edge_counter(self):
        g = triangle()
        a, b, c = g.vertex
        ab, bc = a.get_edge_to(b), b.get_edge_to(c)
        ab.set_state(State.ACTIVE)
        ab.set_state(State.ACTIVE)  # setting twice must not count twice
        bc.set_state(State.ACTIVE)
        self.assertEqual((a.get_active_edge_size(), b.get_active_edge_size()), (1, 2))
        ab.set_state(State.TESTING)
        self.assertEqual((a.get_active_edge_size(), b.get_active_edge_size()), (0, 1))
        g.remove_edge(bc)
        self.assertEqual(c.get_active_edge_size(), 0)

    def test_remove_vertex_removes_its_edges(self):
        g = triangle()
        a, b, c = g.vertex
        g.remove_vertex(a)
        self.assertEqual(len(g.edge), 1)
        self.assertFalse(b.is_connected(a))
        self.assertIsNone(g.get_vertex_by_id(a.id))

    def test_reset_states(self):
        g = triangle()
        for e in g.edge:
            e.set_state(State.ACTIVE)
        g.vertex[0].set_var("visited", True)
        g.reset_states()
        self.assertTrue(all(e.state == State.NONE for e in g.edge))
        self.assertTrue(all(v.get_active_edge_size() == 0 for v in g.vertex))
        self.assertIsNone(g.vertex[0].get_var("visited"))

    def test_listener(self):
        g = triangle()
        seen = []
        g.listener = seen.append
        g.vertex[0].set_state(State.TESTING)
        g.edge[0].set_state(State.ACTIVE)
        self.assertEqual(seen, [g.vertex[0], g.edge[0]])

    def test_to_dict_reindexes(self):
        g = Graph()
        a = g.add_vertex("a", vertex_id=5)
        b = g.add_vertex("b", vertex_id=9)
        g.add_edge(a, b, 2.5, edge_id=7)
        d = g.to_dict()
        self.assertEqual([v["id"] for v in d["vertex"]], [0, 1])
        self.assertEqual(d["edge"], [{"id": 0, "a": 0, "b": 1, "weight": 2.5}])


class TestGraphFiles(unittest.TestCase):
    def test_all_bundled_graphs_load_and_round_trip(self):
        files = sorted(glob.glob(os.path.join(ROOT, "graphs", "*.json")))
        self.assertGreater(len(files), 0)
        for path in files:
            with self.subTest(graph=os.path.basename(path)):
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                g = Graph.load(path)
                self.assertEqual(len(g.vertex), len(data["vertex"]))
                self.assertEqual(len(g.edge), len(data["edge"]))
                with tempfile.TemporaryDirectory() as tmp:
                    out = os.path.join(tmp, "g.json")
                    g.save(out)
                    g2 = Graph.load(out)
                self.assertEqual(g2.to_dict(), g.to_dict())


class TestCoreHasNoInterface(unittest.TestCase):
    def test_core_modules_do_not_import_tkinter(self):
        code = (
            "import sys; sys.path.insert(0, %r);"
            "import grafuria.core.graph, grafuria.core.scripting, grafuria.core.headless,"
            " grafuria.core.state, grafuria.core.settings, grafuria.core.history;"
            "assert 'tkinter' not in sys.modules, 'tkinter imported'" % os.path.join(ROOT, "src")
        )
        result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
