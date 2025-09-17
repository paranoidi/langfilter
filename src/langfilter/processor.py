"""MKV file processing using mkvmerge."""

from __future__ import annotations

import subprocess
from pathlib import Path

from langfilter.parser import AudioTrack


def remove_unwanted_tracks(
    input_file: Path, tracks_to_keep: list[AudioTrack], output_file: Path | None = None
) -> Path:
    """Remove unwanted audio tracks from MKV file using mkvmerge."""
    if output_file is None:
        # Create output filename with suffix
        stem = input_file.stem
        suffix = input_file.suffix
        output_file = input_file.parent / f"{stem}_filtered{suffix}"

    if not tracks_to_keep:
        raise ValueError("No tracks selected to keep")

    # Build mkvmerge command
    cmd = ["mkvmerge", "-o", str(output_file)]

    # Add audio track selection
    # We need to keep track 0 (video) and selected audio tracks
    audio_track_ids = [str(track.mkvmerge_id) for track in tracks_to_keep]

    # Include video track (track 0) and selected audio tracks
    tracks_arg = "0," + ",".join(audio_track_ids)
    cmd.extend(["--audio-tracks", tracks_arg])

    # Copy all subtitle tracks (if any)
    cmd.extend(["--subtitle-tracks", "all"])

    # Input file
    cmd.append(str(input_file))

    print(f"Running: {' '.join(cmd)}")
    print("This may take a while...")

    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)

        print("✔ Successfully created filtered MKV file")
        print(f"Output: {output_file}")
        return output_file

    except subprocess.CalledProcessError as e:
        # Clean up failed output file
        if output_file.exists():
            output_file.unlink()

        error_msg = f"mkvmerge failed (exit code {e.returncode})"
        if e.stderr:
            error_msg += f": {e.stderr}"
        raise RuntimeError(error_msg) from e

    except FileNotFoundError as e:
        raise RuntimeError("mkvmerge command not found. Please install mkvtoolnix.") from e


def create_backup(input_file: Path) -> Path:
    """Create a backup of the original file."""
    backup_file = input_file.parent / f"_original_{input_file.name}"

    # If backup already exists, add a number
    counter = 1
    while backup_file.exists():
        backup_file = input_file.parent / f"_original_{counter}_{input_file.name}"
        counter += 1

    # Use hardlink if possible (faster), otherwise copy
    try:
        backup_file.hardlink_to(input_file)
    except OSError:
        import shutil

        shutil.copy2(input_file, backup_file)

    return backup_file


def replace_original(
    input_file: Path, filtered_file: Path, create_backup_file: bool = True
) -> None:
    """Replace the original file with the filtered version."""
    if create_backup_file:
        backup_file = create_backup(input_file)
        print(f"✔ Created backup: {backup_file}")

    # Replace original with filtered version
    filtered_file.replace(input_file)
    print(f"✔ Replaced original file: {input_file}")
