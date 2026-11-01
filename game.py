# =====================================================================
#  Treats - OvO-style platformer playground (Python / pygame version)
#  A port of game.js. Run main.py.
# =====================================================================

import math
import sys
import time
import json
import base64
import random as _random
from functools import cmp_to_key

import pygame

from engine import O, Ctx, Img, font, color, store_get, store_set, clipboard_set, clipboard_get, \
    radial_surface, hole_mask, linear_v

T = 32                 # tile size (px)
VIEW_W, VIEW_H = 960, 540
STEP = 1 / 120         # fixed physics step
H_STAND, H_LOW, P_W = 34, 20, 30   # Charlie's hitbox (still too tall for 1-tile tunnels)
CHARLIE_W, CHARLIE_H = 38, 34      # drawn size before squash & stretch
INF = math.inf


def random():
    return _random.random()


def sign(v):
    return (v > 0) - (v < 0)


def hypot(*a):
    return math.hypot(*a)


# All movement tuning lives here.
PHYS = O(
    gravity=1800,
    maxFall=900,

    runMax=270,
    runAccel=2600,
    turnAccel=4200,
    groundFriction=2800,
    groundOverDecel=420,   # how fast speed above runMax bleeds off on the ground
    airAccel=1700,
    airTurnAccel=2400,
    airDrag=150,
    airOverDecel=60,       # ...and in the air (keeps boost / dive momentum)

    jump=[560, 650, 820],  # single, double, triple
    tripleWindow=0.15,     # seconds after landing to chain the next jump
    jumpCut=0.45,          # velocity multiplier when jump is released early
    coyote=0.09,
    jumpBuffer=0.12,

    wallSlideMax=140,
    wallJumpX=340,
    wallJumpY=560,
    wallJumpLock=0.14,

    slideFriction=170,
    slideBoost=160,
    slideMaxBoost=500,
    slideMinSpeed=130,     # below this a slide turns into a crouch
    crouchSpeed=120,
    slideJumpY=520,
    slideJumpMult=1.15,
    slideJumpCap=640,

    diveX=480,
    diveBonus=100,
    diveY=230,
    diveGravity=1500,

    smashSpeed=1150,
    smashMaxFall=1400,
    smashJump=900,
    smashJumpWindow=0.35,   # seconds after a smash landing that a jump becomes a smash jump
    smashJumpBuffer=0.3,    # jump pressed while still smashing down is remembered this long

    # with an eight pack (from Grandma's turkey legs), a bit more of everything
    packJump=1.07,         # jump / smash jump / slide jump speed up (higher)...
    packJumpX=1.06,        # ...and sideways (longer)
    packSmash=1.15,        # smash speed down
    packDiveX=1.08,        # dive forward speed
    packDiveGravity=0.8,   # dive falls slower, so it lasts longer
    wingSpeed=330,         # wings: how fast W / S fly Charlie up and down (px/s)
    wingAccel=2400,        # ...and how quickly he gets to that speed
    hurtImmune=1,          # seconds of blinking (no damage) after the eight pack takes a hit

    trampoline=960,
    trampolineHeld=1150,
    trampolineSmash=1300,

    boostSpeed=780,

    crumbleDelay=2,        # seconds a crumbling platform shakes before it falls
    crumbleRespawn=2.5,    # seconds before it comes back
)

# ---------------------------------------------------------------------
#  Input (key names are the browser's, so the bindings read the same)
# ---------------------------------------------------------------------
BIND = O(
    left=['ArrowLeft', 'KeyA'],
    right=['ArrowRight', 'KeyD'],
    jump=['ArrowUp', 'KeyW', 'Space'],
    up=['ArrowUp', 'KeyW'],
    down=['ArrowDown', 'KeyS'],
    dive=['ShiftLeft', 'ShiftRight', 'KeyX'],
    inhale=['KeyZ', 'Digit0', 'Numpad0', 'Mouse0'],   # Mouse0 = left click (aims at the cursor)
)
keys = set()
pressedKeys = set()


def held(a):
    return any(k in keys for k in BIND[a])


def pressed(a):
    return any(k in pressedKeys for k in BIND[a])


cursor = None   # mouse position on the game screen (None until it moves over it)

# ---------------------------------------------------------------------
#  World
#  One continuous world made of sections laid left to right. Chunks made
#  in the editor are added with addChunk(code, ...) in world.py.
#
#  Tiles:  . empty   # solid   g ground (grass on top)   X breakable (smash)
#          ~ crumbling   c crumbled (temporarily gone)   T trampoline
#          > < boost pads   ^ spikes
#  Behind the tiles there's a background layer: dirt background (scenery).
# ---------------------------------------------------------------------
LH, G = 28, 24   # standard chunk height in tiles; G = ground row


def secH(s):
    return s.h or LH


LW, GH = 0, LH     # world size in tiles
grid = signs = checkpoints = treats = greenies = trees = texts = movers = lasers = None
finish = spawn = None
sectionSpans = []
bgGrid = None
chickens = []
baseGrid = None
houses, doors, npcs, props, diamonds = [], [], [], [], []
backdrop = 'sky'   # 'house' = beige wallpaper, 'hut' = log walls
dimness = 0        # 0 = normal light; more = darker, lit only by fireplaces
turkeys = []       # turkey legs on Grandma's table: { x, y, t }
# 'hard' (the intended game) or 'easy': picked when you start a fresh game, kept in save codes.
difficulty = 'hard'
switches = []
secrets, secretMap, activeSecret = [], None, 0
links, portals = [], {}
views, camLikes = [], []
crumbleState = {}
trampAnim = {}
# Forest Depths things: endless-looking walls, winged treats, falling ceilings (see sectionTools)
endlessWalls, wingTreats, slabs = [], [], []


