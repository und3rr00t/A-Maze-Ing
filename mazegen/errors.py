import sys
import curses
import traceback
from types import TracebackType
from typing import List, Optional


class ConfigSyntaxError(Exception):
    """Raised when a line in the configuration file has invalid syntax."""


class ConfigKeyError(Exception):
    """
    Raised when the configuration file contains an unknown or missing key.
    """

    @staticmethod
    def get_required_keys() -> List[str]:
        """Return the list of mandatory configuration keys.

        Returns:
            A list of uppercase key names that *must* be present in the
            configuration file.
        """
        return [
            "WIDTH", "HEIGHT", "ENTRY", "EXIT", "OUTPUT_FILE", "PERFECT"
        ]

    @staticmethod
    def get_additional_keys() -> List[str]:
        """Return the list of optional configuration keys.

        Returns:
            A list of uppercase key names that are recognised but not required
            in the configuration file.
        """
        return ["SEED", "ALGORITHM"]


class ConfigValueError(Exception):
    """Raised when a configuration key is present but its value is invalid."""


def __draw_error_popup(stdscr: curses.window, error_msg: str) -> None:
    """
    Render an error message in a centred box
    and wait for the user to dismiss it.

    The popup handles terminal resize events and mouse clicks gracefully,
    blocking until the user presses any non-mouse, non-resize key.

    Args:
        stdscr: The curses window to draw on.
        error_msg: The full error message to display inside the box.
    """
    curses.curs_set(0)
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_RED, -1)
    curses.mousemask(curses.ALL_MOUSE_EVENTS | curses.REPORT_MOUSE_POSITION)

    lines: List[str] = ["Error"]
    lines.extend(list(map(str.strip, error_msg.split('\n'))))
    bold_red: int = curses.color_pair(1) | curses.A_BOLD

    while True:
        stdscr.erase()
        clean_lines: List[str] = []
        max_y, max_x = stdscr.getmaxyx()

        for line in lines:
            safe_len: int = max_x - 5
            if safe_len > 0:
                clean_lines.append(line[:safe_len])

        box_width: int = max(len(line) for line in clean_lines) + 4
        box_width = min(box_width, max_x - 1)

        start_y: int = max(0, (max_y - (len(clean_lines) + 4)) // 2)
        start_x: int = max(0, (max_x - box_width) // 2)

        if max_y > start_y:
            stdscr.addstr(
                start_y, start_x,
                f"╔{'═' * (box_width - 2)}╗", bold_red
            )
        if max_y > start_y + 1:
            stdscr.addstr(
                start_y + 1, start_x,
                f"║ {clean_lines[0].center(box_width - 4)} ║", bold_red
            )
        if max_y > start_y + 2:
            stdscr.addstr(
                start_y + 2, start_x,
                f"╠{'═' * (box_width - 2)}╣", bold_red
            )

        for i, line in enumerate(clean_lines[1:]):
            if max_y > start_y + 3 + i:
                stdscr.addstr(
                    start_y + 3 + i, start_x,
                    f"║ {line.center(box_width - 4)} ║", bold_red
                )

        if max_y > start_y + 2 + len(clean_lines):
            stdscr.addstr(
                start_y + 2 + len(clean_lines),
                start_x, f"╚{'═' * (box_width - 2)}╝", bold_red
            )

        msg: str = "Press any key to exit"[:max_x-1]
        msg_y: int = min(max_y - 1, start_y + 4 + len(clean_lines))
        msg_x: int = max(0, (max_x - len(msg)) // 2)
        if max_y > msg_y and msg:
            stdscr.addstr(msg_y, msg_x, msg, bold_red)

        stdscr.refresh()
        ch: int = stdscr.getch()

        if ch == curses.KEY_MOUSE:
            continue

        if ch == curses.KEY_RESIZE:
            curses.update_lines_cols()
            continue

        if ch != -1:
            break


def report_error(error: Exception) -> None:
    """Display an unhandled exception to the user via a curses error popup.

    Extracts the originating filename and line number from the traceback,
    builds a formatted message, and shows it in a pop-up.  If curses is
    already active the existing screen is reused; otherwise a new curses
    session is started via :func:curses.wrapper.  Falls back to printing
    to stderr if curses itself raises an exception.

    Args:
        error: The exception to report to the user.
    """
    tb: Optional[TracebackType] = error.__traceback__
    location_info: str = ""

    if tb is not None:
        extracted_tb: traceback.StackSummary = traceback.extract_tb(tb)
        if extracted_tb:
            last_frame: traceback.FrameSummary = extracted_tb[-1]
            filename: str = last_frame.filename
            lineno: Optional[int] = last_frame.lineno
            location_info = f"\nFile: {filename}\nLine: {lineno}"

    error_name = (
        "DisplayError" if isinstance(error, curses.error)
        else type(error).__name__
    )
    full_error_msg: str = f"{error_name}:\n{str(error)}\n{location_info}"

    is_active: bool = False
    try:
        is_active = not curses.isendwin()
    except Exception:
        is_active = False

    if is_active:
        try:
            stdscr: curses.window = curses.initscr()
            __draw_error_popup(stdscr, full_error_msg)
        except Exception:
            print(f"Error {full_error_msg}", file=sys.stderr)
    else:
        try:
            curses.wrapper(
                lambda stdscr: __draw_error_popup(stdscr, full_error_msg)
            )
        except Exception:
            print(f"Error {full_error_msg}", file=sys.stderr)

    sys.exit(1)
