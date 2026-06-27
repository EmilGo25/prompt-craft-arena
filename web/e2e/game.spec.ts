import { test, expect } from "@playwright/test";

// Full single-player game, end to end over real HTTP + WebSocket, against the
// stub image generator + random judge. Runs on a representative desktop + one
// mobile profile (the other devices are covered by the visual/overflow spec).
test("plays a full game from home to game over", async ({ page }, testInfo) => {
  test.skip(
    !["desktop-chromium", "iphone-12"].includes(testInfo.project.name),
    "full game flow runs on representative projects only",
  );

  await page.goto("/");

  // Home → create a game
  await page.getByPlaceholder("e.g. Ada").fill("E2E Player");
  await page.getByRole("button", { name: "Create game" }).click();

  // Lobby → start
  await expect(page.getByRole("button", { name: "Start game" })).toBeVisible({ timeout: 15_000 });
  await page.getByRole("button", { name: "Start game" }).click();

  // Play each round: submit a prompt whenever the prompt box appears, until the
  // game-over screen shows. (Backend is configured for 2 rounds.)
  const promptBox = page.getByPlaceholder(/Describe the target image/);
  const submitBtn = page.getByRole("button", { name: "Submit prompt" });
  const roundLabel = page.locator(".round-banner span").first();
  const gameOver = page.getByRole("heading", { name: "Game over" });

  // Single-player rounds resolve the instant we submit, so we drive by round
  // number (submit once per round) and poll until the game ends.
  const submitted = new Set<string>();
  for (let i = 0; i < 20; i++) {
    if (await gameOver.isVisible().catch(() => false)) break;
    if (await promptBox.isVisible().catch(() => false)) {
      const label = ((await roundLabel.textContent().catch(() => "")) || `r${i}`).trim();
      if (!submitted.has(label)) {
        submitted.add(label);
        await promptBox.fill("a lone red fox on a snowy hill at sunset, painterly");
        await submitBtn.click();
      }
    }
    await page.waitForTimeout(400);
  }

  // Game over: standings + the transparent scorecard are shown
  await expect(gameOver).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText("Your scorecard")).toBeVisible();
  await expect(page.getByText("Round-by-round recap")).toBeVisible();
});
