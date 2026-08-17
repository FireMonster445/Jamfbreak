"""
Embedded HTML/CSS/JS frontend for the Jamfbreak GUI.

Kept as a Python string (rather than a separate .html file) so the whole GUI
ships in two modules with no asset path issues. Loaded directly by pywebview
via `webview.create_window(html=...)`.

Design language: minimalist black & white.
  - Pure black canvas (#0A0A0A — true #000 looks flat on most panels)
  - Pure white type (#FAFAFA — slightly off-white for less retinal burn)
  - Hairline gray dividers (#1F1F1F / #2A2A2A)
  - One accent: the status dot (white when connected, dim when searching)
  - SF Pro Display-like system font stack (no web fonts needed)
  - All motion: cubic-bezier(0.32, 0.72, 0, 1) — the "Apple ease"
  - Console lines fade-in-from-top (translateY(-8px) + opacity 0 -> 0)
"""

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Jamfbreak</title>
<style>
  :root {
    --bg: #0A0A0A;
    --bg-elev: #111111;
    --bg-elev-2: #161616;
    --line: #1F1F1F;
    --line-strong: #2A2A2A;
    --text: #FAFAFA;
    --text-dim: #8A8A8A;
    --text-faint: #4A4A4A;
    --accent: #FAFAFA;
    --danger: #E5E5E5;
    --ease: cubic-bezier(0.32, 0.72, 0, 1);
    --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
    --font: -apple-system, "SF Pro Display", "Segoe UI", "Helvetica Neue", system-ui, sans-serif;
    --mono: "SF Mono", "JetBrains Mono", "Cascadia Mono", "Consolas", monospace;
  }

  * { margin: 0; padding: 0; box-sizing: border-box; }

  html, body {
    height: 100%;
    background: var(--bg);
    color: var(--text);
    font-family: var(--font);
    font-size: 14px;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    overflow: hidden;
    user-select: none;
  }

  body {
    display: flex;
    flex-direction: column;
    min-height: 100vh;
  }

  /* ---------- Top bar ---------- */
  .topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 20px 28px 0 28px;
    flex-shrink: 0;
  }
  .brand {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 13px;
    font-weight: 500;
    letter-spacing: -0.01em;
  }
  .brand-mark {
    width: 18px; height: 18px;
    border: 1.5px solid var(--text);
    border-radius: 5px;
    position: relative;
  }
  .brand-mark::after {
    content: "";
    position: absolute;
    inset: 4px;
    background: var(--text);
    border-radius: 1.5px;
    transition: transform 0.6s var(--ease);
  }
  .brand-text { color: var(--text); }
  .brand-text .dim { color: var(--text-faint); font-weight: 400; }

  .status-pill {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 14px 6px 12px;
    border: 1px solid var(--line-strong);
    border-radius: 999px;
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 0.02em;
    color: var(--text-dim);
    transition: all 0.5s var(--ease);
  }
  .status-pill.connected { color: #4ADE80; border-color: #4ADE80; }
  .status-pill.patching { color: var(--text); border-color: #3A3A3A; }
  .status-pill.success  { color: #4ADE80; border-color: #4ADE80; }
  .status-pill.error    { color: #FF6B6B; border-color: #FF6B6B; }

  .status-dot {
    width: 7px; height: 7px;
    border-radius: 50%;
    background: var(--text-faint);
    transition: background 0.4s var(--ease);
    position: relative;
  }
  .status-pill.searching .status-dot {
    background: var(--text-dim);
    animation: pulse 1.6s var(--ease) infinite;
  }
  .status-pill.connected .status-dot {
    background: #4ADE80;
    box-shadow: 0 0 8px rgba(74, 222, 128, 0.6);
  }
  .status-pill.patching  .status-dot { background: var(--text); animation: pulse 1.2s var(--ease) infinite; }
  .status-pill.success   .status-dot {
    background: #4ADE80;
    box-shadow: 0 0 8px rgba(74, 222, 128, 0.6);
  }
  .status-pill.error     .status-dot { background: #FF6B6B; }

  @keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50%      { opacity: 0.3; transform: scale(0.85); }
  }

  /* ---------- Hero ---------- */
  .hero {
    padding: 56px 28px 24px 28px;
    flex-shrink: 0;
    opacity: 0;
    transform: translateY(12px);
    animation: rise 0.9s var(--ease-out) 0.1s forwards;
  }
  @keyframes rise {
    to { opacity: 1; transform: translateY(0); }
  }
  .eyebrow {
    font-size: 10px;
    font-weight: 500;
    letter-spacing: 0.24em;
    text-transform: uppercase;
    color: var(--text-faint);
    margin-bottom: 14px;
  }
  .hero h1 {
    font-size: 34px;
    font-weight: 600;
    letter-spacing: -0.03em;
    line-height: 1.05;
    margin-bottom: 10px;
  }
  .hero h1 .light { color: var(--text-dim); font-weight: 300; }
  .hero p {
    color: var(--text-dim);
    font-size: 13px;
    line-height: 1.55;
    max-width: 460px;
  }

  /* ---------- Device panel ---------- */
  .device-panel {
    margin: 0 28px;
    border: 1px solid var(--line);
    border-radius: 16px;
    background: var(--bg-elev);
    overflow: hidden;
    opacity: 0;
    transform: translateY(20px);
    transition: opacity 0.7s var(--ease-out), transform 0.7s var(--ease-out);
  }
  .device-panel.visible {
    opacity: 1;
    transform: translateY(0);
  }
  .device-panel .panel-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 18px;
    border-bottom: 1px solid var(--line);
  }
  .panel-head .label {
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--text-faint);
  }
  .panel-head .device-name {
    font-size: 12px;
    color: var(--text-dim);
    font-variant-numeric: tabular-nums;
  }

  .info-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 1px;
    background: var(--line);
  }
  .info-cell {
    background: var(--bg-elev);
    padding: 14px 18px;
    transition: background 0.4s var(--ease);
  }
  .info-cell:hover { background: var(--bg-elev-2); }
  .info-cell .key {
    font-size: 10px;
    font-weight: 500;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--text-faint);
    margin-bottom: 6px;
  }
  .info-cell .val {
    font-size: 13px;
    font-family: var(--mono);
    color: var(--text);
    font-variant-numeric: tabular-nums;
    word-break: break-all;
  }
  .info-cell .val.empty { color: var(--text-faint); font-style: italic; font-family: var(--font); }

  /* Empty state when no device */
  .device-empty {
    padding: 36px 18px;
    text-align: center;
    color: var(--text-faint);
    font-size: 12px;
    line-height: 1.6;
  }
  .device-empty .icon {
    width: 28px; height: 28px;
    margin: 0 auto 14px;
    border: 1.5px solid var(--line-strong);
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    animation: breathe 2.4s var(--ease) infinite;
  }
  .device-empty .icon::after {
    content: "";
    width: 8px; height: 8px;
    border-radius: 50%;
    background: var(--text-faint);
  }
  @keyframes breathe {
    0%, 100% { transform: scale(1); opacity: 1; }
    50%      { transform: scale(0.95); opacity: 0.6; }
  }

  /* ---------- Action row ---------- */
  .actions {
    padding: 24px 28px 16px 28px;
    display: flex;
    gap: 12px;
    align-items: center;
    flex-shrink: 0;
  }
  .btn {
    appearance: none;
    border: none;
    cursor: pointer;
    font-family: var(--font);
    font-size: 13px;
    font-weight: 500;
    letter-spacing: -0.01em;
    padding: 12px 22px;
    border-radius: 999px;
    transition: transform 0.4s var(--ease), background 0.4s var(--ease), color 0.4s var(--ease), opacity 0.3s var(--ease);
    will-change: transform;
  }
  .btn:disabled { cursor: not-allowed; opacity: 0.35; }
  .btn-primary {
    background: var(--text);
    color: var(--bg);
  }
  .btn-primary:not(:disabled):hover { transform: scale(1.02); }
  .btn-primary:not(:disabled):active { transform: scale(0.98); }
  .btn-ghost {
    background: transparent;
    color: var(--text-dim);
    border: 1px solid var(--line-strong);
  }
  .btn-ghost:not(:disabled):hover { color: var(--text); border-color: #3A3A3A; transform: scale(1.02); }
  .btn-ghost:not(:disabled):active { transform: scale(0.98); }

  .actions .spacer { flex: 1; }
  .progress-track {
    flex: 1;
    height: 2px;
    background: var(--line);
    border-radius: 1px;
    overflow: hidden;
    opacity: 0;
    transition: opacity 0.4s var(--ease);
  }
  .progress-track.active { opacity: 1; }
  .progress-bar {
    height: 100%;
    width: 0%;
    background: var(--text);
    transition: width 0.6s var(--ease);
  }
  .progress-bar.indeterminate {
    width: 30%;
    animation: indet 1.4s var(--ease) infinite;
  }
  @keyframes indet {
    0%   { transform: translateX(-100%); }
    100% { transform: translateX(400%); }
  }

  /* ---------- Console ---------- */
  .console-wrap {
    flex: 1;
    margin: 0 28px 28px 28px;
    border: 1px solid var(--line);
    border-radius: 16px;
    background: var(--bg-elev);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    min-height: 0;
  }
  .console-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 18px;
    border-bottom: 1px solid var(--line);
    flex-shrink: 0;
  }
  .console-head .label {
    font-size: 10px;
    font-weight: 500;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--text-faint);
  }
  .console-head .dots { display: flex; gap: 6px; }
  .console-head .dots span {
    width: 7px; height: 7px; border-radius: 50%;
    background: var(--line-strong);
  }

  .console-body {
    flex: 1;
    overflow-y: auto;
    padding: 16px 18px;
    font-family: var(--mono);
    font-size: 12px;
    line-height: 1.7;
    color: var(--text-dim);
    scrollbar-width: thin;
    scrollbar-color: var(--line-strong) transparent;
  }
  .console-body::-webkit-scrollbar { width: 6px; }
  .console-body::-webkit-scrollbar-thumb { background: var(--line-strong); border-radius: 3px; }
  .console-body::-webkit-scrollbar-track { background: transparent; }

  .log-line {
    opacity: 0;
    transform: translateY(-8px);
    animation: logIn 0.5s var(--ease-out) forwards;
    padding: 1px 0;
    word-break: break-word;
    white-space: pre-wrap;
  }
  @keyframes logIn {
    from { opacity: 0; transform: translateY(-8px); }
    to   { opacity: 1; transform: translateY(0); }
  }
  .log-line .ts {
    color: var(--text-faint);
    font-size: 10px;
    margin-right: 10px;
    font-variant-numeric: tabular-nums;
  }
  .log-line .tag {
    display: inline-block;
    min-width: 42px;
    color: var(--text-faint);
    font-size: 10px;
    margin-right: 10px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }
  .log-line.info    { color: var(--text-dim); }
  .log-line.success { color: var(--text); }
  .log-line.error   { color: var(--text); }
  .log-line.error .tag { color: var(--text); }
  .log-line.success .tag { color: var(--text); }
  .log-line.step    { color: var(--text); font-weight: 500; }
  .log-line.step .tag { color: var(--text); }

  .console-empty {
    color: var(--text-faint);
    font-style: italic;
    font-family: var(--font);
    font-size: 12px;
    padding: 8px 0;
  }

  /* ---------- Footer note ---------- */
  .footer {
    padding: 0 28px 16px 28px;
    font-size: 10px;
    color: var(--text-faint);
    letter-spacing: 0.04em;
    flex-shrink: 0;
  }
  .footer .warn { color: var(--text-dim); }
