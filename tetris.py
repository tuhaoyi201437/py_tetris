"""
俄罗斯方块 (Tetris) - Python + tkinter 实现（零依赖，标准库即可运行）

运行方式（无需安装任何包）：
    python tetris.py

控制说明：
    ← / →   左右移动
    ↓       软降（加速下落）
    空格     硬降（直接落到底）
    ↑ / X   顺时针旋转
    Z       逆时针旋转
    P / ESC  暂停 / 继续
    R       重新开始
    Alt+W   关闭游戏

游戏流程：启动后先显示开始界面，点击「开始游戏」按钮（或按回车）进入游戏；
游戏进行中可点击右侧面板底部的「退出」按钮或按 Alt+W 关闭窗口；
点击「彩色模式 / 黑白模式」按钮可随时切换经典彩色与深色（黑底灰块）配色；
点击「设置」按钮可调整粒子数量、切换彩色/黑白模式，设置会记忆到本地文件。
"""

import base64
import colorsys
import json
import math
import os
import random
import struct
import tkinter as tk
import tkinter.font as tk_font
import zlib
from tkinter import messagebox

# ----------------------------- 配置 -----------------------------
COLUMNS = 10          # 游戏区列数
ROWS = 20             # 游戏区行数
CELL = 30             # 每个格子像素大小
CELL_CUT = 6          # 方块格子的切角大小（四角按 45° 直线切掉，呈八边形）
PANEL_W = 180         # 右侧信息面板宽度
DEFAULT_BG_COLOR = "#e2f3ff"   # 彩色模式棋盘的默认纯蓝色背景

# 7 种方块颜色 (Tetromino)
SHAPES = {
    "I": (0, 240, 240),
    "O": (240, 240, 0),
    "T": (170, 0, 240),
    "S": (0, 240, 0),
    "Z": (240, 0, 0),
    "J": (0, 100, 240),
    "L": (240, 160, 0),
}

# 每个方块 4 个旋转朝向的 (x, y) 相对偏移
ROTATIONS = {
    "I": [
        [(0, 1), (1, 1), (2, 1), (3, 1)],
        [(2, 0), (2, 1), (2, 2), (2, 3)],
        [(0, 2), (1, 2), (2, 2), (3, 2)],
        [(1, 0), (1, 1), (1, 2), (1, 3)],
    ],
    "O": [[(1, 0), (2, 0), (1, 1), (2, 1)]],
    "T": [
        [(1, 0), (0, 1), (1, 1), (2, 1)],
        [(1, 0), (1, 1), (2, 1), (1, 2)],
        [(0, 1), (1, 1), (2, 1), (1, 2)],
        [(1, 0), (0, 1), (1, 1), (1, 2)],
    ],
    "S": [
        [(1, 0), (2, 0), (0, 1), (1, 1)],
        [(1, 0), (1, 1), (2, 1), (2, 2)],
        [(1, 1), (2, 1), (0, 2), (1, 2)],
        [(0, 0), (0, 1), (1, 1), (1, 2)],
    ],
    "Z": [
        [(0, 0), (1, 0), (1, 1), (2, 1)],
        [(2, 0), (1, 1), (2, 1), (1, 2)],
        [(0, 1), (1, 1), (1, 2), (2, 2)],
        [(1, 0), (0, 1), (1, 1), (0, 2)],
    ],
    "J": [
        [(0, 0), (0, 1), (1, 1), (2, 1)],
        [(1, 0), (1, 1), (1, 2), (2, 0)],
        [(0, 1), (1, 1), (2, 1), (2, 2)],
        [(1, 0), (1, 1), (0, 2), (1, 2)],
    ],
    "L": [
        [(2, 0), (0, 1), (1, 1), (2, 1)],
        [(1, 0), (1, 1), (1, 2), (2, 2)],
        [(0, 1), (1, 1), (2, 1), (0, 2)],
        [(0, 0), (1, 0), (1, 1), (1, 2)],
    ],
}

SHAPE_NAMES = list(SHAPES.keys())

# 主题：classic 为原彩色风格；dark 为黑底灰块风格（方块用不同灰度区分形状）
THEMES = {
    "classic": {
        "bg_root": "#101018",
        "bg_board": DEFAULT_BG_COLOR,  # 彩色模式棋盘默认底色（可在设置里自定义）
        "bg_panel": "#191921",
        "grid": "#a9cdea",        # 网格线（仅在未自定义底色时作为兜底）
        "pieces": dict(SHAPES),
        "text": "#ffffff",        # 面板文字颜色（彩色模式）
        "title": "#cfcfd8",       # “下一个”等小标题
    },
    "dark": {
        # 黑白模式：背景纯黑、方块深灰、按钮深灰
        "bg_root": "#000000",
        "bg_board": "#000000",
        "bg_panel": "#000000",
        "grid": "#1a1a1a",
        "pieces": {               # 方块统一深灰色（用亮灰边框区分轮廓）
            "I": (80, 80, 80),
            "O": (80, 80, 80),
            "T": (80, 80, 80),
            "S": (80, 80, 80),
            "Z": (80, 80, 80),
            "J": (80, 80, 80),
            "L": (80, 80, 80),
        },
        "text": "#8a8a8a",        # 黑色上的文字为深灰色
        "title": "#8a8a8a",
    },
}

# ----------------------------- 设置（本地记忆） -----------------------------
SETTINGS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "tetris_settings.json")
DEFAULT_SETTINGS = {"particle_count": 3, "theme": "classic", "cell_cut": CELL_CUT,
                    "bg_color": DEFAULT_BG_COLOR}


def load_settings():
    """从本地文件读取设置；文件缺失或内容异常时回退到默认值。"""
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return dict(DEFAULT_SETTINGS)
    s = dict(DEFAULT_SETTINGS)
    try:
        if isinstance(data.get("particle_count"), int):
            s["particle_count"] = max(0, min(12, int(data["particle_count"])))
        if isinstance(data.get("cell_cut"), int):
            s["cell_cut"] = max(0, min(12, int(data["cell_cut"])))
        if data.get("theme") in THEMES:
            s["theme"] = data["theme"]
        bg = data.get("bg_color")
        if isinstance(bg, str) and is_hex_color(bg):
            s["bg_color"] = bg.lower()
    except Exception:
        pass
    return s


