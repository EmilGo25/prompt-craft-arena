import { imageUrl } from "../config";
import { ImageCard } from "../components/ImageCard";
import { Scoreboard } from "../components/Scoreboard";
import { useGame } from "../store";

export function Reveal() {
  const { reveal, roomCode, playerId, roundNum, totalRounds } = useGame();
  if (!reveal || !roomCode) return null;

  const winner = reveal.results.find((r) => r.player_id === reveal.winnerId);

  return (
    <div className="screen reveal">
      <div className="round-banner">
        <span>
          Round {roundNum} of {totalRounds} — results
        </span>
      </div>

      <div className="reveal-top">
        <div className="reveal-target">
          <h3>Target</h3>
          <img
            className="target-img"
            src={imageUrl(roomCode, reveal.targetImageId)}
            alt="Round target"
          />
          {winner && (
            <p className="winner-line">
              👑 <strong>{winner.player_name}</strong> won this round with {winner.score}.
            </p>
          )}
        </div>
        <div className="reveal-standings">
          <h3>Standings</h3>
          <Scoreboard players={reveal.standings} meId={playerId} winnerId={reveal.winnerId} />
        </div>
      </div>

      <h3 className="reveal-h">Everyone's results</h3>
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

      <p className="muted reveal-next">Next round starting…</p>
    </div>
  );
}
