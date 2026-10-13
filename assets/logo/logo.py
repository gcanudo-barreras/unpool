"""The unpool logo, drawn as terminal cells.

    python assets/logo/logo.py path/to/JetBrainsMono-Regular.ttf

-> logo.svg, icon.svg (glyphs as paths, no font needed to view them) and,
   when Chrome or Edge is found, banner.png (1280x640) and icon.png (400x400).

An olympic pool split into lanes, one subject per lane. Every lane starts at a
prompt; the swimmers are cursors. One has not left the block: it is the name,
and its cursor is the only one that blinks. In logo.svg the others swim, one
cell at a time, each at its own pace (SMIL, so it plays where GitHub shows the
README); where nothing animates, the first frame is the still picture.

Every glyph sits on the cell grid, so the picture could be printed by a real
terminal. The font is JetBrains Mono (SIL OFL 1.1), from
https://github.com/JetBrains/JetBrainsMono/raw/master/fonts/ttf/JetBrainsMono-Regular.ttf
"""
import os
import shutil
import subprocess
import sys
import tempfile

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

HERE = os.path.dirname(os.path.abspath(__file__))

BG, WATER, WALL = "#0a0f1a", "#0d2137", "#5b6b82"
ROPE, ROPE_END, BEAD = "#2f6fb0", "#c8443c", "#d7dee8"
WAKE, SWIM, TEXT, PROMPT = "#3f8fb8", "#f5b82e", "#e3e8ef", "#5fd38a"
CW, CH, FS = 9.6, 21, 16          # cell = one advance x one line (1320/1000 em)


class Grid:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.c = [[[" ", TEXT, None] for _ in range(w)] for _ in range(h)]
        self.blink = set()
        self.swim = []                # (row, cursor col, wake, seconds per cell, first, last)

    def put(self, r, c, s, fg=TEXT):
        for i, ch in enumerate(s):
            self.c[r][c + i][:2] = ch, fg

    def fill(self, r, c0, c1, bg):
        for c in range(c0, c1):
            self.c[r][c][2] = bg

    def svg(self, font):
        glyphs, upm = font.getGlyphSet(), font["head"].unitsPerEm
        cmap, s = font.getBestCmap(), FS / upm
        W, H = self.w * CW, self.h * CH
        defs, body = {}, []
        for r, row in enumerate(self.c):          # one rect per run: no seams
            c = 0
            while c < self.w:
                bg, end = row[c][2], c
                while end < self.w and row[end][2] == bg:
                    end += 1
                if bg:
                    body.append('<rect x="%.1f" y="%d" width="%.1f" height="%d" '
                                'fill="%s" shape-rendering="crispEdges"/>'
                                % (c * CW, r * CH, (end - c) * CW, CH + 1, bg))
                c = end

        def use(ch, r, c, fg, inner=""):
            gid = "g%x" % ord(ch)
            if gid not in defs:
                pen = SVGPathPen(glyphs)
                glyphs[cmap[ord(ch)]].draw(pen)
                defs[gid] = ('<path id="%s" transform="scale(%g,-%g)" d="%s"/>'
                             % (gid, s, s, pen.getCommands()))
            return ('<use href="#%s" x="%.1f" y="%.1f" fill="%s">%s</use>'
                    % (gid, c * CW, r * CH + FS * 1.02, fg, inner))   # ascent

        for r, row in enumerate(self.c):
            for c, (ch, fg, _) in enumerate(row):
                if ch == " ":
                    continue
                blink = ('<animate attributeName="opacity" values="1;0" dur="1.1s" '
                         'calcMode="discrete" repeatCount="indefinite"/>'
                         if (r, c) in self.blink else "")
                body.append(use(ch, r, c, fg, blink))
        for r, x, wake, pace, first, last in self.swim:
            # The lane is clipped after its prompt; the swimmer starts where the
            # still picture has it, swims to the far wall and comes back in at
            # the block, one cell per step.
            cells = list(range(x, last + 1)) + list(range(first, x))
            moves = ";".join("%.1f 0" % ((c - x) * CW) for c in cells)
            body.append('<clipPath id="lane%d"><rect x="%.1f" y="%d" width="%.1f" height="%d"/>'
                        '</clipPath>' % (r, (first - 1) * CW, r * CH, (last - first + 2) * CW, CH))
            swimmer = "".join(use("~", r, x - wake + i, WAKE) for i in range(wake))
            body.append('<g clip-path="url(#lane%d)"><g>%s%s<animateTransform '
                        'attributeName="transform" type="translate" values="%s" dur="%.2fs" '
                        'calcMode="discrete" repeatCount="indefinite"/></g></g>'
                        % (r, swimmer, use("▌", r, x, SWIM), moves, pace * len(cells)))
        return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %.1f %.1f" '
                'width="%.1f" height="%.1f" role="img" aria-label="unpool">\n'
                '<defs>%s</defs>\n<rect width="100%%" height="100%%" fill="%s"/>\n%s\n</svg>\n'
                % (W, H, W, H, "".join(defs.values()), BG, "\n".join(body)))


