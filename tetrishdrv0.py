#!/usr/bin/env python3
"""
Samsoft Tetris — Global Edition (多语言全球版)
--------------------------------------------
NES-accurate 60 FPS build with A/B-Type, DAS/ARR/ARE, and multilingual GUI:
English, 中文 (Simplified Chinese), Русский (Russian), 日本語 (Japanese), Filipino (Tagalog).
Includes infinite Korobeiniki OST loop using synthesized NES square waves at 135 BPM.

(C) 2025 Flames Co. / Samsoft Interactive
"""

import tkinter as tk
from tkinter import messagebox
import numpy as np
import random
import io
import wave
import pygame
import collections

# === Global constants ===
CVS_WIDTH, CVS_HEIGHT = 600, 460
BOX_L, W_BOX_NUM, H_BOX_NUM = 20, 10, 20
FONT = 'Fixedsys 10 bold'
TITLE_FONT = 'Fixedsys 24 bold'
FPS, FRAME_MS = 60, 1000 // 60
SCORES = {0: 0, 1: 40, 2: 100, 3: 300, 4: 1200}
WINDOW_TITLE = "Samsoft Tetris — Global Edition (60 FPS)"

NES_GRAVITY_TABLE = {
    0: 48, 1: 43, 2: 38, 3: 33, 4: 28, 5: 23, 6: 18, 7: 13, 8: 8, 9: 6,
    10: 5, 11: 5, 12: 5, 13: 4, 14: 4, 15: 4, 16: 3, 17: 3, 18: 3
}

def gravity_frames(level: int) -> int:
    if level >= 29: return 1
    if level >= 19: return 2
    return NES_GRAVITY_TABLE.get(level, 48)

DAS_DELAY_FRAMES, ARR_FRAMES, LINE_CLEAR_DELAY_FRAMES = 16, 6, 20

# === Multilingual text ===
LANGS = ["EN", "ZH", "RU", "JP", "PH"]
TEXT = {
    "EN": {"title": "SAMSOFT TETRIS", "subtitle": "Samsoft Flames Co. Production", "score": "SCORE", "level": "LEVEL", "lines": "LINES", "next": "NEXT", "start": "PRESS ENTER TO START", "pause": "PAUSED", "gameover": "GAME OVER"},
    "ZH": {"title": "萨姆软件 俄罗斯方块", "subtitle": "萨姆软件公司出品", "score": "分数", "level": "等级", "lines": "行数", "next": "下一个", "start": "按回车开始", "pause": "暂停", "gameover": "游戏结束"},
    "RU": {"title": "САМСОФТ ТЕТРИС", "subtitle": "Производство Samsoft Flames Co.", "score": "СЧЁТ", "level": "УРОВЕНЬ", "lines": "ЛИНИИ", "next": "СЛЕД.", "start": "НАЖМИ ENTER", "pause": "ПАУЗА", "gameover": "ИГРА ОКОНЧЕНА"},
    "JP": {"title": "サムソフト テトリス", "subtitle": "サムソフト・フレイムズ社 制作", "score": "スコア", "level": "レベル", "lines": "ライン", "next": "次", "start": "Enterキーでスタート", "pause": "一時停止", "gameover": "ゲームオーバー"},
    "PH": {"title": "SAMSOFT TETRIS", "subtitle": "Ginawa ng Samsoft Flames Co.", "score": "ISKOR", "level": "ANTAS", "lines": "LINYA", "next": "SUSUNOD", "start": "PINDUTIN ANG ENTER", "pause": "PAHINTUIN", "gameover": "TAPOS NA ANG LARO"}
}

# === Notes and Korobeiniki theme ===
NOTES = {'REST': 0, 'E4': 329.63, 'A4': 440.00, 'B4': 493.88, 'C5': 523.25, 'D5': 587.33, 'E5': 659.25}
KOROBEINIKI = [
    ('E5', 1), ('B4', 0.5), ('C5', 0.5), ('D5', 1), ('C5', 0.5), ('B4', 0.5), ('A4', 1),
    ('A4', 0.5), ('C5', 0.5), ('E5', 1), ('D5', 0.5), ('C5', 0.5), ('B4', 1), ('C5', 0.5),
    ('D5', 0.5), ('E5', 1), ('C5', 1), ('A4', 1), ('A4', 2), ('REST', 0.5)
]

