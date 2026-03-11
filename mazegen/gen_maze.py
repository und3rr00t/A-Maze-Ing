import time
import curses
import random
from enum import Enum
from .cell import Cell
from .maze import Maze
from .visualization import MazeRenderer, Bearings
from typing import Any, Set, List, Tuple, Optional


class Directions(Enum):
    """Cardinal directions used by maze generation and solving algorithms.

    Each member maps to a 5-tuple (dx, dy, wall, opp_wall, move_char)
    where:

    - dx / dy: grid offset to the neighbour cell.
    - wall: :class:~mazegen.visualization.Bearings flag on the *current*
      cell that blocks movement in this direction.
    - opp_wall: :class:~mazegen.visualization.Bearings flag on the
      *neighbour* cell that is the other side of the same wall.
    - move_char: Single-character string used in the solution path
      representation ('N', 'S', 'E', 'W').
    """

    UP = (0, -1, Bearings.NORTH, Bearings.SOUTH, "N")
    DOWN = (0, 1, Bearings.SOUTH, Bearings.NORTH, "S")
    RIGHT = (1, 0, Bearings.EAST, Bearings.WEST, "E")
    LEFT = (-1, 0, Bearings.WEST, Bearings.EAST, "W")


class MazeSolver:
    """BFS-based maze solver with optional step-by-step visualisation.

    Finds the shortest path from the maze entry to the exit using a standard
    breadth-first search and optionally animates both the exploration and the
    final path-tracing phases frame-by-frame.
    """

    def __init__(
        self,
        maze: Maze,
        cells: List[List[Cell]],
        renderer: MazeRenderer,
        stdscr: curses.window
    ) -> None:
        """Attach the solver to an existing maze state.

        Args:
            maze: The :class:~mazegen.maze.Maze whose entry/exit and
                dimensions drive the search.
            cells: 2-D grid of :class:~mazegen.cell.Cell objects
                representing the current wall state.
            renderer: The :class:~mazegen.visualization.MazeRenderer used
                to animate the solving process.
            stdscr: The root curses window, used to poll for skip-key input
                and to refresh the display.
        """
        self.__maze: Maze = maze
        self.__cells: List[List[Cell]] = cells
        self.__renderer: MazeRenderer = renderer
        self.__stdscr: curses.window = stdscr

    def __check_skip(self, skip: bool, visualizing: bool) -> Tuple[bool, bool]:
        """Poll for a skip or theme-change key press during visualisation.

        Returns immediately without blocking.  Handles terminal resize events
        and theme-change ('t') input in addition to the skip condition.

        Args:
            skip: Current skip state; if True the function returns
                immediately without polling.
            visualizing: If False the function returns immediately.

        Returns:
            A 2-tuple (skip, needs_redraw) where skip is True if
            the user pressed Enter to skip, and needs_redraw is True
            if the theme changed or the terminal was resized.
        """
        needs_redraw = False
        if not visualizing or skip:
            return skip, needs_redraw
        self.__stdscr.nodelay(True)
        ch = self.__stdscr.getch()
        self.__stdscr.nodelay(False)

        if ch == curses.KEY_RESIZE:
            curses.update_lines_cols()
            return skip, True

        if ch != -1:
            if ch in (curses.KEY_ENTER, 10, 13):
                return True, needs_redraw
            char_pressed = chr(ch).lower() if 0 <= ch <= 255 else ""
            if char_pressed == 't':
                self.__maze.themes.next_theme()
                needs_redraw = True
        return False, needs_redraw

    @staticmethod
    def get_path_coords(
        start: Tuple[int, int], path_str: str
    ) -> List[Tuple[int, int]]:
        """Convert a direction-string path into a list of (col, row) coords.

        Args:
            start: The (col, row) origin of the path.
            path_str: A sequence of 'N', 'S', 'E', 'W'
                characters representing each step of the solution.

        Returns:
            An ordered list of (col, row) coordinates from start to the
            end of the path, inclusive of both endpoints.
        """
        coords = [start]
        x, y = start
        for move in path_str:
            if move == 'N':
                y -= 1
            elif move == 'S':
                y += 1
            elif move == 'E':
                x += 1
            elif move == 'W':
                x -= 1
            coords.append((x, y))
        return coords

    def find_shortest_path(self) -> str:
        """Run a BFS from entry to exit and return the solution as a string.

        Returns:
            A string of direction characters ('N', 'S', 'E',
            'W') describing the shortest path, or an empty string if no
            path exists.
        """
        queue: List[Tuple[Tuple[int, int], str]] = [((self.__maze.entry), "")]
        visited: Set[Tuple[int, int]] = {self.__maze.entry}

        while queue:
            (cx, cy), path = queue.pop(0)

            if (cx, cy) == self.__maze.exit:
                return path

            for direction in Directions:
                dx, dy, wall, _, move = direction.value
                nx, ny = cx + dx, cy + dy

                if (
                    0 <= nx < self.__maze.width
                    and 0 <= ny < self.__maze.height
                    and not (self.__cells[cy][cx].grid & wall)
                ):
                    if (nx, ny) not in visited:
                        visited.add((nx, ny))
                        queue.append(((nx, ny), path + move))

        return ""

    def solve_maze(self, visualizing: bool = False) -> None:
        """Solve the maze with optional animated BFS visualisation.

        Runs BFS, animating exploration cell-by-cell.  On reaching the exit,
        it animates retraction of non-path explored cells followed by tracing
        the solution path.  Pressing Enter at any point skips straight to the
        final state.

        Args:
            visualizing: True to animate the solve; False to run
                silently.
        """
        self.__stdscr.clear()
        self.__renderer.display_maze(visualizing=visualizing)
        self.__stdscr.refresh()

        skip = False
        queue: List[Tuple[Tuple[int, int], str]] = [((self.__maze.entry), "")]
        visited: Set[Tuple[int, int]] = {self.__maze.entry}
        visited_list: List[Tuple[int, int]] = [self.__maze.entry]

        while queue:
            (cx, cy), path = queue.pop(0)

            if (cx, cy) == self.__maze.exit:
                coords = self.get_path_coords(self.__maze.entry, path)

                if visualizing:
                    if not skip:
                        for v_coord in reversed(visited_list):
                            if (
                                v_coord in visited
                                and v_coord != self.__maze.entry
                                and v_coord != self.__maze.exit
                            ):
                                visited.remove(v_coord)

                            skip, needs_redraw = self.__check_skip(
                                skip, visualizing
                            )
                            if skip:
                                break

                            if needs_redraw:
                                self.__stdscr.clear()
                                self.__renderer.display_maze(
                                    visualizing, None, visited
                                )
                            else:
                                self.__renderer.update_bfs_step(
                                    v_coord, visited, True
                                )
                            self.__stdscr.refresh()
                            curses.napms(2)

                    if skip:
                        visited.clear()
                        self.__stdscr.clear()
                        self.__renderer.display_maze(
                            visualizing, coords, visited
                        )
                        self.__stdscr.refresh()
                        return

                    old_pos: Optional[Tuple[int, int]] = None
                    for coord in coords:
                        skip, needs_redraw = self.__check_skip(
                            skip, visualizing
                        )
                        if skip:
                            visited.clear()
                            self.__stdscr.clear()
                            self.__renderer.display_maze(
                                visualizing, coords, visited
                            )
                            self.__stdscr.refresh()
                            return

                        if needs_redraw:
                            self.__stdscr.clear()
                            tmp_path = coords[:coords.index(coord) + 1]
                            self.__renderer.display_maze(
                                visualizing, tmp_path, visited
                            )
                        else:
                            if old_pos is None:
                                self.__renderer.update_player_move(
                                    coord, coord
                                )
                            else:
                                self.__renderer.update_player_move(
                                    old_pos, coord
                                )

                        old_pos = coord
                        self.__stdscr.refresh()
                        curses.napms(20)
                return

            for direction in Directions:
                dx, dy, wall, _, move = direction.value
                nx, ny = cx + dx, cy + dy

                if (
                    0 <= nx < self.__maze.width
                    and 0 <= ny < self.__maze.height
                    and not (self.__cells[cy][cx].grid & wall)
                ):
                    if (nx, ny) not in visited:
                        visited.add((nx, ny))
                        visited_list.append((nx, ny))
                        queue.append(((nx, ny), path + move))

                        skip, needs_redraw = self.__check_skip(
                            skip, visualizing
                        )
                        if visualizing and not skip:
                            if needs_redraw:
                                self.__stdscr.clear()
                                self.__renderer.display_maze(
                                    visualizing, None, visited
                                )
                            else:
                                self.__renderer.update_bfs_step(
                                    (nx, ny), visited, False
                                )
                            self.__stdscr.refresh()
                            curses.napms(3)


