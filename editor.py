# =====================================================================
#  Treats level editor (pygame). Run:  py editor.py
#  A port of the browser editor (editor.html / editor.js). It uses game.py
#  for drawing and for the chunk code format, so what you see here is
#  exactly what the game draws, and its codes work in both versions.
# =====================================================================

import copy
import math
import os
import random
import subprocess
import sys
import tempfile
import time

import pygame

import game
import world  # noqa: F401  (builds the areas, for Other chunks / Copy level / Generate world)
from engine import O, Ctx, font, color, store_get, store_set, clipboard_set, clipboard_get

T, LH, G = game.T, game.LH, game.G
HERE = os.path.dirname(os.path.abspath(__file__))

DRAFT_KEY = 'treats.editorDraft'
REFS_KEY = 'treats.editorRefs'
TOOLS = [
    O(id='select', label='Select', key='V'),
    O(id='arrange', label='Move chunks', key='M'),
    O(id='rect', label='Rectangle', key='R'),
    O(id='g', label='Ground', key='1'),
    O(id='o', label='Cobblestone', key='O'),
    O(id='b', label='Dirt BG', key='B'),
    O(id='^', label='Spikes', key='2'),
    O(id='T', label='Trampoline', key='3'),
    O(id='~', label='Crumble', key='4'),
    O(id='treat', label='Treat', key='5'),
    O(id='greenie', label='Greenie', key='6'),
    O(id='diamond', label='Diamond', key='D'),
    O(id='tree', label='Tree', key='7'),
    O(id='cp', label='Checkpoint', key='8'),
    O(id='text', label='Text', key='9'),
    O(id='chicken', label='Chicken', key='C'),
    O(id='fire', label='Fireball', key='F'),
    O(id='cloud', label='Cloud', key='L'),
    O(id='note', label='Note', key='N'),
    O(id='erase', label='Eraser', key='0'),
]
NOTE_COLORS = ['255,196,0', '0,184,255', '255,90,200', '120,220,60', '255,120,40']
TILE_TOOLS = 'g^T~o'   # (Dirt BG paints the background layer instead)
# What the Rectangle tool fills with ('.' = empty: clears tiles and dirt background)
RECT_FILLS = [('g', 'Ground'), ('o', 'Cobblestone'), ('b', 'Dirt BG'), ('^', 'Spikes'), ('T', 'Trampoline'),
              ('~', 'Crumble'), ('.', 'Empty (clear)')]
TEXT_COLORS = ['#2b2f36', '#000000', '#ffffff', '#d63031', '#f39237', '#3f8f3a', '#1e6fd9', '#8e44ad']
KIND_LIST = dict(tree='trees', text='texts', treat='treats', greenie='greenies', cp='cps', chicken='chickens',
                 diamond='diamonds', fire='fires', cloud='clouds')
OBJ_LISTS = ['treats', 'greenies', 'cps', 'trees', 'texts', 'chickens', 'diamonds', 'fires', 'clouds']
REF_MARGIN = 6          # empty tiles around everything when other chunks are showing

# window layout
TOP, BOTTOM, SIDE = 48, 58, 250
UI = O(bg='#15181d', bar='#1f2329', side='#1b1f25', line='#2c313a', btn='#2d333d', btnHi='#38404b',
       edge='#3a404b', green='#3f8f3a', greenHi='#4ea347', onEdge='#6fcf5f', text='#e8eaed', dim='#9aa3ad',
       canvas='#0f1115', pink='#ff3d7f', blue='#9fdcf7', orange='#ffb27a')

# --- editor state --------------------------------------------------------
chunk = None
tool = 'g'
painting = 0            # 1 = left drag paints, 2 = right drag erases
lastCell = ''
hover = None
treeH, treeR = 5, 0
lastTextColor = '#2b2f36'
noteDrag = None         # { note, isNew, added } while painting a note
sel = []                # [{ kind, item }]: item is the object's list inside the chunk
selDrag = None
marquee = None
# Blocks in the selection are { kind: 'tile', item: [x, y, tile, bg] }. While they're being
# dragged they're lifted out of the chunk (lifted = True) and put back down on mouse up.
lifted = False
rectDrag = None         # Rectangle tool: { x0, y0, x1, y1 (tiles), erase } while dragging
rectFill = 'g'
# Other chunks from the game, shown around yours: [{ area, name, x, y }] in tiles from your top-left
refs = []
refDrag = None
view = O(ox=0, oy=0)    # where your chunk's top-left sits on the canvas, in tiles
Z = 0.75                # zoom
scroll = [0.0, 0.0]     # canvas scroll, screen pixels
pan = None              # middle-drag panning: (mouse x, y, scroll x, y)
statusMsg, statusT = '', 0.0
heightAtTop = True
nextFire = game.fireSettings({})
nextCloud = game.cloudSettings({})
cloudPathEdit = False
firePreview = True
cloudPreview = True
firePrev = {}           # id(spawner item) -> its running timer
lastFrame = 0.0
sideScroll, sideH = 0, 0
dialog = None           # the open dialog box (text, note, greenie name, confirm)
screen = ctx = None


def W():
    return screen.get_width()


def H():
    return screen.get_height()


def canvasRect():
    return pygame.Rect(SIDE, TOP, max(50, W() - SIDE), max(50, H() - TOP - BOTTOM))


def status(msg):
    global statusMsg, statusT
    statusMsg, statusT = msg, time.time() + 3


# --- chunk state -----------------------------------------------------------
def blankChunk(w=30):
    return O(name='My Chunk', w=w, h=LH,
             rows=[['g' if y >= G else '.'] * w for y in range(LH)],
             bg=[['.'] * w for _ in range(LH)],
             trees=[], treats=[], greenies=[], cps=[], texts=[], chickens=[], diamonds=[], fires=[], clouds=[], notes=[])


def toCode():
    c = O(chunk)
    c.rows = [''.join(r) for r in chunk.rows]
    c.bg = [''.join(r) for r in chunk.bg]
    c.place = O(a=refs[0].area, n=refs[0].name, x=-refs[0].x, y=-refs[0].y) if refs else None
    return game.encodeChunk(c)


def fromCode(code):
    c = game.decodeChunk(code)
    c.rows = [list(r) for r in c.rows]
    c.bg = [list(r) for r in c.bg]
    c.trees = [snapTree(t) for t in c.trees]
    return c


# A level from the game, as a new chunk to change: everything copied, but greenies and
# diamonds get new ids so collecting the copy's ones doesn't count as the original's.
def newId(p):
    n, s = int(time.time() * 1000), ''
    while n:
        n, d = divmod(n, 36)
        s = '0123456789abcdefghijklmnopqrstuvwxyz'[d] + s
    return p + s + ''.join(random.choice('0123456789abcdefghijklmnopqrstuvwxyz') for _ in range(4))


def copyOf(c):
    d = copy.deepcopy(dict(c))
    out = blankChunk(d['w'])
    out.update(d)
    out.name = (d['name'] + ' Copy')[:40]
    out.h = d.get('h') or LH
    out.place, out.notes = None, []
    out.rows = [list(r) for r in d['rows']]
    out.bg = [list(r) for r in (d.get('bg') or ['.' * len(r) for r in d['rows']])]
    out.trees = [snapTree(t) for t in d.get('trees') or []]
    out.greenies = [[x, y, name, newId('c')] for x, y, name, _ in d.get('greenies') or []]
    out.diamonds = [[x, y, newId('d')] for x, y, _ in d.get('diamonds') or []]
    for k in OBJ_LISTS + ['notes']:
        out[k] = out.get(k) or []
    return out


def treeOf(t):
    return game.makeTree(t[0] * T + T / 2, t[1] * T, t[2] * T, t[3] * math.pi / 180)


# Trees only point in the four right-angle directions. The trunk's base sits on the
# edge of its tile it grows out of: bottom for 0, left for 90, top for 180, right for 270.
def snapRot(r):
    return int(round(r / 90) * 90) % 360


def anchorFor(tx, ty, r):
    if r == 90:
        return [tx - 0.5, ty + 0.5]
    if r == 180:
        return [tx, ty]
    if r == 270:
        return [tx + 0.5, ty + 0.5]
    return [tx, ty + 1]


def cellOf(t):
    x, y, r = t[0], t[1], t[3]
    if r == 90:
        return [x + 0.5, y - 0.5]
    if r == 180:
        return [x, y]
    if r == 270:
        return [x - 0.5, y - 0.5]
    return [x, y - 1]


def snapTree(t):
    tx, ty = [round(v) for v in cellOf(t)]
    t[3] = snapRot(t[3])
    t[0], t[1] = anchorFor(tx, ty, t[3])
    return t


def save():
    store_set(DRAFT_KEY, toCode())


def resizeChunk(w):
    w = max(4, min(300, int(round(w or 4))))
    for y, row in enumerate(chunk.rows):
        del row[w:]
        row.extend(['g' if y >= G else '.'] * (w - len(row)))
    for row in chunk.bg:
        del row[w:]
        row.extend(['.'] * (w - len(row)))
    chunk.w = w
    for k in OBJ_LISTS:
        chunk[k] = [e for e in chunk[k] if e[0] < w]
    for n in chunk.notes:
        n[1] = [c for c in n[1] if c[0] < w]
    chunk.notes = [n for n in chunk.notes if n[1]]
    setSelection([])
    sizeCanvas()


# Taller or shorter. Rows are added / removed at the top (more sky; the ground stays put)
# or at the bottom (deeper; new rows copy the ground above them). Everything keeps its
# spot next to the ground, including the other chunks showing around yours.
def resizeHeight(h, atTop):
    h = max(4, min(200, int(round(h or 4))))
    d = h - chunk.h
    if not d:
        return
    w = chunk.w
    if atTop:
        if d > 0:
            chunk.rows[0:0] = [['.'] * w for _ in range(d)]
            chunk.bg[0:0] = [['.'] * w for _ in range(d)]
        else:
            del chunk.rows[0:-d]
            del chunk.bg[0:-d]
        for k in OBJ_LISTS:
            for o in chunk[k]:
                o[1] += d
        for n in chunk.notes:
            for c in n[1]:
                c[1] += d
        for r in refs:
            r.y += d
        saveRefs()
    elif d > 0:
        last = chunk.rows[-1]
        for _ in range(d):
            chunk.rows.append(['g' if c == 'g' else '.' for c in last])
            chunk.bg.append(['.'] * w)
    else:
        del chunk.rows[h:]
        del chunk.bg[h:]
    chunk.h = h
    for k in OBJ_LISTS:
        chunk[k] = [o for o in chunk[k] if 0 <= o[1] <= h]
    for n in chunk.notes:
        n[1] = [c for c in n[1] if 0 <= c[1] < h]
    chunk.notes = [n for n in chunk.notes if n[1]]
    setSelection([])
    sizeCanvas()


