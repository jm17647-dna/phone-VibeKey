// 候选地址故障切换测试：主地址连不上时，自动换二维码里带的备用地址
import fs from 'node:fs';
import vm from 'node:vm';

const els = new Map();
function el(id) {
  if (!els.has(id)) {
    els.set(id, {
      id, value: '', textContent: '', className: '', innerHTML: '', dataset: {},
      handlers: {}, style: {}, classList: { add() {}, remove() {} },
      addEventListener(type, fn) { (this.handlers[type] ||= []).push(fn); },
      fire(type, ev = {}) { (this.handlers[type] || []).forEach((fn) => fn(ev)); },
      appendChild() {}, append() {}, focus() {}, setSelectionRange() {},
      closest() { return null; }, scrollTop: 0, scrollHeight: 0,
      childNodes: [], removeChild() {},
    });
  }
  return els.get(id);
}

const GOOD = 'http://192.168.1.99:8765';
const tried = [];
class WS {
  static OPEN = 1;
  constructor(url) {
    this.url = url;
    this.readyState = 1;
    tried.push(url);
    const good = url.includes('192.168.1.99');
    setTimeout(() => {
      if (good) {
        this.onopen && this.onopen();
        setTimeout(() => this.onmessage && this.onmessage({ data: JSON.stringify({ type: 'welcome', connected: 1 }) }), 30);
      } else {
        this.readyState = 3;
        this.onclose && this.onclose();
      }
    }, 20);
  }
  send() {}
  close() { this.readyState = 3; }
}

const store = new Map();
globalThis.localStorage = {
  getItem: (k) => (store.has(k) ? store.get(k) : null),
  setItem: (k, v) => store.set(k, String(v)),
  removeItem: (k) => store.delete(k),
};
globalThis.window = globalThis.window || { addEventListener() {} };
const alt = JSON.stringify([GOOD]);
globalThis.location = {
  search: '?t=tok123&debug=0&e=' + encodeURIComponent(alt),
  host: '192.168.1.3:8765',
  protocol: 'http:',
  origin: 'http://192.168.1.3:8765',
};
globalThis.WebSocket = WS;
globalThis.document = {
  getElementById: el, addEventListener() {},
  createElement: () => el('tmp-' + Math.random()),
  body: { appendChild() {} },
};
globalThis.confirm = () => false;

const code = fs.readFileSync(new URL('./app.js', import.meta.url), 'utf8');
vm.runInThisContext(code, { filename: 'app.js' });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
await sleep(4500);

const saved = JSON.parse(store.get('vb_endpoints') || '[]');
console.log('tried urls:', tried.map((u) => u.replace(/\/ws\?.*/, '')));
console.log('connected to alt:', tried.some((u) => u.includes('192.168.1.99')));
console.log('saved first endpoint:', saved[0] && saved[0].u);
console.log('status:', el('status').textContent);
const pass = tried.some((u) => u.includes('192.168.1.3'))
  && tried.some((u) => u.includes('192.168.1.99'))
  && saved[0] && saved[0].u === GOOD
  && el('status').textContent === '已连接';
console.log('RESULT', pass ? 'PASS' : 'FAIL');
process.exit(pass ? 0 : 1);
