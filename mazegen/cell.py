import sys
import curses
import random
from typing import List, Tuple, Optional, Set
from .maze import Maze


class Cell:
    """Represents a single cell in the maze grid.

    Each cell tracks which walls are still standing (via a 4-bit grid
    bitmask using :class:~mazegen.visualization.Bearings flags), whether
    the DFS/Wilson algorithm has visited it, and whether it belongs to the
    hidden '42' easter-egg pattern.

    The grid bitmask starts at 15 (all four walls present) and is
    progressively cleared as the generation algorithm removes walls.

    Class Attributes:
        __PATTERN_42: Relative (col, row) offsets that form the '42'
            pixel-art pattern within a 7×5 bounding box.
        __PATTERN_SET: Set version of __PATTERN_42 for O(1) membership
            tests.
        __PATTERN_WIDTH: Bounding-box width of the '42' pattern in cells.
        __PATTERN_HEIGHT: Bounding-box height of the '42' pattern in cells.
    """

    __slots__ = ('grid', 'visited', 'ft_pattern')

    __PATTERN_42: Tuple[Tuple[int, int], ...] = (
        (0, 0), (0, 1), (0, 2), (1, 2), (2, 2), (2, 3), (2, 4),
        (4, 0), (5, 0), (6, 0), (6, 1), (6, 2), (5, 2), (4, 2),
        (4, 3), (4, 4), (5, 4), (6, 4)
    )
    __PATTERN_SET: Set[Tuple[int, int]] = set(__PATTERN_42)
    __PATTERN_WIDTH: int = 7
    __PATTERN_HEIGHT: int = 5

    def __init__(self) -> None:
        """Initialise a cell with all walls intact and unvisited."""
        self.grid: int = 15
        self.visited: bool = False
        self.ft_pattern: bool = False

    @staticmethod
    def __draw_box(
        stdscr: curses.window, y: int, x: int, w: int,
        lines: List[str], attr: int
    ) -> None:
        """Draw a Unicode box with the given lines of text inside it.

        Lines equal to "-" are rendered as horizontal dividers (╠═╣).
        All drawing is clipped to the current terminal dimensions.

        Args:
            stdscr: The curses window to draw on.
            y: Top row of the box (0-indexed).
            x: Left column of the box (0-indexed).
            w: Total width of the box including borders.
            lines: Text lines to place inside the box.
            attr: Curses attribute (colour pair + modifiers).
        """
        max_y, max_x = stdscr.getmaxyx()
        if y >= max_y or x >= max_x:
            return

        def safe_addstr(row: int, col: int, text: str) -> None:
            if row < max_y and col < max_x:
                try:
                    stdscr.addstr(row, col, text[:max_x - col - 1], attr)
                except curses.error:
                    pass

        safe_addstr(y, x, f"╔{'═' * (w - 2)}╗")
        for i, line in enumerate(lines, 1):
            if line == "-":
                safe_addstr(y + i, x, f"╠{'═' * (w - 2)}╣")
            else:
                safe_addstr(y + i, x, f"║{line[:w - 2].center(w - 2)}║")
        safe_addstr(y + len(lines) + 1, x, f"╚{'═' * (w - 2)}╝")

    @classmethod
    def __prompt_warning(cls, message: str, stdscr: curses.window) -> None:
        """Display a modal warning box and let the user continue or exit.

        Pressing 'c' dismisses the warning; pressing 'e' calls
        :func:sys.exit.

        Args:
            message: Warning text to display inside the box.
            stdscr: The curses window to draw on.
        """
        curses.start_color()
        curses.use_default_colors()
        style: int = curses.color_pair(0) | curses.A_BOLD
        curses.curs_set(0)

        msg_len: int = len(message)
        width: int = max(msg_len + 4, 30)
        lines: List[str] = [
            "WARNING",
            "-",
            message,
            "-",
            "C. Continue │ E. Exit"
        ]

        while True:
            stdscr.erase()
            max_y, max_x = stdscr.getmaxyx()
            cls.__draw_box(
                stdscr, max(0, (max_y - len(lines) - 2) // 2),
                max(0, (max_x - width) // 2), width, lines, style
            )
            stdscr.refresh()

            ch: int = stdscr.getch()
            if 0 <= ch <= 255:
                key: str = chr(ch).lower()
                if key == 'e':
                    sys.exit(0)
                if key == 'c':
                    break

    @classmethod
    def __get_valid_start(cls, maze: Maze) -> Optional[Tuple[int, int]]:
        """Find a random top-left anchor for the '42' pattern.

        The chosen position must not overlap the maze entry or exit cells.

        Args:
            maze: The :class:~mazegen.maze.Maze whose dimensions and entry/exit
                coordinates determine valid placements.

        Returns:
            A (col, row) tuple for the top-left corner of the pattern, or
            None if no valid position exists.
        """
        ex, ey = maze.entry
        xx, xy = maze.exit
        cands: List[Tuple[int, int]] = [
            (x, y)
            for x in range(1, maze.width - cls.__PATTERN_WIDTH)
            for y in range(1, maze.height - cls.__PATTERN_HEIGHT)
            if (ex - x, ey - y) not in cls.__PATTERN_SET
            and (xx - x, xy - y) not in cls.__PATTERN_SET
        ]
        return random.choice(cands) if cands else None

    @classmethod
    def get_cells(
        cls, maze: Maze, stdscr: curses.window
    ) -> List[List['Cell']]:
        """Create the full 2-D grid of :class:Cell objects for a maze.

        Attempts to embed the '42' easter-egg pattern into the grid by
        marking the corresponding cells as pre-visited (so the generation
        algorithm treats them as already carved).  Displays a warning and
        returns an undecorated grid if the maze is too small or no valid
        position exists.

        Args:
            maze: The :class:~mazegen.maze.Maze that defines the grid
                dimensions, entry, and exit.
            stdscr: The curses window used to display warnings if needed.

        Returns:
            A 2-D list cells[row][col] of :class:Cell instances with
            the '42' pattern pre-marked when possible.
        """
        cells: List[List['Cell']] = [
            [cls() for _ in range(maze.width)] for _ in range(maze.height)
        ]

        if (
            maze.width < cls.__PATTERN_WIDTH
            or maze.height < cls.__PATTERN_HEIGHT
        ):
            cls.__prompt_warning(
                "Maze size too small for '42' pattern.", stdscr
            )
            return cells

        start: Optional[Tuple[int, int]] = cls.__get_valid_start(maze)
        if not start:
            cls.__prompt_warning(
                "No valid positions for '42' pattern.", stdscr
            )
            return cells

        sx, sy = start
        for px, py in cls.__PATTERN_42:
            cell: 'Cell' = cells[sy + py][sx + px]
            cell.visited = True
            cell.ft_pattern = True

        return cells
