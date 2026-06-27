import { useState } from "react";
import { createRoom, roomExists } from "../api";
import { useTranslation } from "../i18n";
import { Leaderboard } from "../components/Leaderboard";

export function Home({
  onEnter,
}: {
  onEnter: (code: string, name: string) => void;
}) {
  const { t } = useTranslation();
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [rounds, setRounds] = useState(3);
  const [roundSeconds, setRoundSeconds] = useState(60);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const nameOk = name.trim().length > 0;

  async function handleCreate() {
    if (!nameOk) return setError(t("home.errName"));
    setBusy(true);
    setError(null);
    try {
      const room = await createRoom(rounds, roundSeconds);
      onEnter(room.code, name.trim());
    } catch {
      setError(t("home.errCreate"));
    } finally {
      setBusy(false);
    }
  }

  async function handleJoin() {
    if (!nameOk) return setError(t("home.errName"));
    const c = code.trim().toUpperCase();
    if (c.length < 3) return setError(t("home.errCode"));
    setBusy(true);
    setError(null);
    try {
      if (!(await roomExists(c))) {
        setError(t("home.errNoGame"));
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
        <img className="hero-logo" src="/brand/logo.png" alt="Prompt-craft Arena" />
        <h1 className="visually-hidden">Prompt-craft Arena</h1>
        <p className="tagline">{t("home.tagline")}</p>
      </header>

      <div className="home-split">
      <div className="card-panel home-config">
        <label className="field">
          <span>{t("home.displayName")}</span>
          <input
            value={name}
            maxLength={24}
            onChange={(e) => setName(e.target.value)}
            placeholder={t("home.namePlaceholder")}
          />
        </label>

        <div className="config-sections">
          <section className="panel-col">
            <h2>{t("home.createTitle")}</h2>
            <label className="field">
              <span>{t("home.rounds")}</span>
              <input
                type="number"
                min={1}
                max={10}
                value={rounds}
                onChange={(e) => setRounds(Number(e.target.value))}
              />
            </label>
            <label className="field">
              <span>{t("home.secondsPerRound")}</span>
              <input
                type="number"
                min={5}
                max={300}
                value={roundSeconds}
                onChange={(e) => setRoundSeconds(Number(e.target.value))}
              />
            </label>
            <p className="muted">
              {t("home.estimate", {
                rounds,
                seconds: roundSeconds,
                min: Math.ceil((rounds * (roundSeconds + 15)) / 60),
              })}
            </p>
            <button className="btn btn-primary" disabled={busy} onClick={handleCreate}>
              {t("home.createBtn")}
            </button>
          </section>

          <div className="divider-h" />

          <section className="panel-col">
            <h2>{t("home.joinTitle")}</h2>
            <label className="field">
              <span>{t("home.gameCode")}</span>
              <input
                value={code}
                maxLength={4}
                onChange={(e) => setCode(e.target.value.toUpperCase())}
                placeholder="ABCD"
              />
            </label>
            <button className="btn" disabled={busy} onClick={handleJoin}>
              {t("home.joinBtn")}
            </button>
          </section>
        </div>

        {error && <div className="error-banner">{error}</div>}
      </div>

      <Leaderboard />
      </div>

      <footer className="home-foot muted">{t("home.footer")}</footer>
    </div>
  );
}
