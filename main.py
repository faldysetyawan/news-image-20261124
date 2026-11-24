#!/usr/bin/env python3
"""THE WORLD TODAY -- one picture of the world's news, 24 November 2026.

A Python program (standard library only, no network, no randomness) that
draws a newspaper front page and writes it as a 1024x1024 PNG to
$MAKEFUN_OUTPUT_DIR/entry.png (default /output/entry.png).

The page is drawn on a supersampled raster canvas (2x) with a hand-built
vector stroke font and a small PNG encoder written from scratch, then
downsampled to 1024x1024. Two runs produce byte-identical output.

Stories (all reported 23-24 Nov 2026; the lead event happened on Tuesday
24 November in Korea):
  LEAD  Suspected North Korean aircraft breaches South Korean airspace
        near Ulleung Island; islanders ordered to shelter.
  1     Jensen Huang reinstated as Nvidia CEO; shares jump 31%.
  2     US blacklists Singapore chip firm Megaspeed over alleged
        smuggling of Nvidia AI chips to China.
  3     Western intelligence: Russia could launch a nuclear-armed
        satellite, "Sputnik-S", by December; Moscow denies it.
  4     24 dead, about 30 missing after a factory fire in Banten,
        Indonesia.
  Ticker: US DOJ seeks $1.1bn in crypto stolen by North Korean hackers;
        Moscow warns Estonia of "open war"; UK sanctions Myanmar generals
        after recognising the Rohingya genocide.
"""

import math
import os
import struct
import zlib

SS = 2                 # supersampling factor
W = 1024
H = 1024
CW = W * SS
CH = H * SS

INK = (26, 26, 26)
PAPER = (246, 241, 229)
PANEL = (255, 253, 246)
RED = (178, 34, 27)
NAVY = (31, 58, 95)
TEAL = (18, 90, 86)
ORANGE = (214, 96, 20)
GOLD = (176, 132, 40)
SKY = (176, 202, 226)
SEA = (64, 110, 150)
GREEN = (58, 110, 62)
GREY = (110, 104, 94)
LIGHTGREY = (210, 204, 190)

