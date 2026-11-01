# =====================================================================
#  A small canvas-like drawing layer on top of pygame, so the game code
#  can draw the way the browser version does: a transform stack
#  (translate / rotate / scale), paths (lines, arcs, curves, ellipses),
#  fill / stroke with see-through colours, images, text and gradients.
# =====================================================================

import math
import os
import re
import json

import pygame

HERE = os.path.dirname(os.path.abspath(__file__))


# --- JS-style objects: o.x reads like o['x'], missing fields read as None ----
class O(dict):
    def __getattr__(self, k):
        try:
            return self[k]
        except KeyError:
            return None

    def __setattr__(self, k, v):
        self[k] = v

    def __delattr__(self, k):
        self.pop(k, None)


# --- colours: '#rgb', '#rrggbb', 'rgb(...)', 'rgba(...)' -> (r, g, b, a 0..255) ----
_colors = {}


def color(c):
    got = _colors.get(c)
    if got:
        return got
    s = c.strip()
    if s.startswith('#'):
        h = s[1:]
        if len(h) == 3:
            h = ''.join(ch * 2 for ch in h)
        out = (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255)
    else:
        nums = [float(v) for v in re.findall(r'[-\d.]+', s)]
        a = nums[3] if len(nums) > 3 else 1
        out = (int(nums[0]), int(nums[1]), int(nums[2]), max(0, min(255, int(round(a * 255)))))
    _colors[c] = out
    return out


# --- fonts -------------------------------------------------------------------------
_fonts = {}
FAMILIES = {
    'sans': 'segoeui,arial',
    'mono': 'consolas,couriernew',
    'marker': 'comicsansms,segoeprint',
}


def font(weight, size, family='sans'):
    key = (weight, size, family)
    f = _fonts.get(key)
    if f is None:
        f = pygame.font.SysFont(FAMILIES.get(family, family), max(1, int(round(size * 1.0))), bold=weight >= 600)
        _fonts[key] = f
    return f


# --- images ------------------------------------------------------------------------
class Img:
    """A picture, like the browser's Image: .surf (None until loaded), natural size."""

    def __init__(self, path):
        self.surf = None
        try:
            self.surf = pygame.image.load(os.path.join(HERE, path)).convert_alpha()
        except Exception as e:
            print('could not load', path, e)

    @property
    def complete(self):
        return True

    @property
    def naturalWidth(self):
        return self.surf.get_width() if self.surf else 0

    @property
    def naturalHeight(self):
        return self.surf.get_height() if self.surf else 0


# --- saving (the browser's localStorage) --------------------------------------------
STORE_FILE = os.path.join(HERE, 'save_data.json')


def store_get(key):
    try:
        with open(STORE_FILE, 'r', encoding='utf8') as f:
            return json.load(f).get(key)
    except Exception:
        return None


def store_set(key, value):
    data = {}
    try:
        with open(STORE_FILE, 'r', encoding='utf8') as f:
            data = json.load(f)
    except Exception:
        pass
    data[key] = value
    try:
        with open(STORE_FILE, 'w', encoding='utf8') as f:
            json.dump(data, f)
    except Exception:
        pass


# --- clipboard ------------------------------------------------------------------------
def clipboard_set(text):
    try:
        import tkinter
        r = tkinter.Tk()
        r.withdraw()
        r.clipboard_clear()
        r.clipboard_append(text)
        r.update()
        r.destroy()
        return True
    except Exception:
        return False


def clipboard_get():
    try:
        import tkinter
        r = tkinter.Tk()
        r.withdraw()
        try:
            t = r.clipboard_get()
        except Exception:
            t = ''
        r.destroy()
        return t
    except Exception:
        return ''


# --- gradients (cached pictures) ---------------------------------------------------------
_grad_cache = {}


def _stop_at(stops, t):
    """Colour (r, g, b, a 0..1) at t along gradient stops [(pos, '#color' / 'rgba(...)')]."""
    if t <= stops[0][0]:
        c = color(stops[0][1])
        return c[0], c[1], c[2], c[3] / 255
    for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
        if t <= p1:
            k = 0 if p1 == p0 else (t - p0) / (p1 - p0)
            a, b = color(c0), color(c1)
            return tuple(a[i] + (b[i] - a[i]) * k for i in range(3)) + ((a[3] + (b[3] - a[3]) * k) / 255,)
    c = color(stops[-1][1])
    return c[0], c[1], c[2], c[3] / 255