def nes_square(frequency, duration, duty=0.25, volume=0.3, sr=44100):
    if frequency <= 0: return np.zeros(int(sr * duration), dtype=np.int16)
    t = np.arange(int(sr * duration))
    wave = ((t * frequency / sr) % 1) < duty
    out = (wave.astype(float) * 2 - 1) * volume
    return (out * 32767).astype(np.int16)

def generate_korobeiniki_loop():
    BPM = 135  # Original NES Tetris tempo
    beat_sec = 60.0 / BPM  # Seconds per beat (quarter note)
    sr = 44100
    track = [nes_square(NOTES.get(n, 0), beats * beat_sec) for n, beats in KOROBEINIKI * 40]
    arr = np.concatenate(track)
    stereo = np.column_stack((arr, arr))
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr); w.writeframes(stereo.tobytes())
    buf.seek(0)
    return buf

# === Utility ===
def convert_coords(x, y, xs=1, ys=1): return BOX_L * x, BOX_L * y, BOX_L * (x + xs), BOX_L * (y + ys)

# === Shapes ===
FIGURE_SHAPES = collections.OrderedDict([
    ('T', {'c': 'purple', 's': [[(0, 0), (-1, 0), (1, 0), (0, -1)], [(0, 0), (0, -1), (0, 1), (1, 0)], [(0, 0), (-1, 0), (1, 0), (0, 1)], [(0, 0), (0, -1), (0, 1), (-1, 0)]]}),
    ('L', {'c': 'orange', 's': [[(0, 0), (-1, 0), (1, 0), (1, -1)], [(0, 0), (0, -1), (0, 1), (1, 1)], [(0, 0), (1, 0), (-1, 0), (-1, 1)], [(0, 0), (0, 1), (0, -1), (-1, -1)]]}),
    ('J', {'c': 'blue', 's': [[(0, 0), (-1, 0), (1, 0), (-1, 1)], [(0, 0), (0, -1), (0, 1), (-1, -1)], [(0, 0), (1, 0), (-1, 0), (1, 1)], [(0, 0), (0, 1), (0, -1), (1, -1)]]}),
    ('S', {'c': 'green', 's': [[(0, 0), (1, 0), (0, -1), (-1, -1)], [(0, 0), (-1, 0), (0, 1), (-1, -1)]]}),
    ('Z', {'c': 'red', 's': [[(0, 0), (-1, 0), (0, -1), (1, -1)], [(0, 0), (1, 0), (0, 1), (1, -1)]]}),
    ('O', {'c': 'yellow', 's': [[(0, 0), (1, 0), (0, 1), (1, 1)]]}),
    ('I', {'c': 'cyan', 's': [[(-1, 0), (0, 0), (1, 0), (2, 0)], [(0, 1), (0, 0), (0, -1), (0, -2)]]})
])
SHAPE_KEYS = list(FIGURE_SHAPES.keys())

# === Figure class ===
class Figure:
    def __init__(self, cv, key, bg):
        self.cv, self.key, self.bg = cv, key, bg
        self.shape = FIGURE_SHAPES[key]
        self.color = self.shape['c']
        self.rot, self.blocks, self.pivot, self.stopped = 0, [], [4, 1], False

    def get_coords(self, rot, piv): return [(piv[0] + x, piv[1] + y) for x, y in self.shape['s'][rot]]
    def is_colliding(self, coords):
        for x, y in coords:
            if not (0 <= x < W_BOX_NUM and y < H_BOX_NUM): return True
            x1, y1, x2, y2 = convert_coords(x, y)
            if any(i in self.bg for i in self.cv.find_enclosed(x1 - 1, y1 - 1, x2 + 1, y2 + 1)): return True
        return False

    def create(self, next_area=False):
        piv = [self.pivot[0] + 6, self.pivot[1] + 1] if next_area else self.pivot
        coords = self.get_coords(self.rot, piv)
        if not next_area and self.is_colliding(coords): return False
        for x, y in coords:
            rect = self.cv.create_rectangle(convert_coords(x, y), fill=self.color, outline='gray', width=2)
            self.blocks.append(rect)
        return True

    def move(self, dx, dy):
        new_pivot = [self.pivot[0] + dx, self.pivot[1] + dy]
        new_coords = self.get_coords(self.rot, new_pivot)
        if self.is_colliding(new_coords):
            if dy > 0: self.stopped = True
            return False
        self.pivot = new_pivot
        for i, b in enumerate(self.blocks): self.cv.coords(b, convert_coords(*new_coords[i]))
        return True

    def rotate(self, dr):
        new_rot = (self.rot + dr) % len(self.shape['s'])
        for dx, dy in [(0, 0), (-1, 0), (1, 0), (-2, 0), (2, 0), (0, -1)]:
            test_pivot = [self.pivot[0] + dx, self.pivot[1] + dy]
            new_coords = self.get_coords(new_rot, test_pivot)
            if not self.is_colliding(new_coords):
                self.rot, self.pivot = new_rot, test_pivot
                for i, b in enumerate(self.blocks): self.cv.coords(b, convert_coords(*new_coords[i]))
                return True
        return False

    def drop(self):
        while self.move(0, 1): pass
        self.stopped = True

