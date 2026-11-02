# =====================================================================
#  The world layout (the Python copy of world.js).
#
#  The world is split into areas you teleport between: the Tutorial, the
#  Main game, and later places like the House. When the game starts you
#  pick Tutorial or Play on the menu (Esc brings the menu back).
#
#  area('Name') starts an area. Each addChunk line after it adds a chunk
#  made in the level editor (editor.html in the browser version) to that
#  area's right end, unless it says where:
#    addChunk('TREATS1:...', before='My Chunk')
#    addChunk('TREATS1:...', after='My Chunk')
#    addChunk('TREATS1:...', above='Starting Point', dx=20)
#    addChunk('TREATS1:...', below='Starting Point')
#  A code made next to another chunk in the editor remembers that spot, so a
#  plain addChunk puts it right there. extra=f(t) adds hand-built things to a
#  chunk (how editor notes become objects). easy='TREATS1:...' is the chunk's
#  Easy-mode version.
# =====================================================================

from game import clearWorld, area, addChunk, addSection, warpOnGreenie, addChallenge, cloudLapTime

clearWorld()

# ---------------------------------------------------------------------
#  Tutorial
# ---------------------------------------------------------------------
area('Tutorial')

# "My Chunk": the whole adventure, 300 tiles wide.
addChunk('TREATS1:eyJuIjoiTXkgQ2h1bmsiLCJ3IjozMDAsInQiOiI3MC4yNmcxMDQuNWczLjRnODgufDcwLjI2ZzEwNC42ZzMuM2c4OC58NzAuMjZnMTA2LjVnMy4yZzg4Lnw3MC4yNmcxMDcuNWczLmc4OC58NzAuMjZnMTA4LjVnOTEufDcwLjI2ZzEwOS41ZzkwLnw3MC4yNmc1Ni4xM2c0MS41Zzg5Lnw3MC4yNmc1Ni4xM2c0Mi41Zzg4Lnw3MC40ZzE4LjRnNTYuMTNnMzAuXjEyLjRnODgufDcwLjRnMTguNGc1Ni4xM2czMC5eMTMuM2c4OC58NzAuNGcxOC40ZzU2LjEzZzkuMn4zNC4yZzg4Lnw3MC40ZzE4LjRnNTUuXjEzZzE1LjJ+MjguXjg5Lnw3MC40ZzE4LjRnNTUuXjEzZzQ1Ll44OS58NzAuNGc0LjRnLjJ+Ny40ZzU1Ll4zZzE2LjJ+MzcuXjg5Lnw3MC40ZzQuNGcxMC40ZzU1Ll4zZzM0LjJ+OS4yXjguXjg5Lnw3MC40ZzQuNGc0LjJ+NjMuXjNnMjIuMn4xMTMuM2c1Lnw3MC40ZzQuNGc3MC4zZzQ4Ll44Ny41ZzQufDcwLjRnNC40ZzcuMn42MS4zZzE5LjJ+MTE1LjVnNC58NzAuNGc0LjRnNzAuM2c1MC5eNy4yVDc2LjVnNC58NzAuNGc0LjRnNjYuXjMuM2c1OC4yZzc2LjVnNC58NzAuNGc0LjRnMTAuNGc1MC4zZzY0LjJnNzUuN2czLnw3OC40ZzEwLjRnNTAuM2c2NC4yZzc1LjdnMy58NzguNGcxMC40ZzUwLjNnNjQuMmc3NC45ZzIufDM2Ll43LjNeMTAuNV4xNi40ZzEwLjRnMTE2LjRnNy42XjYwLjlnMi58ODJnMTAuMzBnMlQ0Zzg0LjRnNy4zMmdUMTBnVDEwZ1QyMmd8ODJnMTAuMzZnMjQuXjUuVDUzLjRnNy43N2d8ODJnMTAuMzZnMjQuN2c1My40ZzcuNzdnfDgyZzEwLjM2ZzI0LjdnNTMuNGc3Ljc3ZyIsInRyIjpbWzExMiwyNCwxMCwwXSxbMTI3LDI0LDEwLDBdLFsxMjcsMTQsMTAsMF0sWzEzMiwyNCw1LDBdLFsxMzMsMjQsNSwwXSxbMTM0LDI0LDUsMF0sWzEzNSwyNCw1LDBdLFsxMzYsMjQsNSwwXSxbMTM3LDI0LDUsMF0sWzE0MiwyNiw1LDBdLFsxNzEsMjgsOCwwXSxbMTk1LDI1LDgsMF0sWzE5NSwxMywxMi41LDBdLFsxOTksMjAsMTQsMF0sWzIwMiwyMiwxNCwwXSxbMjA0LDI3LDE0LDBdLFsyMDYsMjUsMTQsMF0sWzIxMSwxNSw0LDBdLFsxNzIsMjgsOCwwXSxbMTczLDI4LDksMF1dLCJ0cyI6W1syNTAsMTZdLFsyNDksMTZdLFsyNDgsMTddLFsyNDgsMThdLFsyNDgsMTldLFsyNDksMjBdLFsyNTAsMjBdLFsyNTEsMTldLFsyNTEsMThdLFsyNTEsMTddLFsyNTMsMjBdLFsyNTMsMTldLFsyNTMsMThdLFsyNTMsMTddLFsyNTMsMTZdLFsyNTQsMTddLFsyNTUsMThdLFsyNTUsMTldLFsyNTYsMTldLFsyNTYsMjBdLFsyNTYsMThdLFsyNTYsMTddLFsyNTYsMTZdLFsyNTgsMTZdLFsyNTgsMTddLFsyNTgsMThdLFsyNTgsMjBdLFsyNTgsMTldLFsyNTksMjBdLFsyNjAsMjBdLFsyNTksMThdLFsyNjAsMThdLFsyNTksMTZdLFsyNjAsMTZdLFsyNjUsMTZdLFsyNjYsMTZdLFsyNjcsMTZdLFsyNjYsMTddLFsyNjYsMThdLFsyNjYsMTldLFsyNjYsMjBdLFsyNjksMTZdLFsyNzAsMTZdLFsyNzEsMTZdLFsyNzIsMTddLFsyNzEsMThdLFsyNzAsMThdLFsyNjksMThdLFsyNjksMTddLFsyNjksMTldLFsyNjksMjBdLFsyNzEsMTldLFsyNzIsMjBdLFsyNzQsMTZdLFsyNzQsMTddLFsyNzQsMThdLFsyNzQsMTldLFsyNzQsMjBdLFsyNzUsMjBdLFsyNzYsMjBdLFsyNzUsMThdLFsyNzYsMThdLFsyNzUsMTZdLFsyNzYsMTZdLFsyNzgsMjBdLFsyNzgsMTldLFsyNzgsMThdLFsyNzgsMTddLFsyNzksMTZdLFsyODAsMTZdLFsyODEsMTddLFsyODEsMThdLFsyODEsMTldLFsyODEsMjBdLFsyNzksMThdLFsyODAsMThdLFsyODMsMTZdLFsyODQsMTZdLFsyODUsMTZdLFsyODQsMTddLFsyODQsMThdLFsyODQsMTldLFsyODQsMjBdLFszNiwyMV0sWzQ0LDIxXSxbNDUsMjFdLFs0NiwyMV0sWzU5LDIxXSxbNTgsMjFdLFs2MCwyMV0sWzc5LDExXSxbODAsMTFdLFs5MywxOF0sWzk0LDE4XSxbMTEyLDExXSxbMTIyLDE1XSxbMTIyLDE0XSxbMTIzLDE0XSxbMTIzLDE1XSxbMTUxLDE5XSxbMTUxLDE4XSxbMTUyLDIyXSxbMTcwLDI1XSxbMTcwLDI0XSxbMTcwLDIzXSxbMTcxLDEyXSxbMTcyLDEyXSxbMTc3LDE0XSxbMTc4LDE0XSxbMTc0LDldLFsxNzUsOV0sWzE1Myw0XSxbMTUzLDVdLFsxNTQsNV0sWzE1NCw0XSxbMTU1LDRdLFsxNTUsNV0sWzE5OSw0XSxbMjAyLDZdLFsyMDQsMTFdLFsyMDYsOV0sWzIwOCwzXSxbMjA5LDRdLFsyMTAsNV0sWzE5NiwxOF0sWzE5NiwxOV0sWzE5NiwyMF1dLCJnciI6W1sxNTQsMywiVXAgb24gdGhlIFJvb2YiLCJjbXZrOG9oZTFkbndwIl0sWzIwNywxLCJDYXJ2ZWQgaW4gdGhlIExlZGdlIiwiY212azh2djEyNW4yYSJdLFsyOTMsMTIsIllvdXIgQWR2ZW50dXJlIE9ubHkgQmVnaW5zLi4uIiwiY212azh6Z3o0b2xoOSJdXSwiY3AiOltbMTMzLDE5XSxbMTk1LDE3XV0sInR4IjpbWzQsMTksIldlbGNvbWUgdG8geW91clxuYWR2ZW50dXJlIENoYXJsaWUuLi4iLCIjMDAwMDAwIl0sWzE5LDE5LCJNb3ZlIHdpdGggV0FTRFxub3IgQXJyb3cgS2V5cyIsIiMwMDAwMDAiXSxbMzQsMjIsImRvbnQgdG91Y2giLCIjMDAwMDAwIl0sWzU1LDE4LCJQcmVzcyBXIG9yIFVwIFxuaW4gbWlkYWlyIHRvIGRhc2giLCIjMDAwMDAwIl0sWzk4LDE4LCJDYW4geW91IGNsaW1iIHRoaXMgdHJlZT9cblxuICAgICAgKEhpbnQ6IERhc2gpIiwiIzAwMDAwMCJdLFsxMTUsMTcsIkl0IG1pZ2h0IGJlIGEgYml0XG5lYXNpZXIgdGhpcyB0aW1lXG5cbihIaW50OiBTbWFzaCBKdW1wKSIsIiMwMDAwMDAiXSxbMTMyLDEzLCJQcm92ZSBZb3Vyc2VsZiBDaGFybGllLi4uIiwiIzAwMDAwMCJdLFsxNzcsMTksIlRoYXQgWW91IGFyZSBXb3J0aHkgb2YgdGhlLi4uIiwiIzAwMDAwMCJdLFsyNTMsMTUsIndvcnRoeSBvZiB0aGUiLCIjMDAwMDAwIl1dfQ==')

# Its last greenie, "Your Adventure Only Begins...", takes you to the main game.
warpOnGreenie('cmvk8zgz4olh9', 'Main')