def radial_surface(r0, r1, stops, premultiplied=False):
    """A (2*r1) square picture of a radial gradient centred in it. Outside r1 is see-through."""
    r1 = max(1, int(r1))
    key = ('rad', r0, r1, tuple(stops), premultiplied)
    s = _grad_cache.get(key)
    if s:
        return s
    size = 2 * r1
    if premultiplied:
        s = pygame.Surface((size, size))
        s.fill((0, 0, 0))
    else:
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        s.fill((0, 0, 0, 0))
    for r in range(r1, 0, -1):
        t = 0 if r <= r0 else (r - r0) / max(1e-6, r1 - r0)
        cr, cg, cb, ca = _stop_at(stops, t)
        if premultiplied:
            pygame.draw.circle(s, (int(cr * ca), int(cg * ca), int(cb * ca)), (r1, r1), r)
        else:
            pygame.draw.circle(s, (int(cr), int(cg), int(cb), int(ca * 255)), (r1, r1), r)
    _grad_cache[key] = s
    return s


def hole_mask(r0, r1, keep):
    """A (2*r1) picture to multiply into a dark layer: alpha = keep(t) (1 = stays dark),
    t = 0 inside r0 to 1 at r1. Outside the circle it keeps everything."""
    r1 = max(1, int(r1))
    key = ('hole', r0, r1, keep.__name__)
    s = _grad_cache.get(key)
    if s:
        return s
    size = 2 * r1
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    s.fill((255, 255, 255, 255))
    for r in range(r1, 0, -1):
        t = 0 if r <= r0 else (r - r0) / max(1e-6, r1 - r0)
        pygame.draw.circle(s, (255, 255, 255, int(max(0, min(1, keep(t))) * 255)), (r1, r1), r)
    _grad_cache[key] = s
    return s


def linear_v(w, h, top, bot):
    key = ('lin', w, h, top, bot)
    s = _grad_cache.get(key)
    if s:
        return s
    s = pygame.Surface((w, h))
    a, b = color(top), color(bot)
    for y in range(h):
        k = y / max(1, h - 1)
        pygame.draw.line(s, tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3)), (0, y), (w, y))
    _grad_cache[key] = s
    return s


