"""验证：增量续写 + 清空电脑输入框。"""
import asyncio, ctypes, json, os, pathlib, subprocess, sys, threading, time, tkinter as tk

PORT = 8797
user32 = ctypes.windll.user32
state = {"acks": [], "err": None}


def force_foreground(hwnd):
    fg = user32.GetForegroundWindow()
    t1 = user32.GetWindowThreadProcessId(fg, None)
    t2 = ctypes.windll.kernel32.GetCurrentThreadId()
    user32.AttachThreadInput(t1, t2, True)
    user32.SetForegroundWindow(hwnd); user32.SetFocus(hwnd)
    user32.AttachThreadInput(t1, t2, False)


def ws_worker(token):
    async def run():
        import aiohttp
        async with aiohttp.ClientSession() as sess:
            async with sess.ws_connect(f"ws://127.0.0.1:{PORT}/ws") as ws:
                await ws.send_json({"type": "hello", "token": token})
                await ws.receive_json()
                for part in ("今天下午三点开会", "，顺便带上资料"):
                    await ws.send_json({"type": "text", "text": part, "replace": False})
                    state["acks"].append(await ws.receive_json(timeout=5))
                    await asyncio.sleep(0.3)
                await asyncio.sleep(0.3)
                await ws.send_json({"type": "clear"})
                state["acks"].append(await ws.receive_json(timeout=5))
    try:
        asyncio.run(run())
    except Exception as exc:  # noqa: BLE001
        state["err"] = repr(exc)


def main():
    conf = pathlib.Path(os.environ["APPDATA"]) / "VoiceBridge" / "config.json"
    token = json.loads(conf.read_text("utf-8"))["token"]
    proc = subprocess.Popen([sys.executable, "agent.py", "--port", str(PORT), "--no-tray"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2.0)
    try:
        root = tk.Tk(); root.title("VB_CLEAR_TARGET"); root.geometry("420x160+280+280")
        root.attributes("-topmost", True)
        text = tk.Text(root, font=("Consolas", 14)); text.pack(fill="both", expand=True)
        text.focus_set(); root.update()
        hwnd = int(root.winfo_id()); hwnd = user32.GetAncestor(hwnd, 2) or hwnd
        force_foreground(hwnd); root.update()
        threading.Thread(target=ws_worker, args=(token,), daemon=True).start()

        def verify():
            content = text.get("1.0", "end-1c")
            print("acks:", json.dumps(state["acks"], ensure_ascii=False))
            print("err:", state["err"])
            print("final text repr:", repr(content))
            print("RESULT:", "PASS" if content == "" else "FAIL")
            root.after(50, root.destroy)

        def poll():
            if len(state["acks"]) < 3 and state["err"] is None:
                root.after(200, poll); return
            root.after(800, verify)

        root.after(900, poll)
        root.mainloop()
    finally:
        proc.terminate()
        try: proc.wait(timeout=5)
        except subprocess.TimeoutExpired: proc.kill()


if __name__ == "__main__":
    main()
