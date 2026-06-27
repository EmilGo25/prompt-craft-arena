#!/usr/bin/env bash
#
# share.sh — run the whole game on this machine and expose it to the internet
# with two free Cloudflare quick tunnels, so remote players can join.
#
# Why this exists: the open-weight providers (Ollama judge + Draw Things image
# gen) run locally, so the game must run here. This script starts the backend,
# builds the frontend pointed at the public backend URL, serves it, and opens a
# tunnel for each — then prints the one URL to share with players.
#
# Usage:   ./scripts/share.sh
# Stop:    Ctrl+C (tears down every process it started)
#
# Env overrides:
#   BACKEND_PORT  (default 8000)
#   FRONTEND_PORT (default 4173)
#
set -euo pipefail

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-4173}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$(mktemp -d -t pca-share-XXXXXX)"
PIDS=()

note() { printf '\033[36m[share]\033[0m %s\n' "$1"; }
warn() { printf '\033[33m[share] warning:\033[0m %s\n' "$1"; }
die()  { printf '\033[31m[share] error:\033[0m %s\n' "$1" >&2; exit 1; }

cleanup() {
  note "shutting down…"
  for pid in "${PIDS[@]:-}"; do
    kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
  rm -rf "$LOG_DIR"
}
trap cleanup INT TERM EXIT

# --- preflight ---------------------------------------------------------------
command -v cloudflared >/dev/null 2>&1 || die "cloudflared not found. Install it: brew install cloudflared"
command -v uv >/dev/null 2>&1 || die "uv not found. See https://docs.astral.sh/uv/"
command -v npm >/dev/null 2>&1 || die "npm not found."

# Friendly heads-up if the local model servers aren't up (non-fatal: the stub
# and random providers still work without them).
curl -sf -o /dev/null "http://localhost:11434/v1/models" 2>/dev/null \
  || warn "Ollama not reachable on :11434 — the 'ollama' judge will fall back. (ollama serve)"
curl -sf -o /dev/null "http://localhost:7860/" 2>/dev/null \
  || warn "No A1111/Draw Things server on :7860 — the 'drawthings' image provider will fail. Start Draw Things + enable its HTTP server."

# Wait for a trycloudflare URL to show up in a tunnel's log; echoes the URL.
wait_for_tunnel_url() {
  local logfile="$1" url=""
  for _ in $(seq 1 40); do
    url="$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$logfile" 2>/dev/null | head -1 || true)"
    [ -n "$url" ] && { echo "$url"; return 0; }
    sleep 1
  done
  return 1
}

# --- backend -----------------------------------------------------------------
# Supervised: run-backend.sh restarts the backend if it crashes and stops it
# gracefully when this script tears down (its SIGTERM is forwarded as a clean
# shutdown). `exec` so $! is the supervisor itself, not a wrapper subshell.
note "starting backend on :$BACKEND_PORT (supervised) …"
( cd "$REPO_ROOT" && export BACKEND_PORT && exec ./scripts/run-backend.sh ) \
  >"$LOG_DIR/backend.log" 2>&1 &
PIDS+=("$!")

note "opening tunnel for backend …"
cloudflared tunnel --url "http://localhost:$BACKEND_PORT" \
  >"$LOG_DIR/backend-tunnel.log" 2>&1 &
PIDS+=("$!")

BACKEND_URL="$(wait_for_tunnel_url "$LOG_DIR/backend-tunnel.log")" \
  || die "backend tunnel did not come up (see $LOG_DIR/backend-tunnel.log)"
note "backend public URL: $BACKEND_URL"

# --- frontend ----------------------------------------------------------------
if [ ! -d "$REPO_ROOT/web/node_modules" ]; then
  note "installing frontend deps (first run) …"
  ( cd "$REPO_ROOT/web" && npm install ) >"$LOG_DIR/npm-install.log" 2>&1 \
    || die "npm install failed (see $LOG_DIR/npm-install.log)"
fi

note "building frontend against $BACKEND_URL …"
( cd "$REPO_ROOT/web" && VITE_API_BASE="$BACKEND_URL" npm run build ) \
  >"$LOG_DIR/frontend-build.log" 2>&1 \
  || die "frontend build failed (see $LOG_DIR/frontend-build.log)"

note "serving frontend on :$FRONTEND_PORT …"
( cd "$REPO_ROOT/web" && npm run preview -- --host --port "$FRONTEND_PORT" ) \
  >"$LOG_DIR/frontend.log" 2>&1 &
PIDS+=("$!")

note "opening tunnel for frontend …"
cloudflared tunnel --url "http://localhost:$FRONTEND_PORT" \
  >"$LOG_DIR/frontend-tunnel.log" 2>&1 &
PIDS+=("$!")

FRONTEND_URL="$(wait_for_tunnel_url "$LOG_DIR/frontend-tunnel.log")" \
  || die "frontend tunnel did not come up (see $LOG_DIR/frontend-tunnel.log)"

# --- ready -------------------------------------------------------------------
cat <<EOF

  ┌──────────────────────────────────────────────────────────────┐
  │  Prompt-craft Arena is live. Share this link with players:     │
  │                                                                │
  │     $FRONTEND_URL
  │                                                                │
  │  Backend:  $BACKEND_URL
  │  Logs:     $LOG_DIR
  │                                                                │
  │  Keep this terminal open. Press Ctrl+C to stop and tear down.  │
  └──────────────────────────────────────────────────────────────┘

EOF

note "running — Ctrl+C to stop."
wait
