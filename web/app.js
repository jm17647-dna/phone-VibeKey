(() => {
  const box = document.getElementById('box');
  const statusEl = document.getElementById('status');
  const historyEl = document.getElementById('history');
  const historyWrap = document.getElementById('historyWrap');
  const toastEl = document.getElementById('toast');
  const btnSend = document.getElementById('send');
  const btnEnter = document.getElementById('enter');
  const btnClear = document.getElementById('clear');
  const btnClearAll = document.getElementById('clearAll');
  const hintEl = document.getElementById('hint');

  const HISTORY_KEY = 'vb_history';
  const TOKEN_KEY = 'vb_token';
  const MAX_HISTORY = 10;
  const QUIET_MIN = 700;
  const QUIET_MAX = 1200;
  const QUIET_DEFAULT = 700;
  const SESSION_IDLE_MS = 4500;
  const FINAL_DELAY_MS = 150;

  const EP_KEY = 'vb_endpoints';

  const params = new URLSearchParams(location.search);
  const urlToken = params.get('t');
  if (urlToken) localStorage.setItem(TOKEN_KEY, urlToken);
  const token = localStorage.getItem(TOKEN_KEY) || '';

  const origin = location.origin || (location.protocol + '//' + location.host);

  // 候选地址：同一台电脑可能有多张网卡（有线/WiFi/手机热点），按顺序试，哪个通就用哪个
  function loadEps() {
    try {
      const raw = JSON.parse(localStorage.getItem(EP_KEY) || '[]');
      return Array.isArray(raw) ? raw.filter((x) => x && x.u) : [];
    } catch (err) {
      return [];
    }
  }

  function saveEps(list) {
    localStorage.setItem(EP_KEY, JSON.stringify(list.slice(0, 12)));
  }

  // 二维码里带 e=<JSON 数组>：扫一次就把所有候选地址记下来，换网后自动换一条试
  const eParam = params.get('e');
  if (eParam) {
    try {
      const urls = JSON.parse(eParam);
      if (Array.isArray(urls) && urls.length) {
        const merged = [{ u: origin }].concat(urls.map((u) => ({ u })));
        const seen = {};
        saveEps(merged.filter((x) => {
          if (seen[x.u]) return false;
          seen[x.u] = 1;
          return true;
        }));
      }
    } catch (err) {}
  }
  if (!loadEps().length && urlToken) saveEps([{ u: origin }]);
  let eps = loadEps();
  let epIdx = 0;
  let epFails = 0;
  let openTimer = null;

  function epWsUrl(ep) {
    const u = String(ep.u || '');
    const base = u.replace(/^http:/, 'ws:').replace(/^https:/, 'wss:').replace(/\/+$/, '');
    return base + '/ws?t=' + encodeURIComponent(token);
  }

  function bumpEp() {
    epFails += 1;
    if (eps.length > 1 && epFails >= 2) {
      epFails = 0;
      epIdx = (epIdx + 1) % eps.length;
      dbg('ep.switch', eps[epIdx].u);
    }
  }

  function manualEndpoint() {
    const cur = (loadEps()[0] || {}).u || origin;
    const v = prompt('电脑地址（形如 192.168.1.3:8765）', cur.replace(/^https?:\/\//, ''));
    if (!v) return;
    const u = /^https?:\/\//.test(v) ? v : 'http://' + v;
    saveEps([{ u }].concat(loadEps()));
    eps = loadEps();
    epIdx = 0;
    epFails = 0;
    retry = 0;
    connect();
  }

  function showManualHint() {
    hintEl.textContent = '没连上电脑 · 点这里手动填地址';
    if (hintEl.style) hintEl.style.cursor = 'pointer';
    hintEl.onclick = manualEndpoint;
  }

  const DEBUG = params.get('debug') === '1';
  let dbgEl = null;

  function dbg(tag, detail) {
    if (!DEBUG) return;
    if (!dbgEl) {
      dbgEl = document.createElement('div');
      dbgEl.id = 'dbg';
      dbgEl.style.cssText =
        'position:fixed;left:0;right:0;bottom:0;max-height:40vh;overflow:auto;' +
        'background:rgba(8,12,20,.94);border-top:1px solid #2a3a55;' +
        'font:11px/1.5 ui-monospace,Consolas,monospace;color:#cfe3ff;' +
        'padding:6px 8px;z-index:99;white-space:pre-wrap;';
      document.body.appendChild(dbgEl);
    }
    const d = new Date();
    const pad = (n, w) => String(n).padStart(w, '0');
    const ts = pad(d.getMinutes(), 2) + ':' + pad(d.getSeconds(), 2) + '.' + pad(d.getMilliseconds(), 3);
    const line = document.createElement('div');
    line.textContent = ts + ' ' + tag + ' ' + (detail == null ? '' : String(detail));
    dbgEl.appendChild(line);
    while (dbgEl.childNodes.length > 200) dbgEl.removeChild(dbgEl.firstChild);
    dbgEl.scrollTop = dbgEl.scrollHeight;
  }

  let ws = null;
  let connected = false;
  let retry = 0;
  let retryTimer = null;
  let composing = false;
  let quietTimer = null;
  let lastSentText = null;
  let lastSentFull = null;
  let gaps = [];
  let lastGrowTs = 0;
  let lastLen = 0;
  let sessionActive = false;
  let lastEditTs = 0;
  let editingId = null;
  let toastTimer = null;



  function setStatus(kind, text) {
    statusEl.textContent = text;
    statusEl.className = 'pill ' + kind;
  }

  function toast(msg, bad) {
    toastEl.textContent = msg;
    toastEl.className = 'toast' + (bad ? ' bad' : '');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toastEl.classList.add('hidden'), 1800);
  }

  function connect() {
    clearTimeout(retryTimer);
    clearTimeout(openTimer);
    if (!token) {
      setStatus('off', '未配对');
      return;
    }
    eps = loadEps();
    if (!eps.length) {
      setStatus('off', '未配对');
      showManualHint();
      return;
    }
    const ep = eps[epIdx % eps.length];
    setStatus('wait', '连接中…');
    try {
      ws = new WebSocket(epWsUrl(ep));
    } catch (err) {
      scheduleRetry();
      return;
    }
    // 4 秒还没握手就换下一个候选地址（局域网里连不通通常立刻失败，这里兜住黑洞）
    openTimer = setTimeout(() => {
      if (!connected && ws && ws.readyState !== WebSocket.OPEN) {
        try { ws.close(); } catch (err) {}
      }
    }, 4000);
    ws.onopen = () => {
      clearTimeout(openTimer);
      dbg('ws.open', ep.u);
      ws.send(JSON.stringify({ type: 'hello', token }));
    };
    ws.onmessage = (ev) => {
      let data;
      try { data = JSON.parse(ev.data); } catch (err) { return; }
      if (data.type === 'welcome') {
        connected = true;
        retry = 0;
        epFails = 0;
        hintEl.onclick = null;
        if (hintEl.style) hintEl.style.cursor = '';
        // 把这次连通的地址挪到最前，下次优先用
        const good = eps[epIdx % eps.length];
        const rest = eps.filter((x) => x.u !== good.u);
        saveEps([good].concat(rest));
        eps = loadEps();
        epIdx = 0;
        setStatus('ok', '已连接');
      } else if (data.type === 'ack') {
        dbg('ack', JSON.stringify(data));
        if (data.kind === 'key') {
          toast(data.ok ? '已回车' : '回车失败：' + (data.reason || '未知'), !data.ok);
        } else if (data.kind === 'clear') {
          if (data.ok) {
            // 电脑上的字清掉了，手机这边同步清空，避免下次又把整段重贴一遍
            box.value = '';
            lastSentText = null;
            lastSentFull = null;
            sessionActive = false;
            lastLen = 0;
            lastGrowTs = 0;
            gaps = [];
          }
          if (data.ok) toast('已清空电脑输入框');
          else toast(data.reason === 'nothing-to-clear' ? '电脑输入框本来就是空的' : '清空失败', true);
        } else if (data.ok && data.pasted === false) {
          hintEl.textContent = '电脑上没有输入框 · 已放进剪贴板';
          toast('电脑上没有输入框，文字已放进剪贴板', true);
          restoreText();
          lastSentText = null;
          sessionActive = false;
        } else if (data.ok) {
          hintEl.textContent = `已送达 · ${lastSentText ? lastSentText.length : 0} 字`;
        } else {
          restoreText();
          hintEl.textContent = '发送失败：' + (data.reason || '未知原因');
          toast(data.reason === 'empty' ? '没有内容' : '电脑端没粘上', true);
        }
      } else if (data.type === 'error') {
        if (data.reason === 'bad-token') {
          connected = false;
          setStatus('off', '配对失效');
          toast('配对失效，请在电脑上重新扫码', true);
        }
      }
    };
    ws.onclose = () => {
      clearTimeout(openTimer);
      dbg('ws.close', ep.u);
      connected = false;
      setStatus('off', '未连接');
      bumpEp();
      if (retry >= 2) showManualHint();
      scheduleRetry();
    };
    ws.onerror = () => {};
  }

  function scheduleRetry() {
    clearTimeout(retryTimer);
    const delay = Math.min(3000, 400 * Math.pow(2, retry));
    retry = Math.min(retry + 1, 5);
    retryTimer = setTimeout(connect, delay);
  }

  function pressEnter() {
    if (!connected || !ws || ws.readyState !== WebSocket.OPEN) {
      toast('还没连上电脑', true);
      return;
    }
    dbg('key', 'enter');
    ws.send(JSON.stringify({ type: 'key', key: 'enter' }));
  }

  function sendNow(final) {
    clearTimeout(quietTimer);
    quietTimer = null;
    const text = box.value.trim();
    if (!text) return;
    if (!connected || !ws || ws.readyState !== WebSocket.OPEN) {
      toast('还没连上电脑，稍后再试', true);
      return;
    }
    let payload = text;
    let replace = false;
    if (sessionActive && lastSentText !== null) {
      if (text === lastSentText) {
        if (final) finishSession(text);
        return;
      }
      if (text.startsWith(lastSentText)) {
        // 输入法在原文后面接着长：只把新增的那一截发过去，电脑端直接续写
        payload = text.slice(lastSentText.length).trim();
      } else {
        // 前面的内容被改短/改错：整体替换（电脑端退格掉这一段再重贴）
        replace = true;
      }
    }
    if (!payload) {
      if (final) finishSession(text);
      return;
    }
    dbg('send', JSON.stringify({ replace, len: payload.length, text: payload.slice(0, 40) }));
    ws.send(JSON.stringify({ type: 'text', text: payload, replace }));
    lastSentText = text;
    lastSentFull = text;
    sessionActive = true;
    lastEditTs = Date.now();
    hintEl.textContent = (replace ? '更新中 · ' : '发送中 · ') + text.length + ' 字';
    if (final) finishSession(text);
  }

  // 发送失败/没落到电脑时，把刚才那段字还给输入框，等用户再发一次
  function restoreText() {
    if (box.value.trim()) return;
    if (!lastSentFull) return;
    box.value = lastSentFull;
    lastLen = box.value.length;
    lastGrowTs = 0;
    dbg('restore', box.value.slice(0, 20));
  }

  function clearPc() {
    if (!connected || !ws || ws.readyState !== WebSocket.OPEN) {
      toast('还没连上电脑', true);
      return;
    }
    dbg('clear', box.value.length);
    ws.send(JSON.stringify({ type: 'clear' }));
  }

  function finishSession(text) {
    dbg('finish', text ? text.slice(0, 30) : '');
    if (text) saveHistory(text);
    box.value = '';
    lastLen = 0;
    lastGrowTs = 0;
    gaps = [];
    lastSentText = null;
    sessionActive = false;
    box.focus();
  }

  function quietBudget() {
    if (gaps.length < 2) return QUIET_DEFAULT;
    const sorted = gaps.slice().sort((a, b) => a - b);
    const med = sorted[Math.floor(sorted.length / 2)];
    return Math.max(QUIET_MIN, Math.min(QUIET_MAX, Math.round(med * 2.5)));
  }

  function schedule() {
    const now = Date.now();
    const grew = box.value.length > lastLen;
    lastLen = box.value.length;
    if (grew && lastGrowTs) {
      const gap = now - lastGrowTs;
      if (gap > 80 && gap < 3000) {
        gaps.push(gap);
        if (gaps.length > 8) gaps.shift();
      }
    }
    if (grew) lastGrowTs = now;
    lastEditTs = now;
    if (composing) {
      dbg('input.skip', 'composing len=' + box.value.length);
      return;
    }
    const ms = quietBudget();
    clearTimeout(quietTimer);
    quietTimer = setTimeout(() => sendNow(false), ms);
    dbg('debounce', ms + 'ms len=' + box.value.length + ' gaps=' + gaps.join(','));
  }

  box.addEventListener('compositionstart', () => {
    dbg('comp.start', '');
    composing = true;
    lastEditTs = Date.now();
    clearTimeout(quietTimer);
  });
  box.addEventListener('compositionend', () => {
    dbg('comp.end', box.value.slice(-24));
    composing = false;
    lastEditTs = Date.now();
    clearTimeout(quietTimer);
    quietTimer = setTimeout(() => sendNow(false), FINAL_DELAY_MS);
  });
  let shiftDown = false;
  box.addEventListener('keydown', (ev) => {
    if (ev.key === 'Shift') shiftDown = true;
    if (ev.key === 'Enter' && !ev.shiftKey && !composing) {
      ev.preventDefault();
      dbg('enter', 'keydown');
      pressEnter();
    }
  });
  box.addEventListener('keyup', (ev) => {
    if (ev.key === 'Shift') shiftDown = false;
  });
  // 软键盘/输入法的回车往往不走 keydown，而是 insertLineBreak；拦掉它改成发送
  box.addEventListener('beforeinput', (ev) => {
    const type = ev.inputType || '';
    const isBreak = type === 'insertLineBreak' || type === 'insertParagraph'
      || (type === 'insertText' && (ev.data === '\n' || ev.data === '\r'));
    if (!isBreak) return;
    if (ev.shiftKey) return;
    ev.preventDefault();
    dbg('enter', 'beforeinput:' + type);
    pressEnter();
  });
  box.addEventListener('input', () => {
    if (!shiftDown && box.value.indexOf('\n') !== -1) {
      box.value = box.value.replace(/\n+/g, ' ').replace(/ {2,}/g, ' ');
    }
    schedule();
  });
  if (btnSend) btnSend.addEventListener('click', () => sendNow(true));
  if (btnEnter) btnEnter.addEventListener('click', () => pressEnter());
  btnClear.addEventListener('click', () => {
    clearPc();
    editingId = null;
  });

  setInterval(() => {
    if (!sessionActive || composing) return;
    const text = box.value.trim();
    if (!text || text !== lastSentText) return;
    if (Date.now() - lastEditTs < SESSION_IDLE_MS) return;
    finishSession(text);
  }, 500);

  function loadHistory() {
    try {
      const raw = JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]');
      return Array.isArray(raw) ? raw : [];
    } catch (err) {
      return [];
    }
  }

  function persist(list) {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(list.slice(0, MAX_HISTORY)));
    render();
  }

  function saveHistory(text) {
    const list = loadHistory();
    if (editingId) {
      const idx = list.findIndex((item) => item.id === editingId);
      if (idx >= 0) {
        list[idx].text = text;
        list[idx].ts = Date.now();
      } else {
        list.unshift({ id: newId(), text, ts: Date.now() });
      }
      editingId = null;
    } else {
      list.unshift({ id: newId(), text, ts: Date.now() });
    }
    persist(list);
  }

  function newId() {
    return Date.now().toString(36) + Math.random().toString(16).slice(2, 6);
  }

  function fmtTime(ts) {
    const d = new Date(ts);
    const pad = (n) => String(n).padStart(2, '0');
    return `${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }

  function render() {
    const list = loadHistory();
    historyEl.innerHTML = '';
    if (!list.length) {
      historyWrap.classList.add('hidden');
      return;
    }
    historyWrap.classList.remove('hidden');
    list.forEach((item) => {
      const li = document.createElement('li');
      const p = document.createElement('p');
      p.textContent = item.text;
      const meta = document.createElement('div');
      meta.className = 'meta';
      const time = document.createElement('span');
      time.textContent = fmtTime(item.ts);
      const ops = document.createElement('div');
      ops.className = 'ops';
      const edit = document.createElement('span');
      edit.textContent = '编辑';
      edit.dataset.act = 'edit';
      const del = document.createElement('span');
      del.textContent = '删除';
      del.dataset.act = 'del';
      del.className = 'del';
      ops.append(edit, del);
      meta.append(time, ops);
      li.append(p, meta);
      li.dataset.id = item.id;
      historyEl.appendChild(li);
    });
  }

  historyEl.addEventListener('click', (ev) => {
    const act = ev.target.dataset && ev.target.dataset.act;
    if (!act) return;
    const li = ev.target.closest('li');
    const id = li && li.dataset.id;
    if (!id) return;
    const list = loadHistory();
    const item = list.find((x) => x.id === id);
    if (!item) return;
    if (act === 'edit') {
      box.value = item.text;
      editingId = id;
      lastSentText = null;
      sessionActive = false;
      box.focus();
      box.setSelectionRange(item.text.length, item.text.length);
    } else if (act === 'del') {
      persist(list.filter((x) => x.id !== id));
    }
  });

  btnClearAll.addEventListener('click', () => {
    if (!loadHistory().length) return;
    if (confirm('清空全部记录？此操作不可恢复。')) {
      persist([]);
    }
  });



  document.addEventListener('visibilitychange', () => {
    dbg('visibility', document.hidden ? 'hidden' : 'visible');
    if (!document.hidden && !connected) {
      retry = 0;
      connect();
    }
  });

  setInterval(() => {
    if (connected && ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'ping' }));
    }
  }, 15000);

  window.addEventListener('online', () => {
    dbg('net.online', '');
    retry = 0;
    epFails = 0;
    clearTimeout(retryTimer);
    connect();
  });
  window.addEventListener('offline', () => dbg('net.offline', ''));

  render();
  connect();
  setTimeout(() => box.focus(), 150);
})();
