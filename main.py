#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Main program for Grafuria.

Author: Saulo Popov Zambiasi
Updated: 2025-05-05
Email: saulopz@gmail.com
GitHub: https://github.com/saulopz/grafuria

License: BSD 3-Clause License

This program is designed for the creation of graphs and the execution
of algorithms written in the Lua programming language on those graphs.
It allows users to easily build directed and undirected graphs, assign
weights to edges, and name vertices. The software supports dynamic
interaction with the graph using Lua scripts, enabling the execution
of various algorithms to manipulate the graph's structure and behavior.

Usage:
    python3 main.py [gr=graph/dodecahedron.json] [alg=lua/force.lua]

Note:
    - The 'gr' parameter specifies the graph file (optional).
    - The 'alg' parameter specifies the algorithm script (optional).
    - If no parameters are passed, the program will interactively request
      the user to select the files.

This software is open-source and free to use and modify under the BSD 3-Clause
License.
"""

import sys
from app import App
import tkinter as tk


# -------------------------
# Main
# -------------------------
def main():
    """
    gets arguments if exists and start the graphic interface.

    Arguments
    ---------
    graph: str
        graph path and filename.
    script: str
        script path and filename.
    """
    args = sys.argv[1:]
    graph: str = ""
    algorithm: str = ""
    for arg in args:
        if arg.startswith("graph="):
            graph = arg.split("=", 1)[1]
        elif arg.startswith("script="):
            algorithm = arg.split("=", 1)[1]

    root = tk.Tk()
    app: App = App(master=root, filename=graph, script_lua=algorithm)
    app.mainloop()


if __name__ == "__main__":
    main()

# Todo: save the path founded with solution and a best log.
