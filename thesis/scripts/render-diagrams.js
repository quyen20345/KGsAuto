#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

const WIDTH = Number(process.env.KG_PROMPT_WIDTH || 1400);
const INITIAL_HEIGHT = Number(process.env.KG_PROMPT_INITIAL_HEIGHT || 800);
const DEVICE_SCALE_FACTOR = Number(process.env.KG_PROMPT_DEVICE_SCALE_FACTOR || 2);

function findChrome() {
  if (process.env.PUPPETEER_EXECUTABLE_PATH) return process.env.PUPPETEER_EXECUTABLE_PATH;
  if (process.env.CHROME) return process.env.CHROME;

  for (const name of ['google-chrome', 'chromium', 'chromium-browser']) {
    try {
      return execFileSync('which', [name], { encoding: 'utf8' }).trim();
    } catch (_) {
      // Try the next executable name.
    }
  }
  return undefined;
}

async function main() {
  const [inputArg, outputArg] = process.argv.slice(2);
  if (!inputArg || !outputArg) {
    console.error('Usage: node scripts/render-diagrams.js <input-html> <output-png>');
    process.exit(2);
  }

  const inputPath = path.resolve(inputArg);
  const outputPath = path.resolve(outputArg);
  if (!fs.existsSync(inputPath)) {
    console.error(`Input HTML not found: ${inputPath}`);
    process.exit(1);
  }
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });

  let puppeteer;
  try {
    puppeteer = require('puppeteer');
  } catch (err) {
    console.error('Missing dependency: puppeteer. Run `npm install` in the thesis directory.');
    process.exit(1);
  }

  const executablePath = findChrome();
  const browser = await puppeteer.launch({
    headless: true,
    executablePath,
    args: ['--no-sandbox', '--disable-gpu'],
  });

  try {
    const page = await browser.newPage();
    await page.setViewport({
      width: WIDTH,
      height: INITIAL_HEIGHT,
      deviceScaleFactor: DEVICE_SCALE_FACTOR,
    });

    await page.goto(`file://${inputPath}`, { waitUntil: 'networkidle0' });
    await page.evaluateHandle('document.fonts.ready');

    const height = await page.evaluate(() =>
      Math.ceil(document.documentElement.getBoundingClientRect().height)
    );
    await page.setViewport({
      width: WIDTH,
      height,
      deviceScaleFactor: DEVICE_SCALE_FACTOR,
    });

    await page.screenshot({
      path: outputPath,
      fullPage: false,
      clip: { x: 0, y: 0, width: WIDTH, height },
    });

    console.log(`Rendered ${outputPath} (${WIDTH}x${height} CSS px @${DEVICE_SCALE_FACTOR}x)`);
  } finally {
    await browser.close();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
