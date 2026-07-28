#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
BIN_DIR="${YUZURU_BIN_DIR:-${HOME}/.local/bin}"
FORCE=0
DRY_RUN=0

usage() {
  cat <<'EOF'
Usage:
  ./install.sh [--bin-dir ~/.local/bin] [--force] [--dry-run]

Installs `yuzuru` and the backward-compatible `skill` launcher by symlinking
the repository scripts into a user bin directory. It does not install skills
or plugins by itself.

A dangling destination with a recognizable `yuzuru-skills/<launcher>` target
is repaired automatically. --force is required for any other symlink target.
--dry-run reports the exact launcher actions without changing the bin directory.
EOF
}

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --bin-dir)
      [ "$#" -ge 2 ] || die "--bin-dir requires a value"
      BIN_DIR="${2/#\~/${HOME}}"
      shift 2
      ;;
    --force)
      FORCE=1
      shift
      ;;
    --dry-run)
      DRY_RUN=1
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

if [ "$DRY_RUN" -eq 0 ]; then
  mkdir -p "$BIN_DIR"
fi

install_launcher() {
  local command_name="$1"
  local src="${REPO_ROOT}/${command_name}"
  local dest="${BIN_DIR}/${command_name}"
  local current_target=""
  local recognized_stale=0

  [ -f "$src" ] || die "missing CLI script: $src"
  if [ -e "$dest" ] || [ -L "$dest" ]; then
    if [ -L "$dest" ]; then
      current_target="$(readlink "$dest")"
      case "$current_target" in
        "yuzuru-skills/${command_name}"|*/yuzuru-skills/"${command_name}")
          recognized_stale=1
          ;;
      esac
    fi
    if [ -L "$dest" ] && [ "$current_target" = "$src" ]; then
      printf 'already installed: %s -> %s\n' "$dest" "$src"
    elif [ -L "$dest" ] && [ ! -e "$dest" ] && [ "$recognized_stale" -eq 1 ]; then
      if [ "$DRY_RUN" -eq 1 ]; then
        printf 'would repair stale symlink: %s -> %s\n' "$dest" "$src"
      else
        ln -sfn "$src" "$dest"
        printf 'repaired stale symlink: %s -> %s\n' "$dest" "$src"
      fi
    elif [ -L "$dest" ] && [ "$FORCE" -eq 1 ]; then
      if [ "$DRY_RUN" -eq 1 ]; then
        printf 'would update symlink: %s -> %s\n' "$dest" "$src"
      else
        ln -sfn "$src" "$dest"
        printf 'updated symlink: %s -> %s\n' "$dest" "$src"
      fi
    else
      die "$dest already exists and is not a symlink managed by this repo"
    fi
  else
    if [ "$DRY_RUN" -eq 1 ]; then
      printf 'would install: %s -> %s\n' "$dest" "$src"
    else
      ln -s "$src" "$dest"
      printf 'installed: %s -> %s\n' "$dest" "$src"
    fi
  fi
}

install_launcher yuzuru
install_launcher skill

case ":${PATH}:" in
  *":${BIN_DIR}:"*)
    ;;
  *)
    printf '\n%s is not in PATH.\n' "$BIN_DIR"
    printf 'Add this to your shell config, then restart the shell:\n'
    printf '  export PATH="%s:%s"\n' "$BIN_DIR" "\$PATH"
    ;;
esac

if [ "$DRY_RUN" -eq 0 ]; then
  printf '\nNext steps:\n'
  printf '  yuzuru list\n'
  printf '  yuzuru skill install NAME\n'
  printf '  yuzuru marketplace add --agent codex\n'
fi
