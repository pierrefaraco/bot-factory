const playwright = require('playwright');
const fs = require('fs');

(async () => {
  const url = process.argv[2] || 'http://localhost:4200/workspace';
  const outDir = process.argv[3] || 'client/e2e-screenshots';

  if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });

  const viewports = [
    { name: 'desktop', width: 1366, height: 768 },
    { name: 'tablet', width: 768, height: 1024 },
    { name: 'mobile', width: 375, height: 812 }
  ];

  for (const vp of viewports) {
    console.log(`Capturing ${vp.name} ${vp.width}x${vp.height} ...`);
    const browser = await playwright.chromium.launch({ headless: true });
    const context = await browser.newContext({ viewport: { width: vp.width, height: vp.height } });
    const page = await context.newPage();
    try {
      await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
      // wait for main dashboard to appear
      try {
        await page.waitForSelector('.dashboard, .landing-page, app-root', { timeout: 10000 });
      } catch (e) {
        console.warn('Main selector not found, proceeding to screenshot anyway');
      }
      const path = `${outDir}/workspace-${vp.name}.png`;
      await page.screenshot({ path, fullPage: true });
      console.log(`Saved ${path}`);
    } catch (err) {
      console.error(`Error capturing ${vp.name}:`, err.message);
    } finally {
      await browser.close();
    }
  }

  console.log('All screenshots done');
})();