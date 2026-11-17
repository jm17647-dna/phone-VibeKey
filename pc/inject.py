"""把文字粘到当前焦点窗口：写剪贴板 + 模拟 Ctrl+V，完毕后恢复原剪贴板。

纯 ctypes 调用 Win32，无第三方依赖。
"""
from __future__ import annotations

import ctypes
import time
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
VK_CONTROL = 0x11
VK_BACK = 0x08
VK_V = 0x56
VK_RETURN = 0x0D

kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
kernel32.GlobalLock.restype = wintypes.LPVOID
kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalFree.argtypes = [wintypes.HGLOBAL]

user32.OpenClipboard.argtypes = [wintypes.HWND]
user32.OpenClipboard.restype = wintypes.BOOL
user32.CloseClipboard.restype = wintypes.BOOL
user32.EmptyClipboard.restype = wintypes.BOOL
user32.GetClipboardData.restype = wintypes.HANDLE
user32.GetClipboardData.argtypes = [wintypes.UINT]
user32.SetClipboardData.restype = wintypes.HANDLE
user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
user32.IsClipboardFormatAvailable.argtypes = [wintypes.UINT]
user32.IsClipboardFormatAvailable.restype = wintypes.BOOL

user32.GetWindowThreadProcessId = ctypes.windll.user32.GetWindowThreadProcessId
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.GetForegroundWindow.restype = wintypes.HWND
user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]


class RECT(ctypes.Structure):
    _fields_ = [("left", wintypes.LONG), ("top", wintypes.LONG),
                ("right", wintypes.LONG), ("bottom", wintypes.LONG)]


class GUITHREADINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("hwndActive", wintypes.HWND),
        ("hwndFocus", wintypes.HWND),
        ("hwndCapture", wintypes.HWND),
        ("hwndMenuOwner", wintypes.HWND),
        ("hwndMoveSize", wintypes.HWND),
        ("hwndCaret", wintypes.HWND),
        ("rcCaret", RECT),
    ]


user32.GetGUIThreadInfo.argtypes = [wintypes.DWORD, ctypes.POINTER(GUITHREADINFO)]
user32.GetGUIThreadInfo.restype = wintypes.BOOL

# 明确是文字输入控件的窗口类
_EDITABLE_CLASSES = {
    "edit", "richedit", "richedit20a", "richedit20w", "richedit50w", "rrichedit20w",
    "ricedit20w", "scintilla", "windows.ui.core.corewindow_edit", "tedit", "trichedit",
    "tcombobox", "cascadia", "tcaddition", "rctrl_edit",
}
# 明显不是输入位置的容器（桌面、资源管理器、任务栏）
_CONTAINER_CLASSES = {
    "progman", "workerw", "shell_traywnd", "shell_secondarytraywnd", "cabinetwclass",
    "notifyiconoverflowwindow", "tasklistthumbbar", "mstasklistwclass", "dv2controlhost",
    "explorerframe", "folderview", "syslistview32", "shelldll_defview",
}


def _class_name(hwnd: int) -> str:
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return (buf.value or "").lower()


def focused_edit_state(hwnd: int = 0) -> str:
    """判断当前焦点处是不是能接收文字。

    返回 "editable"（确定是输入框）/ "container"（桌面、资源管理器等肯定不能输入）/
    "unknown"（应用窗口，判断不了，按能输入处理，如微信、浏览器）。
    """
    hwnd = int(hwnd or user32.GetForegroundWindow() or 0)
    if not hwnd:
        return "container"
    focus = hwnd
    tid = user32.GetWindowThreadProcessId(hwnd, None)
    gti = GUITHREADINFO()
    gti.cbSize = ctypes.sizeof(GUITHREADINFO)
    if tid and user32.GetGUIThreadInfo(tid, ctypes.byref(gti)):
        if gti.hwndCaret:
            return "editable"
        if gti.hwndFocus:
            focus = int(gti.hwndFocus)
        elif gti.hwndActive:
            focus = int(gti.hwndActive)
    cls = _class_name(focus)
    if cls in _CONTAINER_CLASSES:
        return "container"
    if cls in _EDITABLE_CLASSES:
        return "editable"
    top = _class_name(hwnd)
    if top in _CONTAINER_CLASSES:
        return "container"
    return "unknown"



class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG)),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG)),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]


