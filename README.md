# Treats (Python / pygame version)

A copy of Treats (the browser game in `..\treatsthegame`) written in Python with pygame.
Everything plays the same: the same moves and physics numbers, the same areas and chunks,
chickens, inhaling, fireballs, secrets, doors, the closet, chest and backpack, Bob, Grandma,
the Easy / Hard choice and the save codes.

## Run it

```
py main.py
```

Needs Python 3 with pygame (`py -m pip install pygame` if it's missing). The window can be resized.

To play-test one chunk code from the level editor on its own:

```
py main.py --test TREATS1:...
```

## Level editor

```
py editor.py
```

The same editor as the browser one (`editor.html`), in its own window, and its codes work in both
versions. Left drag paints, right drag erases. The mouse wheel scrolls (Shift+wheel sideways),
Ctrl+wheel zooms, and middle drag or the arrow keys move around. All the tools are there:
Select (blocks and objects), Move chunks (other chunks and your own), Rectangle, Ground,
Cobblestone, Dirt BG, Spikes, Trampoline, Crumble, Treat, Greenie, Diamond, Tree, Checkpoint,
Text, Chicken, Fireball, Cloud, Note and Eraser. Other chunks, **Generate world** (every chunk of
the main world around yours, where it is in the game) and Copy level are in there too.
**Play** (P) opens the chunk in the game in a new window. **Get code** copies the chunk code
and **Load code** reads one from the clipboard. Your chunk is kept in `save_data.json` between runs.

Clouds can be placed and edited, but the Python game doesn't build them yet, so they don't show up in Play.

## Files

| File | What's in it |
| --- | --- |
| `main.py` | Starts the game |
| `game.py` | The game itself (a line-by-line port of `game.js`) |
| `world.py` | The world layout (the port of `world.js`, with the same chunk codes) |
| `editor.py` | The level editor (a port of `editor.js`) |
| `engine.py` | A small canvas-like drawing layer over pygame, plus saving and the clipboard |
| `images/` | The same pictures as the browser version |

## Saving

Collected greenies and the things you keep are saved in `save_data.json` next to the game
(the browser version keeps them in localStorage instead). Save codes (the SAVE button) are
the same format in both versions, so a code from one works in the other.

## Adding chunks

Make chunks in either editor (`editor.py` or `..\treatsthegame\editor.html`). Paste their codes
into `world.py` the same way as in `world.js`, with keyword arguments for where they go:

```python
addChunk('TREATS1:...', after='Starting Point')
addChunk('TREATS1:...', below='Starting Point', dx=55)
addChunk('TREATS1:...', extra=my_extra_function, easy='TREATS1:...')
```
