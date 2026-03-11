import sys
import curses
from ..cell import Cell
from ..maze import Maze
from enum import IntFlag
from typing import List, Tuple, Optional, Set


class Bearings(IntFlag):
    """Bitmask flags representing the four cardinal walls of a maze cell.

    Each flag corresponds to one wall direction.  A cell's grid attribute
    is a bitwise OR of whichever walls are still intact (all four = 15).

    Attributes:
        NORTH: The wall on the top edge of a cell (bit 0, value 1).
        EAST:  The wall on the right edge of a cell (bit 1, value 2).
        SOUTH: The wall on the bottom edge of a cell (bit 2, value 4).
        WEST:  The wall on the left edge of a cell (bit 3, value 8).
    """

    NORTH = 1
    EAST = 2
    SOUTH = 4
    WEST = 8


class MazeRenderer:
    """Renders a maze and player state onto a curses window.

    Handles full redraws via :meth:display_maze as well as lightweight
    incremental updates (wall removal, BFS exploration step, player move)
    to keep the animation smooth without clearing the whole screen each frame.
    """

    def __init__(
        self, maze: Maze, cells: List[List[Cell]], stdscr: curses.window
    ) -> None:
        """Initialise the renderer and hide the cursor.

        Args:
            maze: The :class:~mazegen.maze.Maze whose configuration drives
                layout calculations.
            cells: 2-D grid cells[row][col] of :class:~mazegen.cell.Cell
                objects representing the maze structure.
            stdscr: The curses window to draw on.
        """
        self.__maze: Maze = maze
        self.__cells: List[List[Cell]] = cells
        self.__stdscr: curses.window = stdscr
        curses.curs_set(0)

    def get_maze_end_y(self) -> int:
        """Return the terminal row immediately below the rendered maze.

        Used by the UI layer to position the HUD menu without overlapping
        the maze.

        Returns:
            The first terminal row below the bottom border of the maze.
        """
        max_y, _ = self.__stdscr.getmaxyx()
        maze_h = self.__maze.height * 2 + 1
        start_y = max(0, (max_y - maze_h - 2) // 2)
        return start_y + maze_h

    def __check_terminal_size(self) -> bool:
        """Return whether the terminal is large enough to display the maze.

        Returns:
            True if both the width and height of the terminal meet the
            minimum requirements for the current maze dimensions.
        """
        max_y, max_x = self.__stdscr.getmaxyx()
        return bool(
            max_x >= self.__maze.width * 4 + 4
            and max_y >= self.__maze.height * 2 + 4
        )

    def update_wall_removal(self, cx: int, cy: int, nx: int, ny: int) -> None:
        """
        Incrementally render the removal of the wall between two cells.

        Paints the passage body and both cell bodies with the passage colour
        without redrawing the full maze.  Entry and exit cells are left as-is.

        Args:
            cx: Column of the source cell.
            cy: Row of the source cell.
            nx: Column of the destination cell.
            ny: Row of the destination cell.
        """
        max_y, max_x = self.__stdscr.getmaxyx()
        maze_w = self.__maze.width * 4 + 2
        maze_h = self.__maze.height * 2 + 1
        start_y = max(0, (max_y - maze_h - 2) // 2)
        start_x = max(0, (max_x - maze_w) // 2)

        BODY = "  "
        color = self.__maze.themes.themes['P_C']

        c_y = start_y + cy * 2 + 1
        c_x = start_x + cx * 4 + 2
        n_y = start_y + ny * 2 + 1
        n_x = start_x + nx * 4 + 2

        if cx == nx:
            b_y = min(c_y, n_y) + 1
            b_x = c_x
            self.__stdscr.addstr(b_y, b_x, BODY, color)
        else:
            b_y = c_y
            b_x = min(c_x, n_x) + 2
            self.__stdscr.addstr(b_y, b_x, BODY, color)

        if (cx, cy) != self.__maze.entry and (cx, cy) != self.__maze.exit:
            self.__stdscr.addstr(c_y, c_x, BODY, color)
        if (nx, ny) != self.__maze.entry and (nx, ny) != self.__maze.exit:
            self.__stdscr.addstr(n_y, n_x, BODY, color)

    def update_bfs_step(
        self,
        new_pos: Tuple[int, int],
        visited_coords: Set[Tuple[int, int]],
        is_retracting: bool = False
    ) -> None:
        """Incrementally update a single BFS exploration or retraction step.

        When advancing (is_retracting=False) the new cell and any open
        passages to already-visited neighbours are painted with the exploration
        colour.  When retracting (is_retracting=True) the cell and its open
        passages are cleared back to the passage colour.

        Args:
            new_pos: The (col, row) of the cell being updated.
            visited_coords: Set of all cells visited so far by the BFS.
            is_retracting: True when erasing the exploration overlay
                on the backward pass, False when painting it.
        """
        max_y, max_x = self.__stdscr.getmaxyx()
        maze_w = self.__maze.width * 4 + 2
        maze_h = self.__maze.height * 2 + 1
        start_y = max(0, (max_y - maze_h - 2) // 2)
        start_x = max(0, (max_x - maze_w) // 2)

        theme = self.__maze.themes.themes
        BLOCK = "██"
        BODY = "  "

        nx, ny = new_pos
        n_y = start_y + ny * 2 + 1
        n_x = start_x + nx * 4 + 2

        if not is_retracting:
            color = theme['EXP_C']
            if new_pos == self.__maze.exit:
                color = theme['E_C']
            elif new_pos == self.__maze.entry:
                color = theme['S_C']

            self.__stdscr.addstr(n_y, n_x, BLOCK, color)

            cell = self.__cells[ny][nx]
            if not (
                cell.grid & Bearings.NORTH
            ) and (nx, ny - 1) in visited_coords:
                self.__stdscr.addstr(n_y - 1, n_x, BLOCK, theme['EXP_C'])
            if not (
                cell.grid & Bearings.SOUTH
            ) and (nx, ny + 1) in visited_coords:
                self.__stdscr.addstr(n_y + 1, n_x, BLOCK, theme['EXP_C'])
            if not (
                cell.grid & Bearings.WEST
            ) and (nx - 1, ny) in visited_coords:
                self.__stdscr.addstr(n_y, n_x - 2, BLOCK, theme['EXP_C'])
            if not (
                cell.grid & Bearings.EAST
            ) and (nx + 1, ny) in visited_coords:
                self.__stdscr.addstr(n_y, n_x + 2, BLOCK, theme['EXP_C'])

        else:
            cell = self.__cells[ny][nx]
            bg_color = theme['P_C']

            if (
                new_pos != self.__maze.entry
                and new_pos != self.__maze.exit
            ):
                self.__stdscr.addstr(n_y, n_x, BODY, bg_color)

            if not (cell.grid & Bearings.NORTH):
                self.__stdscr.addstr(n_y - 1, n_x, BODY, bg_color)
            if not (cell.grid & Bearings.SOUTH):
                self.__stdscr.addstr(n_y + 1, n_x, BODY, bg_color)
            if not (cell.grid & Bearings.WEST):
                self.__stdscr.addstr(n_y, n_x - 2, BODY, bg_color)
            if not (cell.grid & Bearings.EAST):
                self.__stdscr.addstr(n_y, n_x + 2, BODY, bg_color)

    def update_player_move(
        self,
        old_pos: Tuple[int, int],
        new_pos: Tuple[int, int]
    ) -> None:
        """Render a single player move from old_pos to new_pos.

        Recolours the old cell with the solution-path colour (or the entry
        colour if the old position was the entry), paints the passage bridge
        between the two cells, then draws the new cell in the player colour.
        Finishes with a :meth:curses.window.refresh.

        Args:
            old_pos: (col, row) the player is moving from.
            new_pos: (col, row) the player is moving to.
        """
        max_y, max_x = self.__stdscr.getmaxyx()
        maze_w = self.__maze.width * 4 + 2
        maze_h = self.__maze.height * 2 + 1
        start_y = max(0, (max_y - maze_h - 2) // 2)
        start_x = max(0, (max_x - maze_w) // 2)

        theme = self.__maze.themes.themes
        BLOCK = "██"

        old_color = theme['SOL_C']
        bridge_color = theme['SOL_C']
        new_color = theme['PL_C']

        if old_pos == self.__maze.entry:
            old_color = theme['S_C']

        ox, oy = old_pos
        nx, ny = new_pos

        o_y = start_y + oy * 2 + 1
        o_x = start_x + ox * 4 + 2
        n_y = start_y + ny * 2 + 1
        n_x = start_x + nx * 4 + 2

        self.__stdscr.addstr(o_y, o_x, BLOCK, old_color)

        if old_pos != new_pos:
            if ox == nx:
                b_y = min(o_y, n_y) + 1
                b_x = o_x
                self.__stdscr.addstr(b_y, b_x, BLOCK, bridge_color)
            else:
                b_y = o_y
                b_x = min(o_x, n_x) + 2
                self.__stdscr.addstr(b_y, b_x, BLOCK, bridge_color)

        self.__stdscr.addstr(n_y, n_x, BLOCK, new_color)

        self.__stdscr.refresh()

    def display_maze(
        self,
        visualizing: bool = False,
        path_coords: Optional[List[Tuple[int, int]]] = None,
        visited_coords: Optional[Set[Tuple[int, int]]] = None
    ) -> None:
        """Perform a full redraw of the maze with optional overlays.

        Blocks in a resize-handling loop until the terminal is large enough,
        then clears the screen and redraws every cell row by row.  Path edges
        are highlighted in the solution colour, explored cells in the
        exploration colour, and special cells (entry, exit, player head) each
        use their own dedicated colour.

        Does nothing when visualizing is False.

        Args:
            visualizing: Must be True for any rendering to occur.
            path_coords: Ordered list of (col, row) cells forming the
                solution or replay path.  The last element is treated as the
                current player position.
            visited_coords: Set of (col, row) cells explored by BFS,
                drawn in the exploration colour.
        """
        if not visualizing:
            return

        last_y, last_x = self.__stdscr.getmaxyx()
        while not self.__check_terminal_size():
            self.__stdscr.clear()
            max_y, max_x = self.__stdscr.getmaxyx()
            w1 = "WARNING: Terminal is too small."
            w2 = "Please enlarge the terminal."
            w3 = "Press 'E' or ESC to Exit."

            sy = max(0, (max_y - 4) // 2)
            safe_x = max_x - 1

            if max_y > sy and safe_x > 0:
                px = max(0, (max_x - len(w1)) // 2)
                self.__stdscr.addstr(sy, px, w1[:safe_x])
            if max_y > sy + 1 and safe_x > 0:
                px = max(0, (max_x - len(w2)) // 2)
                self.__stdscr.addstr(sy + 1, px, w2[:safe_x])
            if max_y > sy + 3 and safe_x > 0:
                px = max(0, (max_x - len(w3)) // 2)
                self.__stdscr.addstr(sy + 3, px, w3[:safe_x])

            self.__stdscr.refresh()
            ch = self.__stdscr.getch()

            if ch == curses.KEY_RESIZE:
                curses.update_lines_cols()
                continue

            if ch in (ord('q'), ord('Q'), 27):
                sys.exit(0)

        if path_coords is None:
            path_coords = []

        if visited_coords is None:
            visited_coords = set()

        path_edges: Set[Tuple[Tuple[int, int], Tuple[int, int]]] = set()
        if path_coords:
            for i in range(len(path_coords) - 1):
                p1, p2 = path_coords[i], path_coords[i + 1]
                path_edges.add((p1, p2))
                path_edges.add((p2, p1))

        BLOCK = "\u2588"
        theme = self.__maze.themes.themes
        v_wall = BLOCK * 2
        corner = BLOCK * 2
        body = "  "
        h_wall = BLOCK * 4

        self.__stdscr.clear()
        max_y, max_x = self.__stdscr.getmaxyx()
        maze_w = self.__maze.width * 4 + 2
        maze_h = self.__maze.height * 2 + 1
        start_y = max(0, (max_y - maze_h - 2) // 2)
        start_x = max(0, (max_x - maze_w) // 2)

        current_y = start_y

        self.__stdscr.addstr(current_y, start_x, corner, theme['W_C'])
        for _ in self.__cells[0]:
            self.__stdscr.addstr(h_wall, theme['W_C'])
        current_y += 1

        for y, row in enumerate(self.__cells):
            self.__stdscr.addstr(current_y, start_x, "")
            for x, cell in enumerate(row):
                if cell.grid & Bearings.WEST:
                    self.__stdscr.addstr(v_wall, theme['W_C'])
                else:
                    if ((x - 1, y), (x, y)) in path_edges:
                        self.__stdscr.addstr(BLOCK * 2, theme['SOL_C'])
                    elif (
                        (x, y) in visited_coords
                        and (x - 1, y) in visited_coords
                    ):
                        self.__stdscr.addstr(BLOCK * 2, theme['EXP_C'])
                    else:
                        self.__stdscr.addstr(body, theme['P_C'])

                if path_coords and (x, y) == path_coords[-1]:
                    self.__stdscr.addstr(BLOCK * 2, theme['PL_C'])
                elif (x, y) == self.__maze.entry:
                    self.__stdscr.addstr(BLOCK * 2, theme['S_C'])
                elif (x, y) == self.__maze.exit:
                    self.__stdscr.addstr(BLOCK * 2, theme['E_C'])
                elif (x, y) in path_coords:
                    self.__stdscr.addstr(BLOCK * 2, theme['SOL_C'])
                elif (x, y) in visited_coords:
                    self.__stdscr.addstr(BLOCK * 2, theme['EXP_C'])
                elif cell.grid == 15:
                    self.__stdscr.addstr(BLOCK * 2, theme['CC_C'])
                else:
                    self.__stdscr.addstr(body, theme['P_C'])

            if row[-1].grid & Bearings.EAST:
                self.__stdscr.addstr(v_wall, theme['W_C'])
            current_y += 1

            self.__stdscr.addstr(current_y, start_x, corner, theme['W_C'])
            for x, cell in enumerate(row):
                if cell.grid & Bearings.SOUTH:
                    self.__stdscr.addstr(h_wall, theme['W_C'])
                else:
                    if ((x, y), (x, y + 1)) in path_edges:
                        self.__stdscr.addstr(BLOCK * 2, theme['SOL_C'])
                        self.__stdscr.addstr(corner, theme['W_C'])
                    elif (
                        (x, y) in visited_coords
                        and (x, y + 1) in visited_coords
                    ):
                        self.__stdscr.addstr(BLOCK * 2, theme['EXP_C'])
                        self.__stdscr.addstr(corner, theme['W_C'])
                    else:
                        self.__stdscr.addstr(body, theme['P_C'])
                        self.__stdscr.addstr(corner, theme['W_C'])
            current_y += 1
