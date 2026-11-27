"""
Script execution in the interface: play, pause, stop and speed.

ScriptRunner is the *host* of scripts in the graphical interface (see
core/scripting.py). Its host methods are called from the script
thread and never touch widgets directly: everything visual goes
through the App bridge.
"""

import gc
import threading
import time

from ..core import history, scripting


class ScriptRunner:
    SPEED_MAX = 10
    HISTORY_FILE = "execution_history.csv"

    def __init__(self, app):
        self.app = app
        self.stopped = True
        self.paused = False
        self.solved = False
        self.execution_time = 0.0
        self._variables: dict = {}
        self._area: list = []
        self._thread = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    # -------------------------
    # Controls (UI thread)
    # -------------------------
    def start(self, script: str, graph, graph_file: str, variables: dict) -> None:
        """
        Starts the script in a new thread. The parameters are a plain
        copy taken now, so the script never reads Tk variables.
        """
        self.solved = False
        self.execution_time = 0.0
        self.paused = False
        self.stopped = False
        self._variables = dict(variables)
        self._area = []
        # Collect garbage now, in the UI thread. Otherwise the collector
        # may run inside the script thread and finalize discarded Tk
        # variables there, which calls Tcl from the wrong thread.
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

    # -------------------------
    # Script thread
    # -------------------------
    def _run(self, script: str, graph, graph_file: str) -> None:
        try:
            scripting.run_script(script, graph, host=self)
            if self.app.settings.execution_time_log:
                try:
                    history.append_execution(
                        self.HISTORY_FILE, graph_file, script,
                        self.execution_time, self.solved,
                    )
                except OSError as e:
                    self.app.bridge.run_in_ui(
                        self.app.status.set, f"Error saving execution history: {e}"
                    )
        except Exception as e:
            self.app.log(f"[Script error] {e}", system_log=True)
        self.app.bridge.run_in_ui(self.app.on_script_finished)

    # -------------------------
    # Host API (called by scripts, script thread)
    # -------------------------
    def log(self, text) -> None:
        self.app.log(text)

    def step(self) -> None:
        """
        Called by scripts inside their loops: honours pause and the speed
        chosen in the interface (10 = no sleep).
        """
        while self.paused and not self.stopped:
            time.sleep(0.1)
        speed = self.app.settings.speed
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
        area, self._area = self._area, []
        self.app.bridge.run_in_ui(self.app.draw_area, area)
