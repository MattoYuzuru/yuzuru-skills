#!/bin/sh
set -eu

PYTHON_BIN=${PYTHON_BIN:-python3}
SCRIPT_PATH=$0

while [ -L "$SCRIPT_PATH" ]; do
  LINK_TARGET=$(readlink "$SCRIPT_PATH")
  case "$LINK_TARGET" in
    /*) SCRIPT_PATH=$LINK_TARGET ;;
    *) SCRIPT_PATH=$(dirname -- "$SCRIPT_PATH")/$LINK_TARGET ;;
  esac
done

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$SCRIPT_PATH")" && pwd)

exec "$PYTHON_BIN" "$SCRIPT_DIR/bootstrap.py" run "$@"