user32.GetForegroundWindow.restype = wintypes.HWND
user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
user32.SendInput.restype = wintypes.UINT


def _open_clipboard(retries: int = 20, delay: float = 0.01) -> bool:
    for _ in range(retries):
        if user32.OpenClipboard(None):
            return True
        time.sleep(delay)
    return False


def get_clipboard_text() -> str | None:
    if not user32.IsClipboardFormatAvailable(CF_UNICODETEXT):
        return None
    if not _open_clipboard():
        return None
    try:
        handle = user32.GetClipboardData(CF_UNICODETEXT)
        if not handle:
            return None
        ptr = kernel32.GlobalLock(handle)
        if not ptr:
            return None
        try:
            return ctypes.wstring_at(ptr)
        finally:
            kernel32.GlobalUnlock(handle)
    finally:
        user32.CloseClipboard()


def set_clipboard_text(text: str) -> bool:
    data = text.encode("utf-16-le") + b"\x00\x00"
    handle = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
    if not handle:
        return False
    ptr = kernel32.GlobalLock(handle)
    if not ptr:
        kernel32.GlobalFree(handle)
        return False
    ctypes.memmove(ptr, data, len(data))
    kernel32.GlobalUnlock(handle)
    if not _open_clipboard():
        kernel32.GlobalFree(handle)
        return False
    try:
        user32.EmptyClipboard()
        if not user32.SetClipboardData(CF_UNICODETEXT, handle):
            kernel32.GlobalFree(handle)
            return False
    finally:
        user32.CloseClipboard()
    return True


def _key(vk: int, up: bool = False) -> INPUT:
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.ki.wVk = vk
    inp.ki.wScan = 0
    inp.ki.dwFlags = KEYEVENTF_KEYUP if up else 0
    inp.ki.time = 0
    inp.ki.dwExtraInfo = None
    return inp


def send_ctrl_v() -> int:
    keys = (INPUT * 4)(
        _key(VK_CONTROL),
        _key(VK_V),
        _key(VK_V, up=True),
        _key(VK_CONTROL, up=True),
    )
    return int(user32.SendInput(4, keys, ctypes.sizeof(INPUT)))


def press_enter() -> int:
    """在当前焦点窗口按一次回车，返回 SendInput 发出的事件数（应为 2）。"""
    keys = (INPUT * 2)(_key(VK_RETURN), _key(VK_RETURN, up=True))
    return int(user32.SendInput(2, keys, ctypes.sizeof(INPUT)))


def foreground_hwnd() -> int:
    return int(user32.GetForegroundWindow() or 0)


def send_backspaces(count: int) -> int:
    sent = 0
    remaining = max(0, count)
    while remaining:
        k = min(50, remaining)
        seq = []
        for _ in range(k):
            seq.append(_key(VK_BACK))
            seq.append(_key(VK_BACK, up=True))
        keys = (INPUT * len(seq))(*seq)
        sent += int(user32.SendInput(len(seq), keys, ctypes.sizeof(INPUT)))
        remaining -= k
    time.sleep(0.03)
    return sent


def inject(text: str, back: int = 0, settle_ms: int = 40, restore_ms: int = 220,
           keep_clipboard: bool = False) -> dict:
    """先落剪贴板，再按 Ctrl+V，最后恢复剪贴板。

    keep_clipboard=True 时只把文字放进剪贴板、不粘贴也不恢复（当前焦点不像输入框时用，
    避免文字被吞掉）。返回执行结果用于日志。
    """
    text = text or ""
    if not text.strip():
        return {"ok": False, "reason": "empty"}
    if keep_clipboard:
        if not set_clipboard_text(text):
            return {"ok": False, "reason": "clipboard-busy"}
        return {"ok": True, "chars": len(text), "back": 0, "pasted": False,
                "reason": "clipboard-only"}
    if back > 0:
        if send_backspaces(back) != back * 2:
            return {"ok": False, "reason": "backspace-failed"}
    previous = get_clipboard_text()
    if not set_clipboard_text(text):
        return {"ok": False, "reason": "clipboard-busy"}
    time.sleep(settle_ms / 1000)
    sent = send_ctrl_v()
    time.sleep(restore_ms / 1000)
    if previous is not None and get_clipboard_text() == text:
        set_clipboard_text(previous)
    if sent != 4:
        return {"ok": False, "reason": "sendinput-failed"}
    return {"ok": True, "chars": len(text), "back": back}
