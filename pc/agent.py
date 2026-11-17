"""phone-VibeKey PC 端：局域网 HTTP + WebSocket 服务 + 托盘常驻。

手机页面 POST 上来的整段文字，通过「写剪贴板 + Ctrl+V」落到当前焦点窗口。
"""
from __future__ import annotations

import asyncio
import json
import os
import secrets
import hashlib
import socket
import subprocess
import sys
from urllib.parse import quote
import threading
import time
from pathlib import Path

from aiohttp import WSMsgType, web

APP_DIR = Path(__file__).resolve().parent
WEB_DIR = APP_DIR.parent / "web"
CONFIG_DIR = Path(os.environ.get("APPDATA") or Path.home()) / "phone-VibeKey"
CONFIG_FILE = CONFIG_DIR / "config.json"
DEFAULT_PORT = 8765
APP_NAME = "phone-VibeKey"
APP_VERSION = "0.7.6"

sys.path.insert(0, str(APP_DIR))
import inject as injector  # noqa: E402


def _build_id() -> str:
    h = hashlib.sha1()
    for name in ("index.html", "app.js", "style.css"):
        f = WEB_DIR / name
        try:
            h.update(f.read_bytes())
        except OSError:
            h.update(b"?")
    return h.hexdigest()[:7]


def _lan_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("192.168.1.1", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def _all_ips() -> list:
    ips = []
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith("127.") and ip not in ips:
                ips.append(ip)
    except OSError:
        pass
    primary = _lan_ip()
    if primary.startswith("127.") and ips:
        primary = ips[0]
    if primary not in ips:
        ips.insert(0, primary)
    return ips


def load_config() -> dict:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    cfg = {}
    if CONFIG_FILE.exists():
        try:
            cfg = json.loads(CONFIG_FILE.read_text("utf-8"))
        except (OSError, ValueError):
            cfg = {}
    if not cfg.get("token"):
        cfg["token"] = secrets.token_hex(16)
    if not cfg.get("port"):
        cfg["port"] = DEFAULT_PORT
    save_config(cfg)
    return cfg


def save_config(cfg: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), "utf-8")


class Hub:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.token = cfg["token"]
        self.clients = set()
        self.last_text = ""
        self.last_len = 0
        self.last_hwnd = 0
        self.last_ts = 0.0
        # 自上次「输入框被我们写脏」以来，往当前焦点窗口里累计插入了多少个字符
        self.chain_len = 0
        self.chain_hwnd = 0
        self.chain_ts = 0.0
        self.on_state = lambda connected: None

    @property
    def connected(self) -> int:
        return len(self.clients)

    def url_for(self, ip: str) -> str:
        return f"http://{ip}:{self.cfg['port']}/?t={self.token}"

    def primary_url(self) -> str:
        return self.url_for(_lan_ip())

    def pair_url(self) -> str:
        """二维码/复制用的地址：主地址 + e=备用地址列表，扫一次记住全部候选。"""
        primary = self.primary_url()
        alts = [u for u in self.endpoints() if u != primary]
        if alts:
            primary += "&e=" + quote(json.dumps(alts), safe="")
        return primary

    def endpoints(self) -> list:
        """所有可用的配对地址，主地址排最前（多网卡：有线/WiFi/热点各一个）。"""
        primary = _lan_ip()
        ips = [primary] + [ip for ip in _all_ips() if ip != primary]
        return [self.url_for(ip) for ip in ips]


HUB: Hub | None = None


def _no_cache(resp: web.StreamResponse) -> web.StreamResponse:
    resp.headers["Cache-Control"] = "no-store"
    return resp


async def handle_index(request: web.Request) -> web.Response:
    page = (WEB_DIR / "index.html").read_text("utf-8")
    page = page.replace("{{VERSION}}", APP_VERSION).replace("{{BUILD}}", _build_id())
    return _no_cache(
        web.Response(text=page, content_type="text/html", charset="utf-8")
    )


