"""弹出配对二维码（独立进程，避免 Tk 与 asyncio 抢线程）。"""
from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path

APP_NAME = "VoiceBridge"


def main() -> None:
    url = sys.argv[1] if len(sys.argv) > 1 else ""
    alts = []
    if len(sys.argv) > 2:
        import json

        try:
            alts = json.loads(sys.argv[2]) or []
        except ValueError:
            alts = []

    try:
        import qrcode
    except ImportError:
        print("[warn] 未安装 qrcode，无法显示二维码")
        return

    img = qrcode.make(url)
    png = Path(__file__).resolve().parent.parent / "pair.png"
    img.save(png)

    root = tk.Tk()
    root.title(f"{APP_NAME} 配对")
    root.configure(bg="#111827")
    root.attributes("-topmost", True)

    tk.Label(root, text="用手机扫一扫（微信/相机）", bg="#111827", fg="#e5e7eb",
             font=("Microsoft YaHei UI", 12)).pack(padx=20, pady=(16, 6))

    from PIL import ImageTk

    photo = ImageTk.PhotoImage(img.resize((260, 260)))
    label = tk.Label(root, image=photo, borderwidth=0)
    label.image = photo
    label.pack(padx=20, pady=6)

    tk.Label(root, text=url, bg="#111827", fg="#93c5fd", wraplength=320,
             font=("Consolas", 9)).pack(padx=20, pady=4)

    def copy() -> None:
        root.clipboard_clear()
        root.clipboard_append(url)
        btn.config(text="已复制")

    btn = tk.Button(root, text="复制地址", command=copy, bg="#1f2937", fg="#e5e7eb",
                    activebackground="#374151", activeforeground="#ffffff",
                    relief="flat", padx=14, pady=6)
    btn.pack(pady=(6, 16))

    if alts:
        tk.Label(root, text=f"备用地址 {len(alts)} 个（主地址连不上时自动切换）",
                 bg="#111827", fg="#6b7280", font=("Microsoft YaHei UI", 9)).pack(pady=(0, 12))

    root.mainloop()


if __name__ == "__main__":
    main()
