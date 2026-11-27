"""Allows `python3 -m grafuria` (with src/ on the Python path)."""

import sys

from grafuria.cli import main

sys.exit(main())