def setChunk(c):
    global chunk
    chunk = c
    for k in OBJ_LISTS + ['notes']:
        chunk[k] = chunk.get(k) or []
    setSelection([])
    sizeCanvas()


# --- objects (everything that isn't a tile) ------------------------------
def allObjects():
    return [O(kind=kind, item=item) for kind, k in KIND_LIST.items() for item in chunk[k]]


def boundsOf(o):   # in pixels
    kind, item = o.kind, o.item
    if kind == 'tile':
        return O(x=item[0] * T, y=item[1] * T, w=T, h=T)
    if kind == 'tree':
        return treeOf(item).box
    if kind == 'text':
        s = game.pixelTextSize(item[2])
        return O(x=item[0] * T, y=item[1] * T, w=s.w, h=s.h)
    if kind == 'cp':
        return O(x=item[0] * T, y=(item[1] - 2) * T, w=T, h=2 * T)
    if kind == 'cloud':
        return O(x=item[0] * T, y=item[1] * T, w=game.cloudSettings(item[2]).w * T, h=T)
    return O(x=item[0] * T, y=item[1] * T, w=T, h=T)


def hits(o, x, y, w, h):
    if o.kind == 'tree':
        return bool(game.trunkPush(x, y, w, h, treeOf(o.item)))
    b = boundsOf(o)
    return game.overlap(x, y, w, h, b.x, b.y, b.w, b.h)


# Topmost object under a point: small things first, then trees.
def objectAt(px, py):
    objs = allObjects()
    return next((o for o in objs if o.kind != 'tree' and hits(o, px - 2, py - 2, 4, 4)), None) or \
        next((o for o in objs if o.kind == 'tree' and hits(o, px - 3, py - 3, 6, 6)), None)


def removeObject(o):
    k = KIND_LIST[o.kind]
    chunk[k] = [i for i in chunk[k] if i is not o.item]


# --- selection --------------------------------------------------------------
def isSelected(item):
    return any(s.item is item for s in sel)


def tileSelected(x, y):
    return any(s.kind == 'tile' and s.item[0] == x and s.item[1] == y for s in sel)


# A block (or dirt background) at a cell, as a selection entry, or None if the cell is empty.
def tileEntry(tx, ty):
    if tx < 0 or ty < 0 or tx >= chunk.w or ty >= chunk.h:
        return None
    if chunk.rows[ty][tx] == '.' and chunk.bg[ty][tx] == '.':
        return None
    return O(kind='tile', item=[tx, ty, chunk.rows[ty][tx], chunk.bg[ty][tx]])


# Take the selected blocks out of the chunk (they move with the mouse), and put them back.
def liftTiles():
    global lifted
    if lifted:
        return
    for s in sel:
        if s.kind == 'tile':
            x, y = s.item[0], s.item[1]
            s.item[2], s.item[3] = chunk.rows[y][x], chunk.bg[y][x]
            chunk.rows[y][x] = chunk.bg[y][x] = '.'
    lifted = True


def dropTiles():
    global lifted
    if not lifted:
        return
    for s in sel:
        if s.kind == 'tile':
            x, y, c, b = s.item
            if c != '.':
                chunk.rows[y][x] = c
            if b == 'b':
                chunk.bg[y][x] = 'b'
    lifted = False


def setSelection(lst):
    global sel
    dropTiles()
    sel = lst


def selectedOf(kind):
    f = [o for o in sel if o.kind == kind]
    return f[0].item if len(f) == 1 else None


def deleteSelection():
    if not sel:
        return
    dropTiles()
    for s in sel:
        if s.kind == 'tile':
            chunk.rows[s.item[1]][s.item[0]] = chunk.bg[s.item[1]][s.item[0]] = '.'
        else:
            removeObject(s)
    setSelection([])
    save()


# Move the selection by whole tiles, but never off the edge of the chunk.
def moveSelection(dx, dy):
    def ok(ddx, ddy):
        for s in sel:
            x, y = s.item[0] + ddx, s.item[1] + ddy
            if s.kind == 'tile':
                if not (0 <= x < chunk.w and 0 <= y < chunk.h):
                    return False
            elif not (-0.5 <= x <= chunk.w - 0.5 and 0 <= y <= chunk.h):
                return False
        return True
    if not ok(dx, 0):
        dx = 0
    if not ok(dx, dy):
        dy = 0
    for s in sel:
        s.item[0] += dx
        s.item[1] += dy
    return dx, dy


# --- editing ------------------------------------------------------------------
# The eraser takes the front-most thing in the cell: tiles and objects first, and only
# once those are gone the dirt background behind them.
def eraseCell(tx, ty):
    hadTile = chunk.rows[ty][tx] != '.'
    chunk.rows[ty][tx] = '.'
    eraseNoteCell(tx, ty)
    cx, cy, s = tx * T + 1, ty * T + 1, T - 2
    gone = [o for o in allObjects() if hits(o, cx, cy, s, s)]
    if not hadTile and not gone:
        chunk.bg[ty][tx] = '.'
    if not gone:
        return
    for o in gone:
        removeObject(o)
    setSelection([o for o in sel if not any(g.item is o.item for g in gone)])


def eventPx(mx, my):
    r = canvasRect()
    return ((mx - r.x + scroll[0]) / Z - view.ox * T, (my - r.y + scroll[1]) / Z - view.oy * T)


def pxToCell(p):
    return (max(0, min(chunk.w - 1, math.floor(p[0] / T))), max(0, min(chunk.h - 1, math.floor(p[1] / T))))


def applyAt(mx, my, first):
    global lastCell, painting
    px, py = eventPx(mx, my)
    tx, ty = math.floor(px / T), math.floor(py / T)
    if tx < 0 or ty < 0 or tx >= chunk.w or ty >= chunk.h:
        return
    key = '%d,%d' % (tx, ty)
    if key == lastCell and not first:
        return
    lastCell = key

    def here(e):
        return e[0] == tx and e[1] == ty

    if painting == 2 and tool == 'note':
        eraseNoteCell(tx, ty)
        return
    if painting == 2 or tool == 'erase':
        eraseCell(tx, ty)
        return
    if tool == 'b':
        chunk.bg[ty][tx] = 'b'   # behind whatever tile is there
        return
    if tool in TILE_TOOLS:
        chunk.rows[ty][tx] = tool
        return
    if tool == 'note':
        paintNote(tx, ty, first)
        return
    if not first:
        return   # the rest are placed one per click

    if tool == 'treat':
        if not any(here(e) for e in chunk.treats):
            chunk.treats.append([tx, ty])
    elif tool == 'chicken':
        if not any(here(e) for e in chunk.chickens):
            chunk.chickens.append([tx, ty])
    elif tool == 'fire':
        # click a spawner to pick it (its settings show on the left), or empty space to place one
        hit = next((e for e in chunk.fires if here(e)), None)
        if hit:
            setSelection([O(kind='fire', item=hit)])
        else:
            item = [tx, ty, copy.deepcopy(dict(nextFire))]
            chunk.fires.append(item)
            setSelection([O(kind='fire', item=item)])
        save()
    elif tool == 'cloud':
        it = selectedOf('cloud')
        if it and cloudPathEdit:
            # drawing a path: each click is the next spot the cloud's middle passes through
            s = cloudTarget()
            s.pts.append([tx + 0.5 - (it[0] + s.w / 2), ty - it[1]])
            save()
            return
        # click a cloud to pick it, or empty space to put one there
        hit = next((c for c in chunk.clouds if hits(O(kind='cloud', item=c), px, py, 1, 1)), None)
        if hit:
            setSelection([O(kind='cloud', item=hit)])
        else:
            st = copy.deepcopy(dict(nextCloud))
            st['pts'] = []
            item = [tx, ty, st]
            chunk.clouds.append(item)
            setSelection([O(kind='cloud', item=item)])
        save()
    elif tool == 'diamond':
        # each diamond gets its own id so collecting it is remembered
        if not any(here(e) for e in chunk.diamonds):
            chunk.diamonds.append([tx, ty, newId('d')])
    elif tool == 'greenie':
        if any(here(e) for e in chunk.greenies):
            return
        painting = 0
        openDialog('greenie', 'Name this Greenie (it shows up when you collect it)', 'Mystery Greenie',
                   done=lambda name: (chunk.greenies.append([tx, ty, name.strip() or 'Mystery Greenie', newId('c')]), save()))
    elif tool == 'cp':
        if not any(c[0] == tx and c[1] == ty + 1 for c in chunk.cps):
            chunk.cps.append([tx, ty + 1])
    elif tool == 'tree':
        hit = objectAt(px, py)
        if hit and hit.kind == 'tree':
            setSelection([hit])
        else:
            item = anchorFor(tx, ty, treeR) + [treeH, treeR]
            chunk.trees.append(item)
            setSelection([O(kind='tree', item=item)])
    elif tool == 'text':
        painting = 0
        hit = objectAt(px, py)
        openTextDialog(hit.item if hit and hit.kind == 'text' else None, (tx, ty))


# --- select tool: click an object or a block to grab it, drag a box to grab several, then drag to move.
def selectDown(mx, my, shift):
    global selDrag, marquee
    p = eventPx(mx, my)
    tx, ty = math.floor(p[0] / T), math.floor(p[1] / T)
    # objects first, then a block that's already selected, then any block
    hit = objectAt(*p)
    if not hit:
        hit = next((s for s in sel if s.kind == 'tile' and s.item[0] == tx and s.item[1] == ty), None) or tileEntry(tx, ty)
    if hit:
        if hit not in sel and not isSelected(hit.item):
            setSelection(sel + [hit] if shift else [hit])
        selDrag = O(start=pxToCell(p), applied=[0, 0])
    else:
        if not shift:
            setSelection([])
        marquee = O(x0=p[0], y0=p[1], x1=p[0], y1=p[1])


