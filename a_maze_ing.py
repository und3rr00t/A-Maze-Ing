import sys
import curses
from playing_mod import MazePlayer
from typing import Optional, Tuple, List
from mazegen import MazeGenerator, report_error, SplashScreen, clean


def draw_main_menu(
    stdscr: curses.window, gen_maze: MazeGenerator, show_sol: bool = False
) -> str:
    """Display the main menu overlay on top of the maze and wait for input.

    Args:
        stdscr: The curses window to draw on.
        gen_maze: The active maze generator instance used to display the maze.
        show_sol: Whether to render the solution path on the maze.

    Returns:
        A single lowercase character string representing the key pressed,
        or 'resize' if a terminal resize event was detected.
    """
    path_c: Optional[List[Tuple[int, int]]] = (
        gen_maze.solution_coords if show_sol else None
    )
    gen_maze.display_maze(visualizing=True, path_coords=path_c)

    max_y, max_x = stdscr.getmaxyx()
    m_c: int = gen_maze.maze.themes.themes["MENU_C"]

    info_line: str = (
        f" SAVED: {gen_maze.maze.output_file} │ "
        f"PATH LENGTH: {len(gen_maze.solution)} │ "
        f"ALGO: {gen_maze.maze.algo} "
    )

    sol_text: str = "S: Regen Sol" if show_sol else "S: Show Sol"
    menu_items: List[str] = [
        sol_text, "R: New Maze", "P: Play", "A: Algo", "T: Theme", "E: Exit"
    ]

    start_y: int = max(1, min(max_y - 6, gen_maze.end_y + 1))
    info_x: int = max(0, (max_x - len(info_line)) // 2)
    stdscr.addstr(start_y, info_x, info_line[:max_x - 1], m_c)

    parts: List[str] = [f" {item} " for item in menu_items]
    top: str = "  ".join(f"╔{'═' * len(p)}╗" for p in parts)
    mid: str = "  ".join(f"║{p}║" for p in parts)
    bot: str = "  ".join(f"╚{'═' * len(p)}╝" for p in parts)

    menu_x: int = max(0, (max_x - len(top)) // 2)
    for i, line in enumerate((top, mid, bot)):
        stdscr.move(start_y + 2 + i, 0)
        stdscr.clrtoeol()
        stdscr.addstr(start_y + 2 + i, menu_x, line[:max_x - 1], m_c)

    stdscr.refresh()

    while True:
        ch: int = stdscr.getch()
        if ch == curses.KEY_RESIZE:
            curses.update_lines_cols()
            return "resize"
        if ch != -1:
            return chr(ch).lower() if 0 <= ch <= 255 else ""


main_art: List[str] = [
    "█████╗       ███╗   ███╗ █████╗ █"
    "██████╗███████╗    ██╗███╗   ██╗ ██████╗ ",
    "██╔══██╗      ████╗ ████║██╔══██╗"
    "╚══███╔╝██╔════╝    ██║████╗  ██║██╔════╝ ",
    "███████║█████╗██╔████╔██║███████║"
    "  ███╔╝ █████╗█████╗██║██╔██╗ ██║██║  ███╗",
    "██╔══██║╚════╝██║╚██╔╝██║██╔══██║"
    " ███╔╝  ██╔══╝╚════╝██║██║╚██╗██║██║   ██║",
    "██║  ██║      ██║ ╚═╝ ██║██║  ██║"
    "███████╗███████╗    ██║██║ ╚████║╚██████╔╝",
    "╚═╝  ╚═╝      ╚═╝     ╚═╝╚═╝  ╚═╝"
    "╚══════╝╚══════╝    ╚═╝╚═╝  ╚═══╝ ╚═════╝ "
]


def a_maz_ing(stdscr: curses.window, gen_maze: MazeGenerator) -> None:
    """
    Run one full maze session: generate,
    display, and handle menu interactions.

    Loops on the main menu until the user chooses to generate a new maze,
    at which point it returns so the outer loop can restart.

    Args:
        stdscr: The root curses window.
        config_file: Path to the maze configuration file.
    """
    play_mode = MazePlayer(gen_maze, stdscr)

    gen_maze.generate_maze(visualizing=True)
    gen_maze.write_output()

    show_sol: bool = False

    while True:
        choice: str = draw_main_menu(stdscr, gen_maze, show_sol)

        if choice == 'resize':
            stdscr.clear()
        elif choice == 's':
            gen_maze.solve_maze(True)
            show_sol = True
        elif choice == 'r':
            return
        elif choice == 'p':
            play_mode.play()
            show_sol = False
        elif choice == 'a':
            gen_maze.change_algorithm(visualizing=True)
            gen_maze.write_output()
            show_sol = False
        elif choice == 't':
            gen_maze.maze.themes.next_theme()
        elif choice == 'e':
            sys.exit(0)


def intro(stdscr: curses.window) -> None:
    """Display the animated intro splash screen with the application title art.

    Args:
        stdscr: The root curses window.
    """
    splash = SplashScreen(stdscr)

    splash.show_art(
        main_art, 102, "Press Enter to start",
        101, "Created by adraji & oused-da"
    )


def start_app(stdscr: curses.window, config_file: str) -> None:
    """Initialise curses, show the intro, and run the main maze loop forever.

    Args:
        stdscr: The root curses window provided by :func:curses.wrapper.
        config_file: Path to the maze configuration file.
    """
    curses.curs_set(0)
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(101, curses.COLOR_WHITE, -1)
    curses.init_pair(102, curses.COLOR_CYAN, -1)

    gen_maze = MazeGenerator(config_file, stdscr)
    intro(stdscr)

    while True:
        a_maz_ing(stdscr, gen_maze)
        gen_maze = MazeGenerator(config_file, stdscr)


def main() -> None:
    """Entry point: validate CLI arguments, then launch the curses application.

    Exits with a usage message if the config file argument is missing.
    Delegates error display to :func:report_error on unexpected exceptions.
    """
    if len(sys.argv) != 2:
        print("Usage: python a_maze_ing.py <config_file>")
        sys.exit(1)

    try:
        curses.wrapper(start_app, sys.argv[1])
    except Exception as e:
        report_error(e)


if __name__ == "__main__":
    try:
        main()
    except BaseException:
        clean()
        curses.curs_set(1)
