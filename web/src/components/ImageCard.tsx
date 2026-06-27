import { imageUrl } from "../config";
import { useTranslation } from "../i18n";
import type { ResultView } from "../types";

/**
 * One player's result on the reveal screen: their image, final score, and —
 * expanded for the signed-in player — the full transparent breakdown
 * (similarity, speed bonus, per-dimension subscores, and the judge's rationale).
 * Transparency is deliberate (see PRINCIPLES.md).
 */
export function ImageCard({
  code,
  result,
  isMe,
  isWinner,
}: {
  code: string;
  result: ResultView;
  isMe: boolean;
  isWinner: boolean;
}) {
  const { t } = useTranslation();
  return (
    <div className={`card ${isMe ? "card-me" : ""} ${isWinner ? "card-winner" : ""}`}>
      <div className="card-imgwrap">
        {result.image_id ? (
          <img className="card-img" src={imageUrl(code, result.image_id)} alt={result.prompt} />
        ) : (
          <div className="card-img card-img-missing">{t("card.noImage")}</div>
        )}
        <div className="card-score">{result.score ?? 0}</div>
        {isWinner && <div className="card-crown">👑</div>}
      </div>
      <div className="card-body">
        <div className="card-name">
          {result.player_name}
          {isMe && <span className="tag">{t("common.you")}</span>}
        </div>
        <div className="card-prompt">“{result.prompt}”</div>

        {/* The scoring breakdown (similarity, speed, per-dimension subscores, and
            the judge's rationale) is private — shown only on your own card.
            Everyone else sees just the image, prompt, and final score. */}
        {isMe && (
          <>
            {(result.similarity != null || result.speed_bonus != null) && (
              <div className="breakdown">
                <span className="chip">{t("card.match", { n: result.similarity ?? "–" })}</span>
                <span className="chip">{t("card.speed", { n: result.speed_bonus ?? 0 })}</span>
              </div>
            )}
            {result.dimensions && (
              <div className="why">
                <div className="why-dims">
                  {Object.entries(result.dimensions).map(([k, v]) => (
                    <div className="why-dim" key={k}>
                      <span>{t(`dims.${k}`)}</span>
                      <span className="why-dim-bar">
                        <span style={{ width: `${v}%` }} />
                      </span>
                      <span className="why-dim-val">{v}</span>
                    </div>
                  ))}
                </div>
                {result.rationale && <p className="why-text">{result.rationale}</p>}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