# --- the drawing context ----------------------------------------------------------------
class Ctx:
    def __init__(self, surf):
        self.surf = surf
        self.m = [1.0, 0.0, 0.0, 1.0, 0.0, 0.0]   # x' = a x + c y + e, y' = b x + d y + f
        self.stack = []
        self.globalAlpha = 1.0
        self.fillStyle = '#000'
        self.strokeStyle = '#000'
        self.lineWidth = 1
        self.font = font(400, 10)
        self.textAlign = 'left'
        self.textBaseline = 'alphabetic'
        self.imageSmoothingEnabled = True
        self.comp = 'source-over'
        self.clip_r = None
        self.paths = []      # [[points], closed] in screen pixels, or ('circle', x, y, r)
        self.cur = None
        self.pen = (0.0, 0.0)  # current point, local coordinates
        self.shadow = None     # (alpha, offset y) for images while set
        self._img_cache = {}

    # --- state
    def save(self):
        self.stack.append((self.m[:], self.globalAlpha, self.fillStyle, self.strokeStyle, self.lineWidth,
                           self.font, self.textAlign, self.textBaseline, self.imageSmoothingEnabled,
                           self.comp, self.clip_r, self.shadow))

    def restore(self):
        if not self.stack:
            return
        (self.m, self.globalAlpha, self.fillStyle, self.strokeStyle, self.lineWidth, self.font,
         self.textAlign, self.textBaseline, self.imageSmoothingEnabled, self.comp, clip, self.shadow) = self.stack.pop()
        if clip != self.clip_r:
            self.clip_r = clip
            self.surf.set_clip(clip)

    def setTransform(self, a=1, b=0, c=0, d=1, e=0, f=0):
        self.m = [a, b, c, d, e, f]

    def resetTransform(self):
        self.m = [1.0, 0.0, 0.0, 1.0, 0.0, 0.0]

    def translate(self, x, y):
        a, b, c, d, e, f = self.m
        self.m[4] = e + a * x + c * y
        self.m[5] = f + b * x + d * y

    def scale(self, sx, sy):
        self.m[0] *= sx
        self.m[1] *= sx
        self.m[2] *= sy
        self.m[3] *= sy

    def rotate(self, t):
        if not t:
            return
        co, si = math.cos(t), math.sin(t)
        a, b, c, d = self.m[0], self.m[1], self.m[2], self.m[3]
        self.m[0] = a * co + c * si
        self.m[1] = b * co + d * si
        self.m[2] = -a * si + c * co
        self.m[3] = -b * si + d * co

    def pt(self, x, y):
        a, b, c, d, e, f = self.m
        return a * x + c * y + e, b * x + d * y + f

    def aligned(self):
        return abs(self.m[1]) < 1e-9 and abs(self.m[2]) < 1e-9

    # --- clip (axis-aligned boxes only)
    def clip_rect(self, x, y, w, h):
        x0, y0 = self.pt(x, y)
        x1, y1 = self.pt(x + w, y + h)
        r = pygame.Rect(int(round(min(x0, x1))), int(round(min(y0, y1))),
                        int(round(abs(x1 - x0))), int(round(abs(y1 - y0))))
        if self.clip_r:
            r = r.clip(self.clip_r)
        self.clip_r = r
        self.surf.set_clip(r)

    # --- low-level fills
    def _rgba(self, style):
        r, g, b, a = color(style)
        return r, g, b, int(a * self.globalAlpha)

    def _fill_screen_rect(self, rect, col):
        r, g, b, a = col
        if a <= 0 or rect.w <= 0 or rect.h <= 0:
            return
        if self.comp == 'lighter':
            k = a / 255
            self.surf.fill((int(r * k), int(g * k), int(b * k)), rect, special_flags=pygame.BLEND_RGB_ADD)
        elif a >= 255:
            self.surf.fill((r, g, b), rect)
        else:
            s = pygame.Surface((rect.w, rect.h))
            s.fill((r, g, b))
            s.set_alpha(a)
            self.surf.blit(s, rect.topleft)

    def _fill_poly(self, pts, col):
        r, g, b, a = col
        if a <= 0 or len(pts) < 3:
            return
        if a >= 255 and self.comp != 'lighter':
            pygame.draw.polygon(self.surf, (r, g, b), pts)
            return
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        x0, y0 = int(math.floor(min(xs))), int(math.floor(min(ys)))
        w, h = int(math.ceil(max(xs))) - x0 + 1, int(math.ceil(max(ys))) - y0 + 1
        if w <= 0 or h <= 0 or w > 5000 or h > 5000:
            return
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.polygon(s, (r, g, b, a), [(px - x0, py - y0) for px, py in pts])
        self.surf.blit(s, (x0, y0), special_flags=pygame.BLEND_RGB_ADD if self.comp == 'lighter' else 0)

    def _fill_circle(self, x, y, rad, col, width=0):
        r, g, b, a = col
        if a <= 0 or rad <= 0:
            return
        if a >= 255:
            pygame.draw.circle(self.surf, (r, g, b), (x, y), rad, width)
            return
        R = int(math.ceil(rad)) + 2
        s = pygame.Surface((2 * R, 2 * R), pygame.SRCALPHA)
        pygame.draw.circle(s, (r, g, b, a), (R + (x % 1), R + (y % 1)), rad, width)
        self.surf.blit(s, (int(x) - R, int(y) - R))

    def fillRect(self, x, y, w, h):
        col = self._rgba(self.fillStyle)
        if self.aligned():
            x0, y0 = self.pt(x, y)
            x1, y1 = self.pt(x + w, y + h)
            if x0 > x1:
                x0, x1 = x1, x0
            if y0 > y1:
                y0, y1 = y1, y0
            X0, Y0 = int(math.floor(x0 + 0.5)), int(math.floor(y0 + 0.5))
            X1, Y1 = int(math.floor(x1 + 0.5)), int(math.floor(y1 + 0.5))
            if X1 == X0 and x1 - x0 > 0.25:
                X1 = X0 + 1
            if Y1 == Y0 and y1 - y0 > 0.25:
                Y1 = Y0 + 1
            self._fill_screen_rect(pygame.Rect(X0, Y0, X1 - X0, Y1 - Y0), col)
        else:
            self._fill_poly([self.pt(x, y), self.pt(x + w, y), self.pt(x + w, y + h), self.pt(x, y + h)], col)

    def strokeRect(self, x, y, w, h):
        self.beginPath()
        self.rect(x, y, w, h)
        self.stroke()

    # --- paths
    def beginPath(self):
        self.paths = []
        self.cur = None

    def _new(self):
        self.cur = [[], False]
        self.paths.append(self.cur)

    def moveTo(self, x, y):
        self._new()
        self.cur[0].append(self.pt(x, y))
        self.pen = (x, y)

    def lineTo(self, x, y):
        if self.cur is None or isinstance(self.cur, tuple):
            self._new()
        self.cur[0].append(self.pt(x, y))
        self.pen = (x, y)

    def closePath(self):
        if self.cur is not None and not isinstance(self.cur, tuple):
            self.cur[1] = True
            if self.cur[0]:
                p = self.cur[0][0]
                a, b, c, d, e, f = self.m
                det = a * d - b * c
                if det:
                    # pen back to the start (local coordinates)
                    px, py = p[0] - e, p[1] - f
                    self.pen = ((d * px - c * py) / det, (-b * px + a * py) / det)

    def _scale_k(self):
        a, b, c, d = self.m[0], self.m[1], self.m[2], self.m[3]
        return math.sqrt(abs(a * d - b * c))

    def arc(self, cx, cy, r, a0, a1, ccw=False):
        full = abs(a1 - a0) >= math.pi * 2 - 1e-6
        a, b, c, d = self.m[0], self.m[1], self.m[2], self.m[3]
        if full and (self.cur is None or isinstance(self.cur, tuple) or not self.cur[0]) and self.aligned() and abs(abs(a) - abs(d)) < 1e-9:
            x, y = self.pt(cx, cy)
            if self.cur is not None and not isinstance(self.cur, tuple) and not self.cur[0]:
                self.paths.remove(self.cur)
            self.cur = ('circle', x, y, r * abs(a))
            self.paths.append(self.cur)
            self.pen = (cx + r * math.cos(a1), cy + r * math.sin(a1))
            return
        if full:
            a1 = a0 - math.pi * 2 if ccw else a0 + math.pi * 2
        elif ccw:
            while a1 > a0:
                a1 -= math.pi * 2
        else:
            while a1 < a0:
                a1 += math.pi * 2
        span = a1 - a0
        n = max(6, int(abs(span) * max(3, r * self._scale_k()) / 6))
        n = min(n, 120)
        for i in range(n + 1):
            t = a0 + span * i / n
            self.lineTo(cx + math.cos(t) * r, cy + math.sin(t) * r)

    def ellipse(self, cx, cy, rx, ry, rot, a0, a1, ccw=False):
        span = a1 - a0
        n = max(8, min(80, int(abs(span) * max(rx, ry) * self._scale_k() / 6)))
        co, si = math.cos(rot), math.sin(rot)
        for i in range(n + 1):
            t = a0 + span * i / n
            ex, ey = math.cos(t) * rx, math.sin(t) * ry
            self.lineTo(cx + ex * co - ey * si, cy + ex * si + ey * co)

    def quadraticCurveTo(self, qx, qy, x, y):
        x0, y0 = self.pen
        n = 12
        for i in range(1, n + 1):
            t = i / n
            u = 1 - t
            self.lineTo(u * u * x0 + 2 * u * t * qx + t * t * x, u * u * y0 + 2 * u * t * qy + t * t * y)

    def rect(self, x, y, w, h):
        self.moveTo(x, y)
        self.lineTo(x + w, y)
        self.lineTo(x + w, y + h)
        self.lineTo(x, y + h)
        self.closePath()

    def roundRect(self, x, y, w, h, r):
        if isinstance(r, (list, tuple)):
            tl, tr, br, bl = r
        else:
            tl = tr = br = bl = r
        self.moveTo(x + tl, y)
        self.lineTo(x + w - tr, y)
        self.arc(x + w - tr, y + tr, tr, -math.pi / 2, 0)
        self.lineTo(x + w, y + h - br)
        self.arc(x + w - br, y + h - br, br, 0, math.pi / 2)
        self.lineTo(x + bl, y + h)
        self.arc(x + bl, y + h - bl, bl, math.pi / 2, math.pi)
        self.lineTo(x, y + tl)
        self.arc(x + tl, y + tl, tl, math.pi, math.pi * 1.5)
        self.closePath()

    def fill(self):
        col = self._rgba(self.fillStyle)
        for p in self.paths:
            if isinstance(p, tuple):
                self._fill_circle(p[1], p[2], p[3], col)
            else:
                self._fill_poly(p[0], col)

    def stroke(self):
        col = self._rgba(self.strokeStyle)
        if col[3] <= 0:
            return
        wdt = max(1, int(round(self.lineWidth * self._scale_k())))
        for p in self.paths:
            if isinstance(p, tuple):
                self._fill_circle(p[1], p[2], p[3], col, wdt)
                continue
            pts, closed = p
            if len(pts) < 2:
                continue
            if col[3] >= 255:
                pygame.draw.lines(self.surf, col[:3], closed, pts, wdt)
                if wdt > 2:
                    for q in pts:
                        pygame.draw.circle(self.surf, col[:3], q, wdt / 2 - 0.5)
            else:
                xs = [q[0] for q in pts]
                ys = [q[1] for q in pts]
                x0, y0 = int(min(xs)) - wdt - 1, int(min(ys)) - wdt - 1
                w, h = int(max(xs)) - x0 + wdt + 2, int(max(ys)) - y0 + wdt + 2
                if w > 5000 or h > 5000:
                    continue
                s = pygame.Surface((w, h), pygame.SRCALPHA)
                pygame.draw.lines(s, col, closed, [(q[0] - x0, q[1] - y0) for q in pts], wdt)
                self.surf.blit(s, (x0, y0))

    # --- images
    def drawImage(self, img, *args):
        surf = img.surf if isinstance(img, Img) else img
        if surf is None:
            return
        if len(args) == 8:
            sx, sy, sw, sh, dx, dy, dw, dh = args
            sub = (int(sx), int(sy), int(sw), int(sh))
        elif len(args) == 4:
            dx, dy, dw, dh = args
            sub = None
        else:
            dx, dy = args
            dw, dh = surf.get_width(), surf.get_height()
            sub = None
        a, b, c, d = self.m[0], self.m[1], self.m[2], self.m[3]
        kx = math.hypot(a, b)
        if kx < 1e-9:
            return
        ky = (a * d - b * c) / kx
        phi = math.atan2(b, a)
        W, H = kx * dw, ky * dh
        fx, fy = W < 0, H < 0
        W, H = abs(W), abs(H)
        if W < 0.5 or H < 0.5:
            return
        deg = -math.degrees(phi)
        if abs(deg) < 0.05:
            deg = 0
        # (only pictures that stay around are cached: a passing surface's id can be reused)
        key = (id(surf), sub, int(round(W)), int(round(H)), fx, fy, round(deg, 1), self.imageSmoothingEnabled) \
            if isinstance(img, Img) else None
        out = self._img_cache.get(key) if key else None
        if out is None:
            src = surf.subsurface(sub) if sub else surf
            size = (max(1, int(round(W))), max(1, int(round(H))))
            out = (pygame.transform.smoothscale if self.imageSmoothingEnabled else pygame.transform.scale)(src, size)
            if fx or fy:
                out = pygame.transform.flip(out, fx, fy)
            if deg:
                out = pygame.transform.rotate(out, deg)
            if key:
                if len(self._img_cache) > 400:
                    self._img_cache.clear()
                self._img_cache[key] = out
        cx, cy = self.pt(dx + dw / 2, dy + dh / 2)
        pos = (int(round(cx - out.get_width() / 2)), int(round(cy - out.get_height() / 2)))
        alpha = int(255 * self.globalAlpha)
        if self.shadow:
            sh = out.copy()
            sh.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGB_MULT)
            sh.set_alpha(int(alpha * self.shadow[0]))
            self.surf.blit(sh, (pos[0], pos[1] + self.shadow[1]))
        if alpha < 255:
            out = out.copy()
            out.set_alpha(alpha)
        self.surf.blit(out, pos)

    # --- text (axis-aligned; scaling makes the letters bigger)
    def measureText(self, text):
        return self.font.size(text)[0]

    def _text_pos(self, surf_w, surf_h, x, y):
        k = abs(self.m[0]) or 1
        X, Y = self.pt(x, y)
        if self.textAlign == 'center':
            X -= surf_w / 2
        elif self.textAlign == 'right':
            X -= surf_w
        asc = self.font.get_ascent() * self._fscale
        if self.textBaseline == 'middle':
            Y -= surf_h / 2
        elif self.textBaseline == 'alphabetic':
            Y -= asc
        elif self.textBaseline == 'bottom':
            Y -= surf_h
        return int(round(X)), int(round(Y))

    def _render(self, text, style):
        k = abs(self.m[0]) or 1
        f = self.font
        self._fscale = 1
        if abs(k - 1) > 0.02:
            # a bigger (or smaller) copy of the font for scaled text
            for key, val in _fonts.items():
                if val is f:
                    f = font(key[0], max(1, int(round(key[1] * k))), key[2])
                    break
            self._fscale = k
        r, g, b, a = self._rgba(style)
        s = f.render(text, True, (r, g, b))
        if a < 255:
            s.set_alpha(a)
        return s

    def fillText(self, text, x, y):
        text = str(text)
        if not text:
            return
        if not self.aligned():
            # turned text: render it flat, then draw it like a picture
            r, g, b, a = self._rgba(self.fillStyle)
            s = self.font.render(text, True, (r, g, b))
            w, h = s.get_width(), s.get_height()
            lx = x - (w / 2 if self.textAlign == 'center' else w if self.textAlign == 'right' else 0)
            ly = y - (h / 2 if self.textBaseline == 'middle' else self.font.get_ascent() if self.textBaseline == 'alphabetic'
                      else h if self.textBaseline == 'bottom' else 0)
            old = self.globalAlpha
            self.globalAlpha = old * a / 255
            self.drawImage(s, lx, ly, w, h)
            self.globalAlpha = old
            return
        s = self._render(text, self.fillStyle)
        self.surf.blit(s, self._text_pos(s.get_width(), s.get_height(), x, y))

    def strokeText(self, text, x, y):
        text = str(text)
        if not text:
            return
        s = self._render(text, self.strokeStyle)
        X, Y = self._text_pos(s.get_width(), s.get_height(), x, y)
        r = max(1, int(round(self.lineWidth * (abs(self.m[0]) or 1) / 2)))
        for i in range(16):
            t = i * math.pi / 8
            self.surf.blit(s, (X + int(round(math.cos(t) * r)), Y + int(round(math.sin(t) * r))))

    # --- gradients: a cached radial picture, blitted centred on (cx, cy) (local coordinates)
    def fillRadial(self, cx, cy, r0, r1, stops, clip=None, add=False):
        X, Y = self.pt(cx, cy)
        k = self._scale_k()
        s = radial_surface(r0 * k, int(r1 * k), stops, premultiplied=add)
        old = self.clip_r
        if clip:
            self.clip_rect(*clip)
        R = s.get_width() // 2
        if add:
            self.surf.blit(s, (int(X) - R, int(Y) - R), special_flags=pygame.BLEND_RGB_ADD)
        elif self.globalAlpha < 1:
            t = s.copy()
            t.set_alpha(int(255 * self.globalAlpha))
            self.surf.blit(t, (int(X) - R, int(Y) - R))
        else:
            self.surf.blit(s, (int(X) - R, int(Y) - R))
        if clip:
            self.clip_r = old
            self.surf.set_clip(old)
