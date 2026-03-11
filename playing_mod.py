import time
import curses
from enum import Enum
from typing import List, Tuple, Optional
from sound_manager import AudioManager
from mazegen.visualization import Bearings
from mazegen import MazeGenerator, SplashScreen


art_play: List[str] = [
    "██████╗ ██╗      █████╗ ██╗   ██╗",
    "██╔══██╗██║     ██╔══██╗╚██╗ ██╔╝",
    "██████╔╝██║     ███████║ ╚████╔╝ ",
    "██╔═══╝ ██║     ██╔══██║  ╚██╔╝  ",
    "██║     ███████╗██║  ██║   ██║   ",
    "╚═╝     ╚══════╝╚═╝  ╚═╝   ╚═╝   "
]

art_victory: List[str] = [
    "██╗   ██╗██╗ ██████╗████████╗ ██████╗ ██████╗ ██╗   ██╗",
    "██║   ██║██║██╔════╝╚══██╔══╝██╔═══██╗██╔══██╗╚██╗ ██╔╝",
    "██║   ██║██║██║        ██║   ██║   ██║██████╔╝ ╚████╔╝ ",
    "╚██╗ ██╔╝██║██║        ██║   ██║   ██║██╔══██╗  ╚██╔╝  ",
    " ╚████╔╝ ██║╚██████╗   ██║   ╚██████╔╝██║  ██║   ██║   ",
    "  ╚═══╝  ╚═╝ ╚═════╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝   ╚═╝   "
]

art_lose: List[str] = [
    "██████╗ ███████╗███████╗███████╗ █████╗ ████████╗",
    "██╔══██╗██╔════╝██╔════╝██╔════╝██╔══██╗╚══██╔══╝",
    "██║  ██║█████╗  █████╗  █████╗  ███████║   ██║   ",
    "██║  ██║██╔══╝  ██╔══╝  ██╔══╝  ██╔══██║   ██║   ",
    "██████╔╝███████╗██║     ███████╗██║  ██║   ██║   ",
    "╚═════╝ ╚══════╝╚═╝     ╚══════╝╚═╝  ╚═╝   ╚═╝   "
]


