// Run with the existing Playwright runtime; uses synthetic data and an isolated browser.
const { chromium } = require('playwright');
const { spawnSync } = require('node:child_process');
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');

(async () => {
  const source = spawnSync(process.env.PYTHON || 'python3', ['-c',
    'import sys;sys.path.insert(0,"scripts");from context_token_injector import INJECTION_SCRIPT;print(INJECTION_SCRIPT)'],
    { cwd: path.resolve(__dirname, '..'), encoding: 'utf8' });
  assert.equal(source.status, 0, source.stderr);
  const browser = await chromium.launch({ headless: true, ...(process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : {}) });
  try {
    const page = await browser.newPage({ viewport: { width: 1400, height: 800 } });
    await page.route('http://hud.test/**', route => route.fulfill({ contentType: 'text/html', body:
      '<header style="height:46px;position:fixed;top:0;left:0;right:0"><button>Project</button></header><header style="display:flex;align-items:center;height:46px;position:fixed;top:0;left:0;right:0"><button>Task title</button><div style="flex:1"></div><button id="share">Share</button></header>' }));
    await page.goto('http://hud.test/');
    const quota = { source: 'codex', windows: { '5h': { usedPercent: 67, resetsAt: Math.floor(Date.now()/1000)+3600 }, '7d': { usedPercent: 42, resetsAt: Math.floor(Date.now()/1000)+86400 } }, observedAt: Date.now()/1000, credits: { balance: '12', unlimited: false } };
    const inject = q => page.evaluate(`(${source.stdout})(${JSON.stringify({ summaries: [], detailsByThread: {}, quota: q })})`);
    await inject(quota);
    const root = page.locator('.cti-hud');
    assert.match(await root.innerText(), /5H/);
    assert.match(await root.innerText(), /67%/);
    assert.equal(await root.getAttribute('data-collapsed'), 'true');
    assert.equal(await root.locator('[data-cti-toggle]').innerText(), '+');
    assert.equal(await root.getAttribute('data-docked'), 'true');
    const compactRect = await root.boundingBox();
    const shareRect = await page.locator('#share').boundingBox();
    assert.ok(compactRect.x + compactRect.width <= shareRect.x, 'HUD must avoid controls in overlapping headers');
    assert.equal(await root.locator('[data-cti-compact] progress').count(), 2);
    if (process.env.HUD_PREVIEW_DIR) {
      fs.mkdirSync(process.env.HUD_PREVIEW_DIR, { recursive: true });
      await root.screenshot({ path: path.join(process.env.HUD_PREVIEW_DIR, 'hud-compact.png') });
    }
    await root.locator('[data-cti-toggle]').click();
    assert.equal(await root.getAttribute('data-collapsed'), 'false');
    assert.match(await root.innerText(), /12/);
    assert.doesNotMatch(await root.innerText(), /Kevin/);
    assert.equal(await root.locator('[data-cti-quota] progress').count(), 2);
    assert.match(await root.locator('[data-cti-quota]').innerText(), /Reset|重置/);
    if (process.env.HUD_PREVIEW_DIR) {
      await root.screenshot({ path: path.join(process.env.HUD_PREVIEW_DIR, 'hud-expanded.png') });
    }
    const countdown = await root.locator('.cti-reset').first().innerText();
    await page.waitForFunction(previous => document.querySelector('.cti-reset').textContent !== previous,
      countdown, { timeout: 3500 });
    assert.notEqual(await root.locator('.cti-reset').first().innerText(), countdown);
    const titleRect = await root.locator('[data-cti-title]').boundingBox();
    const beforeDrag = await root.boundingBox();
    await page.mouse.move(titleRect.x + titleRect.width + 3, titleRect.y + 5);
    await page.mouse.down();
    await page.mouse.move(titleRect.x + titleRect.width - 80, titleRect.y + 120, { steps: 4 });
    await page.mouse.up();
    assert.ok((await root.boundingBox()).y > beforeDrag.y + 50, 'expanded HUD remains draggable');
    await page.waitForTimeout(1100);
    assert.ok((await root.boundingBox()).y > beforeDrag.y + 50, 'refresh preserves dragged position');
    await inject({ ...quota, observedAt: Date.now()/1000-300 });
    assert.match(await root.innerText(), /Stale|過期/);
    await inject({ ...quota, windows: { '5h': null, '7d': null } });
    assert.match(await root.innerText(), /Unavailable|不可用/);
    assert.equal(await root.locator('progress[value]').count(), 0);
    await inject({ ...quota, windows: { ...quota.windows, '5h': { usedPercent: 0, resetsAt: 1 } } });
    assert.match(await root.innerText(), /Awaiting refresh|等待更新/);
    await inject(quota);
    assert.equal(await page.locator('.cti-hud').count(), 1);
    await root.locator('[data-cti-toggle]').click();
    assert.equal(await root.getAttribute('data-collapsed'), 'true');
    await page.setViewportSize({ width: 320, height: 600 });
    await page.waitForTimeout(1100);
    assert.notEqual(await root.getAttribute('data-docked'), 'true');
    const rect = await root.boundingBox();
    assert.ok(rect.x >= 0 && rect.x + rect.width <= 320);
    for (const scheme of ['dark', 'light']) {
      await page.emulateMedia({ colorScheme: scheme });
      await page.evaluate(s => document.documentElement.style.colorScheme = s, scheme);
      await page.waitForTimeout(1100);
      const colors = await root.evaluate(e => ({ bg: getComputedStyle(e).backgroundColor, fg: getComputedStyle(e).color }));
      assert.notEqual(colors.bg, colors.fg);
      assert.equal(await root.evaluate(e => getComputedStyle(e).colorScheme), scheme,
        'HUD should inherit the app theme rather than override it with the OS preference');
    }
    await page.evaluate(`(${source.stdout})(${JSON.stringify({ summaries: [{ thread_id: 'fixture', session_total_tokens: 123 }], activeThreadId: 'fixture', quota })})`);
    await page.evaluate(`(${source.stdout})(${JSON.stringify({ summaries: [], activeThreadId: 'new-thread', quota })})`);
    assert.equal(await root.evaluate(e => e.__ctiSessionTotalTokens), null, 'switching to an unknown session must clear the previous total');
    await page.waitForTimeout(800);
    await page.evaluate(() => {
      let applying = window.__codexContextTokenInspectorApplying;
      window.testTokenRefreshes = 0;
      Object.defineProperty(window, '__codexContextTokenInspectorApplying', {
        configurable: true,
        get: () => applying,
        set: value => { applying = value; if (value) window.testTokenRefreshes++; },
      });
    });
    await page.waitForTimeout(2200);
    assert.equal(await page.evaluate(() => window.testTokenRefreshes), 0,
      'quota countdown must not trigger token/session rescans');
    console.log('PASS: quota, no-session, toggle, header, stale, missing, expired, reinjection, narrow viewport, themes');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