# ---------------------------------------------------------------- font ----
# Hand-built stroke font. Each glyph lives on a 6-wide by 8-tall grid
# (x 0..6, y 0..8, y grows downwards); a glyph is a list of strokes,
# each stroke a chain of points, written "x,y x,y|x,y x,y".
FONT = {
    "A": "0,8 3,0 6,8|1,5 5,5",
    "B": "0,0 0,8|0,0 4,0 5,1 5,3 4,4 0,4|4,4 5,5 5,7 4,8 0,8",
    "C": "6,1 5,0 1,0 0,1 0,7 1,8 5,8 6,7",
    "D": "0,0 0,8 4,8 6,6 6,2 4,0 0,0",
    "E": "6,0 0,0 0,8 6,8|0,4 4,4",
    "F": "6,0 0,0 0,8|0,4 4,4",
    "G": "6,1 5,0 1,0 0,1 0,7 1,8 5,8 6,7 6,4 3,4",
    "H": "0,0 0,8|6,0 6,8|0,4 6,4",
    "I": "3,0 3,8|1,0 5,0|1,8 5,8",
    "J": "6,0 6,7 5,8 2,8 1,7|1,0 6,0",
    "K": "0,0 0,8|6,0 0,4 6,8",
    "L": "0,0 0,8 6,8",
    "M": "0,8 0,0 3,5 6,0 6,8",
    "N": "0,8 0,0 6,8 6,0",
    "O": "1,0 5,0 6,1 6,7 5,8 1,8 0,7 0,1 1,0",
    "P": "0,8 0,0 4,0 5,1 5,3 4,4 0,4",
    "Q": "1,0 5,0 6,1 6,7 5,8 1,8 0,7 0,1 1,0|4,5 6,8",
    "R": "0,8 0,0 4,0 5,1 5,3 4,4 0,4|3,4 6,8",
    "S": "5,1 4,0 2,0 1,1 1,3 2,4 4,4 5,5 5,7 4,8 2,8 1,7",
    "T": "0,0 6,0|3,0 3,8",
    "U": "0,0 0,7 1,8 5,8 6,7 6,0",
    "V": "0,0 3,8 6,0",
    "W": "0,0 1,8 3,4 5,8 6,0",
    "X": "0,0 6,8|6,0 0,8",
    "Y": "0,0 3,4 6,0|3,4 3,8",
    "Z": "0,0 6,0 0,8 6,8",
    "0": "1,0 5,0 6,1 6,7 5,8 1,8 0,7 0,1 1,0|5,1 1,7",
    "1": "2,1 3,0 3,8|1,8 5,8",
    "2": "1,1 2,0 4,0 5,1 5,3 4,4 0,8 6,8",
    "3": "1,0 4,0 6,2 6,3 4,4|4,4 6,5 6,7 5,8 1,8",
    "4": "0,0 0,4 5,4|4,0 4,8",
    "5": "6,0 0,0 0,4 4,4 5,5 5,7 4,8 0,8",
    "6": "5,1 4,0 1,1 0,3 0,7 1,8 5,8 6,7 6,5 5,4 1,4",
    "7": "0,0 6,0 3,8",
    "8": "1,0 5,0 6,1 6,3 5,4 1,4 0,3 0,1 1,0|1,4 5,4 6,5 6,7 5,8 1,8 0,7 0,5 1,4",
    "9": "0,4 1,3 1,1 2,0 4,0 5,1 5,7 4,8 1,8 0,7 0,5 1,4",
    ".": "3,7 3,7",
    ",": "3,6 3,7|2,8 3,7",
    ":": "3,2 3,2|3,6 3,6",
    ";": "3,2 3,2|3,5 3,7 2,8",
    "!": "3,0 3,5|3,7 3,7",
    "?": "1,1 2,0 4,0 5,1 5,3 4,4 3,4|3,6 3,6",
    "'": "3,0 2,2",
    '"': "2,0 2,2|4,0 4,2",
    "-": "0,4 6,4",
    "(": "4,0 2,1 1,3 1,5 2,7 4,8",
    ")": "2,0 4,1 5,3 5,5 4,7 2,8",
    "/": "5,0 1,8",
    "&": "5,0 3,1 1,3 1,5 3,6 5,7 5,8 1,8|1,3 5,5",
    "%": "1,0 0,1 0,2 1,3 2,2 2,1 1,0|4,5 5,5 6,6 6,7 5,8 4,7 4,6 5,5|5,0 1,8",
    "+": "3,1 3,7|0,4 6,4",
    "=": "0,3 6,3|0,5 6,5",
    "$": "3,0 3,8|5,1 4,0 2,0 1,1 1,3 2,4 4,4 5,5 5,7 4,8 2,8 1,7",
    "·": "3,4 3,4",
}

WIDTHS = {
    "I": 4, "1": 4, ".": 3, ",": 3, ":": 3, ";": 3, "!": 3, "'": 3,
    '"': 4, "-": 4, "(": 4, ")": 4, "/": 4, "·": 3, " ": 3, "M": 7,
    "W": 8, "%": 7, "&": 7,
}


def _glyph(ch):
    """Parse a glyph definition into a list of strokes (point lists)."""
    strokes = []
    for part in FONT.get(ch, FONT["?"]).split("|"):
        pts = []
        for tok in part.split():
            px, py = tok.split(",")
            pts.append((float(px), float(py)))
        strokes.append(pts)
    return strokes


