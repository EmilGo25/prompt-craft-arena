# CLAUDE.md

Guidance for Claude Code (and humans) working in this repo. Read this first; it's
loaded automatically at the start of a session.

## What this is

**Prompt-craft Arena** — a real-time multiplayer game. Each round shows a target
image; players write a prompt; an image model renders each prompt; an AI judge
scores which result is closest to the target. Backend = FastAPI + WebSockets
(server-authoritative game loop). Frontend = React + Vite + TS in `web/`.

## Where things live

- `server/app.py` — FastAPI: REST + WebSocket + image serving
- `server/config.py` — all settings (env / `.env`), pydantic
- `server/rooms/` — `manager.py` (create/reap rooms), `room.py` (round loop), `state.py` (phase machine + pure scoring)
- `server/services/image_gen.py` — pluggable `ImageGenerator`: stub / openai / drawthings
- `server/services/judge.py` — pluggable `Judge`: random / openai / ollama
- `server/services/scoring.py` — composite score = LLM similarity + speed bonus
- `web/` — React client (see `PRINCIPLES.md` for the player-first design rules)

## AI providers (pluggable — this is a key design point)

Two external AI workloads, each behind a Protocol with offline + hosted + local options:

| Workload | Offline | Hosted (OpenAI) | Local open-weight |
|---|---|---|---|
| Image gen | `stub` | `openai` (gpt-image-1) | `drawthings` (FLUX.1/SDXL via A1111 API) |
| Judge | `random` | `openai` (gpt-4o) | `ollama` (qwen2.5vl) |

- The offline `stub`/`random` paths need **no API keys** and are what the tests use.
- Local providers run fully on-device — see the "Run fully local" section in `README.md`.
- When adding a provider, extend the `build_*` factory + `config.py` Literal, and keep
  the existing paths untouched. Reuse the OpenAI SDK with a `base_url` for OpenAI-compatible
  local servers rather than adding a second client.

## Conventions

- Python ≥ 3.13, managed with **uv**. Run the app: `uv run uvicorn server.app:app --port 8000`.
- Tests are the contract — keep them green and offline (no network/keys):
  - Backend: `uv run pytest` (currently 48 tests)
  - Frontend unit: `cd web && npm run test`
  - E2E/mobile: `cd web && npm run test:e2e`
- Per-prompt/per-call failures are isolated and degrade gracefully (a bad prompt or an
  unreachable judge must never crash a round). Follow that pattern in new provider code.

## Decision log

`decisions.md` is the running "why" log (numbered sections). **Append a new section there**
when you make a non-obvious or user-directed decision — don't just leave it in chat, since
chat history does not persist across sessions. `PRINCIPLES.md` holds the player-first design
commitments.

## Active branches

- `open-source-models` — local open-weight providers (Draw Things image gen + Ollama judge).
  See decisions.md §12.