def countdown(stdscr: curses.window, bg_idx: int) -> None:
    """Display an animated 3-2-1-GO countdown before play mode begins.

    Renders each frame as large ASCII art centred on screen, plays the
    matching sound effect, and pauses for one second per frame.

    Args:
        stdscr: The curses window to draw on.
        bg_idx: The curses colour index used for the background so the
            countdown colour pair is initialised with a matching background.
    """
    curses.curs_set(0)
    curses.init_pair(109, curses.COLOR_WHITE, bg_idx)
    audio = AudioManager()

    frames: List[Tuple[str, List[str]]] = [
        ("3", [
            "██████╗ ", "╚════██╗", " █████╔╝",
            " ╚═══██╗", "██████╔╝", "╚═════╝ "
        ]),
        ("2", [
            "██████╗ ", "╚════██╗", " █████╔╝",
            "██╔═══╝ ", "███████╗", "╚══════╝"
        ]),
        ("1", [
            " ██╗ ", "███║ ", "╚██║ ",
            " ██║ ", " ██║ ", " ╚═╝ "
        ]),
        ("go", [
            "██████╗  ██████╗ ", "██╔════╝ ██╔═══██╗",
            "██║  ███╗██║   ██║", "██║   ██║██║   ██║",
            "╚██████╔╝╚██████╔╝", " ╚═════╝  ╚═════╝ "
        ])
    ]

    for sound, frame in frames:
        audio.load_sound(sound, f"{sound}.wav")
        stdscr.clear()
        height, width = stdscr.getmaxyx()
        start_y: int = max(0, (height - len(frame)) // 2)

        for index, line in enumerate(frame):
            start_x: int = max(0, (width - len(line)) // 2)
            stdscr.addstr(
                start_y + index, start_x, line, curses.color_pair(109)
            )

        stdscr.refresh()
        audio.stop_all()
        audio.play_sound(sound)
        time.sleep(1.0)

    stdscr.clear()
    stdscr.refresh()


class Moves(Enum):
    """Directional movement mappings for play mode.

    Each member maps a WASD key to a (dx, dy, wall) tuple where wall
    is the :class:~mazegen.visualization.Bearings flag that must be *clear*
    for movement in that direction to be valid.
    """

    W = (0, -1, Bearings.NORTH)
    S = (0, 1, Bearings.SOUTH)
    A = (-1, 0, Bearings.WEST)
    D = (1, 0, Bearings.EAST)


class MazePlayer:
    """Handles interactive play mode where the user navigates the maze.

    Manages player position, input handling, sound playback, and rendering
    of the HUD, victory/defeat screens, and path replay.
    """

    def __init__(self, gen_maze: MazeGenerator, stdscr: curses.window) -> None:
        """Attach the player to an existing maze generator and window.

        Args:
            gen_maze: The active :class:~mazegen.MazeGenerator instance
                whose maze the player will navigate.
            stdscr: The root curses window used for rendering.
        """
        self.__gen_maze: MazeGenerator = gen_maze
        self.__stdscr: curses.window = stdscr
        self.__maze = self.__gen_maze.maze
        self.__cells = self.__gen_maze.cells
        self.__audio = AudioManager()

        for s_name in (
            "intro", "victory", "defeat", "valid_move", "invalid_move"
        ):
            self.__audio.load_sound(s_name, f"{s_name}.wav")

    def __draw_ui(self, msg: str) -> None:
        """Render a segmented box HUD below the maze.

        Splits msg on '|', wraps each segment in a box border, and
        draws the result centred horizontally just below the last maze row.
        Does nothing if there is insufficient vertical space.

        Args:
            msg: Pipe-separated string of HUD segments to display.
        """
        max_y, max_x = self.__stdscr.getmaxyx()
        y_start: int = self.__gen_maze.end_y + 1

        if y_start + 3 > max_y:
            return

        parts: List[str] = [f" {item.strip()} " for item in msg.split('|')]
        top: str = "  ".join(f"╔{'═' * len(p)}╗" for p in parts)
        mid: str = "  ".join(f"║{p}║" for p in parts)
        bot: str = "  ".join(f"╚{'═' * len(p)}╝" for p in parts)

        menu_x: int = max(0, (max_x - len(top)) // 2)
        m_c: int = self.__maze.themes.themes["MENU_C"]

        for i, line in enumerate((top, mid, bot)):
            self.__stdscr.move(y_start + i, 0)
            self.__stdscr.clrtoeol()
            self.__stdscr.addstr(y_start + i, menu_x, line[:max_x - 1], m_c)

        self.__stdscr.refresh()

    def play(self) -> None:
        """Enter interactive play mode.

        Shows the intro splash, runs the countdown, then loops the gameplay
        session.  Handles winning, losing, theme changes, path replay, and
        returns to the caller when the user exits.
        """
        curses.mousemask(
            curses.ALL_MOUSE_EVENTS | curses.REPORT_MOUSE_POSITION
        )

        bg_idx: int = self.__maze.themes.bg_idx

        for c_id, color in (
            (103, curses.COLOR_BLUE),
            (104, curses.COLOR_GREEN),
            (105, curses.COLOR_RED),
            (108, curses.COLOR_WHITE)
        ):
            curses.init_pair(c_id, color, bg_idx)

        splash = SplashScreen(self.__stdscr)
        self.__audio.play_sound("intro")
        splash.show_art(
            art_play, 103, "Are you ready?", 108, "Press ENTER to start"
        )
        self.__audio.stop_all()

        countdown(self.__stdscr, bg_idx)
        play_msg: str = " PLAY MODE | W,A,S,D: Move | T: Theme | E: Exit "

        while True:
            px, py = self.__maze.entry
            target = self.__maze.exit
            path: List[Tuple[int, int]] = [(px, py)]
            start_time: float = time.time()

            self.__gen_maze.display_maze(True, path)
            self.__draw_ui(play_msg)

            won: bool = False
            while True:
                if (px, py) == target:
                    won = True
                    break

                self.__stdscr.nodelay(True)
                ch: int = self.__stdscr.getch()
                self.__stdscr.nodelay(False)

                if ch == curses.KEY_RESIZE:
                    curses.update_lines_cols()
                    self.__stdscr.clear()
                    self.__gen_maze.display_maze(True, path)
                    self.__draw_ui(play_msg)
                    continue

                if ch == -1:
                    continue

                c: str = chr(ch).lower() if 0 <= ch <= 255 else ""
                old_px, old_py = px, py

                if c == 'e':
                    self.__audio.stop_all()
                    self.__audio.play_sound("defeat")
                    if splash.show_art(
                        art_lose, 105, "You failed!", 108,
                        "E: Exit │ R: Replay", expected_chars=['r', 'e']
                    ) == 'r':
                        self.__audio.stop_all()
                        break
                    self.__audio.quit()
                    return

                if c == 't':
                    self.__maze.themes.next_theme()
                    self.__gen_maze.display_maze(True, path)
                    self.__draw_ui(play_msg)
                    continue

                if c.upper() in Moves.__members__:
                    dx, dy, wall = Moves[c.upper()].value
                    if not (self.__cells[py][px].grid & wall):
                        self.__audio.play_sound("valid_move")
                        px, py = px + dx, py + dy
                    else:
                        self.__audio.play_sound("invalid_move")

                if (px, py) != (old_px, old_py):
                    path.append((px, py))
                    self.__gen_maze.update_player_move(
                        (old_px, old_py), (px, py)
                    )

            if not won:
                continue

            self.__audio.stop_all()
            self.__audio.play_sound("victory")
            dur: float = time.time() - start_time
            choice: Optional[str] = splash.show_art(
                art_victory, 104, f"Time: {dur:.2f}s", 108,
                "E: Exit │ F: Path │ R: Replay",
                expected_chars=['e', 'r', 'f']
            )
            self.__audio.stop_all()

            if choice == 'e':
                self.__audio.quit()
                return
            if choice == 'r':
                continue

            rep_msg: str = " REPLAYING PATH | ENTER: Skip "
            self.__stdscr.nodelay(True)
            self.__gen_maze.display_maze(True, [])
            self.__draw_ui(rep_msg)

            for i, pos in enumerate(path):
                ch_skip: int = self.__stdscr.getch()
                if ch_skip == curses.KEY_RESIZE:
                    curses.update_lines_cols()
                    self.__stdscr.clear()
                    self.__gen_maze.display_maze(True, path[:i + 1])
                    self.__draw_ui(rep_msg)
                    continue

                if ch_skip in (curses.KEY_ENTER, 10, 13):
                    break

                self.__gen_maze.update_player_move(path[max(0, i - 1)], pos)
                curses.napms(30)

            self.__gen_maze.display_maze(True, path)
            self.__draw_ui(" PATH REVIEW COMPLETE: Press Any Key ")
            self.__stdscr.nodelay(False)
            while True:
                ch = self.__stdscr.getch()
                if ch != curses.KEY_MOUSE:
                    break
            self.__audio.quit()
            return