class MazeExporter:
    """Serialises the solved maze to a plain-text output file."""

    def __init__(self, maze: Maze, cells: List[List[Cell]]) -> None:
        """Attach the exporter to a maze and its cell grid.

        Args:
            maze: The :class:~mazegen.maze.Maze whose metadata (seed, entry,
                exit, output path) is written to the file.
            cells: 2-D grid of :class:~mazegen.cell.Cell objects whose
                grid bitmask values are exported row-by-row as hex digits.
        """
        self.__maze: Maze = maze
        self.__cells: List[List[Cell]] = cells

    def write_output(self, solution: str) -> None:
        """Write the maze grid, metadata, and solution to the output file.

        Each row of cells is encoded as a string of single uppercase hex
        digits (0-F) representing each cell's wall bitmask.  After the grid,
        four metadata lines are appended: SEED, ENTRY, EXIT, and
        SOLUTION.

        Args:
            solution: The solution path string (sequence of 'N', 'S',
                'E', 'W' characters) as returned by
                :meth:MazeSolver.find_shortest_path.

        Raises:
            PermissionError: If the output file cannot be written.
            IsADirectoryError: If the output path is a directory.
        """
        output_path = self.__maze.output_file

        try:
            with open(output_path, "w") as f:
                for row in self.__cells:
                    hex_row = "".join([f"{cell.grid:X}" for cell in row])
                    f.write(f"{hex_row}\n")

                f.write(f"\nSEED: {self.__maze.seed}\n")
                f.write(
                    f"ENTRY: {self.__maze.entry[0]},{self.__maze.entry[1]}\n"
                )
                f.write(f"EXIT: {self.__maze.exit[0]},{self.__maze.exit[1]}\n")
                f.write(f"SOLUTION: {solution}\n")
        except PermissionError:
            raise PermissionError(
                f"Permission denied: can't read this file {output_path}"
            )
        except IsADirectoryError:
            raise IsADirectoryError(
                f"Is a directory: {output_path} is a directory"
            )