def selectMove(mx, my):
    p = eventPx(mx, my)
    if selDrag:
        c = pxToCell(p)
        want = [c[0] - selDrag.start[0], c[1] - selDrag.start[1]]
        if want[0] or want[1]:
            liftTiles()
        dx, dy = moveSelection(want[0] - selDrag.applied[0], want[1] - selDrag.applied[1])
        selDrag.applied[0] += dx
        selDrag.applied[1] += dy
    elif marquee:
        marquee.x1, marquee.y1 = p


def selectUp():
    global marquee, selDrag
    if marquee:
        x, y = min(marquee.x0, marquee.x1), min(marquee.y0, marquee.y1)
        w, h = abs(marquee.x1 - marquee.x0), abs(marquee.y1 - marquee.y0)
        if w > 4 or h > 4:
            picked = [o for o in allObjects() if not isSelected(o.item) and hits(o, x, y, w, h)]
            # and every block the box touches
            for ty in range(max(0, math.floor(y / T)), min(chunk.h - 1, math.floor((y + h) / T)) + 1):
                for tx in range(max(0, math.floor(x / T)), min(chunk.w - 1, math.floor((x + w) / T)) + 1):
                    t = not tileSelected(tx, ty) and tileEntry(tx, ty)
                    if t:
                        picked.append(t)
            setSelection(sel + picked)
        marquee = None
    if selDrag:
        selDrag = None
        dropTiles()
        save()


# --- rectangle tool: drag a box, let go to fill it (right drag clears it) ---
def rectBox(r):
    return min(r.x0, r.x1), min(r.y0, r.y1), max(r.x0, r.x1), max(r.y0, r.y1)


def rectUp():
    global rectDrag
    x0, y0, x1, y1 = rectBox(rectDrag)
    fill = '.' if rectDrag.erase else rectFill
    rectDrag = None
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            if fill == 'b':
                chunk.bg[y][x] = 'b'
            elif fill == '.':
                chunk.rows[y][x] = chunk.bg[y][x] = '.'
            else:
                chunk.rows[y][x] = fill
    save()


# --- tree buttons edit the selected tree (or the next one you plant) ---
def setTree(h, r):
    global treeH, treeR
    treeH = max(1, min(14, h))
    treeR = snapRot(r)
    t = selectedOf('tree')
    if t:
        # re-anchor so the tree turns in place on its tile
        tx, ty = [round(v) for v in cellOf(t)]
        t[0], t[1] = anchorFor(tx, ty, treeR)
        t[2], t[3] = treeH, treeR
        save()


def syncTree():
    global treeH, treeR
    t = selectedOf('tree')
    if t:
        treeH, treeR = t[2], t[3]


# --- text: click to place, then type. Lines only break where you press Enter.
def openTextDialog(item, cell):
    me = []   # this dialog (it's closed by the time done runs)

    def done(s):
        global lastTextColor
        s = s.rstrip()
        col = me[0].color
        if item:
            if s:
                item[2], item[3] = s, col
            else:
                removeObject(O(kind='text', item=item))
                setSelection([o for o in sel if o.item is not item])
        elif s:
            chunk.texts.append([cell[0], cell[1], s, col])
        lastTextColor = col
        save()

    def delete():
        removeObject(O(kind='text', item=item))
        setSelection([o for o in sel if o.item is not item])
        save()
    openDialog('text', 'Text', item[2] if item else '', done=done, multiline=True,
               delete=delete if item else None, color=item[3] if item else lastTextColor)
    me.append(dialog)


# --- notes: paint an area, then describe what should go there. They never show up in
# the game; whoever adds the chunk to world.py builds what the note asks for in its place.
def noteAt(tx, ty):
    return next((n for n in chunk.notes if any(c[0] == tx and c[1] == ty for c in n[1])), None)


def paintNote(tx, ty, first):
    global noteDrag
    if first:
        # start on an existing note to add tiles to it (or just click it to edit it), anywhere else to start a new one
        n = noteAt(tx, ty)
        if n:
            noteDrag = O(note=n, isNew=False, added=False)
            return
        note = ['', [[tx, ty]]]
        chunk.notes.append(note)
        noteDrag = O(note=note, isNew=True, added=True)
        return
    if not noteDrag or noteAt(tx, ty):
        return
    noteDrag.note[1].append([tx, ty])
    noteDrag.added = True


def finishNoteDrag():
    global noteDrag
    d, noteDrag = noteDrag, None
    if d.isNew or not d.added:
        openNoteDialog(d.note, d.isNew)
    else:
        save()


def eraseNoteCell(tx, ty):
    for n in chunk.notes:
        n[1] = [c for c in n[1] if c[0] != tx or c[1] != ty]
    chunk.notes = [n for n in chunk.notes if n[1]]


def openNoteDialog(note, isNew):
    def done(s):
        note[0] = s.strip()
        # a note with no description isn't worth keeping
        if not note[0]:
            chunk.notes = [n for n in chunk.notes if n is not note]
        save()

    def cancel():
        if isNew:
            chunk.notes = [n for n in chunk.notes if n is not note]

    def delete():
        chunk.notes = [n for n in chunk.notes if n is not note]
        save()
    openDialog('note', 'Note: describe what should go in this area', note[0], done=done, multiline=True,
               cancel=cancel, delete=None if isNew else delete)


# --- fireball spawners and clouds: settings panels ----------------------------------
FIRE_FIELDS = [
    O(k='every', label='Shoots every (seconds)', range=True, step=0.1, min=0.05),
    O(k='delay', label='First shot after (seconds)', step=0.1, min=0),
    O(k='mode', label='Path', options=[('straight', 'Straight line'), ('orbit', 'Circles around the spawner'), ('spiral', 'Spirals out of the spawner')]),
    O(k='angle', label='Direction (deg)', range=True, step=5, hint='0 right, 90 down, 180 left, 270 up. 0 to 360 = any way'),
    O(k='speed', label='Speed (tiles / second)', range=True, step=0.5, min=0, modes=['straight']),
    O(k='radius', label='Circle radius (tiles)', range=True, step=0.5, min=0, modes=['orbit']),
    O(k='spacing', label='Spiral amplitude (tiles per loop)', range=True, step=0.5, min=0, modes=['spiral']),
    O(k='spin', label='Spin speed (deg / second)', range=True, step=10, hint='negative spins the other way', modes=['orbit', 'spiral']),
    O(k='offX', label='Random X offset (tiles)', range=True, step=0.5),
    O(k='offY', label='Random Y offset (tiles)', range=True, step=0.5),
    O(k='size', label='Size (pixels)', range=True, step=1, min=2),
    O(k='life', label='Burns out after (seconds)', step=0.5, min=0, hint='0 = until it hits a block or leaves'),
    O(k='max', label='Most out at once', step=1, min=1),
    O(k='ghost', label='Flies through blocks', bool=True),
]
MOVING = ['lr', 'ud', 'ellipse', 'path']
CLOUD_FIELDS = [
    O(k='w', label='Width (tiles)', step=0.5, min=1),
    O(k='scale', label='Puff size', step=0.1, min=0.3, max=3, hint='1 = normal'),
    O(k='mode', label='Moves', options=[('still', 'Stays put'), ('lr', 'Left and right'), ('ud', 'Up and down'), ('ellipse', 'Round an ellipse'), ('path', 'Along a path you draw')]),
    O(k='dist', label='Distance (tiles)', step=1, hint='negative goes left / up first', modes=['lr', 'ud']),
    O(k='rx', label='Ellipse width, centre to side (tiles)', step=0.5, min=0, modes=['ellipse']),
    O(k='ry', label='Ellipse height, centre to top (tiles)', step=0.5, min=0, modes=['ellipse']),
    O(k='ccw', label='Anticlockwise', bool=True, modes=['ellipse']),
    O(k='loop', label='Loop back to the first point (off = back and forth)', bool=True, modes=['path']),
    O(k='speed', label='Speed (tiles / second)', step=0.5, min=0, modes=MOVING),
    O(k='start', label='Starts this far along (%)', step=5, min=0, max=100, hint='so clouds next to each other can be out of step', modes=MOVING),
]


# Settings being edited: the picked spawner's / cloud's, or the ones the next one gets.
def fireTarget():
    it = selectedOf('fire')
    if it:
        it[2] = game.fireSettings(it[2])
        return it[2]
    return nextFire


def cloudTarget():
    it = selectedOf('cloud')
    if it:
        it[2] = game.cloudSettings(it[2])
        return it[2]
    return nextCloud


# --- play the chunk in the game (a separate window) ---------------------------
def startPlay():
    save()
    path = os.path.join(tempfile.gettempdir(), 'treats_editor_test.txt')
    with open(path, 'w', encoding='utf8') as f:
        f.write(toCode())
    try:
        subprocess.Popen([sys.executable, os.path.join(HERE, 'main.py'), '--test', '@' + path], cwd=HERE)
        status('Playing "%s" in a new window. R respawns, Enter restarts.' % chunk.name)
    except Exception as e:
        status('Could not start the game: %s' % e)


def setTool(t):
    global tool, cloudPathEdit
    tool = t
    if t != 'cloud':
        cloudPathEdit = False


# --- canvas size -------------------------------------------------------------
def contentSize():
    x0, y0, x1, y1 = 0, 0, chunk.w, chunk.h
    for r in refs:
        c = refChunk(r)
        if c:
            x0, y0, x1, y1 = min(x0, r.x), min(y0, r.y), max(x1, r.x + c.w), max(y1, r.y + c.h)
    m = REF_MARGIN if refs else 0
    return m - x0, m - y0, (x1 - x0 + 2 * m) * T * Z, (y1 - y0 + 2 * m) * T * Z


def clampScroll():
    _, _, w, h = contentSize()
    r = canvasRect()
    scroll[0] = max(0, min(scroll[0], w - r.w + 40))
    scroll[1] = max(0, min(scroll[1], h - r.h + 40))


def sizeCanvas():
    ox, oy, _, _ = contentSize()
    # keep your chunk in the same place on screen when the canvas grows or shrinks on the left / top
    scroll[0] += (ox - view.ox) * T * Z
    scroll[1] += (oy - view.oy) * T * Z
    view.ox, view.oy = ox, oy
    clampScroll()


