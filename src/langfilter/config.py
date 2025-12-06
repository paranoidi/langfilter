"""Configuration handling for langfilter."""

from __future__ import annotations

import configparser
from pathlib import Path

from langfilter.parser import AudioTrack, SubtitleTrack


class LangFilterConfig:
    """Configuration settings for langfilter."""

    def __init__(self) -> None:
        self.keep_languages: set[str] = set()
        self.remove_languages: set[str] = set()
        self.keep_subtitle_languages: set[str] = set()
        self.remove_subtitle_languages: set[str] = set()
        self.default_audio_language: str | None = None
        self.default_subtitle_language: str | None = None

    @classmethod
    def load_from_file(cls, config_path: Path) -> LangFilterConfig:
        """Load configuration from INI file."""
        config = cls()

        if not config_path.exists():
            return config

        parser = configparser.ConfigParser()
        parser.read(config_path)

        # Audio section or main section
        if "audio" in parser:
            section_data = parser["audio"]
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

        # Parse default track languages
        if "default_audio" in section_data:
            default_audio = section_data["default_audio"].strip()
            if default_audio:
                config.default_audio_language = default_audio.strip().lower()

        if "default_subtitle" in section_data:
            default_subtitle = section_data["default_subtitle"].strip()
            if default_subtitle:
                config.default_subtitle_language = default_subtitle.strip().lower()

        # Parse subtitle section
        if "subtitles" in parser:
            subtitle_section = parser["subtitles"]

            if "keep" in subtitle_section:
                keep_str = subtitle_section["keep"].strip()
                if keep_str:
                    config.keep_subtitle_languages = {
                        lang.strip().lower() for lang in keep_str.split(",") if lang.strip()
                    }

            if "remove" in subtitle_section:
                remove_str = subtitle_section["remove"].strip()
                if remove_str:
                    config.remove_subtitle_languages = {
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

    def apply_subtitle_defaults(self, tracks: list[SubtitleTrack]) -> set[int]:
        """
        Apply default selection rules to subtitle tracks.

        Returns set of track indices to remove.
        """
        tracks_to_remove = set()

        for i, track in enumerate(tracks):
            track_lang = (track.language or "unknown").lower()

            # If we have explicit keep rules, only keep those languages
            if self.keep_subtitle_languages:
                if track_lang not in self.keep_subtitle_languages:
                    tracks_to_remove.add(i)

            # If we have explicit remove rules, remove those languages
            if self.remove_subtitle_languages:
                if track_lang in self.remove_subtitle_languages:
                    tracks_to_remove.add(i)

        return tracks_to_remove

    def find_default_audio_track(self, tracks: list[AudioTrack]) -> AudioTrack | None:
        """
        Find the first audio track matching the default audio language.

        Returns None if no default language is set or no matching track is found.
        """
        if not self.default_audio_language:
            return None

        for track in tracks:
            track_lang = (track.language or "unknown").lower()
            if track_lang == self.default_audio_language:
                return track

        return None

    def find_default_subtitle_track(self, tracks: list[SubtitleTrack]) -> SubtitleTrack | None:
        """
        Find the first subtitle track matching the default subtitle language.

        Returns None if no default language is set or no matching track is found.
        """
        if not self.default_subtitle_language:
            return None

        for track in tracks:
            track_lang = (track.language or "unknown").lower()
            if track_lang == self.default_subtitle_language:
                return track

        return None

    def has_rules(self) -> bool:
        """Check if any configuration rules are defined."""
        return bool(
            self.keep_languages
            or self.remove_languages
            or self.keep_subtitle_languages
            or self.remove_subtitle_languages
        )

    def __str__(self) -> str:
        """String representation of configuration."""
        parts = []
        if self.keep_languages:
            parts.append(f"audio keep: {', '.join(sorted(self.keep_languages))}")
        if self.remove_languages:
            parts.append(f"audio remove: {', '.join(sorted(self.remove_languages))}")
        if self.keep_subtitle_languages:
            parts.append(f"subtitle keep: {', '.join(sorted(self.keep_subtitle_languages))}")
        if self.remove_subtitle_languages:
            parts.append(f"subtitle remove: {', '.join(sorted(self.remove_subtitle_languages))}")
        if self.default_audio_language:
            parts.append(f"default audio: {self.default_audio_language}")
        if self.default_subtitle_language:
            parts.append(f"default subtitle: {self.default_subtitle_language}")
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