def lanes(g, inner, n):
    """Walls, water, lane ropes (red near the walls). -> the lane rows."""
    left, top = 2, 1
    for r in range(top, top + 2 * n + 1):
        g.fill(r, left, left + inner + 2, WALL)
    for i in range(2 * n - 1):
        r = top + 1 + i
        g.fill(r, left + 1, left + inner + 1, WATER)
        if i % 2:
            for c in range(inner):
                ch = "∘" if c % 2 else "•"
                end = c < 4 or c > inner - 5
                g.put(r, left + 1 + c, ch, ROPE_END if end else BEAD if ch == "•" else ROPE)
    return [top + 1 + 2 * k for k in range(n)]


PACE = (0.11, 0.15, 0.09, 0.13, 0.17, 0.12)   # seconds per cell, one per lane


def logo(inner, xs, name_lane, swim=False):
    g = Grid(inner + 6, 2 * len(xs) + 3)
    for i, (r, x) in enumerate(zip(lanes(g, inner, len(xs)), xs)):
        g.put(r, 4, ">", PROMPT)
        if i == name_lane:                   # still on the block: the name
            g.put(r, 6, "unpool", TEXT)
            g.put(r, 12, "▌", SWIM)
            g.blink.add((r, 12))
        elif swim:                           # swimming, each at its own pace
            g.swim.append((r, 3 + x, 6, PACE[i % len(PACE)], 6, inner + 2))
        else:                                # gone, each at its own pace
            wake = min(6, x - 4)
            g.put(r, 3 + x - wake, "~" * wake, WAKE)
            g.put(r, 3 + x, "▌", SWIM)
    return g


def browser():
    for p in (r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"):
        if os.path.exists(p):
            return p
    return shutil.which("google-chrome") or shutil.which("chromium")


def png(exe, svg_path, out, w, h, fit):
    """Screenshot the SVG centred on BG, `fit` of the canvas width."""
    with tempfile.TemporaryDirectory() as tmp:
        page = os.path.join(tmp, "p.html")
        with open(page, "w", encoding="utf-8") as fh:
            fh.write('<body style="margin:0;background:%s;display:grid;place-items:center;'
                     'width:%dpx;height:%dpx"><img src="file:///%s" style="width:%dpx">'
                     % (BG, w, h, svg_path.replace("\\", "/"), w * fit))
        subprocess.run([exe, "--headless=new", "--hide-scrollbars", "--disable-gpu",
                        "--force-device-scale-factor=1", "--window-size=%d,%d" % (w, h),
                        "--allow-file-access-from-files", "--user-data-dir=" + tmp,
                        "--screenshot=" + out, "file:///" + page.replace("\\", "/")],
                       check=True, capture_output=True)


def main(font_path):
    font = TTFont(font_path)
    out = {}
    for name, g in (("logo", logo(62, (41, 23, 55, 0, 48, 30), 3, swim=True)),
                    ("icon", logo(22, (17, 0, 12), 1))):
        out[name] = os.path.join(HERE, name + ".svg")
        with open(out[name], "w", encoding="utf-8") as fh:
            fh.write(g.svg(font))
        print(out[name])
    exe = browser()
    if not exe:
        print("no Chrome/Edge found: SVGs only")
        return 0
    for svg, name, w, h, fit in ((out["logo"], "banner.png", 1280, 640, .8),
                                 (out["icon"], "icon.png", 400, 400, .85)):
        png(exe, svg, os.path.join(HERE, name), w, h, fit)
        print(os.path.join(HERE, name))
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1]))
