#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Start two simulated S3 "tenants" (moto servers) on loopback only.
# Usage: start_tenants.sh up|down|status    (LAB_WORK overrides the private work directory)
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK="${LAB_WORK:-${XDG_RUNTIME_DIR:-$HOME/.cache}/cah-xtenant-lab}"
PORT_A=5101   # tenant A: governance (source of record)
PORT_B=5102   # tenant B: analytics (processing side)

# The work folder holds a Python environment this script runs and pid files it
# kills by. Keep it private: yours, not a symlink, not writable by anyone else.
if [ -L "$WORK" ]; then echo "refusing: $WORK is a symlink" >&2; exit 1; fi
if [ -e "$WORK" ]; then
  [ -d "$WORK" ] || { echo "refusing: $WORK is not a directory" >&2; exit 1; }
  [ -O "$WORK" ] || { echo "refusing: $WORK is not owned by you" >&2; exit 1; }
  mode="$(stat -c %a "$WORK" 2>/dev/null || stat -f %Lp "$WORK")"
  case "$mode" in
    *[0-7][2367]|*[2367][0-7]) echo "refusing: $WORK is group or other writable (mode $mode)" >&2; exit 1 ;;
  esac
else
  mkdir -p "$(dirname "$WORK")"
  mkdir -m 700 "$WORK"
fi

pid_ok() {  # $1 = tenant name, $2 = port: pid file is digits only, ours, and a moto server on that port
  local f="$WORK/$1.pid" pid cmd
  [ -f "$f" ] && [ -O "$f" ] || return 1
  pid="$(cat "$f")"
  [[ "$pid" =~ ^[0-9]+$ ]] || return 1
  kill -0 "$pid" 2>/dev/null || return 1
  cmd="$(ps -o command= -p "$pid" 2>/dev/null)" || return 1
  [[ "$cmd" == *"moto.server"* && "$cmd" == *"-p $2"* ]]
}
is_up() { pid_ok "$1" "$([ "$1" = a ] && echo "$PORT_A" || echo "$PORT_B")"; }
case "${1:-status}" in
  up)
    [ -x "$WORK/venv/bin/python" ] || python3 -m venv "$WORK/venv"
    "$WORK/venv/bin/pip" install -q -r "$HERE/requirements.txt"
    for pair in "a:$PORT_A" "b:$PORT_B"; do
      name="${pair%%:*}"; port="${pair##*:}"
      if is_up "$name"; then echo "tenant $name already up"; continue; fi
      "$WORK/venv/bin/python" -m moto.server -H 127.0.0.1 -p "$port" \
        >"$WORK/$name.log" 2>&1 &
      echo $! >"$WORK/$name.pid"
    done
    sleep 3; "$0" status ;;
  down)
    for name in a b; do
      if is_up "$name"; then kill "$(cat "$WORK/$name.pid")" || true; fi
      rm -f "${WORK:?}/${name:?}.pid"
    done
    echo "tenants stopped" ;;
  status)
    for pair in "a:$PORT_A" "b:$PORT_B"; do
      name="${pair%%:*}"; port="${pair##*:}"
      if is_up "$name"; then echo "tenant $name: up on http://127.0.0.1:$port"
      else echo "tenant $name: down"; fi
    done ;;
  *) echo "usage: $0 up|down|status" >&2; exit 2 ;;
esac