# -------------------------------------------------------------- canvas ----
class Canvas:
    """RGB raster in page coordinates (1024x1024), rendered at 2x."""

    def __init__(self):
        self.buf = bytearray(CW * CH * 3)
        self.fill_rect(0, 0, W, H, PAPER)

    def _row(self, y):
        return y * CW * 3

    def hline(self, x0, x1, y, color):
        """Fill one horizontal run; all args in page coordinates."""
        yi = int(round(y * SS))
        if yi < 0 or yi >= CH:
            return
        a = max(0, int(round(x0 * SS)))
        b = min(CW - 1, int(round(x1 * SS)))
        if b < a:
            return
        r, g, bl = color
        i = self._row(yi) + a * 3
        n = b - a + 1
        self.buf[i:i + 3 * n] = bytes((r, g, bl)) * n

    def fill_rect(self, x0, y0, x1, y1, color):
        for y in range(max(0, int(round(y0 * SS))),
                       min(CH, int(round(y1 * SS)))):
            self.hline(x0, x1 - 1.0 / SS, y / SS, color)

    def fill_poly(self, pts, color):
        """Scanline fill of a polygon given in page coordinates."""
        P = [(x * SS, y * SS) for x, y in pts]
        ymin = max(0, int(math.floor(min(p[1] for p in P))))
        ymax = min(CH - 1, int(math.ceil(max(p[1] for p in P))))
        edges = []
        n = len(P)
        for i in range(n):
            x0, y0 = P[i]
            x1, y1 = P[(i + 1) % n]
            if y0 != y1:
                edges.append((y0, x0, y1, x1))
        for yi in range(ymin, ymax + 1):
            xs = []
            for y0, x0, y1, x1 in edges:
                if (y0 <= yi < y1) or (y1 <= yi < y0):
                    t = (yi - y0) / (y1 - y0)
                    xs.append(x0 + t * (x1 - x0))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                self.hline(xs[k] / SS, xs[k + 1] / SS, yi / SS, color)

    def disc(self, cx, cy, r, color):
        """Filled circle, page coordinates."""
        cx, cy, r = cx * SS, cy * SS, r * SS
        r2 = r * r
        for dy in range(-int(r) - 1, int(r) + 2):
            dx = math.sqrt(max(0.0, r2 - dy * dy))
            self.hline((cx - dx) / SS, (cx + dx) / SS, (cy + dy) / SS, color)

    def line(self, x0, y0, x1, y1, half, color):
        """Thick line with round caps, page coordinates."""
        dx, dy = x1 - x0, y1 - y0
        length = math.hypot(dx, dy)
        if length < 0.01:
            self.disc(x0, y0, half, color)
            return
        nx, ny = -dy / length * half, dx / length * half
        self.fill_poly([(x0 + nx, y0 + ny), (x1 + nx, y1 + ny),
                        (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)], color)
        self.disc(x0, y0, half, color)
        self.disc(x1, y1, half, color)

    def arc(self, cx, cy, rx, ry, a0, a1, half, color, steps=40):
        """Elliptical arc as a thick polyline, angles in radians."""
        prev = None
        for i in range(steps + 1):
            a = a0 + (a1 - a0) * i / steps
            p = (cx + rx * math.cos(a), cy + ry * math.sin(a))
            if prev is not None:
                self.line(prev[0], prev[1], p[0], p[1], half, color)
            prev = p

    # ------------------------------------------------------------ text ----
    def text_w(self, s, size, bold=False):
        s = s.upper()
        unit = size / 8.0
        track = size * 0.06
        total = 0.0
        for ch in s:
            if ch == "●":
                total += 6 * unit + track
            else:
                total += WIDTHS.get(ch, 6) * unit + track
        return total - track if total else 0.0

    def text(self, x, y, s, size, color, bold=False, align="l"):
        """Draw text; y is the top of the cap height. Returns end x."""
        s = s.upper()
        if align == "c":
            x -= self.text_w(s, size, bold) / 2.0
        elif align == "r":
            x -= self.text_w(s, size, bold)
        unit = size / 8.0
        track = size * 0.06
        thick = max(1.0, size * (0.14 if bold else 0.105))
        half = thick / 2.0
        for ch in s:
            if ch == " ":
                x += WIDTHS[" "] * unit + track
                continue
            if ch == "●":
                self.disc(x + 3 * unit, y + 4 * unit, size * 0.17, color)
                x += 6 * unit + track
                continue
            for stroke in _glyph(ch):
                pts = [(x + px * unit, y + py * unit) for px, py in stroke]
                for a, b in zip(pts, pts[1:]):
                    self.line(a[0], a[1], b[0], b[1], half, color)
            x += WIDTHS.get(ch, 6) * unit + track
        return x

    def wrap(self, s, size, maxw, bold=False):
        """Word-wrap to lines no wider than maxw (page units)."""
        lines, cur = [], ""
        for word in s.split(" "):
            trial = word if not cur else cur + " " + word
            if self.text_w(trial, size, bold) <= maxw or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
        return lines

    def para(self, x, y, s, size, maxw, leading, color, bold=False,
             max_lines=None):
        """Draw a wrapped paragraph; returns the y after the last line."""
        lines = self.wrap(s, size, maxw, bold)
        if max_lines is not None:
            lines = lines[:max_lines]
        for ln in lines:
            self.text(x, y, ln, size, color, bold)
            y += leading
        return y

    # ------------------------------------------------------- downsample ---
    def to_png(self):
        """Average the 2x buffer down to 1024x1024 and encode a PNG."""
        rows = []
        buf = self.buf
        for oy in range(H):
            y0 = (2 * oy) * CW * 3
            y1 = (2 * oy + 1) * CW * 3
            row = bytearray(W * 3)
            for ox in range(W):
                i0 = y0 + ox * 6
                i1 = y1 + ox * 6
                row[ox * 3] = (buf[i0] + buf[i0 + 3] + buf[i1] + buf[i1 + 3]) // 4
                row[ox * 3 + 1] = (buf[i0 + 1] + buf[i0 + 4] + buf[i1 + 1] + buf[i1 + 4]) // 4
                row[ox * 3 + 2] = (buf[i0 + 2] + buf[i0 + 5] + buf[i1 + 2] + buf[i1 + 5]) // 4
            rows.append(bytes(row))
        raw = b"".join(b"\x00" + r for r in rows)
        comp = zlib.compress(raw, 9)

        def chunk(kind, data):
            out = struct.pack(">I", len(data)) + kind + data
            out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
            return out

        ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
        return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
                + chunk(b"IDAT", comp) + chunk(b"IEND", b""))


