// Rendering test for the question detail view.
//
// Covers the load-bearing claim from ARCHITECTURE.md §4: the detail page
// surfaces the per-predicate breakdown from `aggregates.by_predicate`.
// We render <QuestionDetail/> with seeded data and assert that the
// dimensions, values, and counts all appear in the DOM.

import { describe, it, expect } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { QuestionDetail } from "../src/components/question-detail";
import { groupByDimension } from "../src/components/aggregate-chart";

describe("QuestionDetail rendering", () => {
  const baseQuestion = {
    id: "q-1",
    text: "Should the EU adopt policy X?",
    topic: "politics",
    status: "open",
    createdAt: new Date("2026-05-19T10:00:00Z"),
    closesAt: new Date("2026-05-26T10:00:00Z"),
  };

  it("renders the question text and topic", () => {
    render(
      <QuestionDetail
        question={baseQuestion}
        totalAnswers={0}
        byPredicate={{}}
        envelopes={[]}
        page={1}
        pageSize={25}
        hasNextPage={false}
      />,
    );
    expect(
      screen.getByText("Should the EU adopt policy X?"),
    ).toBeTruthy();
    expect(screen.getByText("#politics")).toBeTruthy();
  });

  it("renders the predicate breakdown from aggregates.by_predicate", () => {
    const byPredicate = {
      "region:EU": 42,
      "region:non-EU": 18,
      "age_band:18-24": 7,
      "age_band:25-34": 30,
      "age_band:35-44": 23,
    };

    render(
      <QuestionDetail
        question={baseQuestion}
        totalAnswers={60}
        byPredicate={byPredicate}
        envelopes={[]}
        page={1}
        pageSize={25}
        hasNextPage={false}
      />,
    );

    // Total surfaces.
    expect(screen.getByText("60")).toBeTruthy();

    // Dimensions appear as section headings.
    expect(screen.getByText("region")).toBeTruthy();
    expect(screen.getByText("age_band")).toBeTruthy();

    // Values appear, with their counts.
    expect(screen.getByText("EU")).toBeTruthy();
    expect(screen.getByText("non-EU")).toBeTruthy();
    expect(screen.getByText("42")).toBeTruthy();
    expect(screen.getByText("18")).toBeTruthy();
    expect(screen.getByText("25-34")).toBeTruthy();
    expect(screen.getByText("30")).toBeTruthy();
  });

  it("renders individual envelopes with their disclosed predicates", () => {
    render(
      <QuestionDetail
        question={baseQuestion}
        totalAnswers={2}
        byPredicate={{ "region:EU": 2 }}
        envelopes={[
          {
            uniqueIdentifier: "abc123def456",
            answer: "Yes, with caveats.",
            disclosedPredicates: { region: "EU", age_band: "25-34" },
            submittedAt: new Date("2026-05-19T11:00:00Z"),
          },
          {
            uniqueIdentifier: "zzz999yyy888",
            answer: "Strongly opposed.",
            disclosedPredicates: { region: "EU", age_band: "35-44" },
            submittedAt: new Date("2026-05-19T11:05:00Z"),
          },
        ]}
        page={1}
        pageSize={25}
        hasNextPage={false}
      />,
    );

    expect(screen.getByText("Yes, with caveats.")).toBeTruthy();
    expect(screen.getByText("Strongly opposed.")).toBeTruthy();

    // Disclosed-predicate chips on each envelope.
    expect(screen.getByText("age_band: 25-34")).toBeTruthy();
    expect(screen.getByText("age_band: 35-44")).toBeTruthy();
  });

  it("shows an empty-state when there are no answers", () => {
    render(
      <QuestionDetail
        question={baseQuestion}
        totalAnswers={0}
        byPredicate={{}}
        envelopes={[]}
        page={1}
        pageSize={25}
        hasNextPage={false}
      />,
    );

    expect(
      screen.getByText(/No envelopes recorded yet/i),
    ).toBeTruthy();
    expect(
      screen.getByText(/No answers yet/i),
    ).toBeTruthy();
  });
});

describe("groupByDimension", () => {
  it("splits 'dim:value' keys correctly and sorts values by count desc", () => {
    const grouped = groupByDimension({
      "region:EU": 42,
      "region:non-EU": 18,
      "age_band:25-34": 30,
    });
    expect(Object.keys(grouped).sort()).toEqual(["age_band", "region"]);
    expect(grouped.region.map((e) => e.value)).toEqual(["EU", "non-EU"]);
    expect(grouped.region[0].count).toBe(42);
  });

  it("ignores non-numeric values", () => {
    const grouped = groupByDimension({
      "region:EU": 10,
      // @ts-expect-error — intentionally bad input
      "region:bad": "oops",
    });
    expect(grouped.region.length).toBe(1);
  });

  it("groups keys without a ':' under 'other'", () => {
    const grouped = groupByDimension({ standalone: 5 });
    expect(grouped.other).toEqual([{ value: "standalone", count: 5 }]);
  });
});

// Silence unused-import warnings from `within`.
void within;
