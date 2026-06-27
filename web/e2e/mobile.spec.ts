import { test, expect, type Page } from "@playwright/test";

/** Fails if the page scrolls horizontally — the classic "broken on mobile" bug. */
async function assertNoHorizontalOverflow(page: Page) {
  const { scrollW, clientW } = await page.evaluate(() => ({
    scrollW: document.documentElement.scrollWidth,
    clientW: document.documentElement.clientWidth,
  }));
  expect(
    scrollW,
    `horizontal overflow: scrollWidth ${scrollW} > clientWidth ${clientW}`,
  ).toBeLessThanOrEqual(clientW + 1); // +1 for sub-pixel rounding
}

test.describe("mobile / responsive", () => {
  test("home renders with no horizontal overflow (+ screenshot)", async ({ page }, testInfo) => {
    await page.goto("/");
    await expect(page.getByRole("button", { name: "Create game" })).toBeVisible();
    await expect(page.getByAltText("Prompt-craft Arena")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Leaderboard" })).toBeVisible();
    await assertNoHorizontalOverflow(page);
    await page.screenshot({
      path: testInfo.outputPath(`home-${testInfo.project.name}.png`),
      fullPage: true,
    });
  });

  test("create + lobby have no horizontal overflow", async ({ page }, testInfo) => {
    await page.goto("/");
    await page.getByPlaceholder("e.g. Ada").fill("Mob");
    await page.getByRole("button", { name: "Create game" }).click();
    await expect(page.getByRole("button", { name: "Start game" })).toBeVisible({ timeout: 15_000 });
    await assertNoHorizontalOverflow(page);
    await page.screenshot({
      path: testInfo.outputPath(`lobby-${testInfo.project.name}.png`),
      fullPage: true,
    });
  });

  test("timer and target image stay pinned while scrolling to the prompt input", async ({
    page,
  }, testInfo) => {
    test.skip(testInfo.project.name === "desktop-chromium", "sticky behavior is mobile-only");

    await page.goto("/");
    await page.getByPlaceholder("e.g. Ada").fill("Sticky");
    await page.getByRole("button", { name: "Create game" }).click();
    await page.getByRole("button", { name: "Start game" }).click();

    // Wait for the prompting screen (target + prompt box), then the timer.
    const promptBox = page.getByPlaceholder(/Describe the target image/);
    await expect(promptBox).toBeVisible({ timeout: 20_000 });
    const timer = page.locator(".timer");
    const target = page.getByAltText("Recreate this");
    await expect(timer).toBeVisible();
    await expect(target).toBeVisible();

    // Scroll down to the prompt input area.
    await promptBox.scrollIntoViewIfNeeded();
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.waitForTimeout(200);

    const vh = page.viewportSize()!.height;

    // Timer still pinned near the top.
    const tBox = await timer.boundingBox();
    expect(tBox, "timer rendered").not.toBeNull();
    expect(tBox!.y, "timer pinned near top").toBeLessThan(vh * 0.4);
    expect(tBox!.y + tBox!.height, "timer within viewport").toBeGreaterThan(0);

    // Minified target image still visible (pinned) and big enough to reference.
    const iBox = await target.boundingBox();
    expect(iBox, "target image rendered").not.toBeNull();
    expect(iBox!.y, "target within viewport top half").toBeLessThan(vh * 0.6);
    expect(iBox!.y + iBox!.height, "target bottom within viewport").toBeGreaterThan(0);
    expect(iBox!.height, "target big enough to use as reference").toBeGreaterThan(120);

    // The language switcher must stay on top (not hidden behind the sticky
    // banner) and remain clickable during a round.
    const langBtn = page.locator(".lang-trigger");
    await expect(langBtn).toBeVisible();
    await langBtn.click(); // would throw if covered/intercepted by another element
    await expect(page.getByRole("option", { name: /עברית/ })).toBeVisible();

    // capture for visual review
    await page.screenshot({ path: testInfo.outputPath(`scrolled-${testInfo.project.name}.png`) });
  });

  test("primary buttons meet the 44px touch-target minimum", async ({ page }) => {
    await page.goto("/");
    for (const name of ["Create game", "Join game"]) {
      const box = await page.getByRole("button", { name }).boundingBox();
      expect(box, `${name} button should be rendered`).not.toBeNull();
      expect(box!.height, `${name} height`).toBeGreaterThanOrEqual(44);
    }
  });
});
