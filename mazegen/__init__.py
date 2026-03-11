"""
mazegen package - maze generation, solving, rendering, and error handling.
"""

from .errors import report_error
from .gen_maze import MazeGenerator
from .visualization import SplashScreen


def clean() -> None:
    """Reset the terminal colour palette to its default state.

    Sends an OSC 104 escape sequence that instructs the terminal emulator to
    restore all custom colours, undoing any palette changes made by the themes.
    """
    print("\033]104\007", end="")


__all__ = ["report_error", "MazeGenerator", "SplashScreen", "clean"]