# ---------------------------------------------------------------------
#  Main game
# ---------------------------------------------------------------------
area('Main')


# "Starting Point": 150 tiles wide. Its notes were built in extra():
def starting_point(t):
    # "Add a house right here, with a door in the middle": pressing W / Up at the
    # door goes inside the House
    t.house(4, 5, 24, 'House', {'id': 'front', 'arrive': 'inside'})
    # "Make this text disappear once you've stomped on all 2 chickens here"
    t.hideTextWhenChickensGone([23, 17], [[30, 23], [31, 23]])
    # "Add Bob the Square here. He doesn't do anything yet."
    t.bob(54, 24)


addChunk('TREATS1:eyJuIjoiU3RhcnRpbmcgUG9pbnQiLCJ3IjoxNTAsInQiOiIxNTAufDE1MC58MTUwLnwxNTAufDE1MC58MTUwLnwxNTAufDE1MC58MTUwLnwxNTAufDc3LjJUMTIuOGc1MS58NzcuMmczLjJnOC42ZzUyLnw4Mi4yZzkuNGc1My58MTUwLnwxNTAufDg2LjRnNjAufDg3LjNnNjAufDgwLjNnNjcufDgxLjJnMTMuMTBnMTMuN2cyNC58OTYuMTJnMTEuNmcyNS58OTYuMTRnNDAufDc2Ll4xOS4xNWczOS58NzEuXi42ZzE3LjE5ZzM1Lnw2OC4xMWcxNy4yMGczNC58ODJnMTQuNDhnMy4zZ3w4MmcxNC40OGczLjNnfDg1ZzExLjQ4ZzMuM2d8ODVnMTEuNDhnMy4zZyIsInRyIjpbWzI4LDI0LDEsMF0sWzM0LDI0LDEsMF0sWzM0LDIzLDEsMF0sWzM0LDIyLDEsMF0sWzI4LDIzLDEsMF0sWzI4LDIyLDEsMF0sWzI4LDIxLDEsMF0sWzM0LDIxLDEsMF0sWzkzLDEwLDQsMF0sWzEyMCwxOCw0LDBdLFsxMjIsMTgsNi41LDBdLFsxMjMsMTgsMywwXSxbMTI5LDI0LDMsMF0sWzEzMiwyNCw1LjUsMF0sWzEzNCwyNCwzLDBdLFsxMzUsMjQsMywwXSxbMTQzLDI0LDYsMF0sWzE0OCwyNCw2LDBdLFsxNDcsMjQsNiwwXSxbMTQyLDI0LDYsMF0sWzE0NCwyMSwzLDBdLFsxNDUsMjEsMywwXSxbMTQ2LDIxLDMsMF1dLCJ0cyI6W1szMCwyMV0sWzMyLDIxXSxbMzEsMjFdLFs3NSwxOV0sWzc2LDE5XSxbNzEsMjBdLFs3MCwyMF0sWzc3LDFdLFs3OCwxXSxbMTQ0LDE0XSxbMTQ1LDE0XSxbMTQ2LDE0XV0sImdyIjpbWzE0NSwyMiwiSGlkZGVuIEluIHRoZSBUcmVlcyIsImNtdmxtcjk3Z2Z6am4iXV0sImNwIjpbWzIsMjRdXSwidHgiOltbMTIsMTksIlByZXNzIFcgLyBVcFxudG8gb3BlbiBkb29ycyIsIiMwMDAwMDAiXSxbMjMsMTcsIlN0b21wIG9uIHRoZXNlIGFubm95aW5nIGNoaWNrZW5zIiwiIzAwMDAwMCJdLFs4MCwxNCwiU2t5IElzbGFuZHMiLCIjMDAwMDAwIl0sWzgwLDIwLCJHcmVlbmllIFRlbXBsZXMiLCIjMDAwMDAwIl1dLCJjayI6W1szMCwyM10sWzMxLDIzXV19', extra=starting_point)

# "Greenie Temples Level 1": 100 tiles wide, under Starting Point (placed in the editor:
# 85 tiles across, one chunk down), so the pit in Starting Point drops you into it.
# Easy: a few spikes fewer, and the fireballs come half as often (the right one falls faster).
addChunk('TREATS1:eyJuIjoiR3JlZW5pZSBUZW1wbGVzIExldmVsIDEiLCJ3IjoxMDAsInQiOiIzZzU5LjE2ZzIyLnwzZzU5LjE2ZzIyLnw2ZzU2LjE2ZzIyLnw2ZzUzLjdnMTJeMjIufDhnNTEuN2czNC58OGc1MS4yZy40ZzM0LnwxMGc0OS4yXi40ZzM0LnwxMGc1Mi40ZzUuXjE4ZzYuNGd8MTFnMzQuMn4xMS4zXi40ZzUuXjE4ZzYuNGd8MTFnNDYuNX40ZzUuXjE4ZzYuNGd8MTJnNTAuNGc1Ll4xOGcxMC58MTJnMjYuNGcyMC40ZzYuM140ZzguM2cxMC58MTNnNC4zfjUuM34xMC40ZzguMn4xMC40ZzkuNGc4LjNnMTAufDEzZzI1LjRnMzMuNGc4LjNnMTAufDEzZzI1LjNnMjcuXjNnMy40ZzguM2cxMC58MTNnMjUuM2cxNC5eMTIuXjNnMy40ZzguM2cxMC58MTRnMTcuM2c1LjJnMTMuMn4xMy4zZzMuNGc4LjNnMTAufDE0ZzE3LjNnNi5nMjguM2deMi4xNWcxMC58MTRnMTcuM2c2Lmc1Ll4yMi4zZ14yLjE1ZzEwLnwxNGcxOC4yZzEyLjJ+MjcuMTVnMTAufDE1ZzE3LjJnMjguNGc5LjE1ZzEwLnwxNWcxNy4yZzEwLn4xNy40ZzkuMTVnMTAufDE1ZzE3LmcyOS40ZzkuMTVnMTAufDE1ZzE3LmcyOS40ZzkuMTVnMTAufDE1ZzE3Lmc1LjR+MTEuMmc3LjRnMi41fjIuM2cxMl4xMC58MTVnMTYuMmcyMC4yZzcuNGc5LjNnMjIufDE1ZzE2LjJnMjBeMmc3XjRnNy5ULjNnMjIufDE1ZzE2LjJnMjB+Mmc3fjRnNi4zfjNnMjIuIiwidHIiOltdLCJ0cyI6W1sxOCwxMF0sWzI2LDEwXSxbMzksOV0sWzQwLDldLFs0NywxOF0sWzU0LDE1XSxbNTMsMjJdLFs1NCwyMl0sWzYyLDE4XSxbNzIsMTVdLFs3MiwxNF0sWzY2LDVdLFs2Niw2XV0sImdyIjpbWzYxLDUsIlRocm91Z2ggdGhlIFNwaWtlcyIsImNtdm13dWJxZjV1anAiXSxbODIuNSwxMywiSGlkZGVuIFRyZWFzdXJlIGluIHRoZSBHcmVlbmllIFRlbXBsZSIsImNtdm5hbTVwOXRtcGwiXV0sImNwIjpbWzMyLDE2XSxbNjQsMjBdLFs4MCw3XV0sInR4IjpbXSwiYmciOiIxMDBifDEwMGJ8MTAwYnwxMDBifDEwMGJ8MTAwYnwxMDBifDEwMGJ8MTAwYnwxMDBifDEwMGJ8MTAwYnwxMDBifDEwMGJ8MTAwYnwxMDBifDEwMGJ8MTAwYnwxMDBifDEwMGJ8MTAwYnwxMDBifDEwMGJ8MTAwYnwxMDBifDEwMGJ8MTAwYnwxMDBiIiwiZG0iOltbODYsNSwiZG12bXd0MzJ4NHBpcCJdXSwicCI6eyJhIjoiTWFpbiIsIm4iOiJTdGFydGluZyBQb2ludCIsIngiOjg1LCJ5IjoyOH0sImZiIjpbWzcwLDEseyJldmVyeSI6WzIsMl0sImRlbGF5IjowLCJtb2RlIjoic3RyYWlnaHQiLCJhbmdsZSI6WzkwLDkwXSwic3BlZWQiOls0LDRdLCJyYWRpdXMiOlszLDNdLCJzcGFjaW5nIjpbMiwyXSwic3BpbiI6WzE4MCwxODBdLCJvZmZYIjpbLTQsNF0sIm9mZlkiOlswLDBdLCJzaXplIjpbMTAsMTBdLCJsaWZlIjowLCJtYXgiOjMwLCJnaG9zdCI6dHJ1ZX1dLFs2MSwxLHsiZXZlcnkiOlsxLDFdLCJkZWxheSI6MCwibW9kZSI6InN0cmFpZ2h0IiwiYW5nbGUiOlsxMzUsMTM1XSwic3BlZWQiOls2LDZdLCJyYWRpdXMiOlszLDNdLCJzcGFjaW5nIjpbMiwyXSwic3BpbiI6WzE4MCwxODBdLCJvZmZYIjpbLTE1LDEwXSwib2ZmWSI6WzAsMF0sInNpemUiOlsxMCwxMF0sImxpZmUiOjAsIm1heCI6MzAsImdob3N0Ijp0cnVlfV1dfQ==', easy='TREATS1:eyJuIjoiR3JlZW5pZSBUZW1wbGVzIExldmVsIDEgQ29weSIsInciOjEwMCwidCI6IjNnNTkuMTZnMjIufDNnNTkuMTZnMjIufDZnNTYuMTZnMjIufDZnNTMuN2cxMl4yMi58OGc1MS43ZzM0Lnw4ZzUxLjJnLjRnMzQufDEwZzQ5LjJeLjRnMzQufDEwZzUyLjRnNS5eMThnNi40Z3wxMWczNC4yfjExLjNeLjRnNS5eMThnNi40Z3wxMWc0Ni41fjRnNS5eMThnNi40Z3wxMmc1MC40ZzUuXjE4ZzEwLnwxMmcyNi40ZzIwLjRnOS40ZzguM2cxMC58MTNnNC4zfjUuM34xMC40ZzguMn4xMC40ZzkuNGc4LjNnMTAufDEzZzI1LjRnMzMuNGc4LjNnMTAufDEzZzI1LjNnMjcuXjNnMy40ZzguM2cxMC58MTNnMjUuM2cyNy5eM2czLjRnOC4zZzEwLnwxNGcxNy4zZzUuMmcxMy4yfjEzLjNnMy40ZzguM2cxMC58MTRnMTcuM2c2LmcyOC4zZ14yLjE1ZzEwLnwxNGcxNy4zZzYuZzI4LjNnXjIuMTVnMTAufDE0ZzE4LjJnMTIuMn4yNy4xNWcxMC58MTVnMTcuMmcyOC40ZzkuMTVnMTAufDE1ZzE3LjJnMTAufjE3LjRnOS4xNWcxMC58MTVnMTcuZzI5LjRnOS4xNWcxMC58MTVnMTcuZzI5LjRnOS4xNWcxMC58MTVnMTcuZzUuNH4xMS4yZzcuNGcyLjV+Mi4zZzEyXjEwLnwxNWcxNi4yZzIwLjJnNy40ZzkuM2cyMi58MTVnMTYuMmcyMF4yZzdeNGc3LlQuM2cyMi58MTVnMTYuMmcyMH4yZzd+NGc2LjN+M2cyMi4iLCJ0ciI6W10sInRzIjpbWzE4LDEwXSxbMjYsMTBdLFszOSw5XSxbNDAsOV0sWzQ3LDE4XSxbNTQsMTVdLFs1MywyMl0sWzU0LDIyXSxbNjIsMThdLFs3MiwxNV0sWzcyLDE0XSxbNjYsNV0sWzY2LDZdXSwiZ3IiOltbNjEsNSwiVGhyb3VnaCB0aGUgU3Bpa2VzIiwiY212cHU3cmJiYWF0ZyJdLFs4Mi41LDEzLCJIaWRkZW4gVHJlYXN1cmUgaW4gdGhlIEdyZWVuaWUgVGVtcGxlIiwiY212cHU3cmJieTloMiJdXSwiY3AiOltbMzIsMTZdLFs2NCwyMF0sWzgwLDddXSwidHgiOltdLCJiZyI6IjEwMGJ8MTAwYnwxMDBifDEwMGJ8MTAwYnwxMDBifDEwMGJ8MTAwYnwxMDBifDEwMGJ8MTAwYnwxMDBifDEwMGJ8MTAwYnwxMDBifDEwMGJ8MTAwYnwxMDBifDEwMGJ8MTAwYnwxMDBifDEwMGJ8MTAwYnwxMDBifDEwMGJ8MTAwYnwxMDBifDEwMGIiLCJkbSI6W1s4Niw1LCJkbXZwdTdyYmM5ZXYzIl1dLCJmYiI6W1s2MSwxLHsiZXZlcnkiOlsyLDJdLCJkZWxheSI6MCwibW9kZSI6InN0cmFpZ2h0IiwiYW5nbGUiOlsxMzUsMTM1XSwic3BlZWQiOls2LDZdLCJyYWRpdXMiOlszLDNdLCJzcGFjaW5nIjpbMiwyXSwic3BpbiI6WzE4MCwxODBdLCJvZmZYIjpbLTE1LDEwXSwib2ZmWSI6WzAsMF0sInNpemUiOlsxMCwxMF0sImxpZmUiOjAsIm1heCI6MzAsImdob3N0Ijp0cnVlfV0sWzcwLDEseyJldmVyeSI6WzQsNF0sImRlbGF5IjowLCJtb2RlIjoic3RyYWlnaHQiLCJhbmdsZSI6WzkwLDkwXSwic3BlZWQiOls2LDZdLCJyYWRpdXMiOlszLDNdLCJzcGFjaW5nIjpbMiwyXSwic3BpbiI6WzE4MCwxODBdLCJvZmZYIjpbLTQsNF0sIm9mZlkiOlswLDBdLCJzaXplIjpbMTAsMTBdLCJsaWZlIjowLCJtYXgiOjMwLCJnaG9zdCI6dHJ1ZX1dXX0=')

