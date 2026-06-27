import { beforeEach, describe, expect, it } from "vitest";
import { useGame } from "./store";
import type { PlayerView, ServerMessage } from "./types";

const g = () => useGame.getState();
const player = (over: Partial<PlayerView> = {}): PlayerView => ({
  id: "p1",
  name: "Ann",
  score: 0,
  connected: true,
  is_host: true,
  picture_url: null,
  ...over,
});
const send = (m: ServerMessage) => g().handle(m);

beforeEach(() => g().resetGame());

describe("game store reducer", () => {
  it("welcome sets identity", () => {
    send({ type: "welcome", player_id: "p1", room_code: "ABCD" });
    expect(g().playerId).toBe("p1");
    expect(g().roomCode).toBe("ABCD");
  });

  it("room_state updates roster, phase and totals", () => {
    send({ type: "room_state", phase: "lobby", round_num: 0, total_rounds: 3, players: [player()] });
    expect(g().totalRounds).toBe(3);
    expect(g().players).toHaveLength(1);
  });

  it("phase_changed to prompting clears prior submissions", () => {
    send({ type: "submission_status", submitted_player_ids: ["p1"], total: 2 });
    send({ type: "prompt_accepted" });
    expect(g().mySubmitted).toBe(true);
    send({ type: "phase_changed", phase: "prompting", round_num: 1 });
    expect(g().submittedIds).toEqual([]);
    expect(g().mySubmitted).toBe(false);
  });

  it("timer yields a future local deadline (skew-corrected)", () => {
    const deadline = Math.floor(Date.now() / 1000) + 30;
    send({ type: "timer", seconds_left: 30, deadline_ts: deadline });
    expect(g().deadlineLocalMs).not.toBeNull();
    expect(g().deadlineLocalMs!).toBeGreaterThan(Date.now());
  });

  it("round_reveal accumulates history in order and sets reveal phase", () => {
    const reveal = (n: number): ServerMessage => ({
      type: "round_reveal",
      round_num: n,
      target_image_id: `t${n}`,
      results: [],
      winner_id: null,
      standings: [],
    });
    send(reveal(1));
    send(reveal(2));
    expect(g().roundsHistory.map((r) => r.roundNum)).toEqual([1, 2]);
    expect(g().phase).toBe("reveal");
  });

  it("a duplicate round_reveal (reconnect) replaces, not duplicates", () => {
    const reveal = (n: number): ServerMessage => ({
      type: "round_reveal", round_num: n, target_image_id: `t${n}`,
      results: [], winner_id: null, standings: [],
    });
    send(reveal(1));
    send(reveal(1));
    expect(g().roundsHistory).toHaveLength(1);
  });

  it("starting a new game (round 1 target) clears history", () => {
    send({ type: "round_reveal", round_num: 1, target_image_id: "t", results: [], winner_id: null, standings: [] });
    send({ type: "phase_changed", phase: "generating_target", round_num: 1 });
    expect(g().roundsHistory).toEqual([]);
  });

  it("game_over records standings and winner", () => {
    send({ type: "game_over", standings: [player({ score: 9 })], winner_id: "p1" });
    expect(g().phase).toBe("game_over");
    expect(g().gameOver?.winnerId).toBe("p1");
  });

  it("error surfaces as a toast", () => {
    send({ type: "error", detail: "oops" });
    expect(g().toast).toBe("oops");
  });
});