# Builders for one section. `shift` / `dy` slide them to wherever the section sits in the world.
def sectionTools(shift, dy=0):
    def Y(y):
        return (y + dy) * T

    def X(x):
        return (x + shift) * T

    def setc(x, y, c):
        x += shift
        y += dy
        if 0 <= y < GH and 0 <= x < LW:
            grid[int(y)][int(x)] = c

    def setBg(x, y):
        x += shift
        y += dy
        if 0 <= y < GH and 0 <= x < LW:
            bgGrid[int(y)][int(x)] = True

    def fill(x, y, w, h, c='#'):
        for j in range(int(y), int(y + h)):
            for i in range(int(x), int(x + w)):
                setc(i, j, c)

    t = O()
    t.set = setc
    t.setBg = setBg
    t.fill = fill
    t.floor = lambda x, w: fill(x, G, w, LH - G)

    def spikePit(x0, x1):
        for x in range(x0, x1 + 1):
            setc(x, G, '.')
            setc(x, G + 1, '^')
    t.spikePit = spikePit
    t.sign = lambda x, text, y=G: signs.append(O(x=X(x) + T / 2, y=Y(y), text=text))
    t.cp = lambda x, y=G: checkpoints.append(O(x=X(x) + T / 2, y=Y(y), active=False))
    t.coin = lambda x, y: treats.append(O(x=X(x) + T / 2, y=Y(y) + T / 2, taken=False))
    # Greenies work like Power Moons: hidden in tricky spots, named, and remembered between plays.
    t.greenie = lambda id, name, x, y: greenies.append(O(id=id, name=name, x=X(x) + T / 2, y=Y(y) + T / 2, taken=False))

    def text(x, y, s, col):
        sz = pixelTextSize(s)
        texts.append(O(x=X(x), y=Y(y), w=sz.w, h=sz.h, text=s, color=col))
    t.text = text
    t.tree = lambda x, y, hTiles, rotDeg: trees.append(makeTree(X(x) + T / 2, Y(y), hTiles * T, rotDeg * math.pi / 180))
    t.chicken = lambda x, y: chickens.append(makeChicken(X(x) + T / 2, Y(y + 1)))

    # A house you walk in front of (no hitbox). Its door, in the middle, leads to area `to`.
    def house(x, w, floor, to, opts=None):
        opts = opts or {}
        h = O(x=X(x), w=w * T, floor=Y(floor))
        houses.append(h)
        doors.append(O(x=h.x + (w // 2) * T, y=h.floor - 2 * T, w=T, h=2 * T, to=to, id=opts.get('id'),
                       arrive=opts.get('arrive'), lockedT=0, house=h))
    t.house = house

    # A door on its own (indoors), with a frame around it.
    def door(x, floor, to, opts=None):
        opts = opts or {}
        doors.append(O(x=X(x), y=Y(floor) - 2 * T, w=T, h=2 * T, to=to, id=opts.get('id'), arrive=opts.get('arrive'),
                       lockedT=0, framed=True))
    t.door = door

    def set_backdrop(kind):
        global backdrop
        backdrop = kind
    t.backdrop = set_backdrop

    def dim(level):
        global dimness
        dimness = level
    t.dim = dim
    t.fireplace = lambda x, floor, w, ceil: props.append(O(kind='fireplace', x=X(x), y=Y(floor) - 3 * T, w=w * T, h=3 * T, top=Y(ceil), t=0))
    t.couch = lambda x, floor, w: props.append(O(kind='couch', x=X(x), y=Y(floor) - 1.6 * T, w=w * T, h=1.6 * T))

    def turkeyTable(x, floor):
        props.append(O(kind='table', x=X(x), y=Y(floor) - 1.2 * T, w=3 * T, h=1.2 * T))
        for i in range(3):
            turkeys.append(O(x=X(x) + T * (0.9 + i * 0.6), y=Y(floor) - 1.2 * T - 10, t=0))
    t.turkeyTable = turkeyTable
    t.chimney = lambda x, top, bottom: props.append(O(kind='chimney', x=X(x), y=Y(top), w=T * 0.9, h=(bottom - top) * T, t=0))
    t.grandma = lambda x, seat: npcs.append(O(kind='grandma', x=X(x), feet=Y(seat), head=70,
                                              lines=GRANDMA_AGAIN if stuff.grandmaDone else GRANDMA_LINES))
    t.light = lambda x, y: props.append(O(kind='light', x=X(x) + T / 2, y=Y(y)))
    t.closet = lambda x, floor: props.append(O(kind='closet', x=X(x), y=Y(floor) - 5 * T, w=3 * T, h=5 * T))
    t.chest = lambda x, floor: props.append(O(kind='chest', x=X(x), y=Y(floor) - 1.5 * T, w=2.5 * T, h=1.5 * T))
    t.diamond = lambda id, x, y: diamonds.append(O(id=id, x=X(x) + T / 2, y=Y(y) + T / 2, taken=False))

    def fire(x, y, st):
        s = fireSettings(st)
        fireSpawners.append(O(x=X(x) + T / 2, y=Y(y) + T / 2, s=s, t=s.delay, alive=0))
    t.fire = fire
    t.bob = lambda x, floor: npcs.append(O(kind='bob', x=X(x) + T / 2, feet=Y(floor)))

    # The text that starts at tile (tx, ty) fades away while all the chickens that
    # started on the given tiles are knocked out (they, and it, come back when you die).
    def hideTextWhenChickensGone(at, spots):
        tx, ty = at
        txt = next((o for o in texts if o.x == X(tx) and o.y == Y(ty)), None)
        cks = [c for c in (next((c for c in chickens if c.home[0] == X(x) + T / 2 and c.home[1] == Y(y + 1)), None)
                           for x, y in spots) if c]
        if txt and cks:
            txt.hideIf = lambda: all(not c.alive for c in cks)
    t.hideTextWhenChickensGone = hideTextWhenChickensGone
    t.mover = lambda ax, ay, bx, by, wTiles, period: movers.append(O(
        ax=X(ax), ay=Y(ay), bx=X(bx), by=Y(by), w=wTiles * T, h=14, period=period,
        x=X(ax), y=Y(ay), dx=0, dy=0))
    t.laser = lambda x, y0, y1, offset: lasers.append(O(x=X(x) + T / 2, y0=Y(y0), y1=Y(y1), period=1.8, on=0.5, offset=offset))

    def setSpawn(x):
        global spawn
        spawn = O(x=X(x) + T / 2, y=Y(G))
    t.setSpawn = setSpawn

    # A wooden plank bridge on row y from x0 to x1, with a button under its middle.
    def bridge(x0, x1, y, id):
        for x in range(x0, x1 + 1):
            setc(x, y, '.' if stuff.flags.get(id) else 'k')
        if stuff.flags.get(id):
            return
        cells = [[x + shift, y + dy] for x in range(x0, x1 + 1)]
        switches.append(O(id=id, x=X((x0 + x1 + 1) / 2) - 12, y=Y(y + 1), w=24, h=8, cells=cells))
    t.bridge = bridge

    # A chicken that comes back `wait` seconds after it's knocked out.
    def chickenSpawner(x, y, wait=3):
        ck = makeChicken(X(x) + T / 2, Y(y + 1))
        ck.respawn = wait
        chickens.append(ck)
    t.chickenSpawner = chickenSpawner

    # A greenie that only shows when Charlie is alive and within `tiles` of it.
    def showGreenieNear(x, y, tiles):
        g = next((o for o in greenies if o.x == X(x) + T / 2 and o.y == Y(y) + T / 2), None)
        if g:
            g.near = tiles * T + T / 2
    t.showGreenieNear = showGreenieNear

    # A secret area. cells: [[x, y], ...]. opts.flood: also everything joined to them through
    # open dirt background (not into opts.except). opts.seeX: when inside, everything from that
    # column rightward still shows. opts.name names it; opts.also: secrets that show along with it.
    # opts.keepOutside: when inside, the world outside it still shows (only it opens up).
    def secret(cells, opts=None):
        opts = opts or {}

        def key(x, y):
            return (y + dy) * LW + x + shift
        out = set()
        skip = set(key(x, y) for x, y in opts.get('except', []))

        def is_open(x, y):
            wx, wy = x + shift, y + dy
            if wx < 0 or wy < 0 or wx >= LW or wy >= GH or not bgGrid[wy][wx]:
                return False
            c = grid[wy][wx]
            return c in ('.', '~', '^', 'T')
        todo = [list(c) for c in cells]
        while todo and len(out) < 20000:
            x, y = todo.pop()
            k = key(x, y)
            if k in out or k in skip:
                continue
            out.add(k)
            if opts.get('flood'):
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if is_open(nx, ny):
                        todo.append([nx, ny])
        secrets.append(O(cells=out, seeX=opts['seeX'] + shift if 'seeX' in opts else None,
                         name=opts.get('name', ''), also=opts.get('also', []), keepOutside=bool(opts.get('keepOutside'))))
    t.secret = secret
    t.view = lambda v: views.append(O(v, edge=v['edge'] + shift))
    t.cameraLike = lambda x, y, w, h, pairs: camLikes.append(O(x=X(x), y=Y(y), w=w * T, h=h * T, pairs=pairs))

    def portal(name, x, y):
        portals[name] = [x + shift, y + dy]
    t.portal = portal
    t.link = lambda x, y, w, h, frm, to: links.append(O(x=X(x), y=Y(y), w=w * T, h=h * T, frm=frm, to=to))

    def setFinish(x):
        global finish
        finish = O(x=X(x) + T / 2, y=Y(G))
    t.setFinish = setFinish

    # A door (standing on row `floor`) that's just a black hole. Up takes you to hole door `to`
    # in this same area.
    t.holeDoor = lambda x, floor, id, to: doors.append(O(x=X(x), y=Y(floor) - 2 * T, w=T, h=2 * T, id=id, here=to,
                                                          lockedT=0, hole=True))
    # Ground columns x0..x1 (rows top..bottom) that hide what's past them: from the left it looks
    # like column x0 - 1 goes on forever to the right, and from the right like column x1 + 1
    # goes on forever to the left.
    t.endlessWall = lambda x0, x1, top, bottom: endlessWalls.append(O(x0=x0 + shift, x1=x1 + shift, y0=top + dy, y1=bottom + dy))
    # A treat with wings flying round and round through the middles of tiles pts ([[x, y], ...]),
    # speed tiles a second. Eat it for wings: W / S fly, and one extra hit (like a turkey leg).
    t.wingedTreat = lambda pts, speed: wingTreats.append(O(
        m=pathOf([[X(x) + T / 2, Y(y) + T / 2] for x, y in pts], True), speed=speed * T, d=0, t=0, x=None, y=None))

    # The tiles in columns x0..x1, rows top..bottom drop at `speed` tiles a second once Charlie
    # touches row `trigger` (same columns), until something solid is under them. Spikes on
    # them hurt; being squashed into the ground kills.
    def dropCeiling(x0, x1, top, bottom, trigger, speed):
        slabs.append(O(x0=x0 + shift, x1=x1 + shift, y0=top + dy, h=bottom - top + 1, trig=trigger + dy, speed=speed,
                       p=0, row=0, max=0, moving=False, cells=None, under={}))
    t.dropCeiling = dropCeiling

    # Bob the Square standing on row `floor`, saying each line once, when its trigger first
    # comes true: near=tiles from Bob / at=[x, y, tiles] (tiles from a chunk tile) /
    # secret=name (Charlie inside that secret); got=greenie id: only once it's been grabbed.
    # {name} in a line is Charlie's name; *words* come out slowly.
    def talkingBob(x, floor, says):
        def one(o):
            o = O(o, done=False)
            if o.at:
                o.at = [X(o.at[0]) + T / 2, Y(o.at[1]) + T / 2, o.at[2]]
            return o
        npcs.append(O(kind='bobTalk', x=X(x) + T / 2, feet=Y(floor), say=None, says=[one(o) for o in says]))
    t.talkingBob = talkingBob
    return t


# Built-in sections (the old course, sections A-M). world.py clears them with clearWorld().
def _sec(id, name, base, w, build):
    return O(id=id, name=name, base=base, w=w, build=build)


def _A(t):
    t.floor(0, 25); t.fill(0, 0, 1, LH)
    t.setSpawn(3)
    t.sign(6, 'Arrows / WASD to run.  Up / W / Space to jump.  Hold jump longer to jump higher.')
    t.fill(12, G - 1, 2, 1)
    t.fill(16, G - 2, 2, 2)
    t.spikePit(20, 22)
    t.coin(21, G - 3)


def _B(t):
    t.floor(25, 32)
    t.cp(26)
    t.sign(30, 'Jump again right as you land for a DOUBLE jump, then a TRIPLE jump. Keep running!')
    t.coin(36, G - 3); t.coin(41, G - 4)
    t.fill(48, G - 5, 9, 5)
    t.coin(52, G - 6)


def _C(t):
    t.floor(57, 20)
    t.cp(57)
    t.sign(60, 'Hold toward a wall to WALL SLIDE. Press jump to WALL JUMP.')
    t.fill(64, 6, 1, G - 2 - 6)
    t.fill(68, 8, 6, G - 8)
    t.coin(66, 15); t.coin(66, 11); t.coin(66, 7); t.coin(71, 7)
    t.greenie('pillar', 'Atop the Pillar', 64, 4.9)


def _D(t):
    t.floor(77, 17)
    t.cp(78)
    t.sign(80, 'Press Down / S while running to SLIDE under low gaps.')
    t.fill(84, G - 10, 10, 9)
    t.coin(86, G - 1); t.coin(89, G - 1); t.coin(92, G - 1)
    t.greenie('leap', 'Leap of Faith', 89, 13)


def _E(t):
    t.floor(94, 14)
    t.cp(95)
    t.sign(97, 'Jump out of a slide for a LONG JUMP.')
    t.spikePit(100, 105)
    t.coin(102, G - 3); t.coin(103, G - 3)


def _F(t):
    t.floor(108, 16)
    t.cp(109)
    t.sign(111, 'Press jump again in mid-air (or Shift / X) to DIVE forward.')
    t.spikePit(114, 121)
    t.coin(117, G - 4); t.coin(118, G - 4)


def _G(t):
    t.floor(124, 25)
    t.cp(125)
    t.sign(127, 'In mid-air press Down to SMASH. Smash breaks cracked blocks!')
    for x in range(131, 135):
        t.set(x, G, 'X'); t.set(x, G + 1, '.'); t.set(x, G + 2, '.')
    t.greenie('cracked', 'Under the Cracked Floor', 132.5, G + 1.6)
    t.sign(138, 'Jump right as you land from a smash for a SMASH JUMP.')
    t.fill(143, G - 6, 6, 6)
    t.coin(146, G - 7)


def _H(t):
    t.floor(149, 37)
    t.cp(150)
    t.sign(153, 'TRAMPOLINES! Hold jump as you land on one to bounce higher.')
    t.set(157, G, 'T'); t.set(158, G, 'T')
    t.fill(161, G - 9, 4, 9)
    t.spikePit(167, 184)
    for x in (170, 175, 180):
        t.set(x, G + 1, 'T')
    t.coin(172, G - 6); t.coin(177, G - 6)
    t.greenie('bounce', 'Super Bounce Summit', 157.5, G - 15)


def _I(t):
    t.floor(186, 35)
    t.cp(187)
    t.sign(189, 'Ride the MOVING PLATFORMS.')
    t.spikePit(191, 207)
    t.mover(192, G - 1, 202, G - 1, 3, 4.5)
    t.mover(210, G - 1, 210, 13, 3, 5)
    t.fill(213, 14, 8, G - 14)
    t.coin(211, 16); t.coin(199, G - 3)
    t.greenie('elevator', 'Elevator Ride', 219, 12.6)
    t.sign(217, 'BOOST PADS launch you. Jump while you are fast!', 14)


def _J(t):
    t.floor(221, 20)
    t.set(223, G, '>'); t.set(224, G, '>')
    t.spikePit(227, 239)
    t.coin(233, G - 4)


def _K(t):
    t.floor(241, 21)
    t.cp(242)
    t.sign(244, 'LASERS switch on and off. Watch the flicker, then run!')
    t.fill(247, 9, 13, 4)
    t.laser(250, 13, G, 0)
    t.laser(254, 13, G, 0.6)
    t.laser(258, 13, G, 1.2)
    t.greenie('laser', 'Laser Gauntlet', 256, G - 3.5)


def _L(t):
    t.floor(262, 27)
    t.cp(263)
    t.sign(265, 'CRUMBLING platforms fall shortly after you touch them.')
    t.spikePit(268, 287)
    for x in (270, 274, 278, 282):
        t.set(x, G - 2, '~'); t.set(x + 1, G - 2, '~')
    t.coin(276.5, G - 4)
    t.greenie('crumble', 'Crumbling Heights', 278.5, G - 9)


def _M(t):
    t.floor(289, 11); t.fill(299, 0, 1, LH)
    t.sign(290, 'R = respawn at checkpoint.  Enter = restart.  H = show hitboxes.')
    t.setFinish(295)


BUILTIN_SECTIONS = [
    _sec('A', 'Basics', 0, 25, _A), _sec('B', 'Triple Jump', 25, 32, _B), _sec('C', 'Wall Jump', 57, 20, _C),
    _sec('D', 'Slide', 77, 17, _D), _sec('E', 'Long Jump', 94, 14, _E), _sec('F', 'Dive', 108, 16, _F),
    _sec('G', 'Smash', 124, 25, _G), _sec('H', 'Trampolines', 149, 37, _H), _sec('I', 'Moving Platforms', 186, 35, _I),
    _sec('J', 'Boost Pads', 221, 20, _J), _sec('K', 'Lasers', 241, 21, _K), _sec('L', 'Crumbling Platforms', 262, 27, _L),
    _sec('M', 'Finish', 289, 11, _M),
]

# The world is split into areas (the tutorial, the main game, a house...) that you
# teleport between with doors, the start menu or special greenies.
AREAS = {'Main': list(BUILTIN_SECTIONS)}
addingTo = 'Main'      # area that addChunk() adds to
areaName = 'Main'      # area being played


def area(name):
    global addingTo
    addingTo = name
    if name not in AREAS:
        AREAS[name] = []


def areaExists(name):
    return bool(AREAS.get(name))


# Greenies that take you somewhere once collected: { greenie id: area name }
GREENIE_WARPS = {}


def warpOnGreenie(id, to):
    GREENIE_WARPS[id] = to


# --- chunk codes (shared with the editor) ----------------------------
CHUNK_PREFIX = 'TREATS1:'
CHUNK_TILES = 'g^T~o'   # tiles the editor can place (o = cobblestone)


def b64encode(s):
    return base64.b64encode(s.encode('utf8')).decode('ascii')


def b64decode(s):
    return base64.b64decode(s + '=' * (-len(s) % 4)).decode('utf8')


def js_json(v):
    return json.dumps(v, separators=(',', ':'), ensure_ascii=False)


def rle(rows):
    out = []
    for row in rows:
        s, i = '', 0
        while i < len(row):
            j = i
            while j < len(row) and row[j] == row[i]:
                j += 1
            n = j - i
            s += (str(n) if n > 1 else '') + row[i]
            i = j
        out.append(s)
    return '|'.join(out)


def unRle(t, w):
    import re
    rows = []
    for r in t.split('|'):
        r = re.sub(r'(\d+)(\D)', lambda m: m.group(2) * int(m.group(1)), r)
        rows.append(r.ljust(w, '.')[:w])
    return rows


def encodeChunk(chunk):
    data = O(n=chunk.name, w=chunk.w, t=rle(chunk.rows), tr=chunk.trees, ts=chunk.treats, gr=chunk.greenies,
             cp=chunk.cps, tx=chunk.texts)
    if len(chunk.rows) != LH:
        data.h = len(chunk.rows)
    if chunk.bg and any('b' in r for r in chunk.bg):
        data.bg = rle(chunk.bg)
    if chunk.chickens:
        data.ck = chunk.chickens
    if chunk.diamonds:
        data.dm = chunk.diamonds
    if chunk.place:
        data.p = chunk.place
    if chunk.fires:
        data.fb = chunk.fires
    if chunk.clouds:
        data.cl = chunk.clouds
    if chunk.notes:
        data.nt = chunk.notes
    return CHUNK_PREFIX + b64encode(js_json(data))


def decodeChunk(code):
    code = ''.join(str(code).split())
    if not code.startswith(CHUNK_PREFIX):
        raise ValueError('Not a Treats chunk code (it should start with ' + CHUNK_PREFIX + ')')
    d = json.loads(b64decode(code[len(CHUNK_PREFIX):]))
    rows = unRle(d['t'], d['w'])
    h = d.get('h') or LH
    if len(rows) != h:
        raise ValueError('Chunk has %d rows, expected %d' % (len(rows), h))
    # older codes kept dirt background in the tile rows: move it to the background layer
    bg = unRle(d['bg'], d['w']) if d.get('bg') else [''.join(ch if ch == 'b' else '.' for ch in r) for r in rows]
    rows = [r.replace('b', '.') for r in rows]
    return O(
        name=d.get('n') or 'Custom', w=d['w'], h=h, rows=rows, bg=bg,
        trees=d.get('tr') or [], treats=d.get('ts') or [], greenies=d.get('gr') or [], cps=d.get('cp') or [],
        texts=[[t[0], t[1], t[4], t[5]] if len(t) >= 6 else t for t in (d.get('tx') or [])],
        chickens=d.get('ck') or [], diamonds=d.get('dm') or [], notes=d.get('nt') or [], place=O(d['p']) if d.get('p') else None,
        fires=d.get('fb') or [], clouds=d.get('cl') or [],
    )


# extra(t) builds hand-made things on top of the chunk (what its notes asked for).
# easy: the chunk's Easy-mode version (same size and spot), built instead of it in Easy.
def chunkSection(hard, extra=None, easy=None):
    def build(t):
        chunk = easy if difficulty == 'easy' and easy else hard
        for y, row in enumerate(chunk.rows):
            for x, ch in enumerate(row):
                if ch in CHUNK_TILES:
                    t.set(x, y, ch)
        for y, row in enumerate(chunk.bg or []):
            for x, ch in enumerate(row):
                if ch == 'b':
                    t.setBg(x, y)
        for x, y, h, r in chunk.trees:
            t.tree(x, y, h, r)
        for c in chunk.treats:
            t.coin(c[0], c[1])
        for x, y, name, id in chunk.greenies:
            t.greenie(id, name, x, y)
        for c in chunk.cps:
            t.cp(c[0], c[1])
        for x, y, s, col in chunk.texts:
            t.text(x, y, s, col)
        for c in chunk.chickens:
            t.chicken(c[0], c[1])
        for x, y, id in chunk.diamonds or []:
            t.diamond(id, x, y)
        for x, y, st in chunk.fires or []:
            t.fire(x, y, st)
        if extra:
            extra(t)
    return O(id=hard.name, name=hard.name, base=0, w=hard.w, h=hard.h, custom=True, chunk=hard, easy=easy, build=build)


# Drop an editor chunk into the current area. Where it goes (keyword arguments):
#   (nothing)               the right end of the main row (or where it was placed in the editor)
#   before='Name' / after='Name'      in the main row, next to another chunk
#   above='Name', dx / below='Name', dx    stacked on / under another chunk
#   frm='Name', dx, dy      dx, dy tiles from another chunk's top-left corner
#   at=[x, y]               exact tiles
# extra=f(t) adds hand-made things; easy='TREATS1:...' is the chunk's Easy-mode version.
def addChunk(code, before=None, after=None, above=None, below=None, frm=None, dx=0, dy=None, at=None, extra=None, easy=None):
    try:
        chunk = decodeChunk(code)
    except Exception as e:
        print('addChunk skipped a bad code:', e)
        return None
    easyc = None
    if easy:
        try:
            easyc = decodeChunk(easy)
            for i, g in enumerate(easyc.greenies):
                h = next((o for o in chunk.greenies if o[2] == g[2]), None) or (chunk.greenies[i] if i < len(chunk.greenies) else None)
                if h:
                    g[3] = h[3]
            for i, d in enumerate(easyc.diamonds):
                if i < len(chunk.diamonds):
                    d[2] = chunk.diamonds[i][2]
        except Exception as e:
            print('addChunk skipped a bad easy code:', e)
            easyc = None
    sec = chunkSection(chunk, extra, easyc)
    near = frm or above or below
    if at:
        sec.place = O(at=at)
    elif near:
        ref = next((o for o in AREAS[addingTo] if o.id == near), None)
        sec.place = O(frm=near, dx=dx or 0,
                      dy=dy if dy is not None else (-chunk.h if above else (secH(ref) if ref else LH) if below else 0))
    elif not before and not after and chunk.place:
        sec.place = O(frm=chunk.place.n, dx=chunk.place.x, dy=chunk.place.y)
    if sec.place:
        AREAS[addingTo].append(sec)
        return sec
    order = AREAS[addingTo]
    ref = before or after
    i = next((k for k, s in enumerate(order) if s.id == ref), -1)
    if i < 0:
        i = len(order)
    elif after:
        i += 1
    order.insert(i, sec)
    return sec


# A hand-built section (not from the editor) for the current area: name, w, h, build(t), place.
def addSection(name, w, build, h=None, place=None):
    AREAS[addingTo].append(O(id=name, name=name, base=0, w=w, h=h, custom=True, build=build,
                             place=O(place) if place else None))


# Throw away the built-in sections (and any areas) so world.py can build everything from chunks.
def clearWorld():
    global addingTo
    AREAS.clear()
    AREAS['Main'] = []
    addingTo = 'Main'


# "Play test" from the command line: python main.py --test TREATS1:... (that chunk alone, between two pads).
TEST_CODE = sys.argv[sys.argv.index('--test') + 1] if '--test' in sys.argv[:-1] else None
if TEST_CODE and TEST_CODE.startswith('@'):   # --test @file: the code is in that file (the editor's Play)
    with open(TEST_CODE[1:], encoding='utf8') as _f:
        TEST_CODE = _f.read().strip()


def _start_pad(t):
    t.floor(0, 6); t.fill(0, 0, 1, LH); t.setSpawn(3)


def _end_pad(t):
    t.floor(0, 10); t.fill(9, 0, 1, LH); t.setFinish(5)


TEST_PADS = [
    O(id='Start', name='Start', pad=True, base=0, w=6, build=_start_pad),
    O(id='End', name='End', pad=True, base=0, w=10, build=_end_pad),
]


# Where each section sits, in tiles: the main row runs left to right with the bottoms
# lined up, and placed sections go where they say (possibly above / below).
# Returns {id(section): [x, y]} (the editor's Generate world uses it too).
def layoutSections(order):
    pos = {}
    rowX = [0]

    def inRow(sec):
        pos[id(sec)] = [rowX[0], LH - secH(sec)]
        rowX[0] += sec.w
    for sec in order:
        if not sec.place:
            inRow(sec)
    for _ in range(len(order)):
        for sec in order:
            if not sec.place or id(sec) in pos:
                continue
            p = sec.place
            ref = next((o for o in order if o.id == p.frm and id(o) in pos), None) if p.frm else None
            if p.at:
                pos[id(sec)] = list(p.at)
            elif ref:
                pos[id(sec)] = [pos[id(ref)][0] + p.dx, pos[id(ref)][1] + p.dy]
    for sec in order:
        if id(sec) not in pos:
            inRow(sec)   # its anchor is missing
    return pos


def buildLevel():
    global LW, GH, grid, bgGrid, signs, checkpoints, treats, greenies, trees, texts, movers, lasers
    global chickens, houses, doors, npcs, props, diamonds, sectionSpans, switches, secrets, links, portals
    global activeSecret, views, camLikes, fireSpawners, fireballs, backdrop, dimness, turkeys, spawn, finish
    global baseGrid, secretMap, endlessWalls, wingTreats, slabs
    order = AREAS.get(areaName) or []
    if TEST_CODE:
        try:
            order = [TEST_PADS[0], chunkSection(decodeChunk(TEST_CODE)), TEST_PADS[1]]
        except Exception as e:
            print('Bad test code:', e)
    pos = layoutSections(order)
    minX, minY, maxX, maxY = 0, 0, 0, LH
    for sec in order:
        x, y = pos[id(sec)]
        minX = min(minX, x); minY = min(minY, y); maxX = max(maxX, x + sec.w); maxY = max(maxY, y + secH(sec))
    LW = int(maxX - minX); GH = int(maxY - minY)
    grid = [['.'] * LW for _ in range(GH)]
    bgGrid = [[False] * LW for _ in range(GH)]
    signs = []; checkpoints = []; treats = []; greenies = []; trees = []; texts = []; movers = []; lasers = []
    chickens = []; houses = []; doors = []; npcs = []; props = []; diamonds = []; sectionSpans = []
    switches = []; secrets = []; links = []; portals = {}; activeSecret = 0; views = []; camLikes = []
    fireSpawners = []; fireballs = []
    endlessWalls = []; wingTreats = []; slabs = []
    backdrop = 'sky'; dimness = 0; turkeys = []
    spawn = None; finish = None   # a world made only of chunks may have neither
    crumbleState.clear(); trampAnim.clear()
    for s in order:
        ox, oy = int(pos[id(s)][0] - minX), int(pos[id(s)][1] - minY)
        s.build(sectionTools(ox - s.base, oy))
        sectionSpans.append(O(id=s.id, name=s.name, custom=bool(s.custom), pad=bool(s.pad), x0=ox, x1=ox + s.w, y0=oy, y1=oy + secH(s)))
    if not spawn:
        # stand Charlie on the first solid tile in column 3 of the main row, counting down from its top
        first = next((o for o in order if not o.place), order[0] if order else None)
        ty = int((pos[id(first)][1] if first else 0) - minY)
        while ty < GH - 1 and not isSolidChar(grid[ty][3 - minX]):
            ty += 1
        spawn = O(x=(3 - minX) * T + T / 2, y=ty * T)
    baseGrid = [r[:] for r in grid]
    secretMap = [0] * (LW * GH)
    for i, z in enumerate(secrets):
        for k in z.cells:
            if 0 <= k < len(secretMap):
                secretMap[k] = i + 1

    def secretId(name):
        return next((i for i, z in enumerate(secrets) if z.name == name), -1) + 1
    for z in secrets:
        z.alsoIds = [secretId(n) for n in z.also]
    for v in views:
        v.whenIds = [secretId(n) for n in v.when]
        v.showId = secretId(v.show)


# --- trees: the trunk is a rotated box you can stand on, wall jump off, etc.
TRUNK_W = 18


def makeTree(bx, by, h, rot):
    ux, uy, nx, ny, hw = math.sin(rot), -math.cos(rot), math.cos(rot), math.sin(rot), TRUNK_W / 2
    tx, ty = bx + ux * h, by + uy * h
    poly = [[bx - nx * hw, by - ny * hw], [bx + nx * hw, by + ny * hw], [tx + nx * hw, ty + ny * hw], [tx - nx * hw, ty - ny * hw]]
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    box = O(x=min(xs), y=min(ys), w=max(xs) - min(xs), h=max(ys) - min(ys))
    return O(bx=bx, by=by, h=h, rot=rot, tx=tx, ty=ty, poly=poly, box=box, axes=[[1, 0], [0, 1], [ux, uy], [nx, ny]],
             seed=abs(math.floor(bx * 7 + by * 13)) % 2147483646 + 1)


# Separating-axis test between a rect and a trunk. Returns how to push the rect out
# ({ nx, ny } unit direction, d depth) or None when they don't touch.
def trunkPush(x, y, w, h, tr):
    b = tr.box
    if not overlap(x, y, w, h, b.x, b.y, b.w, b.h):
        return None
    rc = ((x, y), (x + w, y), (x + w, y + h), (x, y + h))
    best = None
    for ax, ay in tr.axes:
        a0, a1, b0, b1 = INF, -INF, INF, -INF
        for px, py in rc:
            p = px * ax + py * ay
            a0 = min(a0, p); a1 = max(a1, p)
        for px, py in tr.poly:
            p = px * ax + py * ay
            b0 = min(b0, p); b1 = max(b1, p)
        o = min(a1 - b0, b1 - a0)
        if o <= 0:
            return None
        if not best or o < best.d:
            s = -1 if a0 + a1 < b0 + b1 else 1
            best = O(nx=ax * s, ny=ay * s, d=o)
    return best


SOLID_CHARS = set('#gX~T><wpklfo')


def isSolidChar(c):
    return c in SOLID_CHARS


def tileAt(tx, ty):
    if tx < 0 or tx >= LW:
        return '#'
    if ty < 0 or ty >= GH:
        return '.'
    return grid[ty][tx]


def solidAt(tx, ty):
    return tileAt(tx, ty) in SOLID_CHARS


# Solid for Charlie from the sides and below. Crumble blocks aren't: he jumps up through
# them and only lands on them from above.
def wallAt(tx, ty):
    c = tileAt(tx, ty)
    return c != '~' and c in SOLID_CHARS


# Ground a spike can sit on: anything you can stand on without dying.
def groundAt(tx, ty):
    c = tileAt(tx, ty)
    return isSolidChar(c) or c == 'c' or any(trunkPush(tx * T + 4, ty * T + 4, T - 8, T - 8, tr) for tr in (trees or []))


# Which way a spike points (a turn in radians, 0 = up).
def spikeTurn(tx, ty):
    if groundAt(tx, ty + 1):
        return 0
    if groundAt(tx, ty - 1):
        return math.pi
    if groundAt(tx + 1, ty):
        return -math.pi / 2
    if groundAt(tx - 1, ty):
        return math.pi / 2
    return 0


# The part of a spike's tile that hurts: the points, on the side away from its ground.
def spikeBox(tx, ty):
    x, y, t = tx * T, ty * T, spikeTurn(tx, ty)
    if t == math.pi:
        return (x + 4, y, T - 8, T - 14)
    if t == -math.pi / 2:
        return (x + 14, y + 4, T - 14, T - 8)
    if t == math.pi / 2:
        return (x, y + 4, T - 14, T - 8)
    return (x + 4, y + 14, T - 8, T - 14)


def rectHitsSolid(x, y, w, h):
    x0, x1 = math.floor(x / T), math.floor((x + w - 0.001) / T)
    y0, y1 = math.floor(y / T), math.floor((y + h - 0.001) / T)
    for ty in range(y0, y1 + 1):
        for tx in range(x0, x1 + 1):
            if wallAt(tx, ty):
                return True
    return any(trunkPush(x, y, w, h, tr) for tr in trees)


def overlap(ax, ay, aw, ah, bx, by, bw, bh):
    return ax < bx + bw and ax + aw > bx and ay < by + bh and ay + ah > by


def approach(v, target, amt):
    return min(v + amt, target) if v < target else max(v - amt, target)


# ---------------------------------------------------------------------
#  Game state
# ---------------------------------------------------------------------
P = O()
respawnPoint = None
simTime = 0.0
runTime = 0.0
deaths = 0
finished = False
# The last checkpoint you touched, in whichever area: { area, spot }.
lastCp = None
# Each area's tiles as you left them. Dying and restarting put an area back the way it was built.
areaGrids = {}
camX = camY = 0.0
shake = 0.0
debug = False
showTimer = False   # T toggles the timer
particles, popups = [], []
celebrate = None    # { g: greenie, t } while the "You got a Greenie!" moment plays

# Greenies you've ever collected are saved (save_data.json), like moons in a save file.
GREENIE_KEY = 'treats.greenies'
greeniesGot = set() if TEST_CODE else set(store_get(GREENIE_KEY) or [])


def saveGreenies():
    if TEST_CODE:
        return
    store_set(GREENIE_KEY, list(greeniesGot))


def resetPlayer(at):
    P.update(
        x=at.x - P_W / 2, y=at.y - H_STAND, w=P_W, h=H_STAND,
        vx=0, vy=0, facing=1, onGround=False, state='normal',
        coyote=0, jumpBuf=0, wallLock=0, diveReady=True, canCut=False,
        combo=0, landT=1, smashLand=0, slideLock=0, ride=None,
        flip=0, flipping=False, runPhase=0, wallSliding=False, wallDir=0,
        deadT=0, squash=0, squashV=0, eightPack=False, wings=False, immune=0,
    )


# How far up and down the chunks go at world x px: { top, bot } in pixels (None if none).
def columnSpan(px):
    top, bot = INF, -INF
    for s in sectionSpans:
        if s.x0 * T <= px < s.x1 * T:
            top = min(top, s.y0 * T); bot = max(bot, s.y1 * T)
    return None if top == INF else O(top=top, bot=bot)


camSpan = None   # the chunk span the camera last stayed inside


def spanAt(px):
    global camSpan
    camSpan = columnSpan(px) or camSpan or O(top=0, bot=GH * T)
    return camSpan


# Below the lowest chunk under you is the void.
def voidLine(px):
    return spanAt(px).bot


def columnBottom(px):
    sp = columnSpan(px)
    return sp.bot if sp else GH * T


# The chunk the camera keeps to: the one Charlie is in.
camChunk = None


def chunkAt(px, py):
    global camChunk
    inside = next((o for o in sectionSpans if o.x0 * T <= px < o.x1 * T and o.y0 * T <= py < o.y1 * T), None)
    if inside:
        camChunk = inside
    return camChunk or O(y0=0, y1=GH)


# Where the camera wants to be up and down: following Charlie, but never past the top
# or bottom border of his chunk.
def camYFor(px, feet):
    for b in camLikes:
        if px < b.x or px >= b.x + b.w or feet <= b.y or feet > b.y + b.h:
            continue
        best = None
        for frm, to in b.pairs:
            p, q = portals.get(frm), portals.get(to)
            if not p or not q:
                continue
            d = abs(p[0] * T - px)
            if not best or d < best.d:
                best = O(d=d, dx=(q[0] - p[0]) * T, dy=(q[1] - p[1]) * T)
        if best:
            return camYFor(px + best.dx, feet + best.dy) - best.dy
    c = chunkAt(px, feet - 1)
    return max(c.y0 * T, min(c.y1 * T - VIEW_H, feet - 17 - VIEW_H * 0.58))


# Point the camera straight at a spot (after restarts and teleports).
def snapCamera(at):
    global camSpan, camChunk, camX, camY
    camSpan = None; camChunk = None
    spanAt(at.x)
    camX = max(0, min(LW * T - VIEW_W, at.x - VIEW_W / 2))
    camY = camYFor(at.x, at.y)


def restartLevel():
    global respawnPoint, lastCp, areaGrids, deaths, runTime, finished, particles, popups, celebrate
    global stamina, inhale, slurps, thrown
    buildLevel()
    respawnPoint = spawn; lastCp = None; areaGrids = {}
    resetPlayer(spawn)
    deaths = 0; runTime = 0; finished = False
    particles = []; popups = []; celebrate = None
    stamina = 0; inhale = None; slurps = []; thrown = []
    snapCamera(spawn)


# Going to another area (door, menu, warp greenie) builds it fresh.
# `arrive` is the id of a door in that area to come out of (else its spawn point).
# `spot` is a saved location ({ at, cp } from a save code) to come back to instead.
def teleport(to, arrive=None, spot=None):
    global areaName, grid, respawnPoint, lastCp, particles, celebrate, inhale, slurps, thrown, flyingLegs
    if grid and areaName in AREAS:
        areaGrids[areaName] = [['~' if c == 'c' else c for c in r] for r in grid]
    areaName = to
    buildLevel()
    kept = areaGrids.get(to)
    if kept and len(kept) == GH and len(kept[0]) == LW:
        grid = [r[:] for r in kept]
    d = next((o for o in doors if o.id == arrive), None) if arrive else None
    respawnPoint = O(x=d.x + d.w / 2, y=d.y + d.h) if d else spawn
    at = respawnPoint
    if spot:
        if spot.get('cp'):
            lastCp = O(area=spot.get('ca') or to, spot=spot['cp'])
        at = spotAt(spot.get('at')) or respawnPoint
    # your checkpoint is in this area: respawn there, with its flag up again
    cp = spotAt(lastCp.spot) if lastCp and lastCp.area == to else None
    if cp:
        respawnPoint = cp
        for c in checkpoints:
            c.active = abs(c.x - cp.x) < 2 and abs(c.y - cp.y) < 2
    pk, wg = P.eightPack, P.wings
    resetPlayer(at)
    P.eightPack = pk; P.wings = wg   # the eight pack and wings come along, like stamina
    particles = []; celebrate = None; inhale = None; slurps = []; thrown = []; flyingLegs = []
    snapCamera(at)


# A quick fade to black and back, with the teleport in the dark middle.
warp = None   # { to, arrive, spot, t, done }
WARP_TIME = 0.35


# white: fade through white instead of black
def startWarp(to, arrive=None, spot=None, white=False):
    global warp
    if not warp:
        warp = O(to=to, arrive=arrive, spot=spot, white=white, t=0, done=False)


def respawn():
    global grid, stamina, celebrate, inhale, slurps, thrown
    if lastCp and lastCp.area != areaName and areaExists(lastCp.area):
        # your checkpoint is in another area: back you go (that area is built fresh)
        frm = areaName
        teleport(lastCp.area, None, {'at': lastCp.spot})
        # a death puts both areas back the way they were built
        areaGrids.pop(frm, None); areaGrids.pop(areaName, None)
        grid = [r[:] for r in baseGrid]
        P.eightPack = False; P.wings = False; stamina = 0
        return
    resetPlayer(respawnPoint)
    celebrate = None
    # the world goes back the way it was built; collected greenies come back as ghosts
    grid = [r[:] for r in baseGrid]
    for c in treats:
        c.taken = False
    for tk in turkeys:
        tk.t = 0
    for w in wingTreats:
        w.t = 0; w.d = 0
    for sl in slabs:   # (the grid reset put it back up)
        sl.update(p=0, row=0, moving=False, cells=None); sl.under.clear()
    for g in greenies:
        g.taken = False
    stamina = 0
    crumbleState.clear()
    for ck in chickens:
        resetChicken(ck)
    inhale = None; slurps = []; thrown = []


def updateLinks():
    global camX, camY, camChunk
    if P.state == 'dead':
        return
    cx, cy = P.x + P.w / 2, P.y + P.h / 2
    for l in links:
        a, b = portals.get(l.frm), portals.get(l.to)
        if not a or not b or not (l.x <= cx < l.x + l.w and l.y <= cy < l.y + l.h):
            continue
        # same spot in the other doorway; the camera jumps along so nothing seems to change
        dx, dy = (b[0] - a[0]) * T, (b[1] - a[1]) * T
        P.x += dx; P.y += dy; camX += dx; camY += dy; P.ride = None
        camChunk = None
        return


def updateSwitches():
    global shake
    for i in range(len(switches) - 1, -1, -1):
        sw = switches[i]
        # Charlie's head hitting it from below
        if P.state == 'dead' or P.onGround or P.vy > 0 or not overlap(P.x, P.y, P.w, P.h, sw.x, sw.y, sw.w, sw.h + 2):
            continue
        for tx, ty in sw.cells:
            grid[ty][tx] = '.'; baseGrid[ty][tx] = '.'
            for k in range(4):
                spawnParticle(tx * T + random() * T, ty * T + T / 2, (random() - 0.5) * 200, -random() * 150, 0.9,
                              4 + random() * 3, '#b07a45' if k % 2 else '#7d5129', 900)
        stuff.flags[sw.id] = True; saveStuff()
        switches.pop(i)
        shake = 6


# Spikes, lasers, chickens, fireballs. With wings or an eight pack you lose that instead of
# your life (wings first: they burst into feathers; a turkey leg flies out of you).
def hurt():
    global shake
    if P.state == 'dead' or P.immune > 0:
        return
    if not P.eightPack and not P.wings:
        return die()
    P.immune = PHYS.hurtImmune
    P.vy = min(P.vy, -420)   # a little hop up, off whatever got you
    shake = 5
    if P.wings:
        P.wings = False
        for i in range(16):
            spawnParticle(P.x + P.w / 2, P.y + P.h * 0.4, (random() - 0.5) * 320, -random() * 260, 1 + random() * 0.6, 4,
                          '#ffffff' if i % 3 else '#d9dee6', 250)
        return
    P.eightPack = False
    flyingLegs.append(O(x=P.x + P.w / 2, y=P.y + P.h / 2, vx=-P.facing * 160 + (random() - 0.5) * 80, vy=-520, rot=0,
                        spin=(-1 if random() < 0.5 else 1) * 9, t=0))


flyingLegs = []   # turkey legs knocked out of Charlie


def updateFlyingLegs(dt):
    global flyingLegs
    for l in flyingLegs:
        l.vy += PHYS.gravity * dt; l.x += l.vx * dt; l.y += l.vy * dt; l.rot += l.spin * dt; l.t += dt
    flyingLegs = [l for l in flyingLegs if l.t < 1.6]


def drawTurkeyImg(x, y, h, rot, alpha=1):
    if not turkeyImg.naturalWidth:
        return
    w = h * turkeyImg.naturalWidth / turkeyImg.naturalHeight
    ctx.save(); ctx.globalAlpha = alpha; ctx.translate(x, y); ctx.rotate(rot)
    ctx.drawImage(turkeyImg, -w / 2, -h / 2, w, h)
    ctx.restore()


def die():
    global deaths, shake
    if P.state == 'dead':
        return
    P.eightPack = False; P.wings = False; P.immune = 0
    cx, cy = P.x + P.w / 2, P.y + P.h / 2
    for i in range(26):
        a, s = random() * math.pi * 2, 120 + random() * 380
        spawnParticle(cx, cy, math.cos(a) * s, math.sin(a) * s - 150, 0.6 + random() * 0.5, 3 + random() * 3,
                      '#f4ece8' if i % 3 else '#e8a3a3', 900)
    P.state = 'dead'; P.deadT = 0.7; P.vx = P.vy = 0
    deaths += 1; shake = 8


# ---------------------------------------------------------------------
#  Effects
# ---------------------------------------------------------------------
def spawnParticle(x, y, vx, vy, life, size, col, grav=600):
    particles.append(O(x=x, y=y, vx=vx, vy=vy, life=life, max=life, size=size, color=col, grav=grav))


def dust(x, y, n, spread=120, up=80):
    for _ in range(n):
        spawnParticle(x + (random() - 0.5) * 16, y - 2, (random() - 0.5) * spread * 2, -random() * up,
                      0.3 + random() * 0.3, 2 + random() * 3, 'rgba(90,96,108,0.8)', 300)


# ---------------------------------------------------------------------
#  Player helpers
# ---------------------------------------------------------------------
def canStand():
    return not rectHitsSolid(P.x, P.y + P.h - H_STAND, P.w, H_STAND)


def setLow(low):
    if low and P.h != H_LOW:
        P.y += H_STAND - H_LOW; P.h = H_LOW
    elif not low and P.h != H_STAND:
        if not canStand():
            return False
        P.y -= H_STAND - H_LOW; P.h = H_STAND
    return True


def touchingWall(d):
    if d > 0:
        return rectHitsSolid(P.x + P.w, P.y + 4, 1, P.h - 8)
    return rectHitsSolid(P.x - 1, P.y + 4, 1, P.h - 8)


# Wall near enough to wall-jump off: -1 left, 1 right, 0 none.
def wallContact():
    l = rectHitsSolid(P.x - 4, P.y + 4, 4, P.h - 8)
    r = rectHitsSolid(P.x + P.w, P.y + 4, 4, P.h - 8)
    if l and r:
        return P.facing
    return -1 if l else 1 if r else 0


# Multiplier when Charlie has an eight pack (1 otherwise).
def pack(m):
    return m if P.eightPack else 1


def doJump(kind):
    P.onGround = False; P.coyote = 0; P.jumpBuf = 0; P.canCut = True; P.ride = None
    fx, fy = P.x + P.w / 2, P.y + P.h
    if kind == 'smash':
        P.vy = -PHYS.smashJump * pack(PHYS.packJump); P.combo = 0; P.smashLand = 0
        dust(fx, fy, 14, 200, 140)
    elif kind == 'slide':
        P.vy = -PHYS.slideJumpY * pack(PHYS.packJump)
        P.vx = sign(P.vx) * min(abs(P.vx) * PHYS.slideJumpMult, PHYS.slideJumpCap * pack(PHYS.packJumpX))
        P.combo = 0
        dust(fx, fy, 6)
    else:
        if P.combo > 0 and P.landT <= PHYS.tripleWindow and abs(P.vx) > 100:
            P.combo = P.combo % 3 + 1
        else:
            P.combo = 1
        P.vy = -PHYS.jump[P.combo - 1] * pack(PHYS.packJump)
        if P.combo == 3:
            P.flipping = True; P.flip = 0
        dust(fx, fy, 4)
    if kind != 'slide':
        P.vx *= pack(PHYS.packJumpX)
    P.state = 'normal'
    P.squash = -0.55; P.squashV = 0


def wallJump(wd):
    P.vx = -wd * PHYS.wallJumpX; P.vy = -PHYS.wallJumpY
    P.facing = -wd; P.wallLock = PHYS.wallJumpLock
    P.jumpBuf = 0; P.canCut = True; P.combo = 0; P.diveReady = True
    P.state = 'normal'; P.flipping = False
    dust(P.x + P.w if wd > 0 else P.x, P.y + P.h / 2, 6, 60, 60)


def dive(d):
    d = d or P.facing
    P.facing = d
    dx = PHYS.diveX * pack(PHYS.packDiveX)
    P.vx = d * max(abs(P.vx) + PHYS.diveBonus, dx) if sign(P.vx) == d else d * dx
    P.vy = -PHYS.diveY
    P.state = 'dive'; P.diveReady = False; P.jumpBuf = 0; P.canCut = False; P.flipping = False


def smash():
    P.state = 'smash'; P.vy = PHYS.smashSpeed * pack(PHYS.packSmash); P.vx *= 0.2
    P.canCut = False; P.flipping = False


def startSlide():
    P.state = 'slide'; setLow(True); P.slideLock = 0.3
    s = sign(P.vx) or P.facing
    P.facing = s
    spd = abs(P.vx)
    P.vx = s * max(spd, min(spd + PHYS.slideBoost, PHYS.slideMaxBoost))
    dust(P.x + P.w / 2, P.y + P.h, 6)


def bounce(tx, ty):
    wasSmash = P.state == 'smash'
    P.vy = -(PHYS.trampolineSmash if wasSmash else PHYS.trampolineHeld if held('jump') else PHYS.trampoline)
    P.onGround = False; P.state = 'normal'; P.diveReady = True; P.canCut = False; P.combo = 0; P.flipping = False
    setLow(False)
    trampAnim['%d,%d' % (tx, ty)] = 1
    P.squash = -0.6; P.squashV = 0


def onLand(impact):
    global shake
    P.diveReady = True; P.landT = 0; P.flipping = False
    fx, fy = P.x + P.w / 2, P.y + P.h
    if P.state == 'smash':
        P.state = 'normal'; P.smashLand = PHYS.smashJumpWindow; P.combo = 0
        shake = 6
        dust(fx, fy, 18, 260, 120)
    elif P.state == 'dive':
        # dive lands into a slide, keeping the momentum
        P.state = 'slide'; setLow(True); P.slideLock = 0.3
        P.vx = P.facing * max(abs(P.vx), PHYS.slideMinSpeed + 80)
        dust(fx, P.y + P.h, 8)
    elif impact > 350:
        dust(fx, fy, 5)
    P.squash = max(P.squash, min(0.95, impact / 1000)); P.squashV = 0


# ---------------------------------------------------------------------
#  Collision movement
# ---------------------------------------------------------------------
def moveX(dx):
    if dx == 0:
        return False
    P.x += dx
    x0, x1 = math.floor(P.x / T), math.floor((P.x + P.w - 0.001) / T)
    y0, y1 = math.floor(P.y / T), math.floor((P.y + P.h - 0.001) / T)
    if dx > 0:
        for tx in range(x0, x1 + 1):
            for ty in range(y0, y1 + 1):
                if wallAt(tx, ty):
                    P.x = tx * T - P.w; P.vx = 0
                    return True
    else:
        for tx in range(x1, x0 - 1, -1):
            for ty in range(y0, y1 + 1):
                if wallAt(tx, ty):
                    P.x = (tx + 1) * T; P.vx = 0
                    return True
    return False


def moveY(dy):
    if dy == 0:
        return
    prevBottom = P.y + P.h
    P.y += dy
    x0, x1 = math.floor(P.x / T), math.floor((P.x + P.w - 0.001) / T)
    y0, y1 = math.floor(P.y / T), math.floor((P.y + P.h - 0.001) / T)
    if dy > 0:
        for ty in range(y0, y1 + 1):
            hit, hitC = -1, ''
            for tx in range(x0, x1 + 1):
                c = tileAt(tx, ty)
                if c == 'X' and P.state == 'smash':
                    breakBlock(tx, ty)
                    continue
                if c == '~' and prevBottom > ty * T + 0.5:
                    continue   # coming up through it: not a floor yet
                if isSolidChar(c) and (hit < 0 or c == 'T'):
                    hit = tx; hitC = c
            if hit >= 0:
                P.y = ty * T - P.h
                if hitC == 'T':
                    bounce(hit, ty)
                else:
                    P.vy = 0; P.onGround = True
                return
        # moving platforms (one-way from above)
        for m in movers:
            if P.x + P.w > m.x and P.x < m.x + m.w and prevBottom <= m.y + 4 and P.y + P.h >= m.y:
                P.y = m.y - P.h; P.vy = 0; P.onGround = True; P.ride = m
                return
    else:
        for ty in range(y1, y0 - 1, -1):
            for tx in range(x0, x1 + 1):
                if wallAt(tx, ty):
                    P.y = (ty + 1) * T; P.vy = 0; P.canCut = False
                    return


# Push Charlie out of any tree trunk he's overlapping.
def resolveTrunks():
    for tr in trees:
        p = trunkPush(P.x, P.y, P.w, P.h, tr)
        if not p:
            continue
        if p.ny < -0.5:
            # standing on it: push straight up so you don't slowly slide down a leaning trunk
            P.y -= p.d / -p.ny
            if P.vy > 0:
                P.vy = 0
            P.onGround = True
        elif p.ny > 0.5:
            P.y += p.d / p.ny
            if P.vy < 0:
                P.vy = 0; P.canCut = False
        else:
            P.x += p.nx * p.d; P.y += p.ny * p.d
            if sign(P.vx) == -sign(p.nx):
                P.vx = 0
            if P.state == 'dive':
                P.state = 'normal'


def breakBlock(tx, ty):
    global shake
    if tileAt(tx, ty) != 'X':
        return
    grid[ty][tx] = '.'
    # cracked blocks shatter as a connected group
    breakBlock(tx - 1, ty); breakBlock(tx + 1, ty); breakBlock(tx, ty - 1); breakBlock(tx, ty + 1)
    shake = max(shake, 5)
    for _ in range(10):
        spawnParticle(tx * T + random() * T, ty * T + random() * T, (random() - 0.5) * 400, -random() * 300, 0.7,
                      3 + random() * 4, '#8d6e4f', 1200)


# ---------------------------------------------------------------------
#  Player update
# ---------------------------------------------------------------------
def updatePlayer(dt):
    global warp
    if P.state == 'dead':
        P.deadT -= dt
        if P.deadT <= 0:
            respawn()
        return
    dir = (1 if held('right') else 0) - (1 if held('left') else 0)
    D = held('down')
    if pressed('up') and P.onGround:
        d = next((d for d in doors if overlap(P.x, P.y, P.w, P.h, d.x + 4, d.y, d.w - 8, d.h)), None)
        if d:
            # a door to an area that isn't built yet just rattles
            if d.here:
                if not warp:
                    warp = O(local=d, t=0, done=False)
            elif areaExists(d.to):
                startWarp(d.to, d.arrive)
            else:
                d.lockedT = 1.4
            return
        p = next((p for p in props if opensUI(p) and overlap(P.x, P.y, P.w, P.h, p.x, p.y, p.w, p.h)), None)
        if p:
            openUI(p.kind)
            return
    jumpPressed, divePressed, downPressed = pressed('jump'), pressed('dive'), pressed('down')

    P.coyote = PHYS.coyote if P.onGround else P.coyote - dt
    P.jumpBuf = (PHYS.smashJumpBuffer if P.state == 'smash' else PHYS.jumpBuffer) if jumpPressed else P.jumpBuf - dt
    P.wallLock -= dt; P.smashLand -= dt; P.slideLock -= dt
    if P.onGround:
        P.landT += dt
        if P.landT > PHYS.tripleWindow:
            P.combo = 0

    # --- slide / crouch transitions
    if P.onGround and P.state == 'normal':
        if (D or divePressed) and abs(P.vx) > PHYS.slideMinSpeed:
            startSlide()
        elif D:
            P.state = 'crouch'; setLow(True)
    if P.state in ('slide', 'crouch'):
        if not P.onGround and P.coyote <= 0:
            if setLow(False):
                P.state = 'normal'
        elif P.state == 'slide':
            if abs(P.vx) < PHYS.slideMinSpeed:
                P.state = 'crouch'
            elif not D and P.slideLock <= 0 and setLow(False):
                P.state = 'normal'
        elif not D and setLow(False):
            P.state = 'normal'

    # --- horizontal movement
    def accelerate(d, accel, turn, friction, overDecel):
        if d != 0 and sign(P.vx) == -d:
            P.vx += d * turn * dt
        elif abs(P.vx) > PHYS.runMax:
            P.vx = approach(P.vx, sign(P.vx) * PHYS.runMax, overDecel * dt)
        elif d != 0:
            P.vx = approach(P.vx, d * PHYS.runMax, accel * dt)
        else:
            P.vx = approach(P.vx, 0, friction * dt)
    if P.state == 'slide':
        P.vx = approach(P.vx, 0, PHYS.slideFriction * dt)
    elif P.state == 'crouch':
        P.vx = approach(P.vx, dir * PHYS.crouchSpeed, PHYS.groundFriction * dt)
        if dir:
            P.facing = dir
    elif P.state == 'smash':
        P.vx = approach(P.vx, 0, 2000 * dt)
    elif P.state == 'dive':
        if dir and sign(P.vx) != dir:
            P.vx += dir * 500 * dt   # can only brake a dive
    elif P.onGround:
        accelerate(dir, PHYS.runAccel, PHYS.turnAccel, PHYS.groundFriction, PHYS.groundOverDecel)
        if dir:
            P.facing = dir
    else:
        if P.wallLock > 0:
            accelerate(0, 0, 0, 0, PHYS.airOverDecel)
        else:
            accelerate(dir, PHYS.airAccel, PHYS.airTurnAccel, PHYS.airDrag, PHYS.airOverDecel)
            if dir:
                P.facing = dir

    # --- jump / wall jump / dive
    if P.jumpBuf > 0:
        if P.onGround or P.coyote > 0:
            if P.state in ('slide', 'crouch'):
                sliding = P.state == 'slide'
                if setLow(False):
                    doJump('smash' if P.smashLand > 0 else 'slide' if sliding else 'normal')
            elif P.state != 'smash':
                doJump('smash' if P.smashLand > 0 else 'normal')
        elif P.state != 'smash':
            wd = wallContact()
            if wd != 0 and P.h == H_STAND:
                wallJump(wd)
            elif jumpPressed and P.diveReady and P.state == 'normal':
                dive(dir)
    if divePressed and not P.onGround and P.coyote <= 0 and P.diveReady and P.state == 'normal':
        dive(dir)
    if downPressed and not P.wings and not P.onGround and P.coyote <= 0 and P.state in ('normal', 'dive'):
        smash()

    # --- variable jump height
    if P.canCut and P.vy < 0 and not held('jump'):
        P.vy *= PHYS.jumpCut; P.canCut = False
    if P.vy >= 0:
        P.canCut = False

    # --- gravity + wall slide
    g = PHYS.diveGravity * pack(PHYS.packDiveGravity) if P.state == 'dive' else PHYS.gravity
    maxFall = PHYS.smashMaxFall * pack(PHYS.packSmash) if P.state == 'smash' else PHYS.maxFall
    if P.wings and not P.onGround:
        # wings: no falling; W flies up, S flies down, neither hovers
        v = (1 if held('down') else 0) - (1 if held('up') else 0)
        P.vy = approach(P.vy, v * PHYS.wingSpeed, PHYS.wingAccel * dt)
    else:
        P.vy = min(P.vy + g * dt, maxFall)
    P.wallSliding = False
    if not P.onGround and P.state == 'normal' and dir != 0 and P.vy > 0 and touchingWall(dir):
        P.wallSliding = True; P.wallDir = dir; P.facing = -dir; P.flipping = False
        P.vy = min(P.vy, PHYS.wallSlideMax)
        if random() < 0.3:
            spawnParticle(P.x + P.w if dir > 0 else P.x, P.y + 6, -dir * 30, -20, 0.3, 2, 'rgba(90,96,108,0.7)', 0)

    # --- ride moving platform
    if P.ride and P.onGround:
        moveX(P.ride.dx); P.y += P.ride.dy

    # --- move with collision (substepped so fast moves don't tunnel)
    wasGround, impact = P.onGround, P.vy
    P.onGround = False; P.ride = None
    n = max(1, math.ceil(max(abs(P.vx), abs(P.vy)) * dt / 6))
    for _ in range(n):
        if moveX(P.vx * dt / n) and P.state == 'dive':
            P.state = 'normal'
        moveY(P.vy * dt / n)
        resolveTrunks()
    if P.onGround and not wasGround:
        onLand(impact)

    # --- ground tiles: boost pads + crumbles
    if P.onGround and not P.ride:
        fy = math.floor((P.y + P.h + 1) / T)
        x0, x1 = math.floor(P.x / T), math.floor((P.x + P.w - 0.001) / T)
        for tx in range(x0, x1 + 1):
            c = tileAt(tx, fy)
            if c == '>' and P.vx < PHYS.boostSpeed:
                P.vx = PHYS.boostSpeed; P.facing = 1
            if c == '<' and P.vx > -PHYS.boostSpeed:
                P.vx = -PHYS.boostSpeed; P.facing = -1
            k = '%d,%d' % (tx, fy)
            if c == '~' and k not in crumbleState:
                crumbleState[k] = O(phase='shake', t=PHYS.crumbleDelay)

    # --- animation bookkeeping
    if P.onGround and P.state == 'normal':
        P.runPhase += abs(P.vx) * dt * 0.045
    if P.flipping:
        P.flip += dt * math.pi * 2 / 0.55
        if P.flip >= math.pi * 2:
            P.flipping = False; P.flip = 0
    updateSquash(dt)

    # --- hazards, pickups, world bounds
    if P.immune > 0:
        P.immune = max(0, P.immune - dt)
    checkHazards()
    if P.state == 'dead':
        return
    checkPickups()
    if P.y > voidLine(P.x + P.w / 2):
        die()


def checkHazards():
    hx, hy, hw, hh = P.x + 3, P.y + 3, P.w - 6, P.h - 6
    x0, x1 = math.floor(hx / T), math.floor((hx + hw) / T)
    y0, y1 = math.floor(hy / T), math.floor((hy + hh) / T)
    for ty in range(y0, y1 + 1):
        for tx in range(x0, x1 + 1):
            if tileAt(tx, ty) == '^' and overlap(hx, hy, hw, hh, *spikeBox(tx, ty)):
                return hurt()
    for l in lasers:
        if laserOn(l) and overlap(hx, hy, hw, hh, l.x - 5, l.y0, 10, l.y1 - l.y0):
            return hurt()


def checkPickups():
    global stamina, celebrate, respawnPoint, lastCp, finished
    cx, cy = P.x + P.w / 2, P.y + P.h / 2
    for tk in turkeys:
        if tk.t <= 0 and abs(tk.x - cx) < P.w / 2 + 10 and abs(tk.y - cy) < P.h / 2 + 12:
            tk.t = 4   # as many as you like: it's back in a few seconds
            stamina = STAMINA_MAX; P.eightPack = True
            for _ in range(8):
                spawnParticle(tk.x, tk.y, (random() - 0.5) * 180, (random() - 0.5) * 180, 0.4, 3, '#a5561f', 0)
    for c in treats:
        if not c.taken and abs(c.x - cx) < P.w / 2 + 8 and abs(c.y - cy) < P.h / 2 + 10:
            c.taken = True; eatTreat()
            for _ in range(8):
                spawnParticle(c.x, c.y, (random() - 0.5) * 200, (random() - 0.5) * 200, 0.4, 3, '#7bb661', 0)
    for g in greenies:
        if not g.taken and overlap(P.x, P.y, P.w, P.h, g.x - 16, g.y - 20, 32, 40):
            g.taken = True; stamina = STAMINA_MAX
            if g.id in greeniesGot:
                # already in the save file: just a little sparkle, like grabbing a moon twice
                for _ in range(14):
                    spawnParticle(g.x, g.y, (random() - 0.5) * 260, (random() - 0.5) * 260, 0.5, 3, '#c9f27a', 0)
                if g.id in GREENIE_WARPS:
                    startWarp(GREENIE_WARPS[g.id])
            else:
                greeniesGot.add(g.id); saveGreenies()
                celebrate = O(g=g, t=0)
                P.vx = 0; P.vy = 0; P.flipping = False
                P.squash = 0.8; P.squashV = 0
    for d in diamonds:
        if not d.taken and abs(d.x - cx) < P.w / 2 + 10 and abs(d.y - cy) < P.h / 2 + 12:
            d.taken = True
            if d.id not in stuff.diamonds:
                stuff.diamonds.append(d.id); saveStuff()
            for i in range(12):
                spawnParticle(d.x, d.y, (random() - 0.5) * 240, (random() - 0.5) * 240, 0.5, 3, '#7fe8ff' if i % 2 else '#fff', 0)
    for cp in checkpoints:
        if not cp.active and overlap(P.x, P.y, P.w, P.h, cp.x - 16, cp.y - 70, 32, 70):
            for o in checkpoints:
                o.active = False
            cp.active = True; respawnPoint = cp
            lastCp = O(area=areaName, spot=spotOf(cp.x, cp.y))
    if finish and not finished and overlap(P.x, P.y, P.w, P.h, finish.x - 24, finish.y - 100, 48, 100):
        finished = True
        for i in range(60):
            spawnParticle(finish.x, finish.y - 90, (random() - 0.5) * 600, -random() * 500, 1.2, 4,
                          ['#e74c3c', '#f1c40f', '#3498db', '#2ecc71'][i % 4], 700)


# Tile + trunk collision for things that aren't Charlie (chickens, spat-out blocks).
# Moves b by its velocity and reports what it bumped into.
def moveBody(b, dt):
    hit = O(x=False, y=False, tramp=False)
    b.onGround = False
    n = max(1, math.ceil(max(abs(b.vx), abs(b.vy)) * dt / 6))
    for _ in range(n):
        dx = b.vx * dt / n
        if dx:
            b.x += dx
            y0, y1 = math.floor(b.y / T), math.floor((b.y + b.h - 0.001) / T)
            tx = math.floor((b.x + b.w - 0.001 if dx > 0 else b.x) / T)
            for ty in range(y0, y1 + 1):
                if solidAt(tx, ty):
                    b.x = tx * T - b.w if dx > 0 else (tx + 1) * T
                    b.vx = 0; hit.x = True
                    break
        dy = b.vy * dt / n
        if dy:
            b.y += dy
            x0, x1 = math.floor(b.x / T), math.floor((b.x + b.w - 0.001) / T)
            ty = math.floor((b.y + b.h - 0.001 if dy > 0 else b.y) / T)
            for tx in range(x0, x1 + 1):
                if solidAt(tx, ty):
                    if dy > 0:
                        b.y = ty * T - b.h; b.onGround = True
                        if tileAt(tx, ty) == 'T':
                            hit.tramp = True
                    else:
                        b.y = (ty + 1) * T
                    b.vy = 0; hit.y = True
                    break
        for tr in trees:
            p = trunkPush(b.x, b.y, b.w, b.h, tr)
            if not p:
                continue
            if p.ny < -0.5:
                b.y -= p.d / -p.ny
                if b.vy > 0:
                    b.vy = 0
                b.onGround = True; hit.y = True
            elif p.ny > 0.5:
                b.y += p.d / p.ny
                if b.vy < 0:
                    b.vy = 0
                hit.y = True
            else:
                b.x += p.nx * p.d; b.y += p.ny * p.d; b.vx = 0; hit.x = True
    return hit


def lineOfSight(x0, y0, x1, y1):
    n = math.ceil(math.hypot(x1 - x0, y1 - y0) / 8)
    for i in range(1, n):
        if solidAt(math.floor((x0 + (x1 - x0) * i / n) / T), math.floor((y0 + (y1 - y0) * i / n) / T)):
            return False
    return True


# ---------------------------------------------------------------------
#  Chickens
#  They wobble back and forth until they notice Charlie, then waddle after
#  him, walking, dropping off ledges and jumping (as high as Charlie can;
#  half as high in Easy) along the cheapest route they can find. Landing on one knocks it out;
#  running into one knocks Charlie out.
# ---------------------------------------------------------------------
CK_W, CK_H, CK_DRAW_H = 24, 30, 44
CK = O(
    wander=55, chase=150,
    notice=10 * T, forget=16 * T,   # how close Charlie has to be to get noticed / to stay chased
    maxRise=5, maxReach=4,          # tiles a jump can go up / across (Charlie's triple jump clears 5)
    maxJumpV=PHYS.jump[2],
    pounce=lambda: 0.5 + random() * 1.5,   # Hard: seconds between leaps at Charlie
    pounceH=2 * T,                         # ...and how high they go
)


# Easy chickens make the same jumps as in Hard, just half as high (so high ledges are out of reach).
def ckHeight():
    return 0.5 if difficulty == 'easy' else 1


def makeChicken(cx, feet):
    return O(
        home=[cx, feet], x=cx - CK_W / 2, y=feet - CK_H, w=CK_W, h=CK_H, vx=0, vy=0,
        onGround=False, facing=-1, mode='wander', wanderT=1 + random() * 2,
        alive=True, held=False, alertT=0, stunT=0, jumping=False, deadT=0,
        plan=None, planNode='', planT=0, pounceT=0, phase=random() * 6,
    )


def resetChicken(ck):
    respawn_wait = ck.respawn
    ck.update(makeChicken(*ck.home))
    if respawn_wait:
        ck.respawn = respawn_wait


def killChicken(ck):
    if not ck.alive:
        return
    ck.alive = False
    cx, cy = ck.x + ck.w / 2, ck.y + ck.h / 2
    for i in range(18):
        a, s = random() * math.pi * 2, 80 + random() * 260
        spawnParticle(cx, cy, math.cos(a) * s, math.sin(a) * s - 120, 0.7 + random() * 0.5, 3 + random() * 3,
                      '#f4f1ea' if i % 4 else '#d63031', 500)


# --- pathfinding over standing spots: a spot is an open tile with something solid under it.
def ckFree(tx, ty):
    c = tileAt(tx, ty)
    return c not in SOLID_CHARS and c != '^'


def ckStand(tx, ty):
    return 0 <= tx < LW and 0 <= ty < GH - 1 and ckFree(tx, ty) and solidAt(tx, ty + 1)


def colClear(tx, ya, yb):
    for y in range(min(ya, yb), max(ya, yb) + 1):
        if y >= 0 and not ckFree(tx, y):
            return False
    return True


# Every move from standing spot (x, y): [toX, toY, cost, 'walk' | 'jump', dir, dx, dy, high]
def ckMoves(x, y, out):
    out.clear()
    for d in (-1, 1):
        nx = x + d
        if ckStand(nx, y):
            out.append([nx, y, 2, 'walk', d])
        elif ckFree(nx, y) and not solidAt(nx, y + 1):
            # walk off the edge and drop onto whatever is below (not into spikes or the void)
            yy = y + 1
            while yy < GH and ckFree(nx, yy) and not solidAt(nx, yy + 1):
                yy += 1
            if yy - y <= 12 and ckStand(nx, yy):
                out.append([nx, yy, 3 + (yy - y) * 0.5, 'walk', d])
        # jumps: up onto ledges, across gaps, or down
        for dx in range(1, int(CK.maxReach / 2) + 1):
            tx = x + d * dx
            for dy in range(-3, CK.maxRise + 1):
                if dx == 1 and dy <= 0:
                    continue   # walking covers these
                ty = y - dy
                if not ckStand(tx, ty):
                    continue
                peak, low = min(y, ty) - 1, min(y, ty)
                if not colClear(x, peak, y) or not colClear(tx, peak, ty):
                    continue
                ok, high = True, False
                for i in range(1, dx):
                    cx = x + d * i
                    if colClear(cx, peak, low):
                        continue
                    # spikes poking up in between: fine if there's room to hop over the top of them
                    top = low
                    while top > peak - 1 and tileAt(cx, top) == '^':
                        top -= 1
                    if top < low and colClear(cx, low - 4, top):
                        high = True
                        continue
                    ok = False
                    break
                if high:
                    ok = ok and colClear(x, low - 4, y) and colClear(tx, low - 4, ty)
                if ok:
                    out.append([tx, ty, 4 + dx + max(0, dy) * 1.5 + (2 if high else 0), 'jump', d, dx * d, dy, high])


# Cheapest route to the spot nearest Charlie. Returns { node, move } (move = the first step,
# None when the chicken is already as close as it can get), or None when it isn't on a spot.
def ckFindPath(ck):
    import heapq
    fy = math.floor((ck.y + ck.h - 1) / T)
    start = None
    for fx in (math.floor((ck.x + ck.w / 2) / T), math.floor(ck.x / T), math.floor((ck.x + ck.w - 1) / T)):
        if ckStand(fx, fy):
            start = (fx, fy)
            break
    if not start:
        return None
    gx, gy = math.floor((P.x + P.w / 2) / T), math.floor((P.y + P.h - 1) / T)

    def key(x, y):
        return y * LW + x
    dist = {key(*start): 0}
    frm = {}
    heap = [(0, 0, start[0], start[1])]
    moves = []
    best, bestScore, popped, cnt = start, INF, 0, 0
    while heap and popped < 2500:
        c, _, x, y = heapq.heappop(heap)
        k = key(x, y)
        if c > dist[k]:
            continue
        popped += 1
        score = abs(x - gx) + abs(y - gy) * 1.5
        if score < bestScore:
            bestScore = score; best = (x, y)
            if score == 0:
                break
        ckMoves(x, y, moves)
        for m in moves:
            if abs(m[0] - start[0]) > 30:
                continue
            nk, nc = key(m[0], m[1]), c + m[2]
            if nc < dist.get(nk, INF):
                dist[nk] = nc; frm[nk] = (k, m)
                cnt += 1
                heapq.heappush(heap, (nc, cnt, m[0], m[1]))
    k, move = key(*best), None
    while k in frm:
        pk, m = frm[k]
        move = m; k = pk
    return O(node=start, move=move)


# Jump dx tiles across and dy tiles up, no higher than Charlie's best jump.
# In Easy it's the same jump at half the height (it may fall short). high: go 3 tiles over
# the take-off / landing, to clear spikes in between.
def ckJump(ck, dx, dy, high=False):
    g, rise, maxV = PHYS.gravity, dy * T, CK.maxJumpV
    vy = min(maxV, math.sqrt(2 * g * (max(0, rise) + (T * 3 if high else 40))))
    while True:
        t = (vy + math.sqrt(max(0, vy * vy - 2 * g * rise))) / g
        vx = dx * T / t
        if abs(vx) <= 300 or vy >= maxV:
            break
        vy = min(maxV, vy + 40)   # too far for a short hop: go higher for more air time
    vy *= math.sqrt(ckHeight())   # (height goes with speed squared)
    ck.vy = -vy; ck.vx = ck.jumpVx = vx; ck.jumping = True; ck.onGround = False
    ck.facing = sign(dx) or ck.facing


# A leap at Charlie 2 tiles high, or as high as the blocks (or spikes) over its head allow.
def ckPounce(ck, dxPx):
    g, full = PHYS.gravity, CK.pounceH
    x0, x1 = math.floor((ck.x + 1) / T), math.floor((ck.x + ck.w - 1) / T)
    room = full
    ty = math.floor((ck.y - 1) / T)
    while ty * T > ck.y - full - T:
        blocked = any(not ckFree(tx, ty) for tx in range(x0, x1 + 1))
        if blocked:
            room = min(full, ck.y - (ty + 1) * T - 1)
            break
        ty -= 1
    if room < 4:
        return   # no room to jump at all
    vy = math.sqrt(2 * g * room)
    t = 2 * vy / g
    vx = max(-300, min(300, dxPx / t))   # aimed to come down on him
    ck.vy = -vy; ck.vx = ck.jumpVx = vx; ck.jumping = True; ck.onGround = False
    ck.facing = sign(dxPx) or ck.facing


stompGrace = 0   # a moment after a stomp when touching chickens can't hurt Charlie


def updateChickens(dt):
    global stompGrace
    pcx, pcy = P.x + P.w / 2, P.y + P.h / 2
    # Decided once for the whole step, so landing on two chickens at once stomps both
    falling = P.vy > 0
    stomped = False
    stompGrace -= dt
    for ck in chickens:
        if not ck.alive and ck.respawn:
            # a spawner's chicken: a new one pops out where it started a few seconds later
            ck.deadT += dt
            if ck.deadT >= ck.respawn:
                resetChicken(ck)
                for _ in range(10):
                    spawnParticle(ck.x + ck.w / 2, ck.y + ck.h / 2, (random() - 0.5) * 160, -random() * 160, 0.5, 3, '#f4f1ea', 300)
            continue
        if not ck.alive or ck.held:
            continue
        ck.phase += dt; ck.alertT -= dt; ck.stunT -= dt

        if ck.mode == 'flying':
            # spat out: shoots in a straight line until it crashes into something
            hit = moveBody(ck, dt)
            for o in chickens:
                if o is not ck and o.alive and not o.held and overlap(ck.x, ck.y, ck.w, ck.h, o.x, o.y, o.w, o.h):
                    killChicken(o); hit.x = True
            if ck.y > GH * T or ck.y < -12 * T:
                ck.alive = False
            elif hit.x or hit.y:
                ck.mode = 'wander'; ck.vx = 0; ck.vy = 0; ck.stunT = 0.6; ck.wanderT = 1
            continue

        cx, cy = ck.x + ck.w / 2, ck.y + ck.h / 2
        d = math.hypot(pcx - cx, pcy - cy)
        if P.state != 'dead' and ck.mode == 'wander' and ck.stunT <= 0 and d < CK.notice and lineOfSight(cx, cy, pcx, pcy):
            ck.mode = 'chase'; ck.alertT = 0.6; ck.plan = None; ck.pounceT = CK.pounce()
            ck.facing = sign(pcx - cx) or ck.facing
            if ck.onGround:
                ck.vy = -280 * math.sqrt(ckHeight())   # startled hop
        if ck.mode == 'chase' and (d > CK.forget or P.state == 'dead'):
            ck.mode = 'wander'

        # Hard: every 0.5-2 seconds a chasing chicken leaps 2 tiles high at Charlie
        if difficulty == 'hard' and ck.mode == 'chase':
            ck.pounceT -= dt
            if ck.pounceT <= 0 and ck.onGround and not ck.jumping and ck.stunT <= 0 and ck.alertT <= 0:
                ckPounce(ck, pcx - cx); ck.pounceT = CK.pounce()

        want = 0
        # mid-jump it keeps pushing toward the landing spot, so bumping a ledge's side doesn't stop it
        if ck.jumping:
            ck.vx = ck.jumpVx; want = ck.vx
        elif ck.stunT > 0 or ck.alertT > 0:
            want = 0
        elif ck.mode == 'wander':
            ck.wanderT -= dt
            if ck.wanderT <= 0:
                ck.facing *= -1; ck.wanderT = 1.2 + random() * 2.2
            if ck.onGround:
                # turn around at walls and ledges
                fx, fy = math.floor((cx + ck.facing * (ck.w / 2 + 2)) / T), math.floor((ck.y + ck.h - 1) / T)
                if not ckFree(fx, fy) or not solidAt(fx, fy + 1):
                    ck.facing *= -1; ck.wanderT = 1.2 + random() * 2
            want = ck.facing * CK.wander
        elif ck.onGround:
            node = '%d,%d' % (math.floor(cx / T), math.floor((ck.y + ck.h - 1) / T))
            ck.planT -= dt
            if not ck.plan or node != ck.planNode or ck.planT <= 0:
                ck.plan = ckFindPath(ck) or False; ck.planNode = node; ck.planT = 0.4
            m = ck.plan.move if ck.plan else None
            toward = sign(pcx - cx) or ck.facing
            if not ck.plan:
                # standing somewhere the map doesn't know (a tree, a ledge's edge): head straight for him
                want = toward * CK.chase
                if ckBlocked(ck, toward):
                    ckJump(ck, toward * 2, 2)
            elif not m:
                # as close as it can get: shuffle toward him without walking off the edge
                fx, fy = math.floor((cx + toward * (ck.w / 2 + 2)) / T), math.floor((ck.y + ck.h - 1) / T)
                want = toward * CK.chase if abs(pcx - cx) > 4 and solidAt(fx, fy + 1) else 0
                if not want:
                    ck.facing = toward
            elif m[3] == 'walk':
                want = m[4] * CK.chase
            else:
                # line up on the take-off tile, then jump
                nodeCx = ck.plan.node[0] * T + T / 2
                if abs(cx - nodeCx) > 5:
                    want = sign(nodeCx - cx) * CK.chase * 0.6
                else:
                    ckJump(ck, m[5], m[6], m[7]); want = ck.vx
        else:
            want = ck.vx

        if not ck.jumping:
            ck.vx = approach(ck.vx, want, (1400 if ck.onGround else 500) * dt)
            if want:
                ck.facing = sign(want)
        ck.vy = min(ck.vy + PHYS.gravity * dt, PHYS.maxFall)
        hit = moveBody(ck, dt)
        if hit.tramp:
            ck.vy = -PHYS.trampoline; ck.jumping = False
        if ck.onGround:
            ck.jumping = False

        # spikes and the void
        if ck.y > columnBottom(ck.x + ck.w / 2):
            ck.alive = False
            continue
        sx0, sx1 = math.floor((ck.x + 3) / T), math.floor((ck.x + ck.w - 3) / T)
        sy0, sy1 = math.floor((ck.y + 3) / T), math.floor((ck.y + ck.h - 3) / T)
        for ty in range(sy0, sy1 + 1):
            for tx in range(sx0, sx1 + 1):
                if tileAt(tx, ty) == '^' and overlap(ck.x + 3, ck.y + 3, ck.w - 6, ck.h - 6, *spikeBox(tx, ty)):
                    killChicken(ck)
        if not ck.alive:
            continue

        # Charlie: landing on top knocks it out, anything else knocks him out
        if P.state != 'dead' and overlap(P.x, P.y, P.w, P.h, ck.x + 2, ck.y + 4, ck.w - 4, ck.h - 4):
            if P.state == 'smash':
                killChicken(ck)
            elif falling and P.y + P.h - ck.y < 16:
                killChicken(ck); stomped = True
            elif ck.stunT <= 0 and stompGrace <= 0:
                hurt()
    if stomped:
        P.vy = -(650 if held('jump') else 450); P.canCut = held('jump')
        P.state = 'normal'; P.diveReady = True; P.flipping = False; setLow(False)
        P.squash = -0.5; P.squashV = 0
        stompGrace = 0.15


def ckBlocked(ck, d):
    fx = math.floor((ck.x + ck.w / 2 + d * (ck.w / 2 + 2)) / T)
    return not ckFree(fx, math.floor((ck.y + ck.h - 1) / T))


# ---------------------------------------------------------------------
#  Inhaling
#  Z / 0 (or a left click) sucks in the first 2 layers of everything in a 90 degree cone
#  4 tiles long. Charlie holds it for up to 5 seconds, then it all shoots out one at a time,
#  each one kicking Charlie back the other way.
# ---------------------------------------------------------------------
STAMINA_MAX = 8
INHALE = O(
    cost=2.5, range=4 * T, halfAngle=math.pi / 4, depth=2,   # depth: layers of tiles per inhale
    suckTime=0.35, holdTime=5, spitGap=0.12,
    spitSpeed=700, chickenSpeed=800,   # how fast blocks / chickens come out
    kick=360, kickMax=850,             # push on Charlie per item, and his top speed from it
)
INHALE_TILES = 'g#X~T^><'   # (not cobblestone 'o': too heavy)
stamina = 0
staminaFlash = 0
inhale = None    # { phase: 'suck' | 'hold' | 'spit', t, aim, dir, things }
slurps = []      # things flying into Charlie's mouth (just for show)
thrown = []      # spat-out blocks in flight


def eatTreat():
    global stamina
    stamina = min(STAMINA_MAX, stamina + 1)


def mouth():
    return P.x + P.w / 2, P.y + P.h * 0.45


# The way Charlie is moving, or the way he faces when he's (nearly) still.
def moveDir():
    sp = math.hypot(P.vx, P.vy)
    return O(x=P.vx / sp, y=P.vy / sp) if sp > 40 else O(x=P.facing, y=0)


# Where to inhale / spit: toward the cursor for a click, the way he's moving for Z / 0.
def aimDir(byMouse):
    if not byMouse or not cursor:
        return moveDir()
    mx, my = mouth()
    dx, dy = cursor[0] + camX - mx, cursor[1] + camY - my
    d = math.hypot(dx, dy)
    return O(x=dx / d, y=dy / d) if d > 1 else moveDir()


def clicked():
    return 'Mouse0' in pressedKeys


def inCone(px, py):
    mx, my = mouth()
    vx, vy = px - mx, py - my
    d = math.hypot(vx, vy)
    return d <= INHALE.range and (d < 1 or (vx * inhale.aim.x + vy * inhale.aim.y) / d >= math.cos(INHALE.halfAngle))


# How many different solid tiles (not counting tile skipX, skipY) lie between two points?
def tilesBetween(x0, y0, x1, y1, skipX=-1, skipY=-1):
    n = math.ceil(math.hypot(x1 - x0, y1 - y0) / 4)
    seen = set()
    for i in range(1, n):
        tx, ty = math.floor((x0 + (x1 - x0) * i / n) / T), math.floor((y0 + (y1 - y0) * i / n) / T)
        if (tx != skipX or ty != skipY) and solidAt(tx, ty):
            seen.add((tx, ty))
    return len(seen)


def rayBlocked(x0, y0, x1, y1):
    return tilesBetween(x0, y0, x1, y1) > 0


def startInhale(byMouse):
    global stamina, staminaFlash, inhale
    if stamina < INHALE.cost:
        staminaFlash = 0.6
        return
    stamina -= INHALE.cost
    aim = aimDir(byMouse)
    if abs(aim.x) > 0.2:
        P.facing = sign(aim.x)
    inhale = O(phase='suck', t=INHALE.suckTime, aim=aim, things=[], byMouse=byMouse)

    # Tiles come loose up to INHALE.depth layers deep. The view is checked before anything is removed.
    mx, my = mouth()
    r = math.ceil(INHALE.range / T) + 1
    mtx, mty = math.floor(mx / T), math.floor(my / T)
    got = []
    for ty in range(max(0, mty - r), min(GH - 1, mty + r) + 1):
        for tx in range(max(0, mtx - r), min(LW - 1, mtx + r) + 1):
            c = grid[ty][tx]
            if c not in INHALE_TILES or not inCone(tx * T + T / 2, ty * T + T / 2):
                continue
            # look at the tile's nearest point, so the whole face of a wall or floor counts as in view
            px = max(tx * T + 1, min(tx * T + T - 1, mx))
            py = max(ty * T + 1, min(ty * T + T - 1, my))
            if tilesBetween(mx, my, px, py, tx, ty) < INHALE.depth:
                got.append((tx, ty, c))
    for tx, ty, c in got:
        grid[ty][tx] = '.'
        crumbleState.pop('%d,%d' % (tx, ty), None)
        inhale.things.append(O(kind='tile', c=c))
        slurps.append(O(c=c, x=tx * T + T / 2, y=ty * T + T / 2, t=0))
    P.squash = -0.4; P.squashV = 0


# Treats and chickens that drift into the cone while it's open get pulled in too.
def inhaleObjects():
    mx, my = mouth()
    for c in treats:
        if not c.taken and inCone(c.x, c.y) and not rayBlocked(mx, my, c.x, c.y):
            c.taken = True; eatTreat()
            slurps.append(O(treat=True, x=c.x, y=c.y, t=0))
    for ck in chickens:
        if not ck.alive or ck.held:
            continue
        cx, cy = ck.x + ck.w / 2, ck.y + ck.h / 2
        if inCone(cx, cy) and not rayBlocked(mx, my, cx, cy):
            ck.held = True
            inhale.things.append(O(kind='chicken', ck=ck))
            slurps.append(O(ck=ck, x=cx, y=cy, t=0))


def updateInhale(dt):
    global staminaFlash, slurps, inhale
    staminaFlash -= dt
    for s in slurps:
        s.t += dt / 0.25
    slurps = [s for s in slurps if s.t < 1]
    if P.state == 'dead':
        inhale = None   # whatever was inside is lost (respawn resets it)
        return
    if not inhale:
        if pressed('inhale'):
            startInhale(clicked())
    elif inhale.phase == 'suck':
        inhaleObjects()
        inhale.t -= dt
        if inhale.t <= 0:
            if inhale.things:
                inhale.phase = 'hold'; inhale.t = INHALE.holdTime
            else:
                inhale = None   # only treats (or nothing): nothing to spit
    elif inhale.phase == 'hold':
        inhale.t -= dt
        if inhale.t <= 0 or pressed('inhale'):
            # a click spits toward the cursor; running out of time spits the way it was sucked in
            byMouse = clicked() if pressed('inhale') else inhale.byMouse
            inhale.phase = 'spit'; inhale.t = 0; inhale.dir = aimDir(byMouse)
    else:
        inhale.t -= dt
        if inhale.t <= 0:
            spitOne()
            inhale.t = INHALE.spitGap
            if not inhale.things:
                inhale = None


def spitOne():
    item = inhale.things.pop(0)
    # out the way Charlie was moving when the spitting started; each kick pushes him back the other way
    sx, sy = inhale.dir.x, inhale.dir.y
    ax, ay = -sx, -sy
    mx, my = mouth()
    if item.kind == 'tile':
        thrown.append(O(c=item.c, x=mx + sx * 18 - 14, y=my + sy * 18 - 14, w=28, h=28,
                        vx=sx * INHALE.spitSpeed, vy=sy * INHALE.spitSpeed, spin=0))
    else:
        ck = item.ck
        ck.update(held=False, mode='flying', jumping=False, plan=None,
                  x=mx + sx * 18 - ck.w / 2, y=my + sy * 18 - ck.h / 2,
                  vx=sx * INHALE.chickenSpeed, vy=sy * INHALE.chickenSpeed)
        if sx:
            ck.facing = sign(sx)
    # the kick: cancel any speed going against it, push, then cap
    along = P.vx * ax + P.vy * ay
    if along < 0:
        P.vx -= ax * along; P.vy -= ay * along
    P.vx += ax * INHALE.kick; P.vy += ay * INHALE.kick
    sp = math.hypot(P.vx, P.vy)
    if sp > INHALE.kickMax:
        P.vx *= INHALE.kickMax / sp; P.vy *= INHALE.kickMax / sp
    if ay < 0:
        P.coyote = 0; P.ride = None
    if P.state in ('smash', 'dive'):
        P.state = 'normal'
    P.canCut = False; P.flipping = False
    P.squash = 0.55; P.squashV = 0
    for _ in range(6):
        spawnParticle(mx + sx * 16, my + sy * 16, sx * 200 + (random() - 0.5) * 160, sy * 200 + (random() - 0.5) * 160,
                      0.3, 3, 'rgba(255,255,255,0.9)', 0)


# Spat-out blocks fly with gravity until they drop into the void or hit something,
# then snap into the nearest open tile.
def updateThrown(dt):
    global thrown
    for b in thrown:
        b.vy = min(b.vy + PHYS.gravity * dt, 1400)
        b.spin += dt * 10
        hit = moveBody(b, dt)
        for ck in chickens:
            if ck.alive and not ck.held and overlap(b.x, b.y, b.w, b.h, ck.x, ck.y, ck.w, ck.h):
                killChicken(ck)
        if b.y > columnBottom(b.x + b.w / 2):
            b.gone = True
        elif hit.x or hit.y:
            b.gone = True; placeThrown(b)
    thrown = [b for b in thrown if not b.gone]


def placeThrown(b):
    cx, cy = math.floor((b.x + b.w / 2) / T), math.floor((b.y + b.h / 2) / T)
    for ox, oy in ((0, 0), (0, -1), (-1, 0), (1, 0), (0, 1), (-1, -1), (1, -1), (0, -2)):
        tx, ty = cx + ox, cy + oy
        if tx < 0 or ty < 0 or tx >= LW or ty >= GH or grid[ty][tx] != '.':
            continue
        if overlap(P.x, P.y, P.w, P.h, tx * T, ty * T, T, T):
            continue   # never bury Charlie
        if any(ck.alive and not ck.held and overlap(ck.x, ck.y, ck.w, ck.h, tx * T, ty * T, T, T) for ck in chickens):
            continue
        grid[ty][tx] = b.c
        dust(tx * T + T / 2, ty * T + T, 5, 100, 60)
        return
    # no room anywhere near: it shatters
    for _ in range(8):
        spawnParticle(b.x + random() * b.w, b.y + random() * b.h, (random() - 0.5) * 300, -random() * 200, 0.6,
                      3 + random() * 3, COL.dirt, 1200)


# ---------------------------------------------------------------------
#  Fireball spawners
#  Placed in the editor; invisible in the game. Every number setting is a range [from, to].
# ---------------------------------------------------------------------
FIRE_DEFAULTS = dict(
    every=[2, 2],          # seconds between shots
    delay=0,               # seconds before the first shot
    mode='straight',       # 'straight' | 'orbit' | 'spiral'
    angle=[0, 0],          # direction in degrees: 0 right, 90 down, 180 left, 270 up
    speed=[6, 6],          # straight: tiles per second
    radius=[3, 3],         # orbit: circle radius in tiles
    spacing=[2, 2],        # spiral: how far it grows per loop, tiles
    spin=[180, 180],       # orbit / spiral: degrees per second
    offX=[0, 0],           # random sideways offset of where it appears, tiles
    offY=[0, 0],           # random up / down offset, tiles
    size=[10, 10],         # radius in pixels
    life=0,                # seconds before it burns out (0 = until it hits something or leaves)
    max=30,                # most fireballs out at once from this spawner
    ghost=False,           # flies through blocks
)


def fireSettings(s):
    return O(FIRE_DEFAULTS, **(s or {}))


# ---------------------------------------------------------------------
#  Clouds (the editor's Cloud tool, chunk field cl = [[x, y, settings]]).
#  The game doesn't build them yet; the editor draws and moves them.
# ---------------------------------------------------------------------
CLOUD_DEFAULTS = dict(
    w=4,            # tiles wide
    scale=1,        # puff size (1 = normal)
    mode='lr',      # 'still' | 'lr' (left and right) | 'ud' (up and down) | 'ellipse' | 'path'
    dist=6,         # lr / ud: tiles it travels (negative goes left / up first)
    rx=4,           # ellipse: centre to side, tiles (the centre is home)
    ry=2,           # ellipse: centre to top, tiles
    ccw=False,      # ellipse: anticlockwise
    pts=[],         # path: [[dx, dy], ...] tiles from home that the cloud's middle passes through
    loop=False,     # path: from the last point straight back to the first (else back and forth)
    speed=2,        # tiles per second
    start=0,        # % of the way along the trip where it starts
)


def cloudSettings(s):
    out = O(CLOUD_DEFAULTS, **(s or {}))
    out.pts = [list(p) for p in out.pts]
    return out


# The points the cloud's top-left corner goes through (tiles from home), and whether they loop.
def cloudTrip(s):
    if s.mode == 'lr':
        return [[0, 0], [s.dist, 0]], False
    if s.mode == 'ud':
        return [[0, 0], [0, s.dist]], False
    if s.mode == 'ellipse':
        n, d = 64, -1 if s.ccw else 1
        return [[s.rx * math.cos(d * i / n * math.pi * 2), s.ry * math.sin(d * i / n * math.pi * 2)] for i in range(n)], True
    if s.mode == 'path':
        return [[0, 0]] + s.pts, bool(s.loop and len(s.pts) > 1)
    return [[0, 0]], False


def makeCloud(x, y, st):   # x, y: home top-left in pixels
    s = cloudSettings(st)
    pts, loop = cloudTrip(s)
    pts = [[x + px * T, y + py * T] for px, py in pts]
    n = len(pts) if loop else len(pts) - 1
    ln = sum(math.hypot(pts[(i + 1) % len(pts)][0] - pts[i][0], pts[(i + 1) % len(pts)][1] - pts[i][1]) for i in range(n))
    m = O(pts=pts, loop=loop, len=ln, speed=s.speed * T, w=s.w * T, scale=s.scale, hx=x, hy=y)
    m.s0 = s.start / 100 * (ln if loop else 2 * ln)
    m.x, m.y = cloudAt(m, m.s0)
    return m


# Where a cloud is once it has gone d pixels: round and round a loop, or there and back.
def cloudAt(m, d):
    pts, ln, loop = m.pts, m.len, m.loop
    if not ln:
        return pts[0]
    trip = ln if loop else 2 * ln
    s = d % trip
    if s > ln:
        s = trip - s
    segs = len(pts) if loop else len(pts) - 1
    for i in range(segs):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        l = math.hypot(b[0] - a[0], b[1] - a[1])
        if s <= l or i == segs - 1:
            k = min(1, s / l) if l else 0
            return [a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k]
        s -= l


# A fluffy cloud whose flat top is at y: a row of puffs, grey-blue underneath.
def drawCloud(x, y, w, s=1):
    n = max(2, round(w / (24 * s)))
    step = w / n
    for col, dy in (('#c9d6e8', 4 * s), ('#ffffff', 0)):
        ctx.fillStyle = col
        for i in range(n):
            r = (13 + ((i * 5) % 3) * 2) * s
            ctx.beginPath(); ctx.arc(x + step * (i + 0.5), y + 14 * s + dy, r, 0, math.pi * 2); ctx.fill()
        ctx.fillRect(x + 4 * s, y + 12 * s + dy, w - 8 * s, 12 * s)


def pick(r):
    a, b = r
    return a + random() * (b - a)


fireSpawners, fireballs = [], []


# A spawner's next fireball is rolled as soon as the one before it goes out,
# so the game knows ahead of time exactly where it will fly.
def rollFire(sp):
    s = sp.s
    ang = pick(s.angle) * math.pi / 180
    cx, cy = sp.x + pick(s.offX) * T, sp.y + pick(s.offY) * T
    f = O(sp=sp, mode=s.mode, cx=cx, cy=cy, ang=ang, age=0, r=max(2, pick(s.size)), life=s.life, ghost=s.ghost)
    if s.mode == 'straight':
        v = pick(s.speed) * T
        f.vx = math.cos(ang) * v; f.vy = math.sin(ang) * v
    else:
        f.spin = pick(s.spin) * math.pi / 180; f.R = pick(s.radius) * T; f.gap = pick(s.spacing) * T
    f.x, f.y = firePos(f, 0)
    return f


# Where a fireball is `age` seconds after it comes out (every path is a formula of time).
def firePos(f, age):
    if f.mode == 'straight':
        return f.cx + f.vx * age, f.cy + f.vy * age
    turned = f.spin * age
    a = f.ang + turned
    rad = f.R if f.mode == 'orbit' else f.gap * abs(turned) / (math.pi * 2)
    return f.cx + math.cos(a) * rad, f.cy + math.sin(a) * rad


# Would it be gone by then (burned out, out of the world, or into a block)?
def fireDone(f, age, x, y):
    return (f.life > 0 and age > f.life) or x < -T or x > LW * T + T or y < -LH * T or y > GH * T + T or \
        (not f.ghost and solidAt(math.floor(x / T), math.floor(y / T)))


def updateFire(dt, preview=False):
    global fireballs
    for sp in fireSpawners:
        if not sp.next:
            sp.next = rollFire(sp)
        sp.t -= dt
        if sp.t > 0:
            continue
        if sp.alive < sp.s.max:
            fireballs.append(sp.next); sp.alive += 1; sp.next = rollFire(sp)
        sp.t += max(0.05, pick(sp.s.every))
    for f in fireballs:
        f.age += dt
        f.x, f.y = firePos(f, f.age)
        if random() < 0.3:
            spawnParticle(f.x, f.y, (random() - 0.5) * 40, -20 - random() * 40, 0.3, 2 + f.r * 0.25,
                          '#ff7a1a' if random() < 0.5 else '#ffd23f', -60)
        if fireDone(f, f.age, f.x, f.y):
            f.gone = True
            for _ in range(6):
                spawnParticle(f.x, f.y, (random() - 0.5) * 160, (random() - 0.5) * 160, 0.35, 3, '#ff9a3c', 0)
            continue
        if preview:
            continue
        # touching Charlie (closest point of his box within the flame) burns him
        nx, ny = max(P.x, min(P.x + P.w, f.x)), max(P.y, min(P.y + P.h, f.y))
        if P.state != 'dead' and math.hypot(f.x - nx, f.y - ny) < f.r * 0.8:
            hurt()
        for ck in chickens:
            if ck.alive and not ck.held and overlap(f.x - f.r, f.y - f.r, f.r * 2, f.r * 2, ck.x, ck.y, ck.w, ck.h):
                killChicken(ck)
    for f in fireballs:
        if f.gone:
            f.sp.alive -= 1
    fireballs = [f for f in fireballs if not f.gone]


# --- warnings: an arrow on the edge of the screen where a fireball will fly in ---------
WARN_TIME = 1   # how far ahead to look, seconds


def fireIncoming(f, wait):
    def near(x, y):
        return x + f.r > camX and x - f.r < camX + VIEW_W and y + f.r > camY and y - f.r < camY + VIEW_H
    px = py = None
    t = wait
    while t <= WARN_TIME + 1e-6:
        age = f.age + t - wait
        x, y = firePos(f, age)
        if fireDone(f, age, x, y):
            return None
        if near(x, y):
            if px is None:
                return None   # you can already see it (or where it pops out)
            return O(x=x, y=y, dx=x - px, dy=y - py, t=t)
        px, py = x, y
        t += 0.04
    return None


def drawFireWarnings():
    warn = []
    for f in fireballs:
        w = fireIncoming(f, 0)
        if w:
            warn.append(w)
    for sp in fireSpawners:
        if not sp.next or sp.t > WARN_TIME or sp.alive >= sp.s.max:
            continue
        f = sp.next
        wait = max(0, sp.t)
        x0, y0 = firePos(f, 0)
        if x0 + f.r > camX and x0 - f.r < camX + VIEW_W and y0 + f.r > camY and y0 - f.r < camY + VIEW_H:
            # it will pop out on screen: the arrow goes right where it appears, pointing where it heads
            x1, y1 = firePos(f, 0.05)
            warn.append(O(x=x0, y=y0, dx=x1 - x0, dy=y1 - y0, t=wait, here=True))
        else:
            w = fireIncoming(f, wait)
            if w:
                warn.append(w)
    m = 20
    for w in warn:
        if behindEndlessWall(w.x, w.y):
            continue   # (it would give the trick away)
        x = w.x - camX if w.here else max(m, min(VIEW_W - m, w.x - camX))
        y = w.y - camY if w.here else max(m, min(VIEW_H - m, w.y - camY))
        hurry = 1 - w.t / WARN_TIME
        size = 10 + hurry * 8   # grows as it gets close
        ctx.save()
        ctx.translate(x, y); ctx.rotate(math.atan2(w.dy, w.dx))
        ctx.globalAlpha = 0.55 + 0.45 * hurry * (0.75 + 0.25 * math.sin(simTime * 20))
        ctx.fillStyle = '#ff5a1f'; ctx.strokeStyle = '#fff'; ctx.lineWidth = 2.5
        ctx.beginPath(); ctx.moveTo(size, 0); ctx.lineTo(-size * 0.8, -size * 0.75); ctx.lineTo(-size * 0.4, 0)
        ctx.lineTo(-size * 0.8, size * 0.75); ctx.closePath()
        ctx.stroke(); ctx.fill()
        ctx.restore()


# Flat circles: orange, yellow, then a white-hot middle, with a little flicker.
def drawFireballs():
    for f in fireballs:
        k = 1 + math.sin(simTime * 30 + f.age * 7) * 0.08
        ctx.fillStyle = '#ff7a1a'; ctx.beginPath(); ctx.arc(f.x, f.y, f.r * k, 0, math.pi * 2); ctx.fill()
        ctx.fillStyle = '#ffd23f'; ctx.beginPath(); ctx.arc(f.x, f.y, f.r * 0.62, 0, math.pi * 2); ctx.fill()
        ctx.fillStyle = '#fff6d0'; ctx.beginPath(); ctx.arc(f.x, f.y, f.r * 0.28, 0, math.pi * 2); ctx.fill()


# ---------------------------------------------------------------------
#  World update
# ---------------------------------------------------------------------
def laserPhase(l):
    return ((simTime + l.offset) % l.period) / l.period


def laserOn(l):
    return laserPhase(l) < l.on


# Squash is a jelly spring: positive = squashed wide, negative = stretched tall.
def updateSquash(dt):
    rest = 0
    if P.state == 'slide':
        rest = 0.6
    elif P.state == 'crouch':
        rest = 0.45
    elif P.state == 'dive':
        rest = 0.4
    elif P.state == 'smash':
        rest = -0.55
    elif P.wallSliding:
        rest = -0.3
    elif not P.onGround:
        rest = -min(0.3, abs(P.vy) / 2500)
    if inhale and inhale.phase == 'hold':
        rest = 0.4   # cheeks full
    elif inhale and inhale.phase == 'suck':
        rest = -0.2
    P.squashV += (-260 * (P.squash - rest) - 9 * P.squashV) * dt
    P.squash += P.squashV * dt


CELEBRATE_TIME = 2.6


def updateParticles(dt):
    global particles, popups
    for p in particles:
        p.vy += p.grav * dt; p.x += p.vx * dt; p.y += p.vy * dt; p.life -= dt
    particles = [p for p in particles if p.life > 0]
    for p in popups:
        p.t -= dt; p.y -= 40 * dt
    popups = [p for p in popups if p.t > 0]


def update(dt):
    global toast, celebrate, warp, easyScene, simTime, runTime, camX, camY, shake
    if toast:
        toast.t -= dt
        if toast.t <= 0:
            toast = None
    if celebrate:
        # the world freezes while Charlie shows off the Greenie
        celebrate.t += dt
        if random() < 0.5:
            a = random() * math.pi * 2
            spawnParticle(P.x + P.w / 2, P.y - 30, math.cos(a) * 220, math.sin(a) * 220, 0.7, 3 + random() * 3,
                          '#c9f27a' if random() < 0.5 else '#fff6a8', 0)
        updateParticles(dt)
        if celebrate.t > CELEBRATE_TIME or (celebrate.t > 0.9 and pressed('jump')):
            to = GREENIE_WARPS.get(celebrate.g.id)
            celebrate = None
            if to:
                startWarp(to)
        return
    if warp:
        # the world holds still while the screen fades
        warp.t += dt
        if not warp.done and warp.t >= WARP_TIME:
            if warp.local:
                throughLocalDoor(warp.local)
            else:
                teleport(warp.to, warp.arrive, warp.spot)
            warp.done = True; easyScene = None
        if easyScene:
            simTime += dt; easyScene.n.wordT += dt
        if warp.t >= WARP_TIME * 2:
            warp = None
        updateParticles(dt)
        return
    if easyScene:
        simTime += dt; easyScene.n.wordT += dt
        return
    if menu:
        simTime += dt
        return
    if ui:
        return   # closet / chest / backpack screens pause the game
    simTime += dt
    if not finished:
        runTime += dt

    for m in movers:
        k = 0.5 - 0.5 * math.cos(simTime / m.period * math.pi * 2)
        nx, ny = m.ax + (m.bx - m.ax) * k, m.ay + (m.by - m.ay) * k
        m.dx = nx - m.x; m.dy = ny - m.y; m.x = nx; m.y = ny

    for key, s in list(crumbleState.items()):
        s.t -= dt
        if s.t > 0:
            continue
        tx, ty = (int(v) for v in key.split(','))
        if s.phase == 'shake':
            grid[ty][tx] = 'c'; s.phase = 'gone'; s.t = PHYS.crumbleRespawn
            for _ in range(5):
                spawnParticle(tx * T + random() * T, ty * T + T / 2, (random() - 0.5) * 80, 0, 0.6, 4, '#c8a46a', 900)
        elif not overlap(P.x, P.y, P.w, P.h, tx * T, ty * T, T, T):
            grid[ty][tx] = '~'
            del crumbleState[key]
    for d in doors:
        d.lockedT = max(0, d.lockedT - dt)
    for key, v in list(trampAnim.items()):
        nv = v - dt * 4
        if nv <= 0:
            del trampAnim[key]
        else:
            trampAnim[key] = nv

    updatePlayer(dt)
    updateSlabs(dt)
    updateWingTreats(dt)
    updateLinks()
    updateSwitches()
    updateInhale(dt)
    updateChickens(dt)
    updateThrown(dt)
    updateFire(dt)
    updateNpcs(dt)
    updateProps(dt)
    updateFlyingLegs(dt)
    updateParticles(dt)

    # camera: follows Charlie both ways, but up and down it stops at the border of the chunk he's in.
    tx = P.x + P.w / 2 - VIEW_W / 2 + P.vx * 0.25
    k = 1 - math.exp(-dt * 6)
    if P.state != 'dead':
        camY += (camYFor(P.x + P.w / 2, P.y + P.h) - camY) * k
    camX += (tx - camX) * k
    camX = max(0, min(LW * T - VIEW_W, camX))
    shake = approach(shake, 0, dt * 30)


# ---------------------------------------------------------------------
#  Rendering
# ---------------------------------------------------------------------
COL = O(
    skyTop='#d9e2ec', skyBot='#f3f5f8',
    solid='#2b2f36', solidTop='#454c57',
    spike='#1d2026',
    crate='#8d6e4f', crateLine='#5d4630',
    crumble='#c8a46a', crumbleLine='#8c6f3e',
    tramp='#e74c3c', boost='#1abc9c',
    mover='#5e81ac', moverTop='#81a1c1',
    laser='#ff2d55',
    grass='#5cbf4a', dirt='#9b6a3c', dirtBg='#6b4526', cobble='#835832', cobbleCrack='#4a2e17', trunk='#7a4a24',
)

screen = None
ctx = None
charlieImg = greenieImg = chickenImg = hatImg = mapImg = bobImg = bobTalkImg = grandmaImg = turkeyImg = charlieStrongImg = None
greenieBackImg = None


def drawBackdrop():
    if backdrop == 'hut':
        # rough log walls that move with the room
        ctx.fillStyle = '#3e2716'; ctx.fillRect(0, 0, VIEW_W, VIEW_H)
        oy = -(camY % 28) - 28
        y = oy
        while y < VIEW_H + 28:
            ctx.fillStyle = '#4b301b'; ctx.fillRect(0, y + 2, VIEW_W, 22)
            ctx.fillStyle = '#56381f'; ctx.fillRect(0, y + 6, VIEW_W, 5)
            ctx.fillStyle = '#2a190c'; ctx.fillRect(0, y + 25, VIEW_W, 2)
            y += 28
        return
    if backdrop == 'house':
        # light beige wallpaper with soft stripes that move with the room
        ctx.fillStyle = '#f4e9d2'; ctx.fillRect(0, 0, VIEW_W, VIEW_H)
        ctx.fillStyle = 'rgba(214,190,150,0.2)'
        x = -(camX % 48) - 48
        while x < VIEW_W + 48:
            ctx.fillRect(x, 0, 16, VIEW_H)
            x += 48
    else:
        X, Y = ctx.pt(0, 0)
        ctx.surf.blit(linear_v(VIEW_W, VIEW_H, COL.skyTop, COL.skyBot), (int(X), int(Y)))
        # parallax background blocks
        ctx.fillStyle = 'rgba(43,47,54,0.06)'
        bot = camSpan.bot if camSpan else LH * T
        for i in range(40):
            bx = i * 260 - (camX * 0.3) % 260 - 260 + ((i * 97) % 60)
            bh = 120 + ((i * 53) % 200)
            ctx.fillRect(bx, VIEW_H - bh - (camY - (bot - VIEW_H)) * 0.3, 140, bh + 400)


# Everything in the world except Charlie (and what goes on top of him), seen from camX, camY.
def drawWorld(sx, sy):
    ctx.setTransform()
    ctx.translate(-round(camX + sx), -round(camY + sy))
    x0, x1 = max(0, math.floor(camX / T) - 1), min(LW - 1, math.ceil((camX + VIEW_W) / T) + 1)
    y0, y1 = max(0, math.floor(camY / T) - 1), min(GH - 1, math.ceil((camY + VIEW_H) / T) + 1)
    drawBackTiles(x0, x1, y0, y1)
    drawHouses()
    drawSigns()
    drawCheckpoints()
    drawFinish()
    drawLasers()
    drawTiles(x0, x1, y0, y1)
    drawSlabs()
    drawProps()
    drawTrees()
    drawTexts()
    drawMovers()
    drawTreats()
    drawWingTreats()
    drawGreenies()
    drawDiamonds()
    drawNpcs()
    drawChickens()
    drawThrown()
    drawFireballs()
    drawInhaleCone()
    drawSlurps()
    drawSwitches()
    drawSecrets()


# What's past a linked doorway, drawn in place on the screen (see `views`).
def drawViews(sx, sy):
    global camX, camY, activeSecret
    for v in views:
        if activeSecret not in v.whenIds:
            continue
        a, b = portals.get(v['from']), portals.get(v['to'])
        if not a or not b:
            continue
        ex = round(v.edge * T - camX - sx)   # the edge on screen
        if (ex >= VIEW_W) if v.side == 'right' else (ex <= 0):
            continue
        keep = (camX, camY, activeSecret)
        ctx.setTransform()
        ctx.save()
        if v.side == 'right':
            ctx.clip_rect(ex, 0, VIEW_W - ex, VIEW_H)
        else:
            ctx.clip_rect(0, 0, ex, VIEW_H)
        camX += (b[0] - a[0]) * T; camY += (b[1] - a[1]) * T; activeSecret = v.showId
        drawBackdrop()
        drawWorld(sx, sy)
        camX, camY, activeSecret = keep
        ctx.restore()


def draw():
    global activeSecret
    ctx.setTransform()
    drawBackdrop()
    sx, sy = (random() - 0.5) * shake, (random() - 0.5) * shake
    if P.state != 'dead':
        activeSecret = secretAt(math.floor((P.x + P.w / 2) / T), math.floor((P.y + P.h / 2) / T))
    drawWorld(sx, sy)
    drawViews(sx, sy)
    ctx.setTransform()
    ctx.translate(-round(camX + sx), -round(camY + sy))
    if celebrate:
        drawCelebrationBackdrop()
    drawPlayer()
    drawParticles()
    drawEndlessWalls(sx, sy)
    drawDim()
    drawNpcTalk()
    drawPopups()
    if debug:
        drawDebug()

    ctx.setTransform()
    if easyScene:
        drawEasyScene()
    elif menu:
        drawMenu()
    else:
        if not ui and not warp:
            drawFireWarnings()
            drawFarTalk()
        if ui:
            drawUI()
        drawHUD()
    if celebrate:
        drawCelebrationBanner()
    if warp:
        k = warp.t / WARP_TIME if warp.t < WARP_TIME else 2 - warp.t / WARP_TIME
        ctx.fillStyle = 'rgba(%s,%.3f)' % ('255,255,255' if warp.white else '10,12,16', max(0, min(1, k)))
        ctx.fillRect(0, 0, VIEW_W, VIEW_H)
    drawOverlay()


# (the editor keeps its background rows as 'b' / '.' letters, the game as True / False)
def bgAt(tx, ty):
    if not bgGrid or ty < 0 or ty >= len(bgGrid) or tx < 0 or tx >= len(bgGrid[ty]):
        return False
    v = bgGrid[ty][tx]
    return v is True or v == 'b'


# The dirt background layer. Drawn first, so checkpoints, signs and houses sit in front of it.
def drawBackTiles(x0, x1, y0, y1):
    ctx.fillStyle = COL.dirtBg
    for ty in range(y0, y1 + 1):
        for tx in range(x0, x1 + 1):
            # overlapping 1px into background neighbours so no seams show
            if bgAt(tx, ty):
                ctx.fillRect(tx * T, ty * T, T + (1 if bgAt(tx + 1, ty) else 0), T + (1 if bgAt(tx, ty + 1) else 0))


def secretAt(tx, ty):
    return secretMap[ty * LW + tx] if secretMap and 0 <= tx < LW and 0 <= ty < GH else 0


# Is this cell hidden under plain ground right now?
def coveredAt(tx, ty):
    if not secretMap:
        return False
    id = secretAt(tx, ty)
    if not activeSecret:
        return id > 0
    z = secrets[activeSecret - 1]
    if z.keepOutside and not id:
        return False
    return id != activeSecret and id not in z.alsoIds and not (z.seeX is not None and tx >= z.seeX)


# Plain ground over every hidden cell on screen (and over the rest of the world while
# Charlie is inside a secret). Drawn over everything except Charlie himself.
def drawSecrets():
    if not secrets:
        return
    x0, x1 = math.floor(camX / T) - 1, math.ceil((camX + VIEW_W) / T) + 1
    y0, y1 = math.floor(camY / T) - 1, math.ceil((camY + VIEW_H) / T) + 1
    for ty in range(y0, y1 + 1):
        for tx in range(x0, x1 + 1):
            if not coveredAt(tx, ty):
                continue
            ctx.fillStyle = COL.dirt
            ctx.fillRect(tx * T, ty * T, T + (1 if coveredAt(tx + 1, ty) else 0), T + (1 if coveredAt(tx, ty + 1) else 0))
            if not activeSecret and not isSolidChar(tileAt(tx, ty - 1)) and not coveredAt(tx, ty - 1):
                ctx.fillStyle = COL.grass; ctx.fillRect(tx * T, ty * T, T, 10)


def drawSwitches():
    for sw in switches:
        ctx.fillStyle = '#5a5f69'; ctx.fillRect(sw.x - 3, sw.y, sw.w + 6, 3)
        ctx.fillStyle = '#e0413a'
        ctx.beginPath(); ctx.ellipse(sw.x + sw.w / 2, sw.y + 3, sw.w / 2, sw.h, 0, 0, math.pi); ctx.fill()


# cobblestone cracks, three looks picked by the tile's spot: lists of [x, y] points in the tile
CRACKS = [
    [[[5, 4], [11, 12], [9, 19]], [[11, 12], [18, 14]], [[24, 24], [28, 29]]],
    [[[22, 5], [17, 13], [21, 22], [16, 28]], [[17, 13], [11, 15]]],
    [[[6, 22], [13, 25], [19, 21]], [[24, 8], [28, 15]], [[8, 6], [12, 9]]],
]


def drawTiles(x0, x1, y0, y1):
    falling = any(sl.moving for sl in slabs)   # (a falling ceiling is drawn smoothly by drawSlabs)
    for ty in range(y0, y1 + 1):
        row = grid[ty]
        for tx in range(x0, x1 + 1):
            c = row[tx]
            if c != '.' and c != 'c' and not (falling and slabAt(tx, ty)):
                drawTile(c, tx * T, ty * T, tx, ty)


# One tile at (px, py). A loose tile (flying through the air) has no tx, ty and
# is drawn on its own, without looking at neighbours.
def drawTile(c, px, py, tx=None, ty=None):
    loose = tx is None
    exposedTop = loose or not isSolidChar(tileAt(tx, ty - 1))
    sw = T + (1 if not loose and tileAt(tx + 1, ty) == c else 0)
    sh = T + (1 if not loose and tileAt(tx, ty + 1) == c else 0)
    if c == '#':
        ctx.fillStyle = COL.solid; ctx.fillRect(px, py, sw, sh)
        if exposedTop:
            ctx.fillStyle = COL.solidTop; ctx.fillRect(px, py, T, 4)
    elif c == 'g':
        # a stack of ground: grass on the top tile, plain dirt underneath
        ctx.fillStyle = COL.dirt; ctx.fillRect(px, py, sw, sh)
        if loose or (tileAt(tx, ty - 1) != 'g' and not coveredAt(tx, ty - 1)):
            ctx.fillStyle = COL.grass; ctx.fillRect(px, py, sw, 10)
    elif c == 'X':
        ctx.fillStyle = COL.crate; ctx.fillRect(px, py, T, T)
        ctx.strokeStyle = COL.crateLine; ctx.lineWidth = 2
        ctx.strokeRect(px + 2, py + 2, T - 4, T - 4)
        ctx.beginPath()
        ctx.moveTo(px + 8, py + 4); ctx.lineTo(px + 14, py + 14); ctx.lineTo(px + 10, py + 22); ctx.lineTo(px + 16, py + 29)
        ctx.moveTo(px + 14, py + 14); ctx.lineTo(px + 24, py + 12)
        ctx.stroke()
    elif c == '~':
        s = None if loose else crumbleState.get('%d,%d' % (tx, ty))
        # shakes harder the closer it is to falling
        jx = (random() - 0.5) * (1 + 5 * (1 - s.t / PHYS.crumbleDelay)) if s else 0
        ctx.fillStyle = COL.crumble; ctx.fillRect(px + jx, py, T, T * 0.6)
        ctx.strokeStyle = COL.crumbleLine; ctx.lineWidth = 2
        ctx.beginPath()
        ctx.moveTo(px + jx + 6, py + 4); ctx.lineTo(px + jx + 12, py + 14)
        ctx.moveTo(px + jx + 22, py + 6); ctx.lineTo(px + jx + 18, py + 16)
        ctx.stroke()
    elif c == 'T':
        a = 0 if loose else trampAnim.get('%d,%d' % (tx, ty), 0)
        bump = math.sin(a * math.pi) * 6
        ctx.fillStyle = COL.solid; ctx.fillRect(px, py + 10, T, T - 10)
        ctx.strokeStyle = '#888'; ctx.lineWidth = 2
        ctx.beginPath()
        for i in range(3):
            ctx.moveTo(px + 6 + i * 10, py + 10); ctx.lineTo(px + 6 + i * 10, py + 4 - bump)
        ctx.stroke()
        ctx.fillStyle = COL.tramp
        ctx.fillRect(px + 1, py + 2 - bump, T - 2, 6)
    elif c in ('>', '<'):
        ctx.fillStyle = COL.solid; ctx.fillRect(px, py, T, T)
        d = 1 if c == '>' else -1
        off = ((simTime * 40) % 16) * d
        ctx.save()
        if ctx.aligned():
            ctx.clip_rect(px, py, T, 10)
        ctx.strokeStyle = COL.boost; ctx.lineWidth = 3
        ctx.beginPath()
        for i in range(-1, 3):
            cx = px + i * 16 + off + 8
            ctx.moveTo(cx - 4 * d, py + 2); ctx.lineTo(cx + 2 * d, py + 5); ctx.lineTo(cx - 4 * d, py + 8)
        ctx.stroke()
        ctx.restore()
    elif c == 'l':
        # hut wall: stacked logs with dark gaps between them
        ctx.fillStyle = '#5b3a20'; ctx.fillRect(px, py, sw, sh)
        ctx.fillStyle = '#6e4727'; ctx.fillRect(px, py + 2, sw, 12); ctx.fillRect(px, py + 18, sw, 12)
        ctx.fillStyle = '#3b2412'; ctx.fillRect(px, py + 15, sw, 2); ctx.fillRect(px, py + 31, sw, 1)
    elif c == 'f':
        # hut floor: worn dark planks
        ctx.fillStyle = '#6a4526'; ctx.fillRect(px, py, sw, sh)
        ctx.fillStyle = '#4e321b'
        ctx.fillRect(px, py + 10, sw, 1); ctx.fillRect(px, py + 21, sw, 1)
        if ((tx or 0) * 7) % 3 == 0:
            ctx.fillRect(px + 12, py, 1, 10)
        if ((tx or 0) * 5) % 4 == 1:
            ctx.fillRect(px + 22, py + 11, 1, 10)
        if not loose and not isSolidChar(tileAt(tx, ty - 1)):
            ctx.fillStyle = '#80583a'; ctx.fillRect(px, py, sw, 3)
    elif c == 'o':
        # cobblestone: darker dirt with cracks (too heavy to inhale)
        ctx.fillStyle = COL.cobble; ctx.fillRect(px, py, sw, sh)
        ctx.strokeStyle = COL.cobbleCrack; ctx.lineWidth = 2
        ctx.beginPath()
        for line in CRACKS[0 if loose else (tx * 7 + ty * 5) % len(CRACKS)]:
            for i, (x, y) in enumerate(line):
                (ctx.lineTo if i else ctx.moveTo)(px + x, py + y)
        ctx.stroke()
    elif c == 'k':
        # bridge plank: boards across, dark gaps between them, rope rails along the edges
        ctx.fillStyle = '#b07a45'; ctx.fillRect(px, py + 6, sw, 18)
        ctx.fillStyle = '#7d5129'
        ctx.fillRect(px, py + 6, sw, 2); ctx.fillRect(px, py + 22, sw, 2)
        ctx.fillRect(px + 15, py + 8, 2, 14)
        ctx.fillStyle = '#d2b48c'; ctx.fillRect(px, py + 3, sw, 2)
    elif c == 'w':
        # wooden floor: planks with staggered seams, and a white baseboard on the wall above
        ctx.fillStyle = '#a8703f'; ctx.fillRect(px, py, sw, sh)
        ctx.fillStyle = '#8a5a31'
        for r in range(4):
            ctx.fillRect(px, py + r * 8 + 7, sw, 1)
            if ((tx or 0) * 3 + r * 2) % 5 == 0:
                ctx.fillRect(px + 6 + r * 6, py + r * 8, 1, 8)
        if not loose and not isSolidChar(tileAt(tx, ty - 1)):
            ctx.fillStyle = '#c99260'; ctx.fillRect(px, py, sw, 3)
            ctx.fillStyle = '#fbf6ea'; ctx.fillRect(px, py - 10, sw, 10)
            ctx.fillStyle = '#d9c9a6'; ctx.fillRect(px, py - 11, sw, 1)
    elif c == 'p':
        # house walls and ceiling, with trim where they meet the room
        ctx.fillStyle = '#e6d6b4'; ctx.fillRect(px, py, sw, sh)
        if not loose:
            ctx.fillStyle = '#cdb88e'
            if not isSolidChar(tileAt(tx, ty + 1)):
                ctx.fillRect(px, py + T - 7, T, 7)
            if not isSolidChar(tileAt(tx + 1, ty)):
                ctx.fillRect(px + T - 7, py, 7, T)
            if not isSolidChar(tileAt(tx - 1, ty)):
                ctx.fillRect(px, py, 7, T)
    elif c == '^':
        # turned to stick to the ground beside it (a loose one in the air stays upright)
        turn = 0 if loose else spikeTurn(tx, ty)
        ctx.save()
        ctx.translate(px + T / 2, py + T / 2); ctx.rotate(turn)
        ctx.fillStyle = COL.spike
        ctx.beginPath()
        ctx.moveTo(-16, 16); ctx.lineTo(-8, -6); ctx.lineTo(0, 16)
        ctx.lineTo(8, -6); ctx.lineTo(16, 16)
        ctx.closePath(); ctx.fill()
        ctx.restore()


def drawMovers():
    for m in movers:
        ctx.fillStyle = 'rgba(94,129,172,0.15)'
        ctx.fillRect(min(m.ax, m.bx), min(m.ay, m.by), abs(m.bx - m.ax) + m.w, abs(m.by - m.ay) + m.h)
        ctx.fillStyle = COL.mover; ctx.fillRect(m.x, m.y, m.w, m.h)
        ctx.fillStyle = COL.moverTop; ctx.fillRect(m.x, m.y, m.w, 4)


def drawLasers():
    for l in lasers:
        ph = laserPhase(l)
        on = ph < l.on
        untilOn = (1 - ph) * l.period
        ctx.fillStyle = '#3b4049'
        ctx.fillRect(l.x - 9, l.y0, 18, 8)
        ctx.fillRect(l.x - 9, l.y1 - 8, 18, 8)
        if on:
            ctx.fillStyle = 'rgba(255,45,85,0.25)'; ctx.fillRect(l.x - 8, l.y0 + 8, 16, l.y1 - l.y0 - 16)
            ctx.fillStyle = COL.laser; ctx.fillRect(l.x - 3, l.y0 + 8, 6, l.y1 - l.y0 - 16)
            ctx.fillStyle = '#fff'; ctx.fillRect(l.x - 1, l.y0 + 8, 2, l.y1 - l.y0 - 16)
        elif untilOn < 0.4 and math.floor(simTime * 20) % 2 == 0:
            ctx.fillStyle = 'rgba(255,45,85,0.5)'; ctx.fillRect(l.x - 1, l.y0 + 8, 2, l.y1 - l.y0 - 16)


def drawSweetPotato(x, y, rot):
    ctx.save()
    ctx.translate(x, y); ctx.rotate(rot)
    ctx.fillStyle = '#9c4a2a'   # skin
    ctx.beginPath(); ctx.moveTo(-9, -7); ctx.lineTo(7, -9); ctx.lineTo(10, 6); ctx.lineTo(-7, 9); ctx.closePath(); ctx.fill()
    ctx.fillStyle = '#f39237'   # orange inside
    ctx.beginPath(); ctx.moveTo(-9, -7); ctx.lineTo(4, -8.6); ctx.lineTo(7, 6.4); ctx.lineTo(-7, 9); ctx.closePath(); ctx.fill()
    ctx.fillStyle = '#ffc27d'   # shine
    ctx.fillRect(-6, -5, 6, 3)
    ctx.restore()


def drawTreats():
    # sweet potato chunks
    for c in treats:
        if c.taken:
            continue
        if c.x < camX - 40 or c.x > camX + VIEW_W + 40:
            continue
        bob = math.sin(simTime * 3 + c.x * 0.05) * 3
        drawSweetPotato(c.x, c.y + bob, math.sin(simTime * 2 + c.x) * 0.25)


LEAF_COLORS = ['#3fa34d', '#57c05e', '#2e8b3e']


def drawTree(tr):
    ctx.fillStyle = COL.trunk
    ctx.beginPath()
    for i, (x, y) in enumerate(tr.poly):
        if i:
            ctx.lineTo(x, y)
        else:
            ctx.moveTo(x, y)
    ctx.closePath(); ctx.fill()
    # leaves are just decoration: a pile of circles on top of the trunk
    s = [tr.seed]

    def rnd():
        s[0] = (s[0] * 16807) % 2147483647
        return s[0] / 2147483647
    for i in range(18):
        a, r, rad = rnd() * math.pi * 2, rnd() * 30, 11 + rnd() * 12
        ctx.fillStyle = LEAF_COLORS[i % 3]
        ctx.beginPath(); ctx.arc(tr.tx + math.cos(a) * r, tr.ty + math.sin(a) * r * 0.7 - 8, rad, 0, math.pi * 2); ctx.fill()


def drawTrees():
    for tr in trees:
        if tr.box.x < camX + VIEW_W + 80 and tr.box.x + tr.box.w > camX - 80:
            drawTree(tr)


# --- pixel text ---------------------------------------------------------
# A built-in 5x7 pixel font. Each glyph is 7 rows of 5 bits. Lowercase is drawn as uppercase.
_FONT_SRC = {
    'A': '01110 10001 10001 11111 10001 10001 10001', 'B': '11110 10001 10001 11110 10001 10001 11110',
    'C': '01110 10001 10000 10000 10000 10001 01110', 'D': '11110 10001 10001 10001 10001 10001 11110',
    'E': '11111 10000 10000 11110 10000 10000 11111', 'F': '11111 10000 10000 11110 10000 10000 10000',
    'G': '01110 10001 10000 10111 10001 10001 01111', 'H': '10001 10001 10001 11111 10001 10001 10001',
    'I': '01110 00100 00100 00100 00100 00100 01110', 'J': '00111 00010 00010 00010 00010 10010 01100',
    'K': '10001 10010 10100 11000 10100 10010 10001', 'L': '10000 10000 10000 10000 10000 10000 11111',
    'M': '10001 11011 10101 10101 10001 10001 10001', 'N': '10001 10001 11001 10101 10011 10001 10001',
    'O': '01110 10001 10001 10001 10001 10001 01110', 'P': '11110 10001 10001 11110 10000 10000 10000',
    'Q': '01110 10001 10001 10001 10101 10010 01101', 'R': '11110 10001 10001 11110 10100 10010 10001',
    'S': '01111 10000 10000 01110 00001 00001 11110', 'T': '11111 00100 00100 00100 00100 00100 00100',
    'U': '10001 10001 10001 10001 10001 10001 01110', 'V': '10001 10001 10001 10001 10001 01010 00100',
    'W': '10001 10001 10001 10101 10101 10101 01010', 'X': '10001 10001 01010 00100 01010 10001 10001',
    'Y': '10001 10001 10001 01010 00100 00100 00100', 'Z': '11111 00001 00010 00100 01000 10000 11111',
    '0': '01110 10001 10011 10101 11001 10001 01110', '1': '00100 01100 00100 00100 00100 00100 01110',
    '2': '01110 10001 00001 00010 00100 01000 11111', '3': '11111 00010 00100 00010 00001 10001 01110',
    '4': '00010 00110 01010 10010 11111 00010 00010', '5': '11111 10000 11110 00001 00001 10001 01110',
    '6': '00110 01000 10000 11110 10001 10001 01110', '7': '11111 00001 00010 00100 01000 01000 01000',
    '8': '01110 10001 10001 01110 10001 10001 01110', '9': '01110 10001 10001 01111 00001 00010 01100',
    ' ': '00000 00000 00000 00000 00000 00000 00000', '.': '00000 00000 00000 00000 00000 01100 01100',
    ',': '00000 00000 00000 00000 01100 00100 01000', '!': '00100 00100 00100 00100 00100 00000 00100',
    '?': '01110 10001 00001 00010 00100 00000 00100', "'": '00100 00100 01000 00000 00000 00000 00000',
    '"': '01010 01010 01010 00000 00000 00000 00000', '-': '00000 00000 00000 11111 00000 00000 00000',
    '+': '00000 00100 00100 11111 00100 00100 00000', ':': '00000 01100 01100 00000 01100 01100 00000',
    ';': '00000 01100 01100 00000 01100 00100 01000', '/': '00000 00001 00010 00100 01000 10000 00000',
    '(': '00010 00100 01000 01000 01000 00100 00010', ')': '01000 00100 00010 00010 00010 00100 01000',
    '=': '00000 00000 11111 00000 11111 00000 00000', '*': '00000 00100 10101 01110 10101 00100 00000',
    '<': '00010 00100 01000 10000 01000 00100 00010', '>': '01000 00100 00010 00001 00010 00100 01000',
    '#': '01010 01010 11111 01010 11111 01010 01010', '&': '01100 10010 10100 01000 10101 10010 01101',
    '%': '11000 11001 00010 00100 01000 10011 00011', '$': '00100 01111 10100 01110 00101 11110 00100',
    '@': '01110 10001 00001 01101 10101 10101 01110', '_': '00000 00000 00000 00000 00000 00000 11111',
}
PIXEL_FONT = {ch: [int(r, 2) for r in src.split(' ')] for ch, src in _FONT_SRC.items()}

# Every letter is the same size (5x7 pixels at TEXT_SCALE), and lines only break where
# the text has a newline. (x, y) is the top-left corner of the first letter.
TEXT_SCALE = 3


def pixelTextSize(text):
    s = TEXT_SCALE
    lines = text.upper().split('\n')
    return O(lines=lines, w=max(1, max(len(l) for l in lines)) * 6 * s - s, h=len(lines) * 9 * s - 2 * s)


_ptext_cache = {}


def _pixel_text_surface(text, col, k):
    key = (text, col, round(k, 3))
    surf = _ptext_cache.get(key)
    if surf is not None:
        return surf
    s = TEXT_SCALE * k
    sz = pixelTextSize(text)
    w, h = max(1, int(math.ceil(sz.w * k)) + 2), max(1, int(math.ceil(sz.h * k)) + 2)
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    rgb = color(col)[:3]
    for li, line in enumerate(sz.lines):
        ly = li * 9 * s
        for ci, ch in enumerate(line):
            g = PIXEL_FONT.get(ch) or PIXEL_FONT['?']
            for row in range(7):
                bits = g[row]
                col_i = 0
                while col_i < 5:
                    if not bits & (16 >> col_i):
                        col_i += 1
                        continue
                    run = 1
                    while col_i + run < 5 and bits & (16 >> (col_i + run)):
                        run += 1
                    x0 = (ci * 6 + col_i) * s
                    y0 = ly + row * s
                    r = pygame.Rect(int(round(x0)), int(round(y0)), max(1, int(round(x0 + run * s)) - int(round(x0))),
                                    max(1, int(round(y0 + s)) - int(round(y0))))
                    surf.fill(rgb + (255,), r)
                    col_i += run
    if len(_ptext_cache) > 600:
        _ptext_cache.clear()
    _ptext_cache[key] = surf
    return surf


# Pure decoration: no hitbox.
def drawPixelText(text, x, y, col=None):
    col = col or '#2b2f36'
    if ctx.aligned() and ctx.m[0] > 0:
        k = ctx.m[0]
        surf = _pixel_text_surface(text, col, k)
        X, Y = ctx.pt(x, y)
        a = color(col)[3] / 255 * ctx.globalAlpha
        if a < 0.999:
            surf = surf.copy()
            surf.set_alpha(int(255 * a))
        ctx.surf.blit(surf, (int(round(X)), int(round(Y))))
        return
    # turned or flipped: letter by letter
    s = TEXT_SCALE
    ctx.fillStyle = col
    for li, line in enumerate(pixelTextSize(text).lines):
        ly = y + li * 9 * s
        for ci, ch in enumerate(line):
            g = PIXEL_FONT.get(ch) or PIXEL_FONT['?']
            for row in range(7):
                for c in range(5):
                    if g[row] & (16 >> c):
                        ctx.fillRect(x + (ci * 6 + c) * s, ly + row * s, s + 0.5, s + 0.5)


def drawTexts():
    for t in texts:
        if t.hideIf:
            t.alpha = approach(1 if t.alpha is None else t.alpha, 0 if t.hideIf() else 1, 0.04)
        if t.alpha == 0 or t.x >= camX + VIEW_W or t.x + t.w <= camX:
            continue
        ctx.globalAlpha = 1 if t.alpha is None else t.alpha
        drawPixelText(t.text, t.x, t.y, t.color)
        ctx.globalAlpha = 1


# --- houses: flat cut-out walls, roof, windows and a door (all scenery) -------
def drawHouses():
    for h in houses:
        if h.x > camX + VIEW_W + T or h.x + h.w < camX - T:
            continue
        top, cx = h.floor - 3 * T, h.x + h.w / 2
        ctx.fillStyle = '#7a3b2e'   # chimney
        ctx.fillRect(h.x + h.w - T * 1.2, top - T * 2.4, T * 0.6, T * 1.6)
        ctx.fillStyle = '#c0392b'   # roof
        ctx.beginPath(); ctx.moveTo(h.x - T, top); ctx.lineTo(cx, top - 3 * T); ctx.lineTo(h.x + h.w + T, top); ctx.closePath(); ctx.fill()
        ctx.fillStyle = '#f2e3c6'   # walls
        ctx.fillRect(h.x, top, h.w, 3 * T)
        for wx in (h.x + T * 0.3, h.x + h.w - T * 1.3):   # windows
            ctx.fillStyle = '#8fd3ff'; ctx.fillRect(wx, top + T * 0.5, T, T)
            ctx.fillStyle = '#f2e3c6'; ctx.fillRect(wx + T / 2 - 2, top + T * 0.5, 4, T); ctx.fillRect(wx, top + T - 2, T, 4)
    for d in doors:
        if d.x > camX + VIEW_W or d.x + d.w < camX:
            continue
        jig = math.sin(simTime * 70) * 2 if d.lockedT > 1 else 0   # rattles when locked
        if d.hole:
            drawHole(d)
            if P.state != 'dead' and overlap(P.x, P.y, P.w, P.h, d.x + 4, d.y, d.w - 8, d.h):
                drawUpArrow(d.x + d.w / 2, d.y - 18)
            continue
        if d.framed:
            ctx.fillStyle = '#7a5232'; ctx.fillRect(d.x - 3, d.y - 2, d.w + 6, d.h + 2)
        ctx.fillStyle = '#8d5a3b'; ctx.fillRect(d.x + 3 + jig, d.y + 4, d.w - 6, d.h - 4)
        ctx.fillStyle = '#f1c40f'; ctx.beginPath(); ctx.arc(d.x + d.w - 9 + jig, d.y + d.h * 0.55, 3, 0, math.pi * 2); ctx.fill()
        near = P.state != 'dead' and overlap(P.x, P.y, P.w, P.h, d.x + 4, d.y, d.w - 8, d.h)
        if d.lockedT > 0:
            ctx.globalAlpha = min(1, d.lockedT * 2)
            msg = 'COMING SOON'
            sz = pixelTextSize(msg)
            drawPixelText(msg, d.x + d.w / 2 - sz.w / 2, d.y - 3 * T - 40, '#2b2f36')
            ctx.globalAlpha = 1
        elif near:
            drawUpArrow(d.x + d.w / 2, d.y - 18)


# Little bouncing arrow: press Up here.
def drawUpArrow(x, y):
    ay = y + math.sin(simTime * 6) * 3
    ctx.fillStyle = '#2b2f36'
    ctx.beginPath(); ctx.moveTo(x, ay - 9); ctx.lineTo(x - 8, ay); ctx.lineTo(x + 8, ay); ctx.closePath(); ctx.fill()
    ctx.fillRect(x - 3, ay, 6, 7)


# --- Bob the Square: bob.png, switching to bobtalking.png and back with each word he says
BOB_SPRITE = (23, 27, 16, 16)   # where Bob is inside the 64 x 64 pictures


# Grandma Charlie (images/grandma.png), curled up on her couch. She bobs a little while she talks.
def drawGrandma(n):
    if not grandmaImg.naturalWidth:
        return
    talking = npcTalking(n) and unitsShown(n) < lineUnits(n)
    b = math.sin(simTime * 1.6 + n.x) * 0.02 + (abs(math.sin(simTime * 14)) * 0.035 if talking else 0)
    w = 104 * (1 + b * 0.5)
    h = w * grandmaImg.naturalHeight / grandmaImg.naturalWidth * (1 - b * 1.5)
    ctx.drawImage(grandmaImg, n.x - w / 2, n.feet + 8 - h, w, h)


def drawNpcs():
    for n in npcs:
        if n.kind == 'bob' and stuff.bobGone:
            continue
        if n.x < camX - 60 or n.x > camX + VIEW_W + 60:
            continue
        if n.kind == 'grandma':
            drawGrandma(n)
            continue
        img = bobTalkImg if (bobTalkMouth(n) if n.kind == 'bobTalk' else bobMouthOpen(n)) else bobImg
        if not img.naturalWidth:
            continue
        w = h = 36   # Bob stays completely stiff
        ctx.imageSmoothingEnabled = False   # crisp pixel art
        ctx.drawImage(img, *BOB_SPRITE, n.x - w / 2, n.feet - h, w, h)
        ctx.imageSmoothingEnabled = True


def drawCheckpoints():
    for cp in checkpoints:
        ctx.fillStyle = '#555'; ctx.fillRect(cp.x - 2, cp.y - 64, 4, 64)
        ctx.fillStyle = '#27ae60' if cp.active else '#aab2bd'
        wave = math.sin(simTime * 6) * (3 if cp.active else 1)
        ctx.beginPath()
        ctx.moveTo(cp.x + 2, cp.y - 64); ctx.lineTo(cp.x + 26, cp.y - 56 + wave); ctx.lineTo(cp.x + 2, cp.y - 46)
        ctx.closePath(); ctx.fill()


def drawFinish():
    if not finish:
        return
    x, y = finish.x, finish.y
    ctx.fillStyle = '#555'; ctx.fillRect(x - 3, y - 110, 6, 110)
    for r in range(4):
        for c in range(6):
            ctx.fillStyle = '#111' if (r + c) % 2 else '#fff'
            ctx.fillRect(x + 3 + c * 8, y - 110 + r * 8 + math.sin(simTime * 5 + c) * 1.5, 8, 8)


def wrapText(text, maxW):
    words, lines = text.split(' '), []
    line = ''
    for w in words:
        test = line + ' ' + w if line else w
        if ctx.measureText(test) > maxW and line:
            lines.append(line); line = w
        else:
            line = test
    if line:
        lines.append(line)
    return lines


def drawSigns():
    ctx.font = font(600, 13)
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle'
    for s in signs:
        if s.x < camX - 200 or s.x > camX + VIEW_W + 200:
            continue
        lines = wrapText(s.text, 190)
        h, w = len(lines) * 17 + 16, 210
        top = s.y - 70 - h
        ctx.fillStyle = '#7a6a55'; ctx.fillRect(s.x - 3, top + h, 6, 70)
        ctx.fillStyle = '#fffaf0'; ctx.strokeStyle = '#7a6a55'; ctx.lineWidth = 3
        ctx.beginPath(); ctx.roundRect(s.x - w / 2, top, w, h, 6); ctx.fill(); ctx.stroke()
        ctx.fillStyle = '#3a3226'
        for i, ln in enumerate(lines):
            ctx.fillText(ln, s.x, top + 8 + 8.5 + i * 17)


def drawParticles():
    for p in particles:
        ctx.globalAlpha = max(0, p.life / p.max)
        ctx.fillStyle = p.color
        ctx.fillRect(p.x - p.size / 2, p.y - p.size / 2, p.size, p.size)
    ctx.globalAlpha = 1


def drawPopups():
    ctx.font = font(800, 15)
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle'
    for p in popups:
        ctx.globalAlpha = min(1, p.t * 2.5)
        ctx.fillStyle = p.color; ctx.fillText(p.text, p.x, p.y)
    ctx.globalAlpha = 1


# --- Charlie ----------------------------------------------------------
# Charlie is one photo. All of the animation is squash, stretch, tilt and hop.
def drawPlayer():
    for l in flyingLegs:
        drawTurkeyImg(l.x, l.y, 30, l.rot, min(1, (1.6 - l.t) * 3))
    if P.state == 'dead' or not charlieImg.naturalWidth:
        return
    if P.immune > 0 and math.floor(P.immune * 14) % 2 == 0:
        return   # blinking
    cx, feet = P.x + P.w / 2, P.y + P.h
    if P.wings:
        drawWings(cx, feet - CHARLIE_H * 0.62, 22 if held('up') else 10, 1)
    spd = min(1, abs(P.vx) / PHYS.runMax)
    s, rot, lean, hop, jitter = P.squash, 0, 0, 0, 0

    if celebrate:
        # happy jelly wiggle while holding the Greenie up
        t = celebrate.t
        s = math.sin(t * 16) * 0.35 * math.exp(-t * 1.1) - 0.15
        hop = min(1, t * 3) * 8
    elif P.onGround and P.state == 'normal':
        if spd > 0.05:
            # boing-boing run: squash on each footfall, stretch between them
            s += math.sin(P.runPhase * 2) * 0.22 * spd
            hop = abs(math.sin(P.runPhase)) * 7 * spd
            lean = 0.18 * spd
        else:
            s += math.sin(simTime * 3) * 0.04   # breathing
    if P.state == 'slide':
        lean = -0.3
    if P.state == 'crouch' and abs(P.vx) > 10:
        lean = math.sin(simTime * 18) * 0.15   # waddle
    if P.state == 'dive':
        rot = 0.55
    if P.state == 'smash':
        jitter = math.sin(simTime * 70) * 1.5
    if P.flipping:
        rot = P.flip
    if P.wallSliding:
        jitter = math.sin(simTime * 50) * 1

    s = max(-0.6, min(0.95, s))
    sx = 1 + s * 0.6
    sy = 1 / sx   # keep the "volume" roughly constant
    w, h = CHARLIE_W, CHARLIE_H

    ctx.save()
    ctx.translate(cx + jitter, feet - hop)
    ctx.scale(P.facing, 1)
    if rot:
        ctx.translate(0, -h * sy / 2); ctx.rotate(rot); ctx.translate(0, h * sy / 2)
    ctx.rotate(lean)
    ctx.scale(sx, sy)
    # with an eight pack he's the picture with the abs (images/charlie-stong.png)
    strong = P.eightPack and charlieStrongImg.naturalWidth
    ctx.drawImage(charlieStrongImg if strong else charlieImg, -w / 2, -h, w, h)
    if stuff.hat and hatImg.naturalWidth:
        # worn where it was put on in the closet (saved relative to Charlie's picture)
        hw = w * HAT_SIZE
        hh = hw * hatImg.naturalHeight / hatImg.naturalWidth
        ctx.translate(stuff.hat['x'] * w, -h + stuff.hat['y'] * h); ctx.rotate(stuff.hat['rot'])
        ctx.drawImage(hatImg, -hw / 2, -hh / 2, hw, hh)
    ctx.restore()

    if celebrate:
        drawGreenieIcon(cx, P.y - hop - 34, 1.5, celebrate.t * 5, 1)


# The bag, spinning on its vertical axis like a Power Moon.
def drawGreenieIcon(x, y, scale, spin, alpha):
    if not greenieImg.naturalWidth:
        return
    w, h = 30 * scale, 37 * scale
    c = math.cos(spin)
    ctx.save()
    ctx.globalAlpha = alpha
    ctx.translate(x, y)
    ctx.scale(max(0.08, abs(c)), 1)
    # the back of the bag is a bit darker
    ctx.drawImage(greenieBackImg if c < 0 else greenieImg, -w / 2, -h / 2, w, h)
    ctx.restore()


def drawGreenies():
    for g in greenies:
        if g.taken:
            continue
        if g.near and (P.state == 'dead' or max(abs(P.x + P.w / 2 - g.x), abs(P.y + P.h / 2 - g.y)) > g.near):
            continue
        ghost = g.id in greeniesGot   # already collected on an earlier play
        bob = math.sin(simTime * 2.5 + g.x) * 4
        if not ghost:
            ctx.fillRadial(g.x, g.y + bob, 4, 40, [(0, 'rgba(201,242,122,0.7)'), (1, 'rgba(201,242,122,0)')])
            if random() < 0.06:
                spawnParticle(g.x + (random() - 0.5) * 34, g.y + (random() - 0.5) * 40, 0, -30, 0.6, 3, '#fff6a8', 0)
        drawGreenieIcon(g.x, g.y + bob, 1, simTime * 2.2 + g.x, 0.35 if ghost else 1)


# --- chickens: one photo, wobbling side to side as they waddle -----------
def drawChickenAt(cx, feet, facing, rot, alpha=1):
    if not chickenImg.naturalWidth:
        return
    h = CK_DRAW_H
    w = h * chickenImg.naturalWidth / chickenImg.naturalHeight
    ctx.save()
    ctx.globalAlpha = alpha
    ctx.translate(cx, feet)
    ctx.scale(-facing, 1)   # the picture faces left
    ctx.rotate(rot)
    ctx.drawImage(chickenImg, -w / 2, -h, w, h)
    ctx.restore()


def drawChickens(cull=True):
    for ck in chickens:
        if not ck.alive or ck.held:
            continue
        cx, feet = ck.x + ck.w / 2, ck.y + ck.h
        if cull and (cx < camX - 80 or cx > camX + VIEW_W + 80):
            continue
        if ck.mode == 'flying':
            # tumbling through the air: spin around the middle
            ctx.save(); ctx.translate(cx, feet - ck.h / 2); ctx.rotate(ck.phase * 18)
            drawChickenAt(0, CK_DRAW_H / 2, ck.facing, 0)
            ctx.restore()
            continue
        moving = abs(ck.vx) > 5
        speed = 16 if ck.mode == 'chase' else 10
        rot = math.sin(ck.phase * speed) * 0.2 if moving else math.sin(ck.phase * 3) * 0.05
        if ck.stunT > 0:
            rot = math.sin(ck.phase * 40) * 0.25
        hop = abs(math.sin(ck.phase * speed)) * 3 if ck.onGround and moving else 0
        drawChickenAt(cx, feet - hop, ck.facing, rot)
        if ck.alertT > 0:
            drawPixelText('!', cx - 7, feet - CK_DRAW_H - 26, '#d63031')


def drawThrown():
    for b in thrown:
        ctx.save()
        ctx.translate(b.x + b.w / 2, b.y + b.h / 2); ctx.rotate(b.spin)
        drawTile(b.c, -T / 2, -T / 2)
        ctx.restore()


# The inhale: a see-through wedge with wind lines rushing into Charlie's mouth.
def drawInhaleCone():
    if not inhale or inhale.phase != 'suck':
        return
    mx, my = mouth()
    a = math.atan2(inhale.aim.y, inhale.aim.x)
    k = inhale.t / INHALE.suckTime
    ctx.fillStyle = 'rgba(255,255,255,%.3f)' % (0.12 + 0.3 * k)
    ctx.beginPath(); ctx.moveTo(mx, my); ctx.arc(mx, my, INHALE.range, a - INHALE.halfAngle, a + INHALE.halfAngle); ctx.closePath(); ctx.fill()
    ctx.strokeStyle = 'rgba(255,255,255,0.85)'; ctx.lineWidth = 3
    ctx.beginPath()
    for i in range(7):
        la = a + (i / 6 - 0.5) * INHALE.halfAngle * 1.6
        r = (1 - ((simTime * 3 + i * 0.37) % 1)) * INHALE.range
        ctx.moveTo(mx + math.cos(la) * r, my + math.sin(la) * r)
        ctx.lineTo(mx + math.cos(la) * max(8, r - 22), my + math.sin(la) * max(8, r - 22))
    ctx.stroke()


def drawSlurps():
    mx, my = mouth()
    for s in slurps:
        k = s.t * s.t
        sc = 1 - 0.8 * k
        ctx.save()
        ctx.translate(s.x + (mx - s.x) * k, s.y + (my - s.y) * k)
        ctx.scale(sc, sc); ctx.rotate(s.t * 6)
        if s.c:
            drawTile(s.c, -T / 2, -T / 2)
        elif s.ck:
            drawChickenAt(0, CK_DRAW_H / 2, s.ck.facing, 0)
        else:
            drawSweetPotato(0, 0, 0)
        ctx.restore()


def _celebrate_keep(t):
    return t


def drawCelebrationBackdrop():
    # spotlight on Charlie, everything else dimmed
    k = min(1, celebrate.t * 4)
    px, py = P.x + P.w / 2, P.y
    dark = pygame.Surface((VIEW_W, VIEW_H), pygame.SRCALPHA)
    dark.fill((10, 12, 16, int(0.7 * k * 255)))
    mask = hole_mask(40, 420, _celebrate_keep)
    X, Y = ctx.pt(px, py)
    dark.blit(mask, (int(X) - 420, int(Y) - 420), special_flags=pygame.BLEND_RGBA_MULT)
    ctx.surf.blit(dark, (0, 0))
    # rotating light rays behind the Greenie
    ctx.save()
    ctx.translate(px, py - 40)
    ctx.rotate(celebrate.t * 0.8)
    ctx.fillStyle = 'rgba(232,255,170,%.3f)' % (0.25 * k)
    for _ in range(12):
        ctx.rotate(math.pi / 6)
        ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(-14, 220 * k); ctx.lineTo(14, 220 * k); ctx.closePath(); ctx.fill()
    ctx.restore()


def drawCelebrationBanner():
    t = celebrate.t
    pop = 0.6 + (t / 0.25) * 0.55 if t < 0.25 else 1.15 - ((t - 0.25) / 0.15) * 0.15 if t < 0.4 else 1
    ctx.save()
    ctx.translate(VIEW_W / 2, 110)
    ctx.scale(pop, pop)
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle'
    ctx.font = font(900, 46)
    ctx.lineWidth = 8; ctx.strokeStyle = '#1f4d12'; ctx.strokeText('You got a Greenie!', 0, 0)
    ctx.fillStyle = '#c9f27a'; ctx.fillText('You got a Greenie!', 0, 0)
    ctx.font = font(700, 20)
    ctx.lineWidth = 5; ctx.strokeStyle = '#1b1e23'; ctx.strokeText(celebrate.g.name, 0, 44)
    ctx.fillStyle = '#fff'; ctx.fillText(celebrate.g.name, 0, 44)
    ctx.restore()
    if t > 0.9:
        ctx.textAlign = 'center'; ctx.font = font(600, 13)
        ctx.fillStyle = 'rgba(255,255,255,0.75)'; ctx.fillText('Press jump to continue', VIEW_W / 2, 186)


def drawDebug():
    ctx.strokeStyle = '#ff00ff'; ctx.lineWidth = 1
    ctx.strokeRect(P.x + 0.5, P.y + 0.5, P.w - 1, P.h - 1)
    for l in lasers:
        ctx.strokeStyle = 'rgba(255,0,255,0.4)'; ctx.strokeRect(l.x - 5, l.y0, 10, l.y1 - l.y0)


# Stamina, bottom left: 8 cells. While Charlie holds an inhale it turns red and counts down.
def drawStamina():
    cell, gap, bh, x = 22, 3, 16, 16
    y = VIEW_H - 16 - bh - 12
    holding = inhale and inhale.phase == 'hold'
    barX, barW = x + 34, STAMINA_MAX * (cell + gap) - gap
    label = '%.1f' % inhale.t if holding else ''
    ctx.font = font(700, 16, 'mono')
    lw = ctx.measureText(label) + 12 if label else 0
    ctx.fillStyle = 'rgba(20,22,26,0.6)'
    ctx.beginPath(); ctx.roundRect(x - 4, y, barW + 34 + 12 + lw, bh + 24, 8); ctx.fill()
    drawSweetPotato(x + 14, y + 20, -0.2)
    blink = staminaFlash > 0 and math.floor(staminaFlash * 10) % 2 == 0   # tried to inhale without enough
    for i in range(STAMINA_MAX):
        cx, cy = barX + i * (cell + gap), y + 12
        ctx.fillStyle = 'rgba(229,57,53,0.55)' if blink else 'rgba(255,255,255,0.15)'
        ctx.fillRect(cx, cy, cell, bh)
        amount = inhale.t / INHALE.holdTime * STAMINA_MAX if holding else stamina
        f = max(0, min(1, amount - i))
        if f > 0:
            ctx.fillStyle = '#e53935' if holding else '#f39237'
            ctx.fillRect(cx, cy, cell * f, bh)
    if label:
        ctx.fillStyle = '#ff8a80'; ctx.textAlign = 'left'; ctx.textBaseline = 'middle'
        ctx.fillText(label, barX + barW + 10, y + 21)
    px = x - 4 + barW + 34 + 12 + lw + 8
    if P.eightPack:
        # the eight pack: one extra hit
        ctx.fillStyle = 'rgba(20,22,26,0.6)'
        ctx.beginPath(); ctx.roundRect(px, y, 40, bh + 24, 8); ctx.fill()
        drawTurkeyImg(px + 20, y + 20, 30, 0.5 + math.sin(simTime * 3) * 0.08)
        px += 48
    if P.wings:
        # wings: another extra hit
        ctx.fillStyle = 'rgba(20,22,26,0.6)'
        ctx.beginPath(); ctx.roundRect(px, y, 40, bh + 24, 8); ctx.fill()
        drawWings(px + 20, y + 20, 6, 0.8)


# Every greenie in the game (all areas' chunks, plus whatever is built right now).
allGreenieIds = None


def greenieCount():
    global allGreenieIds
    if allGreenieIds is None:
        allGreenieIds = set()
        for k in AREAS:
            for sec in AREAS[k]:
                if sec.chunk:
                    for g in sec.chunk.greenies:
                        allGreenieIds.add(g[3])
    for g in greenies:
        allGreenieIds.add(g.id)
    return sum(1 for id in greeniesGot if id in allGreenieIds)


def drawHUD():
    got = greenieCount()
    ctx.font = font(700, 18, 'mono')
    ctx.textAlign = 'left'; ctx.textBaseline = 'middle'
    ctx.fillStyle = 'rgba(20,22,26,0.6)'
    gw = 50 + ctx.measureText(str(got))
    ctx.beginPath(); ctx.roundRect(12, 12, gw, 40, 8); ctx.fill()
    drawGreenieIcon(32, 32, 0.8, 0, 1)
    ctx.fillStyle = '#c9f27a'; ctx.fillText(str(got), 50, 33)
    # diamonds, right next to the greenies
    dx, dn = 12 + gw + 8, str(len(stuff.diamonds))
    ctx.fillStyle = 'rgba(20,22,26,0.6)'
    ctx.beginPath(); ctx.roundRect(dx, 12, 44 + ctx.measureText(dn), 40, 8); ctx.fill()
    drawDiamondIcon(dx + 20, 32, 0.85)
    ctx.fillStyle = '#7fe8ff'; ctx.fillText(dn, dx + 36, 33)
    if not ui:
        drawStamina()
    if toast:
        ctx.font = font(700, 18); ctx.textAlign = 'center'
        tw = ctx.measureText(toast.text) + 32
        ctx.globalAlpha = min(1, toast.t * 2)
        ctx.fillStyle = 'rgba(20,22,26,0.8)'
        ctx.beginPath(); ctx.roundRect(VIEW_W / 2 - tw / 2, 14, tw, 40, 8); ctx.fill()
        ctx.fillStyle = '#fff'; ctx.fillText(toast.text, VIEW_W / 2, 35)
        ctx.globalAlpha = 1

    if not pygame.key.get_focused():
        ctx.font = font(700, 16); ctx.textAlign = 'center'
        msg = 'Click to play'
        mw = ctx.measureText(msg) + 28
        ctx.fillStyle = 'rgba(20,22,26,0.75)'
        ctx.beginPath(); ctx.roundRect(VIEW_W / 2 - mw / 2, VIEW_H / 2 - 20, mw, 40, 8); ctx.fill()
        ctx.fillStyle = '#fff'; ctx.fillText(msg, VIEW_W / 2, VIEW_H / 2 + 1)

    saveShown = not TEST_CODE and not ui
    if saveShown:
        drawSaveButton()
    if showTimer:
        m = math.floor(runTime / 60)
        sec = ('%.2f' % (runTime % 60)).rjust(5, '0')
        label = '%d:%s' % (m, sec)
        ctx.font = font(700, 18, 'mono')
        tw = ctx.measureText(label) + 24
        right = SAVE_BTN.x - 8 if saveShown else VIEW_W - 12
        ctx.fillStyle = 'rgba(20,22,26,0.6)'
        ctx.beginPath(); ctx.roundRect(right - tw, 12, tw, 40, 8); ctx.fill()
        ctx.fillStyle = '#fff'; ctx.textAlign = 'right'
        ctx.fillText(label, right - 12, 33)


# ---------------------------------------------------------------------
#  Boot: pictures
# ---------------------------------------------------------------------
def loadImages():
    global charlieImg, greenieImg, chickenImg, hatImg, mapImg, bobImg, bobTalkImg, grandmaImg, turkeyImg, charlieStrongImg
    global greenieBackImg
    charlieImg = Img('images/charlie.png')
    greenieImg = Img('images/greenie.png')
    chickenImg = Img('images/chicken.png')
    hatImg = Img('images/newspaperhat.png')
    mapImg = Img('images/geniemap.png')
    bobImg = Img('images/embed/bob.png')
    bobTalkImg = Img('images/embed/bobtalking.png')
    grandmaImg = Img('images/grandma.png')
    turkeyImg = Img('images/turkeyleg.png')
    charlieStrongImg = Img('images/charlie-stong.png')
    # the greenie's back: the same bag, a bit darker and greener
    greenieBackImg = Img('images/greenie.png')
    if greenieBackImg.surf:
        s = greenieBackImg.surf
        s.fill((166, 166, 166), special_flags=pygame.BLEND_RGB_MULT)
        s.fill((10, 31, 10), special_flags=pygame.BLEND_RGB_ADD)


# ---------------------------------------------------------------------
#  Things you keep: diamonds, the newspaper hat and the backpack.
#  Saved like greenies (save_data.json 'treats.stuff').
# ---------------------------------------------------------------------
STUFF_KEY = 'treats.stuff'


def _load_stuff():
    # hat: where it sits on Charlie (None = on its hook in the closet)
    # inv: backpack items [{ id, x, y }]; diamonds: ids of every diamond collected
    # gameName / realName: asked at the start of a fresh game; bobGone: Bob has left for good
    # flags: things changed for good in the world (a broken bridge: flags[id] = True)
    d = O(hat=None, inv=[], diamonds=[], gameName='', realName='', bobGone=False, flags={}, grandmaDone=False)
    if TEST_CODE:
        return d
    got = store_get(STUFF_KEY)
    if isinstance(got, dict):
        d.update(got)
    d.inv = [O(i) for i in (d.inv or [])]
    return d


stuff = _load_stuff()


def saveStuff():
    if TEST_CODE:
        return
    store_set(STUFF_KEY, stuff)


def resetStuff():   # names and Bob stay
    stuff.hat = None; stuff.inv = []; stuff.diamonds = []; stuff.flags = {}
    saveStuff()


# --- diamonds ------------------------------------------------------------
def drawDiamondIcon(x, y, s=1, alpha=1):
    ctx.save()
    ctx.globalAlpha = alpha
    ctx.translate(x, y); ctx.scale(s, s)
    ctx.fillStyle = '#7fe8ff'   # top
    ctx.beginPath(); ctx.moveTo(-12, -4); ctx.lineTo(-6, -10); ctx.lineTo(6, -10); ctx.lineTo(12, -4); ctx.closePath(); ctx.fill()
    ctx.fillStyle = '#2bb5e0'   # point
    ctx.beginPath(); ctx.moveTo(-12, -4); ctx.lineTo(12, -4); ctx.lineTo(0, 12); ctx.closePath(); ctx.fill()
    ctx.fillStyle = '#d4f8ff'   # shine
    ctx.beginPath(); ctx.moveTo(-6, -10); ctx.lineTo(-2, -4); ctx.lineTo(-12, -4); ctx.closePath(); ctx.fill()
    ctx.restore()


def drawDiamonds():
    for d in diamonds:
        if d.taken:
            continue
        ghost = d.id in stuff.diamonds   # collected on an earlier play
        drawDiamondIcon(d.x, d.y + math.sin(simTime * 3 + d.x * 0.05) * 3, 1, 0.35 if ghost else 1)
        if not ghost and random() < 0.04:
            spawnParticle(d.x + (random() - 0.5) * 24, d.y + (random() - 0.5) * 20, 0, -25, 0.5, 2, '#fff', 0)


# --- house furniture -----------------------------------------------------------
# Props you can open (Up in front of them, or a click).
def opensUI(p):
    return p.kind in ('closet', 'chest')


def drawProps():
    for p in props:
        if p.kind == 'light':
            drawCeilingLight(p)
        elif p.kind == 'closet':
            drawClosetProp(p)
        elif p.kind == 'chest':
            drawChestProp(p)
        elif p.kind == 'fireplace':
            drawFireplace(p)
        elif p.kind == 'couch':
            drawCouch(p)
        elif p.kind == 'table':
            drawTable(p)
        elif p.kind == 'chimney':
            drawChimney(p)
        if opensUI(p) and P.state != 'dead' and overlap(P.x, P.y, P.w, P.h, p.x, p.y, p.w, p.h):
            drawUpArrow(p.x + p.w / 2, p.y - 16)
    for i, tk in enumerate(turkeys):
        if tk.t <= 0:
            drawTurkeyImg(tk.x, tk.y + 2, 26, 1.25 + i * 0.25 - 0.25)


# Stones in rows, each a slightly different grey, with dark mortar between.
STONES = ['#77736d', '#6a6661', '#827d76', '#5f5b57', '#716c66']


def drawStones(x, y, w, h, seed=0):
    ctx.fillStyle = '#3a3836'; ctx.fillRect(x, y, w, h)
    sh = 12
    r = 0
    while r * sh < h:
        off = (r % 2) * 9
        c = -1
        while c * 18 < w:
            sx = x + c * 18 + off
            k = ((r * 7 + c * 13 + seed) % 5 + 5) % 5
            ctx.fillStyle = STONES[k]
            x0, x1 = max(x, sx + 1), min(x + w, sx + 17)
            if x1 > x0:
                ctx.fillRect(x0, y + r * sh + 1, x1 - x0, min(sh - 2, y + h - (y + r * sh + 1)))
            c += 1
        r += 1


def drawFireplace(p):
    x, y, w, h = p.x, p.y, p.w, p.h
    drawStones(x + 8, p.top, w - 16, y - p.top + 4, 3)   # the stack up to the ceiling
    drawStones(x, y, w, h, 1)
    ctx.fillStyle = '#4a4744'; ctx.fillRect(x - 6, y - 4, w + 12, 10)   # mantel
    ctx.fillStyle = '#5c3a21'; ctx.fillRect(x - 6, y - 10, w + 12, 7)
    # the opening, with logs and a fire in it
    ox, ow, oy, oh = x + 16, w - 32, y + 22, h - 22
    ctx.fillStyle = '#141010'
    ctx.beginPath(); ctx.moveTo(ox, oy + oh); ctx.lineTo(ox, oy + 18); ctx.quadraticCurveTo(ox + ow / 2, oy - 10, ox + ow, oy + 18)
    ctx.lineTo(ox + ow, oy + oh); ctx.closePath(); ctx.fill()
    fx, fy = ox + ow / 2, oy + oh - 8
    ctx.fillRadial(fx, fy - 10, 4, ow * 0.7, [(0, 'rgba(255,170,60,0.7)'), (1, 'rgba(255,120,30,0)')], clip=(ox, oy, ow, oh))
    for i in range(7):
        fl = math.sin(simTime * (9 + i * 1.7) + i * 2) * 0.5 + 0.5
        bx, fh = fx + (i - 3) * ow * 0.11, 18 + fl * 22 - abs(i - 3) * 4
        ctx.fillStyle = '#ff9f1c' if i % 2 else '#ff5e1a'
        ctx.beginPath(); ctx.moveTo(bx - 9, fy); ctx.quadraticCurveTo(bx - 4, fy - fh * 0.6, bx + math.sin(simTime * 7 + i) * 3, fy - fh)
        ctx.quadraticCurveTo(bx + 4, fy - fh * 0.6, bx + 9, fy); ctx.closePath(); ctx.fill()
    ctx.fillStyle = '#ffe27a'
    for i in range(3):
        fh = 10 + (math.sin(simTime * 11 + i * 3) * 0.5 + 0.5) * 10
        ctx.beginPath(); ctx.ellipse(fx + (i - 1) * 9, fy - fh / 2, 4, fh / 2, 0, 0, math.pi * 2); ctx.fill()
    ctx.fillStyle = '#5a361a'   # logs
    ctx.save(); ctx.translate(fx, fy + 2)
    ctx.rotate(0.18); ctx.fillRect(-ow * 0.32, -4, ow * 0.64, 8)
    ctx.rotate(-0.36); ctx.fillRect(-ow * 0.32, -4, ow * 0.64, 8)
    ctx.restore()


def drawCouch(p):
    x, y, w, h = p.x, p.y, p.w, p.h
    ctx.fillStyle = '#3d2212'   # carved wooden frame and legs
    ctx.fillRect(x + 6, y + h - 8, 6, 8); ctx.fillRect(x + w - 12, y + h - 8, 6, 8)
    ctx.fillStyle = '#7a1f2b'   # tall curved back
    ctx.beginPath(); ctx.moveTo(x + 4, y + h * 0.55); ctx.quadraticCurveTo(x + 6, y - 6, x + w * 0.3, y + 4)
    ctx.quadraticCurveTo(x + w / 2, y - 14, x + w * 0.7, y + 4); ctx.quadraticCurveTo(x + w - 6, y - 6, x + w - 4, y + h * 0.55)
    ctx.closePath(); ctx.fill()
    ctx.strokeStyle = '#c9a24a'; ctx.lineWidth = 2; ctx.stroke()   # gold trim
    ctx.fillStyle = '#93303d'; ctx.fillRect(x + 6, y + h * 0.5, w - 12, h * 0.32)   # seat cushion
    ctx.fillStyle = '#6a1a25'   # rolled arms
    for ax in (x, x + w - 16):
        ctx.beginPath(); ctx.roundRect(ax, y + h * 0.35, 16, h * 0.5, 7); ctx.fill()
    ctx.fillStyle = '#c9a24a'   # buttons in the back
    for i in range(1, 4):
        ctx.beginPath(); ctx.arc(x + w * i / 4, y + h * 0.25, 2, 0, math.pi * 2); ctx.fill()


def drawTable(p):
    x, y, w, h = p.x, p.y, p.w, p.h
    ctx.fillStyle = '#4a2c16'; ctx.fillRect(x + 6, y + 8, 6, h - 8); ctx.fillRect(x + w - 12, y + 8, 6, h - 8)
    ctx.fillStyle = '#6b4222'; ctx.fillRect(x, y, w, 9)
    ctx.fillStyle = '#e9e1cf'   # plate
    ctx.beginPath(); ctx.ellipse(x + w / 2, y - 1, w * 0.36, 5, 0, 0, math.pi * 2); ctx.fill()


def drawChimney(p):
    x, y, w, h = p.x, p.y, p.w, p.h
    drawStones(x, y + 6, w, h - 6, 7)
    ctx.fillStyle = '#4a4744'; ctx.fillRect(x - 4, y, w + 8, 8)   # cap


# Smoke out of chimneys, sparks out of fireplaces.
def updateProps(dt):
    for p in props:
        if p.kind not in ('chimney', 'fireplace'):
            continue
        if p.x + p.w < camX - 200 or p.x > camX + VIEW_W + 200:
            continue
        p.t -= dt
        if p.t > 0:
            continue
        if p.kind == 'chimney':
            p.t += 0.12
            g = 95 + math.floor(random() * 40)
            spawnParticle(p.x + p.w / 2 + (random() - 0.5) * 8, p.y - 2, 10 + random() * 14, -28 - random() * 18,
                          2.2 + random(), 7 + random() * 7, 'rgba(%d,%d,%d,0.55)' % (g, g, g), -6)
        else:
            p.t += 0.25 + random() * 0.3
            spawnParticle(p.x + p.w / 2 + (random() - 0.5) * p.w * 0.4, p.y + p.h - 26, (random() - 0.5) * 30,
                          -60 - random() * 50, 0.8, 2, '#ffb347' if random() < 0.5 else '#ffdd66', -20)
    # turkey legs on the table grow back
    for tk in turkeys:
        if tk.t > 0:
            tk.t -= dt


# The room is dark except near the fireplaces (whose light flickers).
def _dim_keep(t):
    # how much of the dark stays: 1 - (0.95 at the middle, 0.6 at t = 0.45, 0 at the edge)
    if t <= 0.45:
        a = 0.95 + (0.6 - 0.95) * (t / 0.45)
    else:
        a = 0.6 * (1 - (t - 0.45) / 0.55)
    return 1 - a


def drawDim():
    if not dimness:
        return
    dark = pygame.Surface((VIEW_W, VIEW_H), pygame.SRCALPHA)
    dark.fill((10, 5, 2, int(dimness * 255)))
    fires = [p for p in props if p.kind == 'fireplace']
    for p in fires:
        fx, fy = p.x + p.w / 2 - camX, p.y + p.h * 0.7 - camY
        r = 360 + math.sin(simTime * 8.3) * 12 + math.sin(simTime * 21.7) * 7
        r = int(round(r / 4) * 4)
        mask = hole_mask(30, r, _dim_keep)
        dark.blit(mask, (int(fx) - r, int(fy) - r), special_flags=pygame.BLEND_RGBA_MULT)
    ctx.surf.blit(dark, (0, 0))
    # a warm orange glow around the fire
    for p in fires:
        fx, fy = p.x + p.w / 2 - camX, p.y + p.h * 0.7 - camY
        s = radial_surface(10, 260, [(0, 'rgba(255,120,40,0.22)'), (1, 'rgba(255,120,40,0)')], premultiplied=True)
        ctx.surf.blit(s, (int(fx) - 260, int(fy) - 260), special_flags=pygame.BLEND_RGB_ADD)


def drawCeilingLight(p):
    ctx.fillRadial(p.x, p.y + 80, 10, 300, [(0, 'rgba(255,236,170,0.5)'), (1, 'rgba(255,236,170,0)')])
    ctx.fillStyle = '#7a7a7a'; ctx.fillRect(p.x - 10, p.y, 20, 5)   # ceiling plate
    ctx.fillStyle = '#555'; ctx.fillRect(p.x - 1, p.y, 2, 56)        # cord
    ctx.fillStyle = '#fff4c2'; ctx.beginPath(); ctx.arc(p.x, p.y + 82, 9, 0, math.pi * 2); ctx.fill()   # bulb
    ctx.fillStyle = '#3f6e5d'                                        # shade
    ctx.beginPath(); ctx.moveTo(p.x - 12, p.y + 56); ctx.lineTo(p.x + 12, p.y + 56); ctx.lineTo(p.x + 34, p.y + 84)
    ctx.lineTo(p.x - 34, p.y + 84); ctx.closePath(); ctx.fill()


def drawClosetProp(p):
    x, y, w, h = p.x, p.y, p.w, p.h
    ctx.fillStyle = '#5e3b1f'; ctx.fillRect(x, y, w, h)
    ctx.fillStyle = '#8a5a34'   # two doors
    ctx.fillRect(x + 5, y + 12, w / 2 - 7, h - 18); ctx.fillRect(x + w / 2 + 2, y + 12, w / 2 - 7, h - 18)
    ctx.fillStyle = '#4a2e16'; ctx.fillRect(x - 4, y, w + 8, 8)   # top
    ctx.fillStyle = '#e2c26a'
    for kx in (x + w / 2 - 7, x + w / 2 + 7):
        ctx.beginPath(); ctx.arc(kx, y + h / 2, 3, 0, math.pi * 2); ctx.fill()
    ctx.fillStyle = '#fdfcf5'; ctx.fillRect(x + 12, y + 40, 22, 26)   # the note, from outside
    ctx.fillStyle = '#1f4fd6'; ctx.fillRect(x + 15, y + 47, 16, 2); ctx.fillRect(x + 15, y + 54, 12, 2)


def drawChestProp(p):
    x, y, w, h = p.x, p.y, p.w, p.h
    ctx.fillStyle = '#4e321a'; ctx.fillRect(x, y + h * 0.38, w, h * 0.62)   # base
    ctx.fillStyle = '#62401f'                                                 # old rounded lid
    ctx.beginPath(); ctx.moveTo(x, y + h * 0.42); ctx.quadraticCurveTo(x + w / 2, y - h * 0.2, x + w, y + h * 0.42); ctx.closePath(); ctx.fill()
    ctx.fillStyle = '#3d3d3d'                                                 # iron bands
    for bx in (x + w * 0.2, x + w * 0.8):
        ctx.fillRect(bx - 4, y + h * 0.2, 8, h * 0.8)
    ctx.fillRect(x, y + h * 0.38, w, 5)
    ctx.fillStyle = '#a07a2c'; ctx.fillRect(x + w / 2 - 7, y + h * 0.44, 14, 16)   # rusty lock
    ctx.fillStyle = '#2b1a0c'; ctx.fillRect(x + w / 2 - 2, y + h * 0.52, 4, 6)
    ctx.fillStyle = 'rgba(111,138,58,0.85)'                                         # moss
    ctx.fillRect(x + 3, y + h - 6, 14, 6); ctx.fillRect(x + w - 22, y + h * 0.42, 12, 4)


# ---------------------------------------------------------------------
#  Screens you use with the mouse: the closet, the chest and the backpack.
#  The game pauses while one is open. Esc (or E) closes it.
# ---------------------------------------------------------------------
ui = None      # { kind: 'closet' | 'chest' | 'inventory' | 'save', drag, zoom, added }
toast = None   # { text, t }: a message at the top of the screen


def openUI(kind):
    global ui
    ui = O(kind=kind, drag=None, zoom=None, added=False)
    keys.clear()


def closeUI():
    global ui, toast
    if ui and ui.added:
        toast = O(text='Open your inventory with E', t=4)
    if ui and ui.kind == 'save':
        closePanel()
    ui = None


CLOSE_BTN = O(x=VIEW_W - 54, y=14, w=40, h=40)

# --- closet: drag the newspaper hat onto Charlie ---------------------------------
HAT_SIZE = 0.8   # the hat is 80% as wide as Charlie
CLOSET = O(x=130, y=30, w=700, h=480, railY=80, hooks=[200, 310, 420, 540, 650, 760], hatHook=4)
CL_CHARLIE = O(x=365, y=210, w=230, h=230 * CHARLIE_H / CHARLIE_W)
ROT_BTNS = [O(x=410, y=452, d=-1, label='<'), O(x=550, y=452, d=1, label='>')]


def hatDims():
    w = CL_CHARLIE.w * HAT_SIZE
    return w, w * (hatImg.naturalHeight / hatImg.naturalWidth if hatImg.naturalWidth else 0.55)


# Where the hat is on the closet screen (its center, and rotation).
def hatPlace():
    if ui.drag and ui.drag.what == 'hat':
        return ui.drag
    if stuff.hat:
        return O(x=CL_CHARLIE.x + CL_CHARLIE.w / 2 + stuff.hat['x'] * CL_CHARLIE.w, y=CL_CHARLIE.y + stuff.hat['y'] * CL_CHARLIE.h,
                 rot=stuff.hat['rot'])
    _, hh = hatDims()
    return O(x=CLOSET.hooks[CLOSET.hatHook] + 8, y=CLOSET.railY + 34 + hh / 2 - 12, rot=0)   # on its hook


def inRotBox(px, py, b, w, h):
    c, s = math.cos(-b.rot), math.sin(-b.rot)
    dx, dy = px - b.x, py - b.y
    return abs(dx * c - dy * s) <= w / 2 and abs(dx * s + dy * c) <= h / 2


# How much of the hat (0..1) covers Charlie's picture, by sampling points across it.
def hatCoverage(b):
    w, h = hatDims()
    c, s, C = math.cos(b.rot), math.sin(b.rot), CL_CHARLIE
    inside = 0
    for i in range(12):
        for j in range(8):
            lx, ly = ((i + 0.5) / 12 - 0.5) * w, ((j + 0.5) / 8 - 0.5) * h
            px, py = b.x + lx * c - ly * s, b.y + lx * s + ly * c
            if C.x <= px <= C.x + C.w and C.y <= py <= C.y + C.h:
                inside += 1
    return inside / 96


def turnHat(d):
    step = d * math.pi / 12
    if ui.drag and ui.drag.what == 'hat':
        ui.drag.rot += step
    elif stuff.hat:
        stuff.hat['rot'] += step
        saveStuff()


# --- chest + backpack ----------------------------------------------------------
CHEST_BOX = O(x=50, y=95, w=470, h=400)
CHEST_MAP = O(x=285, y=240)   # where the genie map lies in the chest
CHEST_DIAMONDS = [('chest1', 170, 420), ('chest2', 285, 432), ('chest3', 400, 420)]
PACK_AREA = O(x=20, y=55, w=300, h=360)   # inside of the backpack, from its corner
MAP_W = 170


def mapDims():
    return MAP_W, MAP_W * (mapImg.naturalHeight / mapImg.naturalWidth if mapImg.naturalWidth else 0.72)


def packOrigin():
    return O(x=575, y=75) if ui.kind == 'chest' else O(x=VIEW_W / 2 - 170, y=75)


def mapInChest():
    return not any(i.id == 'geniemap' for i in stuff.inv)


# --- mouse --------------------------------------------------------------------
def uiDown(x, y):
    if ui.zoom:
        ui.zoom = None
        return
    if overlap(x, y, 1, 1, CLOSE_BTN.x, CLOSE_BTN.y, CLOSE_BTN.w, CLOSE_BTN.h):
        closeUI()
        return
    if ui.kind == 'save':
        return

    def grab(what, cx, cy, **extra):
        ui.drag = O(what=what, x=cx, y=cy, ox=cx - x, oy=cy - y, sx=x, sy=y, moved=False, **extra)
    if ui.kind == 'closet':
        b = next((r for r in ROT_BTNS if math.hypot(x - r.x, y - r.y) <= 22), None)
        if b:
            turnHat(b.d)
            return
        h = hatPlace()
        w, hh = hatDims()
        if inRotBox(x, y, h, w, hh):
            grab('hat', h.x, h.y, rot=h.rot)
        return
    # backpack items first (they're drawn on top), then what's still in the chest
    o = packOrigin()
    mw, mh = mapDims()
    for it in reversed(stuff.inv):
        cx, cy = o.x + it.x, o.y + it.y
        if abs(x - cx) <= mw / 2 and abs(y - cy) <= mh / 2:
            grab('item', cx, cy, item=it)
            return
    if ui.kind != 'chest':
        return
    if mapInChest() and abs(x - CHEST_MAP.x) <= mw / 2 and abs(y - CHEST_MAP.y) <= mh / 2:
        grab('chestmap', CHEST_MAP.x, CHEST_MAP.y)
        return
    for id, dx, dy in CHEST_DIAMONDS:
        if id not in stuff.diamonds and math.hypot(x - dx, y - dy) < 28:
            stuff.diamonds.append(id); saveStuff()
            return


def uiMove(x, y):
    d = ui.drag
    if not d:
        return
    d.x = x + d.ox; d.y = y + d.oy
    if math.hypot(x - d.sx, y - d.sy) > 5:
        d.moved = True


def uiUp(*_):
    d = ui.drag
    if not d:
        return
    ui.drag = None
    if d.what == 'hat':
        if not d.moved:
            return
        # at least a quarter of it over Charlie counts as wearing it, right where it was dropped
        C = CL_CHARLIE
        stuff.hat = {'x': (d.x - C.x - C.w / 2) / C.w, 'y': (d.y - C.y) / C.h, 'rot': d.rot} if hatCoverage(d) >= 0.25 else None
        saveStuff()
        return
    if not d.moved:
        ui.zoom = 'map'   # a click, not a drag: look at the map up close
        return
    # dropped inside the backpack: it stays exactly where it was put (anywhere else: it goes back)
    o = packOrigin()
    mw, mh = mapDims()
    A = PACK_AREA
    if not overlap(d.x, d.y, 1, 1, o.x + A.x, o.y + A.y, A.w, A.h):
        return
    x = max(A.x + mw / 2, min(A.x + A.w - mw / 2, d.x - o.x))
    y = max(A.y + mh / 2, min(A.y + A.h - mh / 2, d.y - o.y))
    if d.what == 'item':
        d.item.x = x; d.item.y = y
    else:
        stuff.inv.append(O(id='geniemap', x=x, y=y)); ui.added = True
    saveStuff()


def uiWheel(x, y, d):
    h = hatPlace()
    w, hh = hatDims()
    if (ui.drag and ui.drag.what == 'hat') or inRotBox(x, y, h, w, hh):
        turnHat(d)


# --- drawing the screens ------------------------------------------------------------
def drawUI():
    ctx.fillStyle = 'rgba(15,17,21,0.72)'; ctx.fillRect(0, 0, VIEW_W, VIEW_H)
    if ui.kind == 'closet':
        drawClosetScreen()
    elif ui.kind == 'save':
        pass
    else:
        if ui.kind == 'chest':
            drawChestScreen()
        else:
            drawTopText('INVENTORY', 'E or Esc to close')
        o = packOrigin()
        mw, mh = mapDims()
        drawBackpack(o.x, o.y)
        for it in stuff.inv:
            if not ui.drag or ui.drag.item is not it:
                drawMapCard(o.x + it.x, o.y + it.y, mw, mh)
        if ui.drag:
            drawMapCard(ui.drag.x, ui.drag.y, mw, mh, True)
    # close button
    b = CLOSE_BTN
    ctx.fillStyle = 'rgba(255,255,255,0.9)'; ctx.beginPath(); ctx.roundRect(b.x, b.y, b.w, b.h, 8); ctx.fill()
    ctx.strokeStyle = '#2b2f36'; ctx.lineWidth = 4
    ctx.beginPath(); ctx.moveTo(b.x + 12, b.y + 12); ctx.lineTo(b.x + b.w - 12, b.y + b.h - 12)
    ctx.moveTo(b.x + b.w - 12, b.y + 12); ctx.lineTo(b.x + 12, b.y + b.h - 12); ctx.stroke()
    if ui.zoom and mapImg.naturalWidth:
        ctx.fillStyle = 'rgba(10,12,16,0.85)'; ctx.fillRect(0, 0, VIEW_W, VIEW_H)
        k = min(840 / mapImg.naturalWidth, 470 / mapImg.naturalHeight)
        w, h = mapImg.naturalWidth * k, mapImg.naturalHeight * k
        ctx.drawImage(mapImg, VIEW_W / 2 - w / 2, 22, w, h)


def drawTopText(main, sub=None):
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle'
    ctx.font = font(800, 24); ctx.fillStyle = '#fff'; ctx.fillText(main, VIEW_W / 2, 32)
    if sub:
        ctx.font = font(500, 14); ctx.fillStyle = 'rgba(255,255,255,0.75)'; ctx.fillText(sub, VIEW_W / 2, 60)


def drawMapCard(x, y, w, h, lifted=False):
    if not mapImg.naturalWidth:
        return
    ctx.save()
    if lifted:
        ctx.shadow = (0.5, 6)
    ctx.drawImage(mapImg, x - w / 2, y - h / 2, w, h)
    ctx.restore()


def drawClosetScreen():
    c = CLOSET
    ctx.fillStyle = '#3e2612'; ctx.fillRect(c.x - 14, c.y - 14, c.w + 28, c.h + 28)   # frame
    ctx.fillStyle = '#7b5130'; ctx.fillRect(c.x, c.y, c.w, c.h)                        # back wall
    ctx.fillStyle = 'rgba(0,0,0,0.13)'
    x = c.x + 70
    while x < c.x + c.w:
        ctx.fillRect(x, c.y, 3, c.h)
        x += 70
    ctx.fillStyle = '#5a391c'; ctx.fillRect(c.x, c.y + c.h - 44, c.w, 44)              # closet floor
    # rail and hooks
    ctx.fillStyle = '#bdbdbd'; ctx.fillRect(c.x + 24, c.railY - 4, c.w - 48, 8)
    ctx.strokeStyle = '#dcdcdc'; ctx.lineWidth = 5
    for hx in c.hooks:
        ctx.beginPath(); ctx.moveTo(hx, c.railY); ctx.lineTo(hx, c.railY + 24)
        ctx.arc(hx + 8, c.railY + 24, 8, math.pi, 0, True); ctx.lineTo(hx + 16, c.railY + 16)
        ctx.stroke()
    drawClosetNote(158, 245)
    # Charlie, standing in the middle
    C = CL_CHARLIE
    ctx.fillStyle = 'rgba(0,0,0,0.25)'
    ctx.beginPath(); ctx.ellipse(C.x + C.w / 2, C.y + C.h + 2, 100, 10, 0, 0, math.pi * 2); ctx.fill()
    if charlieImg.naturalWidth:
        ctx.drawImage(charlieImg, C.x, C.y, C.w, C.h)
    if hatImg.naturalWidth:
        h = hatPlace()
        w, hh = hatDims()
        ctx.save()
        ctx.translate(h.x, h.y); ctx.rotate(h.rot)
        if ui.drag:
            ctx.shadow = (0.5, 6)
        ctx.drawImage(hatImg, -w / 2, -hh / 2, w, hh)
        ctx.restore()
    # turn buttons
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.font = font(700, 22)
    for b in ROT_BTNS:
        ctx.fillStyle = 'rgba(255,255,255,0.9)'; ctx.beginPath(); ctx.arc(b.x, b.y, 20, 0, math.pi * 2); ctx.fill()
        # a curved arrow, turning the way the button turns the hat
        ctx.strokeStyle = '#2b2f36'; ctx.lineWidth = 3
        ctx.beginPath(); ctx.arc(b.x, b.y, 9, -math.pi * 0.9, math.pi * 0.4) if b.d > 0 else ctx.arc(b.x, b.y, 9, math.pi * 0.6, math.pi * 1.9)
        ctx.stroke()
        ax, ay = (b.x + math.cos(math.pi * 0.4) * 9, b.y + math.sin(math.pi * 0.4) * 9) if b.d > 0 else \
            (b.x + math.cos(math.pi * 0.6) * 9, b.y + math.sin(math.pi * 0.6) * 9)
        ctx.fillStyle = '#2b2f36'
        ctx.beginPath(); ctx.moveTo(ax - 5, ay - 3); ctx.lineTo(ax + 5, ay - 3); ctx.lineTo(ax, ay + 4); ctx.closePath(); ctx.fill()
    ctx.font = font(700, 16); ctx.fillStyle = 'rgba(255,255,255,0.9)'
    ctx.fillText('Scroll', (ROT_BTNS[0].x + ROT_BTNS[1].x) / 2, ROT_BTNS[0].y + 1)


# Lined paper taped to the closet wall, in blue marker.
def drawClosetNote(x, y):
    ctx.save()
    ctx.translate(x, y); ctx.rotate(-0.06)
    ctx.fillStyle = '#fdfcf5'; ctx.fillRect(0, 0, 190, 140)
    ctx.strokeStyle = '#a9c7ea'; ctx.lineWidth = 1.5
    ctx.beginPath()
    for ly in range(30, 140, 18):
        ctx.moveTo(0, ly); ctx.lineTo(190, ly)
    ctx.stroke()
    ctx.strokeStyle = '#e9a3a3'; ctx.beginPath(); ctx.moveTo(26, 0); ctx.lineTo(26, 140); ctx.stroke()
    ctx.fillStyle = 'rgba(236,226,186,0.85)'   # tape
    for tx, r in ((0, -0.6), (190, 0.6)):
        ctx.save(); ctx.translate(tx, 2); ctx.rotate(r); ctx.fillRect(-22, -8, 44, 16); ctx.restore()
    ctx.fillStyle = '#1f4fd6'
    ctx.font = font(700, 30, 'marker')
    ctx.textAlign = 'left'; ctx.textBaseline = 'alphabetic'
    ctx.fillText('GET MORE', 36, 66)
    ctx.fillText('CLOTHES', 36, 104)
    ctx.restore()


def drawChestScreen():
    drawTopText('Open your inventory with E')
    b = CHEST_BOX
    ctx.fillStyle = '#2f1c0b'; ctx.fillRect(b.x - 14, b.y - 14, b.w + 28, b.h + 28)   # old dark rim
    ctx.fillStyle = '#6b4524'; ctx.fillRect(b.x, b.y, b.w, b.h)                        # wooden inside
    ctx.fillStyle = 'rgba(0,0,0,0.2)'
    y = b.y + 50
    while y < b.y + b.h:
        ctx.fillRect(b.x, y, b.w, 3)   # planks
        y += 50
    ctx.fillStyle = 'rgba(255,255,255,0.05)'
    for i in range(9):
        ctx.fillRect(b.x + 30 + i * 47, b.y + 10 + (i * 37) % 300, 60, 2)   # worn scratches
    ctx.fillStyle = '#474747'   # iron corners
    for cx, cy, sx, sy in ((b.x, b.y, 1, 1), (b.x + b.w, b.y, -1, 1), (b.x, b.y + b.h, 1, -1), (b.x + b.w, b.y + b.h, -1, -1)):
        ctx.fillRect(cx if sx > 0 else cx - 40, cy if sy > 0 else cy - 10, 40, 10)
        ctx.fillRect(cx if sx > 0 else cx - 10, cy if sy > 0 else cy - 40, 10, 40)
        ctx.fillStyle = '#8a8a8a'; ctx.beginPath(); ctx.arc(cx + sx * 5, cy + sy * 5, 2.5, 0, math.pi * 2); ctx.fill()
        ctx.fillStyle = '#474747'
    if mapInChest() and not (ui.drag and ui.drag.what == 'chestmap'):
        drawMapCard(CHEST_MAP.x, CHEST_MAP.y, *mapDims())
    for id, dx, dy in CHEST_DIAMONDS:
        if id not in stuff.diamonds:
            drawDiamondIcon(dx, dy, 1.7)


# A plain backpack shape, filled solid white (no grid): items sit wherever they're dropped.
def drawBackpack(ox, oy):
    ctx.fillStyle = ctx.strokeStyle = '#fff'
    ctx.lineWidth = 14
    ctx.beginPath(); ctx.arc(ox + 170, oy + 60, 40, math.pi, 0); ctx.stroke()   # handle
    ctx.fillRect(ox + 4, oy + 150, 20, 200); ctx.fillRect(ox + 316, oy + 150, 20, 200)   # straps
    ctx.beginPath(); ctx.roundRect(ox + 20, oy + 55, 300, 360, [70, 70, 34, 34]); ctx.fill()   # body


enterStreak, lastEnter = 0, -INF   # Enter x5 quickly = reset all greenies (and everything you've kept)

# ---------------------------------------------------------------------
#  Save codes and names
#  The Save button (top right) turns everything you've done into a code.
#  Paste it in the box on the start screen to carry on; start without one
#  and it's a fresh game, which asks for your real name.
#  (The same codes work in the browser version.)
# ---------------------------------------------------------------------
SAVE_PREFIX = 'TREATSAVE1:'
SAVE_BTN = O(x=VIEW_W - 12 - 84, y=12, w=84, h=40)


def playerName():
    return stuff.realName or stuff.gameName or 'traveler'


# Places are saved as tiles from the corner of the chunk they're in (by chunk name).
def spotOf(px, py):
    sp = next((o for o in sectionSpans if not o.pad and o.x0 * T <= px < o.x1 * T and o.y0 * T <= py <= o.y1 * T), None) \
        or next((o for o in sectionSpans if not o.pad and o.x0 * T <= px < o.x1 * T), None)
    return {'s': sp.name, 'x': round(px / T - sp.x0, 2), 'y': round(py / T - sp.y0, 2)} if sp else None


def spotAt(spot):
    sp = next((o for o in sectionSpans if o.name == spot['s']), None) if spot else None
    return O(x=(sp.x0 + spot['x']) * T, y=(sp.y0 + spot['y']) * T) if sp else None


def makeSaveCode():
    return SAVE_PREFIX + b64encode(js_json({
        'g': list(greeniesGot), 'h': stuff.hat, 'i': stuff.inv, 'd': stuff.diamonds,
        'n': stuff.gameName, 'r': stuff.realName, 'b': stuff.bobGone, 'f': stuff.flags, 'gm': stuff.grandmaDone,
        'st': stamina, 'ep': bool(P.eightPack), 'wg': bool(P.wings), 'df': difficulty,
        # where you are: the area, where Charlie stands, and the checkpoint you'd respawn at
        'l': {'a': areaName, 'at': spotOf(P.x + P.w / 2, P.y + P.h),
              'cp': lastCp.spot if lastCp else spotOf(respawnPoint.x, respawnPoint.y),
              'ca': lastCp.area if lastCp else areaName},
    }))


def loadSaveCode(code):
    global difficulty
    code = ''.join(code.split())
    if not code.startswith(SAVE_PREFIX):
        raise ValueError('not a save code')
    d = json.loads(b64decode(code[len(SAVE_PREFIX):]))
    greeniesGot.clear()
    for id in d.get('g') or []:
        greeniesGot.add(id)
    saveGreenies()
    stuff.update(hat=d.get('h') or None, inv=[O(i) for i in (d.get('i') or [])], diamonds=d.get('d') or [],
                 gameName=d.get('n') or '', realName=d.get('r') or '', bobGone=bool(d.get('b')), flags=d.get('f') or {},
                 grandmaDone=bool(d.get('gm')))
    saveStuff()
    difficulty = 'easy' if d.get('df') == 'easy' else 'hard'   # (codes from before Easy existed are Hard)
    return d


def freshStart():
    greeniesGot.clear(); saveGreenies()
    stuff.update(hat=None, inv=[], diamonds=[], gameName='', realName='', bobGone=False, flags={}, grandmaDone=False)
    saveStuff()


# --- boxes you type into or click, drawn over the game (the browser's HTML layer) ----------------
saveBox = O(visible=False, text='', focus=False, x=VIEW_W / 2 - 220, y=424, w=440, h=36,
            placeholder='Paste a save code here (leave it empty to start fresh)')
panel = None   # O(kind='ask' | 'diff' | 'save', ...)


def closePanel():
    global panel
    panel = None


# A box in the middle of the screen with a question; calls back with the answer.
def ask(question, cb):
    global panel
    closePanel()
    panel = O(kind='ask', question=question, text='', cb=cb, shakeT=0)


# Easy or Hard, for a fresh game: a box with a button and a description for each.
DIFFICULTIES = [
    O(id='easy', label='Easy', text='Best for newer players without much platforming experience. The game will breeze through much quicker, and might be less rewarding.'),
    O(id='hard', label='Hard', text='The intended experience. Best for players who have played and are decently skilled at games like OvO, and expect hard challenges that might take a while to complete, but the game will be much more rewarding.'),
]


def askDifficulty(cb):
    global panel
    closePanel()
    panel = O(kind='diff', cb=cb)


# The Save button: shows your save code (and copies it).
def openSave():
    global panel
    openUI('save')
    closePanel()
    code = makeSaveCode()
    panel = O(kind='save', code=code, copied=clipboard_set(code))


def drawSaveButton():
    b = SAVE_BTN
    ctx.fillStyle = 'rgba(20,22,26,0.6)'
    ctx.beginPath(); ctx.roundRect(b.x, b.y, b.w, b.h, 8); ctx.fill()
    ctx.font = font(800, 17); ctx.textAlign = 'center'; ctx.textBaseline = 'middle'
    ctx.fillStyle = '#fff'; ctx.fillText('SAVE', b.x + b.w / 2, b.y + b.h / 2 + 1)


def _wrap_px(text, f, maxW):
    words, lines, line = text.split(' '), [], ''
    for w in words:
        test = line + ' ' + w if line else w
        if f.size(test)[0] > maxW and line:
            lines.append(line); line = w
        else:
            line = test
    if line:
        lines.append(line)
    return lines


def _button(x, y, w, h, label, go=False, hover=False):
    ctx.fillStyle = ('#4ea347' if hover else '#3f8f3a') if go else ('#38404b' if hover else '#2d333d')
    ctx.beginPath(); ctx.roundRect(x, y, w, h, 8); ctx.fill()
    ctx.strokeStyle = '#4ea347' if go else '#3a404b'; ctx.lineWidth = 1; ctx.stroke()
    if label:
        ctx.font = font(600, 15); ctx.textAlign = 'center'; ctx.textBaseline = 'middle'
        ctx.fillStyle = '#fff'; ctx.fillText(label, x + w / 2, y + h / 2)


def _input(x, y, w, h, text, focus, placeholder='', mono=False, colr='#fff'):
    ctx.fillStyle = '#15181d'; ctx.beginPath(); ctx.roundRect(x, y, w, h, 8); ctx.fill()
    ctx.strokeStyle = '#5cbf4a' if focus else '#3a404b'; ctx.lineWidth = 2; ctx.stroke()
    ctx.font = font(400, 15)
    ctx.textAlign = 'left'; ctx.textBaseline = 'middle'
    shown = text
    while shown and ctx.measureText(shown) > w - 26:
        shown = shown[1:]   # long text: show its end
    if shown:
        ctx.fillStyle = colr; ctx.fillText(shown, x + 12, y + h / 2)
    elif placeholder:
        ctx.fillStyle = 'rgba(255,255,255,0.4)'; ctx.fillText(placeholder, x + 12, y + h / 2)
    if focus and int(time.perf_counter() * 2) % 2 == 0:
        cx = x + 12 + (ctx.measureText(shown) if shown else 0) + 1
        ctx.fillStyle = '#fff'; ctx.fillRect(cx, y + 9, 2, h - 18)


def _panel_box(x, y, w, h):
    ctx.fillStyle = 'rgba(0,0,0,0.35)'; ctx.beginPath(); ctx.roundRect(x + 2, y + 10, w, h, 12); ctx.fill()
    ctx.fillStyle = '#1f2329'; ctx.beginPath(); ctx.roundRect(x, y, w, h, 12); ctx.fill()


def panelLayout():
    """Where the current panel's parts are: (box, {name: rect})."""
    p = panel
    if p.kind == 'ask':
        x, y, w = VIEW_W / 2 - 220, 150, 440
        return (x, y, w, 158), {'input': (x + 22, y + 56, w - 44, 40), 'ok': (x + w - 22 - 64, y + 110, 64, 36)}
    if p.kind == 'diff':
        x, y, w = VIEW_W / 2 - 260, 95, 520
        f = font(400, 14)
        parts, by = {}, y + 58
        for d in DIFFICULTIES:
            lines = _wrap_px(d.text, f, w - 44 - 32)
            bh = 24 + 26 + len(lines) * 20
            parts[d.id] = (x + 22, by, w - 44, bh)
            by += bh + 10
        return (x, y, w, by - y + 12), parts
    x, y, w = VIEW_W / 2 - 220, 150, 440
    return (x, y, w, 240), {'code': (x + 22, y + 56, w - 44, 110), 'copy': (x + w - 22 - 84 - 8 - 74, y + 182, 74, 36),
                            'close': (x + w - 22 - 74, y + 182, 74, 36)}


def drawOverlay():
    mx, my = cursor or (-1, -1)

    def hover(r):
        return overlap(mx, my, 1, 1, *r)
    ctx.setTransform()
    if saveBox.visible:
        _input(saveBox.x, saveBox.y, saveBox.w, saveBox.h, saveBox.text, saveBox.focus, saveBox.placeholder)
    if not panel:
        return
    box, parts = panelLayout()
    _panel_box(*box)
    x, y = box[0], box[1]
    ctx.textAlign = 'left'; ctx.textBaseline = 'middle'
    if panel.kind == 'ask':
        ctx.font = font(700, 20); ctx.fillStyle = '#fff'; ctx.fillText(panel.question, x + 22, y + 34)
        ix, iy, iw, ih = parts['input']
        jig = math.sin(panel.shakeT * 60) * 6 if panel.shakeT > 0 else 0
        _input(ix + jig, iy, iw, ih, panel.text, True)
        _button(*parts['ok'], 'OK', True, hover(parts['ok']))
    elif panel.kind == 'diff':
        ctx.font = font(700, 20); ctx.fillStyle = '#fff'; ctx.fillText('Choose a difficulty', x + 22, y + 34)
        for d in DIFFICULTIES:
            r = parts[d.id]
            _button(*r, '', d.id == 'hard', hover(r))
            ctx.textAlign = 'left'; ctx.textBaseline = 'middle'
            ctx.font = font(700, 19); ctx.fillStyle = '#fff'; ctx.fillText(d.label, r[0] + 16, r[1] + 24)
            f = font(400, 14)
            ctx.font = f
            for i, line in enumerate(_wrap_px(d.text, f, r[2] - 32)):
                ctx.fillText(line, r[0] + 16, r[1] + 50 + i * 20)
    else:
        ctx.font = font(700, 20); ctx.fillStyle = '#fff'; ctx.fillText('Your save code', x + 22, y + 34)
        cx, cy, cw, ch = parts['code']
        ctx.fillStyle = '#15181d'; ctx.beginPath(); ctx.roundRect(cx, cy, cw, ch, 8); ctx.fill()
        ctx.strokeStyle = '#3a404b'; ctx.lineWidth = 2; ctx.stroke()
        f = font(400, 12, 'mono')
        ctx.font = f; ctx.fillStyle = '#c9f27a'; ctx.textBaseline = 'top'
        per = max(1, int((cw - 20) / f.size('M')[0]))
        lines = [panel.code[i:i + per] for i in range(0, len(panel.code), per)]
        for i, line in enumerate(lines[:6]):
            ctx.fillText(line, cx + 10, cy + 8 + i * 16)
        if len(lines) > 6:
            ctx.fillText('...', cx + 10, cy + 8 + 6 * 16)
        _button(*parts['copy'], 'Copied!' if panel.copied else 'Copy', False, hover(parts['copy']))
        _button(*parts['close'], 'Close', True, hover(parts['close']))


def overlayClick(x, y):
    """A click on the boxes over the game. Returns True if they used it."""
    if panel:
        box, parts = panelLayout()
        if panel.kind == 'ask':
            if overlap(x, y, 1, 1, *parts['ok']):
                askDone()
        elif panel.kind == 'diff':
            for d in DIFFICULTIES:
                if overlap(x, y, 1, 1, *parts[d.id]):
                    cb = panel.cb
                    closePanel(); cb(d.id)
                    return True
        else:
            if overlap(x, y, 1, 1, *parts['copy']):
                panel.copied = clipboard_set(panel.code)
            elif overlap(x, y, 1, 1, *parts['close']):
                closeUI()
                return True
        if overlap(x, y, 1, 1, *box):
            return True
    if saveBox.visible:
        saveBox.focus = overlap(x, y, 1, 1, saveBox.x, saveBox.y, saveBox.w, saveBox.h)
        if saveBox.focus:
            return True
    return False


def askDone():
    v = panel.text.strip()
    if not v:
        panel.shakeT = 0.3
        return
    cb = panel.cb
    closePanel(); cb(v)


def overlayKey(e):
    """Typing into a box. Returns True if the key went into one."""
    global panel
    target = None
    if panel and panel.kind == 'ask':
        target = 'ask'
    elif saveBox.visible and saveBox.focus:
        target = 'save'
    if not target:
        return False
    obj = panel if target == 'ask' else saveBox
    if e.key == pygame.K_RETURN or e.key == pygame.K_KP_ENTER:
        if target == 'ask':
            askDone()
        elif menu:
            continueSave()
    elif e.key == pygame.K_BACKSPACE:
        obj.text = obj.text[:-1]
        if target == 'save' and menu:
            menu.error = ''
    elif e.key == pygame.K_v and (e.mod & pygame.KMOD_CTRL):
        obj.text += clipboard_get().replace('\n', '').replace('\r', '')
        if target == 'ask':
            obj.text = obj.text[:30]
        elif menu:
            menu.error = ''
    elif e.key == pygame.K_ESCAPE and target == 'save':
        saveBox.focus = False
    return True


def overlayText(s):
    if panel and panel.kind == 'ask':
        panel.text = (panel.text + s)[:30]
        return True
    if saveBox.visible and saveBox.focus:
        saveBox.text += s
        if menu:
            menu.error = ''
        return True
    return False


# ---------------------------------------------------------------------
#  Bob the Square talks once you walk past him. Click to go to the next
#  line. When you've passed him and he goes off screen, he's gone for good.
# ---------------------------------------------------------------------
BOB_LINES = [
    lambda name: "What's up %s?" % name,
    lambda name: "I'm Bob the Square, a Square who loves greeting travelers!",
    lambda name: 'Well %s, one tip to get you started on your journey is left click to inhale, and click again to exhale! You inhale and exhale toward your cursor, which can be useful!' % name,
    lambda name: 'Have a good day %s!' % name,
]
# Grandma Charlie, on her couch. She starts talking when you come in.
GRANDMA_LINES = [
    "Oh my dear Charlie, I'm so glad to see you!",
    "Help yourself to as much turkey legs as you'd like!",
    "Oh deary, if only I had some treats to eat, all of my diet is just turkey legs!",
    "I just wish I had a still-life of treats, so I can remember the old days where I could eat as much treats as I want.",
]
# ...and on later visits, once you've heard all of that (stuff.grandmaDone)
GRANDMA_AGAIN = [
    "Oh, the old days...",
    "Charlie, my dear, could you please find me a beautiful still-life of treats, I need it.",
]
bobHint = True   # "Click to continue" shows until the first click
WORD_TIME = 0.15     # Bob: seconds between words
LETTER_TIME = 0.035  # Grandma: seconds between letters


def byLetter(n):
    return n.kind == 'grandma'


def unitTime(n):
    return LETTER_TIME if byLetter(n) else WORD_TIME


def npcLines(n):
    return [f(playerName()) for f in BOB_LINES] if n.kind == 'bob' else n.lines


def npcTalking(n):
    return n.kind != 'bobTalk' and n.talk is not None and 0 <= n.talk < len(npcLines(n)) and not (n.kind == 'bob' and stuff.bobGone)


def npcLine(n):
    return npcLines(n)[n.talk]


def lineUnits(n):
    return len(npcLine(n)) if byLetter(n) else len(npcLine(n).split(' '))


def unitsShown(n):
    return min(lineUnits(n), math.floor(n.wordT / unitTime(n)) + 1)


# mouth open on every other word, shut once the line is all out
def bobMouthOpen(n):
    return npcTalking(n) and unitsShown(n) < lineUnits(n) and unitsShown(n) % 2 == 1


def updateNpcs(dt):
    for n in npcs:
        if n.kind == 'bobTalk':
            updateBobTalk(n, dt)
            continue
        if n.kind == 'bob' and stuff.bobGone:
            continue
        if n.talk is None:
            n.talk = -1
        onScreen = n.x + 40 >= camX and n.x - 40 <= camX + VIEW_W
        # Bob starts once you've walked past him, Grandma as soon as you come in
        if n.talk < 0 and P.state != 'dead' and (P.x > n.x + 18 if n.kind == 'bob' else onScreen):
            n.talk = 0; n.wordT = 0
        if n.talk < 0:
            continue
        n.wordT += dt
        if n.kind == 'grandma':
            # got to her last line: next time you visit, she says something else
            if n.lines is GRANDMA_LINES and n.talk >= len(GRANDMA_LINES) - 1 and not stuff.grandmaDone:
                stuff.grandmaDone = True; saveStuff()
            continue
        if onScreen:
            n.seen = True   # (only counts once he's actually been on screen talking)
        elif n.seen:
            stuff.bobGone = True; saveStuff()


# A click anywhere moves the talk along. Returns True if it was used.
def clickNpcs():
    global bobHint
    n = next((n for n in npcs if npcTalking(n)), None)
    if not n:
        return False
    # a click while still talking shows the rest of the line; after that, the next line
    if unitsShown(n) < lineUnits(n):
        n.wordT = lineUnits(n) * unitTime(n)
    else:
        n.talk += 1; n.wordT = 0
    bobHint = False
    return True


# Breaks text into lines of at most maxChars letters, between words.
def wrapWords(text, maxChars):
    out, line = [], ''
    for word in text.split(' '):
        test = line + ' ' + word if line else word
        if len(test) > maxChars and line:
            out.append(line); line = word
        else:
            line = test
    if line:
        out.append(line)
    return out


def _shown_lines(n, lines):
    left = unitsShown(n)
    shown = []
    for l in lines:
        if byLetter(n):
            shown.append(l[:max(0, left)]); left -= len(l) + 1
        else:
            w = l.split(' ')
            shown.append(' '.join(w[:max(0, left)])); left -= len(w)
    return shown


# What they say, in the same pixel text as the writing in the world, a few lines above their head.
BOB_WRAP = 22   # letters per line


def drawNpcTalk():
    for n in npcs:
        if n.kind == 'bobTalk':
            b = bobTalkBox(n)
            if b and b.inView:
                drawPixelText(b.text, b.x, b.y, '#000000')
            continue
        if not npcTalking(n):
            continue
        lines = wrapWords(npcLine(n), BOB_WRAP)
        sz = pixelTextSize('\n'.join(lines))
        hintH = 22 if bobHint else 0
        # fixed in the world above their head, like any other writing (it scrolls away with them)
        x, y = n.x - sz.w / 2, n.feet - (n.head or 36) - 20 - hintH - sz.h
        drawPixelText('\n'.join(_shown_lines(n, lines)), x, y, '#ffffff' if byLetter(n) else '#000000')
        if bobHint:
            # smaller, under the words
            ctx.save()
            ctx.translate(x, y + sz.h + 10); ctx.scale(2 / 3, 2 / 3)
            drawPixelText('Click to continue', 0, 0, '#d9cfc2' if byLetter(n) else '#6b7380')
            ctx.restore()


# ---------------------------------------------------------------------
#  Start menu: play the tutorial, or go straight to the main game.
#  Esc brings it back.
# ---------------------------------------------------------------------
MENU_ITEMS = [O(label='TUTORIAL', to='Tutorial'), O(label='PLAY', to='Main')]
menu = None   # { sel, error, asking } while the menu is open


def menuButton(i):
    return O(x=VIEW_W / 2 - 150, y=250 + i * 86, w=300, h=66)


# `code` fills the save box (Esc in the middle of a game puts your progress there).
def openMenu(code=''):
    global menu
    # the tutorial's warp greenie collected? then PLAY is picked to start with
    done = any(id in greeniesGot for id in GREENIE_WARPS)
    menu = O(sel=1 if done else 0, error='', asking=False)
    saveBox.text = code; saveBox.visible = True; saveBox.focus = False


def chooseMenu(i):
    if menu.asking:
        return
    code = saveBox.text.strip()
    if code:
        try:
            loadSaveCode(code)
        except Exception:
            menu.error = "That save code didn't work"
            return
        startGame(i)
        return
    # no save code: a fresh game. Your name (Bob greets you with it), then Easy or Hard.
    # Easy first has Bob try to talk you out of it.
    freshStart()
    menu.asking = True
    saveBox.visible = False

    def named(realName):
        stuff.realName = realName; saveStuff()

        def picked(d):
            global difficulty
            difficulty = d
            if d == 'easy':
                startEasyScene(i)
            else:
                startGame(i)
        askDifficulty(picked)
    ask('What is your real name?', named)


# Enter in the save box: load the save and go right back to where it was made.
def continueSave():
    global menu, deaths, runTime, finished, lastCp, areaGrids, stamina
    if menu.asking:
        return
    code = saveBox.text.strip()
    if not code:
        chooseMenu(menu.sel)
        return
    try:
        d = loadSaveCode(code)
    except Exception:
        menu.error = "That save code didn't work"
        return
    loc = d.get('l')
    if not loc or not areaExists(loc.get('a')):
        startGame(menu.sel)   # an old code without a place
        return
    menu = None
    saveBox.visible = False; saveBox.focus = False
    deaths = 0; runTime = 0; finished = False; lastCp = None; areaGrids = {}
    stamina = d.get('st') or 0
    startWarp(loc['a'], None, loc)
    P.eightPack = bool(d.get('ep')); P.wings = bool(d.get('wg'))


def startGame(i, white=False):
    global menu, stamina, deaths, runTime, finished, lastCp, areaGrids
    menu = None
    saveBox.visible = False; saveBox.focus = False
    stamina = 0; deaths = 0; runTime = 0; finished = False; P.eightPack = False; lastCp = None; areaGrids = {}
    startWarp(MENU_ITEMS[i].to, None, None, white)


# ---------------------------------------------------------------------
#  Picking Easy: a black screen with only Bob, trying to talk you out of it. Click to go
#  on; after his last line the screen fades to white and the game comes in.
# ---------------------------------------------------------------------
EASY_LINES = [
    'Oh, so you really want to do easy mode huh?',
    'Just too bad for the regular mode?',
    'You know, even if you are terrible at platformers, you should still play normal.',
    "It's a lot more rewarding, and you will still beat it, it just might take longer.",
    "Trust me, the creator's little brother played hard mode, and he really enjoyed it.",
    "So you still want to play easy mode, knowing that there is a 99.9% chance you shouldn't.",
    'If you keep clicking on this, that does mean you are going to do it.',
    "So like, given what I've been saying, you should probably stop clicking on it.",
    'Reload the page immediately, and choose hard mode.',
    '...',
    "I'm assuming that click was just an accident. Now reload the page.",
    'This is your last warning.',
    'I will torture you.',
    'I will torture your family.',
    'I will rip off all of your limbs and force you to live as a chicken nugget while I mentally edit your family and make them beat you over the head with your own limbs.',
    '...',
    'So you still want to play easy mode?',
    'You must be very desperate for the easiness.',
    'Fine then, go ahead.',
    'If you need it that bad.',
    'So just as a warning, as soon as you click this text, you will play easy mode.',
    'This will be final.',
    'Like, actually final.',
    'Like, final final final.',
    '...',
    'Go ahead and suffer.',
]
EASY_BOB = 3     # Bob drawn 3x his size in the world
EASY_WRAP = 40   # letters per line
easyScene = None   # { n: Bob (an npc, so he talks like the one in the world), menuItem }


def startEasyScene(i):
    global easyScene
    easyScene = O(n=O(kind='sceneBob', x=VIEW_W / 2, feet=430, lines=EASY_LINES, talk=0, wordT=0), menuItem=i)


def clickEasyScene():
    n = easyScene.n
    if warp:
        return
    if unitsShown(n) < lineUnits(n):
        n.wordT = lineUnits(n) * unitTime(n)
        return
    if n.talk < len(EASY_LINES) - 1:
        n.talk += 1; n.wordT = 0
        return
    startGame(easyScene.menuItem, True)   # fades to white; the scene goes once the game is in


def drawEasyScene():
    n = easyScene.n
    ctx.fillStyle = '#000'; ctx.fillRect(0, 0, VIEW_W, VIEW_H)
    img = bobTalkImg if bobMouthOpen(n) else bobImg
    if img.naturalWidth:
        w = h = 36 * EASY_BOB   # stiff, like in the world
        ctx.imageSmoothingEnabled = False
        ctx.drawImage(img, *BOB_SPRITE, n.x - w / 2, n.feet - h, w, h)
        ctx.imageSmoothingEnabled = True
    # his words above him, filled in a word at a time like in the world
    lines = wrapWords(npcLine(n), EASY_WRAP)
    sz = pixelTextSize('\n'.join(lines))
    x, y = n.x - sz.w / 2, n.feet - 36 * EASY_BOB - 30 - sz.h
    drawPixelText('\n'.join(_shown_lines(n, lines)), x, y, '#ffffff')


def drawMenu():
    ctx.fillStyle = 'rgba(20,22,26,0.55)'; ctx.fillRect(0, 0, VIEW_W, VIEW_H)
    title, big = 'TREATS', 3
    sz = pixelTextSize(title)
    ctx.save()
    ctx.translate(VIEW_W / 2 - sz.w * big / 2, 90); ctx.scale(big, big)
    drawPixelText(title, 0, 0, '#f39237')
    ctx.restore()
    for i, item in enumerate(MENU_ITEMS):
        b, on = menuButton(i), menu.sel == i
        ctx.fillStyle = '#5cbf4a' if on else 'rgba(255,255,255,0.16)'
        ctx.fillRect(b.x, b.y, b.w, b.h)
        ts = pixelTextSize(item.label)
        drawPixelText(item.label, b.x + b.w / 2 - ts.w / 2, b.y + b.h / 2 - ts.h / 2, '#15181d' if on else '#fff')
    ctx.font = font(600, 14); ctx.textAlign = 'center'; ctx.textBaseline = 'middle'
    ctx.fillStyle = 'rgba(255,255,255,0.8)'
    if menu.asking:
        return
    ctx.fillText('Up / Down to choose, Enter or Space to start. Enter in the box goes back to where you saved.', VIEW_W / 2, 506)
    if menu.error:
        ctx.fillStyle = '#ff8a80'; ctx.font = font(700, 14); ctx.fillText(menu.error, VIEW_W / 2, 480)


def menuKey(code):
    if menu.asking:
        return
    if code in BIND.up or code in BIND.down:
        menu.sel = (menu.sel + 1) % len(MENU_ITEMS)
    elif code in ('Enter', 'Space') or code in BIND.inhale:
        chooseMenu(menu.sel)


# ---------------------------------------------------------------------
#  Boot and the main loop
# ---------------------------------------------------------------------
KEY_NAMES = {
    pygame.K_LEFT: 'ArrowLeft', pygame.K_RIGHT: 'ArrowRight', pygame.K_UP: 'ArrowUp', pygame.K_DOWN: 'ArrowDown',
    pygame.K_SPACE: 'Space', pygame.K_LSHIFT: 'ShiftLeft', pygame.K_RSHIFT: 'ShiftRight',
    pygame.K_RETURN: 'Enter', pygame.K_KP_ENTER: 'Enter', pygame.K_ESCAPE: 'Escape', pygame.K_KP0: 'Numpad0',
}


def keyCode(e):
    if e.key in KEY_NAMES:
        return KEY_NAMES[e.key]
    if pygame.K_a <= e.key <= pygame.K_z:
        return 'Key' + chr(e.key).upper()
    if pygame.K_0 <= e.key <= pygame.K_9:
        return 'Digit' + chr(e.key)
    return 'Other%d' % e.key


def onKeyDown(e):
    global debug, showTimer, enterStreak, lastEnter
    if overlayKey(e):
        if e.key == pygame.K_ESCAPE and ui:
            closeUI()
        return
    code = keyCode(e)
    if menu:
        menuKey(code)
        return
    if warp:
        return
    if ui:
        if code in ('Escape', 'KeyE'):
            if ui.zoom:
                ui.zoom = None
            else:
                closeUI()
        return
    if code == 'KeyE':
        openUI('inventory')
        return
    if code == 'Escape' and not TEST_CODE and areaExists('Tutorial'):
        keys.clear(); openMenu(makeSaveCode())
        return
    if code == 'KeyR':
        if P.state != 'dead':
            respawn()
        return
    if code == 'Enter':
        now = time.perf_counter() * 1000
        enterStreak = enterStreak + 1 if now - lastEnter <= 500 else 1
        lastEnter = now
        if enterStreak >= 5:
            greeniesGot.clear(); saveGreenies(); resetStuff(); enterStreak = 0
        restartLevel()
        return
    if code == 'KeyH':
        debug = not debug
        return
    if code == 'KeyT':
        showTimer = not showTimer
        return
    keys.add(code); pressedKeys.add(code)


def onMouseDown(x, y, button):
    global cursor
    if overlayClick(x, y):
        return
    if easyScene:
        clickEasyScene()
        return
    if menu:
        for i in range(len(MENU_ITEMS)):
            b = menuButton(i)
            if overlap(x, y, 1, 1, b.x, b.y, b.w, b.h):
                chooseMenu(i)
        return
    if ui:
        uiDown(x, y)
        return
    if not TEST_CODE and not warp and overlap(x, y, 1, 1, SAVE_BTN.x, SAVE_BTN.y, SAVE_BTN.w, SAVE_BTN.h):
        openSave()
        return
    if clickNpcs():
        return
    # clicking the closet or chest in the world opens it
    p = None if warp else next((p for p in props if opensUI(p) and overlap(x + camX, y + camY, 1, 1, p.x, p.y, p.w, p.h)), None)
    if p:
        openUI(p.kind)
        return
    # anything else: a left click inhales (or spits) toward the cursor
    if button == 1 and not warp:
        cursor = (x, y); pressedKeys.add('Mouse0')


def boot():
    global screen, ctx, cursor
    pygame.init()
    pygame.display.set_caption('Treats')
    screen = pygame.display.set_mode((VIEW_W, VIEW_H), pygame.SCALED | pygame.RESIZABLE)
    ctx = Ctx(screen)
    loadImages()
    pygame.key.start_text_input()

    restartLevel()
    # the menu shows over the main game until you pick (not when play-testing a chunk)
    if not TEST_CODE and areaExists('Tutorial'):
        openMenu()
    clock = pygame.time.Clock()
    acc, last = 0.0, time.perf_counter()
    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                return
            if e.type == pygame.KEYDOWN:
                onKeyDown(e)
            elif e.type == pygame.KEYUP:
                keys.discard(keyCode(e))
            elif e.type == pygame.TEXTINPUT:
                overlayText(e.text)
            elif e.type == pygame.WINDOWFOCUSLOST:
                keys.clear()
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button in (1, 2, 3):
                onMouseDown(e.pos[0], e.pos[1], e.button)
            elif e.type == pygame.MOUSEMOTION:
                cursor = e.pos
                if ui:
                    uiMove(*e.pos)
            elif e.type == pygame.MOUSEBUTTONUP and e.button in (1, 2, 3):
                if ui:
                    uiUp(*e.pos)
            elif e.type == pygame.MOUSEWHEEL:
                if ui and ui.kind == 'closet' and cursor:
                    uiWheel(cursor[0], cursor[1], -sign(e.y))
        now = time.perf_counter()
        acc += min(0.1, now - last)
        last = now
        stepped = False
        while acc >= STEP:
            update(STEP)
            acc -= STEP
            if panel and panel.shakeT:
                panel.shakeT = max(0, panel.shakeT - STEP)
            if not stepped:
                pressedKeys.clear()
                stepped = True
        draw()
        pygame.display.flip()
        clock.tick(60)


# --- Bob who talks when things happen (t.talkingBob). Each line comes out a word at a time
# (*slow* words much slower), stays a few seconds, then he goes quiet. When he's off screen,
# his words show at the edge of the screen instead, so you still hear him.
SLOW_WORD = 0.8   # seconds for each *slow* word
SAY_HOLD = 4      # seconds a line stays once it's all out


def lineWords(line):
    import re
    out, t = [], 0
    for w in line.replace('{name}', playerName()).split(' '):
        out.append(O(w=w.replace('*', ''), at=t))
        t += SLOW_WORD if re.match(r'^\*.+\*\W*$', w) else WORD_TIME
    return out


def updateBobTalk(n, dt):
    if n.say:
        n.say.t += dt
    if P.state == 'dead':
        return
    cx, cy = P.x + P.w / 2, P.y + P.h / 2

    def tiles(x, y):   # diagonals count the same
        return max(abs(cx - x), abs(cy - y)) / T
    id = secretAt(math.floor(cx / T), math.floor(cy / T))
    for o in n.says:
        if o.done or (o.got and not any(g.id == o.got and g.taken for g in greenies)):
            continue
        if o.near is not None:
            now = tiles(n.x, n.feet - 18) <= o.near
        elif o.at:
            now = tiles(o.at[0], o.at[1]) <= o.at[2]
        elif o.secret:
            now = id > 0 and secrets[id - 1].name == o.secret
        else:
            now = False
        if not now:
            continue
        o.done = True
        n.say = O(words=lineWords(o.line), t=0)   # (a newer line cuts in)


def sayShown(say):
    return sum(1 for w in say.words if w.at <= say.t)


def bobTalkMouth(n):
    return bool(n.say) and sayShown(n.say) < len(n.say.words) and sayShown(n.say) % 2 == 1


# Where his words go above his head (world pixels), the words out so far, and whether it's on screen.
def bobTalkBox(n):
    say = n.say
    if not say or say.t > say.words[-1].at + SAY_HOLD:
        return None
    lines = wrapWords(' '.join(w.w for w in say.words), BOB_WRAP)
    left, shown = sayShown(say), []
    for l in lines:
        w = l.split(' ')
        shown.append(' '.join(w[:max(0, left)])); left -= len(w)
    sz = pixelTextSize('\n'.join(lines))
    x, y = n.x - sz.w / 2, n.feet - 36 - 20 - sz.h
    inView = x >= camX and x + sz.w <= camX + VIEW_W and y >= camY and y + sz.h <= camY + VIEW_H
    return O(text='\n'.join(shown), x=x, y=y, w=sz.w, h=sz.h, inView=inView)


# (screen space) Bob's words at the screen edge nearest him while he's out of sight.
def drawFarTalk():
    for n in npcs:
        if n.kind != 'bobTalk':
            continue
        b = bobTalkBox(n)
        if not b or b.inView:
            continue
        pad, k = 10, 0.8
        w, h = b.w * k + pad * 2, (b.h + 26) * k + pad * 2
        bx = max(10, min(VIEW_W - w - 10, n.x - camX - w / 2))
        by = 60 if n.feet < camY + VIEW_H / 2 else VIEW_H - h - 60   # (clear of the HUD)
        ctx.fillStyle = 'rgba(20,22,26,0.72)'
        ctx.beginPath(); ctx.roundRect(bx, by, w, h, 8); ctx.fill()
        ctx.save(); ctx.translate(bx + pad, by + pad); ctx.scale(k, k)
        drawPixelText('BOB:', 0, 0, '#ffb27a')
        drawPixelText(b.text, 0, 26, '#ffffff')
        ctx.restore()


# --- black hole doors (t.holeDoor): a black blot with a soft dark rim, slowly breathing
def drawHole(d):
    cx, cy, k = d.x + d.w / 2, d.y + d.h / 2, 1 + math.sin(simTime * 2.5 + d.x) * 0.04
    for sc, a in ((1.5, 0.12), (1.25, 0.25), (1.08, 0.5)):
        ctx.fillStyle = 'rgba(0,0,0,%s)' % a
        ctx.beginPath(); ctx.ellipse(cx, cy, d.w / 2 * sc * k, d.h / 2 * sc * k, 0, 0, math.pi * 2); ctx.fill()
    ctx.fillStyle = '#040406'
    ctx.beginPath(); ctx.ellipse(cx, cy, d.w / 2 * k, d.h / 2 * k, 0, 0, math.pi * 2); ctx.fill()


# Through a door to another door in the same area: everything stays.
def throughLocalDoor(d):
    o = next((x for x in doors if x.id == d.here), None)
    if o:
        placeCharlie(o.x + o.w / 2, o.y + o.h)


def placeCharlie(cx, feet):
    P.x = cx - P.w / 2; P.y = feet - P.h; P.vx = P.vy = 0; P.ride = None
    snapCamera(O(x=cx, y=feet))


# Is world spot (x, y) hidden past an endless wall, from the side Charlie is on?
def behindEndlessWall(x, y):
    cx = P.x + P.w / 2
    for e in endlessWalls:
        if not (e.y0 * T <= y < (e.y1 + 1) * T):
            continue
        if cx < e.x0 * T and x >= e.x0 * T or cx >= (e.x1 + 1) * T and x < (e.x1 + 1) * T:
            return True
    return False


# --- endless walls (t.endlessWall): from one side, the column next to the wall is drawn again
# and again over the wall and everything past it, as if the place went on forever.
def drawEndlessWalls(sx, sy):
    if not endlessWalls:
        return
    cx = P.x + P.w / 2
    for e in endlessWalls:
        left, right = cx < e.x0 * T, cx >= (e.x1 + 1) * T
        if not left and not right:
            continue
        src = e.x0 - 1 if left else e.x1 + 1
        vx0, vx1 = math.floor(camX / T) - 1, math.ceil((camX + VIEW_W) / T) + 1
        frm, to = (max(e.x0, vx0), vx1) if left else (vx0, min(e.x1, vx1))
        ty0, ty1 = max(e.y0, math.floor(camY / T) - 1), min(e.y1, math.ceil((camY + VIEW_H) / T) + 1)
        if frm > to or ty0 > ty1:
            continue
        # the sky / backdrop first, only over the part being covered
        ctx.save()
        ctx.setTransform()
        ctx.clip_rect(frm * T - camX - sx, ty0 * T - camY - sy, (to - frm + 1) * T, (ty1 - ty0 + 1) * T)
        drawBackdrop()
        ctx.translate(-round(camX + sx), -round(camY + sy))
        for ty in range(ty0, ty1 + 1):
            c, bg = grid[ty][src], bgAt(src, ty)
            for tx in range(frm, to + 1):
                if bg:
                    ctx.fillStyle = COL.dirtBg; ctx.fillRect(tx * T, ty * T, T + 1, T + 1)
                if c != '.' and c != 'c':
                    drawTile(c, tx * T, ty * T, src, ty)
        ctx.restore()


# --- winged treats (t.wingedTreat)
def pathOf(pts, loop):
    """A path through pixel points for cloudAt: its points, whether it loops, and its length."""
    n = len(pts) if loop else len(pts) - 1
    ln = sum(math.hypot(pts[(i + 1) % len(pts)][0] - pts[i][0], pts[(i + 1) % len(pts)][1] - pts[i][1]) for i in range(n))
    return O(pts=pts, loop=loop, len=ln)


def updateWingTreats(dt):
    global stamina
    cx, cy = P.x + P.w / 2, P.y + P.h / 2
    for w in wingTreats:
        w.d += w.speed * dt
        if w.t > 0:
            w.t -= dt   # eaten: grows back
            continue
        w.x, w.y = cloudAt(w.m, w.d)
        if P.state == 'dead' or abs(w.x - cx) > P.w / 2 + 12 or abs(w.y - cy) > P.h / 2 + 12:
            continue
        w.t = 4
        eatTreat(); P.wings = True
        for i in range(12):
            spawnParticle(w.x, w.y, (random() - 0.5) * 220, (random() - 0.5) * 220, 0.5, 3, '#ffffff' if i % 2 else '#7bb661', 0)


def drawWingTreats():
    for w in wingTreats:
        if w.t > 0 or w.x is None:
            continue
        drawWings(w.x, w.y - 4, 18, 0.7)
        drawSweetPotato(w.x, w.y, math.sin(simTime * 3) * 0.2)


# A pair of white feathered wings around (x, y), flapping at `rate`; s = size.
def drawWings(x, y, rate, s):
    flap = math.sin(simTime * rate) * 0.55
    for side in (-1, 1):
        ctx.save()
        ctx.translate(x + side * 9 * s, y); ctx.rotate(side * (-0.35 + flap)); ctx.scale(side * s, s)
        ctx.fillStyle = '#ffffff'; ctx.strokeStyle = '#b9c2cf'; ctx.lineWidth = 1.5
        ctx.beginPath(); ctx.ellipse(12, -4, 15, 7, -0.35, 0, math.pi * 2); ctx.fill(); ctx.stroke()
        ctx.beginPath(); ctx.ellipse(8, 2, 10, 5, -0.1, 0, math.pi * 2); ctx.fill(); ctx.stroke()
        ctx.restore()


# --- falling ceilings (t.dropCeiling). It moves down the grid a tile at a time (so it's solid
# like any ground) and is drawn between the steps where it really is; its spikes hurt from there.
def slabAt(tx, ty):
    for sl in slabs:
        if sl.moving and sl.x0 <= tx <= sl.x1 and sl.y0 + sl.row <= ty < sl.y0 + sl.row + sl.h and \
                sl.cells[ty - sl.y0 - sl.row][tx - sl.x0] != '.':
            return True
    return False


def slabStep(sl):
    w = sl.x1 - sl.x0 + 1
    for r in range(sl.h):   # lift it out, putting back what it covered
        for i in range(w):
            if sl.cells[r][i] == '.':
                continue
            ty, tx = sl.y0 + sl.row + r, sl.x0 + i
            grid[ty][tx] = sl.under.pop(ty * LW + tx, '.')
    sl.row += 1
    for r in range(sl.h):   # and down a row
        for i in range(w):
            if sl.cells[r][i] == '.':
                continue
            ty, tx = sl.y0 + sl.row + r, sl.x0 + i
            sl.under[ty * LW + tx] = grid[ty][tx]
            grid[ty][tx] = sl.cells[r][i]
    if P.state != 'dead' and rectHitsSolid(P.x, P.y, P.w, P.h):
        die()   # squashed


def updateSlabs(dt):
    global shake
    for sl in slabs:
        if not sl.moving:
            if sl.row or sl.cells or P.state == 'dead':
                continue   # (already came down)
            if not overlap(P.x, P.y, P.w, P.h, sl.x0 * T, sl.trig * T, (sl.x1 - sl.x0 + 1) * T, T):
                continue
            sl.cells = [grid[sl.y0 + r][sl.x0:sl.x1 + 1] for r in range(sl.h)]
            # it can come down until the row under it has something solid in it
            sl.max = 0
            while sl.y0 + sl.h + sl.max < GH and not any(isSolidChar(c) for c in grid[sl.y0 + sl.h + sl.max][sl.x0:sl.x1 + 1]):
                sl.max += 1
            sl.moving = sl.max > 0
            shake = 4
            continue
        sl.p = min(sl.max, sl.p + sl.speed * dt)
        while sl.row < math.floor(sl.p):
            slabStep(sl)
        if sl.p >= sl.max:
            sl.moving = False; shake = 6
        # its spikes, where they are right now
        off = (sl.p - sl.row) * T
        hx, hy, hw, hh = P.x + 3, P.y + 3, P.w - 6, P.h - 6
        hit = False
        for r in range(sl.h):
            for i in range(sl.x1 - sl.x0 + 1):
                if sl.cells[r][i] != '^' or P.state == 'dead':
                    continue
                bx, by, bw, bh = spikeBox(sl.x0 + i, sl.y0 + sl.row + r)
                if overlap(hx, hy, hw, hh, bx, by + off, bw, bh):
                    hit = True
        if hit:
            hurt()


def drawSlabs():
    for sl in slabs:
        if not sl.moving:
            continue
        off = (sl.p - sl.row) * T
        for r in range(sl.h):
            for i in range(sl.x1 - sl.x0 + 1):
                c = sl.cells[r][i]
                if c != '.':
                    drawTile(c, (sl.x0 + i) * T, (sl.y0 + sl.row + r) * T + off, sl.x0 + i, sl.y0 + sl.row + r)
