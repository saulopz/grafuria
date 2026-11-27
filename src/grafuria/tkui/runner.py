"""Script execution in the Tkinter interface (see core/execution.py)."""

from ..core import history
from ..core.execution import ScriptHost


class ScriptRunner(ScriptHost):
    """Script host of the Tkinter interface. Visual work goes through the bridge."""

    HISTORY_FILE = "execution_history.csv"

    def __init__(self, app):
        super().__init__()
        self.app = app

    def get_speed(self) -> int:
        return self.app.settings.speed

    def show_log(self, text: str, system: bool = False) -> None:
        self.app.log(text, system_log=system)

    def show_area(self, points: list) -> None:
        self.app.bridge.run_in_ui(self.app.draw_area, points)

    def on_finished(self, script, graph_file, error) -> None:
        if error is None and self.app.settings.execution_time_log:
            try:
                history.append_execution(
                    self.HISTORY_FILE, graph_file, script, self.execution_time, self.solved
                )
            except OSError as e:
                self.app.bridge.run_in_ui(
                    self.app.status.set, f"Error saving execution history: {e}"
                )
        self.app.bridge.run_in_ui(self.app.on_script_finished)