</style>
</head>
<body>

  <div class="topbar">
    <div class="brand">
      <div class="brand-mark"></div>
      <div class="brand-text">Jamfbreak <span class="dim">/ Windows</span></div>
    </div>
    <div class="status-pill searching" id="statusPill">
      <span class="status-dot"></span>
      <span id="statusText">Searching…</span>
    </div>
  </div>

  <div class="hero">
    <div class="eyebrow">iOS · Supervised MDM Removal</div>
    <h1>Remove MDM profiles<br><span class="light">without losing your data.</span></h1>
    <p>For devices you legally own. No jailbreak, IPSW, or bootchain writes. This performs a real settings restore: safeguards reduce risk, but no device-modification tool can guarantee zero data loss or zero boot failure.</p>
  </div>

  <div class="device-panel" id="devicePanel">
    <div class="panel-head">
      <span class="label">Connected Device</span>
      <span class="device-name" id="deviceName">—</span>
    </div>
    <div id="deviceBody">
      <div class="device-empty">
        <div class="icon"></div>
        <div>Waiting for an iOS device on the Wi-Fi selection screen…</div>
      </div>
    </div>
  </div>

  <div class="actions">
    <button class="btn btn-ghost" id="refreshBtn">Refresh</button>
    <button class="btn btn-primary" id="patchBtn" disabled>Bypass</button>
    <div class="progress-track" id="progressTrack">
      <div class="progress-bar" id="progressBar"></div>
    </div>
  </div>

  <div class="console-wrap">
    <div class="console-head">
      <span class="label">Console</span>
      <div class="dots"><span></span><span></span><span></span></div>
    </div>
    <div class="console-body" id="consoleBody">
      <div class="console-empty">Output will appear here.</div>
    </div>
  </div>

  <div class="footer">
    <span class="warn">Use only on devices you own.</span> &nbsp;·&nbsp; This avoids firmware and bootchain writes, but it is still a real settings restore with non-zero risk.
  </div>

