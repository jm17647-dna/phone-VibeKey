"""phone-VibeKey 小红书宣传图 v2：沿用项目自身 UI 风格（深海军蓝 + 蓝青渐变 + 圆角卡片）。
字体：Noto Sans SC Regular / Medium / Bold。2 倍超采样后缩到 1080x1440。
运行：C:/Users/Mjh10/.workbuddy/binaries/python/versions/3.13.12/python.exe 生成图片.py
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os
import re

BASE = os.path.dirname(os.path.abspath(__file__))
SHOTS = os.path.normpath(os.path.join(BASE, "..", "screenshots"))
FDIR = "C:/Windows/Fonts/"
FONTS = {
    "r": FDIR + "Noto Sans SC (TrueType).otf",
    "m": FDIR + "Noto Sans SC Medium (TrueType).otf",
    "b": FDIR + "Noto Sans SC Bold (TrueType).otf",
}

W, H, S = 1080, 1440, 2
# 直接来自 web/style.css
BG_TOP = (11, 18, 38)
BG_BOT = (15, 23, 42)
CARD = (17, 28, 51)
CARD2 = (22, 35, 60)
LINE = (31, 43, 69)
FG = (230, 237, 247)
DIM = (142, 160, 189)
FAINT = (96, 116, 148)
ACCENT = (47, 129, 247)
BLUE = (37, 99, 235)
CYAN = (14, 165, 233)
GREEN = (46, 160, 67)
GREEN_LT = (148, 226, 172)
RED = (217, 83, 79)
RED_LT = (243, 178, 178)
WHITE = (255, 255, 255)

_fc = {}
_probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))

def sc(v):
    return int(round(v * S))

def ft(size, weight="r"):
    k = (weight, size)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(FONTS[weight], sc(size))
    return _fc[k]

def tw(s, font):
    return _probe.textlength(s, font=font)

def lw(s, size, weight="r"):
    return tw(s, ft(size, weight)) / S

def text(d, x, y, s, size, weight="r", fill=FG):
    d.text((sc(x), sc(y)), s, font=ft(size, weight), fill=fill)

_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_\-\.:/]*|\s+|.", re.S)
_CLOSE = set("。，、；：！？）》」』】…%")

def wrap(s, size, weight, max_w):
    """按 token 折行：英文单词不拆开，中文标点不落单行首。"""
    f = ft(size, weight)
    out = []
    for para in s.split("\n"):
        if not para:
            out.append("")
            continue
        cur = ""
        for tok in _TOKEN.findall(para):
            if cur and tw(cur + tok, f) > sc(max_w) and tok not in _CLOSE:
                out.append(cur.rstrip())
                cur = tok.lstrip()
            else:
                cur += tok
        out.append(cur.rstrip())
    return out

def block(d, x, y, s, size, max_w, weight="r", fill=DIM, lh=1.55, max_lines=None):
    ls = wrap(s, size, weight, max_w)
    if max_lines:
        ls = ls[:max_lines]
    step = size * lh
    for i, line in enumerate(ls):
        text(d, x, y + i * step, line, size, weight, fill)
    return y + step * len(ls)

def rr(d, x, y, w, h, r, fill=None, outline=None, width=1):
    d.rounded_rectangle([sc(x), sc(y), sc(x + w), sc(y + h)], radius=sc(r),
                        fill=fill, outline=outline, width=sc(width) if outline else 1)

def rect(d, x, y, w, h, fill):
    d.rectangle([sc(x), sc(y), sc(x + w), sc(y + h)], fill=fill)

def line(d, x1, y1, x2, y2, fill, width=1):
    d.line([(sc(x1), sc(y1)), (sc(x2), sc(y2))], fill=fill, width=sc(width))

def circle(d, cx, cy, r, fill=None, outline=None, width=1):
    d.ellipse([sc(cx - r), sc(cy - r), sc(cx + r), sc(cy + r)],
              fill=fill, outline=outline, width=sc(width))

def grad_px(w, h, c1, c2, horizontal=True):
    n = 256
    strip = Image.new("RGB", (n, 1) if horizontal else (1, n))
    for i in range(n):
        t = i / (n - 1)
        strip.putpixel((i, 0) if horizontal else (0, i),
                       tuple(int(c1[j] + (c2[j] - c1[j]) * t) for j in range(3)))
    return strip.resize((w, h), Image.Resampling.BILINEAR)

def gradient_text(img, x, y, s, size, c1=BLUE, c2=CYAN, weight="b"):
    f = ft(size, weight)
    x0, y0, x1, y1 = _probe.textbbox((0, 0), s, font=f)
    w, h = x1 - x0, y1 - y0
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).text((-x0, -y0), s, font=f, fill=255)
    g = grad_px(w, h, c1, c2)
    img.paste(g, (sc(x) + x0, sc(y) + y0), mask)
    return w / S

def glow(img, cx, cy, r, color, alpha):
    size = sc(r * 2)
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).ellipse([size * 0.22, size * 0.22, size * 0.78, size * 0.78], fill=alpha)
    m = m.filter(ImageFilter.GaussianBlur(sc(r * 0.32)))
    layer = Image.new("RGBA", (size, size), color + (0,))
    layer.putalpha(m)
    img.alpha_composite(layer, (sc(cx - r), sc(cy - r)))

def new_canvas():
    img = grad_px(sc(W), sc(H), BG_TOP, BG_BOT, horizontal=False).convert("RGBA")
    glow(img, 940, 180, 560, BLUE, 90)
    glow(img, 60, 1260, 520, CYAN, 45)
    d = ImageDraw.Draw(img)
    for x in range(48, W - 40, 44):
        for y in range(180, 1300, 44):
            circle(d, x, y, 1.2, fill=(30, 45, 78, 110))
    return img

def logo(img, x, y, size):
    g = grad_px(sc(size), sc(size), BLUE, CYAN, horizontal=False)
    mask = Image.new("L", (sc(size), sc(size)), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, sc(size) - 1, sc(size) - 1],
                                           radius=sc(size * 0.24), fill=255)
    img.paste(g, (sc(x), sc(y)), mask)
    d = ImageDraw.Draw(img)
    cx = x + size / 2
    rr(d, cx - size * 0.095, y + size * 0.20, size * 0.19, size * 0.36, size * 0.095, fill=WHITE)
    d.arc([sc(cx - size * 0.20), sc(y + size * 0.36), sc(cx + size * 0.20), sc(y + size * 0.66)],
          0, 180, fill=WHITE, width=sc(size * 0.05))
    line(d, cx, y + size * 0.68, cx, y + size * 0.80, WHITE, size * 0.05)
    line(d, cx - size * 0.13, y + size * 0.80, cx + size * 0.13, y + size * 0.80, WHITE, size * 0.05)
    circle(d, x + size * 0.74, y + size * 0.28, size * 0.062, fill=(34, 197, 94))

def chip(d, x, y, s, size=22, fg=FG, dot=None, fill=CARD2):
    w = lw(s, size) + 36 + (16 if dot else 0)
    h = size + 22
    rr(d, x, y, w, h, h / 2, fill=fill, outline=LINE, width=1)
    tx = x + 18
    if dot:
        circle(d, x + 20, y + h / 2, 4, fill=dot)
        tx += 16
    text(d, tx, y + 10, s, size, "m", fg)
    return x + w + 14

def header(img, page):
    d = ImageDraw.Draw(img)
    logo(img, 56, 44, 48)
    text(d, 118, 46, "phone-VibeKey", 28, "b", FG)
    text(d, 118, 86, "手机说话 · 电脑落字 · 远程回车", 18, "r", DIM)
    s = "v0.7.1 · MIT"
    w = lw(s, 20) + 34
    rr(d, W - 56 - w, 54, w, 38, 19, fill=CARD, outline=LINE, width=1)
    text(d, W - 56 - w + 17, 62, s, 20, "r", DIM)
    line(d, 56, 132, W - 56, 132, LINE, 1)
    line(d, 56, 1336, W - 56, 1336, LINE, 1)
    text(d, 56, 1352, "开源项目 · MIT License · 零月费", 20, "r", DIM)
    n = "%02d / 09" % page
    text(d, W - 56 - lw(n, 20), 1352, n, 20, "r", DIM)
    for i in range(9):
        circle(d, W / 2 - 72 + i * 18, 1364, 4 if i == page - 1 else 3,
               fill=ACCENT if i == page - 1 else LINE)

def title(d, s, y=168, size=54):
    text(d, 56, y, s, size, "b", FG)
    return y + size * 1.35

def subtitle(d, s, y):
    text(d, 56, y, s, 26, "r", DIM)

def iconbox(d, x, y, size, kind, color=ACCENT):
    rr(d, x, y, size, size, size * 0.28, fill=(20, 38, 68), outline=LINE, width=1)
    cx, cy = x + size / 2, y + size / 2
    u = size / 48.0
    wd = max(2, 3.2 * u)
    if kind == "mic":
        rr(d, cx - 6 * u, y + 10 * u, 12 * u, 20 * u, 6 * u, outline=color, width=wd / u)
        d.arc([sc(cx - 12 * u), sc(y + 18 * u), sc(cx + 12 * u), sc(y + 36 * u)], 0, 180,
              fill=color, width=sc(wd))
        line(d, cx, y + 36 * u, cx, y + 41 * u, color, wd)
    elif kind == "coin":
        circle(d, cx, cy, 14 * u, outline=color, width=wd)
        text(d, cx - lw("¥", int(20 * u), "b") / 2, cy - 13 * u, "¥", int(20 * u), "b", color)
    elif kind == "swap":
        line(d, cx - 14 * u, cy - 6 * u, cx + 12 * u, cy - 6 * u, color, wd)
        line(d, cx + 12 * u, cy - 6 * u, cx + 5 * u, cy - 12 * u, color, wd)
        line(d, cx + 14 * u, cy + 7 * u, cx - 12 * u, cy + 7 * u, color, wd)
        line(d, cx - 12 * u, cy + 7 * u, cx - 5 * u, cy + 13 * u, color, wd)
    elif kind == "enter":
        rr(d, x + 8 * u, y + 12 * u, 32 * u, 24 * u, 5 * u, outline=color, width=wd / u)
        line(d, cx + 9 * u, cy - 6 * u, cx + 9 * u, cy + 6 * u, color, wd)
        line(d, cx + 9 * u, cy + 6 * u, cx - 8 * u, cy + 6 * u, color, wd)
        line(d, cx - 8 * u, cy + 6 * u, cx - 2 * u, cy + 1 * u, color, wd)
        line(d, cx - 8 * u, cy + 6 * u, cx - 2 * u, cy + 11 * u, color, wd)
    elif kind == "clear":
        rr(d, x + 8 * u, y + 13 * u, 32 * u, 22 * u, 5 * u, outline=color, width=wd / u)
        line(d, cx - 6 * u, cy - 5 * u, cx + 6 * u, cy + 5 * u, color, wd)
        line(d, cx + 6 * u, cy - 5 * u, cx - 6 * u, cy + 5 * u, color, wd)
    elif kind == "history":
        d.arc([sc(cx - 13 * u), sc(cy - 13 * u), sc(cx + 13 * u), sc(cy + 13 * u)], 40, 320,
              fill=color, width=sc(wd))
        line(d, cx, cy - 7 * u, cx, cy + 1 * u, color, wd)
        line(d, cx, cy + 1 * u, cx + 6 * u, cy + 4 * u, color, wd)
    elif kind == "shield":
        d.polygon([(sc(cx), sc(y + 9 * u)), (sc(cx + 13 * u), sc(y + 14 * u)),
                   (sc(cx + 13 * u), sc(y + 26 * u)), (sc(cx), sc(y + 39 * u)),
                   (sc(cx - 13 * u), sc(y + 26 * u)), (sc(cx - 13 * u), sc(y + 14 * u))],
                  outline=color, width=sc(wd))
        line(d, cx - 5 * u, cy + 1 * u, cx - 1 * u, cy + 6 * u, color, wd)
        line(d, cx - 1 * u, cy + 6 * u, cx + 7 * u, cy - 5 * u, color, wd)
    elif kind == "wave":
        for i, hh in enumerate([10, 20, 30, 20, 10]):
            line(d, cx + (i - 2) * 7 * u, cy - hh * u / 2, cx + (i - 2) * 7 * u,
                 cy + hh * u / 2, color, wd)
    elif kind == "lock":
        rr(d, cx - 12 * u, cy - 2 * u, 24 * u, 18 * u, 4 * u, outline=color, width=wd / u)
        d.arc([sc(cx - 8 * u), sc(cy - 16 * u), sc(cx + 8 * u), sc(cy + 2 * u)], 180, 360,
              fill=color, width=sc(wd))
    elif kind == "check":
        line(d, cx - 8 * u, cy, cx - 2 * u, cy + 7 * u, color, wd)
        line(d, cx - 2 * u, cy + 7 * u, cx + 10 * u, cy - 8 * u, color, wd)
    elif kind == "x":
        line(d, cx - 8 * u, cy - 8 * u, cx + 8 * u, cy + 8 * u, color, wd)
        line(d, cx + 8 * u, cy - 8 * u, cx - 8 * u, cy + 8 * u, color, wd)

def phone(img, x, y, h, shot_name):
    im = Image.open(os.path.join(SHOTS, shot_name)).convert("RGB")
    scale = h / im.height
    sw, sh = sc(int(im.width * scale)), sc(h)
    im = im.resize((sw, sh), Image.Resampling.LANCZOS)
    bezel = sc(9)
    ow, oh = sw + 2 * bezel, sh + 2 * bezel
    sh_l = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh_l).rounded_rectangle([sc(x) + 8, sc(y) + 22, sc(x) + ow + 8, sc(y) + oh + 22],
                                           radius=sc(46), fill=(0, 0, 0, 120))
    img.alpha_composite(sh_l)
    d = ImageDraw.Draw(img)
    rr(d, x, y, ow / S, oh / S, 46, fill=(7, 11, 22), outline=(58, 76, 110), width=2)
    mask = Image.new("L", (sw, sh), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, sw - 1, sh - 1], radius=sc(36), fill=255)
    img.paste(im, (sc(x) + bezel, sc(y) + bezel), mask)
    if shot_name == "01-phone.png":
        # 原截图键盘工具栏含 github_pat_ 前缀，必须遮掉
        d.rectangle([sc(x + 9 + 24 * scale), sc(y + 9 + 790 * scale),
                     sc(x + 9 + 302 * scale), sc(y + 9 + 840 * scale)], fill=(33, 33, 39))
    rr(d, x + ow / S + 2, y + 130, 3, 64, 2, fill=(58, 76, 110))
    return ow / S

def monitor(img, x, y, w, h):
    d = ImageDraw.Draw(img)
    rr(d, x, y, w, h, 22, fill=(7, 11, 22), outline=(58, 76, 110), width=2)
    rr(d, x + 12, y + 12, w - 24, h - 24, 14, fill=CARD)
    text(d, x + 32, y + 34, "帮我把这段话整理成周报", 23, "r", FG)
    rect(d, x + 32, y + 84, 3, 28, fill=ACCENT)
    s = "已送达 · 12 字"
    cw = lw(s, 19) + 30
    rr(d, x + 32, y + h - 74, cw, 36, 18, fill=(16, 51, 30), outline=(29, 94, 51), width=1)
    text(d, x + 47, y + h - 66, s, 19, "r", GREEN_LT)
    rect(d, x + w / 2 - 7, y + h, 14, 26, fill=(58, 76, 110))
    rr(d, x + w / 2 - 66, y + h + 24, 132, 10, 5, fill=(58, 76, 110))

def history_panel(img, x, y, w, h):
    d = ImageDraw.Draw(img)
    rr(d, x, y, w, h, 24, fill=CARD, outline=LINE, width=1)
    text(d, x + 26, y + 24, "最近记录", 26, "b", FG)
    s = "清空全部"
    text(d, x + w - 26 - lw(s, 19), y + 29, s, 19, "r", RED_LT)
    line(d, x + 26, y + 72, x + w - 26, y + 72, LINE, 1)
    items = [
        ("帮我把会议纪要整理成周报，\n重点写风险和下一步。", "00:17"),
        ("检查登录接口的报错，\n先定位原因，不要改代码。", "00:16"),
        ("把这段需求拆成三个\n可执行的任务。", "00:15"),
    ]
    yy = y + 92
    for t, ts in items:
        rr(d, x + 20, yy, w - 40, 196, 16, fill=CARD2, outline=LINE, width=1)
        block(d, x + 40, yy + 20, t, 21, w - 80, "r", FG, 1.5)
        text(d, x + 40, yy + 152, ts, 18, "r", DIM)
        s = "编辑  重发"
        text(d, x + w - 40 - lw(s, 18), yy + 152, s, 18, "r", (125, 180, 255))
        yy += 212

def save(img, name):
    img.convert("RGB").resize((W, H), Image.Resampling.LANCZOS).save(os.path.join(BASE, name), "PNG")
    print("saved", name)

# ---------- 01 封面 ----------
def cover():
    img = new_canvas()
    header(img, 1)
    d = ImageDraw.Draw(img)
    s = "开源项目 · 不用买硬件 · 不用装 App"
    w = lw(s, 23) + 40
    rr(d, 56, 176, w, 46, 23, fill=(20, 38, 68), outline=(47, 90, 160), width=1)
    text(d, 76, 187, s, 23, "m", (159, 197, 255))
    text(d, 54, 254, "手机也能成为", 82, "b", FG)
    x2 = 54 + lw("你的 ", 92, "b")
    text(d, 54, 366, "你的 ", 92, "b", FG)
    gw = gradient_text(img, x2, 366, "VibeKey", 92)
    text(d, x2 + gw + 6, 366, "。", 92, "b", FG)
    d = ImageDraw.Draw(img)
    text(d, 56, 500, "说完一句，字直接落到电脑光标处。", 31, "m", FG)
    text(d, 56, 550, "顺手点一下回车，Agent 就开始跑。", 31, "r", DIM)
    x = 56
    for t in ["手机当话筒", "远程回车", "历史重发", "局域网直连"]:
        x = chip(d, x, 632, t, 22, dot=ACCENT)
    glow(img, 250, 980, 340, BLUE, 60)
    d = ImageDraw.Draw(img)
    phone(img, 78, 740, 500, "04-recording.jpg")
    monitor(img, 640, 810, 360, 260)
    d = ImageDraw.Draw(img)
    line(d, 420, 960, 600, 960, ACCENT, 4)
    d.polygon([(sc(612), sc(960)), (sc(588), sc(948)), (sc(588), sc(972))], fill=ACCENT)
    text(d, 438, 908, "WiFi 直连", 25, "m", FG)
    text(d, 452, 982, "WebSocket", 19, "r", DIM)
    text(d, 56, 1272, "← 左滑看：它到底解决了哪些麻烦", 24, "r", DIM)
    save(img, "01-封面.png")

# ---------- 02 痛点 ----------
def pain():
    img = new_canvas()
    header(img, 2)
    d = ImageDraw.Draw(img)
    title(d, "这些麻烦，该结束了")
    subtitle(d, "台式机用户和 Agent 玩家的日常", 246)
    items = [
        ("mic", "电脑没麦克风", "想语音输入，先找麦、插线、调设备。\n台式机用户的痛，懂的都懂。"),
        ("coin", "VibeKey 要花钱", "专用硬件不便宜，还要等快递、\n占桌面。其实手机已经够用。"),
        ("swap", "手机说得快", "复制到电脑要切设备、翻聊天记录、\n再粘贴，思路早断了。"),
        ("enter", "Agent 卡在回车", "一句话说完，手还得挪回电脑\n按一次 Enter。"),
    ]
    for i, (ic, head, body) in enumerate(items):
        cx = 56 + (i % 2) * 494
        cy = 320 + (i // 2) * 356
        rr(d, cx, cy, 472, 330, 24, fill=CARD, outline=LINE, width=1)
        iconbox(d, cx + 26, cy + 28, 58, ic, RED_LT if i == 0 else (159, 197, 255))
        text(d, cx + 102, cy + 38, head, 31, "b", FG)
        line(d, cx + 26, cy + 112, cx + 446, cy + 112, LINE, 1)
        block(d, cx + 26, cy + 138, body, 25, 420, "r", DIM, 1.6)
    rr(d, 56, 1056, 968, 176, 24, fill=(20, 38, 68), outline=(47, 90, 160), width=1)
    rect(d, 56, 1056, 5, 176, fill=ACCENT)
    text(d, 92, 1084, "phone-VibeKey 只做一件事", 28, "m", (159, 197, 255))
    text(d, 92, 1134, "把手机上的字，送到电脑光标处。", 38, "b", FG)
    save(img, "02-痛点.png")

# ---------- 03 原理 ----------
def how():
    img = new_canvas()
    header(img, 3)
    d = ImageDraw.Draw(img)
    title(d, "手机说话，电脑落字")
    subtitle(d, "中间没有云，只有一张局域网", 246)
    steps = [
        ("PC 端跑一个小服务", "Windows 上一个 Python 进程，\n内存几十 MB，托盘里一个图标。"),
        ("扫码配对", "手机浏览器打开页面，\n加到主屏幕后像 App 一样点开。"),
        ("用输入法说话", "微信 / 豆包 / 讯飞 / Gboard 都行，\n边说边同步，不是说完才发。"),
        ("落到当前光标", "停约 1 秒自动收尾，\n松手约 2 秒，文字出现在光标处。"),
    ]
    y = 350
    line(d, 82, y + 16, 82, y + 3 * 208 + 16, LINE, 2)
    for i, (head, body) in enumerate(steps, 1):
        circle(d, 82, y + 16, 17, fill=(20, 38, 68), outline=ACCENT, width=2)
        text(d, 82 - lw(str(i), 22, "b") / 2, y + 3, str(i), 22, "b", (159, 197, 255))
        text(d, 122, y - 4, head, 31, "b", FG)
        block(d, 122, y + 48, body, 24, 420, "r", DIM, 1.55)
        y += 208
    glow(img, 800, 780, 340, BLUE, 55)
    phone(img, 610, 330, 880, "04-recording.jpg")
    d = ImageDraw.Draw(img)
    text(d, 610, 296, "手机端实拍", 21, "r", DIM)
    chip(d, 56, 1246, "增量同步 · 不重影 · 断线自动重连", 22, dot=GREEN)
    save(img, "03-原理.png")

# ---------- 04 说话时的状态 ----------
def recording():
    img = new_canvas()
    header(img, 4)
    d = ImageDraw.Draw(img)
    title(d, "一边说，电脑一边写")
    subtitle(d, "录音面板是输入法的，字却直接进电脑", 246)
    glow(img, 250, 780, 340, CYAN, 45)
    phone(img, 70, 330, 880, "04-recording.jpg")
    d = ImageDraw.Draw(img)
    text(d, 70, 296, "手机端实拍 · 正在说话", 21, "r", DIM)
    rows = [
        ("wave", "边说边同步", "文字增量发到电脑，\n不是等你说完才发。"),
        ("check", "松手即落字", "停顿约 1 秒自动收尾，\n松手约 2 秒上屏。"),
        ("enter", "连续说不断句", "句间停顿 1 秒内自动续写，\n不重影、不粘连。"),
        ("shield", "说错能撤回", "录音面板上滑撤回、松手编辑，\n都是输入法原生能力。"),
    ]
    y = 340
    for ic, head, body in rows:
        rr(d, 540, y, 484, 190, 22, fill=CARD, outline=LINE, width=1)
        iconbox(d, 562, y + 26, 52, ic)
        text(d, 632, y + 32, head, 29, "b", FG)
        block(d, 632, y + 84, body, 23, 370, "r", DIM, 1.55)
        y += 212
    chip(d, 540, 1246, "本软件不碰音频，只传文字", 22, dot=GREEN)
    save(img, "04-语音中.png")

# ---------- 05 Agent ----------
def agent():
    img = new_canvas()
    header(img, 5)
    d = ImageDraw.Draw(img)
    title(d, "给 Agent 玩家的加成")
    subtitle(d, "手机按回车，电脑 Agent 直接跑", 246)
    rows = [
        ("enter", "远程回车", "手机点「回车」，电脑真的敲一次 Enter，\n任务直接发出去。"),
        ("clear", "清空输入框", "按已落字数逐字退格，\n说错了不用动手删。"),
        ("history", "历史重发", "最近 10 条可编辑再发，\n改错不用整句重说。"),
        ("shield", "失败不丢字", "发送失败自动退回手机输入框，\n直接再发一次就行。"),
    ]
    y = 340
    for ic, head, body in rows:
        rr(d, 56, y, 500, 190, 22, fill=CARD, outline=LINE, width=1)
        iconbox(d, 78, y + 26, 52, ic)
        text(d, 148, y + 32, head, 30, "b", FG)
        block(d, 148, y + 84, body, 23, 380, "r", DIM, 1.55)
        y += 212
    glow(img, 800, 740, 320, CYAN, 40)
    history_panel(img, 590, 340, 434, 780)
    d = ImageDraw.Draw(img)
    text(d, 590, 306, "界面示意 · 最近记录", 21, "r", DIM)
    text(d, 56, 1256, "记录只存在手机本地，最多 10 条。", 22, "r", DIM)
    save(img, "05-Agent.png")

# ---------- 06 适用环境 ----------
def environment():
    img = new_canvas()
    header(img, 6)
    d = ImageDraw.Draw(img)
    title(d, "先看环境，再看体验")
    subtitle(d, "别在不支持的场景里浪费时间", 246)
    rr(d, 56, 320, 472, 830, 24, fill=CARD, outline=(29, 94, 51), width=1)
    rr(d, 552, 320, 472, 830, 24, fill=CARD, outline=(94, 42, 42), width=1)
    iconbox(d, 82, 348, 52, "check", GREEN_LT)
    text(d, 150, 356, "能 用", 36, "b", GREEN_LT)
    iconbox(d, 578, 348, 52, "x", RED_LT)
    text(d, 646, 356, "不 支 持", 36, "b", RED_LT)
    yes = ["Windows 10/11 + Python 3.10+", "手机和电脑在同一局域网",
           "同一 WiFi / 同一路由器", "PC 有线 + 手机 WiFi",
           "双路由 NAT / 手机热点", "微信 / Office / VS Code"]
    no = ["4G/5G 跨公网（无中继）", "管理员窗口 / 游戏反作弊",
          "远程桌面 / 锁屏登录界面", "AP 隔离 / 访客网络",
          "校园网客户端隔离", "macOS / Linux 电脑"]
    for i, t in enumerate(yes):
        yy = 452 + i * 110
        circle(d, 100, yy + 15, 11, fill=(16, 51, 30))
        line(d, 94, yy + 15, 98, yy + 20, GREEN_LT, 2)
        line(d, 98, yy + 20, 107, yy + 9, GREEN_LT, 2)
        block(d, 126, yy, t, 24, 370, "r", FG, 1.4)
    for i, t in enumerate(no):
        yy = 452 + i * 110
        circle(d, 596, yy + 15, 11, fill=(51, 20, 20))
        line(d, 590, yy + 9, 602, yy + 21, RED_LT, 2)
        line(d, 602, yy + 9, 590, yy + 21, RED_LT, 2)
        block(d, 622, yy, t, 24, 370, "r", FG, 1.4)
    rr(d, 56, 1186, 968, 96, 20, fill=CARD2, outline=LINE, width=1)
    text(d, 82, 1202, "手机不限 iOS / Android，但输入法必须自带语音功能。", 24, "r", FG)
    text(d, 82, 1242, "文字只走局域网，不出网段。", 22, "r", DIM)
    save(img, "06-适用.png")

# ---------- 07 上手 ----------
def setup():
    img = new_canvas()
    header(img, 7)
    d = ImageDraw.Draw(img)
    title(d, "三步上手")
    subtitle(d, "Windows 10/11 · Python 3.10+ · 不用 .NET / Node", 246)
    steps = [
        ("1", "装依赖并启动", "进入 pc 目录安装依赖，双击「启动.cmd」。", "pip install -r requirements.txt"),
        ("2", "扫码配对", "托盘菜单 → 显示配对二维码，\n手机相机扫一扫，页面自动打开。", None),
        ("3", "加到主屏幕", "手机浏览器菜单 → 添加到主屏幕，\n以后点桌面图标，说话就落字。", None),
    ]
    y = 330
    for num, head, body, code in steps:
        rr(d, 56, y, 968, 226, 24, fill=CARD, outline=LINE, width=1)
        circle(d, 116, y + 60, 30, fill=(20, 38, 68), outline=ACCENT, width=2)
        text(d, 116 - lw(num, 34, "b") / 2, y + 39, num, 34, "b", (159, 197, 255))
        text(d, 176, y + 34, head, 34, "b", FG)
        block(d, 176, y + 94, body, 25, 800, "r", DIM, 1.5)
        if code:
            cw = lw(code, 23) + 34
            rr(d, 176, y + 146, cw, 44, 10, fill=(10, 17, 34), outline=LINE, width=1)
            text(d, 193, y + 155, code, 23, "r", (125, 211, 252))
        y += 252
    rr(d, 56, 1084, 560, 210, 22, fill=CARD2, outline=LINE, width=1)
    iconbox(d, 80, 1104, 48, "shield", (240, 220, 168))
    text(d, 146, 1108, "手机连不上？", 27, "b", FG)
    block(d, 146, 1152, "托盘菜单点「修复手机连不上（防火墙）」，\n一键放行，不用手输命令。", 22, 450, "r", DIM, 1.5)
    rr(d, 640, 1084, 384, 210, 18, fill=(7, 11, 22), outline=LINE, width=1)
    cap = "电脑托盘菜单实拍"
    text(d, 640 + (384 - lw(cap, 19)) / 2, 1098, cap, 19, "r", DIM)
    im = Image.open(os.path.join(SHOTS, "03-tray.png")).convert("RGB")
    tw_ = 270
    th_ = int(im.height * tw_ / im.width)
    im = im.resize((sc(tw_), sc(th_)), Image.Resampling.LANCZOS)
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, im.width - 1, im.height - 1], radius=sc(10), fill=255)
    img.paste(im, (sc(640 + (384 - tw_) / 2), sc(1128)), mask)
    save(img, "07-上手.png")

# ---------- 08 隐私 ----------
def privacy():
    img = new_canvas()
    header(img, 8)
    d = ImageDraw.Draw(img)
    title(d, "它不碰你的语音")
    subtitle(d, "为什么不自己写一个语音输入法？", 246)
    rows = [
        ("wave", "识别交给输入法", "微信输入法 / 豆包 / 讯飞的语音识别，\n比自建 ASR 更快、更准、更省事。"),
        ("mic", "不采集不传音频", "本软件不录音、不发送、不存储任何语音。\n识别结果来自你的输入法本身。"),
        ("lock", "文字不出局域网", "手机直连电脑，不走服务器、没有月费。\nMIT 开源，代码可查。"),
    ]
    y = 330
    for ic, head, body in rows:
        rr(d, 56, y, 968, 250, 24, fill=CARD, outline=LINE, width=1)
        iconbox(d, 86, y + 34, 64, ic)
        text(d, 180, y + 40, head, 35, "b", FG)
        line(d, 180, y + 106, 994, y + 106, LINE, 1)
        block(d, 180, y + 132, body, 26, 800, "r", DIM, 1.55)
        y += 280
    rr(d, 56, 1190, 968, 92, 22, fill=(20, 38, 68), outline=(47, 90, 160), width=1)
    text(d, 86, 1216, "它是桥，不是识别引擎。", 32, "b", FG)
    s = "MIT 开源 · 零月费"
    text(d, 1024 - 30 - lw(s, 26, "m"), 1224, s, 26, "m", (159, 197, 255))
    save(img, "08-隐私.png")

# ---------- 09 收尾 ----------
def ending():
    img = new_canvas()
    header(img, 9)
    d = ImageDraw.Draw(img)
    glow(img, 540, 420, 420, BLUE, 80)
    logo(img, 480, 218, 120)
    d = ImageDraw.Draw(img)
    s = "别买硬件了"
    text(d, (W - lw(s, 40, "m")) / 2, 396, s, 40, "m", DIM)
    s = "手机也能成为"
    text(d, (W - lw(s, 82, "b")) / 2, 476, s, 82, "b", FG)
    w1 = lw("你的 ", 92, "b")
    w2 = lw("VibeKey", 92, "b")
    w3 = lw("。", 92, "b")
    x = (W - w1 - w2 - w3) / 2
    text(d, x, 590, "你的 ", 92, "b", FG)
    gradient_text(img, x + w1, 590, "VibeKey", 92)
    d = ImageDraw.Draw(img)
    text(d, x + w1 + w2 + 6, 590, "。", 92, "b", FG)
    s = "开源 · MIT · 零月费 · Windows 10/11"
    text(d, (W - lw(s, 27)) / 2, 742, s, 27, "r", DIM)
    chips = ["没麦的台式机", "高频 Agent 用户", "开源折腾党"]
    ws = [lw(t, 23) + 52 for t in chips]
    x = (W - sum(ws) - 2 * 16) / 2
    for t, w in zip(chips, ws):
        rr(d, x, 816, w, 50, 25, fill=CARD2, outline=LINE, width=1)
        text(d, x + 26, 827, t, 23, "m", FG)
        x += w + 16
    rr(d, 120, 940, 840, 240, 28, fill=CARD, outline=(47, 90, 160), width=2)
    s = "想要部署教程？"
    text(d, (W - lw(s, 30)) / 2, 978, s, 30, "r", DIM)
    s = "评论区留言「语音」"
    text(d, (W - lw(s, 48, "b")) / 2, 1036, s, 48, "b", FG)
    s = "拿到仓库链接后，在置顶评论补上地址"
    text(d, (W - lw(s, 21)) / 2, 1124, s, 21, "r", FAINT)
    s = "phone-VibeKey v0.7.1 · 扫码配对 · 局域网直连"
    text(d, (W - lw(s, 23)) / 2, 1252, s, 23, "r", DIM)
    save(img, "09-收尾.png")

for fn in [cover, pain, how, recording, agent, environment, setup, privacy, ending]:
    fn()
print("ALL DONE")