# --------------------------------------------------------------- icons ----
def draw_jet(cv, x, y, s, color=NAVY):
    """Jet seen from above, flying right, inside a box of size s."""
    u = s / 100.0
    cv.fill_poly([(x + 8 * u, y + 52 * u), (x + 30 * u, y + 46 * u),
                  (x + 78 * u, y + 46 * u), (x + 94 * u, y + 50 * u),
                  (x + 78 * u, y + 54 * u), (x + 30 * u, y + 54 * u)],
                 color)
    cv.fill_poly([(x + 38 * u, y + 46 * u), (x + 52 * u, y + 22 * u),
                  (x + 60 * u, y + 22 * u), (x + 56 * u, y + 46 * u)],
                 color)
    cv.fill_poly([(x + 40 * u, y + 54 * u), (x + 50 * u, y + 76 * u),
                  (x + 58 * u, y + 76 * u), (x + 54 * u, y + 54 * u)],
                 color)
    cv.fill_poly([(x + 10 * u, y + 46 * u), (x + 22 * u, y + 30 * u),
                  (x + 28 * u, y + 30 * u), (x + 26 * u, y + 46 * u)],
                 color)
    cv.fill_poly([(x + 12 * u, y + 54 * u), (x + 24 * u, y + 68 * u),
                  (x + 28 * u, y + 68 * u), (x + 26 * u, y + 54 * u)],
                 color)
    cv.disc(x + 82 * u, y + 50 * u, 2.2 * u, PAPER)


