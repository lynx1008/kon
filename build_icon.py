"""Create a small PNG icon without external graphics tools."""
from __future__ import annotations

import struct
import sys
import zlib


def png(path: str, size: int = 1024):
    pixels = [[(0, 0, 0, 0) for _ in range(size)] for _ in range(size)]

    def put(x, y, color):
        if 0 <= x < size and 0 <= y < size:
            pixels[y][x] = color

    def rounded_rect(x0, y0, x1, y1, radius, color):
        for y in range(y0, y1):
            for x in range(x0, x1):
                dx = max(x0 + radius - x, 0, x - (x1 - radius - 1))
                dy = max(y0 + radius - y, 0, y - (y1 - radius - 1))
                if dx * dx + dy * dy <= radius * radius:
                    put(x, y, color)

    def circle(cx, cy, radius, color):
        for y in range(cy - radius, cy + radius):
            for x in range(cx - radius, cx + radius):
                if (x - cx) ** 2 + (y - cy) ** 2 <= radius ** 2:
                    put(x, y, color)

    green = (151, 218, 178, 255)
    white = (249, 255, 251, 255)
    dark = (25, 49, 41, 255)
    pink = (242, 185, 177, 210)
    teal = (47, 128, 100, 255)
    rounded_rect(0, 0, size, size, 270, green)
    rounded_rect(210, 150, 815, 900, 75, white)
    for y in range(150, 330):
        for x in range(605, 815):
            put(x, y, (220, 239, 229, 255))
    circle(420, 535, 28, dark); circle(605, 535, 28, dark)
    circle(350, 635, 20, pink); circle(675, 635, 20, pink)
    for t in range(80):
        circle(484 + t // 3, 670 + abs(40 - t) // 4, 5, teal)

    raw = b"".join(b"\x00" + b"".join(bytes(px) for px in row) for row in pixels)
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
    content = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    with open(path, "wb") as handle:
        handle.write(content)


def icns(png_path: str, icns_path: str):
    data = open(png_path, "rb").read()
    entries = []
    for kind in (b"ic07", b"ic08", b"ic09", b"ic10"):
        entries.append(kind + struct.pack(">I", len(data) + 8) + data)
    payload = b"".join(entries)
    with open(icns_path, "wb") as handle:
        handle.write(b"icns" + struct.pack(">I", len(payload) + 8) + payload)


if __name__ == "__main__":
    png(sys.argv[1])
    if len(sys.argv) > 2:
        icns(sys.argv[1], sys.argv[2])
