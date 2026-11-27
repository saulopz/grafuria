#!/bin/sh
# Runs the test suite exactly as the CI does (GitHub and Codeberg).
#
#   ci/run-tests.sh
#
# Needs: python3 with venv and Tkinter (Debian/Ubuntu: python3-venv
# python3-tk), without a display xvfb (xvfb-run), and Go (go.mod says
# the minimum version). The race detector is used when a C compiler
# is available.
# Set PYTHON to use another interpreter, e.g. PYTHON=python3.12.
set -eu

cd "$(dirname "$0")/.."
PYTHON="${PYTHON:-python3}"
VENV=".venv-ci"

# --system-site-packages: Tkinter comes from the system Python.
"$PYTHON" -m venv --system-site-packages "$VENV"
. "$VENV/bin/activate"
python -m pip install --quiet --disable-pip-version-check -r requirements-dev.txt
python --version

# In CI the interface tests must run, never be skipped.
export GRAFURIA_REQUIRE_GUI=1

if [ -n "${DISPLAY:-}" ] || ! command -v xvfb-run >/dev/null 2>&1; then
    python -m unittest discover -s tests -v
else
    xvfb-run -a python -m unittest discover -s tests -v
fi

# Go: the port of Grafuria (see go.mod).
if [ -n "${GRAFURIA_REQUIRE_GO:-}" ] && ! command -v go >/dev/null 2>&1; then
    echo "Go is required but not installed" >&2
    exit 1
fi
if command -v go >/dev/null 2>&1; then
    go version
    go vet ./...
    if command -v gcc >/dev/null 2>&1; then
        go test -race -count=1 ./...
    else
        go test -count=1 ./...
    fi
fi