def setZoom(z, mx=None, my=None):
    global Z
    r = canvasRect()
    if mx is None:
        mx, my = r.centerx, r.centery
    # keep the spot under the mouse where it is
    wx, wy = (mx - r.x + scroll[0]) / Z, (my - r.y + scroll[1]) / Z
    Z = max(0.25, min(2.0, z))
    scroll[0], scroll[1] = wx * Z - (mx - r.x), wy * Z - (my - r.y)
    clampScroll()


def scrollTo(tx, ty):
    scroll[0] = max(0, (view.ox + tx) * T * Z - 40)
    scroll[1] = max(0, (view.oy + ty) * T * Z - 40)
    clampScroll()


# --- other chunks from the game ------------------------------------------------
def refChunk(r):
    s = next((o for o in game.AREAS.get(r.area, []) if o.chunk and o.name == r.name), None)
    return s.chunk if s else None


def saveRefs():
    store_set(REFS_KEY, [dict(r) for r in refs])


def addRef(area, name, at=None):
    c = refChunk(O(area=area, name=name))
    if not c:
        return
    # goes to the right of everything already showing, unless a spot is given
    x = chunk.w
    for r in refs:
        rc = refChunk(r)
        if rc:
            x = max(x, r.x + rc.w)
    refs.append(O(area=area, name=name, x=at[0] if at else x, y=at[1] if at else 0))
    saveRefs()
    sizeCanvas()


# Generate world: every chunk of the main world shown around yours, where it really is in
# the game. Yours goes where its code says (or where a chunk with its name already is), else
# past the right end of the world. The first one listed is the one your spot is saved from.
def generateWorld():
    global refs
    order = game.AREAS.get('Main') or []
    pos = game.layoutSections(order)
    others = [s for s in order if s.chunk and s.name != chunk.name]
    if not others:
        status('The main world has no chunks yet.')
        return
    same = next((s for s in order if s.chunk and s.name == chunk.name), None)
    p = chunk.place
    anchor = next((s for s in others if s.name == p.n), None) if p and p.a == 'Main' else None
    first = anchor
    if same:
        me = pos[id(same)]
    elif anchor:
        me = [pos[id(anchor)][0] + p.x, pos[id(anchor)][1] + p.y]
    else:
        # past the right end of everything, ground lined up with the main row (no overlaps)
        first = max(others, key=lambda s: pos[id(s)][0] + s.w)
        me = [pos[id(first)][0] + first.w, LH - chunk.h]
    first = first or others[0]
    refs = [O(area='Main', name=s.name, x=pos[id(s)][0] - me[0], y=pos[id(s)][1] - me[1])
            for s in [first] + [s for s in others if s is not first]]
    saveRefs()
    sizeCanvas()
    scrollTo(-8, -8)
    status('Showing all %d chunks of the main world around yours.' % len(others))


def refAt(px, py):
    for r in reversed(refs):
        c = refChunk(r)
        if c and r.x * T <= px < (r.x + c.w) * T and r.y * T <= py < (r.y + c.h) * T:
            return r
    return None


def gameChunks():
    return [(area, s.name) for area in game.AREAS for s in game.AREAS[area] if s.chunk]


# =====================================================================
#  Drawing the canvas
# =====================================================================
def visibleTiles(rx, ry, w, h):
    """The tile range of a chunk at (rx, ry) tiles from yours that's scrolled into view."""
    r = canvasRect()
    vx = scroll[0] / Z / T - view.ox - rx
    vy = scroll[1] / Z / T - view.oy - ry
    return (max(0, math.floor(vx) - 1), min(w - 1, math.ceil(vx + r.w / Z / T) + 1),
            max(0, math.floor(vy) - 1), min(h - 1, math.ceil(vy + r.h / Z / T) + 1))


def drawSky(w, h):
    # the game's sky: light at the top, lighter at the bottom (in bands)
    a, b = color(game.COL.skyTop), color(game.COL.skyBot)
    n = 12
    for i in range(n):
        k = i / (n - 1)
        ctx.fillStyle = '#%02x%02x%02x' % tuple(int(a[j] + (b[j] - a[j]) * k) for j in range(3))
        ctx.fillRect(0, h * i / n, w, h / n + 1)


def pointGameAt(c, rows, bg):
    """Point the game's drawing code at a chunk (its objects as the game keeps them)."""
    game.grid, game.bgGrid, game.LW, game.GH = rows, bg, c.w, c.h
    game.treats = [O(x=x * T + T / 2, y=y * T + T / 2, taken=False) for x, y in c.treats]
    game.greenies = [O(x=x * T + T / 2, y=y * T + T / 2, name=name, id=id, taken=False) for x, y, name, id in c.greenies]
    game.checkpoints = [O(x=x * T + T / 2, y=y * T, active=False) for x, y in c.cps]
    game.diamonds = [O(x=x * T + T / 2, y=y * T + T / 2, id=id, taken=False) for x, y, id in c.diamonds or []]
    chickens = []
    for x, y in c.chickens or []:
        ck = game.makeChicken(x * T + T / 2, (y + 1) * T)
        ck.phase = game.simTime + x
        chickens.append(ck)
    game.chickens = chickens


def drawObjects(c, x0, x1, y0, y1):
    # (only what's near the visible tiles: trees and leaves reach a few tiles past their spot)
    def near(x, y, m=3):
        return x0 - m <= x <= x1 + m and y0 - m - 14 <= y <= y1 + m + 14
    game.treats = [o for o in game.treats if near(o.x / T, o.y / T)]
    game.greenies = [o for o in game.greenies if near(o.x / T, o.y / T)]
    game.chickens = [o for o in game.chickens if near(o.x / T, o.y / T)]
    game.drawBackTiles(x0, x1, y0, y1)
    game.drawCheckpoints()
    game.drawTiles(x0, x1, y0, y1)
    for t in c.trees:
        if near(t[0], t[1], 16):
            game.drawTree(treeOf(t))
    for x, y, s, col in c.texts:
        game.drawPixelText(s, x * T, y * T, col)
    game.drawTreats()
    game.drawGreenies()
    game.drawDiamonds()
    game.drawChickens(False)


def drawRef(r):
    c = refChunk(r)
    if not c:
        return
    x0, x1, y0, y1 = visibleTiles(r.x, r.y, c.w, c.h)
    if x0 > x1 or y0 > y1:
        return
    ctx.save()
    ctx.translate(r.x * T, r.y * T)
    sparks = len(game.particles)   # its greenie sparkles would land on your chunk: drop them
    pointGameAt(c, c.rows, c.bg)
    drawSky(c.w * T, c.h * T)
    drawObjects(c, x0, x1, y0, y1)
    ctx.fillStyle = 'rgba(15,17,21,0.35)'
    ctx.fillRect(0, 0, c.w * T, c.h * T)   # dimmed, so your chunk stands out
    del game.particles[sparks:]
    ctx.restore()


def outline(cells, rgb, alpha, width=3):
    """Tint cells and outline only the outside edges of the area."""
    mine = set((x, y) for x, y in cells)
    ctx.fillStyle = 'rgba(%s,%s)' % (rgb, alpha)
    for x, y in cells:
        ctx.fillRect(x * T, y * T, T, T)
    ctx.strokeStyle = 'rgba(%s,0.95)' % rgb
    ctx.lineWidth = width
    ctx.beginPath()
    for x, y in cells:
        if (x, y - 1) not in mine:
            ctx.moveTo(x * T, y * T); ctx.lineTo(x * T + T, y * T)
        if (x, y + 1) not in mine:
            ctx.moveTo(x * T, y * T + T); ctx.lineTo(x * T + T, y * T + T)
        if (x - 1, y) not in mine:
            ctx.moveTo(x * T, y * T); ctx.lineTo(x * T, y * T + T)
        if (x + 1, y) not in mine:
            ctx.moveTo(x * T + T, y * T); ctx.lineTo(x * T + T, y * T + T)
    ctx.stroke()


def drawNotes():
    for i, (text, cells) in enumerate(chunk.notes):
        rgb = NOTE_COLORS[i % len(NOTE_COLORS)]
        outline(cells, rgb, 0.28)
        # label on the top-left tile
        lx, ly = min(cells, key=lambda c: (c[1], c[0]))
        first = (text or '(no description yet)').split('\n')[0]
        label = 'NOTE: ' + (first[:40] + '...' if len(first) > 40 else first)
        ctx.font = font(700, 13)
        ctx.textAlign = 'left'; ctx.textBaseline = 'middle'
        w = ctx.measureText(label) + 10
        ctx.fillStyle = 'rgba(%s,0.95)' % rgb
        ctx.fillRect(lx * T, ly * T - 20, w, 20)
        ctx.fillStyle = '#15181d'
        ctx.fillText(label, lx * T + 5, ly * T - 10)


# In the editor a spawner is a dashed orange box with a flame; its path is sketched in.
def drawFireMarkers():
    for it in chunk.fires:
        s = game.fireSettings(it[2])
        x, y = it[0] * T + T / 2, it[1] * T + T / 2
        ctx.strokeStyle = '#ff7a1a'; ctx.lineWidth = 2; ctx.setLineDash([4, 3])
        ctx.strokeRect(it[0] * T + 2, it[1] * T + 2, T - 4, T - 4)
        if s.mode == 'orbit':
            r = (s.radius[0] + s.radius[1]) / 2 * T
            ctx.strokeStyle = 'rgba(255,122,26,0.5)'
            ctx.beginPath(); ctx.arc(x, y, r, 0, math.pi * 2); ctx.stroke()
        ctx.setLineDash([])
        if s.mode == 'straight':   # which way it shoots
            ctx.strokeStyle = 'rgba(255,122,26,0.8)'; ctx.lineWidth = 2
            for a in set(s.angle):
                r = a * math.pi / 180
                ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + math.cos(r) * 26, y + math.sin(r) * 26); ctx.stroke()
        ctx.fillStyle = '#ff7a1a'; ctx.beginPath(); ctx.arc(x, y, 8, 0, math.pi * 2); ctx.fill()
        ctx.fillStyle = '#ffd23f'; ctx.beginPath(); ctx.arc(x, y + 2, 4.5, 0, math.pi * 2); ctx.fill()


