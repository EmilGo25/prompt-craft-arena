import { imageUrl } from "../config";
import { PromptInput } from "../components/PromptInput";
import { Timer } from "../components/Timer";
import { useGame } from "../store";
import { useTranslation } from "../i18n";

export function Prompting() {
  const { t, lang } = useTranslation();
  const {
    phase,
    roomCode,
    roundNum,
    totalRounds,
    targetImageId,
    deadlineLocalMs,
    players,
    submittedIds,
    mySubmitted,
    playerId,
    send,
  } = useGame();

  const preparing = phase === "generating_target" || !targetImageId;

  if (preparing) {
    return (
      <div className="screen prompting">
        <div className="round-banner">
          {t("round.roundOf", { n: roundNum, total: totalRounds })}
        </div>
        <div className="prepare">
          <div className="spinner" />
          <p>{t("round.generatingTarget")}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="screen prompting">
      <div className="round-banner">
        <span>{t("round.roundOf", { n: roundNum, total: totalRounds })}</span>
        <Timer deadlineLocalMs={deadlineLocalMs} />
      </div>

      <div className="prompting-grid">
        <div className="target-panel">
          <h3>{t("prompting.recreate")}</h3>
          <img
            className="target-img"
            src={imageUrl(roomCode!, targetImageId!)}
            alt={t("prompting.recreate")}
          />
        </div>

        <div className="play-panel">
          <PromptInput
            disabled={false}
            submitted={mySubmitted}
            onSubmit={(prompt) => send({ type: "submit_prompt", prompt, lang })}
          />

          <div className="submitted-strip">
            <span className="muted">
              {t("prompting.submittedCount", { n: submittedIds.length, total: players.length })}
            </span>
            <div className="tiles">
              {players.map((p) => {
                const done = submittedIds.includes(p.id);
                return (
                  <div
                    key={p.id}
                    className={`tile ${done ? "tile-done" : "tile-waiting"}`}
                    title={
                      done
                        ? t("prompting.tileSubmitted", { name: p.name })
                        : t("prompting.tileWriting", { name: p.name })
                    }
                  >
                    <span className="tile-mark">{done ? "✓" : "…"}</span>
                    <span className="tile-name">
                      {p.name}
                      {p.id === playerId && ` ${t("prompting.you")}`}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
