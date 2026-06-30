import { chromium } from "playwright";

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const errors = [];

page.on("pageerror", (error) => errors.push(error.message));

const path = `${process.cwd()}\\index.html`.replace(/\\/g, "/");
await page.goto(`file:///${path}`);
await page.waitForTimeout(1000);

await page.click('[data-action="open-skills"]');
await page.waitForSelector(".detail-panel.open");

await page.click('[data-action="start-run"]');
await page.waitForSelector(".run-panel.open");

await page.fill("#taskInput", "/");
await page.waitForSelector(".command-palette.open");

await browser.close();

if (errors.length > 0) {
  console.error(errors.join("\n"));
  process.exit(1);
}

console.log("interaction smoke passed: skill panel, run panel, slash palette");
