import os
import time
from .themes import Themes
from typing import Tuple, Dict, Any, List
from .errors import (ConfigSyntaxError, ConfigKeyError, ConfigValueError)
from pydantic import (
    BaseModel, ValidationError, field_validator, model_validator
)


class MazeConfig(BaseModel):
    """Pydantic model that validates and coerces raw configuration values.

    All fields are populated from the key-value pairs parsed out of the
    configuration file.  Validators normalise strings to the expected Python
    types before the :meth:validate_logic cross-field check runs.

    Attributes:
        WIDTH: Number of columns in the maze (must be > 0).
        HEIGHT: Number of rows in the maze (must be > 0).
        ENTRY: (col, row) coordinates of the maze entry cell.
        EXIT: (col, row) coordinates of the maze exit cell.
        OUTPUT_FILE: Filesystem path where the maze output will be written.
        PERFECT: True to generate a perfect maze, False to allow loops.
        SEED: Integer seed for the random-number generator.
        ALGORITHM: Generation algorithm identifier ('DFS' or 'WILSON').
        HAS_SEED: True when a SEED was explicitly provided in the file.
    """

    WIDTH: int
    HEIGHT: int
    ENTRY: Tuple[int, int]
    EXIT: Tuple[int, int]
    OUTPUT_FILE: str
    PERFECT: bool
    SEED: int
    ALGORITHM: str
    HAS_SEED: bool

    @field_validator("WIDTH", "HEIGHT", mode="before")
    @staticmethod
    def validate_dimensions(value: Any) -> int:
        """Coerce and validate a dimension value to a positive integer.

        Args:
            value: Raw value from the config parser.

        Returns:
            A strictly positive integer.

        Raises:
            ValueError: If value cannot be parsed as an integer or is ≤ 0.
        """
        try:
            val = int(value)
        except ValueError:
            raise ValueError("Dimensions must be valid integers.")
        if val <= 0:
            raise ValueError("Dimensions cannot be negative or zero.")
        return val

    @field_validator("ENTRY", "EXIT", mode="before")
    @staticmethod
    def parse_coordinates(value: Any) -> Tuple[int, int]:
        """Parse a 'x,y' string (or 2-tuple) into a coordinate pair.

        Args:
            value: Either a (int, int) tuple or a 'x,y' string.

        Returns:
            A (col, row) tuple of non-negative integers.

        Raises:
            ValueError: If the format is wrong or coordinates are negative.
        """
        if isinstance(value, tuple) and len(value) == 2:
            return (int(value[0]), int(value[1]))

        val_str = str(value)
        if val_str.count(',') != 1:
            raise ValueError("Expected format: x,y")

        try:
            x, y = map(int, val_str.split(','))
        except ValueError:
            raise ValueError("Coordinates must be integers.")

        if x < 0 or y < 0:
            raise ValueError("Coordinates cannot be negative.")

        return (x, y)

    @field_validator("PERFECT", mode="before")
    @staticmethod
    def parse_perfect(value: Any) -> bool:
        """Parse a 'True'/'False' string (or bool) into a bool.

        Args:
            value: Raw perfectness flag from the config parser.

        Returns:
            True if the value represents a perfect maze, False
            otherwise.

        Raises:
            ValueError: If the string is not 'True' or 'False'.
        """
        if isinstance(value, bool):
            return value

        val_str = str(value).strip().capitalize()
        if val_str not in ("True", "False"):
            raise ValueError("PERFECT expected 'True' or 'False'.")

        return val_str == "True"

    @field_validator("SEED", mode="before")
    @staticmethod
    def parse_seed(value: Any) -> int:
        """Parse a seed value into an integer.

        Digit-only strings are converted directly; arbitrary strings are
        converted via their UTF-8 byte representation using big-endian
        int.from_bytes.

        Args:
            value: Raw seed from the config parser.

        Returns:
            An integer seed suitable for :func:random.seed.
        """
        if isinstance(value, int):
            return value

        val_str = str(value)
        if val_str.isdigit():
            return int(val_str)

        return int.from_bytes(bytes(val_str, 'utf-8'), byteorder='big')

    @field_validator("ALGORITHM", mode="before")
    @staticmethod
    def parse_algorithm(value: Any) -> str:
        """Validate and normalise the algorithm name.

        Args:
            value: Raw algorithm string from the config parser.

        Returns:
            'DFS' or 'WILSON' in upper-case.

        Raises:
            ValueError: If the value is not one of the supported algorithms.
        """
        val = str(value).upper()
        if val not in ("DFS", "WILSON"):
            raise ValueError("Algorithm not found")
        return val

    @field_validator("OUTPUT_FILE", mode="before")
    @staticmethod
    def parse_path(value: Any) -> str:
        """Validate that the output path is writable and not a directory.

        Args:
            value: Raw output file path string.

        Returns:
            The validated path string.

        Raises:
            OSError: If value points to an existing directory.
            PermissionError: If the path is not writable.
        """
        val = str(value)
        if not os.path.exists(val):
            return val

        if not os.path.isfile(val):
            raise OSError(f"Not a file: {val} is not a valid file")

        if not os.access(val, os.W_OK):
            raise PermissionError(
                f"Permission denied: can't write to this file {val}"
            )

        return val

    @model_validator(mode="after")
    def validate_logic(self) -> 'MazeConfig':
        """Cross-field validation: ensure the maze geometry is coherent.

        Checks that the maze area is at least 2 cells, that ENTRY and EXIT
        are within bounds, and that they are distinct.

        Returns:
            The validated :class:MazeConfig instance.

        Raises:
            ValueError: If any geometric constraint is violated.
        """
        if self.WIDTH * self.HEIGHT < 2:
            raise ValueError("Maze area is too small.")
        if self.ENTRY[0] >= self.WIDTH or self.ENTRY[1] >= self.HEIGHT:
            raise ValueError("ENTRY is outside maze boundaries.")
        if self.EXIT[0] >= self.WIDTH or self.EXIT[1] >= self.HEIGHT:
            raise ValueError("EXIT is outside maze boundaries.")
        if self.ENTRY == self.EXIT:
            raise ValueError("The ENTRY and EXIT must be different.")

        return self


