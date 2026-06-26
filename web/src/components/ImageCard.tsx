import { imageUrl } from "../config";
import type { ResultView } from "../types";

const DIM_LABELS: Record<string, string> = {
  subject: "Subject",
  composition: "Composition",
  color: "Color",
  mood: "Mood",
};

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
  return (
    <div className={`card ${isMe ? "card-me" : ""} ${isWinner ? "card-winner" : ""}`}>
      <div className="card-imgwrap">
        {result.image_id ? (
          <img className="card-img" src={imageUrl(code, result.image_id)} alt={result.prompt} />
        ) : (
          <div className="card-img card-img-missing">no image</div>
        )}
        <div className="card-score">{result.score ?? 0}</div>
        {isWinner && <div className="card-crown" title="Round winner">👑</div>}
      </div>
      <div className="card-body">
        <div className="card-name">
          {result.player_name}
          {isMe && <span className="tag">you</span>}
        </div>
        <div className="card-prompt">“{result.prompt}”</div>

        {(result.similarity != null || result.speed_bonus != null) && (
          <div className="breakdown">
            <span className="chip">match {result.similarity ?? "–"}</span>
            <span className="chip">speed +{result.speed_bonus ?? 0}</span>
          </div>
        )}

        {/* Full per-dimension breakdown + rationale, shown for your own card. */}
        {isMe && result.dimensions && (
          <div className="why">
            <div className="why-dims">
              {Object.entries(result.dimensions).map(([k, v]) => (
                <div className="why-dim" key={k}>
                  <span>{DIM_LABELS[k] ?? k}</span>
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
      </div>
    </div>
  );
}