def draw_island(cv, x, y, s):
    """Green island in a blue sea with wave lines."""
    u = s / 100.0
    cv.fill_rect(x, y + 62 * u, s, y + s, SEA)
    cv.fill_poly([(x + 8 * u, y + 66 * u), (x + 28 * u, y + 34 * u),
                  (x + 52 * u, y + 22 * u), (x + 76 * u, y + 44 * u),
                  (x + 94 * u, y + 66 * u)], GREEN)
    cv.fill_poly([(x + 52 * u, y + 22 * u), (x + 58 * u, y + 34 * u),
                  (x + 48 * u, y + 36 * u)], (90, 140, 80))
    for k in range(3):
        yy = y + (74 + k * 9) * u
        cv.arc(x + (16 + k * 26) * u, yy, 12 * u, 4 * u,
               math.pi * 1.15, math.pi * 1.85, 1.4 * u, PAPER, steps=14)


def draw_alert(cv, x, y, s):
    """Red warning triangle with an exclamation mark."""
    u = s / 100.0
    cv.fill_poly([(x + 50 * u, y + 6 * u), (x + 94 * u, y + 88 * u),
                  (x + 6 * u, y + 88 * u)], RED)
    cv.fill_poly([(x + 50 * u, y + 18 * u), (x + 82 * u, y + 80 * u),
                  (x + 18 * u, y + 80 * u)], PAPER)
    cv.line(x + 50 * u, y + 32 * u, x + 50 * u, y + 58 * u, 4 * u, RED)
    cv.disc(x + 50 * u, y + 70 * u, 3.4 * u, RED)


def draw_chip(cv, x, y, s, banned=False):
    """Microchip with pins; optional red ban circle."""
    u = s / 100.0
    for i in range(4):
        px = x + (16 + i * 20) * u
        cv.fill_rect(px, y + 2 * u, px + 7 * u, y + 16 * u, INK)
        cv.fill_rect(px, y + 84 * u, px + 7 * u, y + 98 * u, INK)
        py = y + (16 + i * 20) * u
        cv.fill_rect(x + 2 * u, py, x + 16 * u, py + 7 * u, INK)
        cv.fill_rect(x + 84 * u, py, x + 98 * u, py + 7 * u, INK)
    cv.fill_rect(x + 14 * u, y + 14 * u, x + 86 * u, y + 86 * u, NAVY)
    cv.fill_rect(x + 30 * u, y + 30 * u, x + 70 * u, y + 70 * u, PAPER)
    cv.fill_rect(x + 40 * u, y + 40 * u, x + 60 * u, y + 60 * u, NAVY)
    if banned:
        cv.arc(x + 50 * u, y + 50 * u, 40 * u, 40 * u, 0, math.pi * 2,
               5 * u, RED, steps=48)
        cv.line(x + 22 * u, y + 78 * u, x + 78 * u, y + 22 * u, 5 * u, RED)


def draw_satellite(cv, x, y, s):
    """Satellite with two solar panels on a dashed orbit ring."""
    u = s / 100.0
    for i in range(12):
        a = math.pi * 2 * i / 12
        if i % 2 == 0:
            cv.disc(x + 50 * u + 44 * u * math.cos(a),
                    y + 50 * u + 44 * u * math.sin(a), 1.6 * u, GREY)
    cv.fill_rect(x + 8 * u, y + 42 * u, x + 32 * u, y + 58 * u, NAVY)
    cv.fill_rect(x + 68 * u, y + 42 * u, x + 92 * u, y + 58 * u, NAVY)
    cv.line(x + 10 * u, y + 50 * u, x + 30 * u, y + 50 * u, 1.2 * u, PAPER)
    cv.line(x + 70 * u, y + 50 * u, x + 90 * u, y + 50 * u, 1.2 * u, PAPER)
    cv.fill_rect(x + 34 * u, y + 36 * u, x + 66 * u, y + 64 * u, GOLD)
    cv.fill_rect(x + 42 * u, y + 44 * u, x + 58 * u, y + 56 * u, INK)
    cv.line(x + 50 * u, y + 36 * u, x + 50 * u, y + 24 * u, 1.6 * u, INK)
    cv.disc(x + 50 * u, y + 21 * u, 3 * u, RED)