class MazeAlgorithms:
    """
    Maze generation algorithms (DFS and Wilson's) with visualisation support.

    Each algorithm method accepts and returns a skip flag so that the
    caller can chain multiple generation phases while preserving the skip
    state across them.
    """

    def __init__(
        self,
        maze: Maze,
        cells: List[List[Cell]],
        renderer: MazeRenderer,
        stdscr: curses.window
    ) -> None:
        """Attach the algorithm runner to an existing maze state.

        Args:
            maze: The :class:~mazegen.maze.Maze whose dimensions and
                configuration drive generation.
            cells: 2-D grid of :class:~mazegen.cell.Cell objects to be
                carved by the algorithm.
            renderer: The :class:~mazegen.visualization.MazeRenderer used
                to display incremental wall-removal updates.
            stdscr: The root curses window used to poll for skip-key input.
        """
        self.__maze: Maze = maze
        self.__cells: List[List[Cell]] = cells
        self.__renderer: MazeRenderer = renderer
        self.__stdscr: curses.window = stdscr

    def _check_skip(self, skip: bool, visualizing: bool) -> Tuple[bool, bool]:
        """Poll for a skip or theme-change key press during generation.

        Mirrors :meth:MazeSolver.__check_skip for the generation phase.

        Args:
            skip: Current skip state; returned unchanged if True.
            visualizing: If False returns immediately without polling.

        Returns:
            A 2-tuple (skip, needs_redraw) where skip is True if
            Enter was pressed, and needs_redraw is True if a resize or
            theme change occurred.
        """
        needs_redraw: bool = False
        if not visualizing or skip:
            return skip, needs_redraw

        self.__stdscr.nodelay(True)
        ch: int = self.__stdscr.getch()
        self.__stdscr.nodelay(False)

        if ch == curses.KEY_RESIZE:
            curses.update_lines_cols()
            return skip, True

        if ch != -1:
            if ch in (curses.KEY_ENTER, 10, 13):
                return True, needs_redraw
            char_pressed: str = chr(ch).lower() if 0 <= ch <= 255 else ""
            if char_pressed == 't':
                self.__maze.themes.next_theme()
                needs_redraw = True
        return False, needs_redraw

    def generate_dfs(self, skip: bool, visualizing: bool) -> bool:
        """Generate the maze using a randomised recursive DFS (iterative).

        Carves passages using an explicit stack, starting from the entry cell.
        Skips cells that belong to the '42' easter-egg pattern
        (ft_pattern flag), since those walls are pre-configured.
        Animates each wall removal when visualizing is True.

        Args:
            skip: If True the animation is already skipped; passed
                through to :meth:_check_skip.
            visualizing: True to animate generation frame-by-frame.

        Returns:
            The updated skip flag after generation completes.
        """
        sx: int
        sy: int
        sx, sy = self.__maze.entry
        stack: List[Tuple[int, int]] = [(sx, sy)]
        self.__cells[sy][sx].visited = True

        while stack:
            cx: int
            cy: int
            cx, cy = stack[-1]
            neighbors: List[Tuple[int, int, Bearings, Bearings]] = []

            for direction in Directions:
                dx, dy, wall, opp_wall, _ = direction.value
                nx: int = cx + dx
                ny: int = cy + dy

                if (
                    0 <= nx < self.__maze.width
                    and 0 <= ny < self.__maze.height
                ):
                    if not self.__cells[ny][nx].visited:
                        neighbors.append((nx, ny, wall, opp_wall))

            if neighbors:
                nx, ny, wall, opp_wall = random.choice(neighbors)

                self.__cells[cy][cx].grid &= ~wall
                self.__cells[ny][nx].grid &= ~opp_wall
                self.__cells[ny][nx].visited = True
                stack.append((nx, ny))

                skip, needs_redraw = self._check_skip(skip, visualizing)
                if visualizing and not skip:
                    if needs_redraw:
                        self.__stdscr.clear()
                        self.__renderer.display_maze(visualizing=visualizing)
                    else:
                        self.__renderer.update_wall_removal(cx, cy, nx, ny)
                    self.__stdscr.refresh()
                    curses.napms(10)
            else:
                stack.pop()

        return skip

    def generate_wilson(self, skip: bool, visualizing: bool) -> bool:
        """Generate the maze using Wilson's loop-erased random walk algorithm.

        Performs uniform spanning tree construction: a random unvisited cell
        starts a random walk; when it hits a visited cell the loop-erased walk
        is committed to the maze.  Cells belonging to the '42' pattern are
        excluded from the unvisited pool.

        Args:
            skip: If True the animation is already skipped; passed
                through to :meth:_check_skip.
            visualizing: True to animate each wall carve frame-by-frame.

        Returns:
            The updated skip flag after generation completes.
        """
        width: int = self.__maze.width
        height: int = self.__maze.height
        unvisited: List[Tuple[int, int]] = [
            (x, y) for x in range(width) for y in range(height)
        ]

        root: Tuple[int, int] = self.__maze.entry
        self.__cells[root[1]][root[0]].visited = True
        unvisited.remove(root)

        while unvisited:
            current: Optional[Tuple[int, int]] = None
            while not current and unvisited:
                current = random.choice(unvisited)
                if self.__cells[current[1]][current[0]].ft_pattern:
                    unvisited.remove(current)
                    current = None

            if not current:
                break

            path: List[Tuple[int, int]] = [current]

            while not self.__cells[current[1]][current[0]].visited:
                direction: Directions = random.choice(list(Directions))
                dx, dy, _, _, _ = direction.value
                nx: int = current[0] + dx
                ny: int = current[1] + dy

                if 0 <= nx < width and 0 <= ny < height:
                    if self.__cells[ny][nx].ft_pattern:
                        continue
                    neighbor: Tuple[int, int] = (nx, ny)

                    if neighbor in path:
                        path = path[:path.index(neighbor) + 1]
                    else:
                        path.append(neighbor)
                    current = neighbor

            for i in range(len(path) - 1):
                cx1: int
                cy1: int
                cx1, cy1 = path[i]
                cx2: int
                cy2: int
                cx2, cy2 = path[i + 1]

                for dir_enum in Directions:
                    dx, dy, wall, opp_wall, _ = dir_enum.value
                    if (cx1 + dx == cx2) and (cy1 + dy == cy2):
                        self.__cells[cy1][cx1].grid &= ~wall
                        self.__cells[cy2][cx2].grid &= ~opp_wall
                        break

                self.__cells[cy1][cx1].visited = True
                if (cx1, cy1) in unvisited:
                    unvisited.remove((cx1, cy1))

                skip, needs_redraw = self._check_skip(skip, visualizing)
                if visualizing and not skip:
                    if needs_redraw:
                        self.__stdscr.clear()
                        self.__renderer.display_maze(visualizing=visualizing)
                    else:
                        self.__renderer.update_wall_removal(cx1, cy1, cx2, cy2)
                    self.__stdscr.refresh()
                    curses.napms(10)

        return skip

    def make_imperfect(
        self, skip: bool, chance: float, visualizing: bool
    ) -> bool:
        """Randomly remove extra walls to create loops in the maze.

        For each non-pattern cell that has exactly three walls standing, there
        is a chance probability of breaking one of those walls, creating an
        additional passage and turning the perfect maze into an imperfect one.

        Args:
            skip: Current skip state; passed through to :meth:_check_skip.
            chance: Probability (0.0-1.0) of removing a wall for each eligible
                dead-end cell.
            visualizing: True to animate each wall removal.

        Returns:
            The updated skip flag after processing completes.
        """
        for y in range(self.__maze.height):
            for x in range(self.__maze.width):
                if self.__cells[y][x].ft_pattern:
                    continue

                walls: List[Tuple[int, int, Any, Any]] = []
                for direction in Directions:
                    dx: int
                    dy: int
                    wall: Any
                    opp: Any
                    dx, dy, wall, opp, _ = direction.value
                    if self.__cells[y][x].grid & wall:
                        walls.append((dx, dy, wall, opp))

                if len(walls) == 3 and random.random() < chance:
                    dx, dy, wall, opp_wall = random.choice(walls)
                    nx: int = x + dx
                    ny: int = y + dy

                    if (
                        0 <= nx < self.__maze.width
                        and 0 <= ny < self.__maze.height
                    ):
                        if self.__cells[ny][nx].ft_pattern:
                            continue

                        self.__cells[y][x].grid &= ~wall
                        self.__cells[ny][nx].grid &= ~opp_wall

                        skip, needs_redraw = self._check_skip(
                            skip, visualizing
                        )
                        if visualizing and not skip:
                            if needs_redraw:
                                self.__stdscr.clear()
                                self.__renderer.display_maze(
                                    visualizing=visualizing
                                )
                            else:
                                self.__renderer.update_wall_removal(
                                    x, y, nx, ny
                                )
                            self.__stdscr.refresh()
                            curses.napms(10)

        return skip


