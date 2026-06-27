#!/usr/bin/env bash
#
# run-backend.sh — supervise the Prompt-craft Arena backend.
#
# Runs `uvicorn server.app:app` and keeps it alive: if it exits unexpectedly
# (crash / non-graceful exit), it restarts with capped exponential backoff and a
# crash-loop guard so a permanently-broken backend can't hot-loop forever.
#
# Graceful shutdown: Ctrl+C or SIGTERM stops the backend *cleanly* — it forwards
# SIGTERM to uvicorn, which runs the app's lifespan shutdown (sweeper +
# objective pool drain), waits up to GRACE_SECONDS, and only then exits. A
# graceful stop does NOT trigger a restart.
#
# Usage:   ./scripts/run-backend.sh
# Stop:    Ctrl+C (or `kill <pid>`)
#
# Env overrides:
#   BACKEND_HOST    (default 127.0.0.1)
#   BACKEND_PORT    (default 8000)
#   GRACE_SECONDS   (default 10)  how long to wait for a clean shutdown
#   MAX_CRASHES     (default 5)   crashes within CRASH_WINDOW before giving up
#   CRASH_WINDOW    (default 60)  sliding window (seconds) for the crash guard
#   BACKOFF_MAX     (default 30)  cap (seconds) on restart backoff
#
# NOTE: no `set -e` — this script deliberately inspects non-zero exit codes.
set -uo pipefail

BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
GRACE_SECONDS="${GRACE_SECONDS:-10}"
MAX_CRASHES="${MAX_CRASHES:-5}"
CRASH_WINDOW="${CRASH_WINDOW:-60}"
BACKOFF_MAX="${BACKOFF_MAX:-30}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

note() { printf '\033[36m[backend]\033[0m %s\n' "$1"; }
warn() { printf '\033[33m[backend] warning:\033[0m %s\n' "$1"; }
die()  { printf '\033[31m[backend] error:\033[0m %s\n' "$1" >&2; exit 1; }

# Invoke the venv's uvicorn DIRECTLY (not `uv run uvicorn`): `uv run` stays alive
# as a parent wrapper with the real server as its child, so signaling/killing the
# tracked pid would orphan uvicorn (it keeps holding the port — restarts then fail
# to bind, and graceful shutdown leaks a process). Running the server binary makes
# the supervised pid the actual server.
UVICORN="$REPO_ROOT/.venv/bin/uvicorn"
[ -x "$UVICORN" ] || die "venv server not found at $UVICORN — run \`uv sync\` first."

SHUTTING_DOWN=0
CHILD_PID=""

# SIGINT/SIGTERM -> graceful stop of the child, then exit without restarting.
terminate() {
  SHUTTING_DOWN=1
  note "shutdown signal received — stopping backend gracefully…"
  if [ -n "$CHILD_PID" ] && kill -0 "$CHILD_PID" 2>/dev/null; then
    kill -TERM "$CHILD_PID" 2>/dev/null || true
    local waited=0
    while kill -0 "$CHILD_PID" 2>/dev/null; do
      [ "$waited" -ge "$GRACE_SECONDS" ] && break
      sleep 1
      waited=$((waited + 1))
    done
    if kill -0 "$CHILD_PID" 2>/dev/null; then
      warn "graceful window (${GRACE_SECONDS}s) expired — forcing stop (SIGKILL)."
      kill -KILL "$CHILD_PID" 2>/dev/null || true
    fi
  fi
}
trap terminate INT TERM

# Sliding-window crash timestamps (bash 3.2 indexed array).
CRASH_TS=""

record_crash() {
  local now="$1" kept="" t
  for t in $CRASH_TS; do
    [ $((now - t)) -lt "$CRASH_WINDOW" ] && kept="$kept $t"
  done
  CRASH_TS="$kept $now"
}

crash_count() {
  # shellcheck disable=SC2086
  set -- $CRASH_TS
  echo "$#"
}

backoff=1
note "supervising backend on ${BACKEND_HOST}:${BACKEND_PORT} (Ctrl+C to stop)."

while :; do
  start_ts=$(date +%s)
  ( cd "$REPO_ROOT" && exec "$UVICORN" server.app:app \
      --host "$BACKEND_HOST" --port "$BACKEND_PORT" ) &
  CHILD_PID=$!
  note "started (pid $CHILD_PID)."

  wait "$CHILD_PID"
  exit_code=$?

  # A trapped signal interrupts `wait`; terminate() has already stopped the child.
  if [ "$SHUTTING_DOWN" = "1" ]; then
    note "backend stopped gracefully. Bye."
    exit 0
  fi

  end_ts=$(date +%s)
  ran_for=$((end_ts - start_ts))

  # A run that stayed up longer than the crash window is "healthy" — reset guards.
  if [ "$ran_for" -ge "$CRASH_WINDOW" ]; then
    backoff=1
    CRASH_TS=""
  fi

  record_crash "$end_ts"
  n="$(crash_count)"
  warn "backend exited (code ${exit_code}) after ${ran_for}s — crash ${n}/${MAX_CRASHES} in the last ${CRASH_WINDOW}s."

  if [ "$n" -ge "$MAX_CRASHES" ]; then
    die "backend crashed ${n} times within ${CRASH_WINDOW}s — not restarting (fix the cause, then rerun). Last exit code: ${exit_code}."
  fi

  note "restarting in ${backoff}s…"
  sleep "$backoff"
  # Honor a signal that arrived during the backoff sleep.
  [ "$SHUTTING_DOWN" = "1" ] && { note "shutdown during backoff — not restarting."; exit 0; }

  backoff=$((backoff * 2))
  [ "$backoff" -gt "$BACKOFF_MAX" ] && backoff="$BACKOFF_MAX"
done
