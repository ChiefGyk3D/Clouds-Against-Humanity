#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Start two simulated S3 "tenants" (moto servers) on loopback only.
# Usage: start_tenants.sh up|down|status    (LAB_WORK sets the work directory)
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK="${LAB_WORK:-${TMPDIR:-/tmp}/cah-xtenant-lab}"
PORT_A=5101   # tenant A: governance (source of record)
PORT_B=5102   # tenant B: analytics (processing side)
mkdir -p "$WORK"
is_up() { [ -f "$WORK/$1.pid" ] && kill -0 "$(cat "$WORK/$1.pid")" 2>/dev/null; }
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