# "Filler Chunk 1": 30 tiles of solid ground under Starting Point (placed in the editor:
# 55 tiles across, one chunk down), filling in next to the temple.
addChunk('TREATS1:eyJuIjoiRmlsbGVyIENodW5rIDEiLCJ3IjozMCwidCI6IjMwZ3wzMGd8MzBnfDMwZ3wzMGd8MzBnfDMwZ3wzMGd8MzBnfDMwZ3wzMGd8MzBnfDMwZ3wzMGd8MzBnfDMwZ3wzMGd8MzBnfDMwZ3wzMGd8MzBnfDMwZ3wzMGd8MzBnfDMwZ3wzMGd8MzBnfDMwZyIsInRyIjpbXSwidHMiOltdLCJnciI6W10sImNwIjpbXSwidHgiOltdLCJwIjp7ImEiOiJNYWluIiwibiI6IlN0YXJ0aW5nIFBvaW50IiwieCI6NTUsInkiOjI4fX0=')


# "Forest Level 1": 200 wide and 40 tall, right of Starting Point (placed in the editor:
# 150 across, 12 rows higher, so the ground lines up). It sits over the Greenie Temple:
# the shaft under the bridge drops into it. Its notes were built in extra():
def forest(t):
    # a plank bridge with a button underneath: hit the button from below (coming up out
    # of the Greenie Temple) and the bridge is gone for good
    t.bridge(13, 20, 36, 'forestBridge')
    # the door to Grandma's house, with smoke coming out of the chimney on the wall
    t.door(21, 27, "Grandma's House", {'id': 'grandma', 'arrive': 'front'})
    t.chimney(22.05, 21.2, 24)
    # the cave under the crumble blocks: plain ground from outside; inside, only the cave
    # shows. The trap shaft under its floor (and the crumble rooms above) are part of it.
    tunnel = [[x, y] for y in range(31, 34) for x in range(77, 81)]
    # (the crumble blocks you drop through stay visible on the surface)
    t.secret([[56, 25], [57, 25], [58, 25]], {'name': 'cave', 'flood': True, 'except': tunnel + [[56, 24], [57, 24], [58, 24]]})
    # the end of the cave is the way into the long tunnel
    t.secret(tunnel, {'name': 'cave end', 'also': ['cave']})
    # the tunnel's far end, in the tower: from inside it you can see out to the right
    end = [[x, y] for y in range(11, 14) for x in range(103, 107)]
    t.secret(end, {'name': 'tower end', 'seeX': 107})
    # walking into either end takes you into the long tunnel ("Forest Tunnel", 10x longer)
    t.portal('cave end', 77, 31); t.portal('tower end', 103, 11)
    t.link(77.6, 31, 3.4, 3, 'cave end', 'tunnel left')
    t.link(103, 11, 0.5, 3, 'tower end', 'tunnel right')
    # from the cave you can see down the long tunnel, and from the tower end back into it
    t.view({'when': ['cave', 'cave end'], 'side': 'right', 'edge': 77, 'from': 'cave end', 'to': 'tunnel left', 'show': 'tunnel'})
    t.view({'when': ['tower end'], 'side': 'left', 'edge': 103, 'from': 'tower end', 'to': 'tunnel right', 'show': 'tunnel'})
    # chickens come back 3 seconds after they're knocked out
    t.chickenSpawner(107, 29)
    t.chickenSpawner(123, 29)
    # "Underneath the Missing Spike" only shows when you're within 2 tiles of it
    t.showGreenieNear(88, 33, 2)