def draw_factory(cv, x, y, s):
    """Factory with a chimney and flames above its roof."""
    u = s / 100.0
    cv.fill_poly([(x + 30 * u, y + 96 * u), (x + 30 * u, y + 52 * u),
                  (x + 44 * u, y + 52 * u), (x + 44 * u, y + 62 * u),
                  (x + 58 * u, y + 62 * u), (x + 58 * u, y + 52 * u),
                  (x + 72 * u, y + 52 * u), (x + 72 * u, y + 62 * u),
                  (x + 86 * u, y + 62 * u), (x + 86 * u, y + 52 * u),
                  (x + 96 * u, y + 52 * u), (x + 96 * u, y + 96 * u)],
                 (72, 68, 62))
    cv.fill_rect(x + 8 * u, y + 18 * u, x + 20 * u, y + 96 * u, (72, 68, 62))
    cv.fill_rect(x + 36 * u, y + 68 * u, x + 48 * u, y + 96 * u, PAPER)
    cv.fill_rect(x + 62 * u, y + 68 * u, x + 74 * u, y + 96 * u, PAPER)
    for fx, fh in ((38, 34), (58, 44), (78, 36)):
        cv.fill_poly([(x + (fx - 9) * u, y + 52 * u),
                      (x + fx * u, y + (52 - fh) * u),
                      (x + (fx + 9) * u, y + 52 * u)], ORANGE)
        cv.fill_poly([(x + (fx - 4) * u, y + 52 * u),
                      (x + fx * u, y + (52 - fh + 12) * u),
                      (x + (fx + 4) * u, y + 52 * u)], RED)


# -------------------------------------------------------------- layout ----
def rule(cv, x0, x1, y, thick, color=INK):
    cv.fill_rect(x0, y, x1, y + thick, color)


