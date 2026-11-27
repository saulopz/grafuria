"""
Tests that run the bundled scripts headless.

Expected answers come from graph theory: the Petersen and Herschel
graphs have no Hamiltonian cycle; the cube, dodecahedron, hypercube
and icosahedron have one.
"""

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from headless import load_script_parameters, run_once  # noqa: E402
from state import State  # noqa: E402

try:
    import lupa  # noqa: F401
    HAS_LUA = True
except ImportError:
    HAS_LUA = False

HAMILTONIAN = ["cube", "dodecahedron", "hypercube", "icosaedron"]
NOT_HAMILTONIAN = ["petersen", "herschel"]


def run(graph: str, script: str, seed: int = 1, **overrides) -> dict:
    os.chdir(ROOT)  # Lua scripts use dofile("scripts/...")
    script_path = os.path.join(ROOT, script)
    variables = load_script_parameters(script_path)
    variables.update(overrides)
    return run_once(os.path.join(ROOT, "graphs", graph + ".json"), script_path, variables, seed)


def active_cycle_is_hamiltonian(graph) -> bool:
    """Checks the result drawn by a script: every vertex has exactly two
    active edges and the active edges form one single cycle."""
    active = [e for e in graph.edge if e.state == State.ACTIVE]
    if len(active) != len(graph.vertex):
        return False
    if any(v.get_active_edge_size() != 2 for v in graph.vertex):
        return False
    start = graph.vertex[0]
    previous, current, visited = None, start, 1
    while True:
        nxt = next(
            e.get_adjacent(current) for e in current.edge
            if e.state == State.ACTIVE and e.get_adjacent(current) is not previous
        )
        if nxt is start:
            return visited == len(graph.vertex)
        previous, current, visited = current, nxt, visited + 1


class TestPythonScripts(unittest.TestCase):
    def test_nemertea_py_solves_hamiltonian_graphs(self):
        # Regression: with swapped State values this failed on the dodecahedron.
        for g in HAMILTONIAN:
            with self.subTest(graph=g):
                r = run(g, "scripts/nemertea/nemertea.py")
                self.assertEqual(r["error"], "")
                self.assertTrue(r["solved"])
                self.assertTrue(active_cycle_is_hamiltonian(r["graph"]))

    def test_nemertea_py_never_claims_non_hamiltonian(self):
        for g in NOT_HAMILTONIAN:
            with self.subTest(graph=g):
                self.assertFalse(run(g, "scripts/nemertea/nemertea.py")["solved"])

    def test_other_python_scripts_run_without_error(self):
        for script in ["bfs.py", "dfs.py", "path.py", "info_vertex.py"]:
            with self.subTest(script=script):
                self.assertEqual(run("cube", "scripts/" + script)["error"], "")


@unittest.skipUnless(HAS_LUA, "lupa not installed")
class TestLuaScripts(unittest.TestCase):
    def test_hamilton_brute_force_is_correct(self):
        # Regression: it used to report cycles in Petersen and Herschel.
        for g in HAMILTONIAN[:2]:
            with self.subTest(graph=g):
                r = run(g, "scripts/hamilton_brute.lua")
                self.assertTrue(r["solved"])
                self.assertTrue(active_cycle_is_hamiltonian(r["graph"]))
        for g in NOT_HAMILTONIAN:
            with self.subTest(graph=g):
                self.assertFalse(run(g, "scripts/hamilton_brute.lua")["solved"])

    def test_nemertea_lua_solves_hamiltonian_graphs(self):
        for g in HAMILTONIAN:
            with self.subTest(graph=g):
                r = run(g, "scripts/nemertea/nemertea.lua")
                self.assertEqual(r["error"], "")
                self.assertTrue(r["solved"])
                self.assertTrue(active_cycle_is_hamiltonian(r["graph"]))

    def test_same_seed_same_result(self):
        def cycle(seed):
            r = run("big_circle", "scripts/nemertea/nemertea.lua", seed=seed)
            return [e.id for e in r["graph"].edge if e.state == State.ACTIVE]
        self.assertEqual(cycle(7), cycle(7))

    def test_other_lua_scripts_run_without_error(self):
        for script in ["bfs.lua", "dfs.lua", "path.lua"]:
            with self.subTest(script=script):
                self.assertEqual(run("cube", "scripts/" + script)["error"], "")


if __name__ == "__main__":
    unittest.main()