async def handle_static(request: web.Request) -> web.StreamResponse:
    name = request.match_info["name"]
    target = (WEB_DIR / name).resolve()
    if WEB_DIR.resolve() not in target.parents and target.parent != WEB_DIR.resolve():
        raise web.HTTPNotFound()
    if not target.is_file():
        raise web.HTTPNotFound()
    return _no_cache(web.FileResponse(target))


async def handle_info(request: web.Request) -> web.Response:
    assert HUB is not None
    return web.json_response(
        {
            "host": socket.gethostname(),
            "ips": _all_ips(),
            "port": HUB.cfg["port"],
            "connected": HUB.connected,
            "endpoints": HUB.endpoints(),
            "pair": HUB.pair_url(),
            "version": APP_VERSION,
            "build": _build_id(),
        }
    )


async def handle_ws(request: web.Request) -> web.StreamResponse:
    assert HUB is not None
    ws = web.WebSocketResponse(heartbeat=25, max_msg_size=4 * 1024 * 1024)
    await ws.prepare(request)

    authed = False
    if request.query.get("t") == HUB.token:
        authed = True

    loop = asyncio.get_running_loop()

    async def do_inject(text: str, replace: bool = False) -> dict:
        trimmed = text.strip()
        if not trimmed:
            return {"ok": False, "reason": "empty"}
        now = time.monotonic()
        # 同一段话 1.5 秒内重复到达（重连重发、公网抖动），直接认作已送达，别再粘一遍
        if (not replace and HUB.last_text == trimmed
                and (now - HUB.last_ts) < 1.5):
            return {"ok": True, "chars": len(trimmed), "back": 0, "deduped": True}
        back = 0
        fg = injector.foreground_hwnd()
        # 换了窗口或隔太久，之前累计的长度就不作数了
        if fg != HUB.chain_hwnd or (now - HUB.chain_ts) > 60.0:
            HUB.chain_len = 0
        if replace and HUB.chain_len and (now - HUB.chain_ts) < 10.0:
            back = HUB.chain_len
        state = injector.focused_edit_state()
        if state == "container":
            # 焦点在桌面/资源管理器之类的地方，粘什么都进不去：只放进剪贴板，别退格误伤
            result = {"ok": True, "chars": len(trimmed), "back": 0,
                      "pasted": False, "reason": "no-input-focus"}
            await loop.run_in_executor(
                None, lambda: injector.inject(trimmed, 0, keep_clipboard=True))
        else:
            result = await loop.run_in_executor(None, injector.inject, trimmed, back)
        if result.get("ok") and result.get("pasted") is not False:
            if back:
                HUB.chain_len = len(trimmed)
            else:
                HUB.chain_len += len(trimmed)
            HUB.chain_hwnd = fg
            HUB.chain_ts = time.monotonic()
            HUB.last_text = trimmed
            HUB.last_len = len(trimmed)
            HUB.last_hwnd = fg
            HUB.last_ts = HUB.chain_ts
        return result

    try:
        async for msg in ws:
            if msg.type is not WSMsgType.TEXT:
                continue
            try:
                data = json.loads(msg.data)
            except ValueError:
                continue
            kind = data.get("type")
            if kind == "hello":
                if data.get("token") == HUB.token:
                    authed = True
                    HUB.clients.add(ws)
                    HUB.on_state(HUB.connected)
                    await ws.send_json({"type": "welcome", "connected": HUB.connected})
                else:
                    await ws.send_json({"type": "error", "reason": "bad-token"})
                    await ws.close()
            elif kind == "text":
                if not authed:
                    await ws.send_json({"type": "error", "reason": "not-authed"})
                    continue
                result = await do_inject(str(data.get("text", "")), bool(data.get("replace")))
                ack = {"type": "ack", "ok": result.get("ok", False),
                       "reason": result.get("reason", "")}
                if result.get("deduped"):
                    ack["deduped"] = True
                await ws.send_json(ack)
            elif kind == "key":
                if not authed:
                    await ws.send_json({"type": "error", "reason": "not-authed"})
                    continue
                name = str(data.get("key", "enter")).lower()
                if name != "enter":
                    await ws.send_json({"type": "ack", "kind": "key", "ok": False, "reason": "unknown-key"})
                    continue
                loop = asyncio.get_running_loop()
                sent = await loop.run_in_executor(None, injector.press_enter)
                await ws.send_json(
                    {
                        "type": "ack",
                        "kind": "key",
                        "ok": sent == 2,
                        "reason": "" if sent == 2 else "sendinput-failed",
                    }
                )
            elif kind == "clear":
                if not authed:
                    await ws.send_json({"type": "error", "reason": "not-authed"})
                    continue
                now = time.monotonic()
                fg = injector.foreground_hwnd()
                n = 0
                if fg == HUB.chain_hwnd and (now - HUB.chain_ts) <= 60.0:
                    n = int(HUB.chain_len)
                if n <= 0:
                    await ws.send_json(
                        {"type": "ack", "kind": "clear", "ok": False, "reason": "nothing-to-clear"}
                    )
                    continue
                n = min(n, 2000)
                sent = await loop.run_in_executor(None, injector.send_backspaces, n)
                ok = sent == n * 2
                if ok:
                    HUB.chain_len = 0
                    HUB.last_len = 0
                    HUB.last_text = ""
                await ws.send_json(
                    {
                        "type": "ack",
                        "kind": "clear",
                        "ok": ok,
                        "reason": "" if ok else "backspace-failed",
                        "count": n,
                    }
                )
            elif kind == "ping":
                await ws.send_json({"type": "pong"})
    finally:
        if ws in HUB.clients:
            HUB.clients.discard(ws)
            HUB.on_state(HUB.connected)
    return ws