# Live preview: the game's own fireball code, run on the chunk you're editing.
def previewFire(dt):
    if not firePreview:
        game.fireballs = []
        firePrev.clear()
        return
    alive = set(id(it) for it in chunk.fires)
    for k in list(firePrev):
        if k not in alive:
            del firePrev[k]
    sps = []
    for it in chunk.fires:
        st = game.fireSettings(it[2])
        sp = firePrev.get(id(it))
        if not sp:
            sp = firePrev[id(it)] = O(t=st.delay, alive=0)
        sp.x, sp.y, sp.s = it[0] * T + T / 2, it[1] * T + T / 2, st
        sps.append(sp)
    game.fireSpawners = sps
    game.fireballs = [f for f in game.fireballs if any(f.sp is s for s in sps)]
    game.updateFire(dt, True)


# Each cloud: a dashed box where it lives, its path in light blue, and the cloud itself
# gliding along (or sitting at its start when the preview is off).
def drawClouds():
    for it in chunk.clouds:
        s = game.cloudSettings(it[2])
        hx, hy, w = it[0] * T, it[1] * T, s.w * T
        m = game.makeCloud(hx, hy, s)

        def mid(p):
            return p[0] + w / 2, p[1] + T / 2
        ctx.strokeStyle = 'rgba(79,195,247,0.85)'; ctx.lineWidth = 2; ctx.setLineDash([6, 5])
        if len(m.pts) > 1:
            ctx.beginPath()
            for i, p in enumerate(m.pts):
                (ctx.lineTo if i else ctx.moveTo)(*mid(p))
            if m.loop:
                ctx.closePath()
            ctx.stroke()
        ctx.strokeRect(hx, hy, w, T)
        ctx.setLineDash([])
        if s.mode == 'path':
            ctx.font = font(700, 11); ctx.textAlign = 'center'; ctx.textBaseline = 'middle'
            for i, p in enumerate(m.pts[1:]):
                x, y = mid(p)
                ctx.fillStyle = '#4fc3f7'; ctx.beginPath(); ctx.arc(x, y, 8, 0, math.pi * 2); ctx.fill()
                ctx.fillStyle = '#15181d'; ctx.fillText(str(i + 1), x, y)
        x, y = game.cloudAt(m, (game.simTime * m.speed if cloudPreview else 0) + m.s0)
        game.drawCloud(x, y, m.w, m.scale)


def drawCanvas(now):
    global lastFrame
    dt = min(0.05, now - lastFrame) if lastFrame else 0
    lastFrame = now
    game.simTime = now
    game.updateParticles(dt)   # fireball sparks
    cr = canvasRect()
    screen.set_clip(cr)
    ctx.clip_r = cr
    screen.fill(color(UI.canvas)[:3], cr)
    ctx.setTransform(Z, 0, 0, Z, cr.x - scroll[0] + view.ox * T * Z, cr.y - scroll[1] + view.oy * T * Z)
    for r in refs:
        drawRef(r)

    # the chunk being edited
    W_, H_ = chunk.w * T, chunk.h * T
    gy = (chunk.h - (LH - G)) * T   # where the neighbours' ground is
    pointGameAt(chunk, chunk.rows, chunk.bg)
    drawSky(W_, H_)
    x0, x1, y0, y1 = visibleTiles(0, 0, chunk.w, chunk.h)
    # grid
    if Z >= 0.4:
        ctx.fillStyle = '#d5dbe2'   # (solid: see-through lines cost a picture each)
        for x in range(x0, x1 + 2):
            ctx.fillRect(x * T, y0 * T, 1 / Z, (y1 - y0 + 1) * T)
        for y in range(y0, y1 + 2):
            ctx.fillRect(x0 * T, y * T, (x1 - x0 + 1) * T, 1 / Z)
    if x0 <= x1 and y0 <= y1:
        drawObjects(chunk, x0, x1, y0, y1)
    drawClouds()
    previewFire(dt)
    game.drawFireballs()
    game.drawParticles()
    drawFireMarkers()
    drawNotes()

    # where the neighbouring sections' ground is
    ctx.setLineDash([10, 8]); ctx.strokeStyle = 'rgba(214,48,49,0.7)'; ctx.lineWidth = 2
    ctx.beginPath(); ctx.moveTo(0, gy); ctx.lineTo(W_, gy); ctx.stroke()
    ctx.setLineDash([])
    ctx.fillStyle = 'rgba(214,48,49,0.85)'; ctx.font = font(700, 13)
    ctx.textAlign = 'left'; ctx.textBaseline = 'bottom'
    ctx.fillText("< neighbours' ground level", 6, gy - 4)
    ctx.textAlign = 'right'
    ctx.fillText("neighbours' ground level >", W_ - 6, gy - 4)

    # blocks being dragged, then the selected blocks tinted with an outline round the outside
    tiles = [o for o in sel if o.kind == 'tile']
    if lifted:
        for o in tiles:
            x, y, c, b = o.item
            if b == 'b':
                ctx.fillStyle = game.COL.dirtBg; ctx.fillRect(x * T, y * T, T, T)
            if c != '.':
                game.drawTile(c, x * T, y * T)
    if tiles:
        outline([o.item[:2] for o in tiles], '255,61,127', 0.18, 2)
    # the rectangle being dragged, see-through, with its size
    if rectDrag:
        rx0, ry0, rx1, ry1 = rectBox(rectDrag)
        fill = '.' if rectDrag.erase else rectFill
        ctx.globalAlpha = 0.6
        for y in range(ry0, ry1 + 1):
            for x in range(rx0, rx1 + 1):
                if fill == 'b':
                    ctx.fillStyle = game.COL.dirtBg; ctx.fillRect(x * T, y * T, T, T)
                elif fill != '.':
                    game.drawTile(fill, x * T, y * T)
        ctx.globalAlpha = 1
        ctx.strokeStyle = '#d63031' if fill == '.' else UI.pink; ctx.lineWidth = 3
        ctx.strokeRect(rx0 * T, ry0 * T, (rx1 - rx0 + 1) * T, (ry1 - ry0 + 1) * T)
        ctx.fillStyle = ctx.strokeStyle; ctx.font = font(700, 13); ctx.textAlign = 'left'; ctx.textBaseline = 'bottom'
        ctx.fillText('%d x %d' % (rx1 - rx0 + 1, ry1 - ry0 + 1), rx0 * T + 2, ry0 * T - 4)

    # selection outlines
    ctx.strokeStyle = UI.pink; ctx.lineWidth = 2; ctx.setLineDash([6, 4])
    for o in sel:
        if o.kind == 'tile':
            continue
        if o.kind == 'tree':
            tr = treeOf(o.item)
            ctx.beginPath()
            for j, (x, y) in enumerate(tr.poly):
                (ctx.lineTo if j else ctx.moveTo)(x, y)
            ctx.closePath(); ctx.stroke()
        else:
            b = boundsOf(o)
            ctx.strokeRect(b.x - 3, b.y - 3, b.w + 6, b.h + 6)
    ctx.setLineDash([])
    if marquee:
        x, y = min(marquee.x0, marquee.x1), min(marquee.y0, marquee.y1)
        w, h = abs(marquee.x1 - marquee.x0), abs(marquee.y1 - marquee.y0)
        ctx.fillStyle = 'rgba(255,61,127,0.10)'; ctx.fillRect(x, y, w, h)
        ctx.strokeRect(x, y, w, h)

    # outlines + names of the other chunks, on top so overlaps show
    ctx.font = font(700, 14); ctx.textAlign = 'left'; ctx.textBaseline = 'bottom'
    for r in refs:
        c = refChunk(r)
        if not c:
            continue
        on = bool(refDrag) and refDrag.ref is r
        ctx.strokeStyle = '#ffd166' if on else '#4fc3f7'; ctx.lineWidth = 3; ctx.setLineDash([12, 8])
        ctx.strokeRect(r.x * T, r.y * T, c.w * T, c.h * T)
        ctx.setLineDash([])
        ctx.fillStyle = ctx.strokeStyle
        ctx.fillText(r.area + ' / ' + r.name, r.x * T + 4, r.y * T - 4)
    if refs:
        ctx.strokeStyle = '#ffd166' if refDrag and refDrag.ref == 'me' else UI.pink
        ctx.lineWidth = 3; ctx.strokeRect(0, 0, W_, H_)
        ctx.fillStyle = ctx.strokeStyle; ctx.fillText(chunk.name + ' (yours)', 4, -4)

    # hover preview
    if hover and tool not in ('select', 'arrange') and not rectDrag and 0 <= hover[0] < chunk.w and 0 <= hover[1] < chunk.h:
        tx, ty = hover
        free = not objectAt(tx * T + T / 2, ty * T + T / 2)
        if tool == 'tree' and free:
            ctx.globalAlpha = 0.4; game.drawTree(treeOf(anchorFor(tx, ty, treeR) + [treeH, treeR])); ctx.globalAlpha = 1
        if tool == 'cloud' and not cloudPathEdit and free:
            ctx.globalAlpha = 0.4; game.drawCloud(tx * T, ty * T, nextCloud.w * T, nextCloud.scale); ctx.globalAlpha = 1
        ctx.strokeStyle = '#d63031' if tool == 'erase' else UI.pink; ctx.lineWidth = 2
        ctx.strokeRect(tx * T + 1, ty * T + 1, T - 2, T - 2)
    ctx.resetTransform()
    ctx.clip_r = None
    screen.set_clip(None)


# =====================================================================
#  A small immediate-mode UI: widgets are drawn every frame and register
#  where they can be clicked; clicks are matched against last frame's list.
# =====================================================================
hitList = []            # [(rect, callback)] in drawing order (later = on top)
focus = None            # O(id, buf, commit, live, numeric) for the text field being typed in
dropOpen = None         # O(id, rect, options, cb) for an open drop-down list
clipNow = None          # widgets outside this rect can't be clicked (the scrolled sidebar)
mouse = (0, 0)


def txt(s, x, y, col=None, size=14, weight=400, align='left', valign='top', maxw=None):
    f = font(weight, size)
    s = str(s)
    if maxw:
        while s and f.size(s)[0] > maxw:
            s = s[:-2] + '…' if len(s) > 2 else ''
    surf = f.render(s, True, color(col or UI.text)[:3])
    if align == 'center':
        x -= surf.get_width() / 2
    elif align == 'right':
        x -= surf.get_width()
    if valign == 'middle':
        y -= surf.get_height() / 2
    screen.blit(surf, (int(x), int(y)))
    return surf.get_width()


def wrap(s, w, size=13):
    f = font(400, size)
    out = []
    for para in s.split('\n'):
        line = ''
        for word in para.split(' '):
            t = (line + ' ' + word).strip()
            if f.size(t)[0] > w and line:
                out.append(line)
                line = word
            else:
                line = t
        out.append(line)
    return out


