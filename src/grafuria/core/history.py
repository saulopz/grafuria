"""Execution history (execution_history.csv). No interface code."""

import locale
import os
from datetime import datetime


def append_execution(path: str, graph_file: str, script_file: str,
                     execution_time: float, solved: bool) -> None:
    """
    Appends one tab-separated line: date, time, graph, script,
    execution time and solved.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d\t%H:%M:%S")
    seconds = locale.format_string("%.4f", execution_time or 0, grouping=True)
    fields = [
        timestamp,
        os.path.basename(graph_file),
        os.path.basename(script_file),
        seconds,
        solved,
    ]
    with open(path, "a", encoding="utf-8") as f:
        f.write("\t".join(map(str, fields)) + "\n")
