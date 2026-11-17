"""phone-VibeKey 小红书宣传图 v3 — 纸面 / 墨色 / 朱红，编辑手册式排版。

规则来源：impeccable（单一视觉世界、角色化字阶、细线而非卡片堆叠、
真实产品截图而非手绘假 UI、克制的强调色）。
运行：python 生成图片.py  →  输出 01..09 (1080x1440)
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os, re

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(BASE, "..", ".."))
SHOTS = os.path.join(ROOT, "docs", "screenshots")
FDIR = "C:/Windows/Fonts/"
F = {
    "r": FDIR + "Noto Sans SC (TrueType).otf",
    "m": FDIR + "Noto Sans SC Medium (TrueType).otf",
    "b": FDIR + "Noto Sans SC Bold (TrueType).otf",
    "serif": FDIR + "NotoSerifSC-VF.ttf",
    "mono": FDIR + "consola.ttf",
}

W, H, S = 1080, 1440, 2
PAPER = (245, 242, 234)
PAPER_2 = (238, 234, 223)
INK = (20, 19, 15)
DIM = (88, 86, 78)
FAINT = (140, 137, 126)
RULE = (214, 209, 195)
ACCENT = (191, 60, 41)
ACCENT_SOFT = (238, 219, 210)
OK = (46, 104, 68)
M = 96            # 页边距
CW = W - M * 2    # 内容宽 888

_fc = {}
_probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))

def sc(v): return int(round(v * S))

def ft(size, w="r"):
    k = (w, size)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(F[w], sc(size))
    return _fc[k]

def tw(s, font): return _probe.textlength(s, font=font) / S

def text(d, x, y, s, size, w="r", fill=INK, tracking=0.0):
    """tracking 以 em 为单位，逐字排版（中文标题收紧字距用）。"""
    if tracking == 0:
        d.text((sc(x), sc(y)), s, font=ft(size, w), fill=fill)
        return tw(s, ft(size, w))
    cx = x
    f = ft(size, w)
    for ch in s:
        d.text((sc(cx), sc(y)), ch, font=f, fill=fill)
        cx += tw(ch, f) + size * tracking
    return cx - x

_CJK_BREAK_AFTER = set("，。、；：！？）】」』…%·")
_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_\-\.:/@]*|\s+|.", re.S)

def wrap(s, size, w, max_w, tracking=0.0):
    f = ft(size, w)
    out = []
    for para in s.split("\n"):
        if not para:
            out.append("")
            continue
        cur = ""
        for tok in _TOKEN.findall(para):
            add = tw(tok, f) + (size * tracking * len(tok))
            if cur and tw(cur, f) + add > max_w and tok not in _CJK_BREAK_AFTER:
                out.append(cur.rstrip())
                cur = tok.lstrip()
            else:
                cur += tok
        out.append(cur.rstrip())
    return out

def block(d, x, y, s, size, max_w, w="r", fill=DIM, lh=1.62, tracking=0.0, max_lines=None):
    ls = wrap(s, size, w, max_w, tracking)
    if max_lines:
        ls = ls[:max_lines]
    step = size * lh
    for i, ln in enumerate(ls):
        text(d, x, y + i * step, ln, size, w, fill, tracking)
    return y + step * len(ls)

def rule(d, x, y, w, color=RULE, t=1.5):
    d.rectangle([sc(x), sc(y), sc(x + w), sc(y + t)], fill=color)

CJK = re.compile(r"[一-鿿]")

def label(d, x, y, s, color=FAINT, size=24, w=None):
    """拉丁用等宽 + 宽字距；含中文时换 Noto 并收窄字距，避免豆腐块。"""
    if w is None:
        if CJK.search(s):
            return text(d, x, y, s, size, "m", color, tracking=0.04)
        return text(d, x, y, s.upper(), size, "mono", color, tracking=0.16)
    return text(d, x, y, s, size, w, color, tracking=0.04)

def page(d, n, total=9):
    label(d, W - M - 78, H - 74, f"{n:02d} / {total:02d}", FAINT, 22)
    text(d, M, H - 78, "phone-VibeKey", 22, "m", FAINT, tracking=0.02)

def canvas(bg=PAPER):
    img = Image.new("RGB", (sc(W), sc(H)), bg)
    return img, ImageDraw.Draw(img)

def rounded_mask(w, h, r):
    m = Image.new("L", (sc(w), sc(h)), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, sc(w) - 1, sc(h) - 1], radius=sc(r), fill=255)
    return m

def shot(img, path, x, y, w, r=26, border=RULE, shadow=True):
    src = Image.open(path).convert("RGB")
    h = int(w * src.height / src.width)
    src = src.resize((sc(w), sc(h)), Image.Resampling.LANCZOS)
    if shadow:
        sh = Image.new("RGB", (sc(w) + sc(40), sc(h) + sc(40)), PAPER)
        ImageDraw.Draw(sh).rounded_rectangle(
            [sc(20), sc(24), sc(w) + sc(20), sc(h) + sc(24)], radius=sc(r), fill=(226, 221, 209))
        sh = sh.filter(ImageFilter.GaussianBlur(sc(9)))
        img.paste(sh, (sc(x) - sc(20), sc(y) - sc(22)))
    m = rounded_mask(w, h, r)
    img.paste(src, (sc(x), sc(y)), m)
    if border:
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([sc(x), sc(y), sc(x + w), sc(y + h)], radius=sc(r),
                            outline=border, width=sc(1.2))
    return h

def checkbox(d, x, y, size, kind="yes"):
    c = OK if kind == "yes" else ACCENT
    if kind == "yes":
        d.rounded_rectangle([sc(x), sc(y), sc(x + size), sc(y + size)], radius=sc(size * .22),
                            outline=c, width=sc(1.6))
        d.line([(sc(x + size * .26), sc(y + size * .53)),
                (sc(x + size * .45), sc(y + size * .71)),
                (sc(x + size * .76), sc(y + size * .31))], fill=c, width=sc(2.2))
    else:
        d.line([(sc(x + size * .28), sc(y + size * .28)), (sc(x + size * .72), sc(y + size * .72))],
               fill=c, width=sc(2.2))
        d.line([(sc(x + size * .72), sc(y + size * .28)), (sc(x + size * .28), sc(y + size * .72))],
               fill=c, width=sc(2.2))

def save(img, name):
    img.resize((W, H), Image.Resampling.LANCZOS).save(os.path.join(BASE, name), optimize=True)
    print("wrote", name)

REPO = "github.com/jm17647-dna/phone-VibeKey"
VER = "v0.7.6"

def head(d, kicker, title, y=250, size=86, color=INK, lh=1.2, max_w=None):
    label(d, M, y - 62, kicker, ACCENT, 22)
    return block(d, M, y, title, size, max_w or CW, "b", color, lh, tracking=-0.015)


def cover():
    img, d = canvas()
    label(d, M, 96, "open source · mit", ACCENT, 24)
    text(d, W - M - 118, 96, VER, 24, "mono", FAINT, tracking=0.1)
    rule(d, M, 152, CW)

    y = 300
    y2 = block(d, M, y, "手机就是", 150, CW, "b", INK, 1.14, tracking=-0.03)
    y2 = block(d, M, y2 + 6, "你的 VibeKey。", 150, CW, "b", INK, 1.14, tracking=-0.03)
    rule(d, M, y2 + 54, 180, ACCENT, 4)

    block(d, M, y2 + 104, "说完一句，字落在电脑光标处。", 38, 560, "m", DIM, 1.55)
    block(d, M, y2 + 172, "回车一按，Agent 就开始跑。", 38, 560, "m", DIM, 1.55)

    shot(img, os.path.join(SHOTS, "05-ui-076.png"), 646, 986, 356, r=28)

    label(d, M, H - 152, "windows 10 / 11 · python 3.10+", FAINT, 21)
    text(d, M, H - 108, "github.com/jm17647-dna", 24, "mono", INK, tracking=0.01)
    text(d, M, H - 70, "phone-VibeKey", 24, "mono", INK, tracking=0.01)
    save(img, "01-封面.png")


def pain():
    img, d = canvas()
    head(d, "01 — 麻烦", "为了一句语音输入，\n要先做四件事。", 250, 84)
    items = [
        ("01", "找麦克风", "台式机、瘦客户机根本没有，得先翻抽屉。"),
        ("02", "买硬件", "VibeKey 这类专用键，要花钱、等快递、占桌面。"),
        ("03", "换设备倒字", "手机说完，切到电脑，翻聊天记录，再粘贴。"),
        ("04", "手离开杯子", "用 Agent 时，最后一下回车还是得回键盘上按。"),
    ]
    y = 600
    for num, t, s in items:
        rule(d, M, y, CW)
        text(d, M, y + 30, num, 28, "mono", ACCENT, tracking=0.1)
        text(d, M + 96, y + 24, t, 38, "b", INK, tracking=-0.005)
        block(d, M + 96, y + 84, s, 30, CW - 120, "r", DIM, 1.6, max_lines=1)
        y += 148
    rule(d, M, y, CW)

    block(d, M, y + 50, "这四件事，现在一件都不用做。", 44, CW - 40, "b", INK, 1.4, tracking=-0.01)
    page(d, 2)
    save(img, "02-痛点.png")


def flow():
    img, d = canvas()
    head(d, "02 — 链路", "链路很短：\n手机 → 路由器 → 电脑。", 250, 84)

    y = 660
    bw, bh, gap = 250, 210, 44
    boxes = [("01", "手机浏览器", "打开就是界面\n不装 App"), ("02", "同一局域网", "WebSocket\n只走内网"), ("03", "PC 托盘进程", "写剪贴板\n粘贴到光标")]
    for i, (n, t, s) in enumerate(boxes):
        x = M + i * (bw + gap + 24)
        d.rounded_rectangle([sc(x), sc(y), sc(x + bw), sc(y + bh)], radius=sc(18), outline=RULE, width=sc(1.4))
        text(d, x + 24, y + 22, n, 24, "mono", ACCENT, tracking=0.1)
        text(d, x + 24, y + 60, t, 34, "b", INK, tracking=-0.01)
        block(d, x + 24, y + 118, s, 26, bw - 48, "r", DIM, 1.5)
        if i < 2:
            ax = x + bw + 12
            d.line([(sc(ax), sc(y + bh / 2)), (sc(ax + 36), sc(y + bh / 2))], fill=FAINT, width=sc(1.6))
            d.line([(sc(ax + 28), sc(y + bh / 2 - 7)), (sc(ax + 36), sc(y + bh / 2)),
                    (sc(ax + 28), sc(y + bh / 2 + 7))], fill=FAINT, width=sc(1.6))

    rule(d, M, 960, CW)
    block(d, M, 1000, "识别发生在你手机里的输入法上；这个工具只搬运文字，不碰音频，也不经过云。",
          32, CW - 40, "r", DIM, 1.7)
    text(d, M, 1160, "松手 → 落字 ≈ 2s", 44, "b", INK, tracking=-0.01)
    label(d, M, 1232, "在同一局域网内实测", FAINT, 22)
    page(d, 3)
    save(img, "03-原理.png")


def speaking():
    img, d = canvas()
    head(d, "03 — 说话", "边说边出字，\n松手就落字。", 250, 84, max_w=620)

    h = shot(img, os.path.join(SHOTS, "04-recording.jpg"), M, 646, 300, r=26)
    x2 = M + 300 + 72
    rows = [("用哪个语音", "手机输入法自己的就行：微信、豆包、讯飞、Gboard。"),
            ("不重影", "连续说几句，按顺序各落一段，不粘连、不重复。"),
            ("不丢字", "发送失败会自动退回输入框，改完再发一次。")]
    y = 680
    for t, s in rows:
        text(d, x2, y, t, 34, "b", INK, tracking=-0.01)
        y = block(d, x2, y + 56, s, 28, W - M - x2, "r", DIM, 1.65) + 34
    page(d, 4)
    save(img, "04-语音中.png")


def agent():
    img, d = canvas()
    head(d, "04 — 交给 Agent", "按一下回车，\n电脑敲一次 Enter。", 250, 82, max_w=700)

    y = 640
    feats = [("回车 ⏎", "手机点一下，或输入法上按换行，电脑直接回车。"),
             ("清空电脑输入框", "说错了，一键退掉刚才落下去的那段字。"),
             ("最近 10 条", "可编辑、可重发、可单条删除，清空前会确认。")]
    for t, s in feats:
        rule(d, M, y, 620)
        text(d, M, y + 26, t, 34, "b", INK, tracking=-0.01)
        block(d, M, y + 80, s, 27, 590, "r", DIM, 1.6, max_lines=2)
        y += 158
    rule(d, M, y, 620)

    shot(img, os.path.join(SHOTS, "06-history-076.png"), 720, 636, 264, r=24)
    page(d, 5)
    save(img, "05-Agent.png")


def env():
    img, d = canvas()
    head(d, "05 — 适用", "能用 / 不能用，\n先说清楚。", 250, 84)

    y = 640
    text(d, M, y, "能", 30, "b", OK, tracking=0.04)
    rule(d, M, y + 52, 400, RULE)
    yes = ["同一 WiFi，PC 有线也行", "双路由 NAT、手机热点给电脑", "微信 / 钉钉 / 飞书 / Word", "浏览器、VS Code、终端输入框"]
    yy = y + 78
    for s in yes:
        checkbox(d, M, yy + 4, 26, "yes")
        yy = block(d, M + 44, yy, s, 27, 372, "r", DIM, 1.55) + 26

    x2 = W / 2 + 20
    text(d, x2, y, "不能", 30, "b", ACCENT, tracking=0.04)
    rule(d, x2, y + 52, W - M - x2, RULE)
    no = ["手机流量在外、不在同一张网", "管理员窗口 / 游戏 / 远程桌面", "AP 隔离的访客网络、公司校园网", "macOS / Linux 电脑（只做 Windows）"]
    yy = y + 78
    for s in no:
        checkbox(d, x2, yy + 4, 26, "no")
        yy = block(d, x2 + 44, yy, s, 27, W - M - x2 - 44, "r", DIM, 1.55) + 26

    rule(d, M, 1226, CW)
    block(d, M, 1252, "不支持的部分都是真话，不用等买回来才发现。", 30, CW, "m", INK, 1.5)
    page(d, 6)
    save(img, "06-适用.png")


def start():
    img, d = canvas()
    head(d, "06 — 上手", "三步，五分钟。", 250, 86)

    y = 620
    steps = [("01", "装依赖", "python -m pip install -r pc/requirements.txt"),
             ("02", "双击启动", "pc\\启动.cmd   托盘里出现图标"),
             ("03", "扫码配对", "托盘 → 显示配对二维码 → 手机扫 → 加主屏幕")]
    for n, t, code in steps:
        text(d, M, y, n, 26, "mono", ACCENT, tracking=0.1)
        text(d, M + 78, y - 4, t, 36, "b", INK, tracking=-0.01)
        d.rounded_rectangle([sc(M + 78), sc(y + 62), sc(W - M), sc(y + 132)], radius=sc(12),
                            fill=PAPER_2, outline=RULE, width=sc(1.2))
        cw = "mono" if not CJK.search(code) else "r"
        text(d, M + 102, y + 84, code, 24 if cw == "mono" else 26, cw, INK)
        y += 208

    rule(d, M, y + 6, CW)
    block(d, M, y + 36, "连不上就点托盘里的「修复手机连不上（防火墙）」。",
          27, CW - 60, "r", DIM, 1.6)
    page(d, 7)
    save(img, "07-上手.png")


def privacy():
    img, d = canvas()
    label(d, M, 250, "07 — 隐私", ACCENT, 22)
    block(d, M, 300, "不录音，\n不传音频，\n不经过云。", 96, CW, "serif", INK, 1.3, tracking=-0.01)

    rule(d, M, 800, CW)
    facts = [("只搬文字", "音频始终留在你手机里，工具只收到识别后的文本。"),
             ("只到同网段", "文字从手机发给局域网里的那台电脑，没有中转服务器。"),
             ("零月费", "MIT 开源，代码全公开，随时可以自己改、自己审计。")]
    y = 850
    for t, s in facts:
        text(d, M, y, t, 34, "b", INK, tracking=-0.01)
        y = block(d, M, y + 56, s, 28, CW - 60, "r", DIM, 1.65) + 40
    label(d, M, H - 150, "输入法本身是否把音频上云，取决于你用的输入法", FAINT, 21)
    page(d, 8)
    save(img, "08-隐私.png")


def ending():
    img, d = canvas()
    head(d, "08 — 仓库", "代码在这里。", 250, 92)

    import qrcode
    qr = qrcode.QRCode(version=None, box_size=12, border=0,
                       error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data("https://" + REPO)
    qr.make(fit=True)
    qimg = qr.make_image(fill_color=INK, back_color=PAPER).convert("RGB")
    qw = 340
    qimg = qimg.resize((sc(qw), sc(qw)), Image.Resampling.NEAREST)
    img.paste(qimg, (sc(M), sc(560)))

    x2 = M + 340 + 72
    label(d, x2, 566, "github", FAINT, 22)
    block(d, x2, 606, "jm17647-dna/\nphone-VibeKey", 40, W - M - x2, "b", INK, 1.3, tracking=-0.01)
    block(d, x2, 760, "MIT 协议 · 零月费\nWindows 10/11 · Python 3.10+", 26, W - M - x2, "r", DIM, 1.7)

    rule(d, M, 1040, CW)
    block(d, M, 1080, "有问题评论区问，看到就回。", 46, CW, "b", INK, 1.4, tracking=-0.01)
    block(d, M, 1160, "部署步骤、防火墙、连不上的排查，都可以直接问。", 28, CW - 40, "r", DIM, 1.6)
    page(d, 9, 9)
    save(img, "09-收尾.png")


if __name__ == "__main__":
    cover(); pain(); flow(); speaking(); agent(); env(); start(); privacy(); ending()
    print("done")
