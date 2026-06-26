# Prompt-craft Arena

A real-time multiplayer game where players compete to write the best prompt. Each
round shows a **target image**; players write a prompt; an image model generates an
image from each prompt; and **Claude judges** which result lands closest to the
target. Closest wins the round.

- **Backend:** FastAPI + WebSockets (server-authoritative game loop)
- **Image generation:** pluggable — `stub` (offline, no keys) or `openai` (`gpt-image-1`)
- **Judge:** `random` (offline) or `openai` (`gpt-4o`, vision + structured outputs);
  per-submission composite score = LLM similarity + submission-speed bonus
- **Frontend:** React + Vite + TypeScript (`web/`) — full game UI, ethical design
  (see `PRINCIPLES.md`)

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

```bash
uv run pytest
```

Covers the state machine, the wire protocol, the Claude/stub judge, and a full
two-player game driven to `GAME_OVER`.

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
