import fs from 'node:fs';
import vm from 'node:vm';

const els = new Map();
function el(id) {
  if (!els.has(id)) {
    els.set(id, {
      id,
      value: '',
      textContent: '',
      className: '',
      innerHTML: '',
      dataset: {},
      handlers: {},
      classList: { add() {}, remove() {} },
      addEventListener(type, fn) { (this.handlers[type] ||= []).push(fn); },
      fire(type, ev = {}) { (this.handlers[type] || []).forEach((fn) => fn(ev)); },
      appendChild() {},
      append() {},
      focus() {},
      setSelectionRange() {},
      closest() { return null; },
      scrollTop: 0,
      scrollHeight: 0,
      childNodes: [],
      removeChild() {},
    });
  }
  return els.get(id);
}

const sent = [];
const wsInstances = [];
class WS {
  static OPEN = 1;
  constructor(url) {
    this.url = url;
    this.readyState = 1;
    wsInstances.push(this);
    setTimeout(() => this.onopen && this.onopen(), 0);
  }
  send(data) { sent.push(JSON.parse(data)); }
  close() { this.readyState = 3; }
}

const store = new Map();
globalThis.localStorage = {
  getItem: (k) => (store.has(k) ? store.get(k) : null),
  setItem: (k, v) => store.set(k, String(v)),
  removeItem: (k) => store.delete(k),
};
globalThis.window = globalThis.window || { addEventListener() {} };
globalThis.location = { search: '?t=tok123&debug=0', host: '127.0.0.1:8799', protocol: 'http:', origin: 'http://127.0.0.1:8799' };
globalThis.WebSocket = WS;
globalThis.document = {
  getElementById: el,
  addEventListener() {},
  createElement: () => el('tmp-' + Math.random()),
  body: { appendChild() {} },
};
globalThis.confirm = () => false;

const code = fs.readFileSync(new URL('./app.js', import.meta.url), 'utf8');
vm.runInThisContext(code, { filename: 'app.js' });

const box = el('box');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

await sleep(10);
const ws = wsInstances[0];
ws.onmessage({ data: JSON.stringify({ type: 'welcome', connected: 1 }) });

// 1) 模拟逐字增长，观察第一次发送的时机
const chars = ['我', '我想', '我想约你', '我想约你明天', '我想约你明天下午三点'];
const t0 = Date.now();
for (let i = 0; i < chars.length; i += 1) {
  box.value = chars[i];
  box.fire('input', {});
  await sleep(120);
}
let firstSendAt = null;
const watch = setInterval(() => {
  if (firstSendAt === null && sent.some((x) => x.type === 'text')) firstSendAt = Date.now() - t0;
}, 10);
await sleep(1400);
clearInterval(watch);
const first = sent.find((x) => x.type === 'text');
console.log('first text payload:', JSON.stringify(first));
console.log('first send delay from start of typing (ms):', firstSendAt);

// 2) 继续增长 -> 应为 replace:true
box.value = '我想约你明天下午三点在楼下咖啡店见面';
box.fire('input', {});
await sleep(900);
const second = sent.filter((x) => x.type === 'text').at(-1);
console.log('second text payload:', JSON.stringify({ replace: second.replace, len: second.text.length }));

// 3) compositionend 应 150ms 内触发一次发送
sent.length = 0;
box.value = '我想约你明天下午三点在楼下咖啡店见面并带上资料';
box.fire('compositionstart', {});
box.fire('compositionend', {});
await sleep(320);
console.log('after comp.end sends:', sent.filter((x) => x.type === 'text').length,
  'replace:', sent.find((x) => x.type === 'text')?.replace);

// 4) 空闲 4.5s 后会话收尾，输入框清空
await sleep(5000);
console.log('box cleared after idle:', box.value === '');
console.log('hint:', el('hint').textContent);
process.exit(0);
