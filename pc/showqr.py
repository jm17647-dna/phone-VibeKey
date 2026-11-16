"""显示配对二维码的小窗口（独立进程，避免和 asyncio 主循环抢线程）。"""
from __future__ import annotations

import json
import sys
import tkinter as tk
from tkinter import ttk

import qrcode
from PIL import ImageTk


def main() -> None:
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765/"
    try:
        ips = json.loads(sys.argv[2]) if len(sys.argv) > 2 else []
    except ValueError:
        ips = []

    root = tk.Tk()
    root.title("VoiceBridge 配对")
    root.resizable(False, False)
    root.attributes("-topmost", True)

    img = qrcode.make(url, box_size=7, border=2).get_image().resize((320, 320))
    photo = ImageTk.PhotoImage(img)

    tk.Label(root, image=photo).pack(padx=18, pady=(18, 6))
    tk.Label(root, text="用手机「扫一扫」扫这个码", font=("Microsoft YaHei UI", 13, "bold")).pack(pady=(0, 2))
    tk.Label(root, text="打开后输入框会自动聚焦，直接用输入法语音说话", fg="#555").pack(pady=(0, 8))

    box = tk.Text(root, height=2, width=46, font=("Consolas", 9), wrap="char")
    box.insert("1.0", url)
    box.configure(state="disabled")
    box.pack(padx=18, pady=(0, 8))

    others = [u for u in ips if u != url]
    if len(others) > 0:
        tk.Label(root, text="二维码里已含备用地址；扫不出时可手动输入：", fg="#777").pack()
        for u in others:
            tk.Label(root, text=u[:58], fg="#777", font=("Consolas", 8)).pack()

    row = tk.Frame(root)
    row.pack(pady=(6, 16))

    def copy_url() -> None:
        root.clipboard_clear()
        root.clipboard_append(url)
        btn.configure(text="已复制")

    btn = ttk.Button(row, text="复制地址", command=copy_url)
    btn.pack(side="left", padx=6)
    ttk.Button(row, text="关闭", command=root.destroy).pack(side="left", padx=6)

    root.mainloop()


if __name__ == "__main__":
    main()
