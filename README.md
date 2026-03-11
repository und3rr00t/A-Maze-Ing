_This project has been created as part of the 42 curriculum by oused-da, adraji._

# A-Maze-Ing

## Description

**A-Maze-Ing** is an interactive terminal-based maze generator and solver built in Python. The goal of the project is to procedurally generate mazes of configurable size, solve them automatically, and let players navigate them manually — all rendered directly in the terminal using the `curses` library.

The project is structured around a reusable `mazegen` package that encapsulates:

- **Maze generation** using two distinct algorithms: _Depth-First Search (DFS)_ and _Wilson's algorithm (loop-erased random walk)_
- **Maze solving** using _Breadth-First Search (BFS)_, which guarantees the shortest path
- **Real-time visualization** of both generation and solving steps, rendered cell-by-cell in the terminal
- **Interactive player mode**, where the user can navigate the maze using arrow keys
- **Theming system** with multiple visual styles switchable at runtime
- **Audio support** via `pygame` for sound effects during the intro
- **Configuration-driven** setup: maze dimensions, entry/exit points, algorithm, seed, and output file are all defined in a plain-text config file

Mazes can be saved to a text file in a compact hexadecimal grid format, along with the seed, entry/exit coordinates, and solution string.

---

## Instructions

### Requirements

- Python ≥ 3.12
- [Poetry](https://python-poetry.org/) (dependency manager)
- A terminal with `curses` support (Linux/macOS natively; Windows via WSL or ConEmu)

### Installation

```bash
# Clone the repository
git clone https://github.com/SEGV-Survivors/A-Maze-Ing.git
cd A-Maze-Ing

# Install project dependencies
make install
```

### Running

```bash
# Run with the default config file
make run

# Or run directly
poetry run python3 a_maze_ing.py config.txt

# Run with a custom config file
poetry run python3 a_maze_ing.py my_config.txt
```

### Configuration

Edit `config.txt` to customize the maze before launching:

```ini
WIDTH=20          # Maze width (number of columns)
HEIGHT=20         # Maze height (number of rows)
ENTRY=0,0         # Entry point (x,y)
EXIT=19,19        # Exit point (x,y)
OUTPUT_FILE=maze_output.txt

PERFECT=True      # True = perfect maze (no loops), False = imperfect

# Optional: fix the random seed for reproducibility
# SEED=1769678149

# Algorithm: DFS or WILSON
ALGORITHM=DFS
```

### Linting

```bash
# Run mandatory lint (flake8 + mypy)
make lint

# Run strict mypy lint
make lint-strict
```

### Cleaning

```bash
make clean
```

---

## Usage Examples

### Main Menu Controls

| Key | Action                                     |
| --- | ------------------------------------------ |
| `S` | Show / regenerate solution                 |
| `R` | Generate a new maze                        |
| `P` | Enter player mode                          |
| `A` | Switch generation algorithm (DFS ↔ Wilson) |
| `T` | Cycle through visual themes                |
| `E` | Exit                                       |

### Player Mode Controls

| Key | Action            |
| --- | ----------------- |
| `W` | Move up           |
| `A` | Move left         |
| `S` | Move down         |
| `D` | Move right        |
| `E` | Exit to main menu |

### Output File

After generation, the maze is saved to `OUTPUT_FILE` (as set in config):

```
B953955553
AAFAC3FFFA
AAFC5057FA
AEFFFAFFFA
C53BFAFD52
97AAFEFFFA
856853953A
C556BA83AA
97916AEAAA
C56C5456C6

SEED: 1773046184
ENTRY: 0,0
EXIT: 9,9
SOLUTION: SSSSEESSWWSEEENEESSSEENNWNEESSSEq
```

Each row is a hexadecimal encoding of cell wall bits. The `SOLUTION` field is a string of cardinal directions (`N`, `S`, `E`, `W`).

---

## Features

- Two maze generation algorithms: **DFS** (fast, river-like) and **Wilson's** (uniform spanning tree)
- **BFS solver** with animated step-by-step visualization
- Multiple **terminal themes** switchable at runtime with `T`
- **Player mode** with collision detection and move tracking
- Maze **export** to a structured text file with seed and solution
- **Audio intro** using pygame
- **Seed support** for fully reproducible mazes
- **Imperfect maze** mode (adds extra passages for multiple paths)
- Press **Enter** during generation/solving to skip the animation

---

## Contributions

| Author       | Work                                                                                             |
| ------------ | ------------------------------------------------------------------------------------------------ |
| **oused-da** | Maze generation algorithms (DFS, Wilson's), BFS solving algorithm, solution path computation     |
| **adraji**   | Config parsing, curses rendering & visualization, player mode, theming system, audio integration |

---

## Resources

### Documentation & References

- [Maze generation algorithms — Wikipedia](https://en.wikipedia.org/wiki/Maze_generation_algorithm)
- [Depth-First Search — Wikipedia](https://en.wikipedia.org/wiki/Depth-first_search)
- [Wilson's Algorithm — Wikipedia](https://en.wikipedia.org/wiki/Loop-erased_random_walk)
- [Breadth-First Search — Wikipedia](https://en.wikipedia.org/wiki/Breadth-first_search)
- [Python `curses` documentation](https://docs.python.org/3/library/curses.html)
- [Python `curses` HOWTO](https://docs.python.org/3/howto/curses.html)
- [Pygame documentation](https://www.pygame.org/docs/)
- [Poetry documentation](https://python-poetry.org/docs/)
- [Jamis Buck — Maze Algorithms Blog](https://weblog.jamisbuck.org/2011/2/7/maze-generation-algorithm-recap)
- [Mypy documentation](https://mypy.readthedocs.io/en/stable/)

### AI Usage

AI was used in a limited capacity as a small assistant for two specific tasks:

- **Debugging**: Occasionally consulted to help understand error messages (e.g., mypy type errors, curses color pair issues). All fixes were implemented and validated by the authors themselves.
- **README**: Used to help draft and structure this README file.

All design decisions, algorithms, architecture, and code were written entirely by oused-da and adraji.