def addHit(r, cb):
    rr = r.clip(clipNow) if clipNow else r
    if rr.w > 0 and rr.h > 0:
        hitList.append((rr, cb))


def box(r, fill, edge=None, radius=6):
    pygame.draw.rect(screen, color(fill)[:3], r, border_radius=radius)
    if edge:
        pygame.draw.rect(screen, color(edge)[:3], r, 1, border_radius=radius)


def button(r, label, cb, on=False, primary=False, disabled=False, key=None, size=14):
    r = pygame.Rect(r)
    hot = r.collidepoint(mouse) and not disabled and (not clipNow or clipNow.collidepoint(mouse))
    fill = UI.green if on or primary else UI.btn
    if hot:
        fill = UI.greenHi if on or primary else UI.btnHi
    box(r, fill, UI.onEdge if on else ('#4ea347' if primary else UI.edge))
    col = '#6b727c' if disabled else UI.text
    txt(label, r.x + 8 if key else r.centerx, r.centery, col, size, align='left' if key else 'center', valign='middle',
        maxw=r.w - (26 if key else 10))
    if key:
        txt(key, r.right - 6, r.centery, '#7b838d', 11, align='right', valign='middle')
    if not disabled:
        addHit(r, cb)


def fmt(v):
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return str(v)


def commitFocus():
    global focus
    f, focus = focus, None
    if f and not f.live:
        f.commit(f.buf)


def field(fid, r, value, commit, numeric=False, live=False):
    global focus
    r = pygame.Rect(r)
    on = focus and focus.id == fid
    if on:
        focus.commit, focus.live = commit, live   # (the latest closure, in case things changed)
    box(r, '#15181d', UI.pink if on else UI.edge)
    s = focus.buf if on else fmt(value)
    f = font(400, 14)
    while s and f.size(s)[0] > r.w - 14:
        s = s[1:]
    w = txt(s, r.x + 7, r.centery, UI.text, 14, valign='middle')
    if on and int(time.time() * 2) % 2 == 0:
        pygame.draw.line(screen, color(UI.text)[:3], (r.x + 8 + w, r.y + 5), (r.x + 8 + w, r.bottom - 6))

    def click():
        global focus
        if focus and focus.id == fid:
            return
        commitFocus()
        focus = O(id=fid, buf=fmt(value), commit=commit, live=live, numeric=numeric)
    addHit(r, click)


def numCommit(set_, lo=None, hi=None):
    def commit(s):
        try:
            v = float(s)
        except ValueError:
            return
        if lo is not None:
            v = max(lo, v)
        if hi is not None:
            v = min(hi, v)
        set_(int(v) if v.is_integer() else v)
    return commit


def checkbox(r, label, value, cb):
    r = pygame.Rect(r)
    b = pygame.Rect(r.x, r.y + 2, 16, 16)
    box(b, UI.green if value else '#15181d', UI.edge, 3)
    if value:
        pygame.draw.lines(screen, (255, 255, 255), False, [(b.x + 3, b.y + 8), (b.x + 7, b.y + 12), (b.x + 13, b.y + 4)], 2)
    lines = wrap(label, r.w - 24, 13)
    for i, line in enumerate(lines):
        txt(line, r.x + 24, r.y + 2 + i * 16, '#c8ced6', 13)
    addHit(pygame.Rect(r.x, r.y, r.w, max(20, len(lines) * 16 + 4)), lambda: cb(not value))
    return max(20, len(lines) * 16 + 4)


def dropdown(fid, r, options, value, cb):
    global dropOpen
    r = pygame.Rect(r)
    label = next((l for v, l in options if v == value), str(value) if value is not None else '')
    box(r, '#15181d', UI.edge)
    txt(label, r.x + 7, r.centery, UI.text, 13, valign='middle', maxw=r.w - 26)
    pygame.draw.polygon(screen, color(UI.dim)[:3], [(r.right - 16, r.centery - 2), (r.right - 8, r.centery - 2), (r.right - 12, r.centery + 3)])

    def click():
        global dropOpen
        commitFocus()
        dropOpen = O(id=fid, rect=r.copy(), options=options, cb=cb)
    addHit(r, click)


def drawDropList():
    if not dropOpen:
        return
    r, opts = dropOpen.rect, dropOpen.options
    ih = 24
    w = max(r.w, max((font(400, 13).size(l)[0] + 20 for _, l in opts), default=r.w))
    h = ih * len(opts)
    x = min(r.x, W() - w - 4)
    y = r.bottom + 2 if r.bottom + 2 + h < H() else max(2, r.y - 2 - h)
    box(pygame.Rect(x, y, w, h), '#22262d', UI.edge)
    for i, (v, l) in enumerate(opts):
        ir = pygame.Rect(x + 1, y + i * ih, w - 2, ih)
        if ir.collidepoint(mouse):
            pygame.draw.rect(screen, color(UI.btnHi)[:3], ir)
        txt(l, ir.x + 8, ir.centery, UI.text, 13, valign='middle')


