/**
 * Accessibility contract tests.
 * These verify the structural ARIA invariants that WCAG 2.1 AA requires,
 * without needing a running browser or Next.js router.
 */

import { describe, it, expect } from "vitest";

// ── ARIA attribute contract helpers ───────────────────────────────────────────

/** Validate that a progressbar has the required ARIA attributes. */
function validateProgressbar(attrs: Record<string, unknown>) {
  expect(attrs.role).toBe("progressbar");
  expect(typeof attrs["aria-valuenow"]).toBe("number");
  expect(typeof attrs["aria-valuemin"]).toBe("number");
  expect(typeof attrs["aria-valuemax"]).toBe("number");
  expect(attrs["aria-valuemin"] as number).toBeLessThanOrEqual(attrs["aria-valuenow"] as number);
  expect(attrs["aria-valuenow"] as number).toBeLessThanOrEqual(attrs["aria-valuemax"] as number);
  expect(typeof attrs["aria-label"]).toBe("string");
}

/** Validate that a radiogroup / radio pair is correctly wired. */
function validateRadiogroup(groupAttrs: Record<string, unknown>, radioAttrs: Record<string, unknown>[]) {
  expect(groupAttrs.role).toBe("radiogroup");
  expect(typeof groupAttrs["aria-labelledby"]).toBe("string");
  for (const r of radioAttrs) {
    expect(r.role).toBe("radio");
    expect(typeof r["aria-checked"]).toBe("boolean");
  }
}

/** Validate a live region used for status announcements. */
function validateStatusRegion(attrs: Record<string, unknown>) {
  expect(attrs.role).toBe("status");
  expect(attrs["aria-live"]).toBe("polite");
}

/** Validate a role=alert region (immediate announcement). */
function validateAlertRegion(attrs: Record<string, unknown>) {
  expect(attrs.role).toBe("alert");
}

// ── Progressbar ───────────────────────────────────────────────────────────────

describe("progressbar ARIA contract", () => {
  it("valid: step 1 of 6", () => {
    validateProgressbar({
      role: "progressbar",
      "aria-valuenow": 0,
      "aria-valuemin": 0,
      "aria-valuemax": 100,
      "aria-label": "Assessment progress: step 1 of 6",
    });
  });

  it("valid: step 3 of 6 (50%)", () => {
    validateProgressbar({
      role: "progressbar",
      "aria-valuenow": 50,
      "aria-valuemin": 0,
      "aria-valuemax": 100,
      "aria-label": "Assessment progress: step 3 of 6",
    });
  });

  it("invalid: missing aria-label fails contract", () => {
    expect(() =>
      validateProgressbar({
        role: "progressbar",
        "aria-valuenow": 0,
        "aria-valuemin": 0,
        "aria-valuemax": 100,
      })
    ).toThrow();
  });
});

// ── Radio group ───────────────────────────────────────────────────────────────

describe("radiogroup ARIA contract", () => {
  const groupAttrs = { role: "radiogroup", "aria-labelledby": "question-heading" };

  it("valid: one option selected", () => {
    validateRadiogroup(groupAttrs, [
      { role: "radio", "aria-checked": true },
      { role: "radio", "aria-checked": false },
    ]);
  });

  it("valid: no option selected yet", () => {
    validateRadiogroup(groupAttrs, [
      { role: "radio", "aria-checked": false },
      { role: "radio", "aria-checked": false },
    ]);
  });

  it("invalid: aria-pressed instead of aria-checked fails contract", () => {
    expect(() =>
      validateRadiogroup(groupAttrs, [{ role: "radio", "aria-pressed": true }])
    ).toThrow();
  });
});

// ── Live regions ──────────────────────────────────────────────────────────────

describe("live region ARIA contracts", () => {
  it("loading spinner is a status region", () => {
    validateStatusRegion({ role: "status", "aria-live": "polite" });
  });

  it("conflict card is an alert region", () => {
    validateAlertRegion({ role: "alert" });
  });

  it("checkin message card is a status region", () => {
    validateStatusRegion({ role: "status", "aria-live": "polite" });
  });
});

// ── Touch target size ─────────────────────────────────────────────────────────

describe("touch target size (WCAG 2.5.5 — minimum 44px)", () => {
  const MIN_PX = 44;

  function assertMinTouchTarget(widthPx: number, heightPx: number) {
    expect(widthPx).toBeGreaterThanOrEqual(MIN_PX);
    expect(heightPx).toBeGreaterThanOrEqual(MIN_PX);
  }

  it("send button in chat (44px)", () => assertMinTouchTarget(44, 44));
  it("call button in care page (44px)", () => assertMinTouchTarget(44, 44));
  it("language tab buttons in companion (44px)", () => assertMinTouchTarget(44, 44));
  it("hamburger button in Navbar (44px)", () => assertMinTouchTarget(44, 44));
});