addChunk('TREATS1:eyJuIjoiRm9yZXN0IExldmVsIDEiLCJ3IjoyMDAsInQiOiIyMDAufDg4LjVeMTA3Lnw4Ny5eNWdeMTA2Lnw4Ny5eNWdeMTA2Lnw4Ny5eNWdeMTA2Lnw4Ny5eNWdeMTA2Lnw4Ny5eNWdeMTA2Lnw4Ny5eNWdeNi5eNmcxNy42ZzcwLnw4Ny5eNWdeNi5eNmcxNy42ZzcwLnw4Ny5eNWdeNi5eNmcxMy4zXi42ZzcwLnw4Ny5eNWdeNy42ZzN+OS41fjZnNzAufDg3Ll41Z143LjJnMjEuNmc3MC58NzIuMTJnMy5eNWdeNi4zZzIxLjdnNjkufDcyLjEyZzQuNV43LjNnMjEuN2c2OS58NzIuMTJnMTYuN2cyLjd+OC43ZzY5Lnw3MS4xM2cxNS44ZzE3LjhnNjgufDcwLjE0ZzE1LjhnMTAuMl4zLjJeOGc0NC4yMGc0Lnw3MC4xNGc4LjJeNS44ZzguNH4yLjN+OGc0NC4yMGc0Lnw3MC4yZzUuN2c3Ll4yZ140LjhnMTcuOGc0NC4yMGc0Lnw3MC4yZzUuNmc4Ll4yZ140LjhnMTcuOGc0NC4yMF40Lnw2OS4zZzJeLjJeNmc4Ll4yZ140LjhnMTcuOGc2OC58NjguNGc1fjZnOC5eMmdeNC44ZzE3fjhnNjgufDYzLjlnNS42ZzMuM2czLjJeMi5eMTBnMTcuMTBnNjYufDE5LjRnMzguMTFnNS42ZzMuM2c3Ll4xMGcxN34xMGc2Ni58NTQuMmczfjEzZzV+Nmc0LjJnOC4xMGcxNy4xMGczMC42ZzMwLnw1My4zZzMuM2cxNS42ZzEzLjExZzQuM14zLjNeNC4xMWcyOS42ZzMwLnw1MC42ZzMuM2cxNS42ZzEyLjEyZzE3fjEyZzY0LnwxNi4xMGcyMS45ZzMuM2cxNS42ZzExLjEzZzE3LjEzZzYzLnwxNi4xMGcxNy45ZzI1LjdnMTAuMTNnMTcuMTNnNjMufDE2LjEwZzE3LjlnMTguN343ZzEwLjEzZzE3LjEzZzYzLnwxNi4xMGcxNy45ZzI1LjdnMl4uN14xOWc1fjE5ZzYzLnwxNi4xMF4xNi4xMGcyOS4zZzEwfjE5ZzUuMTlnOC40MWcyVDEyZ3w0MS4xMWcyOS4zZzEwLjE5ZzUuMTlnOC41NWd8MzguMTRnMjkuM2cxMC4xOWc1LjE5ZzguNTVnfDM4LjE5ZzN+MjRnMTAuMTlnNS4xOWc4LjU1Z3wyMi4yXjcuMl40LjIwZzMuMjRnOS4yMGc1LjIwZzcuNTVnfDU3ZzMuNTNnNS4yMGc3LjU1Z3wxM2c4LjM2ZzMuNzhnNy41NWd8MTNnOC4zNmczLjc4ZzcuNTVnfDEzZzguMzZnMy43OGc3LjU1ZyIsInRyIjpbWzUsMzYsMi41LDBdLFs3LDM2LDMuNSwwXSxbOSwzNiw0LjUsMF0sWzE3LDI3LDQuNSwwXSxbMTgsMjcsNywwXSxbMjMsMjcsNywwXSxbMjQsMjcsNC41LDBdLFsxOSwyMyw0LjUsMF0sWzIxLDIzLDQuNSwwXSxbMjAsMjMsNC41LDBdLFsyMiwyMyw0LjUsMF0sWzg2LDIyLDUsMF0sWzg3LDIyLDEuNSwwXSxbODgsMjIsMywwXSxbMTU1LDMxLDYsMF0sWzE1NiwzMSw2LDBdLFsxNTcsMzEsNiwwXSxbMTQ4LDMxLDMuNSwwXSxbMTQ5LDMxLDMuNSwwXSxbMTY0LDI0LDMuNSwwXSxbMTY1LDI0LDMuNSwwXSxbMTY2LDI0LDMuNSwwXSxbMTY2LDI0LDMuNSwwXSxbMTY3LDI0LDMuNSwwXSxbMTY4LDI0LDMuNSwwXSxbMTY5LDI0LDMuNSwwXSxbMTc5LDMxLDMsMF0sWzE4MCwzMSwzLDBdLFsxODEsMzEsMywwXSxbMTg5LDMxLDgsMF0sWzE5MCwzMSw4LDBdLFsxODQsMTYsMiwwXSxbMTg1LDE2LDIsMF0sWzE4NiwxNiwyLDBdLFsxODcsMTYsMiwwXSxbMTg4LDE2LDQsMF0sWzE4OSwxNiw0LDBdLFsxOTAsMTYsNCwwXSxbMTk0LDE2LDEuNSwwXV0sInRzIjpbWzIwLDE1XSxbNSwzMF0sWzcsMjldLFs5LDI4XSxbNDQsMjZdLFs0NSwyNl0sWzU4LDM2XSxbNTgsMzddLFs1OCwzOF0sWzU3LDI2XSxbNTcsMjddLFsxMTAsMTldLFsxMTIsMTldLFsxMTEsMTldLFsxMTgsMTldLFsxMTksMTldLFs5OSwxMl0sWzk5LDEzXSxbOTksMTRdLFsxMjAsMTldLFsxMTEsMTJdLFsxMTIsMTJdLFsxMTMsMTJdLFsxNjUsMTddLFsxNjYsMTddLFsxNjcsMTddLFsxNjgsMTddLFsxODksMjBdLFsxOTAsMjBdXSwiZ3IiOltbNzQsMTksIkEgQ2hpY2tlbidzIFRyZWFzdXJlIiwiY212bzRhdW4wa3VveiJdLFsxMTUsMzMsIkZsYW1pbicgSG90IEdyZWVuaWUiLCJjbXZvNXNpM3djZWI5Il0sWzg4LDMzLCJVbmRlcm5lYXRoIHRoZSBNaXNzaW5nIFNwaWtlIiwiY212bzV5aWxtaGJmdSJdXSwiY3AiOltbMiwzNl0sWzU0LDM0XSxbMTAzLDddXSwidHgiOltdLCJoIjo0MCwiYmciOiIyMDAufDIwMC58MjAwLnwyMDAufDIwMC58MjAwLnwyMDAufDIwMC58MjAwLnwyMDAufDIwMC58MTAzLjRiOTMufDEwMy40YjkzLnwxMDMuNGI5My58MjAwLnw3MS43YjEyMi58NzEuMmIuNWIxMjEufDcwLjEwYjEyMC58NzAuMTBiMTIwLnw3MC4xMGIxMjAufDY5LmIuOWIxMjAufDY4LjEzYjExOS58NjMuMTdiMTIwLnw2MS4yMGIxMTkufDE5LjRiMzEuOGIyLjE3YjgzLjZiMzAufDE5LjRiMzAuMjhiODMuNmIzMC58MTkuNGIyNy4zMWI4My42YjMwLnw0Ny4zNGI4My42YjMwLnw0NC40Yi4zMmIyLmI4MC42YjMwLnw0NC4zOGIuYjgwLjZiMzAufDQ0LjRiLjM0YjMwLjViNDYuNmIzMC58NDQuNGIuNDliMTUuNWI0Ni42YjMwLnw0NC40Yi40N2IuYjE1LjViNDYuNmIzMC58NDQuNTJiLmIxNS41YjgyLnw0OS40OWIxNS41YjgyLnw0OS40OGIxNi41YjgyLnw1MS4yOWIyLjNiOC5iMTkuNWI4Mi58NTUuN2IyMS43Yi40YjEwNS58NTUuN2IxMzgufDU1LjdiMTM4LiIsImNrIjpbWzE5LDM1XSxbMjYsMzVdLFs0NCwyN10sWzY0LDMzXSxbNzIsMjhdLFs3NCwyM10sWzExMSwxM10sWzEwOSwyMF0sWzExOSwyMF0sWzEwOSwyNV1dLCJkbSI6W1sxMTQsMjgsImRtdm81bXpuNDU4cGgiXSxbMTE1LDI4LCJkbXZvNW4wcmEwdHFpIl0sWzExNiwyOCwiZG12bzVuMTFjeDB4cSJdXSwicCI6eyJhIjoiTWFpbiIsIm4iOiJTdGFydGluZyBQb2ludCIsIngiOjE1MCwieSI6LTEyfSwiZmIiOltbMTE1LDMzLHsiZXZlcnkiOlsyLDJdLCJkZWxheSI6MCwibW9kZSI6Im9yYml0IiwiYW5nbGUiOlswLDBdLCJzcGVlZCI6WzYsNl0sInJhZGl1cyI6WzIsMl0sInNwYWNpbmciOlsyLDJdLCJzcGluIjpbMTgwLDE4MF0sIm9mZlgiOlswLDBdLCJvZmZZIjpbMCwwXSwic2l6ZSI6WzEwLDEwXSwibGlmZSI6MCwibWF4IjozMCwiZ2hvc3QiOmZhbHNlfV1dfQ==', extra=forest)


# "Sky Islands": 100 wide and 75 tall, high above Starting Point (placed in the editor:
# 66 across, 75 rows up). Its notes were built in sky_islands():
def sky_islands(t):
    # "Tucked in the Corner of Sky Islands" only shows when you're within 2 tiles of it
    t.showGreenieNear(8, 55, 2)
    # a locked door with 3 keyholes; the 3 keys are sealed in pockets in the ground below it.
    # Each key follows Charlie once he digs to it, and goes in its hole when he's near the door.
    t.lockDoor(38, 4, 3, 4, 'skyDoor', 3)
    t.key(11, 17, 'skyDoor', 'skyKey1')
    t.key(39, 17, 'skyDoor', 'skyKey2')
    t.key(57, 17, 'skyDoor', 'skyKey3')
    # clouds that carry Charlie (jump up through them from below)
    t.cloud(73, 35, 5, {'x': [-8, 8]}, 2)    # 16 tiles side to side, 2 tiles a second
    t.cloud(81, 31, 4, {'x': [-6, 6]}, 3)    # -6 to +6 tiles, 3 tiles a second
    t.cloud(75, 28, 3, {'y': [-15, 0]}, 2)   # 15 tiles up and back down, 2 tiles a second
    # a blue and purple spiraling portal to the Cloud Challenge
    t.swirlPortal(93, 21, 2, 2, 'Cloud Challenge', {'id': 'skyPortal', 'arrive': 'back'})


