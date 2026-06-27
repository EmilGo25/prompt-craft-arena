import type { PlayerView } from "../types";
import { useTranslation } from "../i18n";

export function Scoreboard({
  players,
  meId,
  winnerId,
}: {
  players: PlayerView[];
  meId: string | null;
  winnerId?: string | null;
}) {
  const { t } = useTranslation();
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
            {p.id === meId && <span className="tag">{t("common.you")}</span>}
            {p.is_host && <span className="tag tag-host">{t("common.host")}</span>}
            {!p.connected && <span className="tag tag-off">{t("common.left")}</span>}
          </span>
          <span className="score-points">{p.score}</span>
        </li>
      ))}
    </ol>
  );
}
