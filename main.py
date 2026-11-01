# Treats (Python / pygame version). Run:  py main.py
# Play-test one chunk code:                py main.py --test TREATS1:...

import game
import world  # noqa: F401  (builds the areas)

if __name__ == '__main__':
    game.boot()
