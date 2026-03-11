import os
import pygame
from typing import Optional, Dict


class AudioManager:
    """Manages loading and playback of game sound effects via pygame.

    Wraps pygame.mixer with graceful fallback behaviour when the audio
    subsystem is unavailable (e.g. in headless CI environments).
    """

    def __init__(self, assets_dir: str = "sounds") -> None:
        """Initialise the audio manager and attempt to start the mixer.

        Args:
            assets_dir: Directory that contains the .wav sound files.
                Defaults to "sounds".
        """
        self.__assets_dir: str = assets_dir
        self.__sounds: Dict[str, pygame.mixer.Sound] = {}
        self.__is_initialized: bool = False
        self.__init_mixer()

    def __init_mixer(self) -> None:
        """Attempt to initialise pygame.mixer.

        Sets __is_initialized to True on success, False on failure.
        Failure is silent so
        the rest of the application continues without audio.
        """
        try:
            pygame.mixer.init()
            self.__is_initialized = True
        except Exception:
            self.__is_initialized = False

    def load_sound(self, name: str, filename: str) -> None:
        """Load a sound file and store it under a logical name.

        Does nothing if the mixer failed to initialise
        or the file does not exist.

        Args:
            name: Logical key used to reference the sound later.
            filename: Filename (not full path) of the .wav file inside
                assets_dir.
        """
        if not self.__is_initialized:
            return

        file_path: str = os.path.join(self.__assets_dir, filename)
        if os.path.exists(file_path):
            try:
                self.__sounds[name] = pygame.mixer.Sound(file_path)
            except pygame.error:
                pass

    def play_sound(self, name: str, loops: int = 0) -> None:
        """Play a previously loaded sound.

        Does nothing if the mixer is not initialised or the sound has not been
        loaded.

        Args:
            name: Logical key of the sound to play.
            loops: Number of *additional* times to repeat playback after the
                first play. Use -1 for infinite looping.
        """
        if not self.__is_initialized:
            return

        sound: Optional[pygame.mixer.Sound] = self.__sounds.get(name, None)
        if sound is not None:
            sound.play(loops=loops)

    def stop_all(self) -> None:
        """Stop all currently playing sounds immediately."""
        if self.__is_initialized:
            pygame.mixer.stop()

    def quit(self) -> None:
        """Shut down the pygame mixer and mark it as uninitialised."""
        if self.__is_initialized:
            pygame.mixer.quit()
            self.__is_initialized = False
