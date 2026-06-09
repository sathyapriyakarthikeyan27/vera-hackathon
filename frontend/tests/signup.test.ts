/**
 * Tests for signup page pure logic utilities.
 * No DOM rendering — these cover the computeAgeGroup and BMI helpers
 * that run on the client before the API call.
 */

import { describe, it, expect } from "vitest";

// ── Age group computation (mirrors frontend logic) ────────────────────────────

function computeAgeGroup(dob: string): string {
  const age = Math.floor(
    (Date.now() - new Date(dob).getTime()) / (365.25 * 24 * 60 * 60 * 1000)
  );
  if (age < 25) return "under_25";
  if (age < 35) return "25_34";
  if (age < 45) return "35_44";
  if (age < 55) return "45_54";
  return "55_plus";
}

function computeBmi(heightCm: number, weightKg: number): number {
  return Math.round((weightKg / Math.pow(heightCm / 100, 2)) * 10) / 10;
}

// ── computeAgeGroup ───────────────────────────────────────────────────────────

describe("computeAgeGroup", () => {
  it("classifies a 20-year-old as under_25", () => {
    const dob = new Date();
    dob.setFullYear(dob.getFullYear() - 20);
    expect(computeAgeGroup(dob.toISOString().slice(0, 10))).toBe("under_25");
  });

  it("classifies a 30-year-old as 25_34", () => {
    const dob = new Date();
    dob.setFullYear(dob.getFullYear() - 30);
    expect(computeAgeGroup(dob.toISOString().slice(0, 10))).toBe("25_34");
  });

  it("classifies a 40-year-old as 35_44", () => {
    const dob = new Date();
    dob.setFullYear(dob.getFullYear() - 40);
    expect(computeAgeGroup(dob.toISOString().slice(0, 10))).toBe("35_44");
  });

  it("classifies a 50-year-old as 45_54", () => {
    const dob = new Date();
    dob.setFullYear(dob.getFullYear() - 50);
    expect(computeAgeGroup(dob.toISOString().slice(0, 10))).toBe("45_54");
  });

  it("classifies a 60-year-old as 55_plus", () => {
    const dob = new Date();
    dob.setFullYear(dob.getFullYear() - 60);
    expect(computeAgeGroup(dob.toISOString().slice(0, 10))).toBe("55_plus");
  });
});

// ── computeBmi ────────────────────────────────────────────────────────────────

describe("computeBmi", () => {
  it("returns 22.9 for 70kg / 175cm", () => {
    expect(computeBmi(175, 70)).toBe(22.9);
  });

  it("returns 30.9 for 100kg / 180cm", () => {
    expect(computeBmi(180, 100)).toBe(30.9);
  });

  it("returns 17.6 for 48kg / 165cm", () => {
    expect(computeBmi(165, 48)).toBe(17.6);
  });
});