def _root_file(name: str):
    async def handler(request: web.Request) -> web.StreamResponse:
        target = WEB_DIR / name
        if not target.is_file():
            raise web.HTTPNotFound()
        return _no_cache(web.FileResponse(target))

    return handler


def build_app(cfg: dict) -> web.Application:
    global HUB
    HUB = Hub(cfg)
    app = web.Application(client_max_size=4 * 1024 * 1024)
    app.router.add_get("/", handle_index)
    app.router.add_get("/manifest.webmanifest", _root_file("manifest.webmanifest"))
    app.router.add_get("/icon.svg", _root_file("icon.svg"))
    app.router.add_get("/favicon.ico", _root_file("icon.svg"))
    app.router.add_get("/api/info", handle_info)
    app.router.add_get("/ws", handle_ws)
    app.router.add_get("/static/{name:.*}", handle_static)
    return app


# ---------------------------------------------------------------- tray


def _tray_image(connected: bool):
    from PIL import Image, ImageDraw

    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    fill = (46, 160, 67, 255) if connected else (120, 120, 120, 255)
    draw.ellipse((2, 2, size - 3, size - 3), fill=fill)
    draw.rectangle((26, 14, 38, 30), fill=(255, 255, 255, 255))
    draw.polygon([(24, 30), (40, 30), (32, 42)], fill=(255, 255, 255, 255))
    return img


def _startup_command() -> str:
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    exe = pythonw if pythonw.exists() else Path(sys.executable)
    return f'"{exe}" "{APP_DIR / "agent.py"}"'


def _startup_enabled() -> bool:
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
            value, _ = winreg.QueryValueEx(key, APP_NAME)
            return bool(value)
    except OSError:
        return False


def _set_startup(enabled: bool) -> None:
    import winreg

    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",
        0,
        winreg.KEY_SET_VALUE,
    ) as key:
        if enabled:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, _startup_command())
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except OSError:
                pass


