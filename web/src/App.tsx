import { useEffect, useState } from "react";
import { useGame } from "./store";
import { useGameSocket } from "./ws";
import { useTranslation } from "./i18n";
import { LanguageMenu } from "./components/LanguageMenu";
import { Home } from "./screens/Home";
import { Lobby } from "./screens/Lobby";
import { Prompting } from "./screens/Prompting";
import { Scoring } from "./screens/Scoring";
import { Reveal } from "./screens/Reveal";
import { GameOver } from "./screens/GameOver";

export default function App() {
  const { t } = useTranslation();
  const [session, setSession] = useState<{ code: string; name: string } | null>(null);
  const phase = useGame((s) => s.phase);
  const connected = useGame((s) => s.connected);
  const connError = useGame((s) => s.connError);
  const toast = useGame((s) => s.toast);
  const clearToast = useGame((s) => s.clearToast);
  const resetGame = useGame((s) => s.resetGame);

  useGameSocket(session?.code ?? null, session?.name ?? null);

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(clearToast, 3500);
    return () => clearTimeout(t);
  }, [toast, clearToast]);

  function leave() {
    resetGame();
    setSession(null);
  }

  if (!session) {
    return (
      <>
        <LanguageMenu />
        <Home onEnter={(code, name) => setSession({ code, name })} />
      </>
    );
  }

  // A failed connect (e.g. bad code) bounces back to Home.
  if (connError) {
    return (
      <>
        <LanguageMenu />
        <div className="screen">
          <div className="card-panel center">
            <p className="error-banner">{t(connError)}</p>
            <button className="btn btn-primary" onClick={leave}>
              {t("common.back")}
            </button>
          </div>
        </div>
      </>
    );
  }

  if (!connected) {
    return (
      <>
        <LanguageMenu />
        <div className="screen">
          <div className="prepare">
            <div className="spinner" />
            <p>{t("common.connecting")}</p>
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      <LanguageMenu />
      {toast && <div className="toast">{toast}</div>}
      {phase === "lobby" && <Lobby onLeave={leave} />}
      {(phase === "generating_target" || phase === "prompting") && <Prompting />}
      {phase === "scoring" && <Scoring />}
      {phase === "reveal" && <Reveal />}
      {phase === "game_over" && <GameOver onLeave={leave} />}
    </>
  );
}
