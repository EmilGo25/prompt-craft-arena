import { describe, expect, it } from "vitest";
import { buildScorecard } from "./scorecard";
import type { ResultView } from "./types";

function result(
  over: { final?: number; sim?: number; speed?: number; dims?: Record<string, number> } = {},
): ResultView {
  return {
    player_id: "p1",
    player_name: "Ann",
    prompt: "x",
    image_id: "i",
    score: over.final ?? 0,
    similarity: over.sim ?? 0,
    speed_bonus: over.speed ?? 0,
    rationale: "",
    dimensions: over.dims ?? { subject: 0, composition: 0, color: 0, mood: 0 },
  };
}

describe("buildScorecard", () => {
  it("averages final / similarity / speed across rounds", () => {
    const card = buildScorecard([
      result({ final: 80, sim: 80, speed: 100 }),
      result({ final: 60, sim: 40, speed: 0 }),
    ]);
    expect(card.roundsPlayed).toBe(2);
    expect(card.avgFinal).toBe(70);
    expect(card.avgSimilarity).toBe(60);
    expect(card.avgSpeed).toBe(50);
  });

  it("identifies strongest and weakest dimension by average", () => {
    const card = buildScorecard([
      result({ dims: { subject: 90, composition: 80, color: 70, mood: 60 } }),
      result({ dims: { subject: 50, composition: 60, color: 40, mood: 30 } }),
    ]);
    expect(card.best?.key).toBe("subject"); // (90+50)/2 = 70, highest
    expect(card.worst?.key).toBe("mood"); // (60+30)/2 = 45, lowest
  });

  it("ignores rounds the player didn't play", () => {
    const card = buildScorecard([undefined, result({ final: 50 }), undefined]);
    expect(card.roundsPlayed).toBe(1);
    expect(card.avgFinal).toBe(50);
  });

  it("returns an empty card when nothing was submitted", () => {
    const card = buildScorecard([undefined, undefined]);
    expect(card.roundsPlayed).toBe(0);
    expect(card.best).toBeNull();
    expect(card.worst).toBeNull();
  });
});
