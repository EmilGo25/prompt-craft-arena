import { useGame } from "../store";

export function Lobby({ onLeave }: { onLeave: () => void }) {
  const { roomCode, players, playerId, totalRounds, send } = useGame();
  const me = players.find((p) => p.id === playerId);
  const isHost = me?.is_host ?? false;

  return (
    <div className="screen lobby">
      <div className="card-panel">
        <div className="lobby-head">
          <div>
            <h2>Lobby</h2>
            <p className="muted">Share this code so friends can join:</p>
          </div>
          <div className="roomcode">{roomCode}</div>
        </div>

        <p className="lobby-config">
          This game is <strong>{totalRounds}</strong>{" "}
          {totalRounds === 1 ? "round" : "rounds"}. You can leave any time.
        </p>

        <ul className="player-list">
          {players.map((p) => (
            <li key={p.id} className="player-list-item">
              <span className="dot" />
              {p.name}
              {p.id === playerId && <span className="tag">you</span>}
              {p.is_host && <span className="tag tag-host">host</span>}
            </li>
          ))}
        </ul>

        <div className="lobby-actions">
          <button className="btn btn-ghost" onClick={onLeave}>
            Leave
          </button>
          {isHost ? (
            <button
              className="btn btn-primary"
              disabled={players.length < 1}
              onClick={() => send({ type: "start_game" })}
            >
              Start game
            </button>
          ) : (
            <span className="muted">Waiting for the host to start…</span>
          )}
        </div>
      </div>
    </div>
  );
}
