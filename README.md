# Prompt-craft Arena

<p align="center">
  <img src="web/public/brand/logo.png" alt="Prompt-craft Arena" width="460" />
</p>

A real-time multiplayer game where players compete to write the best prompt. Each
round shows a **target image**; players write a prompt; an image model generates an
image from each prompt; and **an AI judge** scores which result lands closest to the
target. Closest wins the round.

- **Backend:** FastAPI + WebSockets (server-authoritative game loop)
- **Image generation:** pluggable — `stub` (offline, no keys), `openai` (`gpt-image-1`),
  or `drawthings` (local open-weight FLUX.1 / SDXL via a Draw Things / A1111 server)
- **Judge:** `random` (offline), `openai` (`gpt-4o`, vision + structured outputs),
  or `ollama` (local open-weight vision model, e.g. `qwen2.5vl`);
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

## Play with remote friends (free)

The game (and, with the local providers, the AI models) runs on your machine — so to
let friends join over the internet you expose this machine with a tunnel. One command
does it, using two free [Cloudflare](https://github.com/cloudflare/cloudflared) quick
tunnels:

```bash
brew install cloudflared      # once
./scripts/share.sh            # prints a public URL to share; Ctrl+C tears it all down
```

It starts the backend, builds the frontend against the public backend URL, serves it,
opens a tunnel for each, and prints the one link to share. Keep the terminal open and
your Mac awake (`caffeinate`). Ports are overridable via `BACKEND_PORT` / `FRONTEND_PORT`.

## Enable real generation + OpenAI judge

Copy `.env.example` to `.env` and set:

```
OPENAI_API_KEY=...
IMAGE_PROVIDER=openai      # gpt-image-1
JUDGE=openai               # gpt-4o, vision + structured outputs
```

## Run fully local (open-weight models, no keys)

Both workloads can run on-device with open-weight models — no API keys, nothing
leaves the machine. Tuned for Apple Silicon (e.g. an M4 / 24 GB Mac).

**Judge — Ollama + a vision model:**

```bash
brew install ollama && ollama serve     # in one terminal
ollama pull qwen2.5vl:7b                 # ~6 GB; or qwen2.5vl:32b for more accuracy
```

**Image generation — Draw Things (or any A1111-compatible WebUI):**

Install [Draw Things](https://drawthings.ai), load an open-weight model
(**FLUX.1-schnell** is the best speed/quality balance for live rounds; SDXL-Turbo
is faster, FLUX.1-dev is higher quality but ~50 s/image), and enable its HTTP API
server (defaults to `http://localhost:7860`). AUTOMATIC1111 / Forge / SD.Next work
too — they share the `/sdapi/v1/txt2img` API.

Then in `.env`:

```
IMAGE_PROVIDER=drawthings   # local FLUX.1 / SDXL
DRAWTHINGS_STEPS=4          # low steps suit schnell / turbo models
JUDGE=ollama                # local qwen2.5vl
OLLAMA_JUDGE_MODEL=qwen2.5vl:7b
```

> **Note on a single Mac:** there's one GPU, so per-player generations *serialize*
> rather than run in parallel. Favor fast step counts (schnell/turbo) and consider
> the objective pool (`OBJECTIVE_POOL_ENABLED=true`) to pre-generate target images
> off the request path. With 24 GB, run the image model and the judge sequentially
> rather than expecting both resident at once.

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
