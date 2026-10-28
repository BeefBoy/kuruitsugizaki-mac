#!/usr/bin/env bash
# macOS: undo what setup.sh did (controller script, FL's kuruitsugizaki MIDI setting, the Claude entries, saved plugin
# states). uv, ffmpeg and .venv stay. Pass --yes to skip the question; --help lists the rest.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ ! -x "$HERE/.venv/bin/python" ]]; then
  echo ".venv is missing; run ./setup.sh first, or remove the pieces by hand (INSTALL-macos.md)." >&2
  exit 1
fi
cd "$HERE"
exec "$HERE/.venv/bin/python" "$HERE/scripts/uninstall.py" "$@"
