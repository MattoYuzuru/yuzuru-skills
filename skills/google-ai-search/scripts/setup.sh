#!/bin/sh
set -eu

PYTHON_BIN=${PYTHON_BIN:-python3}
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

exec "$PYTHON_BIN" "$SCRIPT_DIR/setup.py" configure
