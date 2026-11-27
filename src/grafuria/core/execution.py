"""
Script execution control shared by every interface: play, pause, stop
and speed, with the script running in its own thread.

ScriptHost implements the host API that scripts use (see scripting.py).
Interfaces subclass it and say how to show logs and areas, how fast to
go, and what to do when the script ends. Methods called from the
script thread must never touch interface objects directly.
"""

import gc
import threading
import time
from typing import Optional

from . import scripting


class ScriptHost:
    SPEED_MAX = 10

    def __init__(self):
        self.stopped = True
        self.paused = False
        self.solved = False
        self.execution_time: Optional[float] = None
        self._variables: dict = {}
        self._area: list = []
        self._thread: Optional[threading.Thread] = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    # -------------------------
    # Controls (interface thread)
    # -------------------------
    def start(self, script: str, graph, graph_file: str, variables: dict) -> None:
        """
        Starts the script in a new thread. The parameters are a plain
        copy taken now, so the script never reads interface objects.
        """
        self.solved = False
        self.execution_time = None
        self.paused = False
        self.stopped = False
        self._variables = dict(variables)
        self._area = []
        # Collect garbage now, in the interface thread. Otherwise the
        # collector may run in the script thread and finalize discarded
        # interface objects there (Tk variables, for example).
        gc.collect()
        self._thread = threading.Thread(
            target=self._run, args=(script, graph, graph_file), daemon=True
        )
        self._thread.start()

    def pause(self) -> None:
        self.paused = True

    def resume(self) -> None:
        self.paused = False

    def stop(self) -> None:
        self.paused = False
        self.stopped = True

    def join(self, timeout: Optional[float] = None) -> None:
        if self._thread is not None:
            self._thread.join(timeout)

    # -------------------------
    # Script thread
    # -------------------------
    def _run(self, script: str, graph, graph_file: str) -> None:
        error = None
        try:
            scripting.run_script(script, graph, host=self)
        except Exception as e:
            error = e
            self.show_log(f"[Script error] {e}", system=True)
        self.on_finished(script, graph_file, error)

    # -------------------------
    # Hooks for interfaces (called from the script thread)
    # -------------------------
    def get_speed(self) -> int:
        """1 (slowest) .. SPEED_MAX (no pauses)."""
        return self.SPEED_MAX

    def show_log(self, text: str, system: bool = False) -> None:
        pass

    def show_area(self, points: list) -> None:
        pass

    def on_finished(self, script: str, graph_file: str, error: Optional[Exception]) -> None:
        pass

    # -------------------------
    # Host API (called by scripts)
    # -------------------------
    def log(self, text) -> None:
        if text:
            self.show_log(str(text))

    def step(self) -> None:
        """Called by scripts inside their loops: honours pause and speed."""
        while self.paused and not self.stopped:
            time.sleep(0.1)
        speed = self.get_speed()
        if speed < self.SPEED_MAX:
            time.sleep((self.SPEED_MAX - speed) ** 2 / 100)

    def is_stopped(self) -> bool:
        return self.stopped

    def set_solved(self, solved) -> None:
        self.solved = bool(solved)

    def set_execution_time(self, seconds) -> None:
        self.execution_time = seconds

    def get_var(self, name):
        return self._variables.get(name)

    def area_add(self, x, y) -> None:
        self._area.append((x, y))

    def area_close(self) -> None:
        points, self._area = self._area, []
        self.show_area(points)
