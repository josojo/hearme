// Smoke tests for the geo lib. We can't exercise the IP-lookup path here
// without network, but the static country → continent map and the country
// flag emoji generator are pure and easy to assert on.

import { describe, it, expect } from "vitest";
import {
  COUNTRY_TO_CONTINENT,
  CONTINENT_NAMES,
  type Continent,
} from "../src/lib/geo-data";
import { countryFlag } from "../src/lib/flags";

describe("COUNTRY_TO_CONTINENT", () => {
  it("maps known major countries correctly", () => {
    expect(COUNTRY_TO_CONTINENT.US).toBe("NA");
    expect(COUNTRY_TO_CONTINENT.DE).toBe("EU");
    expect(COUNTRY_TO_CONTINENT.JP).toBe("AS");
    expect(COUNTRY_TO_CONTINENT.BR).toBe("SA");
    expect(COUNTRY_TO_CONTINENT.AU).toBe("OC");
    expect(COUNTRY_TO_CONTINENT.NG).toBe("AF");
  });

  it("every mapped continent has a friendly name", () => {
    for (const c of Object.values(COUNTRY_TO_CONTINENT)) {
      expect(CONTINENT_NAMES[c as Continent]).toBeTruthy();
    }
  });
});

describe("countryFlag", () => {
  it("renders a regional-indicator pair for valid codes", () => {
    // 🇺🇸 = U+1F1FA U+1F1F8
    expect(countryFlag("US")).toBe("🇺🇸");
    expect(countryFlag("de")).toBe("🇩🇪");
  });

  it("falls back to the globe for invalid input", () => {
    expect(countryFlag("")).toBe("🌐");
    expect(countryFlag("X")).toBe("🌐");
    expect(countryFlag("12")).toBe("🌐");
  });
});
