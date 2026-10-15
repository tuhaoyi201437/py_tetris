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

import json
import math
import os
import random
import tkinter as tk
import tkinter.font as tk_font
from tkinter import messagebox

# ----------------------------- 配置 -----------------------------
COLUMNS = 10          # 游戏区列数
ROWS = 20             # 游戏区行数
CELL = 30             # 每个格子像素大小
PANEL_W = 180         # 右侧信息面板宽度

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
        "bg_board": "#0f0f14",
        "bg_panel": "#191921",
        "grid": "#26262f",
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
DEFAULT_SETTINGS = {"particle_count": 3, "theme": "classic"}


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
        if data.get("theme") in THEMES:
            s["theme"] = data["theme"]
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
        self.started = False       # 是否已进入游戏（点击“开始游戏”后变 True）
        self.settings_open = False  # 设置窗口是否打开（打开时方块不下降）
        self._btn_active = {}       # 圆角按钮 id -> 悬停高亮色

        board_w = COLUMNS * CELL
        board_h = ROWS * CELL
        self.canvas = tk.Canvas(root, width=board_w, height=board_h,
                                bg=t["bg_board"], highlightthickness=0)
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
        self.next_rects = [self.panel.create_rectangle(0, 0, 0, 0, tags="np")
                           for _ in range(4)]
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
    def _round_rect(self, canvas, x0, y0, x1, y1, r, fill="#000000"):
        """返回一个圆角矩形多边形（用于绘制圆角按钮）。"""
        r = min(r, (x1 - x0) / 2, (y1 - y0) / 2)
        steps = 8
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
        return canvas.create_polygon(pts, fill=fill, outline=fill)

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

    def _apply_theme(self):
        """套用当前主题的配色（背景、网格、按钮）并重绘。"""
        t = THEMES[self.theme]
        self.root.configure(bg=t["bg_root"])
        self.canvas.configure(bg=t["bg_board"])
        self.panel.configure(bg=t["bg_panel"])
        self._refresh_panel_buttons()
        self._draw_static_grid()
        self._render()

    def _show_start_screen(self):
        """显示开始界面覆盖层（标题 + 开始游戏圆角按钮 + 操作提示）。"""
        bg = THEMES[self.theme]["bg_root"]
        overlay = tk.Frame(self.root, bg=bg)
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        W = COLUMNS * CELL + PANEL_W + 20
        H = ROWS * CELL + 20
        oc = tk.Canvas(overlay, width=W, height=H, bg=bg, highlightthickness=0)
        oc.place(relx=0.5, rely=0.5, anchor="center")
        title_color = THEMES[self.theme]["title"]
        oc.create_text(W / 2, H * 0.34, text="俄罗斯方块", font=F(36, "bold"),
                       fill=title_color)
        oc.create_text(W / 2, H * 0.44, text="T E T R I S", font=F(15),
                       fill="#7f77dd")
        # 开始游戏圆角按钮（黑白模式为深灰底 + 黑字）
        sb_bg, sb_fg, sb_act = ("#378ADD", "#ffffff", "#5a9ee6") \
            if self.theme != "dark" else ("#444444", "#000000", "#5a5a5a")
        self._make_round_button(oc, W / 2, H * 0.62, 170, 48, text="开始游戏",
                                fill=sb_bg, fg=sb_fg, active=sb_act,
                                command=self._start_game, font=F(18, "bold"))
        oc.create_text(W / 2, H * 0.74, text="← → 移动    ↓ 软降    空格 硬降",
                       font=F(12), fill="#9a9aa8")
        oc.create_text(W / 2, H * 0.79, text="↑ / X 旋转    P 暂停    Alt+W 退出",
                       font=F(12), fill="#9a9aa8")
        self.overlay = overlay

    def _start_game(self):
        """点击开始游戏按钮 / 回车：移除覆盖层，进入游戏。"""
        if self.started:
            return
        if hasattr(self, "overlay"):
            self.overlay.destroy()
            del self.overlay
        self.started = True
        self.game.reset()
        self._render()

    def _open_settings(self):
        """打开设置窗口：调整粒子数量、切换彩色/黑白模式，并记忆到本地。
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
        sl = tk.Scale(f1, from_=0, to=12, orient="horizontal", variable=count_var,
                      bg="#191921", fg="#ffffff", font=F(11), highlightthickness=0,
                      troughcolor="#378ADD", length=240, sliderrelief="flat")
        sl.pack(fill="x", pady=(2, 0))
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

        # 确认 / 取消（圆角按钮，配色随当前主题）
        bf = tk.Canvas(win, width=240, height=46, bg="#191921",
                       highlightthickness=0)
        bf.pack(pady=(8, 16))
        ok_bg, ok_fg, ok_act = ("#378ADD", "#ffffff", "#5a9ee6") \
            if self.theme != "dark" else ("#444444", "#000000", "#5a5a5a")
        ca_bg, ca_fg, ca_act = ("#3a3a44", "#ffffff", "#4a4a56") \
            if self.theme != "dark" else ("#444444", "#000000", "#5a5a5a")

        def _on_ok():
            self.particle_count = max(0, min(12, int(count_var.get())))
            self.settings["particle_count"] = self.particle_count
            new_theme = "dark" if mode_var.get() == "黑白" else "classic"
            self.settings["theme"] = new_theme
            save_settings(self.settings)
            if new_theme != self.theme:
                self._set_theme(new_theme)
            else:
                self._apply_theme()
            _close()

        self._make_round_button(bf, 62, 23, 104, 34, text="确定",
                                fill=ok_bg, fg=ok_fg, active=ok_act,
                                command=_on_ok, font=F(12, "bold"))
        self._make_round_button(bf, 178, 23, 104, 34, text="取消",
                                fill=ca_bg, fg=ca_fg, active=ca_act,
                                command=_close, font=F(12))

    # ---------- 绘制 ----------
    def _draw_static_grid(self):
        self.canvas.delete("grid")
        for r in range(ROWS + 1):
            self.canvas.create_line(0, r * CELL, COLUMNS * CELL, r * CELL,
                                    fill=THEMES[self.theme]["grid"], tags="grid")
        for c in range(COLUMNS + 1):
            self.canvas.create_line(c * CELL, 0, c * CELL, ROWS * CELL,
                                    fill=THEMES[self.theme]["grid"], tags="grid")

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
                    self.canvas.create_rectangle(
                        x * CELL + 2, yy * CELL + 2, x * CELL + CELL - 2, yy * CELL + CELL - 2,
                        outline=hex_color(self._color_of(g.current.name)), width=1, tags="ghost")
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
        self.canvas.create_rectangle(x0 + 1, y0 + 1, x1 - 1, y1 - 1,
                                     fill=fill, outline=hex_color(self._cell_outline(color)), tags=tag)
        # 高光
        self.canvas.create_rectangle(x0 + 5, y0 + 5, x1 - 5, y1 - 5,
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
            self.panel.coords(rect, 0, 0, 0, 0)
        for i, (dx, dy) in enumerate(cells):
            x0 = bx + dx * 22
            y0 = by + dy * 22
            self.panel.coords(self.next_rects[i], x0, y0, x0 + 20, y0 + 20)
            col = self._color_of(np.name)
            self.panel.itemconfig(self.next_rects[i], fill=hex_color(col),
                                  outline=hex_color(self._cell_outline(col)))
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
