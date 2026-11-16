import ctypes
import sys
import tkinter as tk
from ctypes import wintypes
from pathlib import Path

out = Path(sys.argv[1])
hwnd_file = out.with_name(out.stem + "_hwnd.txt")

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
user32.GetAncestor.restype = wintypes.HWND
user32.GetForegroundWindow.restype = wintypes.HWND
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]

root = tk.Tk()
root.title("VB_TEST_TARGET")
root.geometry("720x260+140+140")
txt = tk.Text(root, width=70, height=8)
txt.pack(fill="both", expand=True)
txt.focus_set()
root.attributes("-topmost", True)

state = {"hwnd": 0}


def steal():
    hwnd = user32.GetAncestor(root.winfo_id(), 2)
    state["hwnd"] = hwnd
    fg = user32.GetForegroundWindow()
    tid_fg = user32.GetWindowThreadProcessId(fg, None)
    tid_me = kernel32.GetCurrentThreadId()
    user32.AttachThreadInput(tid_me, tid_fg, True)
    user32.ShowWindow(hwnd, 5)
    user32.BringWindowToTop(hwnd)
    user32.SetForegroundWindow(hwnd)
    user32.AttachThreadInput(tid_me, tid_fg, False)
    hwnd_file.write_text(str(hwnd), encoding="utf-8")
    txt.focus_set()


def tick():
    out.write_text(txt.get("1.0", "end-1c"), encoding="utf-8")
    if user32.GetForegroundWindow() != state["hwnd"]:
        steal()
    root.after(250, tick)


root.after(300, steal)
root.after(1500, steal)
root.after(400, tick)
root.after(20000, root.destroy)
root.mainloop()
