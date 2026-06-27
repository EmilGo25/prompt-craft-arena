# Prompt-craft Arena

<p align="center">
  <img src="web/public/brand/logo.png" alt="Prompt-craft Arena" width="460" />
</p>

A real-time multiplayer game where players compete to write the best prompt. Each
round shows a **target image**; players write a prompt; an image model generates an
image from each prompt; and **an AI judge** scores which result lands closest to the
target. Closest wins the round.

- **Backend:** FastAPI + WebSockets (server-authoritative game loop)
- **Image generation:** pluggable — `stub` (offline, no keys) or `openai` (`gpt-image-1`)
- **Judge:** `random` (offline) or `openai` (,`gpt-4o`, vision + structured outputs);
  per-submission composite score = LLM similarity + submission-speed bonus
- **Frontend:** React + Vite + TypeScript (`web/`) — full game UI, player-friendly
  design (see `PRINCIPLES.md`)

## Status

**Playable end-to-end** with the stub image generator + random judge — no API keys.
Backend game engine + React client are built and verified. Still to come:
authentication + profiles + saved game history (Workstream B). See the plan in
`~/.claude/plans/parsed-whistling-elephant.md` and the full decision log in
`decisions.md`.

## Run it (offline, no keys)

Backend:

```bash
uv sync
uv run uvicorn server.app:app --port 8000
```

Frontend (in another terminal):

```bash
cd web
npm install
npm run dev          # http://localhost:5173
```

Open the web app, pick a name, **Create game** (set rounds + seconds), and share the
4-letter code. The host starts; everyone writes prompts against the target image.
Set `VITE_API_BASE` if the backend isn't on `http://localhost:8000`.

## Enable real generation + OpenAI judge

Copy `.env.example` to `.env` and set:

```
OPENAI_API_KEY=...
IMAGE_PROVIDER=openai      # gpt-image-1
JUDGE=openai               # gpt-4o, vision + structured outputs
```

## Tests

Three layers:

```bash
# Backend — unit + API/WebSocket integration (37 tests, no keys needed)
uv run pytest

# Frontend — unit (store, scorecard, i18n, components) via Vitest
cd web && npm run test

# End-to-end + mobile visual/overflow across device profiles (Playwright)
cd web && npx playwright install chromium   # once
cd web && npm run test:e2e
```

- **Backend** (`server/tests/`): state machine, wire protocol, composite scoring,
  target-prompt difficulty, leaderboard, and full HTTP/WebSocket games to `GAME_OVER`
  via `TestClient` — all on the offline stub generator + random judge.
- **Frontend unit** (`web/src/**/*.test.*`): the store reducer, scorecard aggregation,
  i18n (incl. a check that Hebrew defines every English key), and the Leaderboard.
- **E2E + mobile** (`web/e2e/`): a real single-player game from home to game over, plus
  **no-horizontal-overflow** assertions, touch-target sizing, and screenshots on iPhone
  SE / 12 / 14 Pro Max, Galaxy S9+, Pixel 5, and desktop. Spins up an isolated stub
  stack on test ports (8123/5180), so it won't touch your dev servers.

## Layout

```
server/
  app.py              FastAPI: REST + WebSocket + image serving
  config.py           Settings (env / .env)
  rooms/
    manager.py        Create / look up / reap rooms
    room.py           Per-room async round loop (the game engine)
    state.py          Phase machine + data model + pure scoring
  realtime/
    protocol.py       Typed client<->server messages
    connection.py     Transport-agnostic connection wrapper
  services/
    image_gen.py      ImageGenerator: Stub + OpenAI (gpt-image-1)
    judge.py          Judge: Random + OpenAI (gpt-4o)
    scoring.py        Composite score: LLM similarity + speed bonus
    seed_prompts.py   Seed pool for per-round AI targets
  tests/
```
