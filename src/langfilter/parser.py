"""Parser for mkvinfo output to extract track information."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class AudioTrack:
    """Represents an audio track in an MKV file."""

    track_number: int
    mkvmerge_id: int
    language: str | None
    name: str | None
    codec: str | None
    channels: int | None

    def __str__(self) -> str:
        """String representation for display."""
        lang_str = f"[{self.language}]" if self.language else "[unknown]"
        name_str = f" - {self.name}" if self.name else ""
        channels_str = f" ({self.channels}ch)" if self.channels else ""
        return f"Track {self.track_number} {lang_str}{name_str}{channels_str}"


def parse_mkvinfo_output(output: str) -> list[AudioTrack]:
    """Parse mkvinfo output and extract audio track information."""
    tracks = []
    current_track = None
    in_audio_track = False

    for line in output.split("\n"):
        line = line.strip()

        # Start of a new track
        if match := re.match(
            r".*\+ Track number: (\d+) \(track ID for mkvmerge & mkvextract: (\d+)\)", line
        ):
            if current_track and in_audio_track:
                tracks.append(current_track)

            track_number = int(match.group(1))
            mkvmerge_id = int(match.group(2))
            current_track = AudioTrack(
                track_number=track_number,
                mkvmerge_id=mkvmerge_id,
                language=None,
                name=None,
                codec=None,
                channels=None,
            )
            in_audio_track = False

        # Track type
        elif re.search(r"\+ Track type: audio", line) and current_track:
            in_audio_track = True

        elif re.search(r"\+ Track type:", line) and not re.search(r"\+ Track type: audio", line):
            in_audio_track = False

        # Track properties (only if we're in an audio track)
        elif in_audio_track and current_track:
            if match := re.search(r"\+ Language: (.+)", line):
                current_track.language = match.group(1)

            elif match := re.search(r"\+ Name: (.+)", line):
                current_track.name = match.group(1)

            elif match := re.search(r"\+ Codec ID: (.+)", line):
                current_track.codec = match.group(1)

            elif match := re.search(r"\+ Channels: (\d+)", line):
                current_track.channels = int(match.group(1))

    # Don't forget the last track
    if current_track and in_audio_track:
        tracks.append(current_track)

    return tracks


def get_audio_tracks(mkv_file: Path) -> list[AudioTrack]:
    """Get all audio tracks from an MKV file using mkvinfo."""
    try:
        result = subprocess.run(
            ["mkvinfo", str(mkv_file)], capture_output=True, text=True, check=True
        )
        return parse_mkvinfo_output(result.stdout)

    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"mkvinfo failed: {e.stderr}") from e

    except FileNotFoundError as e:
        raise RuntimeError("mkvinfo command not found. Please install mkvtoolnix.") from e