def clickDropList(mx, my):
    global dropOpen
    r, opts = dropOpen.rect, dropOpen.options
    ih = 24
    w = max(r.w, max((font(400, 13).size(l)[0] + 20 for _, l in opts), default=r.w))
    h = ih * len(opts)
    x = min(r.x, W() - w - 4)
    y = r.bottom + 2 if r.bottom + 2 + h < H() else max(2, r.y - 2 - h)
    d, dropOpen = dropOpen, None
    if x <= mx < x + w and y <= my < y + h:
        d.cb(d.options[int((my - y) // ih)][0])


# --- dialogs ---------------------------------------------------------------------
def openDialog(kind, title, text, done, multiline=False, cancel=None, delete=None, color=None):
    global dialog, focus, dropOpen
    commitFocus()
    dropOpen = None
    dialog = O(kind=kind, title=title, buf=text, done=done, multiline=multiline, cancel=cancel, delete=delete, color=color)


def confirm(msg, yes):
    openDialog('confirm', msg, '', done=lambda _: yes())


def closeDialog(ok):
    global dialog
    d, dialog = dialog, None
    if ok:
        d.done(d.buf)
    elif d.cancel:
        d.cancel()


def drawDialog():
    if not dialog:
        return
    d = dialog
    s = pygame.Surface((W(), H()), pygame.SRCALPHA)
    s.fill((0, 0, 0, 130))
    screen.blit(s, (0, 0))
    w = min(520, W() - 40)
    lines = wrap(d.title, w - 32, 15)
    th = len(lines) * 20
    bh = 0 if d.kind == 'confirm' else (150 if d.multiline else 34)
    h = 16 + th + 10 + bh + (44 if d.kind == 'text' else 0) + 54
    r = pygame.Rect((W() - w) // 2, (H() - h) // 2, w, h)
    box(r, UI.bar, UI.edge, 10)
    y = r.y + 16
    for line in lines:
        txt(line, r.x + 16, y, UI.text, 15, 700)
        y += 20
    y += 10
    if bh:
        tb = pygame.Rect(r.x + 16, y, w - 32, bh)
        box(tb, '#15181d', UI.pink)
        f = font(400, 14, 'mono')
        rows = wrap(d.buf, tb.w - 16, 14) if d.multiline else [d.buf]
        rows = rows[-(bh // 18):]
        for i, line in enumerate(rows):
            surf = f.render(line, True, color(UI.text)[:3])
            screen.blit(surf, (tb.x + 8, tb.y + 7 + i * 18))
        if int(time.time() * 2) % 2 == 0:
            cx = tb.x + 9 + f.size(rows[-1] if rows else '')[0]
            cy = tb.y + 7 + (len(rows) - 1) * 18
            pygame.draw.line(screen, color(UI.text)[:3], (cx, cy), (cx, cy + 16))
        y += bh + 8
        hint = 'Enter = new line, Ctrl+Enter = save, Ctrl+V pastes, Esc cancels' if d.multiline else 'Enter = save, Esc cancels'
        txt(hint, r.x + 16, y, UI.dim, 12)
    if d.kind == 'text':
        y += 20
        txt('Color', r.x + 16, y + 4, UI.dim, 13)
        for i, c in enumerate(TEXT_COLORS):
            sw = pygame.Rect(r.x + 70 + i * 30, y, 24, 24)
            box(sw, c, UI.pink if d.color == c else UI.edge, 4)
            if d.color == c:
                pygame.draw.rect(screen, color(UI.pink)[:3], sw.inflate(4, 4), 2, border_radius=5)
            addHit(sw, lambda c=c: setattr(dialog, 'color', c))
    by = r.bottom - 46
    x = r.right - 16
    for label, cb, prim in [('OK' if d.kind == 'confirm' else 'Save', lambda: closeDialog(True), True),
                            ('Cancel', lambda: closeDialog(False), False)] + \
            ([('Delete', lambda: (globals().__setitem__('dialog', None), d.delete()), False)] if d.delete else []):
        bw = font(400, 14).size(label)[0] + 28
        x -= bw
        button((x, by, bw, 32), label, cb, primary=prim)
        x -= 8


def dialogKey(e):
    d = dialog
    ctrl = e.mod & pygame.KMOD_CTRL
    if e.key == pygame.K_ESCAPE:
        closeDialog(False)
    elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
        if d.multiline and not ctrl:
            d.buf += '\n'
        else:
            closeDialog(True)
    elif e.key == pygame.K_BACKSPACE:
        d.buf = d.buf[:-1]
    elif e.key == pygame.K_v and ctrl:
        d.buf += clipboard_get().replace('\r', '') if d.multiline else clipboard_get().replace('\r', '').replace('\n', ' ')


# =====================================================================
#  The bars and the sidebar
# =====================================================================
def drawTopBar():
    pygame.draw.rect(screen, color(UI.bar)[:3], (0, 0, W(), TOP))
    pygame.draw.line(screen, color(UI.line)[:3], (0, TOP - 1), (W(), TOP - 1))
    x = 12
    x += txt('Treats Level Editor', x, TOP / 2, UI.text, 17, 700, valign='middle') + 16

    def setName(s):
        chunk.name = s.strip()[:40] or 'My Chunk'
        save()
    x += txt('Name', x, TOP / 2, UI.text, 14, valign='middle') + 6
    field('name', (x, 10, 150, 28), chunk.name, setName, live=True)
    x += 162
    x += txt('Width', x, TOP / 2, UI.text, 14, valign='middle') + 6
    field('width', (x, 10, 52, 28), chunk.w, numCommit(lambda v: (resizeChunk(v), save())), numeric=True)
    x += 60
    x += txt('Height', x, TOP / 2, UI.text, 14, valign='middle') + 6
    field('height', (x, 10, 52, 28), chunk.h, numCommit(lambda v: (resizeHeight(v, heightAtTop), save())), numeric=True)
    x += 58

    def flip():
        global heightAtTop
        heightAtTop = not heightAtTop
    button((x, 10, 100, 28), 'rows at top' if heightAtTop else 'rows at bottom', flip, size=13)
    x += 110
    button((x, 10, 52, 28), 'New', lambda: confirm('Start a new chunk? Your current one is replaced (grab its code first if you want to keep it).',
                                                    lambda: (setChunk(blankChunk()), save())))
    x += 60
    opts = [('%s|%s' % p, '%s / %s' % p) for p in gameChunks()]
    global copyPick
    if copyPick is None and opts:
        copyPick = opts[0][0]
    dropdown('copyPick', (x, 10, 190, 28), opts, copyPick, lambda v: globals().__setitem__('copyPick', v))
    x += 196

    def copyLevel():
        if not copyPick:
            return
        area, name = copyPick.split('|', 1)
        c = refChunk(O(area=area, name=name))
        if c:
            confirm('Start a new chunk as a copy of "%s"? Your current one is replaced (grab its code first if you want to keep it).' % name,
                    lambda: (setChunk(copyOf(c)), save(), status('Copied "%s". Change what you like, then Get code.' % name)))
    button((x, 10, 92, 28), 'Copy level', copyLevel)
    x += 100
    button((x, 10, 70, 28), 'Play', startPlay, primary=True)
    x += 80
    if statusMsg and time.time() < statusT:
        txt(statusMsg, x, TOP / 2, UI.dim, 13, valign='middle', maxw=max(10, W() - x - 10))


copyPick = None
refPick = None


def drawBottomBar():
    y0 = H() - BOTTOM
    pygame.draw.rect(screen, color(UI.bar)[:3], (0, y0, W(), BOTTOM))
    pygame.draw.line(screen, color(UI.line)[:3], (0, y0), (W(), y0))

    def getCode():
        global lastCode
        lastCode = toCode()
        if clipboard_set(lastCode):
            status('Code copied! Paste it in chat.')
        else:
            status('Could not reach the clipboard.')

    def loadCode():
        code = clipboard_get().strip()
        try:
            setChunk(fromCode(code))
        except Exception as e:
            status('That code did not load (copy a TREATS1: code first): %s' % e)
            return
        save()
        status('Loaded "%s".' % chunk.name)
        # a code that remembers its spot next to another chunk brings that chunk back in
        p = chunk.place
        if p and refChunk(O(area=p.a, name=p.n)) and not any(r.area == p.a and r.name == p.n for r in refs):
            addRef(p.a, p.n, (-p.x, -p.y))
    button((W() - 200, y0 + 12, 186, 34), 'Get code (copies it)', getCode, primary=True)
    button((W() - 396, y0 + 12, 186, 34), 'Load code (clipboard)', loadCode)
    box(pygame.Rect(12, y0 + 10, W() - 420, BOTTOM - 20), '#15181d', UI.edge)
    shown = lastCode or 'Get code puts the chunk code on the clipboard. Load code reads one from it.'
    txt(shown, 20, y0 + BOTTOM / 2, '#c9f27a' if lastCode else '#6b727c', 12, valign='middle', maxw=W() - 440)


lastCode = ''


def drawSidebar():
    global clipNow, sideH, sideScroll, refPick
    r = pygame.Rect(0, TOP, SIDE, H() - TOP - BOTTOM)
    pygame.draw.rect(screen, color(UI.side)[:3], r)
    pygame.draw.line(screen, color(UI.line)[:3], (SIDE - 1, TOP), (SIDE - 1, r.bottom))
    sideScroll = max(0, min(sideScroll, sideH - r.h + 20))
    screen.set_clip(r)
    clipNow = r
    x, w = 12, SIDE - 24
    y = TOP + 10 - sideScroll

    def head(s, extra=None):
        nonlocal y
        y += 6
        txt(s.upper(), x, y, UI.dim, 12, 700)
        if extra:
            txt(extra, x + font(700, 12).size(s.upper())[0] + 8, y, UI.orange, 12)
        y += 22

    head('Tools')
    bw = (w - 6) // 2
    for i, t in enumerate(TOOLS):
        bx, by = x + (i % 2) * (bw + 6), y + (i // 2) * 34
        button((bx, by, bw, 30), t.label, lambda t=t: setTool(t.id), on=tool == t.id, key=t.key, size=13)
    y += ((len(TOOLS) + 1) // 2) * 34 + 4

    head('Rectangle')
    txt('Fills with', x, y + 6, '#c8ced6', 13)
    dropdown('rectFill', (x + 70, y, w - 70, 26), RECT_FILLS, rectFill,
             lambda v: (globals().__setitem__('rectFill', v), setTool('rect')))
    y += 34

    syncTree()
    head('Tree')
    for label, val, dec, inc in [('Trunk height', '%s tiles' % fmt(treeH), lambda: setTree(treeH - 0.5, treeR), lambda: setTree(treeH + 0.5, treeR)),
                                 ('Rotation', '%d deg' % treeR, lambda: setTree(treeH, treeR - 90), lambda: setTree(treeH, treeR + 90))]:
        txt(label, x, y + 5, '#c8ced6', 13)
        button((x + w - 92, y, 26, 26), '-', dec)
        txt(val, x + w - 46, y + 13, UI.text, 13, align='center', valign='middle')
        button((x + w - 26, y, 26, 26), '+', inc)
        y += 32
    button((x, y, w, 28), 'Delete selected', deleteSelection, disabled=not sel)
    y += 36

    # fireball and cloud settings
    def settingsRows(prefix, fields, s, changed):
        nonlocal y
        for f in fields:
            if f.modes and s.mode not in f.modes:
                continue
            if f.bool:
                y += checkbox((x, y, w, 20), f.label, bool(s[f.k]), lambda v, k=f.k: (s.__setitem__(k, v), changed())) + 4
            else:
                for line in wrap(f.label, w, 13):
                    txt(line, x, y, '#c8ced6', 13)
                    y += 17
                y += 2
                if f.options:
                    dropdown(prefix + f.k, (x, y, w, 26), f.options, s[f.k], lambda v, k=f.k: (s.__setitem__(k, v), changed()))
                elif f.range:
                    hw = (w - 30) // 2

                    def setter(i, k=f.k):
                        def set_(v):
                            a = list(s[k])
                            a[i] = v
                            s[k] = a
                            changed()
                        return set_
                    field(prefix + f.k + '.0', (x, y, hw, 26), s[f.k][0], numCommit(setter(0), f.min, f.max), numeric=True)
                    txt('to', x + hw + 15, y + 13, UI.dim, 13, align='center', valign='middle')
                    field(prefix + f.k + '.1', (x + hw + 30, y, hw, 26), s[f.k][1], numCommit(setter(1), f.min, f.max), numeric=True)
                else:
                    field(prefix + f.k, (x, y, w, 26), s[f.k],
                          numCommit(lambda v, k=f.k: (s.__setitem__(k, v), changed()), f.min, f.max), numeric=True)
                y += 30
            if f.hint:
                for line in wrap(f.hint, w, 11):
                    txt(line, x, y - 2, '#8a939e', 11)
                    y += 14
            y += 4

    it = selectedOf('fire')
    if tool == 'fire' or it:
        global nextFire, firePreview
        head('Fireball', 'Picked spawner' if it else 'Next spawner you place')
        y += checkbox((x, y, w, 20), 'Preview fireballs here', firePreview, lambda v: globals().__setitem__('firePreview', v)) + 6
        s = fireTarget()
        settingsRows('fire.', FIRE_FIELDS, s, (lambda: save()) if it else (lambda: None))

    it = selectedOf('cloud')
    if tool == 'cloud' or it:
        global cloudPathEdit
        if not it or tool != 'cloud':
            cloudPathEdit = False
        head('Cloud', 'Picked cloud' if it else 'Next cloud you place')
        y += checkbox((x, y, w, 20), 'Preview movement here', cloudPreview, lambda v: globals().__setitem__('cloudPreview', v)) + 6
        s = cloudTarget()
        settingsRows('cloud.', CLOUD_FIELDS, s, (lambda: save()) if it else (lambda: None))
        if s.mode == 'path':
            if not it:
                info = 'Place the cloud first, then draw its path.'
            elif cloudPathEdit:
                info = "Click spots for the cloud's middle to pass through, in order. %d so far." % len(s.pts)
            else:
                info = '%d points.' % len(s.pts) if s.pts else 'No path yet: press Draw path.'
            for line in wrap(info, w, 12):
                txt(line, x, y, '#8a939e', 12)
                y += 15
            if it:
                y += 4
                bw3 = (w - 12) // 3

                def drawPath():
                    global cloudPathEdit
                    on = not cloudPathEdit
                    if tool != 'cloud':
                        setTool('cloud')   # (clicks only add points with the Cloud tool)
                    cloudPathEdit = on
                button((x, y, bw3, 28), 'Done' if cloudPathEdit else 'Draw path', drawPath, primary=cloudPathEdit, size=12)
                button((x + bw3 + 6, y, bw3, 28), 'Undo point', lambda: (s.pts.pop(), save()), disabled=not s.pts, size=12)
                button((x + 2 * bw3 + 12, y, bw3, 28), 'Clear', lambda: (s.pts.clear(), save()), disabled=not s.pts, size=12)
                y += 34

    head('Other chunks')
    opts = [('%s|%s' % p, '%s / %s' % p) for p in gameChunks()]
    if refPick is None and opts:
        refPick = opts[0][0]
    dropdown('refPick', (x, y, w - 58, 28), opts, refPick, lambda v: globals().__setitem__('refPick', v))
    button((x + w - 52, y, 52, 28), 'Add', lambda: refPick and addRef(*refPick.split('|', 1)))
    y += 34
    button((x, y, w, 28), 'Generate world', generateWorld)
    y += 34
    for i, rf in enumerate(list(refs)):
        label = rf.area + ' / ' + rf.name + (' (spot saved)' if i == 0 else '')
        for j, line in enumerate(wrap(label, w - 34, 12)):
            txt(line, x, y + 4 + j * 15, UI.blue, 12)

        def remove(rf=rf):
            refs.remove(rf)
            saveRefs()
            sizeCanvas()
        button((x + w - 26, y, 26, 22), 'x', remove, size=12)
        y += max(26, len(wrap(label, w - 34, 12)) * 15 + 6)

    head('How to')
    for line in HELP:
        for wl in wrap(line, w, 12):
            txt(wl, x, y, '#9aa3ad', 12)
            y += 15
        y += 6
    sideH = y + sideScroll - TOP
    screen.set_clip(None)
    clipNow = None


HELP = [
    'Left drag paints, right drag erases. Mouse wheel scrolls (Shift+wheel sideways), Ctrl+wheel zooms, middle drag or arrow keys move around.',
    'Select (V): click an object or a block, or drag a box around several, then drag them to move. Shift adds, Delete removes, Esc lets go.',
    'Rectangle (R): drag a box and let go to fill it with the block picked above. Right drag clears the box.',
    'Cobblestone (O): a solid block Charlie can\'t inhale.',
    'Other chunks: pick a chunk from the game and press Add to see it next to yours, then drag it with Move chunks (M). Drag your own chunk the same way to move it among the others. The first one\'s spot is saved in your code.',
    'Generate world: shows every chunk of the main world around yours, right where it is in the game.',
    'Tree (7): click a trunk to pick it. [ ] change its height, Q E turn it.',
    'Text (9), Greenie (6) and Note (N) ask for words in a box. Fireball (F) and Cloud (L) show their settings above.',
    'Play (P) opens the chunk in the game in its own window. Get code copies the chunk code; paste it in chat with where it should go.',
]


# =====================================================================
#  Input
# =====================================================================
def onMouseDown(e):
    global painting, lastCell, refDrag, rectDrag, pan, sideScroll
    mx, my = e.pos
    if e.button in (4, 5):
        return
    if dropOpen:
        clickDropList(mx, my)
        return
    # widgets (topmost first)
    for r, cb in reversed(hitList):
        if r.collidepoint(mx, my) and e.button == 1:
            cb()
            return
    if dialog:
        return
    commitFocus()
    cr = canvasRect()
    if not cr.collidepoint(mx, my):
        return
    if e.button == 2:
        pan = (mx, my, scroll[0], scroll[1])
        return
    shift = pygame.key.get_mods() & pygame.KMOD_SHIFT
    if tool == 'select' and e.button == 1:
        selectDown(mx, my, shift)
        return
    if tool == 'rect':
        if e.button in (1, 3):
            tx, ty = pxToCell(eventPx(mx, my))
            rectDrag = O(x0=tx, y0=ty, x1=tx, y1=ty, erase=e.button == 3)
        return
    if tool == 'arrange':
        # your chunk is on top, so a press inside it moves yours; anywhere else, the chunk under it
        px, py = eventPx(mx, my)
        mine = 0 <= px < chunk.w * T and 0 <= py < chunk.h * T
        r = 'me' if mine else refAt(px, py)
        if r == 'me' and not refs:
            status('Add other chunks (or Generate world) first: yours moves next to them.')
        elif r and e.button == 1:
            refDrag = O(ref=r, sx=mx, sy=my, moved=[0, 0])
        return
    painting = 2 if e.button == 3 else 1
    lastCell = ''
    applyAt(mx, my, True)


def onMouseUp(e):
    global refDrag, painting, pan
    if e.button == 2:
        pan = None
        return
    if refDrag:
        refDrag = None
        saveRefs()
        return
    if rectDrag:
        rectUp()
        return
    selectUp()
    if noteDrag:
        painting = 0
        finishNoteDrag()
        return
    if painting:
        painting = 0
        save()


def onMouseMove(e):
    global hover
    mx, my = e.pos
    if pan:
        scroll[0] = pan[2] - (mx - pan[0])
        scroll[1] = pan[3] - (my - pan[1])
        clampScroll()
        return
    if refDrag:
        # whole tiles, any direction (above / below too), by how far the mouse has gone
        d = refDrag
        nx, ny = round((mx - d.sx) / (T * Z)), round((my - d.sy) / (T * Z))
        ddx, ddy = nx - d.moved[0], ny - d.moved[1]
        if ddx or ddy:
            d.moved = [nx, ny]
            if d.ref == 'me':
                # your chunk moves = everything else moves the other way; scroll so the others stay put
                for r in refs:
                    r.x -= ddx
                    r.y -= ddy
                sizeCanvas()
                scroll[0] -= ddx * T * Z
                scroll[1] -= ddy * T * Z
                clampScroll()
            else:
                d.ref.x += ddx
                d.ref.y += ddy
                sizeCanvas()   # grows to fit (it scrolls along, so the mouse stays on the same spot)
    if selDrag or marquee:
        selectMove(mx, my)
    if rectDrag:
        rectDrag.x1, rectDrag.y1 = pxToCell(eventPx(mx, my))
    if canvasRect().collidepoint(mx, my) and not dialog:
        px, py = eventPx(mx, my)
        hover = (math.floor(px / T), math.floor(py / T))
        if painting:
            applyAt(mx, my, False)
    else:
        hover = None


def onWheel(e):
    global sideScroll
    mx, my = mouse
    if dialog or dropOpen:
        return
    mods = pygame.key.get_mods()
    if mx < SIDE and TOP < my < H() - BOTTOM:
        sideScroll = max(0, sideScroll - e.y * 40)
        return
    if mods & pygame.KMOD_CTRL:
        setZoom(Z * (1.15 if e.y > 0 else 1 / 1.15), mx, my)
    elif mods & pygame.KMOD_SHIFT:
        scroll[0] -= e.y * 80
    else:
        scroll[0] -= e.x * 80
        scroll[1] -= e.y * 80
    clampScroll()


def onKeyDown(e):
    global cloudPathEdit
    if dialog:
        dialogKey(e)
        return
    if focus:
        if e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_TAB):
            commitFocus()
        elif e.key == pygame.K_ESCAPE:
            globals()['focus'] = None
        elif e.key == pygame.K_BACKSPACE:
            focus.buf = focus.buf[:-1]
            if focus.live:
                focus.commit(focus.buf)
        elif e.key == pygame.K_v and e.mod & pygame.KMOD_CTRL:
            focus.buf += clipboard_get().strip().replace('\n', ' ')
            if focus.live:
                focus.commit(focus.buf)
        return
    if dropOpen and e.key == pygame.K_ESCAPE:
        globals()['dropOpen'] = None
        return
    ctrl = e.mod & pygame.KMOD_CTRL
    ch = (e.unicode or '').upper()
    if ctrl:
        if e.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
            setZoom(Z * 1.15)
        elif e.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
            setZoom(Z / 1.15)
        elif e.key == pygame.K_0:
            setZoom(0.75)
        return
    t = next((t for t in TOOLS if t.key == ch), None) if ch else None
    if t:
        setTool(t.id)
    elif ch == '[':
        setTree(treeH - 0.5, treeR)
    elif ch == ']':
        setTree(treeH + 0.5, treeR)
    elif ch == 'Q':
        setTree(treeH, treeR - 90)
    elif ch == 'E':
        setTree(treeH, treeR + 90)
    elif e.key in (pygame.K_DELETE, pygame.K_BACKSPACE):
        deleteSelection()
    elif ch == 'P':
        startPlay()
    elif e.key == pygame.K_ESCAPE:
        if cloudPathEdit:
            cloudPathEdit = False
        else:
            setSelection([])
    elif e.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN):
        step = 160
        scroll[0] += step * ((e.key == pygame.K_RIGHT) - (e.key == pygame.K_LEFT))
        scroll[1] += step * ((e.key == pygame.K_DOWN) - (e.key == pygame.K_UP))
        clampScroll()


def onText(s):
    if dialog:
        if dialog.kind != 'confirm':
            dialog.buf += s
        return
    if focus:
        if focus.numeric and not all(c in '0123456789.-' for c in s):
            return
        focus.buf += s
        if focus.live:
            focus.commit(focus.buf)


# =====================================================================
#  Start and the main loop
# =====================================================================
def init():
    global screen, ctx, refs
    pygame.init()
    pygame.display.set_caption('Treats - Level Editor')
    screen = pygame.display.set_mode((1400, 860), pygame.RESIZABLE)
    ctx = Ctx(screen)
    game.ctx = ctx
    game.loadImages()
    # nothing in the editor is ever off screen as far as the game's drawing is concerned
    game.camX, game.camY, game.VIEW_W, game.VIEW_H = -1e9, -1e9, 2e9, 2e9
    pygame.key.start_text_input()
    start = blankChunk()
    d = store_get(DRAFT_KEY)
    if d:
        try:
            start = fromCode(d)
        except Exception as e:
            print('Draft did not load:', e)
    try:
        refs = [O(r) for r in (store_get(REFS_KEY) or []) if refChunk(O(r))]
    except Exception:
        refs = []
    setChunk(start)
    scrollTo(0, 0)


def main():
    global screen, ctx, mouse
    init()
    clock = pygame.time.Clock()
    t0 = time.perf_counter()
    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                return
            if e.type == pygame.VIDEORESIZE or e.type == pygame.WINDOWSIZECHANGED:
                screen = pygame.display.get_surface()
                ctx = game.ctx = Ctx(screen)
                clampScroll()
            elif e.type == pygame.KEYDOWN:
                onKeyDown(e)
            elif e.type == pygame.TEXTINPUT:
                onText(e.text)
            elif e.type == pygame.MOUSEBUTTONDOWN:
                onMouseDown(e)
            elif e.type == pygame.MOUSEBUTTONUP:
                onMouseUp(e)
            elif e.type == pygame.MOUSEMOTION:
                mouse = e.pos
                onMouseMove(e)
            elif e.type == pygame.MOUSEWHEEL:
                onWheel(e)
        hitList.clear()
        screen.fill(color(UI.bg)[:3])
        drawCanvas(time.perf_counter() - t0)
        drawSidebar()
        drawTopBar()
        drawBottomBar()
        if dialog:
            hitList.clear()   # only the dialog can be clicked while it's open
        drawDialog()
        drawDropList()
        pygame.display.flip()
        clock.tick(60)


if __name__ == '__main__':
    main()
