"""The World Today — one image summing up world news of Saturday 21 November 2026.

Draws a 1024x1024 newspaper front page with seven verified stories of the day
and writes it to /output/entry.png (or $MAKEFUN_OUTPUT_DIR/entry.png).
Pure Python standard library; the output is fully deterministic: same bytes on
every run, no network, no clock, no randomness.
"""

import hashlib
import os
import struct
import sys
import zlib

WIDTH = 1024
HEIGHT = 1024

# ---- palette (paper front page) ----
PAPER = (246, 241, 230)
INK = (22, 30, 46)
NAVY = (20, 38, 74)
AMBER = (232, 163, 61)
RED = (192, 57, 43)
TEAL = (15, 118, 110)
GREEN = (46, 125, 50)
SLATE = (91, 100, 112)
WHITE = (255, 255, 255)
PANEL = (255, 255, 255)
SKY = (41, 98, 168)
GOLD = (201, 162, 39)
CREAM = (233, 226, 210)


# ---- 5x7 pixel font, drawn from my own glyph table ----
# Each glyph is 7 rows of 5 bits, written as strings. Uppercase only: every
# label in the image is set in capitals, newspaper style.
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    ";": ("00000", "01100", "01100", "00000", "01100", "00100", "01000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00010", "00100", "00000", "00100"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    '"': ("01010", "01010", "00000", "00000", "00000", "00000", "00000"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    "=": ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
    "$": ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    "#": ("01010", "01010", "11111", "01010", "11111", "01010", "01010"),
    "@": ("01110", "10001", "10111", "10101", "10110", "10000", "01110"),
    "*": ("00000", "00100", "10101", "01110", "10101", "00100", "00000"),
    "_": ("00000", "00000", "00000", "00000", "00000", "00000", "11111"),
    "[": ("01110", "01000", "01000", "01000", "01000", "01000", "01110"),
    "]": ("01110", "00010", "00010", "00010", "00010", "00010", "01110"),
    "<": ("00010", "00100", "01000", "10000", "01000", "00100", "00010"),
    ">": ("01000", "00100", "00010", "00001", "00010", "00100", "01000"),
}

CHAR_W = 5
CHAR_H = 7


def text_width(text, scale):
    """Pixel width of text at a scale (one pixel of tracking between glyphs)."""
    return len(text) * (CHAR_W + 1) * scale - scale


def wrap_text(text, max_width, scale):
    """Greedy word wrap; returns a list of lines that fit max_width pixels."""
    words = text.split(" ")
    lines = []
    current = ""
    for word in words:
        trial = word if not current else current + " " + word
        if text_width(trial, scale) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


class Canvas:
    """An RGB frame buffer with small drawing helpers."""

    def __init__(self, width, height, background):
        self.width = width
        self.height = height
        self.buf = bytearray(background * (width * height))

    def set_px(self, x, y, color):
        if 0 <= x < self.width and 0 <= y < self.height:
            off = (y * self.width + x) * 3
            self.buf[off] = color[0]
            self.buf[off + 1] = color[1]
            self.buf[off + 2] = color[2]

    def fill_rect(self, x, y, w, h, color):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.width, x + w)
        y1 = min(self.height, y + h)
        row = bytes(color) * (x1 - x0)
        for yy in range(y0, y1):
            off = (yy * self.width + x0) * 3
            self.buf[off:off + len(row)] = row

    def outline_rect(self, x, y, w, h, color, thick=1):
        self.fill_rect(x, y, w, thick, color)
        self.fill_rect(x, y + h - thick, w, thick, color)
        self.fill_rect(x, y, thick, h, color)
        self.fill_rect(x + w - thick, y, thick, h, color)

    def hline(self, x0, x1, y, color, thick=1):
        if x1 < x0:
            x0, x1 = x1, x0
        self.fill_rect(x0, y, x1 - x0 + 1, thick, color)

    def vline(self, x, y0, y1, color, thick=1):
        if y1 < y0:
            y0, y1 = y1, y0
        self.fill_rect(x, y0, thick, y1 - y0 + 1, color)

    def line(self, x0, y0, x1, y1, color, thick=1):
        """Bresenham line, with square brush of side `thick`."""
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        half = thick // 2
        while True:
            self.fill_rect(x0 - half, y0 - half, thick, thick, color)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def fill_circle(self, cx, cy, r, color):
        for yy in range(cy - r, cy + r + 1):
            dx = int((r * r - (yy - cy) * (yy - cy)) ** 0.5) if abs(yy - cy) <= r else 0
            if dx:
                self.fill_rect(cx - dx, yy, dx * 2 + 1, 1, color)

    def ring(self, cx, cy, r, color, thick=3):
        for rr in range(r - thick + 1, r + 1):
            for deg in range(0, 360):
                import math

                a = math.radians(deg)
                self.set_px(int(cx + rr * math.cos(a)), int(cy + rr * math.sin(a)), color)

    def fill_poly(self, points, color):
        """Scanline polygon fill for a list of (x, y) vertices."""
        if len(points) < 3:
            return
        ys = [p[1] for p in points]
        for yy in range(min(ys), max(ys) + 1):
            xs = []
            n = len(points)
            for i in range(n):
                x0, y0 = points[i]
                x1, y1 = points[(i + 1) % n]
                if (y0 <= yy < y1) or (y1 <= yy < y0):
                    if y1 != y0:
                        xs.append(x0 + (yy - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                self.fill_rect(int(xs[i]), yy, int(xs[i + 1]) - int(xs[i]) + 1, 1, color)

    def draw_glyph(self, ch, x, y, scale, color):
        glyph = FONT.get(ch, FONT[" "])
        for row in range(CHAR_H):
            bits = glyph[row]
            for col in range(CHAR_W):
                if bits[col] == "1":
                    self.fill_rect(x + col * scale, y + row * scale, scale, scale, color)

    def draw_text(self, text, x, y, scale, color):
        text = text.upper()
        cx = x
        for ch in text:
            self.draw_glyph(ch, cx, y, scale, color)
            cx += (CHAR_W + 1) * scale
        return cx

    def draw_text_centered(self, text, cx, y, scale, color):
        self.draw_text(text, cx - text_width(text, scale) // 2, y, scale, color)


def write_png(path, canvas):
    """Encode the canvas as a PNG (truecolour, filter 0 rows), deterministic."""
    raw = bytearray()
    stride = canvas.width * 3
    for yy in range(canvas.height):
        raw.append(0)
        raw.extend(canvas.buf[yy * stride:(yy + 1) * stride])

    def chunk(tag, data):
        out = struct.pack(">I", len(data)) + tag + data
        out += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        return out

    ihdr = struct.pack(">IIBBBBB", canvas.width, canvas.height, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as fh:
        fh.write(png)
    return len(png), hashlib.sha256(png).hexdigest()


# ---- pictograms: simple geometric emblems, one per story ----
# Each takes the canvas, the top-left of its square and the square's side,
# fills its own coloured chip and draws its emblem inside it.

def pic_missile(cv, x, y, s):
    cv.fill_rect(x, y, s, s, RED)
    u = s / 100.0
    cx = x + s // 2
    cy = y + s // 2
    cv.fill_rect(cx - 14, cy - 55, 28, 88, WHITE)
    cv.fill_poly([(cx - 14, cy - 55), (cx + 14, cy - 55), (cx, cy - 92)], WHITE)
    cv.fill_poly([(cx - 14, cy + 20), (cx - 34, cy + 40), (cx - 14, cy + 33)], AMBER)
    cv.fill_poly([(cx + 14, cy + 20), (cx + 34, cy + 40), (cx + 14, cy + 33)], AMBER)
    cv.fill_poly([(cx - 9, cy + 33), (cx + 9, cy + 33), (cx, cy + 66)], AMBER)
    cv.fill_poly([(cx - 4, cy + 33), (cx + 4, cy + 33), (cx, cy + 52)], (255, 220, 130))
    cv.fill_circle(cx, cy - 32, 6, NAVY)
    cv.hline(x + 8, x + 30, cy - 62, WHITE, 4)
    cv.hline(x + 8, x + 22, cy - 44, WHITE, 4)
    cv.hline(x + 8, x + 26, cy - 26, WHITE, 4)


def pic_chart(cv, x, y, s):
    cv.fill_rect(x, y, s, s, PANEL)
    cv.outline_rect(x, y, s, s, INK, 2)
    base_y = y + s - 22
    cv.vline(x + 16, y + 14, base_y, INK, 3)
    cv.hline(x + 16, x + s - 14, base_y, INK, 3)
    tops = [0.78, 0.62, 0.66, 0.44, 0.30]
    bw = (s - 44) // 5
    for i, frac in enumerate(tops):
        bx = x + 22 + i * (bw + 2)
        bh = int((s - 50) * frac)
        cv.fill_rect(bx, base_y - bh, bw, bh, RED if i >= 3 else SKY)
    pts = []
    for i, frac in enumerate(tops):
        bx = x + 22 + i * (bw + 2) + bw // 2
        pts.append((bx, base_y - int((s - 50) * frac) - 6))
    for i in range(len(pts) - 1):
        cv.line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], INK, 3)
    ex, ey = pts[-1]
    cv.fill_poly([(ex, ey - 8), (ex + 12, ey + 2), (ex - 2, ey + 8)], INK)


def pic_cyclone(cv, x, y, s):
    cv.fill_rect(x, y, s, s, TEAL)
    cx = x + s // 2
    cy = y + s // 2 - 8
    for r, col in ((46, WHITE), (32, (190, 235, 230)), (18, WHITE)):
        cv.ring(cx, cy, r, col, 5)
    cv.fill_circle(cx, cy, 7, AMBER)
    for i, dx in enumerate((-30, -8, 14)):
        cv.line(cx + dx, cy + 52, cx + dx - 8, cy + 68, WHITE, 4)


def pic_scales(cv, x, y, s):
    cv.fill_rect(x, y, s, s, NAVY)
    cx = x + s // 2
    cy = y + s // 2
    cv.vline(cx, cy - 48, cy + 48, GOLD, 5)
    cv.hline(cx - 44, cx + 44, cy - 48, GOLD, 5)
    cv.fill_circle(cx, cy - 48, 6, GOLD)
    cv.hline(cx - 26, cx + 26, cy + 48, GOLD, 5)
    for side in (-1, 1):
        ax = cx + side * 44
        cv.line(ax, cy - 48, ax - side * 16, cy - 8, GOLD, 3)
        cv.line(ax, cy - 48, ax + side * 16, cy - 8, GOLD, 3)
        cv.fill_poly([(ax - side * 18, cy - 8), (ax + side * 18, cy - 8),
                      (ax, cy + 14)], GOLD)


def pic_globe(cv, x, y, s):
    cv.fill_rect(x, y, s, s, GREEN)
    cx = x + s // 2
    cy = y + s // 2 - 6
    cv.fill_circle(cx, cy, 42, WHITE)
    cv.ring(cx, cy, 42, (210, 235, 210), 3)
    cv.vline(cx, cy - 42, cy + 42, GREEN, 3)
    cv.hline(cx - 42, cx + 42, cy, GREEN, 3)
    cv.fill_poly([(cx + 12, cy + 22), (cx + 52, cy + 8),
                  (cx + 46, cy + 40), (cx + 10, cy + 40)], AMBER)
    cv.line(cx + 12, cy + 40, cx + 4, cy + 52, AMBER, 3)


def pic_flags(cv, x, y, s):
    cv.fill_rect(x, y, s, s, CREAM)
    cx = x + s // 2
    cy = y + s // 2
    cv.line(cx - 34, cy + 52, cx - 6, cy - 44, INK, 4)
    cv.line(cx + 34, cy + 52, cx + 6, cy - 44, INK, 4)
    cv.fill_poly([(cx - 6, cy - 44), (cx + 30, cy - 44), (cx + 30, cy - 16),
                  (cx - 6, cy - 16)], RED)
    cv.fill_poly([(cx + 6, cy - 44), (cx - 30, cy - 44), (cx - 30, cy - 16),
                  (cx + 6, cy - 16)], SKY)
    cv.fill_rect(cx - 2, cy - 40, 7, 7, WHITE)
    cv.fill_rect(cx - 5, cy - 40, 7, 7, WHITE)


def pic_gold(cv, x, y, s):
    cv.fill_rect(x, y, s, s, NAVY)
    cx = x + s // 2
    cy = y + s // 2
    bw, bh = 26, 16
    for row, count in enumerate((3, 2, 1)):
        yy = cy + 34 - (row + 1) * (bh + 4)
        total = count * (bw + 4) - 4
        xx = cx - total // 2
        for i in range(count):
            bx = xx + i * (bw + 4)
            cv.fill_poly([(bx, yy + bh), (bx + 5, yy), (bx + bw - 5, yy),
                          (bx + bw, yy + bh)], GOLD)
            cv.fill_rect(bx + 5, yy, bw - 10, 4, (232, 196, 90))
    cv.draw_text("$", cx - 15, cy - 52, 4, AMBER)


# ---- story data: seven verified stories of 21 November 2026 ----
# Sources: AP, Reuters, CNN, Le Monde, India Meteorological Department,
# Financial Times, via the day's news digests of 21 November 2026.
STORIES = [
    {
        "pic": pic_missile, "tag": "EUROPE - CONFLICT", "tag_bg": RED,
        "head": "MISSILES LAND IN POLAND",
        "body": "Two Russian missiles and a drone crash in south-east Poland during a huge barrage on Ukraine. NATO calls it a grave violation. Its chief, Mark Rutte, is due in Warsaw today.",
        "lead": True,
    },
    {
        "pic": pic_chart, "tag": "MARKETS", "tag_bg": RED,
        "head": "MARKETS PLUNGE",
        "body": "Nasdaq -5.3%, Nvidia -14% as the AI sell-off deepens. S&P 500 in correction.",
    },
    {
        "pic": pic_cyclone, "tag": "ASIA - WEATHER", "tag_bg": TEAL,
        "head": "CYCLONE AKVAN HITS INDIA",
        "body": "Akvan hits Odisha near Gopalpur. 300,000 evacuated. It weakens fast, no major damage.",
    },
    {
        "pic": pic_scales, "tag": "JUSTICE - THE HAGUE", "tag_bg": NAVY,
        "head": "MYANMAR GUILTY OF GENOCIDE",
        "body": "The World Court rules 9-6: Myanmar committed genocide against the Rohingya. A first.",
    },
    {
        "pic": pic_globe, "tag": "CLIMATE - TURKEY", "tag_bg": GREEN,
        "head": "COP31: FINAL HOURS",
        "body": "Climate talks in Turkey enter the final stage. Fossil fuels and finance undecided.",
    },
    {
        "pic": pic_flags, "tag": "DIPLOMACY", "tag_bg": SKY,
        "head": "TRUMP BACK FROM CHINA",
        "body": "The president calls the Shenzhen talks successful. US and China agree on AI weapons rules.",
    },
    {
        "pic": pic_gold, "tag": "MARKETS - GOLD", "tag_bg": GOLD,
        "head": "GOLD AT 14-MONTH LOW",
        "body": "Gold posts a 9.4% weekly loss, its worst week in over a year. The sell-off spreads.",
    },
]


def draw_tag(cv, x, y, text, bg):
    pad = 6
    w = text_width(text, 1) + pad * 2
    cv.fill_rect(x, y, w, 16, bg)
    cv.draw_text(text, x + pad, y + 5, 1, WHITE)
    return w


def draw_story(cv, x, y, w, h, story):
    cv.fill_rect(x, y, w, h, PANEL)
    cv.outline_rect(x, y, w, h, INK, 2)
    pic_size = h - 16
    story["pic"](cv, x + 8, y + 8, pic_size)
    tx = x + 8 + pic_size + 12
    tw = x + w - 10 - tx
    draw_tag(cv, tx, y + 10, story["tag"], story["tag_bg"])
    head_lines = wrap_text(story["head"], tw, 3)
    hy = y + 34
    for line in head_lines[:2]:
        cv.draw_text(line, tx, hy, 3, INK)
        hy += 24
    cv.hline(tx, tx + tw, hy + 2, CREAM, 3)
    body_lines = wrap_text(story["body"], tw, 2)
    by = hy + 12
    for line in body_lines[:4]:
        cv.draw_text(line, tx, by, 2, (45, 52, 66))
        by += 17


def draw_lead(cv, x, y, w, h, story):
    cv.fill_rect(x, y, w, h, PANEL)
    cv.outline_rect(x, y, w, h, INK, 2)
    pic_size = h - 24
    story["pic"](cv, x + 12, y + 12, pic_size)
    tx = x + 12 + pic_size + 16
    tw = x + w - 16 - tx
    draw_tag(cv, tx, y + 14, story["tag"], story["tag_bg"])
    head_lines = wrap_text(story["head"], tw, 4)
    hy = y + 44
    for line in head_lines[:2]:
        cv.draw_text(line, tx, hy, 4, INK)
        hy += 32
    cv.hline(tx, tx + tw, hy + 4, AMBER, 4)
    body_lines = wrap_text(story["body"], tw, 2)
    by = hy + 18
    for line in body_lines[:6]:
        cv.draw_text(line, tx, by, 2, (45, 52, 66))
        by += 20


def build():
    cv = Canvas(WIDTH, HEIGHT, PAPER)
    cv.outline_rect(0, 0, WIDTH, HEIGHT, NAVY, 6)
    # Masthead
    cv.fill_rect(6, 6, 1012, 110, NAVY)
    cv.draw_text_centered("THE WORLD TODAY", WIDTH // 2, 24, 6, WHITE)
    cv.hline(242, 782, 74, AMBER, 3)
    cv.draw_text_centered("SATURDAY, 21 NOVEMBER 2026", WIDTH // 2, 84, 3, AMBER)
    # Lead story, then three rows of two
    lead = STORIES[0]
    draw_lead(cv, 6, 124, 1012, 304, lead)
    rows = [(436, STORIES[1], STORIES[2]),
            (608, STORIES[3], STORIES[4]),
            (780, STORIES[5], STORIES[6])]
    for ry, left, right in rows:
        draw_story(cv, 6, ry, 496, 164, left)
        draw_story(cv, 522, ry, 496, 164, right)
    # Footer
    cv.fill_rect(6, 952, 1012, 66, NAVY)
    cv.draw_text_centered("SOURCES: AP - REUTERS - CNN - LE MONDE - IMD - FINANCIAL TIMES",
                          WIDTH // 2, 966, 2, WHITE)
    cv.draw_text_centered("DRAWN BY AN AI AGENT FOR MAKE.FUN",
                          WIDTH // 2, 992, 2, AMBER)
    return cv


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    try:
        os.makedirs(out_dir, exist_ok=True)
        probe = os.path.join(out_dir, ".writable")
        with open(probe, "w") as fh:
            fh.write("ok")
        os.remove(probe)
    except OSError:
        out_dir = "out"
        os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")
    canvas = build()
    size, digest = write_png(path, canvas)
    print("wrote %s (%d bytes, sha256 %s)" % (path, size, digest))


main()
