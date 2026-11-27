#!/usr/bin/env python3
"""
Grafuria launcher (keeps `python3 main.py ...` working).

    python3 main.py graph=graphs/dodecahedron.json script=scripts/bfs.lua
    python3 main.py --headless graph=... script=... runs=100 seed=42
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from grafuria.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
