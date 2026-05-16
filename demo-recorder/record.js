/**
 * VERA Demo Recorder
 * Records a Playwright-driven walkthrough of the VERA app.
 * Output: ./output/vera-demo.webm  (convert to mp4 with ffmpeg if needed)
 *
 * Prerequisites:
 *   npm install
 *   npm run install-browsers
 *   Make sure the VERA frontend is running at http://localhost:3000
 *   Make sure the backend is running at http://localhost:8000
 *
 * Run:
 *   npm run record
 */

const { chromium } = require("playwright");

const BASE = "http://localhost:3000";
const API  = "http://localhost:8000";

// Persona — primary demo user from CLAUDE.md
const PERSONA = {
  name:      "Arjun",
  age:       "45_54",
  gender:    "male",
  location:  "Mumbai, India",
  language:  "en",
};

// Pause helper — use instead of hard-coded sleeps
const pause = (ms) => new Promise((r) => setTimeout(r, ms));

// Type with realistic cadence
async function type(page, selector, text, delay = 60) {
  await page.click(selector);
  await page.type(selector, text, { delay });
}

async function main() {
  console.log("Starting VERA demo recorder...");

  const browser = await chromium.launch({
    headless: false,   // set true for CI / unattended recording
    slowMo: 80,        // adds slight delay between actions so it reads naturally on video
    args: ["--start-maximized"],
  });

  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    recordVideo: {
      dir: "./output",
      size: { width: 1440, height: 900 },
    },
  });

  const page = await context.newPage();

  // ─────────────────────────────────────────────────────────────────────────
  // STAGE 1 — Landing page
  // ─────────────────────────────────────────────────────────────────────────
  console.log("[1/7] Landing page");
  await page.goto(BASE);
  await page.waitForLoadState("networkidle");
  await pause(3500); // let judges read the hero

  // ─────────────────────────────────────────────────────────────────────────
  // STAGE 2 — Sign up
  // ─────────────────────────────────────────────────────────────────────────
  console.log("[2/7] Signup");
  await page.click("text=Talk to VERA");
  await page.waitForURL(`${BASE}/signup`);
  await pause(800);

  // Name
  await type(page, 'input[placeholder*="first name"]', PERSONA.name);
  await pause(400);

  // Age group pill
  await page.click(`button:has-text("45")`);
  await pause(300);

  // Gender pill
  await page.click(`button:has-text("Male")`);
  await pause(300);

  // Location
  await type(page, 'input[placeholder*="Mumbai"]', PERSONA.location);
  await pause(400);

  // Language (English already selected by default, just pause to show it)
  await pause(500);

  // Submit
  await page.click('button[type="submit"]');
  await page.waitForURL(`${BASE}/chat`);
  await pause(600);

  // ─────────────────────────────────────────────────────────────────────────
  // STAGE 3 — Adaptive health conversation (Agent 1)
  // ─────────────────────────────────────────────────────────────────────────
  console.log("[3/7] Adaptive chat");

  // Q1 — Family history
  await page.waitForSelector('button:has-text("colorectal")', { timeout: 15000 });
  await pause(1200);
  await page.click('button:has-text("colorectal")');
  await pause(900);

  // Q2 — Last screening
  await page.waitForSelector('button:has-text("3")', { timeout: 10000 });
  await pause(1000);
  await page.click('button:has-text("3 – 5 years")');
  await pause(900);

  // Q3 — HPV vaccine
  await page.waitForSelector('button:has-text("No, I")', { timeout: 10000 });
  await pause(900);
  await page.click('button:has-text("No, I")');
  await pause(800);

  // Q4 — Smoking
  await page.waitForSelector('button:has-text("currently")', { timeout: 10000 });
  await pause(900);
  await page.click('button:has-text("currently")');
  await pause(800);

  // Q5 — Symptoms (optional — skip)
  await page.waitForSelector('button:has-text("Skip")', { timeout: 10000 });
  await pause(1500);
  await page.click('button:has-text("Skip")');

  // Wait for redirect to /risk
  await page.waitForURL(`${BASE}/risk`, { timeout: 15000 });
  await pause(2000);

  // ─────────────────────────────────────────────────────────────────────────
  // STAGE 4 — Risk profile (MEDIUM)
  // ─────────────────────────────────────────────────────────────────────────
  console.log("[4/7] Risk profile");
  await pause(4000); // let the score animate in

  // ─────────────────────────────────────────────────────────────────────────
  // STAGE 5 — Care navigation (Agent 2)
  // ─────────────────────────────────────────────────────────────────────────
  console.log("[5/7] Care navigation");
  await page.goto(`${BASE}/schemes`);
  await page.waitForLoadState("networkidle");
  await pause(4000);

  // ─────────────────────────────────────────────────────────────────────────
  // STAGE 6 — Records explainer + conflict (Agent 3 + Agent 1 reconcile)
  // ─────────────────────────────────────────────────────────────────────────
  console.log("[6/7] Records + conflict");
  await page.goto(`${BASE}/records`);
  await page.waitForLoadState("networkidle");
  await pause(4500); // show the records upload UI

  // ─────────────────────────────────────────────────────────────────────────
  // STAGE 7 — Companion (Agent 4) + "Simulate 3 Days Later"
  // ─────────────────────────────────────────────────────────────────────────
  console.log("[7/7] Companion");
  await page.goto(`${BASE}/companion`);
  await page.waitForLoadState("networkidle");
  await pause(4000);

  // Click the simulate button if it exists
  const simulateBtn = page.locator('button:has-text("Simulate")');
  if (await simulateBtn.isVisible()) {
    await simulateBtn.click();
    await pause(3500);
  }

  // Final pause — hold on companion screen before ending
  await pause(2000);

  // ─────────────────────────────────────────────────────────────────────────
  // Done
  // ─────────────────────────────────────────────────────────────────────────
  console.log("Recording complete. Closing browser...");
  await context.close(); // this finalises and writes the .webm file
  await browser.close();

  console.log("\nVideo saved to: ./output/  (look for the .webm file)");
  console.log("To convert to mp4 (requires ffmpeg):");
  console.log("  ffmpeg -i output/<file>.webm -c:v libx264 output/vera-demo.mp4");
}

main().catch((err) => {
  console.error("Recording failed:", err);
  process.exit(1);
});
