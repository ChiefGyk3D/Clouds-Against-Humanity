#!/usr/bin/env bash
# Run the synthetic multi-site monitoring demo in labs/demo-monitoring.
# Every metric is invented by a generator container. Nothing here touches a
# real host or cloud account.
#
#   scripts/demo_monitoring.sh up                 start Prometheus, Grafana and the generator
#   scripts/demo_monitoring.sh silent-site [S]    make site S (default site-tor2) stop answering
#   scripts/demo_monitoring.sh restore-site       let every site answer again
#   scripts/demo_monitoring.sh restart-prometheus apply an edit to a rule file (only the target file is watched)
#   scripts/demo_monitoring.sh test               promtool: check config, run the alert unit tests
#   scripts/demo_monitoring.sh screenshots        print the capture plan (viewport, URLs, file names)
#   scripts/demo_monitoring.sh status             show the containers and the alert state
#   scripts/demo_monitoring.sh down               stop everything and delete the demo volumes
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAB="$ROOT/labs/demo-monitoring"
PROM_IMAGE="docker.io/prom/prometheus:v3.5.0"

die() { echo "demo_monitoring: $*" >&2; exit 1; }

compose() {
  if docker compose version >/dev/null 2>&1; then
    docker compose --project-directory "$LAB" -f "$LAB/docker-compose.yml" "$@"
  elif command -v docker-compose >/dev/null 2>&1; then
    docker-compose --project-directory "$LAB" -f "$LAB/docker-compose.yml" "$@"
  else
    die "neither 'docker compose' nor 'docker-compose' is available"
  fi
}

need_docker() {
  command -v docker >/dev/null 2>&1 || die "docker is not installed"
  docker info >/dev/null 2>&1 || die "docker is not usable by this user (no sudo is used here)"
}

load_ports() {
  # Read the optional port overrides without sourcing the file (no code execution).
  GRAFANA_PORT=3300
  PROM_PORT=9190
  if [ -f "$LAB/.env" ]; then
    local v
    v="$(sed -n 's/^DEMO_GRAFANA_PORT=//p' "$LAB/.env" | tail -n 1)"
    if [ -n "$v" ]; then GRAFANA_PORT="$v"; fi
    v="$(sed -n 's/^DEMO_PROMETHEUS_PORT=//p' "$LAB/.env" | tail -n 1)"
    if [ -n "$v" ]; then PROM_PORT="$v"; fi
  fi
}

ensure_env() {
  if [ -f "$LAB/.env" ] && grep -q '^GRAFANA_ADMIN_PASSWORD=.\+' "$LAB/.env"; then
    return 0
  fi
  if [ -n "${GRAFANA_ADMIN_PASSWORD:-}" ]; then
    return 0
  fi
  local pw
  pw="$(head -c 24 /dev/urandom | base64 | tr -d '/+=\n' | head -c 24)"
  (umask 077 && cp "$LAB/env.example" "$LAB/.env")
  # Replace the empty value; the password is random and lives only in the untracked .env.
  sed -i "s/^GRAFANA_ADMIN_PASSWORD=.*/GRAFANA_ADMIN_PASSWORD=${pw}/" "$LAB/.env"
  echo "Wrote $LAB/.env (untracked) with a random Grafana admin password."
}

# Say where the Grafana admin password comes from, never what it is. Compose
# gives the shell environment precedence over the .env file, so check it first.
password_hint() {
  if [ -n "${GRAFANA_ADMIN_PASSWORD:-}" ]; then
    echo "password: your shell environment (GRAFANA_ADMIN_PASSWORD)"
  else
    echo "password: in $LAB/.env (GRAFANA_ADMIN_PASSWORD)"
  fi
}

cmd_up() {
  need_docker
  ensure_env
  load_ports
  compose up -d
  echo
  echo "Grafana     http://127.0.0.1:${GRAFANA_PORT}   user: admin   $(password_hint)"
  echo "Prometheus  http://127.0.0.1:${PROM_PORT}"
  echo "Give it two minutes to collect a few scrapes, then open the dashboard CAH: Sites overview."
}

cmd_down() {
  need_docker
  ensure_env
  compose down -v
  rm -f "$LAB/state/silent"
}

cmd_restart_prometheus() {
  need_docker
  ensure_env
  load_ports
  # Rule files are read at start; the lab has no lifecycle reload endpoint, and
  # only prometheus/targets.json (file service discovery) is re-read on its own.
  compose restart prometheus
  echo "Prometheus restarted; it re-read prometheus.yml and the rule files."
}

cmd_silent() {
  local site="${1:-site-tor2}"
  case "$site" in
    site-tor1 | site-tor2) ;;
    *) die "unknown site '$site' (the demo has site-tor1 and site-tor2)" ;;
  esac
  mkdir -p "$LAB/state"
  printf '%s\n' "$site" >"$LAB/state/silent"
  chmod 644 "$LAB/state/silent"
  echo "$site now answers every scrape with HTTP 503. Watch up == 0, then CloudSiteSilent after about a minute."
}

cmd_restore() {
  rm -f "$LAB/state/silent"
  echo "Every site answers again."
}

cmd_test() {
  need_docker
  docker run --rm --entrypoint promtool -v "$LAB/prometheus:/etc/prometheus:ro" "$PROM_IMAGE" \
    check config /etc/prometheus/prometheus.yml
  docker run --rm --entrypoint promtool -v "$LAB/prometheus:/etc/prometheus:ro" "$PROM_IMAGE" \
    test rules /etc/prometheus/tests/alerts.test.yml /etc/prometheus/tests/alerts-site-removed.test.yml
}

cmd_status() {
  need_docker
  ensure_env
  load_ports
  compose ps
  echo
  curl -fsS "http://127.0.0.1:${PROM_PORT}/api/v1/alerts" || echo "Prometheus is not answering on ${PROM_PORT}."
  echo
}

cmd_screenshots() {
  load_ports
  cat <<EOF
Screenshot plan (headless browser, fixed viewport 1440x900, strip PNG metadata, keep each file <= 600 KB).
Take the Grafana ones after logging in as admin. Never put the password in a screenshot or a file.

  1  http://127.0.0.1:${GRAFANA_PORT}/d/cah-sites-overview?from=now-15m&to=now        demo-sites-overview-healthy.png
  2  http://127.0.0.1:${GRAFANA_PORT}/d/cah-droplet-health?from=now-15m&to=now&var-site=site-tor1&var-instance=192.0.2.11   demo-droplet-health.png
  3  http://127.0.0.1:${PROM_PORT}/targets                                                 demo-prometheus-targets.png
  then: $0 silent-site site-tor2   (wait about 2 minutes)
  4  http://127.0.0.1:${GRAFANA_PORT}/d/cah-sites-overview?from=now-15m&to=now        demo-sites-overview-silent.png
  5  http://127.0.0.1:${PROM_PORT}/alerts                                                  demo-prometheus-alerts-firing.png
  finally: $0 restore-site
EOF
}

main() {
  local sub="${1:-}"
  if [ "$#" -gt 0 ]; then shift; fi
  case "$sub" in
    up) cmd_up ;;
    down) cmd_down ;;
    silent-site) cmd_silent "$@" ;;
    restore-site) cmd_restore ;;
    restart-prometheus) cmd_restart_prometheus ;;
    test) cmd_test ;;
    status) cmd_status ;;
    screenshots) cmd_screenshots ;;
    *)
      sed -n '2,14p' "${BASH_SOURCE[0]}"
      [ -z "$sub" ] || die "unknown subcommand '$sub'"
      ;;
  esac
}

# Run only when executed, so the tests can source the functions.
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  main "$@"
fi