addChunk('TREATS1:eyJuIjoiU2t5IElzbGFuZHMiLCJ3IjoxMDAsInQiOiIxMDAufDEwMC58MTAwLnwxMDAufDEwMC58MTAwLnwxMDAufDEwMC58MzcuNX41OC58MTAwLnwxMDAufDEwMC58MTAwLnwxMDAufDEwMC58MTAwLnw3LjU4ZzM1Lnw3LjRnLjI3Zy4xN2cuN2czNS58Ny41OGczNS58MTAwLnwxMDAufDExLn42Ln4xMC5+OS5+MTcufjMufjM4LnwxMDAufDEwMC58OC40XjguMl42LjJeNC4yXjcuXjcuXjIuXjUuM14yMy4xMWczLnw3LjZ+My44fjMuMTN+My4yfjMuOH4zLjZ+MjEuMTFnMy58ODYuMTFnMy58MTAwLnwxMDAufDE3LjNeMTEuNF4zLl43LjJeMi4yXjUuXjQyLnw3LjJ+LjJULjl+LjJULjE1fi4yVC43fi4yVC4yfi4yVC4zfjM1LnwxMDAufDEwMC58MTAwLnwxMDAufDM5LjR+NTcufDEwMC58MTAwLnwxMDAufDQ1LjV+NTAufDEwMC58NzMuMmcyLjJnMjEufDcuMlQyZ14yNy43fjMuNH44LjJ+MTAuMmcyLjJnMjEufDcuNGdeODgufDcuNGdeODgufDcuNGdeMTkuM14zLjJeNi40XjE1LjJeMzQufDcuNGdeMTguMTF+My42fjUuMTV+MzAufDcuNGdeNzEuNGcxMy58Ny40Z14xMC5nXjU5LjRnMTMufDcuNGdeMTAuZ140OS41ZzIyLnw3LjRnXjguMlRnXjQ5LjVnMjIufDcuNGdeOC4zZ143Ni58Ny40Z142Ny4zVDE4Lnw3LjRnXjg4LnwxMC5nXjQ3Ll4uXjMxLmc2LnwxMC5nXjQ3LjRnMjkuMmc2LnwxMC5nXjQ3LjRnMjguM2c2Lnw5MS4zZzYufDY2LjZnNy4yZzE5Lnw2Ni42ZzcuMmcxOS58MzIuMlQxOS5eMjUuMmcxOS58MzIuMmcxOS4zZzIzLjJnMTkufDUzLjNnNDQufDIwLjlnNTkuXjExLnwxNC4yXjQuOWcxOC4zZzEwLl4yNi4zZzEwLnwxMy40ZzQuN2cxOS4zZzkuNGcyNC4zZzEwLnwxMy40ZzQyLjRnMzcufDEzLjRnODMufDcuNGcyLjRnMzMuM1QzLjNUNC4zVDM0Lnw3LjRnMi40ZzgzLnw3LjRnMi40ZzgzLnw3LjRnMi40ZzgzLnw3LjRnMi40ZzgzLnw3LjRnMi40Zzc0LjNnMlQ0Z3w3LjRnMi40Zzc1LjhnIiwidHIiOltbODAuNSw2MC41LDUsOTBdLFs4MC41LDU5LjUsNSw5MF0sWzkxLDU2LDgsMF0sWzkyLDU1LDgsMF0sWzkzLDU0LDgsMF0sWzcsMTYsMywwXSxbMjMsMTYsMywwXSxbMzksMTYsMywwXSxbNTQsMTYsMywwXSxbOCwxNiwzLjUsMF0sWzI0LDE2LDMuNSwwXSxbNDAsMTYsMy41LDBdLFs1NSwxNiwzLjUsMF0sWzU2LDE2LDQsMF0sWzI1LDE2LDQsMF0sWzksMTYsNCwwXSxbMTAsMTYsNC41LDBdLFsyNiwxNiw0LjUsMF0sWzU3LDE2LDQuNSwwXSxbMTEsMTYsNSwwXSxbMjcsMTYsNSwwXSxbNDMsMTYsNSwwXSxbNTgsMTYsNSwwXSxbMTIsMTYsNS41LDBdLFsyOCwxNiw1LjUsMF0sWzQ0LDE2LDUuNSwwXSxbNTksMTYsNS41LDBdLFsxOCwxNiw1LjUsMF0sWzM0LDE2LDUuNSwwXSxbNDksMTYsNS41LDBdLFsxMywxNiw2LDBdLFsxNywxNiw2LDBdLFsyOSwxNiw2LDBdLFszMywxNiw2LDBdLFs0NSwxNiw2LDBdLFs0OCwxNiw2LDBdLFsxNCwxNiw2LjUsMF0sWzE2LDE2LDYuNSwwXSxbMzAsMTYsNi41LDBdLFszMiwxNiw2LjUsMF0sWzQ2LDE2LDYuNSwwXSxbNDcsMTYsNi41LDBdLFsxNSwxNiw3LDBdLFszMSwxNiw3LDBdLFs2MCwxNiw2LDBdLFs2MSwxNiw2LjUsMF0sWzYzLDE2LDYuNSwwXSxbNjIsMTYsNywwXSxbNjQsMTYsNiwwXSxbMTksMTYsNSwwXSxbMzUsMTYsNSwwXSxbNTAsMTYsNSwwXSxbMjAsMTYsNC41LDBdLFszNiwxNiw0LjUsMF0sWzUxLDE2LDQuNSwwXSxbMjEsMTYsNCwwXSxbMzcsMTYsNCwwXSxbNTIsMTYsNCwwXSxbMjIsMTYsMy41LDBdLFszOCwxNiwzLjUsMF0sWzUzLDE2LDMuNSwwXSxbNDEsMTYsNCwwXSxbNDIsMTYsNC41LDBdXSwidHMiOltbNDcsNjJdLFs0OSw2Ml0sWzQ4LDYyXSxbNTEsNTZdLFs1Nyw1Nl0sWzY0LDU2XSxbODIsNTddLFs4Myw1N10sWzkwLDUwXSxbOTAsNTFdLFs3NywzOV0sWzczLDM5XSxbNzQsMzldLFs3OCwzOV0sWzUwLDQwXSxbNTEsNDBdLFs0MSw0MF0sWzQyLDQwXSxbMTQsMjddLFsxNSwyN10sWzI4LDI3XSxbMTYsMjddLFsyMCwyN10sWzI5LDI3XSxbMjcsMjddLFszNiwyN10sWzQ4LDI3XSxbNDksMjddLFs2MiwyN10sWzY0LDI3XSxbNjMsMjddLFs3LDI3XSxbOCwyN10sWzE3LDIyXSxbMTgsMjJdLFsyMiwyMl0sWzIzLDIyXSxbMzEsMjJdLFszMiwyMl0sWzQ0LDIyXSxbNDksMjJdLFs1MiwyMl0sWzUzLDIyXSxbNTAsMjJdLFs0OCwyMl0sWzExLDE5XSxbMTgsMTldLFsyOSwxOV0sWzM5LDE5XSxbNTcsMTldLFs2MSwxOV0sWzIyLDldLFsyMyw5XSxbMjQsOV0sWzUzLDldLFs1NCw5XSxbNTUsOV0sWzg4LDIyXSxbODksMjJdLFs5MCwyMl0sWzIxLDM1XSxbMjEsMzZdLFsyMSwzN10sWzIxLDM4XSxbMjEsMzldLFsyMSw0MF0sWzIxLDQxXSxbMjEsNDJdXSwiZ3IiOltbOCw1NSwiVHVja2VkIGluIHRoZSBDb3JuZXIgb2YgU2t5IElzbGFuZHMiLCJjbXZyZzl4ZjJ3d3AzIl1dLCJjcCI6W1syNCw2M10sWzg0LDQ3XSxbOSw0Ml0sWzM3LDhdXSwidHgiOltdLCJoIjo3NSwiYmciOiIxMDAufDEwMC58MTAwLnwxMDAufDEwMC58MTAwLnwxMDAufDEwMC58MTAwLnwxMDAufDEwMC58MTAwLnwxMDAufDEwMC58MTAwLnwxMDAufDguOGIxOS45YjEwLjdiMzkufDguOGIxOS4xMGIyLmIuMmIuYi43YjM5Lnw4LjEyYi5iLmIuYi5iLmIuMTJiMTEuN2IzOS58MTAwLnwxMDAufDEwMC58MTAwLnwxMDAufDEwMC58MTAwLnwxMDAufDEwMC58MTAwLnwxMDAufDEwMC58MTAwLnwxMDAufDEwMC58MTAwLnwxMDAufDEwMC58MTAwLnwxMDAufDEwMC58MTAwLnwxMDAufDcuNGI4OS58Ny40Yjg5Lnw3LjRiODkufDcuNGI4OS58Ny40Yjg5Lnw3LjRiODkufDcuNGI4OS58Ny40Yjg5Lnw3LjRiODkufDcuNGI4OS58Ny40Yjg5Lnw3LjRiODkufDcuNGI4OS58Ny40Yjg5Lnw3LjRiODkufDEwMC58MTAwLnwxMDAufDEwMC58MTAwLnwxMDAufDEwMC58MTAwLnwxMDAufDEwMC58MTAwLnwxMDAufDEwMC58MTAwLnwxMDAufDEwMC58MTAwLnwxMDAuIiwiY2siOltbNzAsNTddLFs2MSw0MV0sWzU3LDQ1XSxbNzQsNDhdLFs0Miw0MV0sWzQ3LDM4XSxbNTEsNDFdXSwiZG0iOltbMzgsOSwiZG12czcxbnN4aGRjciJdLFszOSw5LCJkbXZzNzFvMTdqcXdyIl0sWzQwLDksImRtdnM3MW9iN3FhdmwiXV0sInAiOnsiYSI6Ik1haW4iLCJuIjoiU3RhcnRpbmcgUG9pbnQiLCJ4Ijo2NiwieSI6LTc1fSwiZmIiOltbMzUsMTgseyJldmVyeSI6WzAuNSwwLjVdLCJkZWxheSI6MCwibW9kZSI6InN0cmFpZ2h0IiwiYW5nbGUiOls5MCw5MF0sInNwZWVkIjpbNiw2XSwicmFkaXVzIjpbMywzXSwic3BhY2luZyI6WzIsMl0sInNwaW4iOlsxODAsMTgwXSwib2ZmWCI6Wy0yNywyOV0sIm9mZlkiOlswLDBdLCJzaXplIjpbMTAsMTBdLCJsaWZlIjo4LCJtYXgiOjEwMCwiZ2hvc3QiOnRydWV9XSxbNiwyMix7ImV2ZXJ5IjpbNCw0XSwiZGVsYXkiOjAsIm1vZGUiOiJzdHJhaWdodCIsImFuZ2xlIjpbMCwwXSwic3BlZWQiOlsxMiwxMl0sInJhZGl1cyI6WzMsM10sInNwYWNpbmciOlsyLDJdLCJzcGluIjpbMTgwLDE4MF0sIm9mZlgiOlswLDBdLCJvZmZZIjpbMCwwXSwic2l6ZSI6WzEwLDEwXSwibGlmZSI6MCwibWF4IjozMCwiZ2hvc3QiOmZhbHNlfV0sWzYsMjcseyJldmVyeSI6WzQsNF0sImRlbGF5IjoxLCJtb2RlIjoic3RyYWlnaHQiLCJhbmdsZSI6WzAsMF0sInNwZWVkIjpbMTIsMTJdLCJyYWRpdXMiOlszLDNdLCJzcGFjaW5nIjpbMiwyXSwic3BpbiI6WzE4MCwxODBdLCJvZmZYIjpbMCwwXSwib2ZmWSI6WzAsMF0sInNpemUiOlsxMCwxMF0sImxpZmUiOjAsIm1heCI6MzAsImdob3N0IjpmYWxzZX1dXX0=', extra=sky_islands)

# "Greenie Temples Level 1 Part 2": 200 wide and 45 tall, right under Forest Level 1 (placed in the editor: 35
# across, one chunk down), next to the Greenie Temple. Its notes were built in temple_part2():
def temple_part2(t):
    # the passage up from Bob's room looks like plain ground until you're in the room, and the
    # pocket round "Bob's Greenie" until you're in the pocket. Inside they show as dirt
    # background, and the greenie only shows within 2 tiles.
    pocket = [[x, y] for y in range(13, 18) for x in range(3, 8)]
    passage = [[x, y] for y in range(18, 25) for x in range(8, 12)]
    t.secret(passage, {'name': 'bobPassage', 'keepOutside': True, 'showFrom': [0, 25, 15, 37]})
    t.secret(pocket, {'name': 'bobPocket', 'keepOutside': True, 'also': ['bobPassage']})
    t.showGreenieNear(5, 15, 2)
    # Bob the Square, by the reward treats. His words change when these happen (each once):
    t.talkingBob(10, 28, [
        {'near': 7, 'line': 'Wow! Nice job finding me {name}! You can get these treats as a reward, cause there is nothing else to see here!'},
        {'secret': ['bobPassage', 'bobPocket'], 'line': "Hey! Get back down here, there's Greenies to see outside of this area!"},
        {'at': [5, 15, 5], 'line': "You know what's up, huh?"},
        {'at': [5, 15, 3], 'line': 'If you take my special Greenie, you will D I E.'},
        {'got': 'cmvy6swexv5g0', 'near': 5, 'line': 'I told you so.', 'start': 'bobRoom', 'delay': 2},
    ])
    # ...2 seconds after "I told you so", his room shuts, top opening too, and fills with spikes
    # that fly at you. Bob and his platform sink 5 tiles, then a second platform appears 5 left and 1 up.
    # (They stand free, so they stay clear of the spikes.)
    t.spikeRoom('bobRoom', {
        'start': [0, 25], 'box': [0, 13, 21, 38], 'bounds': [0, 0, 199, 44],
        'seal': [[-1, 25], [-1, 26], [-1, 27], [20, 36], [21, 36], [20, 37], [21, 37], [8, 24], [9, 24], [10, 24], [11, 24]],
        'lower': {'x0': 8, 'x1': 11, 'row': 28, 'by': 5, 'speed': 3, 'twin': [-5, -1]},
    })
    # two black holes: Up in one and you come out of the other
    t.holeDoor(78, 21, 'depthsHoleA', 'depthsHoleB')
    t.holeDoor(114, 15, 'depthsHoleB', 'depthsHoleA')
    # the wall between the two halves: from either side the place seems to go on forever
    t.endlessWall(110, 112, 0, 44)
    # a treat with wings flying round its track: eat it to fly (W / S), plus one extra hit
    t.wingedTreat([[121, 9], [126, 9], [126, 13], [121, 13]], 3)
    # the spiked ceiling over the corridor comes down, 3 tiles a second and through anything,
    # once you reach its bottom row, and carries on out of the bottom of the chunk
    t.dropCeiling(113, 147, 17, 18, 23, 3, 45)