class Maze:
    """Immutable runtime representation of a maze's configuration.

    Parses and validates the configuration file on construction and exposes
    the resulting settings as read-only properties.  seed and algo
    are settable so the generator can switch algorithm mid-session.

    The :class:Themes instance is also owned here and shared with the
    renderer.
    """

    def __init__(self, config_file: str, stdscr: Any) -> None:
        """Parse config_file and build the maze configuration.

        Args:
            config_file: Path to the plain-text configuration file.
            stdscr: The root curses window, forwarded to :class:Themes.
        """
        config = self.MazeParseConfig.parsing_conf(config_file)
        self.__width: int = config["WIDTH"]
        self.__height: int = config["HEIGHT"]
        self.__entry: Tuple[int, int] = config["ENTRY"]
        self.__exit: Tuple[int, int] = config["EXIT"]
        self.__output_file: str = config["OUTPUT_FILE"]
        self.__perfection: bool = config["PERFECT"]
        self.__seed: int = config["SEED"]
        self.__has_seed: bool = config["HAS_SEED"]
        self.__algo: str = config["ALGORITHM"]
        self.__themes: Themes = Themes(stdscr)

    @property
    def width(self) -> int:
        """Number of columns in the maze grid."""
        return self.__width

    @property
    def height(self) -> int:
        """Number of rows in the maze grid."""
        return self.__height

    @property
    def entry(self) -> Tuple[int, int]:
        """(col, row) coordinates of the maze entry cell."""
        return self.__entry

    @property
    def exit(self) -> Tuple[int, int]:
        """(col, row) coordinates of the maze exit cell."""
        return self.__exit

    @property
    def output_file(self) -> str:
        """Filesystem path where the maze output file is written."""
        return self.__output_file

    @property
    def perfection(self) -> bool:
        """True if the maze is perfect (no loops), False otherwise."""
        return self.__perfection

    @property
    def seed(self) -> int:
        """Integer seed used to initialise the random-number generator."""
        return self.__seed

    @seed.setter
    def seed(self, value: int) -> None:
        """Set a new seed value.

        Args:
            value: A non-negative integer seed.  Ignored if negative or
                not an integer.
        """
        if isinstance(value, int) and value >= 0:
            self.__seed = value

    @property
    def has_seed(self) -> bool:
        """True if a seed was explicitly provided in the config file."""
        return self.__has_seed

    @property
    def algo(self) -> str:
        """Active generation algorithm identifier ('DFS' or 'WILSON')."""
        return self.__algo

    @algo.setter
    def algo(self, value: str) -> None:
        """Set the active generation algorithm.

        Args:
            value: Algorithm name; must be 'DFS' or 'WILSON'
                (case-insensitive).

        Raises:
            ValueError: If value is not a recognised algorithm name.
        """
        if value.upper() not in ("DFS", "WILSON"):
            raise ValueError(f"Unknown algorithm: '{value.upper()}'")
        self.__algo = value.upper()

    @property
    def themes(self) -> Themes:
        """The :class:~mazegen.themes.Themes instance for this maze."""
        return self.__themes

    class MazeParseConfig:
        """Parses the plain-text configuration file into a validated dict."""

        @staticmethod
        def parsing_conf(file_path: str) -> Dict[str, Any]:
            """Read, parse, and validate a maze configuration file.

            The file format is KEY = VALUE (one per line).  Lines that are
            empty or start with '#' are ignored.  Missing required keys,
            unknown keys, syntax errors, and value errors all raise descriptive
            exceptions.

            Args:
                file_path: Path to the configuration file to parse.

            Returns:
                A fully validated dictionary with the following keys:
                WIDTH, HEIGHT, ENTRY, EXIT, OUTPUT_FILE,
                PERFECT, SEED, ALGORITHM, HAS_SEED.

            Raises:
                FileNotFoundError: If file_path does not exist.
                PermissionError: If the file cannot be read.
                IsADirectoryError: If file_path is a directory.
                ConfigSyntaxError: If a line does not contain exactly one =.
                ConfigKeyError: If an unknown key is encountered or required
                    keys are missing.
                ConfigValueError: If a key has an empty or invalid value.
            """
            req_keys: List[str] = list(ConfigKeyError.get_required_keys())
            add_keys: List[str] = list(ConfigKeyError.get_additional_keys())
            config: Dict[str, Any] = {}

            try:
                with open(file_path, "r") as file:
                    for i, line in enumerate(file, 1):
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue

                        if line.count('=') != 1:
                            raise ConfigSyntaxError(
                                f"Syntax Error at line {i}: '{line}' "
                                f"in config file: Expected exactly one '=' "
                                f"operator (found {line.count('=')})"
                            )

                        key, value = map(str.strip, line.split('='))
                        key = key.upper()

                        if not value:
                            raise ConfigValueError(
                                f"Empty key '{key}' value at "
                                f"line {i}: '{line}' in config file."
                            )

                        if key not in req_keys and key not in add_keys:
                            raise ConfigKeyError(
                                f"Unknown key '{key}' at "
                                f"line {i}: '{line}' in config file."
                            )

                        config[key] = value

                        if key in req_keys:
                            req_keys.remove(key)
                        elif key in add_keys:
                            add_keys.remove(key)

                if req_keys:
                    raise ConfigKeyError(
                        f"Missing mandatory keys in config file: "
                        f"{', '.join(req_keys)}"
                    )

                has_seed_flag: bool = "SEED" in config

                if not has_seed_flag:
                    config["SEED"] = int(time.time())

                if "ALGORITHM" not in config:
                    config["ALGORITHM"] = "DFS"

                config["HAS_SEED"] = has_seed_flag

                validated = MazeConfig(**config)

                return {
                    "WIDTH": validated.WIDTH,
                    "HEIGHT": validated.HEIGHT,
                    "ENTRY": validated.ENTRY,
                    "EXIT": validated.EXIT,
                    "OUTPUT_FILE": validated.OUTPUT_FILE,
                    "PERFECT": validated.PERFECT,
                    "SEED": validated.SEED,
                    "ALGORITHM": validated.ALGORITHM,
                    "HAS_SEED": validated.HAS_SEED
                }

            except FileNotFoundError:
                raise FileNotFoundError(
                    f"The configuration file '{file_path}' "
                    "was not found. Ensure the path is correct."
                )
            except PermissionError:
                raise PermissionError(
                    f"Access denied to '{file_path}'. "
                    "Check read permissions."
                )
            except IsADirectoryError:
                raise IsADirectoryError(
                    f"'{file_path}' is a directory. "
                    "A valid configuration file path is required."
                )
            except ValidationError as e:
                raise ConfigValueError(
                    "Validation Error:\n"
                    f"{'\n'.join(
                        [error.get('msg', "") for error in e.errors()])}"
                )
