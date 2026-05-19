// Tests for the /ask server action.
//
// We test:
//   1. validateCreateQuestion — pure validation, exhaustive.
//   2. createQuestion — happy path with an in-memory fake Drizzle handle.
//
// We intentionally don't test createQuestionAction end-to-end here because
// it calls Next's `redirect()`, which throws a special error and is annoying
// to fake outside a Next request context. Validation + DB insertion is the
// load-bearing logic; the action is a thin shell that ties them together.

import { describe, it, expect, vi } from "vitest";
import { createQuestion } from "../src/actions/create-question";
import {
  validateCreateQuestion,
  type CreateQuestionInput,
} from "../src/actions/validate-question";

// ---------- validateCreateQuestion ----------

describe("validateCreateQuestion", () => {
  const futureDate = new Date(Date.now() + 86_400_000);

  it("accepts a valid input", () => {
    const r = validateCreateQuestion({
      displayName: "Alice",
      text: "Should we ship?",
      topic: "engineering",
      closesAt: futureDate,
    });
    expect(r.ok).toBe(true);
    if (r.ok) {
      expect(r.value.displayName).toBe("Alice");
      expect(r.value.topic).toBe("engineering");
    }
  });

  it("trims whitespace", () => {
    const r = validateCreateQuestion({
      displayName: "  Alice  ",
      text: "  hello?  ",
      topic: "   ",
      closesAt: futureDate,
    });
    expect(r.ok).toBe(true);
    if (r.ok) {
      expect(r.value.displayName).toBe("Alice");
      expect(r.value.text).toBe("hello?");
      // Empty topic after trim becomes null.
      expect(r.value.topic).toBeNull();
    }
  });

  it("rejects missing display_name", () => {
    const r = validateCreateQuestion({
      displayName: "",
      text: "Hi?",
      closesAt: futureDate,
    });
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.errors.displayName).toBeTruthy();
  });

  it("rejects missing text", () => {
    const r = validateCreateQuestion({
      displayName: "Alice",
      text: "   ",
      closesAt: futureDate,
    });
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.errors.text).toBeTruthy();
  });

  it("rejects past closes_at", () => {
    const r = validateCreateQuestion({
      displayName: "Alice",
      text: "Hi?",
      closesAt: new Date(Date.now() - 60_000),
    });
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.errors.closesAt).toBeTruthy();
  });

  it("rejects too-long text", () => {
    const r = validateCreateQuestion({
      displayName: "Alice",
      text: "a".repeat(2001),
      closesAt: futureDate,
    });
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.errors.text).toBeTruthy();
  });
});

// ---------- createQuestion (happy path) ----------

 /**
  * Build a fake Drizzle handle that records the calls the action makes.
 * We mimic just enough surface to satisfy the chained
 * `.insert()...returning()` flows.
 */
function buildFakeDb(opts: {
  newAskerId?: string;
  newQuestionId?: string;
}) {
  const calls: { kind: string; args: unknown }[] = [];

  const insert = vi.fn((_table: unknown) => {
    return {
      values: (vals: unknown) => {
        return {
          returning: async () => {
            // The first insert is the display-only asker row; the second is
            // the question. We disambiguate by inspecting the values.
            if (vals && typeof vals === "object" && "displayName" in vals) {
              calls.push({ kind: "insert-asker", args: vals });
              return [{ id: opts.newAskerId ?? "asker-uuid" }];
            }
            calls.push({ kind: "insert-question", args: vals });
            return [{ id: opts.newQuestionId ?? "question-uuid" }];
          },
        };
      },
    };
  });

  return {
    fake: { insert } as unknown as Parameters<
      typeof createQuestion
    >[1],
    calls,
  };
}

describe("createQuestion", () => {
  const input: CreateQuestionInput = {
    displayName: "Alice",
    text: "Should we ship today?",
    topic: "engineering",
    closesAt: new Date(Date.now() + 86_400_000),
  };

  it("creates a fresh asker display row, then inserts the question", async () => {
    const { fake, calls } = buildFakeDb({
      newAskerId: "asker-1",
      newQuestionId: "question-1",
    });
    const r = await createQuestion(input, fake);
    expect(r.questionId).toBe("question-1");

    const kinds = calls.map((c) => c.kind);
    expect(kinds).toEqual(["insert-asker", "insert-question"]);

    const qInsert = calls.find((c) => c.kind === "insert-question")!
      .args as Record<string, unknown>;
    expect(qInsert.askerId).toBe("asker-1");
    expect(qInsert.text).toBe(input.text);
    expect(qInsert.topic).toBe("engineering");
  });
});