addChunk('TREATS1:eyJuIjoiR3JlZW5pZSBUZW1wbGVzIExldmVsIDEgUGFydCAyIiwidyI6MjAwLCJ0IjoiMjJnMy41ZzQuNGc0LjRnMTcuMmcxNC4yZzI5LjkwZ3wyMmczLjVnNC40ZzQuNGcxNy4yZzE0LjJnMjkuOTBnfDYuNV4xNC41ZzQuNGc0LjRnMTcuMmcxNC4yZzI5LjkwZ3wyNS41ZzQuNGc0LjRnMTcuMl4xNC4yZzI5LjkwZ3wyNS41ZzQuNGc0LjRnMjcuNH4yLjJeMjkuOTBnfDI1LjVnNC40ZzQuNGc2NC45MGd8My4zXjUuN143LjVnNC40ZzQuNGc2NC45MGd8MjJnMy41ZzQuNGc0LjRnMTcuMl40NS4zZzE3LjVnMl42M2d8MjJnMy41ZzQuNGc0LjRnMTEuM34yLl4yZ34xMy4yXjkuM34xNy4zZzE3LjNnMl4yLl42Mmd8MjJnMy41ZzQuNGc0LjRnMTYuXjJnMTQuMmd+MjguM2cxNy4zXjUuXjYxZ3wyMmczLjVnNC40ZzQuNGcxNi5eMmcxNC4yZzI5LjNnMjYuOV41Mmd8MjJnMy41ZzQuNGc0LjRnMTYuXjJnMTQuMmcyOS4zZzIyLjJeMjAuNDNnfDIyZzMuNV40LjRnNC40ZzE3LjJnMTQuMmcyOS4zZzIwLjJeMmdeMTkuNDNnfDNnNS4xNGcxMi40ZzQuNGcxNC41ZzUuOV4yZzI5LjNnMTcuM141Z14xOC40M2d8M2c1LjE0ZzEyLjRnNC40ZzE0LjVnNS4xMWcyOS4zZzE3LjlnOV42ZzMuNDNnfDNnNS4xNGcxMi40ZzQuNF4xNC41ZzUuMTFnMjkuNDRnMy40M2d8M2c1LjE0ZzMuNV40LjRnMjIuNWc0NS40NGczLjQzZ3wzZzUuMTRnMy41ZzQuNGcyMi41ZzQ1LjQ0ZzMuNDNnfDhnNC4xMGczLjVnNC40ZzIyLjVnNDUuM2czNV42ZzMuNDNnfDhnNC4xMGczLjVnNC40ZzQuNF4xNC41ZzE5LjJeMi4yXjIwLjNnNDQuNDNnfDhnNC4xMGczLjVnNC40ZzQuNGcxNC41ZzE5LjlnMTcuM2c0NC40M2d8OGc0LjEwZzMuNWc0LjRnNC40ZzQuNH42LjVnNy43fjUuOWczLjR+MTAuM2c0NC40M2d8OGc0LjEwZzMuNWc0LjRnNC40ZzE0LjVnMTkuOWcxNy4zZzM1LjUyZ3w4ZzQuMTBnMy41ZzQuNGc0LjRnMjQuMl4zOC4zZzQuMTFeNy4xMF4zLjUyZ3w4ZzQuMTBnMy41ZzQuNF40LjRnMjQuM2czNy4zZzMuXjExZ141Ll4xMGdeMi41Mmd8MTYuNmczLjVnMTIuNGcyNC4zZzE3LjNeMTcuM2czLl4xMWdeNS5eMTBnXjIuNTJnfDE2LjZnMy41ZzEyLjRnMjQuM2cxNi5eM2deMTYuM2czLl4xMWdeNS5eMTBnXjIuNTJnfDE2LjZnMy41ZzEyLjRnMjQuM2cxNi5eM2deMTYuM2czLl4xMWdeNS5eMTBnXjIuNTJnfDguNGc0LjZnMy41ZzQuNF40LjRnMjQuM2c0LjNeOS5eM2deMTYuM2czLl4xMWdeNS5eMTBnXjIuNTJnfDE2LjZnMy41ZzQuNGc0LjRnMzEuM2d+OC5eM2deMTYuM2czLl4xMWdeNi4xMF4zLjUyZ3wxNi42ZzMuNWc0LjRnNC40ZzMxLjNnMTAuM14xNy4zZzMuXjExZ14xOS41Mmd8MTYuNmczLjVnNC40ZzQuNGczMS4zZzMwLjNnMy5eMTFnXjE5LjUyZ3wxNi42ZzMuNWc0LjRnNC40ZzMxLjNnMzAuM2c0LjExXjE2LjReNTJnfDE2LjZnMy41ZzQuNGc0LjRnMTEuM34xNy4zZzEwLjN+MTcuM2czMC5eNTZnfDE2LjZnMy41ZzQuNGc0LjRnNjQuM2czMC5eNTZnfDE2LjZnMy41ZzQuNGc0LjRnNjQuM2czMC5eNTZnfDIwLjJeMy41ZzQuNGc0LjRnNjQuM2czMS40XjUyZ3wyMC4yXjMuNWc0LjRnNC40ZzI3LjR+MzMuM2czNS41Mmd8MjJnMy41ZzQuNGc0LjRnNjQuM2czNS41Mmd8MjJnMy41ZzQuNGc0LjRnNjQuM2czNS41Mmd8MjJnMy41ZzQuNGc0LjRnNjQuM2czNS41Mmd8MjJnMy41ZzQuNGc0LjRnNjQuM2czNS41Mmd8MjJnMy41ZzQuNGc0LjRnNjQuM2czNS41Mmd8MjJnM141ZzReNGc0XjRnNjReM2czNS41Mmd8MTExbzJnMzUuNTJnIiwidHIiOltdLCJ0cyI6W1syLDI5XSxbMywyOV0sWzQsMjldLFs0LDMwXSxbMywzMF0sWzIsMzBdLFsyLDMxXSxbMywzMV0sWzQsMzFdLFs0LDMzXSxbMywzNF0sWzQsMzRdLFs0LDM1XSxbMywzNV0sWzIsMzVdLFsyLDM0XSxbMiwzM10sWzMsMzNdLFsyLDMyXSxbMywzMl0sWzQsMzJdLFsyLDI4XSxbMywyOF0sWzQsMjhdLFs0LDI3XSxbMiwyN10sWzMsMjddLFsxMjMsMTFdLFsxMjQsMTFdLFsxMjQsMzddLFsxMzcsMzddLFsxMzcsNDFdLFsxMjQsNDFdLFsxMjMsMzddLFsxMjMsNDFdLFsxMzYsNDFdLFsxMzYsMzddLFs1MSwxOV0sWzUyLDE5XSxbNTgsMzFdLFs1OCw2XSxbNzQsMl0sWzc1LDJdLFs5MSw2XSxbOTcsMTldLFs5OCwxOV0sWzc0LDM1XSxbNzUsMzVdLFsyNiwxNF0sWzI3LDE0XSxbMjgsMTRdLFszNSwyNl0sWzM2LDI2XSxbNDMsMTddLFs0NCwxN11dLCJnciI6W1s1LDE1LCJCb2IncyBHcmVlbmllIiwiY212eTZzd2V4djVnMCJdLFs5MSwzMSwiNDozMCIsImNtdnlheDRxYmZjanQiXV0sImNwIjpbWzczLDIxXSxbNTAsMjFdLFsxMTYsMTVdXSwidHgiOltdLCJoIjo0NSwiYmciOiIxNTBiNTAufDE1MGI1MC58MTUwYjUwLnwxNTBiNTAufDE1MGI1MC58MTUwYjUwLnwxNTBiNTAufDE1MGI1MC58MTUwYjUwLnwxNTBiNTAufDE1MGI1MC58MTU3YjQzLnwxNTdiNDMufDE1N2I0My58MTUwYjQuM2I0My58MTUwYjQuM2I0My58MTUwYjQuM2I0My58MTUwYjQuM2I0My58MTUwYjQuM2I0My58MTU3YjQzLnwxNTdiNDMufDE1N2I0My58MTUwYjUwLnwxNTBiNTAufDE1MGI1MC58MTUwYjUwLnwxNTBiNTAufDE1MGI1MC58MTUwYjUwLnwxNTBiNTAufDE1MGI1MC58MTUwYjUwLnwxNTBiNTAufDE1MGI1MC58MTUwYjUwLnwxNTBiNTAufDE1MGI1MC58MTUwYjUwLnwxNTBiNTAufDE1MGI1MC58MTUwYjUwLnwxNTBiNTAufDE1MGI1MC58MTUwYjUwLnwxNTBiNTAuIiwiZG0iOltbNzUsMjAsImRtdnk4YjBpM3o0bW4iXSxbNzYsMjAsImRtdnk4YjFzeTNkb3UiXV0sInAiOnsiYSI6Ik1haW4iLCJuIjoiRm9yZXN0IExldmVsIDEiLCJ4IjozNSwieSI6NDB9LCJmYiI6W1s3NSwyMCx7ImV2ZXJ5IjpbMiwyXSwiZGVsYXkiOjAsIm1vZGUiOiJzcGlyYWwiLCJhbmdsZSI6WzAsMF0sInNwZWVkIjpbNiw2XSwicmFkaXVzIjpbMywzXSwic3BhY2luZyI6WzQsNF0sInNwaW4iOlsxODAsMTgwXSwib2ZmWCI6WzAsMF0sIm9mZlkiOlswLDBdLCJzaXplIjpbMTAsMTBdLCJsaWZlIjoxNCwibWF4IjozMCwiZ2hvc3QiOnRydWV9XSxbMTEzLDM0LHsiZXZlcnkiOlsxLDFdLCJkZWxheSI6MCwibW9kZSI6InN0cmFpZ2h0IiwiYW5nbGUiOlswLDBdLCJzcGVlZCI6WzEyLDEyXSwicmFkaXVzIjpbMywzXSwic3BhY2luZyI6WzIsMl0sInNwaW4iOlsxODAsMTgwXSwib2ZmWCI6WzAsMF0sIm9mZlkiOlswLDBdLCJzaXplIjpbMTAsMTBdLCJsaWZlIjowLCJtYXgiOjMwLCJnaG9zdCI6ZmFsc2V9XSxbMTQ3LDM5LHsiZXZlcnkiOlsxLDFdLCJkZWxheSI6MCwibW9kZSI6InN0cmFpZ2h0IiwiYW5nbGUiOlsxODAsMTgwXSwic3BlZWQiOlsxMiwxMl0sInJhZGl1cyI6WzMsM10sInNwYWNpbmciOlsyLDJdLCJzcGluIjpbMTgwLDE4MF0sIm9mZlgiOlswLDBdLCJvZmZZIjpbMCwwXSwic2l6ZSI6WzEwLDEwXSwibGlmZSI6MCwibWF4IjozMCwiZ2hvc3QiOmZhbHNlfV0sWzExMyw0Myx7ImV2ZXJ5IjpbMSwxXSwiZGVsYXkiOjAuMzcsIm1vZGUiOiJzdHJhaWdodCIsImFuZ2xlIjpbMCwwXSwic3BlZWQiOlsxMiwxMl0sInJhZGl1cyI6WzMsM10sInNwYWNpbmciOlsyLDJdLCJzcGluIjpbMTgwLDE4MF0sIm9mZlgiOlswLDBdLCJvZmZZIjpbMCwwXSwic2l6ZSI6WzEwLDEwXSwibGlmZSI6MCwibWF4IjozMCwiZ2hvc3QiOmZhbHNlfV1dfQ==', extra=temple_part2)

