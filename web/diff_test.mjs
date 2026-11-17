import fs from 'node:fs';
import vm from 'node:vm';
const els = new Map();
function el(id) {
  if (!els.has(id)) els.set(id, {
    id, value: '', textContent: '', className: '', innerHTML: '', dataset: {},
    handlers: {},
    classList: { add() {}, remove() {} },
    addEventListener(t, f) { (this.handlers[t] ||= []).push(f); },
    fire(t, ev = {}) { (this.handlers[t] || []).forEach((f) => f(ev)); },
    appendChild() {}, append() {}, focus() {}, setSelectionRange() {},
    closest() { return null; }, scrollTop: 0, scrollHeight: 0, childNodes: [],
  });
  return els.get(id);
}
const sent = []; const sockets = [];
class WS { static OPEN = 1; constructor(u) { this.url = u; this.readyState = 1; sockets.push(this); setTimeout(() => this.onopen && this.onopen(), 0); } send(d) { sent.push(JSON.parse(d)); } close() {} }
const store = new Map();
globalThis.localStorage = { getItem: (k) => (store.get(k) ?? null), setItem: (k, v) => store.set(k, String(v)), removeItem: (k) => store.delete(k) };
globalThis.window = globalThis.window || { addEventListener() {} };
globalThis.location = { search: '?t=tok', host: 'h', protocol: 'http:' };
globalThis.WebSocket = WS;
globalThis.document = { getElementById: el, addEventListener() {}, createElement: () => el('x' + Math.random()), body: { appendChild() {} } };
globalThis.confirm = () => false;
vm.runInThisContext(fs.readFileSync(new URL('./app.js', import.meta.url), 'utf8'), { filename: 'app.js' });
const box = el('box');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
await sleep(10);
const ws = sockets[0];
ws.onmessage({ data: JSON.stringify({ type: 'welcome', connected: 1 }) });

// 1) 第一句
sent.length = 0;
box.value = '今天下午三点开会';
box.fire('input', {});
await sleep(1000);
let t = sent.filter((x) => x.type === 'text');
console.log('句1 发送:', JSON.stringify(t[0]), '| 发送后输入框仍有内容:', box.value === '今天下午三点开会');
ws.onmessage({ data: JSON.stringify({ type: 'ack', ok: true, reason: '' }) });

// 2) 间隔很短，第二句接在后面
box.value = '今天下午三点开会顺便带上资料';
box.fire('input', {});
await sleep(1000);
t = sent.filter((x) => x.type === 'text');
console.log('句2 发送:', JSON.stringify(t.at(-1)));

// 3) 内容被改短 -> 应走 replace
ws.onmessage({ data: JSON.stringify({ type: 'ack', ok: true, reason: '' }) });
box.value = '今天下午三点';
box.fire('input', {});
await sleep(1000);
t = sent.filter((x) => x.type === 'text');
console.log('改短后发送:', JSON.stringify(t.at(-1)));

// 4) 清空按钮 -> 发 clear
sent.length = 0;
el('clear').fire('click', {});
await sleep(50);
console.log('清空按钮发出:', JSON.stringify(sent.filter((x) => x.type === 'clear')));
ws.onmessage({ data: JSON.stringify({ type: 'ack', kind: 'clear', ok: true, reason: '', count: 5 }) });
await sleep(50);
console.log('清空提示:', JSON.stringify(el('toast').textContent));
process.exit(0);
