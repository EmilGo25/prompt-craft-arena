// All user-facing strings, per language. Add a language by adding a `Lang` and a
// dictionary here (and an entry in LANGS). Keys use {placeholders} for values.

export type Lang = "en" | "he";

export interface LangMeta {
  code: Lang;
  label: string; // shown in its own language
  flag: string; // emoji flag
  dir: "ltr" | "rtl";
}

export const LANGS: LangMeta[] = [
  { code: "en", label: "English", flag: "🇬🇧", dir: "ltr" },
  { code: "he", label: "עברית", flag: "🇮🇱", dir: "rtl" },
];

const en: Record<string, string> = {
  // common
  "common.you": "you",
  "common.host": "host",
  "common.left": "left",
  "common.leave": "Leave",
  "common.back": "Back",
  "common.connecting": "Connecting…",
  "common.secondsUnit": "s",
  "conn.notFound": "That game code wasn't found.",
  "conn.problem": "Connection problem.",

  // home
  "home.tagline": "Write the prompt that recreates the target image. Closest wins.",
  "home.displayName": "Display name",
  "home.namePlaceholder": "e.g. Ada",
  "home.createTitle": "Create a game",
  "home.rounds": "Rounds",
  "home.secondsPerRound": "Seconds per round",
  "home.estimate": "{rounds} rounds × {seconds}s — about {min} min total.",
  "home.createBtn": "Create game",
  "home.joinTitle": "Join a game",
  "home.gameCode": "Game code",
  "home.joinBtn": "Join game",
  "home.footer": "No account needed. No ads, no purchases — just the game.",
  "lb.title": "Leaderboard",
  "lb.subtitle": "Top players by average score",
  "lb.empty": "No games finished yet — win one and claim the top spot!",
  "lb.games": "{n} games",
  "lb.gamesOne": "1 game",
  "lb.avgLabel": "avg",
  "home.errName": "Pick a display name first.",
  "home.errCreate": "Could not create the game. Is the server running?",
  "home.errCode": "Enter a game code.",
  "home.errNoGame": "No game with that code.",

  // lobby
  "lobby.title": "Lobby",
  "lobby.share": "Share this code so friends can join:",
  "lobby.config": "This game is {n} rounds. You can leave any time.",
  "lobby.startBtn": "Start game",
  "lobby.waitingHost": "Waiting for the host to start…",

  // round / prompting
  "round.roundOf": "Round {n} of {total}",
  "round.generatingTarget": "Generating this round's target image…",
  "prompting.recreate": "Recreate this",
  "prompting.submittedCount": "Submitted {n}/{total}",
  "prompting.tileSubmitted": "{name} submitted",
  "prompting.tileWriting": "{name} is still writing",
  "prompting.you": "(you)",
  "prompting.placeholder": "Describe the target image as precisely as you can…",
  "prompting.locked": "✓ Prompt locked in — waiting for the other players…",
  "prompting.pasteDisabled": "Pasting is disabled — type your prompt.",
  "prompting.submitBtn": "Submit prompt",

  // scoring
  "scoring.waiting": "Waiting for scores…",
  "scoring.waitingDesc":
    "All prompts are in. Generating each player's image and judging how close it is to the target.",

  // reveal
  "reveal.resultsTitle": "Round {n} of {total} — results",
  "reveal.target": "Target",
  "reveal.wonRound": "{name} won this round with {score}.",
  "reveal.standings": "Standings",
  "reveal.everyoneResults": "Everyone's results",
  "reveal.nextRound": "Next round starting…",

  // card
  "card.noImage": "no image",
  "card.match": "match {n}",
  "card.speed": "speed +{n}",

  // dimensions
  "dims.subject": "Subject",
  "dims.composition": "Composition",
  "dims.color": "Color",
  "dims.mood": "Mood",

  // game over
  "gameover.title": "Game over",
  "gameover.winsYou": "{name} wins — that's you!",
  "gameover.wins": "{name} wins",
  "gameover.playAgain": "Play again",
  "gameover.scorecard": "Your scorecard",
  "gameover.visualSimilarity": "Visual similarity",
  "gameover.speedBonus": "Speed bonus",
  "gameover.finalScore": "Final score",
  "gameover.hintJudge": "LLM judge, avg",
  "gameover.hintSpeed": "for early submits, avg",
  "gameover.hintFinal": "per round, avg",
  "gameover.weighting":
    "Each round's score = 80% visual similarity (subject, composition, color & mood) + 20% speed bonus. Similarity always dominates, so an accurate prompt beats a fast but sloppy one.",
  "gameover.recap": "Round-by-round recap",
  "gameover.recapDesc":
    "Compare each player's image against the target and see if the scores look fair.",
  "gameover.roundTarget": "Round {n} target",

  // scorecard summary
  "scorecard.none": "You didn't submit a prompt this game — jump in next round!",
  "scorecard.main":
    "Over {n} rounds you averaged {avg}/100. Your prompts matched the target best on {best} ({bestVal}) and weakest on {worst} ({worstVal}).",
  "scorecard.speedHigh": " Submitting early earned you solid speed bonuses.",
  "scorecard.speedLow": " You could climb the board by submitting a bit earlier.",
};

