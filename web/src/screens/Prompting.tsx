import { imageUrl } from "../config";
import { PromptInput } from "../components/PromptInput";
import { Timer } from "../components/Timer";
import { useGame } from "../store";

export function Prompting() {
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
          Round {roundNum} of {totalRounds}
        </div>
        <div className="prepare">
          <div className="spinner" />
          <p>Generating this round's target image…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="screen prompting">
      <div className="round-banner">
        <span>
          Round {roundNum} of {totalRounds}
        </span>
        <Timer deadlineLocalMs={deadlineLocalMs} />
      </div>

      <div className="prompting-grid">
        <div className="target-panel">
          <h3>Recreate this</h3>
          <img
            className="target-img"
            src={imageUrl(roomCode!, targetImageId!)}
            alt="Target to recreate"
          />
        </div>

        <div className="play-panel">
          <PromptInput
            disabled={false}
            submitted={mySubmitted}
            onSubmit={(prompt) => send({ type: "submit_prompt", prompt })}
          />

          <div className="submitted-strip">
            <span className="muted">
              Submitted {submittedIds.length}/{players.length}
            </span>
            <div className="tiles">
              {players.map((p) => {
                const done = submittedIds.includes(p.id);
                return (
                  <div
                    key={p.id}
                    className={`tile ${done ? "tile-done" : "tile-waiting"}`}
                    title={done ? `${p.name} submitted` : `${p.name} is still writing`}
                  >
                    <span className="tile-mark">{done ? "✓" : "…"}</span>
                    <span className="tile-name">
                      {p.name}
                      {p.id === playerId && " (you)"}
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
