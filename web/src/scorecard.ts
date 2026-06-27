import type { ResultView } from "./types";

export const DIMENSIONS = ["subject", "composition", "color", "mood"] as const;
export const DIM_LABELS: Record<string, string> = {
  subject: "Subject",
  composition: "Composition",
  color: "Color",
  mood: "Mood",
};

export interface Scorecard {
  roundsPlayed: number;
  avgFinal: number;
  avgSimilarity: number;
  avgSpeed: number;
  dims: Record<string, number>; // average per dimension
  best: { key: string; value: number } | null;
  worst: { key: string; value: number } | null;
  summary: string;
}

function mean(xs: number[]): number {
  return xs.length ? Math.round(xs.reduce((a, b) => a + b, 0) / xs.length) : 0;
}

/** Aggregate one player's results across every round into a scorecard. */
export function buildScorecard(myResults: (ResultView | undefined)[]): Scorecard {
  const mine = myResults.filter((r): r is ResultView => !!r);

  if (mine.length === 0) {
    return {
      roundsPlayed: 0,
      avgFinal: 0,
      avgSimilarity: 0,
      avgSpeed: 0,
      dims: Object.fromEntries(DIMENSIONS.map((d) => [d, 0])),
      best: null,
      worst: null,
      summary: "You didn't submit a prompt this game — jump in next round!",
    };
  }

  const avgFinal = mean(mine.map((r) => r.score ?? 0));
  const avgSimilarity = mean(mine.map((r) => r.similarity ?? 0));
  const avgSpeed = mean(mine.map((r) => r.speed_bonus ?? 0));

  const dims: Record<string, number> = {};
  for (const d of DIMENSIONS) {
    dims[d] = mean(mine.map((r) => r.dimensions?.[d] ?? 0));
  }
  const ranked = [...DIMENSIONS].sort((a, b) => dims[b] - dims[a]);
  const best = { key: ranked[0], value: dims[ranked[0]] };
  const worst = { key: ranked[ranked.length - 1], value: dims[ranked[ranked.length - 1]] };

  let speedNote = "";
  if (avgSpeed >= 60) speedNote = " Submitting early earned you solid speed bonuses.";
  else if (avgSpeed <= 30) speedNote = " You could climb the board by submitting a bit earlier.";

  const summary =
    `Over ${mine.length} ${mine.length === 1 ? "round" : "rounds"} you averaged ` +
    `${avgFinal}/100. Your prompts matched the target best on ` +
    `${DIM_LABELS[best.key].toLowerCase()} (${best.value}) and weakest on ` +
    `${DIM_LABELS[worst.key].toLowerCase()} (${worst.value}).${speedNote}`;

  return { roundsPlayed: mine.length, avgFinal, avgSimilarity, avgSpeed, dims, best, worst, summary };
}
