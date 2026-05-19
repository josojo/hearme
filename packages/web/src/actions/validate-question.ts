// Pure validation for /ask. Kept in its own module so we can `import` it
// from non-server code (forms, tests) without falling under the
// "use server" rule that every export of a server-action module must be
// an async function.

import { COUNTRY_TO_CONTINENT, type Continent } from "@/lib/geo-data";

export type Scope = "worldwide" | "continent" | "country";

export type CreateQuestionInput = {
  displayName: string;
  text: string;
  topic?: string | null;
  closesAt: Date;
  scope: Scope;
  country: string | null;
  continent: Continent | null;
};

const MAX_TEXT_LEN = 2000;
const MAX_TOPIC_LEN = 80;
const MAX_NAME_LEN = 80;

const CONTINENTS: ReadonlyArray<Continent> = ["AF","AN","AS","EU","NA","OC","SA"];

export function validateCreateQuestion(
  input: Partial<CreateQuestionInput>,
):
  | { ok: true; value: CreateQuestionInput }
  | { ok: false; errors: Record<string, string> } {
  const errors: Record<string, string> = {};

  const displayName = (input.displayName ?? "").trim();
  if (!displayName) {
    errors.displayName = "Display name is required.";
  } else if (displayName.length > MAX_NAME_LEN) {
    errors.displayName = `Display name must be ≤ ${MAX_NAME_LEN} characters.`;
  }

  const text = (input.text ?? "").trim();
  if (!text) {
    errors.text = "Question text is required.";
  } else if (text.length > MAX_TEXT_LEN) {
    errors.text = `Question must be ≤ ${MAX_TEXT_LEN} characters.`;
  }

  const topicRaw = (input.topic ?? "").toString().trim();
  const topic = topicRaw === "" ? null : topicRaw;
  if (topic && topic.length > MAX_TOPIC_LEN) {
    errors.topic = `Topic must be ≤ ${MAX_TOPIC_LEN} characters.`;
  }

  const closesAt = input.closesAt instanceof Date ? input.closesAt : null;
  if (!closesAt || Number.isNaN(closesAt.getTime())) {
    errors.closesAt = "A close time is required.";
  } else if (closesAt.getTime() <= Date.now()) {
    errors.closesAt = "Close time must be in the future.";
  }

  const scopeRaw = (input.scope ?? "worldwide") as Scope;
  let scope: Scope = "worldwide";
  let country: string | null = null;
  let continent: Continent | null = null;
  if (scopeRaw === "worldwide" || scopeRaw === "continent" || scopeRaw === "country") {
    scope = scopeRaw;
  } else {
    errors.scope = "Invalid scope.";
  }

  if (scope === "continent") {
    const c = (input.continent ?? "")?.toString().toUpperCase() as Continent;
    if (!c || !CONTINENTS.includes(c)) {
      errors.continent = "Please pick a continent.";
    } else {
      continent = c;
    }
  } else if (scope === "country") {
    const cc = (input.country ?? "")?.toString().toUpperCase();
    if (!cc || cc.length !== 2) {
      errors.country = "Please pick a country.";
    } else {
      const derived = COUNTRY_TO_CONTINENT[cc];
      if (!derived) {
        errors.country = "Unknown country code.";
      } else {
        country = cc;
        continent = derived;
      }
    }
  }

  if (Object.keys(errors).length > 0) {
    return { ok: false, errors };
  }

  return {
    ok: true,
    value: {
      displayName,
      text,
      topic,
      closesAt: closesAt as Date,
      scope,
      country,
      continent,
    },
  };
}
