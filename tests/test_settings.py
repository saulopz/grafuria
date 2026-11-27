"""Tests for settings.json and the execution history (no interface)."""

import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from grafuria.core import history  # noqa: E402
from grafuria.core.settings import Settings  # noqa: E402


class TestSettings(unittest.TestCase):
    def test_defaults_when_missing_or_broken(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "settings.json")
            self.assertEqual(Settings.load(path), Settings())
            with open(path, "w") as f:
                f.write("{ not json")
            self.assertEqual(Settings.load(path), Settings())

    def test_round_trip_and_partial_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "settings.json")
            Settings(animation=False, speed=3, logs_symbols="#$").save(path)
            loaded = Settings.load(path)
            self.assertEqual((loaded.animation, loaded.speed, loaded.logs_symbols), (False, 3, "#$"))
            with open(path, "w") as f:
                f.write('{"speed": 5, "unknown_key": 1}')
            loaded = Settings.load(path)
            self.assertEqual(loaded.speed, 5)
            self.assertTrue(loaded.animation)  # default kept


class TestHistory(unittest.TestCase):
    def test_append(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "h.csv")
            history.append_execution(path, "/x/graphs/cube.json", "/x/scripts/a.lua", 0.5, True)
            history.append_execution(path, "cube.json", "a.lua", None, False)
            with open(path) as f:
                lines = [line.rstrip("\n").split("\t") for line in f]
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0][2:], ["cube.json", "a.lua", "0.5000", "True"])
        self.assertEqual(lines[1][-1], "False")


if __name__ == "__main__":
    unittest.main()
