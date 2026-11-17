"""重复消息幂等测试：同一句话 1.5 秒内重复到达，不允许重复落字。"""
import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

import aiohttp

APP = Path(__file__).resolve().parent
OUT = APP / "_dedup_out.txt"
PORT = 8796
FIRST = "重复测试"
SECOND = "第二批"


async def main() -> None:
    cfg_path = Path(os.environ["APPDATA"]) / "phone-VibeKey" / "config.json"
    backup = cfg_path.read_text("utf-8") if cfg_path.exists() else None
    OUT.write_text("", encoding="utf-8")
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
            async with s.ws_connect(f"http://127.0.0.1:{PORT}/ws?t={token}") as ws:
                await ws.send_json({"type": "hello", "token": token})
                print("hello ->", await ws.receive_json())
                await ws.send_json({"type": "text", "text": FIRST})
                a1 = await ws.receive_json()
                await ws.send_json({"type": "text", "text": FIRST})
                a2 = await ws.receive_json()
                print("ack1 ->", a1)
                print("ack2 ->", a2, "(应带 deduped)")
                await ws.send_json({"type": "text", "text": SECOND})
                a3 = await ws.receive_json()
                print("ack3 ->", a3)
        await asyncio.sleep(0.9)
        got = OUT.read_text("utf-8").strip()
        print("final text:", repr(got))
        ok = got == FIRST + SECOND and a2.get("deduped") is True
        print("RESULT", "PASS" if ok else "FAIL")
    finally:
        agent.kill()
        target.kill()
        if backup is not None:
            await asyncio.sleep(0.4)
            cfg_path.write_text(backup, "utf-8")


if __name__ == "__main__":
    asyncio.run(main())
