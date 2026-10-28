#!/usr/bin/env bash
# macOS setup for kuruitsugizaki (the file tools: read and write .flp projects; no live link to FL on this platform yet).
#   ./setup.sh            asks before touching the Claude desktop app's config
#   ./setup.sh --yes      asks nothing
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
YES=0
[[ "${1:-}" == "--yes" || "${1:-}" == "-y" ]] && YES=1

say() { printf '\n== %s\n' "$1"; }
ask() { [[ $YES -eq 1 ]] && return 0; read -r -p "$1 [y/N] " a; [[ "$a" == [yY]* ]]; }

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This script is for macOS. On Windows use setup.bat." >&2
  exit 1
fi

say "uv"
if ! command -v uv >/dev/null 2>&1; then
  if command -v brew >/dev/null 2>&1; then
    ask "uv is missing; install it with Homebrew?" && brew install uv
  else
    ask "uv is missing; install it with uv's own installer (astral.sh)?" && curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
  fi
fi
command -v uv >/dev/null 2>&1 || { echo "uv is required: https://docs.astral.sh/uv/" >&2; exit 1; }

say "environment (uv sync, about 400 MB in .venv)"
(cd "$HERE" && uv sync)

say "ffmpeg (optional: analysis of renders)"
if ! command -v ffmpeg >/dev/null 2>&1; then
  if command -v brew >/dev/null 2>&1 && ask "ffmpeg is missing; install it with Homebrew?"; then
    brew install ffmpeg
  else
    echo "skipped; renders made in FL work without it, but cannot be analysed here"
  fi
fi

say "live link (FL's controller script and MIDI setting; FL must be closed)"
if ask "Install the controller script and set up FL's kuruitsugizaki MIDI port (FL's settings get a .bak copy)?"; then
  "$HERE/.venv/bin/python" "$HERE/scripts/doctor.py" --install || true
fi

say "Claude desktop app"
if ask "Add the server to the Claude desktop app's config (a .bak copy is kept)?"; then
  "$HERE/.venv/bin/python" "$HERE/scripts/doctor.py" --claude || true
fi

say "check"
"$HERE/.venv/bin/python" "$HERE/scripts/doctor.py" || true

cat <<EOF

Ready. Quit the Claude app fully (Cmd-Q) and start it again, then in a new chat ask it to read docs/INDEX.md in
$HERE and write something. Projects it writes are .flp files; project_write(open=true) opens them in FL. With FL open and the
server running, the live tools (fl_probe, fl_exec, fl_transport) talk to it over a virtual MIDI port.
EOF
