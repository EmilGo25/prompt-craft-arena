# Design Principles

Prompt-craft Arena is built to be **fair, fun, and respectful of players' time**.
These are the commitments that shape the product.

## Respect your time
- **The time commitment is clear up front.** `POST /rooms` returns `total_rounds`
  and `round_seconds`; the lobby shows the round count before anyone starts.
- **Games are finite with a clear end.** A game is a fixed number of rounds, then a
  clean `GAME_OVER` and final standings.
- **Leave any time, no penalty.** Disconnecting is handled gracefully; standings
  persist and nothing is lost.

## Free and open
- **No monetization.** No currency, purchases, boosters, or ads. Scoring depends only
  on your prompt and how quickly you submit — it can't be bought.

## Friendly and social
- **Guest play is first-class.** You never need an account to play; signing in only
  adds a personal profile + history.
- **Easy to play with friends.** Joining is a short room code the players share
  themselves — no contact harvesting, no required invites.

## Transparent scoring
- **You see how every score is made.** Each round reveal shows the full breakdown:
  the judge's holistic similarity, the per-dimension subscores (subject / composition
  / color / mood), the submission-speed bonus, and a written rationale explaining why.
- **Scores are earned from a published rubric**, not chance. The judge applies a fixed,
  documented rubric (`services/judge.py` → `JUDGE_SYSTEM`) with clear calibration
  anchors. The speed bonus is a small, disclosed 20% weight that never lets a fast but
  inaccurate answer beat a slow, accurate one.
- **Your breakdown is private to you.** Each player sees the reasoning behind their own
  score; others see only the shared images and final scores.

## Healthy competition
- **A global leaderboard ranks by average score**, so improvement — not grinding — is
  what climbs the board. Top finishers earn gold, silver, and bronze.

## In the frontend
- The lobby states the exact round count and per-round time limit before "Start".
- The reveal screen renders the full score breakdown + rationale — no hidden math.
- A visible, accurate countdown gives a clear, calm cue as time runs low.
- A clear "leave game" option is always available.
- Sign-in is an optional button, never a wall.