<script>
  // ---- State ----
  let lastLogIndex = 0;
  let isPatching = false;

  const statusPill   = document.getElementById('statusPill');
  const statusText   = document.getElementById('statusText');
  const devicePanel  = document.getElementById('devicePanel');
  const deviceName   = document.getElementById('deviceName');
  const deviceBody   = document.getElementById('deviceBody');
  const patchBtn     = document.getElementById('patchBtn');
  const refreshBtn   = document.getElementById('refreshBtn');
  const consoleBody  = document.getElementById('consoleBody');
  const progressTrack= document.getElementById('progressTrack');
  const progressBar  = document.getElementById('progressBar');
  // ---- Helpers ----
  function setStatus(state, text) {
    statusPill.className = 'status-pill ' + state;
    statusText.textContent = text;
  }

  function ts() {
    const d = new Date();
    const pad = n => n.toString().padStart(2, '0');
    return pad(d.getHours()) + ':' + pad(d.getMinutes()) + ':' + pad(d.getSeconds());
  }

  function log(text, kind, tag) {
    // Clear the empty placeholder on first log
    const empty = consoleBody.querySelector('.console-empty');
    if (empty) empty.remove();

    const line = document.createElement('div');
    line.className = 'log-line ' + (kind || 'info');
    const stamp = document.createElement('span');
    stamp.className = 'ts';
    stamp.textContent = ts();
    line.appendChild(stamp);
    if (tag) {
      const tagNode = document.createElement('span');
      tagNode.className = 'tag';
      tagNode.textContent = String(tag);
      line.appendChild(tagNode);
    }
    line.appendChild(document.createTextNode(String(text)));
    consoleBody.appendChild(line);
    // Auto-scroll to bottom
    consoleBody.scrollTop = consoleBody.scrollHeight;
  }

  function renderDeviceInfo(d) {
    deviceBody.replaceChildren();
    if (!d) {
      const empty = document.createElement('div');
      empty.className = 'device-empty';
      const icon = document.createElement('div');
      icon.className = 'icon';
      const message = document.createElement('div');
      message.textContent = 'Waiting for an iOS device on the Wi-Fi selection screen…';
      empty.append(icon, message);
      deviceBody.appendChild(empty);
      deviceName.textContent = '—';
      return;
    }
    deviceName.textContent = d.name || d.product_type || 'iOS Device';
    const rows = [
      ['Model',         d.product_type],
      ['Serial',        d.serial],
      ['UDID',          d.udid],
      ['IMEI',          d.imei || '(Wi-Fi only)'],
      ['iOS',           d.product_version],
      ['Build',         d.build_version],
      ['Activation',    d.activation_state],
      ['Device Name',   d.name]
    ];
    const grid = document.createElement('div');
    grid.className = 'info-grid';
    rows.forEach(([key, value]) => {
      const cell = document.createElement('div');
      cell.className = 'info-cell';
      const keyNode = document.createElement('div');
      keyNode.className = 'key';
      keyNode.textContent = key;
      const valueNode = document.createElement('div');
      valueNode.className = 'val' + (value ? '' : ' empty');
      valueNode.textContent = String(value || '—');
      cell.append(keyNode, valueNode);
      grid.appendChild(cell);
    });
    deviceBody.appendChild(grid);
  }

  function setProgress(active, indeterminate, pct) {
    if (active) {
      progressTrack.classList.add('active');
      if (indeterminate) {
        progressBar.classList.add('indeterminate');
        progressBar.style.width = '';
      } else {
        progressBar.classList.remove('indeterminate');
        progressBar.style.width = (pct || 0) + '%';
      }
    } else {
      progressTrack.classList.remove('active');
      progressBar.classList.remove('indeterminate');
      progressBar.style.width = '0%';
    }
  }

  // ---- Polling loop ----
  async function poll() {
    try {
      const state = await window.pywebview.api.get_state();
      if (!state) return;

      // Status pill
      setStatus(state.status, state.status_text);

      // Device info
      if (state.device) {
        if (!devicePanel.classList.contains('visible')) {
          devicePanel.classList.add('visible');
        }
        renderDeviceInfo(state.device);
        patchBtn.disabled = isPatching || state.status !== 'connected';
      } else {
        if (devicePanel.classList.contains('visible') && state.status === 'searching') {
          // keep panel visible but show empty state
        }
        renderDeviceInfo(null);
        patchBtn.disabled = true;
      }

      // New console lines
      if (state.logs && state.logs.length > lastLogIndex) {
        for (let i = lastLogIndex; i < state.logs.length; i++) {
          const l = state.logs[i];
          log(l.text, l.kind, l.tag);
        }
        lastLogIndex = state.logs.length;
      }

      // Progress
      if (state.status === 'patching') {
        setProgress(true, true);
      } else if (state.status === 'success') {
        setProgress(false);
      } else if (state.status === 'error') {
        setProgress(false);
      } else {
        setProgress(false);
      }
    } catch (e) {
      // pywebview bridge may not be ready yet
    }
  }

  setInterval(poll, 250);
  poll();

  // ---- Button handlers ----
  refreshBtn.addEventListener('click', async () => {
    refreshBtn.disabled = true;
    try { await window.pywebview.api.refresh(); } catch (e) {}
    setTimeout(() => { refreshBtn.disabled = false; }, 800);
  });

  patchBtn.addEventListener('click', async () => {
    if (isPatching) return;
    isPatching = true;
    patchBtn.disabled = true;
    refreshBtn.disabled = true;
    patchBtn.textContent = 'Bypassing…';
    try {
      const result = await window.pywebview.api.start_bypass();
      patchBtn.textContent = result && result.success ? 'Done' : 'Bypass';
    } catch (e) {
      patchBtn.textContent = 'Bypass';
    }
    isPatching = false;
    refreshBtn.disabled = false;
    // Re-enable the button only if the device remains connected.
    setTimeout(() => {
      window.pywebview.api.get_state().then(s => {
        if (s && s.status === 'connected') {
          patchBtn.disabled = false;
          patchBtn.textContent = 'Bypass';
        }
      });
    }, 600);
  });
</script>
</body>
</html>
"""
