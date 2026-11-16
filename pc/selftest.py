import asyncio
import ctypes
import json
import os
import subprocess
import sys
from ctypes import wintypes
from pathlib import Path

import aiohttp

APP = Path(__file__).resolve().parent
OUT = APP / "_selftest_out.txt"
HWND_FILE = APP / "_selftest_out_hwnd.txt"
PORT = 8799
FIRST = "你好 VoiceBridge 测试 123"
FULL = "你好 VoiceBridge 测试 123 这是一句更完整的话"

user32 = ctypes.WinDLL("user32", use_last_error=True)
user32.GetForegroundWindow.restype = wintypes.HWND
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)


def force_fg(hwnd: int) -> None:
    """别的窗口偶尔会抢焦点，发之前把目标窗口重新拉到前台。"""
    if not hwnd:
        return
    fg = user32.GetForegroundWindow()
    if fg == hwnd:
        return
    t1 = user32.GetWindowThreadProcessId(fg, None)
    t2 = kernel32.GetCurrentThreadId()
    user32.AttachThreadInput(t1, t2, True)
    user32.SetForegroundWindow(hwnd)
    user32.BringWindowToTop(hwnd)
    user32.AttachThreadInput(t1, t2, False)


async def main() -> None:
    cfg_path = Path(os.environ["APPDATA"]) / "VoiceBridge" / "config.json"
    backup = cfg_path.read_text("utf-8") if cfg_path.exists() else None
    OUT.write_text("", encoding="utf-8")
    HWND_FILE.unlink(missing_ok=True)
    agent = subprocess.Popen(
        [sys.executable, str(APP / "agent.py"), "--port", str(PORT), "--no-tray"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
    )
    target = subprocess.Popen([sys.executable, str(APP / "target_window.py"), str(OUT)])
    ok = True
    try:
        await asyncio.sleep(2.5)
        token = json.loads(cfg_path.read_text("utf-8"))["token"]
        async with aiohttp.ClientSession() as s:
            async with s.get(f"http://127.0.0.1:{PORT}/") as r:
                print("index", r.status, "has_textarea", "<textarea" in await r.text())
            async with s.ws_connect(f"http://127.0.0.1:{PORT}/ws?t={token}") as ws:
                await ws.send_json({"type": "hello", "token": token})
                print("hello ->", await ws.receive_json())
                hwnd = int(HWND_FILE.read_text("utf-8") or 0) if HWND_FILE.exists() else 0
                print("focus_ok", hwnd == user32.GetForegroundWindow())
                force_fg(hwnd)
                await asyncio.sleep(0.15)
                await ws.send_json({"type": "text", "text": FIRST})
                print("ack1 ->", await ws.receive_json())
                await asyncio.sleep(0.7)
                step1 = OUT.read_text("utf-8")
                print("step1:", repr(step1))
                force_fg(hwnd)
                await asyncio.sleep(0.15)
                await ws.send_json({"type": "text", "text": FULL, "replace": True})
                print("ack2 ->", await ws.receive_json())
        await asyncio.sleep(0.9)
        step2 = OUT.read_text("utf-8")
        print("step2:", repr(step2))
        ok = step1.strip() == FIRST and step2.strip() == FULL
        print("RESULT", "MATCH" if ok else "MISMATCH")
    finally:
        agent.kill()
        target.kill()
        if backup is not None:
            await asyncio.sleep(0.4)
            cfg_path.write_text(backup, "utf-8")


if __name__ == "__main__":
    asyncio.run(main())
