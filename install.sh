#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
COMMAND_NAME="skill"
BIN_DIR="${HOME}/.local/bin"
FORCE=0

usage() {
  cat <<'EOF'
Usage:
  ./install.sh [--command skill] [--bin-dir ~/.local/bin] [--force]

Installs the repository CLI by symlinking ./skill into a user bin directory.
It does not install any Codex skills by itself; run `skill install` after this.
EOF
}

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --command)
      [ "$#" -ge 2 ] || die "--command requires a value"
      COMMAND_NAME="$2"
      shift 2
      ;;
    --bin-dir)
      [ "$#" -ge 2 ] || die "--bin-dir requires a value"
      BIN_DIR="${2/#\~/${HOME}}"
      shift 2
      ;;
    --force)
      FORCE=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage >&2
      die "unknown option: $1"
      ;;
  esac
done

case "$COMMAND_NAME" in
  *[!A-Za-z0-9._-]*|'')
    die "unsafe command name: $COMMAND_NAME"
    ;;
esac

SRC="${REPO_ROOT}/skill"
DEST="${BIN_DIR}/${COMMAND_NAME}"

[ -f "$SRC" ] || die "missing CLI script: $SRC"
mkdir -p "$BIN_DIR"

if [ -e "$DEST" ] || [ -L "$DEST" ]; then
  if [ -L "$DEST" ] && [ "$(readlink "$DEST")" = "$SRC" ]; then
    printf 'already installed: %s -> %s\n' "$DEST" "$SRC"
  elif [ -L "$DEST" ] && [ "$FORCE" -eq 1 ]; then
    ln -sfn "$SRC" "$DEST"
    printf 'updated symlink: %s -> %s\n' "$DEST" "$SRC"
  else
    die "$DEST already exists and is not a symlink managed by this repo"
  fi
else
  ln -s "$SRC" "$DEST"
  printf 'installed: %s -> %s\n' "$DEST" "$SRC"
fi

case ":${PATH}:" in
  *":${BIN_DIR}:"*)
    ;;
  *)
    printf '\n%s is not in PATH.\n' "$BIN_DIR"
    printf 'Add this to your shell config, then restart the shell:\n'
    printf '  export PATH="%s:$PATH"\n' "$BIN_DIR"
    ;;
esac

printf '\nNext steps:\n'
printf '  %s list\n' "$COMMAND_NAME"
printf '  %s install\n' "$COMMAND_NAME"
printf '  %s install all\n' "$COMMAND_NAME"