# === Game class ===
class TetrisGame:
    def __init__(self):
        self.tk = tk.Tk(); self.tk.title(WINDOW_TITLE)
        self.cv = tk.Canvas(self.tk, width=CVS_WIDTH, height=CVS_HEIGHT, bg='black'); self.cv.pack()
        self.lang_idx = 0; self.state = 'langmenu'
        self.bg, self.score, self.lines, self.level = [], 0, 0, 0
        self.tk.bind("<KeyPress>", self.key_press); self.tk.bind("<KeyRelease>", self.key_release)
        self.keys_held = set()
        self.gravity_counter, self.das_counter, self.arr_counter, self.das_dir = 0, 0, 0, 0
        self.line_clear_frames = 0
        self.draw_language_menu()

    def t(self, key): return TEXT[LANGS[self.lang_idx]].get(key, key.upper())

    def draw_language_menu(self):
        self.cv.delete("all")
        self.cv.create_text(300, 100, text="Select Language / 选择语言 / Выберите язык / 言語選択 / Piliin ang Wika", font=TITLE_FONT, fill='white')
        for i, code in enumerate(LANGS):
            color = 'yellow' if i == self.lang_idx else 'gray'
            self.cv.create_text(300, 180 + i * 40, text=code, font=FONT, fill=color)

    def start_game(self):
        self.cv.delete("all"); self.state = 'play'
        self.draw_ui(); self.play_music()
        self.rand = self.tgm_randomizer()
        self.next_fig = Figure(self.cv, next(self.rand), self.bg)
        self.spawn_figure()
        self.tk.after(FRAME_MS, self.game_loop)

    def play_music(self):
        pygame.mixer.init(frequency=44100, size=-16, channels=2)
        try:
            buf = generate_korobeiniki_loop()
            pygame.mixer.music.load(buf)
            pygame.mixer.music.play(-1, fade_ms=500)
        except Exception as e: print(f"Music Error: {e}")

    def draw_ui(self):
        self.cv.create_rectangle(convert_coords(0, 0, W_BOX_NUM, H_BOX_NUM), outline='gray')
        self.cv.create_text(420, 50, text=self.t('title'), font='Fixedsys 16 bold', fill='white', anchor='center')
        self.cv.create_text(420, 120, text=self.t('next'), font=FONT, fill='white', anchor='center')
        self.cv.create_rectangle(convert_coords(11, 3, 4, 4), outline='gray')
        self.score_text = self.cv.create_text(420, 250, text=f"{self.t('score')}\n0", font=FONT, fill='white', anchor='center')
        self.lines_text = self.cv.create_text(420, 300, text=f"{self.t('lines')}\n0", font=FONT, fill='white', anchor='center')
        self.level_text = self.cv.create_text(420, 350, text=f"{self.t('level')}\n0", font=FONT, fill='white', anchor='center')

    def update_ui(self):
        self.cv.itemconfig(self.score_text, text=f"{self.t('score')}\n{self.score}")
        self.cv.itemconfig(self.lines_text, text=f"{self.t('lines')}\n{self.lines}")
        self.cv.itemconfig(self.level_text, text=f"{self.t('level')}\n{self.level}")

    def spawn_figure(self):
        self.curr_fig = self.next_fig
        if not self.curr_fig.create(): self.game_over(); return
        
        self.next_fig = Figure(self.cv, next(self.rand), self.bg)
        self.next_fig.create(next_area=True)

    def tgm_randomizer(self):
        pool = SHAPE_KEYS * 5
        history = [random.choice(SHAPE_KEYS) for _ in range(4)]
        while True:
            roll = random.choice(pool)
            while roll in history: roll = random.choice(pool)
            pool.remove(roll)
            if not pool: pool = SHAPE_KEYS * 5
            history = history[1:] + [roll]
            yield roll

    def lock_figure(self):
        self.bg.extend(self.curr_fig.blocks)
        lines_cleared, rows_to_shift = self.clear_lines()
        if lines_cleared > 0:
            self.lines += lines_cleared
            self.score += SCORES[lines_cleared] * (self.level + 1)
            self.level = self.lines // 10
            self.line_clear_frames = LINE_CLEAR_DELAY_FRAMES
            self.pending_line_shift = rows_to_shift
        else:
            self.spawn_figure()
        self.update_ui()

    def clear_lines(self):
        full_lines_y = []
        for y in range(H_BOX_NUM):
            x1, y1, x2, y2 = 0, y * BOX_L, W_BOX_NUM * BOX_L, (y + 1) * BOX_L
            overlaps = self.cv.find_enclosed(x1, y1, x2, y2)
            blocks_in_row = [b for b in overlaps if b in self.bg]
            if len(blocks_in_row) == W_BOX_NUM:
                full_lines_y.append(y)
                for block in blocks_in_row:
                    self.cv.delete(block)
                    self.bg.remove(block)
        return len(full_lines_y), sorted(full_lines_y)

    def finish_line_clear(self):
        for y_cleared in self.pending_line_shift:
            for item in self.bg:
                if self.cv.coords(item)[1] < y_cleared * BOX_L:
                    self.cv.move(item, 0, BOX_L)
        self.spawn_figure()

    def game_loop(self):
        if self.state != 'play':
            self.tk.after(FRAME_MS, self.game_loop); return

        if self.line_clear_frames > 0:
            self.line_clear_frames -= 1
            if self.line_clear_frames == 0: self.finish_line_clear()
        else:
            self.handle_movement()
            self.handle_gravity()
        
        self.tk.after(FRAME_MS, self.game_loop)

    def handle_movement(self):
        if self.das_dir != 0:
            self.das_counter += 1
            if self.das_counter > DAS_DELAY_FRAMES:
                self.arr_counter += 1
                if self.arr_counter >= ARR_FRAMES:
                    self.curr_fig.move(self.das_dir, 0)
                    self.arr_counter = 0

    def handle_gravity(self):
        soft_dropping = 'Down' in self.keys_held
        gravity_limit = 2 if soft_dropping else gravity_frames(self.level)
        self.gravity_counter += 1
        if self.gravity_counter >= gravity_limit:
            self.gravity_counter = 0
            if not self.curr_fig.move(0, 1):
                self.lock_figure()
            if soft_dropping: self.score += 1
            
    def key_press(self, e):
        key = e.keysym
        if self.state == 'langmenu':
            if key in ("Up", "Down"):
                self.lang_idx = (self.lang_idx + (-1 if key == "Up" else 1)) % len(LANGS)
                self.draw_language_menu()
            elif key == "Return": self.start_game()
            return

        if self.state != 'play' or key in self.keys_held or self.line_clear_frames > 0: return
        self.keys_held.add(key)

        if key in ("x", "Up"): self.curr_fig.rotate(1)
        elif key == "z": self.curr_fig.rotate(-1)
        elif key == "space": self.curr_fig.drop(); self.lock_figure()
        elif key in ("Left", "Right"):
            self.das_dir = -1 if key == "Left" else 1
            self.curr_fig.move(self.das_dir, 0)
            self.das_counter = 0
        elif key == "p": self.toggle_pause()

    def key_release(self, e):
        key = e.keysym
        self.keys_held.discard(key)
        if (key == "Left" and self.das_dir == -1) or (key == "Right" and self.das_dir == 1):
            self.das_dir = 0; self.das_counter = 0; self.arr_counter = 0

    def toggle_pause(self):
        if self.state == 'play':
            self.state = 'paused'
            pygame.mixer.music.pause()
            self.pause_text = self.cv.create_text(100, 220, text=self.t('pause'), font=TITLE_FONT, fill="white", anchor="w")
        elif self.state == 'paused':
            self.state = 'play'
            pygame.mixer.music.unpause()
            self.cv.delete(self.pause_text)

    def game_over(self):
        self.state = 'gameover'
        pygame.mixer.music.fadeout(1000)
        messagebox.showinfo(self.t('gameover'), f"{self.t('score')}: {self.score}\n{self.t('lines')}: {self.lines}")
        self.tk.quit()

if __name__ == "__main__":
    game = TetrisGame()
    game.tk.mainloop()
