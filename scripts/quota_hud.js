// Included in the existing injector closure; all account values use DOM properties.
function quotaText(node, value) {
  if (node.textContent !== value) node.textContent = value;
}

function renderQuota(root, quota) {
  let style = document.getElementById('cti-quota-style');
  if (!style) {
    style = document.createElement('style');
    style.id = 'cti-quota-style';
    document.head.append(style);
  }
  const scheme = getComputedStyle(document.body).colorScheme === 'normal' ? 'light dark' : 'inherit';
  const css = `
    .cti-hud { max-width:calc(100vw - 16px); color-scheme:${scheme}; }
    .cti-hud:not([data-collapsed="true"]) { max-height:calc(100vh - 70px);overflow:auto; }
    .dark .cti-hud { color-scheme:dark; }
    .light .cti-hud { color-scheme:light; }
    .cti-hud [data-cti-title] { display:flex;gap:10px;width:auto;height:auto;padding:0;border:0;background:none;color:inherit;font:inherit; }
    [data-cti-compact] { display:flex;gap:12px;align-items:center; }
    .cti-mini { display:grid;grid-template-columns:auto auto;gap:2px 5px;font:10px/1.2 system-ui;min-width:68px;text-align:left; }
    .cti-mini progress { grid-column:1 / -1;width:100%;height:4px; }
    .cti-hud progress { appearance:none;border:0;border-radius:8px;overflow:hidden;background:color-mix(in srgb,CanvasText 12%,Canvas);accent-color:var(--cti-fill,#39877a); }
    .cti-hud progress::-webkit-progress-bar { background:color-mix(in srgb,CanvasText 12%,Canvas);border-radius:8px; }
    .cti-hud progress::-webkit-progress-value { background:var(--cti-fill,#39877a);border-radius:8px; }
    .cti-hud progress:not([value]) { opacity:.35; }
    [data-cti-quota] { padding:12px;display:grid;gap:12px;min-width:310px; }
    .cti-quota-row { display:grid;grid-template-columns:1fr auto;gap:5px;font:12px/1.4 system-ui; }
    .cti-quota-row progress { grid-column:1 / -1;width:100%;height:7px; }
    .cti-reset { grid-column:1 / -1;font-size:11px;opacity:.7; }
    .cti-quota-note { font:11px/1.4 system-ui;opacity:.7; }
    .cti-hud[data-collapsed="true"] [data-cti-quota] { display:none; }
    .cti-hud:not([data-collapsed="true"]) [data-cti-compact] { display:none; }
    .cti-hud[data-docked="true"][data-collapsed="true"] { box-shadow:none;background:Canvas;border-radius:7px; }
    .cti-hud[data-docked="true"] { -webkit-app-region:no-drag;pointer-events:auto; }
    .cti-hud[data-docked="true"][data-collapsed="true"] .cti-hud-head { cursor:default; }
    .cti-hud-body { white-space:normal;overflow-wrap:anywhere;max-width:450px; }
    .cti-hud[data-collapsed="true"] .cti-hud-head { padding:4px 7px;gap:7px;border-bottom:0; }
    .cti-hud[data-stale="true"] progress { opacity:.45; }
    @media(max-width:380px) { [data-cti-quota] { min-width:0; } .cti-hud:not([data-collapsed="true"]) { width:calc(100vw - 16px); } }
  `;
  if (style.textContent !== css) style.textContent = css;
  const zh = uiLanguage() === 'zh';
  const unavailable = zh ? '不可用' : 'Unavailable';
  const stale = typeof quota?.observedAt === 'number' && Date.now()/1000 - quota.observedAt > 240;
  root.setAttribute('data-stale', String(stale));
  const compact = root.querySelector('[data-cti-compact]');
  const panel = root.querySelector('[data-cti-quota]');
  if (!panel.children.length) {
    for (const key of ['5h', '7d']) {
      const mini = document.createElement('span');
      mini.className = 'cti-mini';
      mini.dataset.window = key;
      mini.innerHTML = '<span></span><span data-value></span><progress max="100"></progress>';
      compact.append(mini);
      const row = document.createElement('div');
      row.className = 'cti-quota-row';
      row.dataset.window = key;
      row.innerHTML = '<span></span><strong data-value></strong><progress max="100"></progress><span class="cti-reset"></span>';
      panel.append(row);
    }
    for (const kind of ['status', 'credits']) {
      const note = document.createElement('div');
      note.className = 'cti-quota-note';
      note.dataset.note = kind;
      panel.append(note);
    }
  }
  for (const key of ['5h', '7d']) {
    const windowQuota = quota?.windows?.[key];
    const value = windowQuota?.usedPercent;
    const valid = typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= 100;
    for (const row of root.querySelectorAll(`[data-window="${key}"]`)) {
      quotaText(row.firstElementChild, key.toUpperCase());
      quotaText(row.querySelector('[data-value]'), valid ? `${Math.round(value)}%${stale ? ' · !' : ''}` : '—');
      const progress = row.querySelector('progress');
      if (valid) progress.value = value;
      else progress.removeAttribute('value');
      progress.setAttribute('aria-label', `${key.toUpperCase()} ${valid ? value + '% ' + (zh ? '已使用' : 'used') : unavailable}`);
      progress.style.setProperty('--cti-fill', value >= 90 ? '#ce625b' : value >= 70 ? '#bd8b32' : '#39877a');
      const reset = row.querySelector('.cti-reset');
      if (reset) {
        const at = windowQuota?.resetsAt;
        let text = unavailable;
        if (valid && typeof at === 'number' && Number.isFinite(at) && at > 0) {
          const seconds = Math.ceil(at - Date.now()/1000);
          text = seconds <= 0 ? (zh ? '等待更新' : 'Awaiting refresh') :
            `${zh ? '重置' : 'Reset'} ${new Date(at*1000).toLocaleString()} · ${Math.floor(seconds/3600)}h ${Math.floor(seconds%3600/60)}m ${seconds%60}s`;
        }
        quotaText(reset, text);
      }
    }
  }
  const status = quota?.error || !quota?.observedAt ? unavailable : stale ? (zh ? '資料已過期，等待更新' : 'Stale · awaiting update') : (zh ? 'Codex 額度 · 已使用' : 'Codex quota · used');
  quotaText(panel.querySelector('[data-note="status"]'), status);
  compact.title = status;
  const credits = quota?.credits;
  const creditsText = credits?.unlimited ? (zh ? 'Credits：不限' : 'Credits: unlimited') : typeof credits?.balance === 'string' ? `Credits: ${credits.balance}` : '';
  quotaText(panel.querySelector('[data-note="credits"]'), creditsText);
  layoutQuotaHud(root);
}

