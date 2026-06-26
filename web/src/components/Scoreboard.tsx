import type { PlayerView } from "../types";

export function Scoreboard({
  players,
  meId,
  winnerId,
}: {
  players: PlayerView[];
  meId: string | null;
  winnerId?: string | null;
}) {
  return (
    <ol className="scoreboard">
      {players.map((p, i) => (
        <li
          key={p.id}
          className={`score-row ${p.id === meId ? "is-me" : ""} ${
            p.id === winnerId ? "is-winner" : ""
          }`}
        >
          <span className="score-rank">{i + 1}</span>
          <span className="score-name">
            {p.name}
            {p.id === meId && <span className="tag">you</span>}
            {p.is_host && <span className="tag tag-host">host</span>}
            {!p.connected && <span className="tag tag-off">left</span>}
          </span>
          <span className="score-points">{p.score}</span>
        </li>
      ))}
    </ol>
  );
}
