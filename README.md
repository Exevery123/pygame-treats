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

## Files

| File | What's in it |
| --- | --- |
| `main.py` | Starts the game |
| `game.py` | The game itself (a line-by-line port of `game.js`) |
| `world.py` | The world layout (the port of `world.js`, with the same chunk codes) |
| `engine.py` | A small canvas-like drawing layer over pygame, plus saving and the clipboard |
| `images/` | The same pictures as the browser version |

## Saving

Collected greenies and the things you keep are saved in `save_data.json` next to the game
(the browser version keeps them in localStorage instead). Save codes (the SAVE button) are
the same format in both versions, so a code from one works in the other.

## Adding chunks

The level editor is still the browser one (`..\treatsthegame\editor.html`). Paste its codes
into `world.py` the same way as in `world.js`, with keyword arguments for where they go:

```python
addChunk('TREATS1:...', after='Starting Point')
addChunk('TREATS1:...', below='Starting Point', dx=55)
addChunk('TREATS1:...', extra=my_extra_function, easy='TREATS1:...')
```
