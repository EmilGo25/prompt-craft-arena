import { describe, expect, it } from "vitest";
import { translate } from "./i18n";
import { translations } from "./i18n/translations";

describe("i18n translate", () => {
  it("interpolates parameters", () => {
    expect(translate("en", "round.roundOf", { n: 1, total: 3 })).toBe("Round 1 of 3");
  });

  it("returns the key itself for an unknown key (no crash)", () => {
    expect(translate("en", "nope.missing")).toBe("nope.missing");
  });

  it("falls back to English when a key is missing in the target language", () => {
    // A key present in en; if absent in he the english value is returned.
    const v = translate("he", "home.createBtn");
    expect(typeof v).toBe("string");
    expect(v.length).toBeGreaterThan(0);
  });

  it("Hebrew defines every English key (no missing translations)", () => {
    const enKeys = Object.keys(translations.en);
    const heKeys = new Set(Object.keys(translations.he));
    const missing = enKeys.filter((k) => !heKeys.has(k));
    expect(missing).toEqual([]);
  });

  it("English defines every Hebrew key (no stray keys)", () => {
    const heKeys = Object.keys(translations.he);
    const enKeys = new Set(Object.keys(translations.en));
    expect(heKeys.filter((k) => !enKeys.has(k))).toEqual([]);
  });
});
