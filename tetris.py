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
游戏进行中可点击右侧面板底部的「退出」按钮或按 Alt+W 关闭窗口。
"""

import math
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
                self.board[y][x] = self.current.color
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
        self.root.title("俄罗斯方块 Tetris")
        self.root.resizable(False, False)
        self.root.configure(bg="#101018")

        self.game = Tetris()
        self.particles = []        # 消行粒子特效
        self.started = False       # 是否已进入游戏（点击“开始游戏”后变 True）

        board_w = COLUMNS * CELL
        board_h = ROWS * CELL
        self.canvas = tk.Canvas(root, width=board_w, height=board_h,
                                bg="#0f0f14", highlightthickness=0)
        self.canvas.grid(row=0, column=0, padx=10, pady=10)

        # 面板下方多留一截，用来放置“退出”按钮
        self.panel = tk.Canvas(root, width=PANEL_W, height=board_h + 70,
                               bg="#191921", highlightthickness=0)
        self.panel.grid(row=0, column=1, padx=(0, 10), pady=10)

        self._build_panel_text()
        self._build_quit_button()
        self._bind_keys()
        self._draw_static_grid()
        self._show_start_screen()
        self._loop()
        self._render()

    # ---------- 面板文字 ----------
    def _build_panel_text(self):
        self.panel.create_text(PANEL_W // 2, 18, text="下一个", fill="#cfcfd8",
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

    def _build_quit_button(self):
        """在右侧面板底部放置“退出”按钮。"""
        btn = tk.Button(self.panel, text="退出", font=F(14, "bold"),
                        bg="#c0392b", fg="#ffffff", activebackground="#e74c3c",
                        relief="flat", cursor="hand2",
                        command=self.root.destroy)
        self.panel.create_window(PANEL_W // 2, ROWS * CELL + 35,
                                 window=btn, width=120, height=34)

    def _show_start_screen(self):
        """显示开始界面覆盖层（标题 + 开始游戏按钮 + 操作提示）。"""
        overlay = tk.Frame(self.root, bg="#101018")
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        tk.Label(overlay, text="俄罗斯方块", font=F(36, "bold"),
                 fg="#ffffff", bg="#101018").place(relx=0.5, rely=0.34, anchor="center")
        tk.Label(overlay, text="T E T R I S", font=F(15),
                 fg="#7f77dd", bg="#101018").place(relx=0.5, rely=0.44, anchor="center")
        start = tk.Button(overlay, text="开始游戏", font=F(18, "bold"),
                          bg="#378ADD", fg="#ffffff", activebackground="#5a9ee6",
                          relief="flat", cursor="hand2", width=12, height=1,
                          command=self._start_game)
        start.place(relx=0.5, rely=0.62, anchor="center")
        tk.Label(overlay, text="← → 移动    ↓ 软降    空格 硬降", font=F(12),
                 fg="#9a9aa8", bg="#101018").place(relx=0.5, rely=0.74, anchor="center")
        tk.Label(overlay, text="↑ / X 旋转    P 暂停    Alt+W 退出", font=F(12),
                 fg="#9a9aa8", bg="#101018").place(relx=0.5, rely=0.79, anchor="center")
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

    # ---------- 绘制 ----------
    def _draw_static_grid(self):
        self.canvas.delete("grid")
        for r in range(ROWS + 1):
            self.canvas.create_line(0, r * CELL, COLUMNS * CELL, r * CELL,
                                    fill="#26262f", tags="grid")
        for c in range(COLUMNS + 1):
            self.canvas.create_line(c * CELL, 0, c * CELL, ROWS * CELL,
                                    fill="#26262f", tags="grid")

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
                        outline=hex_color(g.current.color), width=1, tags="ghost")
        # 已固定方块
        for r in range(ROWS):
            for c in range(COLUMNS):
                col = g.board[r][c]
                if col:
                    self._draw_cell(c, r, col, "block")
        # 当前方块
        if not g.game_over:
            for (x, y) in g.current.cells():
                if y >= 0:
                    self._draw_cell(x, y, g.current.color, "block")

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
                        base = row[c]
                        blended = tuple(int(base[i] + (255 - base[i]) * progress * 0.85)
                                        for i in range(3))
                        self._draw_cell(c, y, blended, "block")
            else:
                # 上方方块随动画向下塌落填补空隙
                shift = sum(1 for r in ca["rows"] if r > y)
                off = progress * shift * CELL
                for c in range(COLUMNS):
                    if row[c]:
                        self._draw_cell(c, y, row[c], "block", yoff=off)

    def _draw_cell(self, c, r, color, tag, yoff=0):
        x0, y0 = c * CELL, r * CELL + yoff
        x1, y1 = x0 + CELL, y0 + CELL
        fill = hex_color(color)
        self.canvas.create_rectangle(x0 + 1, y0 + 1, x1 - 1, y1 - 1,
                                     fill=fill, outline="#000000", tags=tag)
        # 高光
        self.canvas.create_rectangle(x0 + 5, y0 + 5, x1 - 5, y1 - 5,
                                     outline=hex_color(tuple(min(255, v + 50) for v in color)),
                                     tags=tag)

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
            self.panel.itemconfig(self.next_rects[i], fill=hex_color(np.color),
                                  outline="#000000")
        self.panel.itemconfig(self.score_var, text=f"分数  {g.score}")
        self.panel.itemconfig(self.level_var, text=f"等级  {g.level}")
        self.panel.itemconfig(self.lines_var, text=f"消行  {g.lines}")
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
                for _ in range(3):
                    ang = random.uniform(0, 2 * math.pi)
                    spd = random.uniform(60, 220)
                    self.particles.append({
                        "x": cx, "y": cy,
                        "vx": math.cos(ang) * spd,
                        "vy": math.sin(ang) * spd - 70,   # 略微上抛
                        "life": random.uniform(0.4, 0.9),
                        "max": 0.9,
                        "color": col,
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
            if self.started:
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
