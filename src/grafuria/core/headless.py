"""
Headless execution of Grafuria scripts (no graphical interface).

Runs a script several times over a graph and prints one line per run
as tab-separated values, ready for a spreadsheet or pandas:

    python3 main.py --headless graph=graphs/dodecahedron.json \\
        script=scripts/nemertea/nemertea.lua runs=100 seed=42 deep=9

Arguments
---------
graph=PATH      graph file (required)
script=PATH     Lua or Python script (required)
runs=N          number of executions (default 1)
seed=S          base seed; run i uses seed S+i. Without it a random base
                seed is chosen. The seed of every run is always printed,
                so any run can be reproduced.
log=SYMBOLS     print script log lines starting with these symbols to
                stderr (e.g. log=#$). Default: none.
NAME=VALUE      overrides a script parameter (from the script's .json).
"""

import json
import os
import random
import sys
import time
from typing import Optional

from .graph import Graph
from .scripting import describe_error, load_script_parameters, run_script


class HeadlessHost:
    """Host for scripts without interface: no animation, no pauses."""

    def __init__(self, variables: dict, log_symbols: str = "", out=sys.stderr):
        self.variables = variables
        self.log_symbols = log_symbols
        self.out = out
        self.solved = False
        self.execution_time: Optional[float] = None
        self.logs: list = []

    def log(self, text):
        if not text:
            return
        text = str(text)
        self.logs.append(text)
        if text[0] in self.log_symbols:
            print(text[1:], file=self.out)

    def step(self):
        pass

    def is_stopped(self):
        return False

    def get_var(self, name):
        return self.variables.get(name)

    def set_solved(self, solved):
        self.solved = bool(solved)

    def set_execution_time(self, seconds):
        self.execution_time = seconds

    def area_add(self, x, y):
        pass

    def area_close(self):
        pass


def parse_value(text: str):
    """'7' -> 7, '0.5' -> 0.5, 'true' -> True, anything else -> str."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def run_once(graph_file: str, script: str, variables: dict, seed: int,
             log_symbols: str = "") -> dict:
    """Loads a fresh graph, runs the script once and returns the result."""
    graph = Graph.load(graph_file)
    graph.shuffle_edges(random.Random(seed))  # as the interface does on load
    host = HeadlessHost(variables, log_symbols)
    start = time.perf_counter()
    error = ""
    try:
        run_script(script, graph, host, seed=seed)
    except Exception as e:
        error = describe_error(e, script).splitlines()[0]
    wall = time.perf_counter() - start
    return {
        "seed": seed,
        "solved": host.solved,
        "script_time": host.execution_time,
        "wall_time": wall,
        "error": error,
        "graph": graph,
        "host": host,
    }


def main(args: list) -> int:
    options = {}
    for arg in args:
        if "=" not in arg:
            print(f"Invalid argument: {arg} (expected NAME=VALUE)", file=sys.stderr)
            return 2
        key, value = arg.split("=", 1)
        options[key] = value

    graph_file = options.pop("graph", "")
    script = options.pop("script", "")
    if not graph_file or not script:
        print(__doc__, file=sys.stderr)
        return 2
    runs = int(options.pop("runs", 1))
    seed_text = options.pop("seed", None)
    base_seed = int(seed_text) if seed_text is not None else random.randrange(2**31)
    log_symbols = options.pop("log", "")

    variables = load_script_parameters(script)
    for key, value in options.items():
        if key not in variables:
            known = ", ".join(sorted(variables)) or "none"
            print(f"Unknown parameter '{key}'. Script parameters: {known}", file=sys.stderr)
            return 2
        variables[key] = parse_value(value)

    graph_name = os.path.splitext(os.path.basename(graph_file))[0]
    script_name = os.path.basename(script)
    params = " ".join(f"{k}={v}" for k, v in sorted(variables.items()))
    print(f"# graph={graph_name} script={script_name} runs={runs} base_seed={base_seed} {params}")
    print("run\tseed\tsolved\tscript_time\twall_time\terror")

    solved_count = 0
    walls = []
    for i in range(runs):
        r = run_once(graph_file, script, variables, base_seed + i, log_symbols)
        solved_count += r["solved"]
        walls.append(r["wall_time"])
        script_time = "" if r["script_time"] is None else f"{r['script_time']:.6f}"
        print(f"{i}\t{r['seed']}\t{r['solved']}\t{script_time}\t{r['wall_time']:.6f}\t{r['error']}")
        sys.stdout.flush()

    mean = sum(walls) / len(walls) if walls else 0
    print(f"# solved {solved_count}/{runs} | mean wall time {mean:.6f}s", file=sys.stderr)
    return 0
