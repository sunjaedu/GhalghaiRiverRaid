# -*- coding: utf-8 -*-
"""
River Raid для Android (Kivy)
Управление: тапай/веди пальцем по экрану — самолёт следует за пальцем.
Стрельба автоматическая. После проигрыша — тап для рестарта.
"""

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle, Ellipse, Line
from kivy.core.window import Window
from kivy.core.text import Label as CoreLabel
from kivy.utils import platform
import random

# На ПК окно фиксированного размера, на телефоне — во весь экран
if platform not in ('android', 'ios'):
    Window.size = (480, 800)

# ============================ ЦВЕТА ============================
C_WATER   = (0.10, 0.32, 0.71)
C_WATER2  = (0.08, 0.26, 0.61)
C_LAND    = (0.19, 0.55, 0.24)
C_LAND2   = (0.14, 0.44, 0.19)
C_PLANE   = (0.96, 0.96, 0.98)
C_ENEMY   = (0.86, 0.24, 0.24)
C_HELI    = (0.92, 0.78, 0.28)
C_JET     = (0.59, 0.63, 0.90)
C_BULLET  = (1.00, 0.96, 0.47)
C_FUEL    = (0.98, 0.76, 0.16)
C_BRIDGE  = (0.59, 0.57, 0.55)


# ============================ РЕКА ============================
class River:
    """Процедурное русло реки: для каждой строки мира — границы [left, right]."""

    def __init__(self, width):
        self.W = width
        l = width // 2 - 70
        r = width // 2 + 70
        self.rows = [(l, r)]
        self.tleft, self.tright = l, r
        self.change_in = 80

    def ensure(self, upto):
        while len(self.rows) <= upto:
            i = len(self.rows)
            pl, pr = self.rows[-1]
            self.change_in -= 1
            if self.change_in <= 0:
                if i > 600 and random.random() < 0.25:
                    w = 74
                    self.change_in = random.randint(220, 380)
                else:
                    w = random.randint(110, 250)
                    self.change_in = random.randint(70, 160)
                cx = random.randint(w // 2 + 36, self.W - w // 2 - 36)
                self.tleft = cx - w // 2
                self.tright = cx + w // 2

            left = pl + (2 if self.tleft > pl else -2 if self.tleft < pl else 0)
            right = pr + (2 if self.tright > pr else -2 if self.tright < pr else 0)
            left = max(10, min(self.W - 20, left))
            right = max(20, min(self.W - 10, right))
            self.rows.append((left, right))

    def at(self, i):
        if i < 0:
            return self.rows[0]
        self.ensure(i)
        return self.rows[i]


# ============================ ВРАГ ============================
class Enemy:
    def __init__(self, kind, x, w):
        self.kind = kind
        self.x = float(x)
        self.w = float(w)
        self.alive = True
        self.vx = 0.0
        self.vw = 0.0
        if kind == 'ship':
            self.wid, self.hei = 26, 34
            self.vw = -0.2
        elif kind == 'heli':
            self.wid, self.hei = 34, 26
            self.vw = -0.6
            self.vx = random.choice([-1.0, 1.0])
        elif kind == 'jet':
            self.wid, self.hei = 42, 20
            self.vw = -3.6
            self.vx = random.choice([-2.0, 2.0])
        elif kind == 'fuel':
            self.wid, self.hei = 32, 32
            self.vw = 0.0

    def update(self, game):
        self.w += self.vw
        if self.kind == 'heli':
            d = game.px - self.x
            self.vx += 0.06 * (1 if d > 0 else -1)
            self.vx = max(-2.2, min(2.2, self.vx))
        self.x += self.vx
        if self.x < 20 or self.x > game.W - 20:
            self.vx *= -1
            self.x = max(20, min(game.W - 20, self.x))


# ============================ ИГРОВОЙ ВИДЖЕТ ============================
class GameWidget(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.inited = False
        self.text_cache = {}
        self.best = 0
        Clock.schedule_interval(self.update, 1 / 60)

    # ---------- инициализация ----------
    def init_game(self):
        self.W = self.width
        self.H = self.height
        self.scale = min(self.W / 480.0, self.H / 800.0)
        s = self.scale

        self.river = River(int(self.W))
        self.px = self.W / 2
        self.pw = 0.0
        self.cam = -0.4 * self.H
        self.speed = 2.4 * s
        self.fuel = 100.0
        self.score = 0
        self.bullets = []
        self.enemies = []
        self.booms = []
        self.shoot_cd = 0
        self.spawn_w = 0.4 * self.H
        self.over = False
        self.touch_x = None
        self.touching = False

    # ---------- тач-управление ----------
    def on_touch_down(self, touch):
        if self.over:
            best = self.best
            self.init_game()
            self.best = best
            return True
        self.touch_x = touch.x
        self.touching = True
        return True

    def on_touch_move(self, touch):
        self.touch_x = touch.x
        self.touching = True
        return True

    def on_touch_up(self, touch):
        self.touching = False
        return True

    # ---------- игровая логика ----------
    def die(self):
        if self.over:
            return
        self.over = True
        self.best = max(self.best, self.score)
        self.add_boom(self.px, self.pw - self.cam)

    def add_boom(self, x, y):
        s = self.scale
        for _ in range(3):
            self.booms.append({
                'x': x, 'y': y, 't': 0,
                'dx': random.uniform(-2, 2) * s,
                'dy': random.uniform(-2, 2) * s,
                'r': random.randint(10, 18) * s
            })

    def spawn(self):
        s = self.scale
        limit = self.cam + self.H + 520 * s
        while self.spawn_w < limit:
            w = self.spawn_w
            l, r = self.river.at(int(w))
            kind = random.choices(
                ['ship', 'heli', 'jet', 'fuel'],
                weights=[34, 20, 20, 26])[0]
            if kind in ('ship', 'fuel'):
                x = random.randint(int(l + 20), max(int(l + 20), int(r - 20)))
            else:
                x = random.randint(40, max(40, int(self.W) - 40))
            self.enemies.append(Enemy(kind, x, w))
            self.spawn_w += random.randint(150, 300) * s

    def update(self, dt):
        if not self.inited:
            if self.width > 0 and self.height > 0:
                self.init_game()
                self.inited = True
            return

        s = self.scale

        # взрывы
        for b in self.booms:
            b['t'] += 1
            b['x'] += b['dx']
            b['y'] += b['dy']
        self.booms = [b for b in self.booms if b['t'] < 24]

        if self.over:
            self.redraw()
            return

        # скорость и прокрутка
        base_speed = 2.4 * s
        self.speed = base_speed + min(1.4 * s, self.score / 5000.0 * s)
        self.cam += self.speed * 1.05

        # движение самолёта за пальцем
        if self.touching and self.touch_x is not None:
            dx = self.touch_x - self.px
            max_step = 10 * s
            self.px += max(-max_step, min(max_step, dx * 0.35))

        self.px = max(14 * s, min(self.W - 14 * s, self.px))
        self.pw += self.speed

        # удержание самолёта в вертикальной зоне экрана
        if self.pw > self.cam + 0.85 * self.H:
            self.pw = self.cam + 0.85 * self.H
        if self.pw < self.cam + 0.15 * self.H:
            self.pw = self.cam + 0.15 * self.H

        # топливо
        self.fuel -= 0.018 * (self.speed / s)
        if self.fuel <= 0:
            self.fuel = 0
            self.die()
            self.redraw()
            return

        # авто-стрельба
        self.shoot_cd -= 1
        if self.shoot_cd <= 0:
            self.bullets.append([self.px, self.pw])
            self.shoot_cd = 11

        for b in self.bullets:
            b[1] += 10 * s
        self.bullets = [b for b in self.bullets
                        if (b[1] - self.cam) > -30 * s]

        # враги
        for e in self.enemies:
            e.update(self)
        self.enemies = [e for e in self.enemies
                        if e.alive and -140 * s < (e.w - self.cam) < self.H + 160 * s]

        self.spawn()
        self.collisions()
        self.redraw()

    def collisions(self):
        s = self.scale
        psy = self.pw - self.cam
        pr = 9 * s
        p0x, p1x = self.px - pr, self.px + pr
        p0y, p1y = psy - pr, psy + pr

        # берега
        l, r = self.river.at(int(self.pw))
        if self.px - 7 * s < l or self.px + 7 * s > r:
            self.die()
            return

        # враги
        for e in self.enemies:
            if not e.alive:
                continue
            ex, ey = e.x, e.w - self.cam
            ew, eh = e.wid * s / 2, e.hei * s / 2
            if p0x < ex + ew and p1x > ex - ew and p0y < ey + eh and p1y > ey - eh:
                if e.kind == 'fuel':
                    self.fuel = 100.0
                    self.score += 80
                    e.alive = False
                    self.add_boom(e.x, e.w - self.cam)
                else:
                    self.die()
                    return

        # пули
        for b in self.bullets:
            bsy = b[1] - self.cam
            for e in self.enemies:
                if not e.alive or e.kind == 'fuel':
                    continue
                ex, ey = e.x, e.w - self.cam
                ew, eh = e.wid * s / 2, e.hei * s / 2
                if (b[0] - 3 * s < ex + ew and b[0] + 3 * s > ex - ew and
                        bsy - 9 * s < ey + eh and bsy + 9 * s > ey - eh):
                    e.alive = False
                    b[1] = -10 ** 9
                    self.add_boom(e.x, e.w - self.cam)
                    self.score += {'ship': 30, 'heli': 60, 'jet': 100}[e.kind]
                    break
        self.bullets = [b for b in self.bullets if b[1] > -10 ** 8]

    # ---------- отрисовка ----------
    def redraw(self):
        self.canvas.clear()
        self.draw_terrain()
        self.draw_entities()
        self.draw_hud()
        if self.over:
            self.draw_gameover()

    def draw_terrain(self):
        W, H = self.W, self.H
        cam = self.cam
        step = 4
        int_H = int(H)

        Color(*C_LAND2)
        Rectangle(pos=(0, 0), size=(W, H))

        for sy in range(0, int_H, step):
            w = cam + sy
            i = int(w)
            l, r = self.river.at(i)
            band = (i // 24) % 2

            Color(*(C_WATER if band else C_WATER2))
            Rectangle(pos=(l, sy), size=(max(1, r - l), step))

            if band:
                Color(*C_LAND)
            else:
                Color(*C_LAND2)
            if l > 0:
                Rectangle(pos=(0, sy), size=(l, step))
            if r < W:
                Rectangle(pos=(r, sy), size=(W - r, step))

            # узкое место — мост
            if r - l < 105:
                Color(*C_BRIDGE)
                bx = int(l)
                while bx < r:
                    Rectangle(pos=(bx, sy), size=(min(8, r - bx), step))
                    bx += 12

    def draw_entities(self):
        s = self.scale
        for e in self.enemies:
            self.draw_enemy(e)

        Color(*C_BULLET)
        for b in self.bullets:
            sy = b[1] - self.cam
            Rectangle(pos=(b[0] - 2 * s, sy - 9 * s), size=(4 * s, 14 * s))

        if not self.over:
            self.draw_player()

        for b in self.booms:
            a = max(0.0, 1.0 - b['t'] / 24.0)
            r = max(1, b['r'] * (0.5 + a))
            Color(1.0, 0.8 * a, 0.24 * a, max(0.05, a))
            Line(circle=(b['x'], b['y'], r), width=2 * s)

    def draw_player(self):
        s = self.scale
        x = self.px
        y = self.pw - self.cam
        Color(*C_PLANE)
        Line(points=[x, y - 15 * s, x - 5 * s, y + 3 * s,
                     x - 5 * s, y + 12 * s, x + 5 * s, y + 12 * s,
                     x + 5 * s, y + 3 * s, x, y - 15 * s], width=1.5 * s)
        Line(points=[x - 17 * s, y + 5 * s, x - 4 * s, y - 3 * s,
                     x + 4 * s, y - 3 * s, x + 17 * s, y + 5 * s,
                     x - 17 * s, y + 5 * s], width=1.5 * s)
        Line(points=[x - 9 * s, y + 15 * s, x + 9 * s, y + 15 * s,
                     x + 5 * s, y + 5 * s, x - 5 * s, y + 5 * s], width=1.5 * s)

    def draw_enemy(self, e):
        s = self.scale
        x = e.x
        y = e.w - self.cam

        if e.kind == 'ship':
            Color(*C_ENEMY)
            Line(points=[x, y - 16 * s, x - 12 * s, y + 6 * s,
                         x - 8 * s, y + 16 * s, x + 8 * s, y + 16 * s,
                         x + 12 * s, y + 6 * s, x, y - 16 * s], width=2 * s)

        elif e.kind == 'heli':
            Color(0.35, 0.35, 0.35)
            Line(points=[x - 20 * s, y + 8 * s, x + 20 * s, y + 8 * s], width=2 * s)
            Color(*C_HELI)
            Ellipse(pos=(x - 9 * s, y - 7 * s), size=(18 * s, 18 * s))
            Color(0.5, 0.35, 0.1)
            Line(points=[x, y + 6 * s, x, y - 10 * s], width=1.5 * s)
            Line(points=[x - 12 * s, y - 12 * s, x + 12 * s, y - 12 * s], width=1.5 * s)

        elif e.kind == 'jet':
            Color(*C_JET)
            Line(points=[x, y + 12 * s, x - 18 * s, y - 8 * s,
                         x - 6 * s, y - 4 * s, x, y - 10 * s,
                         x + 6 * s, y - 4 * s, x + 18 * s, y - 8 * s,
                         x, y + 12 * s], width=1.5 * s)

        elif e.kind == 'fuel':
            Color(*C_FUEL)
            Rectangle(pos=(x - 14 * s, y - 14 * s), size=(28 * s, 28 * s))
            Color(0.63, 0.47, 0.04)
            Line(points=[x - 14 * s, y - 14 * s, x + 14 * s, y - 14 * s,
                         x + 14 * s, y + 14 * s, x - 14 * s, y + 14 * s,
                         x - 14 * s, y - 14 * s], width=2 * s)
            Color(0.24, 0.16, 0)
            Line(points=[x - 4 * s, y + 7 * s, x + 5 * s, y + 7 * s,
                         x + 5 * s, y - 1 * s, x - 4 * s, y - 1 * s,
                         x - 4 * s, y - 7 * s], width=2 * s)

    def draw_text(self, text, x, y, size, color=(1, 1, 1), anchor='left'):
        if len(self.text_cache) > 200:
            self.text_cache.clear()
        key = (text, int(size), color)
        if key not in self.text_cache:
            lbl = CoreLabel(text=text, font_size=int(size), color=color)
            lbl.refresh()
            self.text_cache[key] = lbl.texture
        tex = self.text_cache[key]
        if anchor == 'center':
            x -= tex.width / 2
        elif anchor == 'right':
            x -= tex.width
        Color(1, 1, 1, 1)
        Rectangle(texture=tex, pos=(x, y), size=tex.size)

    def draw_hud(self):
        s = self.scale
        W, H = self.W, self.H

        Color(0, 0, 0, 0.55)
        Rectangle(pos=(8 * s, H - 30 * s), size=(220 * s, 24 * s))
        Color(0.31, 0.31, 0.31)
        Rectangle(pos=(10 * s, H - 28 * s), size=(216 * s, 20 * s))
        w = int(216 * s * self.fuel / 100)
        if self.fuel > 35:
            Color(0.24, 0.86, 0.24)
        else:
            Color(0.9, 0.27, 0.24)
        Rectangle(pos=(10 * s, H - 28 * s), size=(w, 20 * s))

        self.draw_text("FUEL", 234 * s, H - 27 * s, 16 * s, (1, 1, 1))
        self.draw_text(f"SCORE {self.score}", W - 10 * s, H - 60 * s,
                       18 * s, (1, 1, 1), anchor='right')

    def draw_gameover(self):
        W, H = self.W, self.H
        s = self.scale

        Color(0, 0, 0, 0.6)
        Rectangle(pos=(0, 0), size=(W, H))

        self.draw_text("GAME OVER", W / 2, H / 2 + 60 * s, 40 * s,
                       (1, 0.35, 0.35), anchor='center')
        self.draw_text(f"Счёт: {self.score}", W / 2, H / 2 + 10 * s, 24 * s,
                       (1, 1, 1), anchor='center')
        self.draw_text(f"Рекорд: {self.best}", W / 2, H / 2 - 20 * s, 22 * s,
                       (1, 0.86, 0.47), anchor='center')
        self.draw_text("Коснитесь для рестарта", W / 2, H / 2 - 80 * s,
                       18 * s, (0.78, 0.78, 0.78), anchor='center')


# ============================ ПРИЛОЖЕНИЕ ============================
class RiverRaidApp(App):
    def build(self):
        self.title = "River Raid"
        return GameWidget()


if __name__ == '__main__':
    RiverRaidApp().run()