function layoutQuotaHud(root) {
  if (root.hasAttribute('data-dragging')) return;
  // Find actual unoccupied titlebar space; never assume a fixed Share-button offset.
  let gap = null;
  const headers = [...document.querySelectorAll('header')].filter(header => {
    const r = header.getBoundingClientRect();
    return r.top >= 0 && r.top <= 4 && r.height >= 25 && r.height <= 70 && r.width > 280;
  });
  const occupied = [];
  for (const header of headers) {
    for (const element of header.querySelectorAll('button,[role="button"],a')) {
      const r = element.getBoundingClientRect();
      if (r.width && r.height && getComputedStyle(element).visibility !== 'hidden') occupied.push([r.left-10, r.right+10]);
    }
    const walker = document.createTreeWalker(header, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
      if (!walker.currentNode.textContent.trim()) continue;
      const range = document.createRange();
      range.selectNodeContents(walker.currentNode);
      const r = range.getBoundingClientRect();
      if (r.width && r.height) occupied.push([r.left-10, r.right+10]);
    }
  }
  if (headers.length) {
    const bounds = headers[0].getBoundingClientRect();
    occupied.sort((a,b) => a[0]-b[0]);
    let left = Math.max(90, bounds.left+8);
    for (const [start,end] of [...occupied, [bounds.right-8,bounds.right]]) {
      if (start-left >= 280 && (!gap || start-left > gap.right-gap.left)) gap = { left, right:start, bottom:bounds.bottom, top:bounds.top };
      left = Math.max(left,end);
    }
  }
  const collapsed = root.getAttribute('data-collapsed') === 'true';
  if (collapsed) root.__ctiFloating = false;
  if (!collapsed && root.__ctiFloating) gap = null;
  if (gap) {
    root.setAttribute('data-docked', 'true');
    root.style.left = `${Math.max(8, Math.min(gap.right-root.offsetWidth, innerWidth-root.offsetWidth-8))}px`;
    root.style.top = `${collapsed ? gap.top + Math.max(0,(gap.bottom-gap.top-root.offsetHeight)/2) : gap.bottom+8}px`;
    root.style.right = 'auto';
    root.style.bottom = 'auto';
  } else {
    if (root.getAttribute('data-docked') === 'true') {
      root.style.left = '';
      root.style.top = '';
      root.style.right = '8px';
      root.style.bottom = '8px';
    }
    root.setAttribute('data-docked', 'false');
    const r = root.getBoundingClientRect();
    if (r.left < 0 || r.right > innerWidth || r.top < 0 || r.bottom > innerHeight) {
      root.style.left = `${Math.max(8,Math.min(r.left,innerWidth-r.width-8))}px`;
      root.style.top = `${Math.max(8,Math.min(r.top,innerHeight-r.height-8))}px`;
      root.style.right = 'auto';
      root.style.bottom = 'auto';
    }
  }
}