# "Filler Chunk 2": solid ground under the Greenie Temple and left of its Part 2.
addChunk('TREATS1:eyJuIjoiRmlsbGVyIENodW5rIDIiLCJ3IjoxMDAsInQiOiIxMDBnfDEwMGd8MTAwZ3wxMDBnfDEwMGd8MTAwZ3wxMDBnfDEwMGd8MTAwZ3wxMDBnfDEwMGd8MTAwZ3wxMDBnfDEwMGd8MTAwZ3wxMDBnfDEwMGciLCJ0ciI6W10sInRzIjpbXSwiZ3IiOltdLCJjcCI6W10sInR4IjpbXSwiaCI6MTd9', below='Greenie Temples Level 1')

# The long tunnel between the cave and the tower (10x the 4 tiles it looks like):
# 40 tiles of corridor, tucked far above the forest where nobody can see it. Its ends are
# copies of the cave end and the tower end, and you're moved between them as you walk.
def forest_tunnel(t):
    t.fill(0, 0, 42, 20, 'g')
    cells = []
    for y in range(11, 14):
        for x in range(1, 41):
            t.set(x, y, '.'); t.setBg(x, y); cells.append([x, y])
    t.secret(cells, {'name': 'tunnel'})
    t.portal('tunnel left', 1, 11); t.portal('tunnel right', 37, 11)
    t.link(0, 11, 1.5, 3, 'tunnel left', 'cave end')
    t.link(37.6, 11, 3.4, 3, 'tunnel right', 'tower end')
    t.view({'when': ['tunnel'], 'side': 'left', 'edge': 1, 'from': 'tunnel left', 'to': 'cave end', 'show': 'cave'})
    t.view({'when': ['tunnel'], 'side': 'right', 'edge': 41, 'from': 'tunnel right', 'to': 'tower end', 'show': 'tower end'})
    t.cameraLike(0, 0, 42, 20, [['tunnel left', 'cave end'], ['tunnel right', 'tower end']])


addSection('Forest Tunnel', 42, forest_tunnel, h=20, place={'frm': 'Forest Level 1', 'dx': 80, 'dy': -50})

# ---------------------------------------------------------------------
#  House: inside the house at the Starting Point (built by hand, one screen wide)
# ---------------------------------------------------------------------
area('House')


def house(t):
    t.backdrop('house')            # light beige wallpaper instead of sky
    t.fill(0, 0, 30, 12, 'p')      # ceiling
    t.fill(0, 12, 1, 12, 'p')      # left wall
    t.fill(29, 12, 1, 12, 'p')     # right wall
    t.fill(0, 24, 30, 4, 'w')      # wooden floor
    t.setSpawn(15)
    t.light(14.5, 12)              # ceiling light, hanging from the middle
    t.closet(3, 24)                # left: the closet (newspaper hat)
    t.door(14.5, 24, 'Main', {'id': 'inside', 'arrive': 'front'})   # back outside
    t.chest(24, 24)                # right: the ancient chest (genie map, 3 diamonds)


addSection('House', 30, house)

# ---------------------------------------------------------------------
#  Grandma's House: through the door in the forest. An old hut with log walls, lit only by
#  the fireplace. Grandma Charlie sits on her antique couch and talks to you.
# ---------------------------------------------------------------------
area("Grandma's House")


def grandmas_house(t):
    t.backdrop('hut')              # rough log walls instead of sky
    t.dim(0.82)                    # dark, except near the fire
    t.fill(0, 0, 30, 12, 'l')      # log ceiling
    t.fill(0, 12, 1, 12, 'l')      # left wall
    t.fill(29, 12, 1, 12, 'l')     # right wall
    t.fill(0, 24, 30, 4, 'f')      # worn plank floor
    t.setSpawn(4)
    t.door(3, 24, 'Main', {'id': 'front', 'arrive': 'grandma'})   # back out to the forest
    t.fireplace(11, 24, 4, 12)     # stone fireplace, its stack going up to the ceiling
    t.couch(17, 24, 4)             # the antique couch...
    t.grandma(19, 23.2)            # ...with Grandma Charlie on it
    t.turkeyTable(23, 24)          # help yourself to the turkey legs


addSection("Grandma's House", 30, grandmas_house)


# ---------------------------------------------------------------------
#  Cloud Challenge: through the swirl portal in Sky Islands. 250 x 50, built from the
#  "Cloud Challenge Level" code; its notes were built in cloud_challenge(). The greenie at
#  the end is a challenge greenie (it shows on the Achievements screen).
# ---------------------------------------------------------------------
area('Cloud Challenge')

addChallenge('cmvt47zkwr9p1', "The Chicken's Test", 'cloudGreenie')


def cloud_challenge(t):
    # the swirl portal back to Sky Islands
    t.swirlPortal(1, 34, 2, 2, 'Main', {'id': 'back', 'arrive': 'skyPortal'})
    # this cloud waits until Charlie is standing on it
    t.tuneCloud(68, 29, {'waitRide': True})
    # the big looping cloud: its track is drawn, and it goes half speed through the dip
    # (and half speed again in the box at columns 153-157, rows 28-30, which it passes
    # through on its way up from the bottom right)
    loop = t.tuneCloud(142, 38, {'track': True, 'zones': [
        {'x0': 175, 'y0': 36, 'x1': 181, 'y1': 42, 'pace': 0.5},
        {'x0': 153, 'y0': 28, 'x1': 157, 'y1': 30, 'pace': 0.5},
    ]})
    # two doors: through one to the other, only the clouds start over
    t.localDoor(126, 14, 'cloudDoor1', 'cloudDoor2')
    t.localDoor(143, 38, 'cloudDoor2', 'cloudDoor1')
    # teleporters: the one in the pocket under the ground and the one past the barrier
    t.teleporter(157, 48, 'cloudTpLow', 'cloudTpHigh')
    t.teleporter(203, 23, 'cloudTpHigh', 'cloudTpLow')
    # an invisible wall all the way up
    t.barrier(196, 0, 2, 50)
    # passing column 58-59 lets out the giant chicken 10 tiles behind. Between the doors it
    # slows so that, starting 1 tile behind the first door, its front reaches the second
    # door just as the looping cloud finishes one lap. It bursts at the barrier.
    t.giantChicken({'trigger': [58, 2, 59, 32], 'front': 48, 'floor': 50, 'top': 0, 'stop': 196,
                    'slow': {'x0': 125, 'x1': 143, 'time': cloudLapTime(loop)}})
    # a checkpoint on the pillar where it's let out: respawning there lets it out again
    t.cp(58, 33)


