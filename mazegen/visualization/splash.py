import curses
from typing import List, Optional


class SplashScreen:
    """Renders animated ASCII-art splash screens using curses.

    Art lines are revealed progressively column-by-column each frame, and
    an optional blinking prompt is shown once the animation completes.
    Input handling is deferred until the art is fully drawn.
    """

    def __init__(self, stdscr: curses.window) -> None:
        """Attach the splash screen to a curses window.

        Args:
            stdscr: The curses window to draw on.
        """
        self.__stdscr: curses.window = stdscr

    def show_art(
        self,
        art: List[str],
        art_pair: int,
        msg: str,
        msg_pair: int = 0,
        opts: Optional[str] = None,
        expected_chars: Optional[List[str]] = None
    ) -> Optional[str]:
        """Display an animated splash screen and return the user's choice.

        The art is revealed one column at a time.  Once fully drawn, msg
        is shown as a bold caption and opts (if provided) blinks between
        A_DIM and A_BOLD every 50 frames.  The function blocks until
        the user presses Enter (returns None) or one of expected_chars.
        Terminal resize events are handled gracefully.

        Args:
            art: List of equal-width strings forming the ASCII-art banner.
            art_pair: Curses colour-pair index used to render the art.
            msg: Caption text displayed below the art once animation finishes.
            msg_pair: Curses colour-pair index for msg and opts.
                Defaults to 0 (the terminal default).
            opts: Optional secondary prompt (e.g. "E: Exit │ R: Replay").
                Shown below msg with a blinking effect.
            expected_chars: List of single lowercase characters that the caller
                wants to handle.  If the user presses one of these keys it is
                returned directly.  Defaults to an empty list (only Enter is
                accepted).

        Returns:
            The matched character from expected_chars if the user pressed
            one of those keys, or None if the user pressed Enter.
        """
        if expected_chars is None:
            expected_chars = []

        curses.curs_set(0)
        curses.use_default_colors()
        self.__stdscr.nodelay(True)

        frame: int = 0
        art_len: int = len(art)
        art_width: int = max([len(line) for line in art])

        while True:
            self.__stdscr.erase()

            max_y, max_x = self.__stdscr.getmaxyx()

            start_y: int = max(0, (max_y - (art_len + 4)) // 2)
            msg_y: int = start_y + art_len + 1
            opts_y: int = start_y + art_len + 3

            for y in range(start_y - 3, opts_y + 3):
                if 0 <= y < max_y:
                    self.__stdscr.move(y, 0)
                    self.__stdscr.clrtoeol()

            art_attr: int = curses.color_pair(art_pair)
            cols_to_show: int = min(art_width, frame)

            for i, line in enumerate(art):
                if 0 <= start_y + i < max_y:
                    visible_line: str = line[:cols_to_show]
                    s_line: str = visible_line[:max_x - 1]

                    self.__stdscr.addstr(
                        start_y + i,
                        max(0, (max_x - len(s_line)) // 2),
                        s_line,
                        art_attr
                    )

            msg_attr: int = curses.color_pair(msg_pair) | curses.A_BOLD
            if 0 <= msg_y < max_y and max_x > 1 and art_width < frame:
                s_msg: str = msg[:max_x - 1]
                self.__stdscr.addstr(
                    msg_y, max(0, (max_x - len(s_msg)) // 2),
                    s_msg, msg_attr
                )

            if (
                opts
                and 0 <= opts_y < max_y
                and max_x > 1
                and art_width < frame
            ):
                s_opts: str = opts[:max_x - 1]
                opt_attr: int = curses.color_pair(msg_pair) | (
                    curses.A_DIM if (frame // 50) % 2 == 0
                    else curses.A_BOLD
                )
                self.__stdscr.addstr(
                    opts_y,
                    max(0, (max_x - len(s_opts)) // 2),
                    s_opts,
                    opt_attr
                )

            self.__stdscr.refresh()

            ch: int = self.__stdscr.getch() if art_width < frame else -1
            if ch != -1:
                if ch == curses.KEY_RESIZE:
                    curses.update_lines_cols()
                else:
                    char_input: str = chr(ch).lower() if 0 <= ch <= 255 else ""

                    if char_input in expected_chars:
                        return char_input

                    if ch in (curses.KEY_ENTER, 10, 13):
                        return None

            frame += 1
            curses.napms(10)
