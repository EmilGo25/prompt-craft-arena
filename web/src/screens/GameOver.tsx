import { Scoreboard } from "../components/Scoreboard";
import { useGame } from "../store";

export function GameOver({ onLeave }: { onLeave: () => void }) {
  const { gameOver, players, playerId, send } = useGame();
  if (!gameOver) return null;
  const winner = gameOver.standings.find((p) => p.id === gameOver.winnerId);
  const me = players.find((p) => p.id === playerId);
  const isHost = me?.is_host ?? false;

  return (
    <div className="screen gameover">
      <div className="card-panel center">
        <h1>Game over</h1>
        {winner && (
          <p className="winner-big">
            👑 {winner.name} wins{winner.id === playerId ? " — that's you!" : ""}
          </p>
        )}
        <Scoreboard players={gameOver.standings} meId={playerId} winnerId={gameOver.winnerId} />
        <div className="lobby-actions center">
          <button className="btn btn-ghost" onClick={onLeave}>
            Leave
          </button>
          {isHost && (
            <button className="btn btn-primary" onClick={() => send({ type: "play_again" })}>
              Play again
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