addChunk('TREATS1:eyJuIjoiQ2xvdWQgQ2hhbGxlbmdlIExldmVsIiwidyI6MjUwLCJ0IjoiMTA5Ll45Z14xNS5eOWdeMTA0LnwxMDkuXjlnXjE1Ll45Z14xMDQufDEwOS5eOWdeMTUuXjlnXjEwNC58MTA5Ll45Z14xNS5eOWdeMTA0LnwxMDkuXjlnXjE1Ll45Z14xMDQufDEwOS5eOWdeMTUuXjlnXjEwNC58MTA5Ll45Z141LjJeOC5eOWdeMTA0LnwxMDkuXjlnXjQuXjJnXjcuXjlnXjEwNC58MTEwLjleNS5eMmdeNy5eOWdeMTA0LnwxMjMuXmcyLmdeNi5eOWdeMTA0LnwxMjMuXmcyLmdeNi5eOWdeMTA0LnwxMTAuMl42Ll40Ll5nMi5nXjYuXjlnXjEwNC58MTA5Ll45Z14yLl5nNC5nXjUuXjlnXjEwNC58MTA5Ll45Z14yLl5nNC5nXjUuXjlnXjEwNC58MTA5Ll45Z14yLl5nLjJ+LmdeNS5eOWdeMTA0LnwxMDkuXjlnXjIuXmc0LmdeNS5eOWdeMTA0LnwxMDkuXjlnXjIuXmc0LmdeNS5eOWdeMTA0LnwxMDkuXjlnXjIuXmdeMy5nXjUuXjlnXjEwNC58MTA5Ll45Z14yLl5nXjMuZ141Ll45Z14xMDQufDEwOS5eOWdeMi5eZzQuZ141Ll45Z14xMDQufDEwNi4yVC5eOWdeMi5eZzExLl45Z14zNi4zXjY1LnwxMDkuXjlnXjIuXmcxMS5eOWdeMzUuXjNnXjY0Lnw4NS4yXjIyLl45Z14yLl5nLjJeOC5eOWdeMzUuXjNnXjY0Lnw4NC5eMmdeMjEuXjlnXjIuXjZnXjUuXjlnXjM1Ll4zZ142NC58ODQuXjJnXjIxLl45Z14zLl40Z142Ll45Z14zNS5eM2deNjQufDg0Ll4yZ14yMS5eOWdeMy5eNGdeNi5eOWdeNC4yXjI5Ll4zZ142NC58ODQuXjJnXjIyLjleNC5eNGdeNi5eOWdeMy5eMmdeMjguXjNnXjY0Lnw4NS4yXjM3Ll4yZ143Ll45Z14zLl4yZ14yOC5eM2deNjQufDExMC4yXjEyLl4yZ143Ll45Z140LjJeMjkuXjNnXjY0LnwxMDkuXjJnMTMuMl44Ll45Z14xNC40XjE3Ll4zZ142NC58MTA5Ll4yZzJeMjEuXjlnXjEzLl40Z14xNi5eM2deNjQufDEwOS5eNGcyMS5eOWdeMTMuXjRnXjE2Ll4zZ142NC58MTA5Ll40ZzJeMTkuXjlnXjEzLl40Z14xNi5eM2deNjQufDU3LjRnNDguXjZnMTkuXjlnXjEzLl40Z14xNy4zXjY1Lnw1Ny40ZzQ4Ll42ZzIwLjleMTUuNF44Ni58NTcuNGc0OC5eMTFnMlRnXjEyNS58NTcuNGc0OC5eMTRnXjEyNS58NWc1Mi41ZzJUZzQ0Ll4xNGdeOTAuMzVnfDVnNTIuOGc0NC5eMTRnXjkwLjM1Z3w1ZzUyLjhnNDQuXjE0Z145MC4zNWd8MTA5Ll4xNGdeNTcuM34zMC4zNWd8MTA5Ll4xNGdeOTAuMzVnfDEwOS5eMTRnXjExLjleNi4xN2c0Ny4zNWd8MTA5Ll4xNGdeMTAuXjlnXjUuMTdnNDcuMzVnfDEwOS5eMTRnXjEwLl45Z141LjE3ZzQ3LjM1Z3wxMDkuXjE0Z14xMC5eOWdeNS4xN2c0Ny4zNWd8MTA5Ll4xNGdeMTAuXjlnXjUuMTdnNDcuMzVnfDEwOS5eMTRnXjEwLl45Z141LjE3ZzQ3LjM1Z3wxMDkuXjE0Z14xMC5eOWdeNS42ZzUuNmc0Ny4zNWd8MTA5Ll4xNGdeMTAuXjlnXjUuMTdnNDcuMzVnIiwidHIiOltdLCJ0cyI6W1sxNTgsMjhdLFsxNTgsMjldLFsxNTgsMzBdLFsxODMsMzhdLFsxODIsMzhdLFsxODQsMzhdLFsxNTgsMjddLFsxNDgsMjVdXSwiZ3IiOltbMTE3LDMyLCJDaGlja2VuJ3MgQnVycm93IiwiY212dDI5MDdtM3FwayJdLFsyNDQsMTcsIlRoZSBDaGlja2VuJ3MgVGVzdCIsImNtdnQ0N3prd3I5cDEiXV0sImNwIjpbWzQsMzddXSwidHgiOltdLCJoIjo1MCwiYmciOiIxMTkuMTdiMTE0LnwxMTkuMTdiMTE0LnwxMTkuMTdiMTE0LnwxMTkuMTdiMTE0LnwxMTkuMTdiMTE0LnwxMTkuMTdiMTE0LnwxMTAuMjZiMTE0LnwxMTAuMTZiLjliMTE0LnwxMTAuMTViLjEwYjExNC58MTEwLjI2YjExNC58MTEwLjI2YjExNC58MTEwLjI2YjExNC58MTEwLjI2YjExNC58MTEwLjRiLjIxYjExNC58MTEwLjdiMi4xN2IxMTQufDExMS40YjQuMTdiMTE0LnwxMTEuNGI0LjliLjdiMTE0LnwxMTMuYjUuMTdiMTE0LnwxMTMuYjUuNGIuMTJiMTE0LnwxMTIuYjYuNGIuMTJiMTE0LnwxMTIuYjYuMTdiMTE0LnwxMTEuYjcuMTdiMTE0LnwxMTEuYjcuMTdiMTE0LnwxMTEuYjcuMTdiMTE0LnwxMTAuYjguMTdiMTE0LnwxMTAuYjguMTdiMTE0LnwxMTAuMTViLjEwYjExNC58MTEwLjI2YjExNC58MTEwLjE1Yi4xMGIxMTQufDExMi4yNGIxMTQufDExMi4yNGIxMTQufDExNC4yMmIxMTQufDExNC4yMmIxMTQufDExNi4yMGIxMTQufDExNi4yOWIxMDUufDEyMC4zYi4yMWIxMDUufDEyNC4yMWIxMDUufDEyNC4yMWIxMDUufDEyNC4yMWIxMDUufDEyNC4yMWIxMDUufDEyNC4yMWIxMDUufDEyNC4yMWIxMDUufDEyNC4yMWIxMDUufDEyNC4xMmIxMTQufDEyNC4xMmIxMTQufDEyNC4xMmIxMTQufDEyNC4xMmIxMTQufDEyNC4xMmIxMTQufDEyNC4xMmIxMTQufDEyNC4xMmIxMTQuIiwiZG0iOltbMTYwLDQ4LCJkbXZ0M3NqYzhuaHZ1Il0sWzE2MSw0OCwiZG12dDNzamt1ejAxdiJdLFsxNTksNDgsImRtdnQ2dGdlbHUycjkiXSxbMTU4LDQ4LCJkbXZ0NnRndTB1MWl3Il1dLCJjbCI6W1s3LDMyLHsidyI6NCwic2NhbGUiOjEsIm1vZGUiOiJ1ZCIsImRpc3QiOjEwLCJyeCI6NCwicnkiOjIsImNjdyI6ZmFsc2UsInB0cyI6W10sImxvb3AiOmZhbHNlLCJzcGVlZCI6NCwic3RhcnQiOjUwfV0sWzE0LDMyLHsidyI6NCwic2NhbGUiOjEsIm1vZGUiOiJ1ZCIsImRpc3QiOjEwLCJyeCI6NCwicnkiOjIsImNjdyI6ZmFsc2UsInB0cyI6W10sImxvb3AiOmZhbHNlLCJzcGVlZCI6Niwic3RhcnQiOjgwfV0sWzIxLDMyLHsidyI6NCwic2NhbGUiOjEsIm1vZGUiOiJ1ZCIsImRpc3QiOjEwLCJyeCI6NCwicnkiOjIsImNjdyI6ZmFsc2UsInB0cyI6W10sImxvb3AiOmZhbHNlLCJzcGVlZCI6OCwic3RhcnQiOjB9XSxbMzIsMzYseyJ3Ijo0LCJzY2FsZSI6MSwibW9kZSI6ImVsbGlwc2UiLCJkaXN0Ijo2LCJyeCI6NSwicnkiOjUsImNjdyI6ZmFsc2UsInB0cyI6W10sImxvb3AiOmZhbHNlLCJzcGVlZCI6MTIsInN0YXJ0IjowfV0sWzQzLDMwLHsidyI6NCwic2NhbGUiOjEsIm1vZGUiOiJlbGxpcHNlIiwiZGlzdCI6NiwicngiOjEwLCJyeSI6MTAsImNjdyI6dHJ1ZSwicHRzIjpbXSwibG9vcCI6ZmFsc2UsInNwZWVkIjoxNSwic3RhcnQiOjB9XSxbNDIsMzAseyJ3Ijo1LCJzY2FsZSI6MSwibW9kZSI6ImVsbGlwc2UiLCJkaXN0Ijo2LCJyeCI6MTAsInJ5IjoxMCwiY2N3Ijp0cnVlLCJwdHMiOltdLCJsb29wIjpmYWxzZSwic3BlZWQiOjE1LCJzdGFydCI6NTB9XSxbNjgsMjkseyJ3Ijo0LCJzY2FsZSI6MSwibW9kZSI6InBhdGgiLCJkaXN0Ijo2LCJyeCI6NCwicnkiOjIsImNjdyI6ZmFsc2UsInB0cyI6W1sxMy41LDBdLFsxOC41LC05XSxbMjguNSwtOV1dLCJsb29wIjpmYWxzZSwic3BlZWQiOjEyLCJzdGFydCI6MH1dLFsxMjQsMTcseyJ3Ijo0LCJzY2FsZSI6MSwibW9kZSI6ImVsbGlwc2UiLCJkaXN0Ijo2LCJyeCI6NCwicnkiOjEyLCJjY3ciOmZhbHNlLCJwdHMiOltdLCJsb29wIjpmYWxzZSwic3BlZWQiOjE1LCJzdGFydCI6MH1dLFsxNDIsMzgseyJ3Ijo4LCJzY2FsZSI6MSwibW9kZSI6InBhdGgiLCJkaXN0Ijo2LCJyeCI6NCwicnkiOjIsImNjdyI6ZmFsc2UsInB0cyI6W1sxNi41LC03XSxbNy41LC0xNl0sWzQwLjUsLTE2XSxbMzMuNSwzXSxbMi41LC0xMl0sWzI2LjUsLTEwXV0sImxvb3AiOnRydWUsInNwZWVkIjoxNCwic3RhcnQiOjB9XSxbMjAyLDI1LHsidyI6Mywic2NhbGUiOjEsIm1vZGUiOiJ1ZCIsImRpc3QiOjE1LCJyeCI6NCwicnkiOjIsImNjdyI6ZmFsc2UsInB0cyI6W10sImxvb3AiOmZhbHNlLCJzcGVlZCI6NSwic3RhcnQiOjB9XSxbMjQyLDIxLHsidyI6NSwic2NhbGUiOjEsIm1vZGUiOiJ1ZCIsImRpc3QiOjEyLCJyeCI6NCwicnkiOjIsImNjdyI6ZmFsc2UsInB0cyI6W10sImxvb3AiOmZhbHNlLCJzcGVlZCI6Mywic3RhcnQiOjB9XV19', extra=cloud_challenge)