def _ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def fix_firewall() -> None:
    exe = sys.executable
    cmd = (
        "netsh advfirewall firewall delete rule name=phone-VibeKey > $null 2>&1; "
        f"netsh advfirewall firewall add rule name=phone-VibeKey dir=in action=allow "
        f"program={_ps_quote(exe)} profile=private,domain,public enable=yes"
    )
    subprocess.Popen(
        ["powershell", "-NoProfile", "-Command", f"Start-Process powershell -Verb RunAs -ArgumentList '-NoProfile','-Command',{_ps_quote(cmd)}"],
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def show_qr() -> None:
    assert HUB is not None
    subprocess.Popen(
        [sys.executable, str(APP_DIR / "showqr.py"), HUB.pair_url(), json.dumps(HUB.endpoints())],
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def copy_url() -> None:
    assert HUB is not None
    injector.set_clipboard_text(HUB.pair_url())


def start_tray(hub: Hub, loop: asyncio.AbstractEventLoop, quiet: bool = False) -> object | None:
    if quiet:
        return None
    try:
        import pystray
    except ImportError:
        print("[warn] 未安装 pystray，托盘不可用")
        return None

    icon = pystray.Icon(APP_NAME, _tray_image(False), f"{APP_NAME}：运行中，未连接")

    def on_state(connected: int) -> None:
        connected = int(connected or 0)

        def apply() -> None:
            icon.icon = _tray_image(connected > 0)
            icon.title = f"{APP_NAME}：{'已连接 ' + str(connected) + ' 台' if connected else '运行中，等待手机'}"

        try:
            loop.call_soon_threadsafe(apply)
        except RuntimeError:
            pass

    hub.on_state = on_state

    def menu_show(_icon=None, _item=None):
        show_qr()

    def menu_copy(_icon=None, _item=None):
        copy_url()

    def menu_firewall(_icon=None, _item=None):
        fix_firewall()

    def toggle_startup(_icon=None, _item=None):
        _set_startup(not _startup_enabled())

    def menu_quit(_icon=None, _item=None):
        icon.stop()
        loop.call_soon_threadsafe(lambda: os._exit(0))

    icon.menu = pystray.Menu(
        pystray.MenuItem("显示配对二维码", menu_show, default=True),
        pystray.MenuItem("复制手机地址", menu_copy),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("开机自启", toggle_startup, checked=lambda _i: _startup_enabled()),
        pystray.MenuItem("修复手机连不上（防火墙）", menu_firewall),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("退出", menu_quit),
    )
    threading.Thread(target=icon.run, daemon=True).start()
    return icon


# ---------------------------------------------------------------- main


async def _serve(port: int | None, quiet: bool) -> None:
    cfg = load_config()
    if port is None:
        port = int(cfg["port"])
    # 命令行 --port 只做本次临时覆盖，不写回 config（测试/多实例调试不该污染正式端口）
    if _port_busy(port):
        msg = f"{APP_NAME} 已经在运行（端口 {port} 被占用）。"
        if quiet:
            print(msg)
        else:
            _message_box(msg + "\n请在任务栏托盘里操作，或先退出旧实例。")
        return
    app = build_app(cfg)
    hub = HUB
    assert hub is not None
    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    try:
        # 有 IPv6 就顺手也听一个（双栈），失败不影响 IPv4
        await web.TCPSite(runner, "::", port).start()
    except OSError:
        pass
    await site.start()

    loop = asyncio.get_running_loop()
    start_tray(hub, loop, quiet=quiet)

    print(f"{APP_NAME} 已启动：{hub.primary_url()}")
    for ip in _all_ips():
        print(f"  手机地址 http://{ip}:{port}/?t={hub.token}")
    if not quiet:
        show_qr()

    try:
        await asyncio.Event().wait()
    finally:
        await runner.cleanup()


def _message_box(text: str) -> None:
    if os.name != "nt":
        print(text)
        return
    import ctypes

    ctypes.windll.user32.MessageBoxW(0, text, APP_NAME, 0x40)


def _port_busy(port: int) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("0.0.0.0", port))
        return False
    except OSError:
        return True
    finally:
        s.close()


def main() -> None:
    try:
        _main()
    except Exception:
        import traceback

        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        log = CONFIG_DIR / "agent.log"
        log.write_text(traceback.format_exc(), "utf-8")
        _message_box(f"{APP_NAME} 启动失败，详情见\n{log}")


def _main() -> None:
    port: int | None = None
    quiet = False
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--port" and i + 1 < len(args):
            port = int(args[i + 1])
            i += 2
            continue
        if args[i] == "--no-tray":
            quiet = True
        i += 1
    if os.name == "nt":
        try:
            import ctypes

            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    try:
        asyncio.run(_serve(port, quiet))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
