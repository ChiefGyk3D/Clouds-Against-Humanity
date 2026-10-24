#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Drive the scaled-down WordPress fleet replica. Local only; every port is on 127.0.0.1.
#
#   ./lab.sh up          write .env (random origin secret), start the stack
#   ./lab.sh status      containers and the shared counters
#   ./lab.sh cache       cold request, then warm request: watch X-Cache-Status go MISS -> HIT
#   ./lab.sh bypass      prove a logged-in cookie bypasses the cache, and the careless edge leaks
#   ./lab.sh stampede    20 simultaneous cold requests: careful edge vs careless edge
#   ./lab.sh waf         the toy WAF, a rate limit, and an evasion of the toy rules
#   ./lab.sh uploads     the plugin-writes-to-disk mistake and its fix
#   ./lab.sh drill       kill one web node, keep sending traffic, bring it back
#   ./lab.sh redis-drill stop the object cache; pages still work, slower
#   ./lab.sh origin      show that the origin refuses a request that skipped the edge
#   ./lab.sh down        stop everything and delete the lab's volumes
set -euo pipefail

LAB="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RULE="$(cd "$LAB/../.." && pwd)/scripts/secret_rule.py"
EDGE="http://127.0.0.1:${EDGE_PORT:-8080}"
NAIVE="http://127.0.0.1:${EDGE_NAIVE_PORT:-8081}"
FAILS=0

die() { echo "lab: $*" >&2; exit 1; }
compose() {
  if docker compose version >/dev/null 2>&1; then
    docker compose --project-directory "$LAB" -f "$LAB/compose.yaml" "$@"
  elif command -v docker-compose >/dev/null 2>&1; then
    docker-compose --project-directory "$LAB" -f "$LAB/compose.yaml" "$@"
  else
    die "neither 'docker compose' nor 'docker-compose' is available"
  fi
}
check() { # check "what" condition-exit-status
  if [ "$2" -eq 0 ]; then echo "PASS  $1"; else echo "FAIL  $1"; FAILS=$((FAILS + 1)); fi
}
header() { curl -s -D - -o /dev/null "${@:2}" "$1" | tr -d '\r' ; }
hval() { grep -i "^$1:" | head -1 | sed 's/^[^:]*: *//'; }
reset() { curl -s -X POST "$EDGE/reset-stats" -o /dev/null || true; }
dbq() { curl -s "$EDGE/stats?x=$RANDOM" | python3 -I -c 'import json,sys; print(json.load(sys.stdin).get("db_queries",-1))'; }
finish() { [ "$FAILS" -eq 0 ] && echo "all checks passed" || { echo "$FAILS check(s) failed"; exit 1; }; }

# ORIGIN_SECRET is required: it is what makes the origin refuse a request that
# skipped the edge. A value from the shell environment (compose reads it first)
# or from .env must pass the repository's one placeholder rule
# (scripts/secret_rule.py) or the lab refuses to start. Only an empty or missing
# value gets a random one. The value is never printed.
ensure_origin_secret() {
  local v="" new
  if [ -n "${ORIGIN_SECRET:-}" ]; then
    printf '%s' "$ORIGIN_SECRET" | python3 -I "$RULE" ORIGIN_SECRET >&2 ||
      die "refusing to start: the ORIGIN_SECRET in your shell environment is not usable"
    return 0
  fi
  if [ -f "$LAB/.env" ]; then v="$(sed -n 's/^ORIGIN_SECRET=//p' "$LAB/.env" | tail -n 1)"; fi
  if [ -n "$v" ]; then
    printf '%s' "$v" | python3 -I "$RULE" ORIGIN_SECRET >&2 ||
      die "refusing to start: the ORIGIN_SECRET in $LAB/.env is not usable (clear it to get a random one)"
    return 0
  fi
  new="$(python3 -I -c 'import secrets; print(secrets.token_hex(16))')"
  if [ -f "$LAB/.env" ] && grep -q '^ORIGIN_SECRET=' "$LAB/.env"; then
    sed -i "s/^ORIGIN_SECRET=.*/ORIGIN_SECRET=${new}/" "$LAB/.env"
  else
    (umask 077 && printf 'ORIGIN_SECRET=%s\n' "$new" >> "$LAB/.env")
  fi
}

# Sourced by the tests: define the functions and stop before the command switch.
if [ "${BASH_SOURCE[0]}" != "$0" ]; then return 0; fi