class MazeGenerator:
    """High-level façade that orchestrates maze generation, solving, and I/O.

    Owns and coordinates all sub-components: :class:Maze, :class:Cell
    grid, :class:MazeRenderer, :class:MazeSolver, :class:MazeExporter,
    and :class:MazeAlgorithms.  This is the primary interface used by the
    application layer.
    """

    def __init__(self, config_file: str, stdscr: curses.window) -> None:
        """Load configuration and initialise all sub-components.

        Args:
            config_file: Path to the plain-text configuration file.
            stdscr: The root curses window forwarded to all sub-components.
        """
        self.__stdscr: curses.window = stdscr
        self.__maze: Maze = Maze(config_file, self.__stdscr)
        random.seed(self.__maze.seed)
        self.__cells: List[List[Cell]] = Cell.get_cells(
            self.__maze, self.__stdscr
        )
        self.__solution: str = ""

        self.__renderer: MazeRenderer = MazeRenderer(
            self.__maze, self.__cells, self.__stdscr
        )
        self.__solver: MazeSolver = MazeSolver(
            self.__maze, self.__cells, self.__renderer, self.__stdscr
        )
        self.__exporter: MazeExporter = MazeExporter(self.__maze, self.__cells)

        self.__algorithms: MazeAlgorithms = MazeAlgorithms(
            self.__maze, self.__cells, self.__renderer, self.__stdscr
        )

    @property
    def maze(self) -> Maze:
        """The underlying :class:~mazegen.maze.Maze configuration object."""
        return self.__maze

    @property
    def cells(self) -> List[List[Any]]:
        """The 2-D cell grid cells[row][col]."""
        return self.__cells

    @property
    def solution(self) -> str:
        """The solution path string from the last :meth:generate_maze call."""
        return self.__solution

    @property
    def solution_coords(self) -> List[Tuple[int, int]]:
        """The solution path as an ordered list of (col, row) coordinates.

        Returns an empty list if no solution has been computed yet.
        """
        if not self.__solution:
            return []
        return MazeSolver.get_path_coords(self.__maze.entry, self.__solution)

    @property
    def end_y(self) -> int:
        """Terminal row immediately below the rendered maze."""
        return self.__renderer.get_maze_end_y()

    def update_player_move(
        self,
        old_pos: Tuple[int, int],
        new_pos: Tuple[int, int]
    ) -> None:
        """Delegate a player move render to the renderer.

        Args:
            old_pos: (col, row) the player is moving from.
            new_pos: (col, row) the player is moving to.
        """
        self.__renderer.update_player_move(old_pos, new_pos)

    def change_algorithm(self, visualizing: bool = False) -> None:
        """Toggle the generation algorithm and regenerate the maze.

        Switches between 'DFS' and 'WILSON'.  If no seed was provided
        in the config file, a new time-based seed is used so successive
        algorithm changes produce different mazes.  Rebuilds the cell grid,
        renderer, solver, exporter, and algorithm runner before regenerating.

        Args:
            visualizing: True to animate the new maze generation.
        """
        self.__maze.algo = "WILSON" if self.__maze.algo == "DFS" else "DFS"

        if not self.__maze.has_seed:
            self.__maze.seed = int(time.time())

        random.seed(self.__maze.seed)
        self.__cells = Cell.get_cells(self.__maze, self.__stdscr)
        self.__renderer = MazeRenderer(
            self.__maze, self.__cells, self.__stdscr
        )
        self.__solver = MazeSolver(
            self.__maze, self.__cells, self.__renderer, self.__stdscr
        )
        self.__exporter = MazeExporter(self.__maze, self.__cells)

        self.__algorithms = MazeAlgorithms(
            self.__maze, self.__cells, self.__renderer, self.__stdscr
        )

        self.generate_maze(visualizing)

    def generate_maze(self, visualizing: bool = False) -> None:
        """Generate the maze using the configured algorithm.

        Runs the selected algorithm (DFS or Wilson's), optionally followed by
        :meth:MazeAlgorithms.make_imperfect when PERFECT = False.
        Computes the solution via BFS after generation and, if visualizing and
        a skip was requested, performs a clean final full redraw.

        Args:
            visualizing: True to animate generation and the final redraw.
        """
        skip: bool = False
        algo: str = self.__maze.algo.upper()
        self.__stdscr.clear()

        if visualizing:
            self.__renderer.display_maze(visualizing=visualizing)
            self.__stdscr.refresh()

        if algo == "WILSON":
            skip = self.__algorithms.generate_wilson(skip, visualizing)
        else:
            skip = self.__algorithms.generate_dfs(skip, visualizing)

        if not self.__maze.perfection:
            skip = self.__algorithms.make_imperfect(skip, 0.7, visualizing)

        self.__solution = self.__solver.find_shortest_path()

        if visualizing:
            if skip:
                self.__stdscr.clear()
                self.__renderer.display_maze(visualizing=visualizing)
                self.__stdscr.refresh()

    def solve_maze(self, visualizing: bool = False) -> None:
        """Solve the maze with optional animated visualisation.

        Args:
            visualizing: True to animate the BFS solving process.
        """
        self.__solver.solve_maze(visualizing)

    def write_output(self) -> None:
        """Write the current maze state and solution to the output file."""
        self.__exporter.write_output(self.__solution)

    def display_maze(
        self,
        visualizing: bool = False,
        path_coords: Optional[List[Tuple[int, int]]] = None,
        visited_coords: Optional[Set[Tuple[int, int]]] = None
    ) -> None:
        """Perform a full maze redraw, forwarded to the renderer.

        Args:
            visualizing: Must be True for rendering to occur.
            path_coords: Solution or replay path to highlight.
            visited_coords: BFS-explored cells to highlight.
        """
        self.__renderer.display_maze(
            visualizing, path_coords, visited_coords
        )
