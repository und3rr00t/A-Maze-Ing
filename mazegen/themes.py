import curses
from typing import Callable, Dict, List


class Themes:
    """Manages colour themes for the maze renderer.

    Encapsulates a collection of theme factory methods and tracks the
    currently active theme.  Each theme defines curses colour pairs for
    walls, the player, the solution path, explored cells, entry/exit
    markers, and the menu overlay.

    The background colour is stored as bg_idx and is set per-theme
    using :meth:__set_bg_color.
    """

    def __init__(self, stdscr: curses.window) -> None:
        """Initialise themes and load the first theme.

        Args:
            stdscr: The root curses window used to apply the background
                colour via :func:curses.window.bkgd.
        """
        self.__stdscr: curses.window = stdscr
        self.__current_index: int = 0
        self.__bg_idx: int = curses.COLOR_BLACK
        self.__themes: List[Callable[[], Dict[str, int]]] = [
            self.__get_badlands_theme,
            self.__get_dark_forest_theme,
            self.__get_cherry_grove_theme,
            self.__get_pale_garden_theme
        ]
        self.__theme: Dict[str, int] = self.__themes[self.__current_index]()

    @property
    def themes(self) -> Dict[str, int]:
        """Return the active theme colour-pair mapping.

        Returns:
            A dictionary mapping semantic colour names (e.g. 'W_C',
            'P_C', 'MENU_C') to curses colour-pair integers.
        """
        return self.__theme

    @property
    def bg_idx(self) -> int:
        """Return the curses colour index used as the background colour.

        Returns:
            An integer curses colour index for the current theme background.
        """
        return self.__bg_idx

    def next_theme(self) -> None:
        """Advance to the next theme in the rotation and apply it."""
        self.__current_index = (self.__current_index + 1) % len(self.__themes)
        self.__theme = self.__themes[self.__current_index]()

    def __set_bg_color(self, hex_str: str, fallback: int) -> int:
        """Configure the background custom colour and return its index.

        Attempts to initialise curses colour index 19 with an RGB value
        derived from hex_str.  Falls back to a standard colour constant
        when the terminal does not support colour redefinition.

        Args:
            hex_str: Six-character hex string RRGGBB (no leading #).
            fallback: A standard curses colour constant used when
                :func:curses.can_change_color returns False.

        Returns:
            The curses colour index to use as the background (19 or
            fallback).
        """
        bg_idx = 19
        if curses.can_change_color():
            r = int(hex_str[0:2], 16) * 1000 // 255
            g = int(hex_str[2:4], 16) * 1000 // 255
            b = int(hex_str[4:6], 16) * 1000 // 255
            curses.init_color(bg_idx, r, g, b)
            return bg_idx
        return fallback

    def __apply_bg(self, bg_idx: int) -> None:
        """Apply the background colour to the entire curses window.

        Initialises colour pair 19 with white foreground and the given
        background index, then sets it as the window background character.

        Args:
            bg_idx: The curses colour index to use as the background.
        """
        curses.init_pair(19, curses.COLOR_WHITE, bg_idx)
        self.__stdscr.bkgd(' ', curses.color_pair(19))

    def __init_hex_color(
        self, color_num: int, hex_str: str, fg_fallback: int, bg_idx: int
    ) -> int:
        """Initialise a curses colour pair from a hex RGB value.

        When the terminal supports colour redefinition, the RGB components of
        hex_str are used to define color_num and then paired with
        bg_idx.  Otherwise, fg_fallback is used as the foreground.

        Args:
            color_num: The curses colour *and* colour-pair index to initialise.
            hex_str: Six-character RRGGBB hex string for the foreground.
            fg_fallback: Standard curses colour constant used as a fallback
                foreground when colour redefinition is unsupported.
            bg_idx: The curses colour index used as the background.

        Returns:
            The curses.color_pair(color_num) integer ready for use in
            :func:curses.window.addstr calls.
        """
        if curses.can_change_color():
            r = int(hex_str[0:2], 16) * 1000 // 255
            g = int(hex_str[2:4], 16) * 1000 // 255
            b = int(hex_str[4:6], 16) * 1000 // 255
            curses.init_color(color_num, r, g, b)
            curses.init_pair(color_num, color_num, bg_idx)
            return curses.color_pair(color_num)
        curses.init_pair(color_num, fg_fallback, bg_idx)
        return curses.color_pair(color_num)

    def __get_badlands_theme(self) -> Dict[str, int]:
        """Build and return the Badlands colour theme.

        A warm, desert-inspired palette with a near-black brown background,
        rust-orange walls, and golden menu accents.

        Returns:
            A dictionary of semantic colour names to curses colour-pair
            integers for this theme.
        """
        self.__bg_idx = self.__set_bg_color("1A0A00", curses.COLOR_BLACK)
        self.__apply_bg(self.__bg_idx)

        res = {
            "W_C": self.__init_hex_color(
                11, "D35400", curses.COLOR_RED, self.__bg_idx
            ),
            "P_C": self.__init_hex_color(
                12, "FDF5E6", curses.COLOR_WHITE, self.__bg_idx
            ),
            "S_C": self.__init_hex_color(
                13, "27AE60", curses.COLOR_GREEN, self.__bg_idx
            ),
            "E_C": self.__init_hex_color(
                14, "F1C40F", curses.COLOR_YELLOW, self.__bg_idx
            ),
            "SOL_C": self.__init_hex_color(
                15, "64D2FF", curses.COLOR_BLUE, self.__bg_idx
            ),
            "EXP_C": self.__init_hex_color(
                16, "34495E", curses.COLOR_CYAN, self.__bg_idx
            ),
            "CC_C": self.__init_hex_color(
                17, "505050", curses.COLOR_BLACK, self.__bg_idx
            ),
            "PL_C": self.__init_hex_color(
                18, "FF8C00", curses.COLOR_MAGENTA, self.__bg_idx
            )
        }
        res["M_C"] = res["SOL_C"] | curses.A_REVERSE
        res["MENU_C"] = self.__init_hex_color(
            20, "D35400", curses.COLOR_YELLOW, self.__bg_idx
        )
        return res

    def __get_dark_forest_theme(self) -> Dict[str, int]:
        """Build and return the Dark Forest colour theme.

        A deep-green palette evoking a dense, shadowy woodland.

        Returns:
            A dictionary of semantic colour names to curses colour-pair
            integers for this theme.
        """
        self.__bg_idx = self.__set_bg_color("051409", curses.COLOR_BLACK)
        self.__apply_bg(self.__bg_idx)

        res = {
            "W_C": self.__init_hex_color(
                11, "0D3B18", curses.COLOR_GREEN, self.__bg_idx
            ),
            "P_C": self.__init_hex_color(
                12, "ECF0F1", curses.COLOR_WHITE, self.__bg_idx
            ),
            "S_C": self.__init_hex_color(
                13, "2ECC71", curses.COLOR_GREEN, self.__bg_idx
            ),
            "E_C": self.__init_hex_color(
                14, "C0392B", curses.COLOR_RED, self.__bg_idx
            ),
            "SOL_C": self.__init_hex_color(
                15, "3498DB", curses.COLOR_BLUE, self.__bg_idx
            ),
            "EXP_C": self.__init_hex_color(
                16, "2C3E50", curses.COLOR_CYAN, self.__bg_idx
            ),
            "CC_C": self.__init_hex_color(
                17, "3C3C3C", curses.COLOR_BLACK, self.__bg_idx
            ),
            "PL_C": self.__init_hex_color(
                18, "654321", curses.COLOR_MAGENTA, self.__bg_idx
            )
        }
        res["M_C"] = res["W_C"] | curses.A_REVERSE
        res["MENU_C"] = self.__init_hex_color(
            20, "0D3B18", curses.COLOR_YELLOW, self.__bg_idx
        )
        return res

    def __get_cherry_grove_theme(self) -> Dict[str, int]:
        """Build and return the Cherry Grove colour theme.

        A soft pink-and-violet palette inspired by cherry blossom scenery.

        Returns:
            A dictionary of semantic colour names to curses colour-pair
            integers for this theme.
        """
        self.__bg_idx = self.__set_bg_color("1A0B12", curses.COLOR_BLACK)
        self.__apply_bg(self.__bg_idx)

        res = {
            "W_C": self.__init_hex_color(
                11, "FFB6C1", curses.COLOR_MAGENTA, self.__bg_idx
            ),
            "P_C": self.__init_hex_color(
                12, "FFFFFF", curses.COLOR_WHITE, self.__bg_idx
            ),
            "S_C": self.__init_hex_color(
                13, "DB7093", curses.COLOR_RED, self.__bg_idx
            ),
            "E_C": self.__init_hex_color(
                14, "8E44AD", curses.COLOR_MAGENTA, self.__bg_idx
            ),
            "SOL_C": self.__init_hex_color(
                15, "87CEEB", curses.COLOR_CYAN, self.__bg_idx
            ),
            "EXP_C": self.__init_hex_color(
                16, "FF69B4", curses.COLOR_MAGENTA, self.__bg_idx
            ),
            "CC_C": self.__init_hex_color(
                17, "F0F0F0", curses.COLOR_WHITE, self.__bg_idx
            ),
            "PL_C": self.__init_hex_color(
                18, "BA55D3", curses.COLOR_MAGENTA, self.__bg_idx
            )
        }
        res["M_C"] = res["E_C"] | curses.A_REVERSE
        res["MENU_C"] = self.__init_hex_color(
            20, "FFB6C1", curses.COLOR_YELLOW, self.__bg_idx
        )
        return res

    def __get_pale_garden_theme(self) -> Dict[str, int]:
        """Build and return the Pale Garden colour theme.

        A muted grey-blue palette with a minimal, airy aesthetic.

        Returns:
            A dictionary of semantic colour names to curses colour-pair
            integers for this theme.
        """
        self.__bg_idx = self.__set_bg_color("111516", curses.COLOR_BLACK)
        self.__apply_bg(self.__bg_idx)

        res = {
            "W_C": self.__init_hex_color(
                11, "BDC3C7", curses.COLOR_WHITE, self.__bg_idx
            ),
            "P_C": self.__init_hex_color(
                12, "F5F5F5", curses.COLOR_WHITE, self.__bg_idx
            ),
            "S_C": self.__init_hex_color(
                13, "7F8C8D", curses.COLOR_CYAN, self.__bg_idx
            ),
            "E_C": self.__init_hex_color(
                14, "5F9EA0", curses.COLOR_BLUE, self.__bg_idx
            ),
            "SOL_C": self.__init_hex_color(
                15, "ADD8E6", curses.COLOR_CYAN, self.__bg_idx
            ),
            "EXP_C": self.__init_hex_color(
                16, "95A5A6", curses.COLOR_CYAN, self.__bg_idx
            ),
            "CC_C": self.__init_hex_color(
                17, "646464", curses.COLOR_BLACK, self.__bg_idx
            ),
            "PL_C": self.__init_hex_color(
                18, "DCDCDC", curses.COLOR_WHITE, self.__bg_idx
            )
        }
        res["M_C"] = res["E_C"] | curses.A_REVERSE
        res["MENU_C"] = self.__init_hex_color(
            20, "BDC3C7", curses.COLOR_YELLOW, self.__bg_idx
        )
        return res
