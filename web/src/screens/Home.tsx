import { useState } from "react";
import { createRoom, roomExists } from "../api";

export function Home({
  onEnter,
}: {
  onEnter: (code: string, name: string) => void;
}) {
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [rounds, setRounds] = useState(3);
  const [roundSeconds, setRoundSeconds] = useState(30);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const nameOk = name.trim().length > 0;

  async function handleCreate() {
    if (!nameOk) return setError("Pick a display name first.");
    setBusy(true);
    setError(null);
    try {
      const room = await createRoom(rounds, roundSeconds);
      onEnter(room.code, name.trim());
    } catch {
      setError("Could not create the game. Is the server running?");
    } finally {
      setBusy(false);
    }
  }

  async function handleJoin() {
    if (!nameOk) return setError("Pick a display name first.");
    const c = code.trim().toUpperCase();
    if (c.length < 3) return setError("Enter a game code.");
    setBusy(true);
    setError(null);
    try {
      if (!(await roomExists(c))) {
        setError("No game with that code.");
        return;
      }
      onEnter(c, name.trim());
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="screen home">
      <header className="hero">
        <h1>Prompt-craft Arena</h1>
        <p className="tagline">
          Write the prompt that recreates the target image. Closest wins.
        </p>
      </header>

      <div className="card-panel">
        <label className="field">
          <span>Display name</span>
          <input
            value={name}
            maxLength={24}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Ada"
          />
        </label>

        <div className="panel-cols">
          <section className="panel-col">
            <h2>Create a game</h2>
            <label className="field">
              <span>Rounds</span>
              <input
                type="number"
                min={1}
                max={10}
                value={rounds}
                onChange={(e) => setRounds(Number(e.target.value))}
              />
            </label>
            <label className="field">
              <span>Seconds per round</span>
              <input
                type="number"
                min={5}
                max={300}
                value={roundSeconds}
                onChange={(e) => setRoundSeconds(Number(e.target.value))}
              />
            </label>
            <p className="muted">
              {rounds} {rounds === 1 ? "round" : "rounds"} × {roundSeconds}s — about{" "}
              {Math.ceil((rounds * (roundSeconds + 15)) / 60)} min total.
            </p>
            <button className="btn btn-primary" disabled={busy} onClick={handleCreate}>
              Create game
            </button>
          </section>

          <div className="divider" />

          <section className="panel-col">
            <h2>Join a game</h2>
            <label className="field">
              <span>Game code</span>
              <input
                value={code}
                maxLength={4}
                onChange={(e) => setCode(e.target.value.toUpperCase())}
                placeholder="ABCD"
              />
            </label>
            <button className="btn" disabled={busy} onClick={handleJoin}>
              Join game
            </button>
          </section>
        </div>

        {error && <div className="error-banner">{error}</div>}
      </div>

      <footer className="home-foot muted">
        No account needed. No ads, no purchases — just the game.
      </footer>
    </div>
  );
}
