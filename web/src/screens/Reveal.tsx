import { imageUrl } from "../config";
import { ImageCard } from "../components/ImageCard";
import { Scoreboard } from "../components/Scoreboard";
import { useGame } from "../store";
import { useTranslation } from "../i18n";

export function Reveal() {
  const { t } = useTranslation();
  const { reveal, roomCode, playerId, roundNum, totalRounds } = useGame();
  if (!reveal || !roomCode) return null;

  const winner = reveal.results.find((r) => r.player_id === reveal.winnerId);

  return (
    <div className="screen reveal">
      <div className="round-banner">
        <span>{t("reveal.resultsTitle", { n: roundNum, total: totalRounds })}</span>
      </div>

      <div className="reveal-top">
        <div className="reveal-target">
          <h3>{t("reveal.target")}</h3>
          <img
            className="target-img"
            src={imageUrl(roomCode, reveal.targetImageId)}
            alt={t("reveal.target")}
          />
          {winner && (
            <p className="winner-line">
              👑{" "}
              {t("reveal.wonRound", {
                name: winner.player_name,
                score: winner.score ?? 0,
              })}
            </p>
          )}
        </div>
        <div className="reveal-standings">
          <h3>{t("reveal.standings")}</h3>
          <Scoreboard players={reveal.standings} meId={playerId} winnerId={reveal.winnerId} />
        </div>
      </div>

      <h3 className="reveal-h">{t("reveal.everyoneResults")}</h3>
      <div className="cards">
        {reveal.results.map((r) => (
          <ImageCard
            key={r.player_id}
            code={roomCode}
            result={r}
            isMe={r.player_id === playerId}
            isWinner={r.player_id === reveal.winnerId}
          />
        ))}
      </div>

      <p className="muted reveal-next">{t("reveal.nextRound")}</p>
    </div>
  );
}
