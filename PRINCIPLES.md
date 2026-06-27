# Ethical game design — applying darkpattern.games


## Temporal — *"makes you play longer than you meant to"*
Avoid: daily-reward / login streaks, appointment timers, grinding, can't-pause/save.

- **Disclose the time commitment up front.** `POST /rooms` returns `total_rounds`
  and `round_seconds`; the lobby shows "N rounds × M seconds" before anyone starts.
- **Natural, finite endpoint.** A game is a fixed number of rounds, then it ends with
  a clear `GAME_OVER`. No infinite ladder, no "one more round" pressure.
- **Leave anytime, no penalty.** Disconnecting is handled cleanly; standings persist
  but there is no streak to break, no punishment, nothing lost.
- **No daily rewards / login bonuses / appointment mechanics.** None exist by design.

## Monetary — *"tricks you into spending"*
Avoid: pay-to-win, pay-to-skip, premium currency, lootboxes, bait-and-switch.

- **No monetization at all.** No currency, no purchases, no boosters, no ads. Scoring
  cannot be bought; the only inputs are your prompt and how quickly you submit.

## Social — *"uses your relationships against you"*
Avoid: friend spam, social obligation / guild pressure, fear-of-missing-out.

- **Guest play is first-class.** You never need an account to play; sign-in only adds
  a personal profile + history (opt-in), never gates the game.
- **No friend spam / invites / sharing prompts.** Joining is a short room code shared
  by the players themselves — no contact harvesting, no "invite 3 friends to unlock".
- **No FOMO.** No limited-time events or expiring content.

## Psychological — *"tricks you into bad decisions"*
Avoid: variable/random "slot-machine" rewards, complete-the-collection, aesthetic
manipulation, illusion of control (hidden mechanics).

- **Transparent scoring (counters illusion of control).** Every round reveal shows the
  full breakdown: the LLM judge's holistic similarity, the per-dimension subscores
  (subject / composition / color / mood), the submission-speed bonus, and a written
  rationale explaining *why*. The mechanics are visible, not a black box.
- **Scores are earned, not random.** The judge applies a fixed, published rubric
  (`services/judge.py` → `JUDGE_SYSTEM`) with calibration anchors — not a variable
  reward designed to hook. The speed bonus is a small, disclosed weight (20%) that
  never lets a fast-but-wrong answer beat a slow-but-accurate one.
- **No collection/completion compulsion.** No badges-to-collect, no unlock treadmill.
  The reward is the fun of the round and seeing how close you got.

## Carry-through to the frontend (Workstream C)
- Lobby states the exact round count and per-round time limit before "Start".
- Reveal screen renders the entire score breakdown + rationale (no hidden math).
- A visible, accurate countdown (server-driven) with a calm urgency cue near zero —
  an honest signal, not an anxiety-inducing manipulation.
- Clear "leave game" affordance with no penalty messaging.
- Sign-in is an optional button, never a wall or a nag.
