import type { ResultView } from "./types";

export const DIMENSIONS = ["subject", "composition", "color", "mood"] as const;

export interface Scorecard {
  roundsPlayed: number;
  avgFinal: number;
  avgSimilarity: number;
  avgSpeed: number;
  dims: Record<string, number>; // average per dimension
  best: { key: string; value: number } | null;
  worst: { key: string; value: number } | null;
}

function mean(xs: number[]): number {
  return xs.length ? Math.round(xs.reduce((a, b) => a + b, 0) / xs.length) : 0;
}

/** Aggregate one player's results across every round into a scorecard.
 * Localized summary text is composed in the component from this data. */
export function buildScorecard(myResults: (ResultView | undefined)[]): Scorecard {
  const mine = myResults.filter((r): r is ResultView => !!r);

  const dims: Record<string, number> = {};
  for (const d of DIMENSIONS) dims[d] = mean(mine.map((r) => r.dimensions?.[d] ?? 0));

  if (mine.length === 0) {
    return {
      roundsPlayed: 0,
      avgFinal: 0,
      avgSimilarity: 0,
      avgSpeed: 0,
      dims,
      best: null,
      worst: null,
    };
  }

  const ranked = [...DIMENSIONS].sort((a, b) => dims[b] - dims[a]);
  return {
    roundsPlayed: mine.length,
    avgFinal: mean(mine.map((r) => r.score ?? 0)),
    avgSimilarity: mean(mine.map((r) => r.similarity ?? 0)),
    avgSpeed: mean(mine.map((r) => r.speed_bonus ?? 0)),
    dims,
    best: { key: ranked[0], value: dims[ranked[0]] },
    worst: { key: ranked[ranked.length - 1], value: dims[ranked[ranked.length - 1]] },
  };
}