def build():
    cv = Canvas()

    # Outer double border.
    cv.fill_rect(12, 12, 1012, 15, INK)
    cv.fill_rect(12, 1009, 1012, 1012, INK)
    cv.fill_rect(12, 12, 15, 1012, INK)
    cv.fill_rect(1009, 12, 1012, 1012, INK)
    cv.fill_rect(20, 20, 1004, 22, INK)
    cv.fill_rect(20, 1002, 1004, 1004, INK)
    cv.fill_rect(20, 20, 22, 1004, INK)
    cv.fill_rect(1002, 20, 1004, 1004, INK)

    # Masthead.
    cv.text(512, 34, "THE WORLD TODAY", 80, INK, bold=True, align="c")
    rule(cv, 28, 996, 128, 4)
    rule(cv, 28, 996, 136, 1.5)
    cv.text(28, 146, "WORLD EDITION", 16, GREY, bold=True)
    cv.text(996, 146, "NO. 329", 16, GREY, bold=True, align="r")
    cv.text(512, 142, "TUESDAY 24 NOVEMBER 2026", 40, RED, bold=True,
            align="c")
    rule(cv, 28, 996, 190, 1.5)

    # Lead story.
    cv.text(512, 202, "SUSPECTED NORTH KOREAN JET", 40, INK, bold=True,
            align="c")
    cv.text(512, 248, "BREACHES SOUTH KOREA AIRSPACE", 40, INK, bold=True,
            align="c")
    # Scene: sky box with island, radar arcs and a jet overhead.
    cv.fill_rect(28, 302, 336, 448, SKY)
    cv.fill_rect(28, 302, 336, 304, INK)
    cv.fill_rect(28, 446, 336, 448, INK)
    cv.fill_rect(28, 302, 30, 448, INK)
    cv.fill_rect(334, 302, 336, 448, INK)
    draw_island(cv, 44, 330, 120)
    cv.arc(196, 448, 150, 120, math.pi * 1.15, math.pi * 1.85, 1.6, INK,
           steps=36)
    cv.arc(196, 448, 110, 88, math.pi * 1.15, math.pi * 1.85, 1.6, INK,
           steps=36)
    draw_jet(cv, 200, 312, 120)
    draw_alert(cv, 268, 386, 52)
    cv.text(182, 452, "ULLEUNG ISLAND, 7:52 A.M.", 13, INK, bold=True,
            align="c")
    deck = ("Seoul orders people on Ulleung Island to shelter after a "
            "flying object crosses into South Korean airspace at 7:52 "
            "a.m. The alert is lifted five minutes later. Officials "
            "first blame a Russian plane, then say the intruder was "
            "probably North Korean.")
    cv.para(360, 306, deck, 20, 636, 27, INK, max_lines=6)
    rule(cv, 28, 996, 466, 2)

    # Four panels, 2 x 2.
    panels = [
        ("TECH · UNITED STATES", "HUANG BACK AT NVIDIA",
         "Board reinstates Jensen Huang as chief after Trump says he "
         "'made the deal'. Shares jump 31% in a day.",
         lambda c, x, y, s: draw_chip(c, x, y, s)),
        ("TRADE · SINGAPORE", "US BLACKLISTS MEGASPEED",
         "Singapore chip firm put on the US Entity List over alleged "
         "smuggling of Nvidia AI chips to China.",
         lambda c, x, y, s: draw_chip(c, x, y, s, banned=True)),
        ("SPACE · RUSSIA", "RUSSIA'S NUCLEAR SATELLITE ALARM",
         "Western intelligence says the 'Sputnik-S' satellite could "
         "launch by December. Moscow denies the claim.",
         draw_satellite),
        ("ASIA · INDONESIA", "24 DEAD IN INDONESIA FACTORY FIRE",
         "Candy plant blaze in Banten leaves about 30 missing. "
         "DNA tests must identify victims.",
         draw_factory),
    ]
    px0, py0, pw, ph, gap = 28, 478, 472, 190, 24
    for i, (kicker, head, body, icon) in enumerate(panels):
        x = px0 + (i % 2) * (pw + gap)
        y = py0 + (i // 2) * (ph + 12)
        cv.fill_rect(x, y, x + pw, y + ph, PANEL)
        cv.fill_rect(x, y, x + pw, y + 2, INK)
        cv.fill_rect(x, y + ph - 2, x + pw, y + ph, INK)
        cv.fill_rect(x, y, x + 2, y + ph, INK)
        cv.fill_rect(x + pw - 2, y, x + pw, y + ph, INK)
        cv.text(x + 14, y + 12, kicker, 15, RED, bold=True)
        icon(cv, x + 14, y + 42, 92)
        lines = cv.wrap(head, 22, 330, bold=True)[:2]
        hy = y + 40
        for ln in lines:
            cv.text(x + 122, hy, ln, 22, INK, bold=True)
            hy += 27
        cv.para(x + 122, hy + 6, body, 17, 330, 22, INK, max_lines=4)

    # Red ticker.
    ty = 880
    cv.fill_rect(28, ty, 996, ty + 64, RED)
    ticker = ("●  US SEEKS $1.1BN IN CRYPTO STOLEN BY N. KOREA HACKERS   "
              "●  MOSCOW WARNS ESTONIA OF 'OPEN WAR'   "
              "●  UK SANCTIONS MYANMAR GENERALS")
    cv.para(44, ty + 10, ticker, 19, 936, 25, (255, 255, 255),
            bold=True, max_lines=2)

    # Footer.
    cv.text(512, 956, "THE WORLD TODAY  ·  TUESDAY 24 NOVEMBER 2026  ·  "
                      "DRAWN BY A PROGRAM, NO PHOTOGRAPHS", 14, GREY,
            align="c")
    return cv


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    data = build().to_png()
    path = os.path.join(out_dir, "entry.png")
    with open(path, "wb") as f:
        f.write(data)
    print("wrote %s (%d bytes)" % (path, len(data)))


if __name__ == "__main__":
    main()
