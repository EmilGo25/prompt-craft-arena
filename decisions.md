# Decision Log — Prompt-craft Arena

A running record of every design/architecture/product decision, in the order made,
with the reasoning. Newest sections are appended at the bottom.

---

## 1. Game concept
- **What:** A real-time multiplayer game where players compete to write the prompt whose
  generated image lands **closest to a target image**. Closest wins the round.

## 2. Core product decisions (initial Q&A)
| Decision | Choice | Why |
|---|---|---|
| **Modality** | Image-to-image (prompt → image, scored vs a target image) | Most visual/fun; plays to a multimodal judge's strengths |
| **Multiplayer** | Live rooms, real-time, **server-authoritative** | Shared timer + scoring must be tamper-proof; clients only render + submit |
| **Stack** | Python **FastAPI** (WebSockets) backend + **React** frontend | Async real-time fit; one language server-side; React for the live UI |
| **Scoring** | **LLM-as-judge** | Handles nuanced visual similarity better than raw embeddings for a party game |
| **Image generation** | Hosted, behind a **pluggable `ImageGenerator`** interface | The model can't be self-hosted cheaply for a live game; keep it swappable |
| **Targets** | **AI-generated fresh each round** from a seed-prompt pool | Infinite variety; reuses the same image generator |

## 3. Architecture decisions
- **Server-authoritative game loop:** all state, timers, scoring live on the server; one
  `asyncio` task per room drives the phase machine. Prevents client-side cheating.
- **In-memory room store** (`RoomManager.rooms`) for the MVP, behind a manager so a Redis
  swap later doesn't touch game logic.
- **Phase state machine:** `LOBBY → GENERATING_TARGET → PROMPTING → SCORING → REVEAL →
  (loop) → GAME_OVER`.
- **Round resolution trigger:** prompting ends on timer expiry **or** when all connected
  players have submitted (whichever first); non-submitters score 0.
- **Transport-agnostic Room:** the Room talks to `Connection` objects, not FastAPI
  WebSockets directly, so the engine is unit-testable with a fake connection.
- **Typed wire protocol:** every client↔server message is a discriminated Pydantic model
  (`realtime/protocol.py`); invalid messages are rejected, not guessed.
- **Images off the WS frames:** images referenced by `image_id`, fetched over HTTP
  (`GET /rooms/{code}/images/{id}`) to keep frames small.
- **Offline-first defaults:** `IMAGE_PROVIDER=stub` + `JUDGE=random` so the whole game runs
  and is testable with **zero API keys**; real providers are opt-in via env.

## 4. Phase 1 build (engine) — completed
- Implemented rooms/state, protocol, image_gen (Stub), judge (Random), Room loop, manager,
  FastAPI app. **18 tests** (now) pass; a live 2-player, 5-round game verified end-to-end
  (targets generated, prompts scored, reveals broadcast, images served, standings correct).

## 5. Product-design round (functional + non-functional requirements)
| Decision | Choice | Why |
|---|---|---|
| **Auth method** | **Google OAuth** (server-side flow, app issues its own JWT) | No passwords to manage; user's choice |
| **Guest play** | **Allowed**; profile + history only for signed-in users | Lowest friction; a friendly "no login wall" |
| **Database** | **SQLite** via SQLModel/SQLAlchemy (async) | Zero-ops for MVP; same ORM migrates to Postgres later |
| **Time limit** | **Configured per-game at creation** (`POST /rooms {rounds, round_seconds}`, clamped) | Required by product design |
| **Submission indication** | Server broadcasts **per-player submitted IDs** (`SubmissionStatus`) | Frontend shows placeholder tiles when others submit |
| **Clock accuracy** | Server sends `deadline_ts` (epoch); frontend runs an **offset-corrected rAF countdown** | Smooth + drift-free; "running short" turns red |
| **Anti-cheat (paste)** | **Frontend disables paste/drop** on the prompt box | Soft deterrent (documented as not a security boundary) |
| **History images** | **Persist target + result images to disk** at game over | Survive room teardown so history is reviewable |

## 6. Scoring model (new requirement: per-submission score + summary)
- **Per-submission processing:** the moment a player submits, their image is generated and
  judged **immediately** in the background — producing a score + written summary.
- **Not revealed early:** results are withheld until round end (revealing live would let
  late players copy). Only the "submitted" status is broadcast.
- **"Waiting for score" screen:** after all prompts are in, the server enters a `SCORING`
  phase and holds until every image is generated + judged, then reveals.
- **Composite score = LLM similarity (80%) + submission-speed bonus (20%)**, weights sum to 1
  so the final stays 0–100 and **similarity always dominates** (a fast-but-wrong answer can't
  beat a slow-but-accurate one). Speed bonus = `(1 − fraction_of_time_used) × 100`.
- **Per-dimension subscores:** the judge returns subject / composition / color / mood
  subscores + a holistic overall + a one–two sentence rationale, so the "why you scored X"
  summary is concrete. (`services/scoring.py`, `services/judge.py`.)

## 7. LLM-judge prompt design (researched)
- **Structured system prompt** (best practice): role → task → weighted dimensions →
  calibration anchors (0–9 … 90–100) → guardrails → output contract.
- **Guardrails:** judge only similarity to the target (not standalone art quality); weight the
  main subject most; penalize missing/extra major elements; be consistent regardless of order;
  judge the *images*, not the cleverness of the prompt text.
- **Structured outputs** (JSON schema) so verdicts are validated and parseable, not regex'd.

## 8. AI provider — switched to **OpenAI** (user directive)
- **Image generation:** `OpenAIImageGenerator` → OpenAI image API, default **`gpt-image-1`**
  (config: `gpt-image-1.5` / `gpt-image-2` available; `OPENAI_IMAGE_SIZE` default 1024²).
- **LLM judge:** `OpenAIJudge` → Chat Completions with **`gpt-4o`** (vision + `response_format:
  json_schema` structured outputs). Model configurable via `JUDGE_MODEL`.
- **Fairness note:** target and player images use the **same model** so similarity isn't
  unfairly penalized for generator-style differences.
- Replaced the earlier Claude/fal wiring; dropped the `anthropic` dependency, added `openai`.
  Stub/Random remain for offline dev + tests.

## 9. Player-friendly design (user directive)
- Adopted a set of player-first design principles, documented in `PRINCIPLES.md`.
- **Commitments:** respect players' time (round count + time limit shown up front; finite
  games with a clear end; leave anytime with no penalty); free and open (no monetization,
  no ads — scoring can't be bought); friendly and social (guest-first, short room code,
  optional sign-in); transparent scoring (full breakdown + published rubric; each player's
  reasoning is private to them); healthy competition (leaderboard ranks by average score).
- These shape the frontend: disclose round count + time limit up front; reveal the full score
  breakdown + rationale; clear countdown; optional (never walled) sign-in.

---

## 10. Single image model for both (user directive)
- **Decided:** use **one image model for both** the target and player images (not a
  higher-quality model for targets). Reasons: fairest scoring (same style space), simpler,
  lower latency on the "waiting for score" screen.

## 11. Build order (user directive)
- Build the **React frontend (Workstream C) next**, before the auth/history layer
  (Workstream B). The frontend is guest-only for now; sign-in/history hooks added with B.

---

## Open / pending (not yet built)
- Workstream B (SQLite + Google auth + history) — planned, not yet built.
- See `~/.claude/plans/parsed-whistling-elephant.md`.
