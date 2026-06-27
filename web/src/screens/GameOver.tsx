import { imageUrl } from "../config";
import { Scoreboard } from "../components/Scoreboard";
import { ImageCard } from "../components/ImageCard";
import { buildScorecard, DIMENSIONS } from "../scorecard";
import { useGame } from "../store";
import { useTranslation } from "../i18n";

export function GameOver({ onLeave }: { onLeave: () => void }) {
  const { t } = useTranslation();
  const { gameOver, players, playerId, roomCode, roundsHistory, send } = useGame();
  if (!gameOver) return null;

  const winner = gameOver.standings.find((p) => p.id === gameOver.winnerId);
  const me = players.find((p) => p.id === playerId);
  const isHost = me?.is_host ?? false;

  // My results across every round → aggregate scorecard + localized summary.
  const myResults = roundsHistory.map((r) => r.results.find((res) => res.player_id === playerId));
  const card = buildScorecard(myResults);

  let summary: string;
  if (card.roundsPlayed === 0 || !card.best || !card.worst) {
    summary = t("scorecard.none");
  } else {
    const speed =
      card.avgSpeed >= 60
        ? t("scorecard.speedHigh")
        : card.avgSpeed <= 30
          ? t("scorecard.speedLow")
          : "";
    summary =
      t("scorecard.main", {
        n: card.roundsPlayed,
        avg: card.avgFinal,
        best: t(`dims.${card.best.key}`),
        bestVal: card.best.value,
        worst: t(`dims.${card.worst.key}`),
        worstVal: card.worst.value,
      }) + speed;
  }

  return (
    <div className="screen gameover">
      <div className="card-panel center">
        <h1>{t("gameover.title")}</h1>
        {winner && (
          <p className="winner-big">
            👑{" "}
            {winner.id === playerId
              ? t("gameover.winsYou", { name: winner.name })
              : t("gameover.wins", { name: winner.name })}
          </p>
        )}
        <Scoreboard players={gameOver.standings} meId={playerId} winnerId={gameOver.winnerId} />
        <div className="lobby-actions center">
          <button className="btn btn-ghost" onClick={onLeave}>
            {t("common.leave")}
          </button>
          {isHost && (
            <button className="btn btn-primary" onClick={() => send({ type: "play_again" })}>
              {t("gameover.playAgain")}
            </button>
          )}
        </div>
      </div>

      {/* Your scorecard: the exact criteria the score was based on + a summary. */}
      <div className="card-panel">
        <h2>{t("gameover.scorecard")}</h2>
        <p className="muted scorecard-summary">{summary}</p>

        <div className="scorecard-grid">
          {DIMENSIONS.map((d) => (
            <div className="why-dim" key={d}>
              <span>{t(`dims.${d}`)}</span>
              <span className="why-dim-bar">
                <span style={{ width: `${card.dims[d]}%` }} />
              </span>
              <span className="why-dim-val">{card.dims[d]}</span>
            </div>
          ))}
        </div>

        <div className="criteria-row">
          <Criterion
            label={t("gameover.visualSimilarity")}
            value={card.avgSimilarity}
            hint={t("gameover.hintJudge")}
          />
          <Criterion
            label={t("gameover.speedBonus")}
            value={card.avgSpeed}
            hint={t("gameover.hintSpeed")}
          />
          <Criterion
            label={t("gameover.finalScore")}
            value={card.avgFinal}
            hint={t("gameover.hintFinal")}
          />
        </div>
        <p className="muted criteria-note">{t("gameover.weighting")}</p>
      </div>

      {/* Round-by-round recap so everyone can compare images and judge fairness. */}
      {roomCode && roundsHistory.length > 0 && (
        <div className="card-panel">
          <h2>{t("gameover.recap")}</h2>
          <p className="muted">{t("gameover.recapDesc")}</p>
          {roundsHistory.map((r) => (
            <div className="recap-round" key={r.roundNum}>
              <div className="recap-target">
                <h4>{t("gameover.roundTarget", { n: r.roundNum })}</h4>
                <img
                  className="target-img"
                  src={imageUrl(roomCode, r.targetImageId)}
                  alt={`Round ${r.roundNum} target`}
                />
              </div>
              <div className="recap-cards">
                {r.results.map((res) => (
                  <ImageCard
                    key={res.player_id}
                    code={roomCode}
                    result={res}
                    isMe={res.player_id === playerId}
                    isWinner={res.player_id === r.winnerId}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function Criterion({ label, value, hint }: { label: string; value: number; hint: string }) {
  return (
    <div className="criterion">
      <div className="criterion-val">{value}</div>
      <div className="criterion-label">{label}</div>
      <div className="criterion-hint muted">{hint}</div>
    </div>
  );
}
