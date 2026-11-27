"""
Command line entry point of Grafuria.

Author: Saulo Popov Zambiasi
Created : 2024-10-25
Last Updated: 2025-06-20
Email: saulopz@gmail.com
GitHub: https://github.com/saulopz/grafuria

License: BSD 3-Clause License

This program is designed for the creation of graphs and the execution
of algorithms written in the Lua or Python programming language on those
graphs. It allows users to easily build directed and undirected graphs,
assign weights to edges, and name vertices. The software supports dynamic
interaction with the graph using Lua or Python scripts, enabling the
execution of various algorithms to manipulate the graph's structure and
behavior.

Usage:
    python3 main.py graph=graphs/dodecahedron.json script=scripts/bfs.lua

    Without interface (batch experiments, see headless.py):
    python3 main.py --headless graph=... script=... runs=100 seed=42

Note:
    - The 'graph' parameter specifies the graph file (optional).
    - The 'script' parameter specifies the algorithm script (optional).
    - If no parameters are passed, the program will interactively request
      the user to select the files.

This software is open-source and free to use and modify under the BSD 3-Clause
License.
"""

import os
import sys

# Project folder (contains graphs/, scripts/ and settings.json).
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def resolve_paths(args: list) -> list:
    """
    Makes graph= and script= absolute. Paths given by the user are
    relative to where they called the program; after that we work from
    the project folder, so settings.json and dofile("scripts/...")
    always resolve.
    """
    resolved = []
    for arg in args:
        key, sep, value = arg.partition("=")
        if sep and key in ("graph", "script") and value:
            arg = f"{key}={os.path.abspath(value)}"
        resolved.append(arg)
    return resolved


# -------------------------
# Main
# -------------------------
def main() -> int:
    """Reads the arguments and starts the interface or the headless mode."""
    args = resolve_paths(sys.argv[1:])
    os.chdir(PROJECT_ROOT)

    if "--web" in args:
        from .webui import server  # needs fastapi and uvicorn

        return server.main([a for a in args if a != "--web"])

    if "--headless" in args:
        from .core import headless  # no Tkinter needed

        return headless.main([a for a in args if a != "--headless"])

    graph: str = ""
    script: str = ""
    for arg in args:
        if arg.startswith("graph="):
            graph = arg.split("=", 1)[1]
        elif arg.startswith("script="):
            script = arg.split("=", 1)[1]

    import tkinter as tk

    from .tkui.app import App

    root = tk.Tk()
    app = App(master=root, filename=graph, script=script)
    app.mainloop()
    return 0
