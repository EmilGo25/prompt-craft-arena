import { useGame } from "../store";
import { useTranslation } from "../i18n";

export function Lobby({ onLeave }: { onLeave: () => void }) {
  const { t } = useTranslation();
  const { roomCode, players, playerId, totalRounds, send } = useGame();
  const me = players.find((p) => p.id === playerId);
  const isHost = me?.is_host ?? false;

  return (
    <div className="screen lobby">
      <div className="card-panel">
        <div className="lobby-head">
          <div>
            <h2>{t("lobby.title")}</h2>
            <p className="muted">{t("lobby.share")}</p>
          </div>
          <div className="roomcode">{roomCode}</div>
        </div>

        <p className="lobby-config">{t("lobby.config", { n: totalRounds })}</p>

        <ul className="player-list">
          {players.map((p) => (
            <li key={p.id} className="player-list-item">
              <span className="dot" />
              {p.name}
              {p.id === playerId && <span className="tag">{t("common.you")}</span>}
              {p.is_host && <span className="tag tag-host">{t("common.host")}</span>}
            </li>
          ))}
        </ul>

        <div className="lobby-actions">
          <button className="btn btn-ghost" onClick={onLeave}>
            {t("common.leave")}
          </button>
          {isHost ? (
            <button
              className="btn btn-primary"
              disabled={players.length < 1}
              onClick={() => send({ type: "start_game" })}
            >
              {t("lobby.startBtn")}
            </button>
          ) : (
            <span className="muted">{t("lobby.waitingHost")}</span>
          )}
        </div>
      </div>
    </div>
  );
}