def save_settings(s):
    """把设置写入本地文件（失败不影响游戏）。"""
    try:
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(s, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def hex_color(rgb):
    return "#%02x%02x%02x" % rgb


# ----------------------------- 颜色小工具 -----------------------------
def is_hex_color(s):
    """判断字符串是否为 '#rrggbb' 形式的颜色。"""
    if not isinstance(s, str) or len(s) != 7 or not s.startswith("#"):
        return False
    try:
        int(s[1:], 16)
    except ValueError:
        return False
    return True


def hex_to_rgb(s):
    """把 '#rrggbb' 解析成 (r, g, b)；解析失败时返回白色。"""
    if not is_hex_color(s):
        return (255, 255, 255)
    return (int(s[1:3], 16), int(s[3:5], 16), int(s[5:7], 16))


def rgb_to_hex(rgb):
    """把 (r, g, b) 转成 '#rrggbb'，越界值会被夹紧到 0–255。"""
    return hex_color(tuple(max(0, min(255, int(v))) for v in rgb))


def mix_rgb(a, b, t):
    """把颜色 a 按比例 t（0–1）混向颜色 b。"""
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def luminance(rgb):
    """感知亮度（0–255）。"""
    return 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]


def is_light(rgb):
    """颜色是否偏亮（用来决定文字用深色还是浅色）。"""
    return luminance(rgb) > 150


def contrast_color(rgb, amount=0.24):
    """返回底色上可见的网格线颜色：亮底压暗、暗底提亮。"""
    return mix_rgb(rgb, (0, 0, 0), amount) if is_light(rgb) \
        else mix_rgb(rgb, (255, 255, 255), amount)


def hsv_square_png(hue, w, h):
    """生成「横轴饱和度、纵轴明度」渐变方块的 PNG 字节（用于设置里的取色器）。

    纯标准库实现：手写 PNG 结构 + zlib 压缩，再由 Tk 直接解码显示。
    """
    raw = bytearray()
    for y in range(h):
        v = 1.0 - y / max(1, h - 1)
        raw.append(0)                      # 每行的 filter 字节
        for x in range(w):
            s = x / max(1, w - 1)
            r, g, b = colorsys.hsv_to_rgb(hue, s, v)
            raw += bytes((int(r * 255 + 0.5), int(g * 255 + 0.5), int(b * 255 + 0.5)))

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff))

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes(raw), 6)) + chunk(b"IEND", b""))


def _cjk_font_name():
    """挑选系统中存在的中文字体，保证中文不被显示成方块。"""
    try:
        families = list(tk_font.families())
    except Exception:
        return "Microsoft YaHei"
    # 按优先级尝试常见中文字体
    for name in ("Microsoft YaHei", "微软雅黑", "SimHei", "黑体",
                 "SimSun", "宋体", "NSimSun", "Microsoft JhengHei",
                 "MingLiU", "Arial Unicode MS"):
        if name in families:
            return name
    return "TkDefaultFont"


CJK_FONT = "Microsoft YaHei"  # 默认回退，__init__ 中会用系统中真实存在的字体覆盖


def F(size, weight="normal"):
    """构造使用中文金属的字体元组。"""
    return (CJK_FONT, size, weight)


class Piece:
    """下落中的方块。"""

    def __init__(self, name):
        self.name = name
        self.color = SHAPES[name]
        self.template = ROTATIONS[name]
        self.rotation = 0
        self.x = COLUMNS // 2 - 2
        self.y = -1 if name == "I" else 0

    def cells(self):
        return [(self.x + dx, self.y + dy) for (dx, dy) in self.template[self.rotation]]

    def next_rotation(self, direction):
        n = len(self.template)
        return (self.rotation + (1 if direction == 1 else -1)) % n


class Tetris:
    def __init__(self):
        self.reset()

    def reset(self):
        self.board = [[None for _ in range(COLUMNS)] for _ in range(ROWS)]
        self.score = 0
        self.level = 1
        self.lines = 0
        self.game_over = False
        self.paused = False
        self.current = self._new_piece()
        self.next_piece = self._new_piece()
        self.fall_speed = 500
        self.fall_time = 0
        self.state = "play"          # play | clearing
        self.clear_anim = None       # 消行塌落动画数据
        self.pending_clears = []     # 待生成粒子的消行信息

    def toggle_pause(self):
        if not self.game_over:
            self.paused = not self.paused

    def _new_piece(self):
        return Piece(random.choice(SHAPE_NAMES))

    def _valid(self, piece, rotation, ox=0, oy=0):
        for (dx, dy) in piece.template[rotation]:
            x = piece.x + dx + ox
            y = piece.y + dy + oy
            if x < 0 or x >= COLUMNS or y >= ROWS:
                return False
            if y >= 0 and self.board[y][x] is not None:
                return False
        return True

    def move(self, dx):
        if self.paused or self.game_over or self.state == "clearing":
            return
        if self._valid(self.current, self.current.rotation, dx, 0):
            self.current.x += dx

    def rotate(self, direction):
        if self.paused or self.game_over or self.state == "clearing":
            return
        nr = self.current.next_rotation(direction)
        for kick in (0, -1, 1, -2, 2):
            if self._valid(self.current, nr, kick, 0):
                self.current.x += kick
                self.current.rotation = nr
                return

    def soft_drop(self):
        if self.paused or self.game_over or self.state == "clearing":
            return
        if self._valid(self.current, self.current.rotation, 0, 1):
            self.current.y += 1
        else:
            self._lock()

    def hard_drop(self):
        if self.paused or self.game_over or self.state == "clearing":
            return
        while self._valid(self.current, self.current.rotation, 0, 1):
            self.current.y += 1
        self._lock()

    def _lock(self):
        for (x, y) in self.current.cells():
            if y >= 0:
                self.board[y][x] = self.current.name
        full = [y for y in range(ROWS) if all(c is not None for c in self.board[y])]
        if full:
            # 进入消行动画阶段，暂不起下一个方块
            self.state = "clearing"
            self.clear_anim = {"rows": full, "t": 0, "duration": 220}
            self.pending_clears = [(y, self.board[y][:]) for y in full]
        else:
            self._advance()

    def _advance(self):
        self.current = self.next_piece
        self.next_piece = self._new_piece()
        if not self._valid(self.current, self.current.rotation):
            self.game_over = True

    def _finish_clear(self):
        cleared = len(self.clear_anim["rows"])
        kept = [row for row in self.board if not all(c is not None for c in row)]
        for _ in range(cleared):
            kept.insert(0, [None for _ in range(COLUMNS)])
        self.board = kept
        self.lines += cleared
        self.score += {1: 100, 2: 300, 3: 500, 4: 800}[cleared] * self.level
        self.level = self.lines // 10 + 1
        self.fall_speed = max(80, 500 - (self.level - 1) * 40)
        self.state = "play"
        self.clear_anim = None
        self._advance()

    def tick(self, dt):
        if self.paused or self.game_over:
            return
        if self.state == "clearing":
            self.clear_anim["t"] += dt
            if self.clear_anim["t"] >= self.clear_anim["duration"]:
                self._finish_clear()
            return
        self.fall_time += dt
        if self.fall_time >= self.fall_speed:
            self.fall_time = 0
            self.soft_drop()

    def ghost_y(self):
        """当前方块硬降后的落点 y 偏移（用于投影）。"""
        gy = 0
        while self._valid(self.current, self.current.rotation, 0, gy + 1):
            gy += 1
        return gy


