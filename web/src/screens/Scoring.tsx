import { useGame } from "../store";

export function Scoring() {
  const { roundNum, totalRounds } = useGame();
  return (
    <div className="screen scoring">
      <div className="round-banner">
        Round {roundNum} of {totalRounds}
      </div>
      <div className="prepare">
        <div className="spinner" />
        <h3>Waiting for scores…</h3>
        <p className="muted">
          All prompts are in. Generating each player's image and judging how close
          it is to the target.
        </p>
      </div>
    </div>
  );
}
