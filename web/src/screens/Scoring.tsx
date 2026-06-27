import { useGame } from "../store";
import { useTranslation } from "../i18n";

export function Scoring() {
  const { t } = useTranslation();
  const { roundNum, totalRounds } = useGame();
  return (
    <div className="screen scoring">
      <div className="round-banner">
        {t("round.roundOf", { n: roundNum, total: totalRounds })}
      </div>
      <div className="prepare">
        <div className="spinner" />
        <h3>{t("scoring.waiting")}</h3>
        <p className="muted">{t("scoring.waitingDesc")}</p>
      </div>
    </div>
  );
}
