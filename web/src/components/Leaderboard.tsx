import { useEffect, useState } from "react";
import { getLeaderboard } from "../api";
import { useTranslation } from "../i18n";
import type { LeaderboardEntry } from "../types";

const MEDAL: Record<number, string> = { 1: "🥇", 2: "🥈", 3: "🥉" };

/** Global leaderboard, ranked by average per-round score. Top three get
 * gold / silver / bronze medals to drive the climb-the-board competition. */
export function Leaderboard() {
  const { t } = useTranslation();
  const [entries, setEntries] = useState<LeaderboardEntry[] | null>(null);

  useEffect(() => {
    let alive = true;
    getLeaderboard(20).then((e) => alive && setEntries(e));
    return () => {
      alive = false;
    };
  }, []);

  return (
    <aside className="card-panel leaderboard-panel">
      <div className="lb-head">
        <h2>🏆 {t("lb.title")}</h2>
        <p className="muted">{t("lb.subtitle")}</p>
      </div>

      {entries === null ? (
        <div className="lb-loading">
          <div className="spinner" />
        </div>
      ) : entries.length === 0 ? (
        <p className="muted lb-empty">{t("lb.empty")}</p>
      ) : (
        <ol className="lb-list">
          {entries.map((e) => {
            const medal = MEDAL[e.rank];
            return (
              <li key={e.name} className={`lb-row ${medal ? `lb-top lb-rank${e.rank}` : ""}`}>
                <span className="lb-rank">{medal ?? e.rank}</span>
                <span className="lb-name">
                  {e.name}
                  <span className="lb-games">
                    {e.games === 1 ? t("lb.gamesOne") : t("lb.games", { n: e.games })}
                  </span>
                </span>
                <span className="lb-avg">
                  {e.avg}
                  <span className="lb-avg-label">{t("lb.avgLabel")}</span>
                </span>
              </li>
            );
          })}
        </ol>
      )}
    </aside>
  );
}
