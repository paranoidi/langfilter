"""Configuration handling for langfilter."""

from __future__ import annotations

import configparser
from pathlib import Path

from langfilter.parser import AudioTrack


class LangFilterConfig:
    """Configuration settings for langfilter."""

    def __init__(self) -> None:
        self.keep_languages: set[str] = set()
        self.remove_languages: set[str] = set()

    @classmethod
    def load_from_file(cls, config_path: Path) -> LangFilterConfig:
        """Load configuration from INI file."""
        config = cls()

        if not config_path.exists():
            return config

        parser = configparser.ConfigParser()
        parser.read(config_path)

        # Default section or main section
        if "DEFAULT" in parser:
            section_data = parser["DEFAULT"]
        elif len(parser.sections()) > 0:
            section_data = parser[parser.sections()[0]]
        else:
            section_data = {}

        # Parse keep languages
        if "keep" in section_data:
            keep_str = section_data["keep"].strip()
            if keep_str:
                config.keep_languages = {
                    lang.strip().lower() for lang in keep_str.split(",") if lang.strip()
                }

        # Parse remove languages
        if "remove" in section_data:
            remove_str = section_data["remove"].strip()
            if remove_str:
                config.remove_languages = {
                    lang.strip().lower() for lang in remove_str.split(",") if lang.strip()
                }

        return config

    def apply_defaults(self, tracks: list[AudioTrack]) -> set[int]:
        """
        Apply default selection rules to tracks.

        Returns set of track indices to remove.
        """
        tracks_to_remove = set()

        for i, track in enumerate(tracks):
            track_lang = (track.language or "unknown").lower()

            # If we have explicit keep rules, only keep those languages
            if self.keep_languages:
                if track_lang not in self.keep_languages:
                    tracks_to_remove.add(i)

            # If we have explicit remove rules, remove those languages
            if self.remove_languages:
                if track_lang in self.remove_languages:
                    tracks_to_remove.add(i)

        return tracks_to_remove

    def has_rules(self) -> bool:
        """Check if any configuration rules are defined."""
        return bool(self.keep_languages or self.remove_languages)

    def __str__(self) -> str:
        """String representation of configuration."""
        parts = []
        if self.keep_languages:
            parts.append(f"keep: {', '.join(sorted(self.keep_languages))}")
        if self.remove_languages:
            parts.append(f"remove: {', '.join(sorted(self.remove_languages))}")
        return "; ".join(parts) if parts else "no rules"


def find_config_file() -> Path | None:
    """
    Find configuration file in standard locations.

    Priority order:
    1. Standard Linux config location
    2. Current directory configs
    3. Legacy home directory config
    """
    possible_paths = [
        # Standard Linux config location (highest priority)
        Path.home() / ".config" / "langfilter" / "config.ini",
        # Current directory configs
        Path.cwd() / "langfilter.ini",
        Path.cwd() / ".langfilter.ini",
        # Legacy home directory config (lowest priority)
        Path.home() / ".langfilter.ini",
    ]

    for path in possible_paths:
        if path.exists():
            return path

    return None
