"""验证「手机按回车 -> 电脑真的敲了一次回车」：agent(WS) -> SendInput -> 前台 Tk 窗口。"""
import asyncio
import ctypes
import json
import os
import pathlib
import subprocess
import sys
import threading
import time
import tkinter as tk

PORT = 8798
user32 = ctypes.windll.user32
state = {"ack": None, "err": None}


def force_foreground(hwnd):
    fg = user32.GetForegroundWindow()
    t1 = user32.GetWindowThreadProcessId(fg, None)
    t2 = ctypes.windll.kernel32.GetCurrentThreadId()
    user32.AttachThreadInput(t1, t2, True)
    user32.SetForegroundWindow(hwnd)
    user32.SetFocus(hwnd)
    user32.AttachThreadInput(t1, t2, False)


def ws_worker(token):
    async def run():
        import aiohttp
        async with aiohttp.ClientSession() as sess:
            async with sess.ws_connect(f"ws://127.0.0.1:{PORT}/ws") as ws:
                await ws.send_json({"type": "hello", "token": token})
                await ws.receive_json()
                await ws.send_json({"type": "key", "key": "enter"})
                for _ in range(20):
                    msg = await ws.receive_json(timeout=5)
                    if msg.get("type") == "ack":
                        state["ack"] = msg
                        return
    try:
        asyncio.run(run())
    except Exception as exc:  # noqa: BLE001
        state["err"] = repr(exc)


def main():
    conf = pathlib.Path(os.environ["APPDATA"]) / "phone-VibeKey" / "config.json"
    token = json.loads(conf.read_text("utf-8"))["token"]
    proc = subprocess.Popen(
        [sys.executable, "agent.py", "--port", str(PORT), "--no-tray"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(2.0)
    try:
        root = tk.Tk()
        root.title("VB_KEY_TARGET")
        root.geometry("380x150+260+260")
        root.attributes("-topmost", True)
        text = tk.Text(root, font=("Consolas", 14))
        text.pack(fill="both", expand=True)
        text.focus_set()
        root.update()
        hwnd = int(root.winfo_id())
        hwnd = user32.GetAncestor(hwnd, 2) or hwnd
        force_foreground(hwnd)
        root.update()
        threading.Thread(target=ws_worker, args=(token,), daemon=True).start()

        def verify():
            fg = user32.GetForegroundWindow()
            buf = ctypes.create_unicode_buffer(200)
            user32.GetWindowTextW(fg, buf, 200)
            content = text.get("1.0", "end-1c")
            print("ack:", state["ack"], "err:", state["err"])
            print("foreground:", buf.value, "| is target:", fg == hwnd)
            print("text repr:", repr(content))
            print("RESULT:", "PASS" if content.count("\n") == 1 else "FAIL")
            root.after(50, root.destroy)

        def poll():
            if state["ack"] is None and state["err"] is None:
                root.after(150, poll)
                return
            force_foreground(hwnd)
            # 让 Tk 主循环把注入的按键消息处理掉，再读内容
            root.after(700, verify)

        root.after(800, poll)
        root.mainloop()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    main()