case "${1:-}" in
  up)
    ensure_origin_secret
    compose --env-file "$LAB/.env" up -d
    echo "edge (careful): $EDGE    edge (careless): $NAIVE"
    for _ in $(seq 1 30); do curl -sf "$EDGE/" -o /dev/null && break; sleep 1; done
    curl -s "$EDGE/" ;;
  status)
    compose --env-file "$LAB/.env" ps
    curl -s "$EDGE/stats?x=$RANDOM" ;;
  cache)
    reset
    u="$EDGE/?page=$RANDOM"
    echo "--- first request for $u"; header "$u" | grep -i -E "^(HTTP|x-cache-status|x-node|x-obj-cache)"
    echo "--- second request for the same URL"; header "$u" | grep -i -E "^(HTTP|x-cache-status|x-node|age)" ;;
  bypass)
    u="$EDGE/?bypass=$RANDOM"
    curl -s "$u" -o /dev/null
    a=$(header "$u" | hval X-Cache-Status)
    check "anonymous visitor: second request is a HIT (got $a)" "$([ "$a" = HIT ]; echo $?)"
    b=$(header "$u" -H 'Cookie: wordpress_logged_in_demo=1' | hval X-Cache-Status)
    check "logged-in cookie: cache is BYPASSed (got $b)" "$([ "$b" = BYPASS ]; echo $?)"
    body=$(curl -s "$u" -H 'Cookie: wordpress_logged_in_demo=1')
    check "logged-in visitor sees the private page" "$(echo "$body" | grep -q 'Welcome back'; echo $?)"
    body=$(curl -s "$u")
    check "the next anonymous visitor does NOT see it" "$(! echo "$body" | grep -q 'Welcome back'; echo $?)"
    v="$NAIVE/?leak=$RANDOM"
    curl -s "$v" -H 'Cookie: wordpress_logged_in_demo=1' -o /dev/null
    leaked=$(curl -s "$v")
    if echo "$leaked" | grep -q 'Welcome back'; then echo "LEAK  careless edge served the logged-in page to an anonymous visitor"; else echo "no leak on the careless edge (unexpected)"; fi
    finish ;;
  stampede)
    reset
    k=$RANDOM
    for i in $(seq 1 20); do curl -s "$EDGE/slow?k=good$k" -o /dev/null & done; wait
    good=$(dbq); echo "careful edge (cache lock on): 20 simultaneous cold requests -> $good origin queries"
    reset
    for i in $(seq 1 20); do curl -s "$NAIVE/slow?k=naive$k" -o /dev/null & done; wait
    naive=$(dbq); echo "careless edge (no lock):        20 simultaneous cold requests -> $naive origin queries" ;;
  waf)
    for path in "/?q=1" "/?q=1%20union%20select%201" "/?q=%3Cscript%3E" "/?q=uni%6fn%20select%201"; do
      printf '%-34s -> %s\n' "$path" "$(curl -s -o /dev/null -w '%{http_code}' "$EDGE$path")"
    done
    echo "--- 8 quick logins from one address (limit: 1 per second, burst 3)"
    for i in $(seq 1 8); do curl -s -o /dev/null -w '%{http_code} ' -X POST "$EDGE/wp-login.php"; done; echo ;;
  uploads)
    reads() { for i in $(seq 1 6); do curl -s -o /dev/null -w '%{http_code} ' "$EDGE/$1/$2?x=$RANDOM$i"; done; echo; }
    echo "--- one upload written to ONE node's own disk, then read 6 times through the balancer:"
    curl -s -X POST --data 'hello' "$EDGE/upload-local?name=a.txt"
    printf 'status codes: '; reads local-files a.txt
    echo "--- one upload written to the shared volume, then read 6 times:"
    curl -s -X POST --data 'hello' "$EDGE/upload-shared?name=b.txt"
    printf 'status codes: '; reads shared-files b.txt ;;
  drill)
    count() { for i in $(seq 1 12); do curl -s -o /dev/null -D - "$EDGE/?n=$RANDOM$i" | tr -d '\r' | hval X-Node; done | sort | uniq -c | tr '\n' ' '; echo; }
    echo "both nodes up:   $(count)"
    compose --env-file "$LAB/.env" kill web1 >/dev/null
    errs=0; for i in $(seq 1 12); do c=$(curl -s -o /dev/null -w '%{http_code}' "$EDGE/?n=$RANDOM$i"); [ "$c" = 200 ] || errs=$((errs + 1)); done
    echo "web1 killed:     $(count) errors out of 12 requests: $errs"
    compose --env-file "$LAB/.env" start web1 >/dev/null; sleep 8
    echo "web1 restarted:  $(count)" ;;
  redis-drill)
    compose --env-file "$LAB/.env" stop redis >/dev/null
    printf 'object cache stopped: '; header "$EDGE/?n=$RANDOM" | grep -i -E "^(HTTP|x-obj-cache)" | tr '\n' ' '; echo
    compose --env-file "$LAB/.env" start redis >/dev/null; sleep 2
    printf 'object cache back:    '; header "$EDGE/?n=$RANDOM" | grep -i -E "^(HTTP|x-obj-cache)" | tr '\n' ' '; echo ;;
  origin)
    echo "--- from inside the web tier, call the balancer WITHOUT the edge's secret header:"
    compose --env-file "$LAB/.env" exec -T web1 python -I -c \
      'import urllib.request,urllib.error
try: print(urllib.request.urlopen("http://lb/").status)
except urllib.error.HTTPError as e: print(e.code, e.read().decode().strip())'
    echo "--- from the host, the balancer and the web nodes publish no port:"
    compose --env-file "$LAB/.env" ps --format '{{.Service}} {{.Ports}}' ;;
  down)
    compose --env-file "$LAB/.env" down -v 2>/dev/null || compose down -v
    rm -f "$LAB/.env" ;;
  *) sed -n '3,15p' "$0"; exit 2 ;;
esac