const he: Record<string, string> = {
  // common
  "common.you": "אתה",
  "common.host": "מארח",
  "common.left": "עזב",
  "common.leave": "עזיבה",
  "common.back": "חזרה",
  "common.connecting": "מתחבר…",
  "common.secondsUnit": "שנ׳",
  "conn.notFound": "קוד המשחק לא נמצא.",
  "conn.problem": "תקלת חיבור.",

  // home
  "home.tagline": "כתבו את הפרומפט שמשחזר את תמונת המטרה. הכי קרוב מנצח.",
  "home.displayName": "שם תצוגה",
  "home.namePlaceholder": "למשל: אדה",
  "home.createTitle": "יצירת משחק",
  "home.rounds": "סיבובים",
  "home.secondsPerRound": "שניות לסיבוב",
  "home.estimate": "{rounds} סיבובים × {seconds} שנ׳ — כ-{min} דק׳ בסך הכול.",
  "home.createBtn": "צור משחק",
  "home.joinTitle": "הצטרפות למשחק",
  "home.gameCode": "קוד משחק",
  "home.joinBtn": "הצטרף",
  "home.footer": "לא נדרש חשבון. בלי פרסומות, בלי רכישות — רק המשחק.",
  "lb.title": "טבלת המובילים",
  "lb.subtitle": "השחקנים המובילים לפי ניקוד ממוצע",
  "lb.empty": "עוד לא הסתיימו משחקים — נצחו באחד ותפסו את המקום הראשון!",
  "lb.games": "{n} משחקים",
  "lb.gamesOne": "משחק אחד",
  "lb.avgLabel": "ממוצע",
  "home.errName": "בחרו שם תצוגה תחילה.",
  "home.errCreate": "לא ניתן ליצור משחק. האם השרת פועל?",
  "home.errCode": "הזינו קוד משחק.",
  "home.errNoGame": "אין משחק עם הקוד הזה.",

  // lobby
  "lobby.title": "חדר המתנה",
  "lobby.share": "שתפו את הקוד כדי שחברים יוכלו להצטרף:",
  "lobby.config": "המשחק כולל {n} סיבובים. אפשר לעזוב בכל רגע.",
  "lobby.startBtn": "התחל משחק",
  "lobby.waitingHost": "ממתינים שהמארח יתחיל…",

  // round / prompting
  "round.roundOf": "סיבוב {n} מתוך {total}",
  "round.generatingTarget": "יוצרים את תמונת המטרה לסיבוב…",
  "prompting.recreate": "שחזרו את זה",
  "prompting.submittedCount": "נשלחו {n}/{total}",
  "prompting.tileSubmitted": "{name} שלח",
  "prompting.tileWriting": "{name} עדיין כותב",
  "prompting.you": "(אתה)",
  "prompting.placeholder": "תארו את תמונת המטרה בדיוק רב ככל האפשר…",
  "prompting.locked": "✓ הפרומפט נשלח — ממתינים לשאר השחקנים…",
  "prompting.pasteDisabled": "הדבקה מושבתת — הקלידו את הפרומפט.",
  "prompting.submitBtn": "שליחת פרומפט",

  // scoring
  "scoring.waiting": "ממתינים לציונים…",
  "scoring.waitingDesc":
    "כל הפרומפטים התקבלו. יוצרים את תמונת כל שחקן ומדרגים עד כמה היא קרובה למטרה.",

  // reveal
  "reveal.resultsTitle": "סיבוב {n} מתוך {total} — תוצאות",
  "reveal.target": "מטרה",
  "reveal.wonRound": "{name} ניצח בסיבוב עם {score}.",
  "reveal.standings": "טבלת דירוג",
  "reveal.everyoneResults": "התוצאות של כולם",
  "reveal.nextRound": "הסיבוב הבא מתחיל…",

  // card
  "card.noImage": "אין תמונה",
  "card.match": "התאמה {n}",
  "card.speed": "מהירות +{n}",

  // dimensions
  "dims.subject": "נושא",
  "dims.composition": "קומפוזיציה",
  "dims.color": "צבע",
  "dims.mood": "אווירה",

  // game over
  "gameover.title": "המשחק נגמר",
  "gameover.winsYou": "{name} מנצח — זה אתה!",
  "gameover.wins": "{name} מנצח",
  "gameover.playAgain": "שחק שוב",
  "gameover.scorecard": "כרטיס הניקוד שלך",
  "gameover.visualSimilarity": "דמיון חזותי",
  "gameover.speedBonus": "בונוס מהירות",
  "gameover.finalScore": "ציון סופי",
  "gameover.hintJudge": "שופט ה-LLM, ממוצע",
  "gameover.hintSpeed": "על שליחה מוקדמת, ממוצע",
  "gameover.hintFinal": "לסיבוב, ממוצע",
  "gameover.weighting":
    "הניקוד בכל סיבוב = 80% דמיון חזותי (נושא, קומפוזיציה, צבע ואווירה) + 20% בונוס מהירות. הדמיון תמיד מכריע, כך שפרומפט מדויק מנצח פרומפט מהיר ורשלני.",
  "gameover.recap": "סיכום סיבוב אחר סיבוב",
  "gameover.recapDesc": "השוו את תמונת כל שחקן למטרה ובדקו אם הציונים הוגנים.",
  "gameover.roundTarget": "מטרת סיבוב {n}",

  // scorecard summary
  "scorecard.none": "לא שלחת פרומפט במשחק הזה — הצטרף בסיבוב הבא!",
  "scorecard.main":
    "לאורך {n} סיבובים הממוצע שלך היה {avg}/100. הפרומפטים שלך התאימו למטרה הכי טוב ב{best} ({bestVal}) והכי פחות ב{worst} ({worstVal}).",
  "scorecard.speedHigh": " שליחה מוקדמת הקנתה לך בונוסי מהירות יפים.",
  "scorecard.speedLow": " תוכל לטפס בטבלה אם תשלח מעט מוקדם יותר.",
};

export const translations: Record<Lang, Record<string, string>> = { en, he };