class TetrisGUI:
    def __init__(self, root):
        self.root = root
        # 窗口创建后再检测系统中存在的中文字体（families() 需要 Tk 已初始化）
        global CJK_FONT
        CJK_FONT = _cjk_font_name()
        # 读取本地记忆的设置（主题、粒子数量）
        self.settings = load_settings()
        self.theme = self.settings["theme"]
        t = THEMES[self.theme]
        self.root.title("俄罗斯方块 Tetris")
        self.root.resizable(False, False)
        self.root.configure(bg=t["bg_root"])

        self.game = Tetris()
        self.particles = []        # 消行粒子特效
        self.particle_count = self.settings["particle_count"]  # 每格粒子数（0=关闭）
        self.cell_cut = self.settings["cell_cut"]              # 方块四角切角大小（像素）
        self.bg_color = self.settings["bg_color"]              # 彩色模式棋盘背景色
        self.started = False       # 是否已进入游戏（点击“开始游戏”后变 True）
        self.settings_open = False  # 设置窗口是否打开（打开时方块不下降）
        self._btn_active = {}       # 圆角按钮 id -> 悬停高亮色

        board_w = COLUMNS * CELL
        board_h = ROWS * CELL
        self.canvas = tk.Canvas(root, width=board_w, height=board_h,
                                bg=self._board_bg(), highlightthickness=0)
        self.canvas.grid(row=0, column=0, padx=10, pady=10)

        # 面板下方多留一截，用来放置“设置 / 颜色模式 / 退出”按钮
        self.panel = tk.Canvas(root, width=PANEL_W, height=board_h + 130,
                               bg=t["bg_panel"], highlightthickness=0)
        self.panel.grid(row=0, column=1, padx=(0, 10), pady=10)

        self._build_panel_text()
        self._build_setting_button()
        self._build_theme_button()
        self._build_quit_button()
        self._bind_keys()
        self._draw_static_grid()
        self._show_start_screen()
        self._loop()
        self._render()

    # ---------- 面板文字 ----------
    def _build_panel_text(self):
        self.panel.create_text(PANEL_W // 2, 18, text="下一个",
                               fill=THEMES[self.theme]["title"],
                               font=F(14, "bold"), tags="title")
        self.next_rects = []      # 预览方块（圆角多边形），每帧重建
        self.score_var = self.panel.create_text(PANEL_W // 2, 200, text="",
                                                fill="#ffffff", font=F(16))
        self.level_var = self.panel.create_text(PANEL_W // 2, 260, text="",
                                                 fill="#ffffff", font=F(16))
        self.lines_var = self.panel.create_text(PANEL_W // 2, 320, text="",
                                                 fill="#ffffff", font=F(16))
        self.status_var = self.panel.create_text(PANEL_W // 2, ROWS * CELL - 30, text="",
                                                  fill="#ffd23c", font=F(13))

    # ---------- 键盘 ----------
    def _bind_keys(self):
        self.root.bind("<Left>", lambda e: self._safe(lambda: self.game.move(-1)))
        self.root.bind("<Right>", lambda e: self._safe(lambda: self.game.move(1)))
        self.root.bind("<Down>", lambda e: self._safe(lambda: self.game.soft_drop()))
        self.root.bind("<space>", lambda e: self._safe(lambda: self.game.hard_drop()))
        self.root.bind("<Up>", lambda e: self._safe(lambda: self.game.rotate(1)))
        self.root.bind("x", lambda e: self._safe(lambda: self.game.rotate(1)))
        self.root.bind("z", lambda e: self._safe(lambda: self.game.rotate(-1)))
        self.root.bind("p", lambda e: self._safe(lambda: self.game.toggle_pause()))
        self.root.bind("r", lambda e: self._safe(lambda: self.game.reset()))
        self.root.bind("<Escape>", lambda e: self._safe(lambda: self.game.toggle_pause()))
        self.root.bind("<Return>", lambda e: self._start_game())
        self.root.bind("<Alt-Key-w>", lambda e: self.root.destroy())
        self.root.bind("<Alt-Key-W>", lambda e: self.root.destroy())

    def _safe(self, fn):
        """仅在已进入游戏后执行操作，并刷新画面。"""
        if self.started:
            fn()
        self._render()

    def _build_setting_button(self):
        """在右侧面板底部放置“设置”圆角按钮。"""
        self.btn_setting = self._make_round_button(
            self.panel, PANEL_W // 2, ROWS * CELL + 25, 120, 30,
            which="setting", command=self._open_settings, font=F(13, "bold"))

    def _build_theme_button(self):
        """在右侧面板底部放置“彩色 / 黑白”切换圆角按钮。"""
        self.btn_theme = self._make_round_button(
            self.panel, PANEL_W // 2, ROWS * CELL + 65, 120, 30,
            which="theme", command=self._toggle_theme, font=F(13, "bold"))

    def _build_quit_button(self):
        """在右侧面板底部放置“退出”圆角按钮。"""
        self.btn_quit = self._make_round_button(
            self.panel, PANEL_W // 2, ROWS * CELL + 105, 120, 30,
            which="quit", command=self.root.destroy, font=F(14, "bold"))

    # ---------- 圆角按钮 ----------
    def _round_rect(self, canvas, x0, y0, x1, y1, r, fill="#000000",
                    outline=None, width=1, tags=None, steps=8):
        """返回一个圆角矩形多边形（用于绘制圆角按钮与方块格子）。"""
        r = min(r, (x1 - x0) / 2, (y1 - y0) / 2)
        pts = []
        arcs = [
            (x0 + r, y0 + r, math.pi, 1.5 * math.pi),        # 左上
            (x1 - r, y0 + r, -0.5 * math.pi, 0),             # 右上
            (x1 - r, y1 - r, 0, 0.5 * math.pi),              # 右下
            (x0 + r, y1 - r, 0.5 * math.pi, math.pi),        # 左下
        ]
        for (cx, cy, a0, a1) in arcs:
            for i in range(steps + 1):
                a = a0 + (a1 - a0) * (i / steps)
                pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        kw = {"fill": fill, "outline": fill if outline is None else outline,
              "width": width}
        if tags is not None:
            kw["tags"] = tags
        return canvas.create_polygon(pts, **kw)

    def _octagon_points(self, x0, y0, x1, y1, cut):
        """返回八边形顶点列表：正方形四角按 45° 直线切掉 cut 像素。"""
        cut = min(cut, (x1 - x0) / 2, (y1 - y0) / 2)
        return [(x0 + cut, y0), (x1 - cut, y0),
                (x1, y0 + cut), (x1, y1 - cut),
                (x1 - cut, y1), (x0 + cut, y1),
                (x0, y1 - cut), (x0, y0 + cut)]

    def _octagon(self, canvas, x0, y0, x1, y1, cut, fill="#000000",
                 outline=None, width=1, tags=None):
        """在 canvas 上创建八边形多边形（切角为直线，不是圆弧）。"""
        kw = {"fill": fill, "outline": fill if outline is None else outline,
              "width": width}
        if tags is not None:
            kw["tags"] = tags
        return canvas.create_polygon(self._octagon_points(x0, y0, x1, y1, cut), **kw)

    def _make_round_button(self, canvas, cx, cy, w, h, text="", which=None,
                           fill=None, fg=None, active=None, command=None,
                           font=None):
        """在任意 canvas 上绘制圆角按钮（圆角矩形 + 文字 + 点击/悬停）。"""
        if which is not None:
            bg, fg, active, label = self._btn_colors(which)
        else:
            bg, fg, active, label = fill, fg, active, text
        x0, y0, x1, y1 = cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2
        rect = self._round_rect(canvas, x0, y0, x1, y1, 10, fill=bg)
        txt = canvas.create_text(cx, cy, text=label, fill=fg,
                                 font=font or F(13, "bold"))
        self._btn_active[rect] = active

        def _enter(_=None):
            canvas.itemconfig(rect, fill=active, outline=active)

        def _leave(_=None):
            canvas.itemconfig(rect, fill=bg, outline=bg)

        for item in (rect, txt):
            canvas.tag_bind(item, "<Button-1>",
                            lambda e, c=command: c() if c else None)
            canvas.tag_bind(item, "<Enter>", _enter)
            canvas.tag_bind(item, "<Leave>", _leave)
        return rect, txt

    def _btn_colors(self, which):
        """返回 (bg, fg, active, label)，依据当前主题与按钮身份。"""
        dark = self.theme == "dark"
        if which == "setting":
            if dark:
                return ("#444444", "#000000", "#5a5a5a", "设置")
            return ("#3a3a44", "#ffffff", "#4a4a56", "设置")
        if which == "theme":
            if dark:
                return ("#444444", "#000000", "#5a5a5a", "黑白模式")
            return ("#378ADD", "#ffffff", "#5a9ee6", "彩色模式")
        if which == "quit":
            if dark:
                return ("#444444", "#000000", "#5a5a5a", "退出")
            return ("#c0392b", "#ffffff", "#e74c3c", "退出")
        return ("#3a3a44", "#ffffff", "#4a4a56", "按钮")

    def _refresh_panel_buttons(self):
        """按当前主题刷新三个面板圆角按钮的颜色与文字。"""
        self._set_btn(self.btn_setting, "setting")
        self._set_btn(self.btn_theme, "theme")
        self._set_btn(self.btn_quit, "quit")

    def _set_btn(self, btn, which):
        bg, fg, act, label = self._btn_colors(which)
        rect, txt = btn
        self.panel.itemconfig(rect, fill=bg, outline=bg)
        self.panel.itemconfig(txt, text=label, fill=fg)
        self._btn_active[rect] = act

    def _set_theme(self, theme):
        """设定主题并记忆到本地设置。"""
        if theme not in THEMES:
            return
        self.theme = theme
        self.settings["theme"] = theme
        save_settings(self.settings)
        self._apply_theme()

    def _toggle_theme(self):
        """切换经典 / 黑白主题。"""
        self._set_theme("dark" if self.theme == "classic" else "classic")

    def _board_bg(self):
        """棋盘底色：彩色模式用自定义背景色，黑白模式用主题底色。"""
        if self.theme == "dark":
            return THEMES["dark"]["bg_board"]
        return self.bg_color

    def _grid_color(self):
        """网格线颜色：黑白模式用主题色，彩色模式按自定义底色自动取对比色。"""
        if self.theme == "dark":
            return THEMES["dark"]["grid"]
        return rgb_to_hex(contrast_color(hex_to_rgb(self.bg_color)))

    def _start_bg(self):
        """开始界面底色：彩色模式跟随棋盘背景色，黑白模式用主题底色。"""
        if self.theme == "dark":
            return THEMES["dark"]["bg_root"]
        return self.bg_color

    def _apply_theme(self):
        """套用当前主题的配色（背景、网格、按钮）并重绘。"""
        t = THEMES[self.theme]
        self.root.configure(bg=t["bg_root"])
        self.canvas.configure(bg=self._board_bg())
        self.panel.configure(bg=t["bg_panel"])
        self._refresh_panel_buttons()
        self._draw_static_grid()
        self._render()
        self._paint_start_screen()

    def _start_btn_colors(self, which):
        """开始界面按钮配色：返回 (底色, 文字色, 悬停色)。"""
        dark = self.theme == "dark"
        if which == "start":
            if dark:
                return ("#444444", "#000000", "#5a5a5a")
            return ("#378ADD", "#ffffff", "#5a9ee6")
        if dark:
            return ("#444444", "#000000", "#5a5a5a")
        return ("#3a3a44", "#ffffff", "#4a4a56")

    def _start_text_colors(self):
        """按开始界面底色的明暗返回 (标题色, 副标题色, 提示色) 的 hex 字符串。"""
        bg = hex_to_rgb(self._start_bg())
        if is_light(bg):
            return (rgb_to_hex(mix_rgb(bg, (0, 0, 0), 0.80)),
                    rgb_to_hex(mix_rgb(bg, (70, 55, 170), 0.78)),
                    rgb_to_hex(mix_rgb(bg, (0, 0, 0), 0.42)))
        return ("#ffffff", "#a6a0ff", "#b9b9c6")

    def _paint_start_screen(self):
        """按当前底色刷新开始界面的底色与文字颜色（未进入游戏时才有覆盖层）。"""
        oc = getattr(self, "overlay_canvas", None)
        if oc is None:
            return
        bg = self._start_bg()
        self.overlay.configure(bg=bg)
        oc.configure(bg=bg)
        title_c, sub_c, hint_c = self._start_text_colors()
        palette = {"title": title_c, "subtitle": sub_c, "hint": hint_c}
        for item, role in self._start_items:
            oc.itemconfig(item, fill=palette[role])
        # 开始游戏 / 设置按钮的配色同样跟随主题
        for rect, txt, which in getattr(self, "_start_buttons", []):
            bg_c, fg_c, act_c = self._start_btn_colors(which)
            oc.itemconfig(rect, fill=bg_c, outline=bg_c)
            oc.itemconfig(txt, fill=fg_c)
            self._btn_active[rect] = act_c

    def _show_start_screen(self):
        """显示开始界面覆盖层（标题 + 开始游戏 / 设置按钮 + 操作提示）。

        彩色模式下覆盖层直接使用棋盘背景色，文字颜色按底色明暗自动取反。
        """
        bg = self._start_bg()
        overlay = tk.Frame(self.root, bg=bg)
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        W = COLUMNS * CELL + PANEL_W + 20
        H = ROWS * CELL + 20
        oc = tk.Canvas(overlay, width=W, height=H, bg=bg, highlightthickness=0)
        oc.place(relx=0.5, rely=0.5, anchor="center")
        t_item = oc.create_text(W / 2, H * 0.30, text="俄罗斯方块",
                                font=F(36, "bold"), fill="#ffffff")
        s_item = oc.create_text(W / 2, H * 0.40, text="T E T R I S", font=F(15),
                                fill="#a6a0ff")
        # 开始游戏 / 设置圆角按钮（黑白模式为深灰底 + 黑字）
        sb = self._start_btn_colors("start")
        start_btn = self._make_round_button(
            oc, W / 2, H * 0.545, 170, 48, text="开始游戏",
            fill=sb[0], fg=sb[1], active=sb[2],
            command=self._start_game, font=F(18, "bold"))
        st = self._start_btn_colors("setting")
        set_btn = self._make_round_button(
            oc, W / 2, H * 0.675, 120, 34, text="设置",
            fill=st[0], fg=st[1], active=st[2],
            command=self._open_settings, font=F(13, "bold"))
        h1 = oc.create_text(W / 2, H * 0.78, text="← → 移动    ↓ 软降    空格 硬降",
                            font=F(12), fill="#b9b9c6")
        h2 = oc.create_text(W / 2, H * 0.83, text="↑ / X 旋转    P 暂停    Alt+W 退出",
                            font=F(12), fill="#b9b9c6")
        self.overlay = overlay
        self.overlay_canvas = oc
        self._start_items = [(t_item, "title"), (s_item, "subtitle"),
                             (h1, "hint"), (h2, "hint")]
        self._start_buttons = [(start_btn[0], start_btn[1], "start"),
                               (set_btn[0], set_btn[1], "setting")]
        self._paint_start_screen()

    def _start_game(self):
        """点击开始游戏按钮 / 回车：移除覆盖层，进入游戏。"""
        if self.started:
            return
        if hasattr(self, "overlay"):
            self.overlay.destroy()
            del self.overlay
        self.overlay_canvas = None
        self._start_items = []
        self._start_buttons = []
        self.started = True
        self.game.reset()
        self._render()

    def _open_settings(self):
        """打开设置窗口：调整粒子数量、方块切口大小、切换彩色/黑白模式，并记忆到本地。
        打开期间方块不下降（settings_open 标志让主循环跳过下落）。"""
        self.settings_open = True

        def _close():
            self.settings_open = False
            win.destroy()

        win = tk.Toplevel(self.root)
        win.title("设置")
        win.resizable(False, False)
        win.configure(bg="#191921")
        win.transient(self.root)
        win.grab_set()
        win.protocol("WM_DELETE_WINDOW", _close)
        try:
            win.geometry("+%d+%d" % (self.root.winfo_x() + 140,
                                     self.root.winfo_y() + 70))
        except Exception:
            pass

        tk.Label(win, text="设置", font=F(16, "bold"), fg="#ffffff",
                 bg="#191921").pack(pady=(14, 8))

        # 粒子数量
        f1 = tk.Frame(win, bg="#191921")
        f1.pack(pady=4, padx=22, fill="x")
        tk.Label(f1, text="粒子数量（消行时每格喷发数）", font=F(12),
                 fg="#cfcfd8", bg="#191921").pack(anchor="w")
        count_var = tk.IntVar(value=self.particle_count)
        # 深色模式下拖动条槽为灰色（滑块方块仍为黑色），彩色模式保持蓝色
        sl_count = tk.Scale(f1, from_=0, to=12, orient="horizontal",
                      variable=count_var,
                      bg="#191921", fg="#ffffff", font=F(11), highlightthickness=0,
                      troughcolor="#6b6b75" if self.theme == "dark" else "#378ADD",
                      length=240, sliderrelief="flat")
        sl_count.pack(fill="x", pady=(2, 0))
        lbl = tk.Label(f1, text="", font=F(11), fg="#9a9aa8", bg="#191921")
        lbl.pack(anchor="w")

        def _upd(*_):
            v = count_var.get()
            lbl.config(text="当前：%d 个/格（0 = 关闭粒子特效）" % v)

        count_var.trace_add("write", _upd)
        _upd()

        # 颜色模式
        f2 = tk.Frame(win, bg="#191921")
        f2.pack(pady=8, padx=22, fill="x")
        tk.Label(f2, text="颜色模式", font=F(12), fg="#cfcfd8",
                 bg="#191921").pack(anchor="w")
        mode_var = tk.StringVar(value="黑白" if self.theme == "dark" else "彩色")
        rb_c = tk.Radiobutton(f2, text="彩色（经典）", variable=mode_var, value="彩色",
                              bg="#191921", fg="#cfcfd8", font=F(11),
                              selectcolor="#2a2a33", activebackground="#191921",
                              cursor="hand2")
        rb_b = tk.Radiobutton(f2, text="黑白（深色）", variable=mode_var, value="黑白",
                              bg="#191921", fg="#cfcfd8", font=F(11),
                              selectcolor="#2a2a33", activebackground="#191921",
                              cursor="hand2")
        rb_c.pack(anchor="w", pady=2)
        rb_b.pack(anchor="w", pady=2)

        # 方块切口大小（切角）
        f3 = tk.Frame(win, bg="#191921")
        f3.pack(pady=8, padx=22, fill="x")
        tk.Label(f3, text="方块切口大小（四角切掉的长度）", font=F(12),
                 fg="#cfcfd8", bg="#191921").pack(anchor="w")
        inner = tk.Frame(f3, bg="#191921")
        inner.pack(fill="x")
        cut_var = tk.IntVar(value=self.cell_cut)
        sl_cut = tk.Scale(inner, from_=0, to=12, orient="horizontal",
                      variable=cut_var,
                      bg="#191921", fg="#ffffff", font=F(11), highlightthickness=0,
                      troughcolor="#6b6b75" if self.theme == "dark" else "#378ADD",
                      length=170, sliderrelief="flat")
        sl_cut.pack(side="left", fill="x", expand=True, pady=(2, 0))
        pcv = tk.Canvas(inner, width=44, height=44, bg="#191921",
                        highlightthickness=0)
        pcv.pack(side="right", padx=(6, 0))
        cut_lbl = tk.Label(f3, text="", font=F(11), fg="#9a9aa8", bg="#191921")
        cut_lbl.pack(anchor="w")

        def _draw_preview():
            cut = max(0, min(12, int(cut_var.get())))
            pcv.delete("all")
            pts = self._octagon_points(4, 4, 40, 40, cut)
            # 彩色模式为黄色方块；黑白（深色）模式改为灰块 + 浅灰描边
            if mode_var.get() == "黑白":
                fill_c, outline_c = "#505050", "#9a9a9a"
            else:
                fill_c, outline_c = "#F0F000", "#141414"
            pcv.create_polygon(pts, fill=fill_c, outline=outline_c, width=1)
            cut_lbl.config(text="当前：%d px（0 = 直角方块）" % cut)

        cut_var.trace_add("write", lambda *_: _draw_preview())
        _draw_preview()

        # 棋盘背景色（仅彩色模式生效；黑白模式下整块隐藏，见 _on_mode_change）
        f4 = tk.Frame(win, bg="#191921")
        tk.Label(f4, text="棋盘背景色（仅彩色模式）", font=F(12),
                 fg="#cfcfd8", bg="#191921").pack(anchor="w")
        SV_W, SV_H, HUE_H = 190, 104, 14
        sv = tk.Canvas(f4, width=SV_W, height=SV_H, bg="#191921",
                       highlightthickness=0, cursor="crosshair")
        sv.pack(pady=(4, 3))
        hue_bar = tk.Canvas(f4, width=SV_W, height=HUE_H, bg="#191921",
                            highlightthickness=0, cursor="hand2")
        hue_bar.pack()
        for i in range(SV_W):
            hue_bar.create_line(i, 0, i, HUE_H, fill=rgb_to_hex(
                tuple(int(c * 255) for c in colorsys.hsv_to_rgb(i / (SV_W - 1), 1, 1))))

        st = {"h": 0.0, "s": 1.0, "v": 1.0, "rgb": hex_to_rgb(self.bg_color)}
        st["h"], st["s"], st["v"] = colorsys.rgb_to_hsv(*[c / 255 for c in st["rgb"]])

        row = tk.Frame(f4, bg="#191921")
        row.pack(pady=(7, 0), fill="x")
        swatch = tk.Canvas(row, width=42, height=24, bg="#191921",
                           highlightthickness=0)
        swatch.pack(side="left")
        hex_lbl = tk.Label(row, text="", font=F(11), fg="#cfcfd8", bg="#191921")
        hex_lbl.pack(side="left", padx=(8, 0))
        guard = [False]
        rv, gv, bv = [tk.IntVar(value=st["rgb"][i]) for i in range(3)]
        for name, var in (("R", rv), ("G", gv), ("B", bv)):
            tk.Label(row, text=name, font=F(11), fg="#9a9aa8",
                     bg="#191921").pack(side="left", padx=(8, 2))
            tk.Spinbox(row, from_=0, to=255, width=4, textvariable=var,
                       font=F(11), bg="#2a2a33", fg="#ffffff", relief="flat",
                       buttonbackground="#3a3a44", insertbackground="#ffffff",
                       highlightthickness=0, justify="center").pack(side="left")

        def _apply_bg_live():
            """把当前选择的颜色实时套到棋盘与开始界面上（确定前不写盘）。"""
            self.bg_color = rgb_to_hex(st["rgb"])
            self._apply_theme()

        def _draw_sv():
            img = tk.PhotoImage(data=base64.b64encode(
                hsv_square_png(st["h"], SV_W, SV_H)).decode("ascii"))
            sv._img = img                     # 持有引用，避免被回收
            sv.delete("all")
            sv.create_image(0, 0, anchor="nw", image=img)
            mx, my = st["s"] * (SV_W - 1), (1 - st["v"]) * (SV_H - 1)
            sv.create_oval(mx - 4, my - 4, mx + 4, my + 4, outline="#ffffff", width=2)
            sv.create_oval(mx - 4, my - 4, mx + 4, my + 4, outline="#000000", width=1)

        def _draw_hue_mark():
            hue_bar.delete("mark")
            x = st["h"] * (SV_W - 1)
            hue_bar.create_line(x, 0, x, HUE_H, fill="#ffffff", width=3, tags="mark")
            hue_bar.create_line(x, 0, x, HUE_H, fill="#000000", width=1, tags="mark")

        def _sync(hsv=None):
            """统一刷新：RGB 输入框、色块、两个取色区，并实时预览棋盘。"""
            st["h"], st["s"], st["v"] = hsv if hsv else \
                colorsys.rgb_to_hsv(*[c / 255 for c in st["rgb"]])
            guard[0] = True
            for var, v in zip((rv, gv, bv), st["rgb"]):
                var.set(v)
            guard[0] = False
            swatch.delete("all")
            swatch.create_rectangle(0, 0, 41, 23, fill=rgb_to_hex(st["rgb"]),
                                    outline="#7a7a86")
            hex_lbl.config(text=rgb_to_hex(st["rgb"]).upper())
            _draw_sv()
            _draw_hue_mark()
            _apply_bg_live()

        def _set_rgb(rgb, hsv=None):
            st["rgb"] = tuple(max(0, min(255, int(round(v)))) for v in rgb)
            _sync(hsv)

        def _set_hsv(hsv):
            st["rgb"] = tuple(int(round(c * 255))
                              for c in colorsys.hsv_to_rgb(*hsv))
            _sync(hsv)

        def _sv_pick(e):
            _set_hsv((st["h"],
                      max(0.0, min(1.0, e.x / (SV_W - 1))),
                      max(0.0, min(1.0, 1 - e.y / (SV_H - 1)))))

        def _hue_pick(e):
            _set_hsv((max(0.0, min(1.0, e.x / (SV_W - 1))), st["s"], st["v"]))

        def _rgb_typed(*_):
            if guard[0]:
                return
            try:
                _set_rgb([max(0, min(255, int(v.get()))) for v in (rv, gv, bv)])
            except Exception:
                return

        sv.bind("<Button-1>", _sv_pick)
        sv.bind("<B1-Motion>", _sv_pick)
        hue_bar.bind("<Button-1>", _hue_pick)
        hue_bar.bind("<B1-Motion>", _hue_pick)
        for var in (rv, gv, bv):
            var.trace_add("write", _rgb_typed)
        _sync()

        # 底部按钮：恢复默认 / 取消 / 确定（圆角按钮，配色随当前主题）
        bf = tk.Canvas(win, width=342, height=46, bg="#191921",
                       highlightthickness=0)
        bf.pack(pady=(10, 16))

        def _on_mode_change():
            """切换彩色 / 黑白：黑白模式隐藏背景色区块，并把拖动条槽与预览块改为灰色。"""
            dark = mode_var.get() == "黑白"
            if dark:
                f4.pack_forget()
            else:
                # before=bf 保证背景色区块始终位于底部按钮栏上方
                f4.pack(pady=8, padx=22, fill="x", before=bf)
            trough = "#6b6b75" if dark else "#378ADD"
            sl_count.config(troughcolor=trough)
            sl_cut.config(troughcolor=trough)
            _draw_preview()

        rb_c.config(command=_on_mode_change)
        rb_b.config(command=_on_mode_change)

        ok_bg, ok_fg, ok_act = ("#378ADD", "#ffffff", "#5a9ee6") \
            if self.theme != "dark" else ("#444444", "#000000", "#5a5a5a")
        ca_bg, ca_fg, ca_act = ("#3a3a44", "#ffffff", "#4a4a56") \
            if self.theme != "dark" else ("#444444", "#000000", "#5a5a5a")
        rs_bg, rs_fg, rs_act = ("#a1761c", "#ffffff", "#bd8c26") \
            if self.theme != "dark" else ("#444444", "#000000", "#5a5a5a")

        orig_bg = self.bg_color

        def _cancel():
            """取消：把实时预览的背景色还原回去。"""
            if self.bg_color != orig_bg:
                self.bg_color = orig_bg
                self._apply_theme()
            _close()

        def _restore_defaults():
            """把所有设置项恢复为默认值（背景色立即预览，其余确定后生效）。"""
            count_var.set(DEFAULT_SETTINGS["particle_count"])
            cut_var.set(DEFAULT_SETTINGS["cell_cut"])
            mode_var.set("黑白" if DEFAULT_SETTINGS["theme"] == "dark" else "彩色")
            _set_rgb(hex_to_rgb(DEFAULT_SETTINGS["bg_color"]))
            _on_mode_change()

        def _on_ok():
            self.particle_count = max(0, min(12, int(count_var.get())))
            self.settings["particle_count"] = self.particle_count
            self.cell_cut = max(0, min(12, int(cut_var.get())))
            self.settings["cell_cut"] = self.cell_cut
            self.settings["bg_color"] = rgb_to_hex(st["rgb"])
            new_theme = "dark" if mode_var.get() == "黑白" else "classic"
            self.settings["theme"] = new_theme
            save_settings(self.settings)
            if new_theme != self.theme:
                self._set_theme(new_theme)
            else:
                self._apply_theme()
            _close()

        win.protocol("WM_DELETE_WINDOW", _cancel)
        self._make_round_button(bf, 59, 23, 104, 34, text="恢复默认",
                                fill=rs_bg, fg=rs_fg, active=rs_act,
                                command=_restore_defaults, font=F(12))
        self._make_round_button(bf, 171, 23, 104, 34, text="取消",
                                fill=ca_bg, fg=ca_fg, active=ca_act,
                                command=_cancel, font=F(12))
        self._make_round_button(bf, 283, 23, 104, 34, text="确定",
                                fill=ok_bg, fg=ok_fg, active=ok_act,
                                command=_on_ok, font=F(12, "bold"))

        # 初次显示就按当前模式决定背景色区块是否出现
        _on_mode_change()

    # ---------- 绘制 ----------
    def _draw_static_grid(self):
        self.canvas.delete("grid")
        gc = self._grid_color()
        for r in range(ROWS + 1):
            self.canvas.create_line(0, r * CELL, COLUMNS * CELL, r * CELL,
                                    fill=gc, tags="grid")
        for c in range(COLUMNS + 1):
            self.canvas.create_line(c * CELL, 0, c * CELL, ROWS * CELL,
                                    fill=gc, tags="grid")

    def _render(self):
        self.canvas.delete("block", "ghost", "particle")
        if self.game.state == "clearing":
            self._render_clearing()
        else:
            self._render_normal()
        self._draw_particles()
        self._render_panel()

    def _render_normal(self):
        g = self.game
        # 幽灵投影
        if not g.game_over and not g.paused:
            gy = g.ghost_y()
            for (x, y) in g.current.cells():
                yy = y + gy
                if yy >= 0:
                    self._octagon(
                        self.canvas, x * CELL + 2, yy * CELL + 2,
                        x * CELL + CELL - 2, yy * CELL + CELL - 2, self.cell_cut - 2,
                        fill="", outline=hex_color(self._color_of(g.current.name)),
                        width=1, tags="ghost")
        # 已固定方块
        for r in range(ROWS):
            for c in range(COLUMNS):
                col = g.board[r][c]
                if col:
                    self._draw_cell(c, r, self._color_of(col), "block")
        # 当前方块
        if not g.game_over:
            for (x, y) in g.current.cells():
                if y >= 0:
                    self._draw_cell(x, y, self._color_of(g.current.name), "block")

    def _render_clearing(self):
        g = self.game
        ca = g.clear_anim
        rows = set(ca["rows"])
        progress = min(1.0, ca["t"] / ca["duration"])
        for y in range(ROWS):
            row = g.board[y]
            if y in rows:
                # 被消除的行：向白色闪烁渐变后消失
                for c in range(COLUMNS):
                    if row[c]:
                        base = self._color_of(row[c])
                        blended = tuple(int(base[i] + (255 - base[i]) * progress * 0.85)
                                        for i in range(3))
                        self._draw_cell(c, y, blended, "block")
            else:
                # 上方方块随动画向下塌落填补空隙
                shift = sum(1 for r in ca["rows"] if r > y)
                off = progress * shift * CELL
                for c in range(COLUMNS):
                    if row[c]:
                        self._draw_cell(c, y, self._color_of(row[c]), "block", yoff=off)

    def _draw_cell(self, c, r, color, tag, yoff=0):
        x0, y0 = c * CELL, r * CELL + yoff
        x1, y1 = x0 + CELL, y0 + CELL
        fill = hex_color(color)
        # 方块本体：切角正方形（八边形，四角为 45° 直线切口）
        self._octagon(self.canvas, x0 + 1, y0 + 1, x1 - 1, y1 - 1, self.cell_cut,
                      fill=fill, outline=hex_color(self._cell_outline(color)),
                      tags=tag)
        # 高光
        self._octagon(self.canvas, x0 + 5, y0 + 5, x1 - 5, y1 - 5, self.cell_cut - 2,
                      fill="",
                      outline=hex_color(tuple(min(255, v + 50) for v in color)),
                      tags=tag)

    def _color_of(self, name):
        """按当前主题返回方块的 RGB 颜色。"""
        return THEMES[self.theme]["pieces"][name]

    def _cell_outline(self, color):
        """按主题返回方块边框色（深色模式下用略亮的灰边以区分轮廓）。"""
        if self.theme == "dark":
            return tuple(min(255, v + 80) for v in color)
        return (0, 0, 0)

    def _render_panel(self):
        g = self.game
        # 下一个方块预览
        np = g.next_piece
        cells = np.template[0]
        bx = (PANEL_W - 4 * 22) // 2
        by = 40
        for rect in self.next_rects:
            self.panel.delete(rect)
        self.next_rects = []
        col = self._color_of(np.name)
        for (dx, dy) in cells:
            x0 = bx + dx * 22
            y0 = by + dy * 22
            self.next_rects.append(self._octagon(
                self.panel, x0, y0, x0 + 20, y0 + 20, 4,
                fill=hex_color(col), outline=hex_color(self._cell_outline(col)),
                tags="np"))
        self.panel.itemconfig("title", fill=THEMES[self.theme]["title"])
        self.panel.itemconfig(self.score_var, text=f"分数  {g.score}",
                              fill=THEMES[self.theme]["text"])
        self.panel.itemconfig(self.level_var, text=f"等级  {g.level}",
                              fill=THEMES[self.theme]["text"])
        self.panel.itemconfig(self.lines_var, text=f"消行  {g.lines}",
                              fill=THEMES[self.theme]["text"])
        if g.game_over:
            self.panel.itemconfig(self.status_var, text="游戏结束 · 按 R 重开", fill="#ff5050")
        elif g.paused:
            self.panel.itemconfig(self.status_var, text="已暂停 · 按 P 继续", fill="#ffd23c")
        else:
            self.panel.itemconfig(self.status_var, text="", fill="#ffd23c")

    # ---------- 粒子特效 ----------
    def spawn_clear_particles(self, cleared):
        """为被消除的每一格生成若干向外飞溅的粒子。"""
        for (y, colors) in cleared:
            for c in range(COLUMNS):
                col = colors[c]
                if not col:
                    continue
                cx = c * CELL + CELL / 2
                cy = y * CELL + CELL / 2
                for _ in range(self.particle_count):
                    ang = random.uniform(0, 2 * math.pi)
                    spd = random.uniform(60, 220)
                    self.particles.append({
                        "x": cx, "y": cy,
                        "vx": math.cos(ang) * spd,
                        "vy": math.sin(ang) * spd - 70,   # 略微上抛
                        "life": random.uniform(0.4, 0.9),
                        "max": 0.9,
                        "color": self._color_of(col),
                        "size": random.uniform(3, 6),
                    })

    def _update_particles(self, dt):
        ms = dt / 1000.0
        gravity = 700.0
        alive = []
        for p in self.particles:
            p["life"] -= ms
            if p["life"] <= 0:
                continue
            p["vy"] += gravity * ms
            p["x"] += p["vx"] * ms
            p["y"] += p["vy"] * ms
            alive.append(p)
        self.particles = alive

    def _draw_particles(self):
        for p in self.particles:
            a = max(0.0, min(1.0, p["life"] / p["max"]))
            sz = p["size"] * (0.4 + 0.6 * a)
            self.canvas.create_rectangle(p["x"] - sz, p["y"] - sz,
                                         p["x"] + sz, p["y"] + sz,
                                         fill=hex_color(p["color"]), outline="",
                                         tags="particle")

    # ---------- 主循环 ----------
    def _loop(self):
        last = self._last_ms if hasattr(self, "_last_ms") else None
        now = self.root.tk.call("clock", "milliseconds")
        if last is not None:
            dt = now - last
            if dt > 200:          # 防止切后台回来后一次性大跳
                dt = 200
            if self.started and not self.settings_open:
                g = self.game
                # 消行发生：生成粒子
                if g.pending_clears:
                    self.spawn_clear_particles(g.pending_clears)
                    g.pending_clears = []
                prev_over = g.game_over
                g.tick(dt)
                self._update_particles(dt)
                if g.game_over and not prev_over:
                    self._render()
                    messagebox.showinfo("游戏结束", f"最终分数：{g.score}\n消除行数：{g.lines}")
                else:
                    self._render()
        self._last_ms = now
        self.root.after(30, self._loop)


def main():
    root = tk.Tk()
    TetrisGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
