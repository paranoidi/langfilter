#!/usr/bin/env python3
"""Main entry point for langfilter command-line tool."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from langfilter.config import LangFilterConfig, find_config_file
from langfilter.interactive import (
    RESET,
    YELLOW,
    UserCancelledError,
    select_subtitle_tracks_non_interactive,
    select_subtitle_tracks_to_keep,
    select_tracks_non_interactive,
    select_tracks_to_keep,
)
from langfilter.parser import AudioTrack, SubtitleTrack, get_audio_tracks, get_subtitle_tracks
from langfilter.processor import remove_unwanted_tracks, replace_original


class TrackSelectionResult(Enum):
    """Outcome of track selection for a file."""

    SUCCESS = "success"  # Tracks selected successfully
    SKIPPED_NO_TRACKS = "no_tracks"  # File has no audio tracks
    SKIPPED_NO_SELECTION = "no_selection"  # User/config selected no tracks
    SKIPPED_ALL_SELECTED = "all_selected"  # All tracks selected (no filtering needed)
    FAILED = "failed"  # Error occurred during analysis


@dataclass
class FileAnalysisResult:
    """Result of analyzing a file for track selection."""

    status: TrackSelectionResult
    all_tracks: list[AudioTrack] | None = None
    selected_tracks: list[AudioTrack] | None = None
    all_subtitle_tracks: list[SubtitleTrack] | None = None
    selected_subtitle_tracks: list[SubtitleTrack] | None = None
    default_audio_track: AudioTrack | None = None
    default_subtitle_track: SubtitleTrack | None = None
    error_message: str | None = None

    @property
    def should_process(self) -> bool:
        """Whether this file should be processed (has tracks to filter)."""
        has_audio_to_process = (
            self.status == TrackSelectionResult.SUCCESS and self.selected_tracks is not None
        )
        has_subtitle_to_process = (
            self.selected_subtitle_tracks is not None and len(self.selected_subtitle_tracks) > 0
        )
        return has_audio_to_process or has_subtitle_to_process

    @property
    def needs_filtering(self) -> bool:
        """Whether this file needs filtering (not all tracks selected)."""
        audio_needs_filtering = (
            self.should_process
            and self.all_tracks is not None
            and self.selected_tracks is not None
            and len(self.selected_tracks) < len(self.all_tracks)
        )
        subtitle_needs_filtering = (
            self.all_subtitle_tracks is not None
            and self.selected_subtitle_tracks is not None
            and len(self.selected_subtitle_tracks) < len(self.all_subtitle_tracks)
        )
        return audio_needs_filtering or subtitle_needs_filtering


def analyze_and_select_tracks(
    filename: Path, config: LangFilterConfig | None, non_interactive: bool = False
) -> FileAnalysisResult:
    """
    Analyze an MKV file and determine which tracks to keep.

    This function combines track discovery with track selection logic.
    """
    print(f"\nAnalyzing MKV file: {filename}")
    print("Running mkvinfo to extract track information...")

    try:
        # Get all audio tracks
        audio_tracks = get_audio_tracks(filename)
        # Get all subtitle tracks
        subtitle_tracks = get_subtitle_tracks(filename)

        if not audio_tracks and not subtitle_tracks:
            print("No audio or subtitle tracks found in the file.")
            return FileAnalysisResult(
                status=TrackSelectionResult.SKIPPED_NO_TRACKS,
                all_tracks=None,
                selected_tracks=None,
                all_subtitle_tracks=None,
                selected_subtitle_tracks=None,
            )

        # Audio track selection (interactive or non-interactive)
        selected_audio_tracks: list[AudioTrack] = []
        default_audio_track: AudioTrack | None = None
        default_audio_index: int | None = None

        if audio_tracks:
            if non_interactive:
                if config is None or not config.has_rules():
                    print(f"{YELLOW}Non-interactive mode requires configuration rules.{RESET}")
                    print("No tracks will be removed. File will be skipped.")
                    return FileAnalysisResult(
                        status=TrackSelectionResult.SKIPPED_NO_SELECTION,
                        all_tracks=audio_tracks,
                        selected_tracks=None,
                        all_subtitle_tracks=subtitle_tracks,
                        selected_subtitle_tracks=None,
                    )
                selected_audio_tracks = select_tracks_non_interactive(audio_tracks, config)
                # Find default audio track from config
                if config:
                    default_audio_track = config.find_default_audio_track(selected_audio_tracks)
                    if default_audio_track:
                        default_audio_index = next(
                            (
                                i
                                for i, track in enumerate(selected_audio_tracks)
                                if track.mkvmerge_id == default_audio_track.mkvmerge_id
                            ),
                            None,
                        )
            else:
                selected_audio_tracks, default_audio_index = select_tracks_to_keep(
                    audio_tracks, config
                )
                if default_audio_index is not None and default_audio_index < len(audio_tracks):
                    # Find the default track in selected tracks by matching mkvmerge_id
                    original_default_track = audio_tracks[default_audio_index]
                    default_audio_track = next(
                        (
                            track
                            for track in selected_audio_tracks
                            if track.mkvmerge_id == original_default_track.mkvmerge_id
                        ),
                        None,
                    )

            if not selected_audio_tracks:
                print("No audio tracks selected. File will be skipped.")
                return FileAnalysisResult(
                    status=TrackSelectionResult.SKIPPED_NO_SELECTION,
                    all_tracks=audio_tracks,
                    selected_tracks=None,
                    all_subtitle_tracks=subtitle_tracks,
                    selected_subtitle_tracks=None,
                )

        # Subtitle track selection (interactive or non-interactive)
        selected_subtitle_tracks: list[SubtitleTrack] = []
        default_subtitle_track: SubtitleTrack | None = None
        default_subtitle_index: int | None = None

        if subtitle_tracks:
            if non_interactive:
                if config is None or not config.has_rules():
                    print(f"{YELLOW}Non-interactive mode requires configuration rules.{RESET}")
                    print("No subtitle tracks will be removed. All subtitle tracks will be kept.")
                    selected_subtitle_tracks = subtitle_tracks
                else:
                    selected_subtitle_tracks = select_subtitle_tracks_non_interactive(
                        subtitle_tracks, config
                    )
                # Find default subtitle track from config
                if config:
                    default_subtitle_track = config.find_default_subtitle_track(
                        selected_subtitle_tracks
                    )
                    if default_subtitle_track:
                        default_subtitle_index = next(
                            (
                                i
                                for i, track in enumerate(selected_subtitle_tracks)
                                if track.mkvmerge_id == default_subtitle_track.mkvmerge_id
                            ),
                            None,
                        )
            else:
                selected_subtitle_tracks, default_subtitle_index = select_subtitle_tracks_to_keep(
                    subtitle_tracks, config
                )
                if default_subtitle_index is not None and default_subtitle_index < len(
                    subtitle_tracks
                ):
                    # Find the default track in selected tracks by matching mkvmerge_id
                    original_default_track = subtitle_tracks[default_subtitle_index]
                    default_subtitle_track = next(
                        (
                            track
                            for track in selected_subtitle_tracks
                            if track.mkvmerge_id == original_default_track.mkvmerge_id
                        ),
                        None,
                    )

        # Check if all tracks are selected (no filtering needed)
        audio_all_selected = not audio_tracks or len(selected_audio_tracks) == len(audio_tracks)
        subtitle_all_selected = not subtitle_tracks or len(selected_subtitle_tracks) == len(
            subtitle_tracks
        )

        if audio_all_selected and subtitle_all_selected:
            print("All tracks selected. No filtering needed for this file.")
            return FileAnalysisResult(
                status=TrackSelectionResult.SKIPPED_ALL_SELECTED,
                all_tracks=audio_tracks,
                selected_tracks=selected_audio_tracks,
                all_subtitle_tracks=subtitle_tracks,
                selected_subtitle_tracks=selected_subtitle_tracks,
                default_audio_track=default_audio_track,
                default_subtitle_track=default_subtitle_track,
            )

        audio_summary = ""
        if audio_tracks:
            audio_summary = f"{len(selected_audio_tracks)} audio track(s) to keep, {len(audio_tracks) - len(selected_audio_tracks)} to remove"
        subtitle_summary = ""
        if subtitle_tracks:
            subtitle_summary = f"{len(selected_subtitle_tracks)} subtitle track(s) to keep, {len(subtitle_tracks) - len(selected_subtitle_tracks)} to remove"

        summary_parts = [p for p in [audio_summary, subtitle_summary] if p]
        print(f"Selection complete: {'; '.join(summary_parts)}")

        return FileAnalysisResult(
            status=TrackSelectionResult.SUCCESS,
            all_tracks=audio_tracks,
            selected_tracks=selected_audio_tracks,
            all_subtitle_tracks=subtitle_tracks,
            selected_subtitle_tracks=selected_subtitle_tracks,
            default_audio_track=default_audio_track,
            default_subtitle_track=default_subtitle_track,
        )

    except UserCancelledError:
        raise
    except Exception as e:
        error_msg = f"Error analyzing {filename}: {e}"
        print(error_msg, file=sys.stderr)
        return FileAnalysisResult(status=TrackSelectionResult.FAILED, error_message=error_msg)


def process_file_with_selection(
    filename: Path,
    selected_tracks: list[AudioTrack],
    output_path: Path | None,
    replace_original_file: bool,
    create_backup: bool,
    selected_subtitle_tracks: list[SubtitleTrack] | None = None,
    default_audio_track: AudioTrack | None = None,
    default_subtitle_track: SubtitleTrack | None = None,
) -> bool:
    """
    Process a file with predetermined track selection.

    Returns success status.
    """
    print(f"\nProcessing: {filename}")

    try:
        # Determine default track IDs
        default_audio_track_id = default_audio_track.mkvmerge_id if default_audio_track else None
        default_subtitle_track_id = (
            default_subtitle_track.mkvmerge_id if default_subtitle_track else None
        )

        # Process the file
        filtered_file = remove_unwanted_tracks(
            filename,
            selected_tracks,
            output_path,
            selected_subtitle_tracks,
            default_audio_track_id,
            default_subtitle_track_id,
        )

        # Replace original if requested
        if replace_original_file:
            replace_original(filename, filtered_file, create_backup_file=create_backup)

        print("✔ File processed successfully!")
        return True

    except Exception as e:
        print(f"✗ Error processing {filename}: {e}", file=sys.stderr)
        return False


def main() -> int:
    """Main entry point for langfilter."""
    parser = argparse.ArgumentParser(
        prog="langfilter",
        description="Remove unwanted languages from MKV files",
    )

    parser.add_argument(
        "filenames",
        nargs="+",
        type=Path,
        help="Path(s) to the MKV file(s) to process",
    )

    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output file path (only valid with single input file)",
    )

    parser.add_argument(
        "--non-interactive",
        "-n",
        action="store_true",
        help="Non-interactive mode: only apply config rules, no user interaction",
    )

    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Don't create backup when replacing original file (default: create backup)",
    )

    parser.add_argument(
        "--config",
        "-c",
        type=Path,
        help="Path to configuration file (default: auto-detect)",
    )

    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )

    args = parser.parse_args()

    # Validate arguments
    if args.output and len(args.filenames) > 1:
        print("Error: --output can only be used with a single input file.", file=sys.stderr)
        return 1

    # Validate that all files exist
    valid_files = []
    for filename in args.filenames:
        if not filename.exists():
            print(f"Error: File '{filename}' does not exist.", file=sys.stderr)
            continue

        if not filename.is_file():
            print(f"Error: '{filename}' is not a file.", file=sys.stderr)
            continue

        # Check if it's an MKV file
        if filename.suffix.lower() != ".mkv":
            print(f"Warning: '{filename}' does not have .mkv extension.", file=sys.stderr)

        valid_files.append(filename)

    if not valid_files:
        print("Error: No valid files to process.", file=sys.stderr)
        return 1

    try:
        # Load configuration
        config = None
        config_path = None

        if args.config:
            # Explicit config file specified
            config_path = args.config
            if not config_path.exists():
                print(
                    f"Error: Specified config file '{config_path}' does not exist.", file=sys.stderr
                )
                return 1
        else:
            # Auto-detect config file
            config_path = find_config_file()

        if config_path:
            try:
                config = LangFilterConfig.load_from_file(config_path)
                if config.has_rules():
                    if args.config:
                        print(f"Loaded configuration from: {config_path}")
                    else:
                        print(f"Found and loaded configuration from: {config_path}")
                        # Check if it's the standard Linux location
                        standard_location = Path.home() / ".config" / "langfilter" / "config.ini"
                        if config_path == standard_location:
                            print("Using standard Linux configuration directory.")
            except Exception as e:
                print(f"Warning: Failed to load config from {config_path}: {e}", file=sys.stderr)

        # Validate non-interactive mode requirements
        if args.non_interactive:
            if config is None or not config.has_rules():
                print(
                    "Error: Non-interactive mode requires a configuration file with rules.",
                    file=sys.stderr,
                )
                print(
                    "Please create a config file with 'keep' or 'remove' rules, or run without --non-interactive.",
                    file=sys.stderr,
                )
                return 1
            print(f"Running in non-interactive mode with rules: {config}")

        # Phase 1: Analyze all files and collect selections
        file_selections = []
        analysis_failed = []

        print(f"\n{'=' * 60}")
        print(f"PHASE 1: Analyzing {len(valid_files)} file(s) and collecting track selections")
        print(f"{'=' * 60}")

        for i, filename in enumerate(valid_files):
            print(f"\n--- File {i + 1}/{len(valid_files)}: {filename.name} ---")

            try:
                result = analyze_and_select_tracks(filename, config, args.non_interactive)
            except UserCancelledError:
                print("Operation cancelled by user.")
                return 0

            if result.should_process:
                file_selections.append(
                    (
                        filename,
                        result.selected_tracks or [],
                        result.selected_subtitle_tracks,
                        result.default_audio_track,
                        result.default_subtitle_track,
                    )
                )
                print(f"✓ Selection recorded for {filename.name}")
            elif result.status == TrackSelectionResult.FAILED:
                analysis_failed.append(filename)
                print(f"✗ Failed to analyze {filename.name}")
            else:
                # File was skipped for valid reasons
                print(f"⚠ Skipping {filename.name} ({result.status.value})")

        if not file_selections:
            print(f"\n{'=' * 60}")
            print("No files to process (no valid selections made)")
            return 0 if not analysis_failed else 1

        # Phase 2: Process all files with their selections
        print(f"\n{'=' * 60}")
        print(f"PHASE 2: Processing {len(file_selections)} file(s) with selected tracks")
        print(f"{'=' * 60}")

        success_count = 0
        processing_failed = []

        for i, (
            filename,
            selected_tracks,
            selected_subtitle_tracks,
            default_audio_track,
            default_subtitle_track,
        ) in enumerate(file_selections):
            print(f"\n--- Processing {i + 1}/{len(file_selections)}: {filename.name} ---")
            track_summary_parts = []
            if selected_tracks:
                track_summary_parts.append(f"{len(selected_tracks)} audio track(s)")
            if selected_subtitle_tracks:
                track_summary_parts.append(f"{len(selected_subtitle_tracks)} subtitle track(s)")
            print(f"Keeping {', '.join(track_summary_parts)}...")

            success = process_file_with_selection(
                filename,
                selected_tracks,
                args.output if len(valid_files) == 1 else None,
                True,  # Always replace original file (new default behavior)
                not args.no_backup,
                selected_subtitle_tracks,
                default_audio_track,
                default_subtitle_track,
            )

            if success:
                success_count += 1
            else:
                processing_failed.append(filename)

        # Final summary
        print(f"\n{'=' * 60}")
        print("PROCESSING COMPLETE")
        print(f"{'=' * 60}")
        print(f"Files analyzed: {len(valid_files)}")
        print(f"Files processed: {success_count}/{len(file_selections)}")

        if analysis_failed:
            print(f"Analysis failed: {len(analysis_failed)} file(s)")
            for filename in analysis_failed:
                print(f"  ✗ {filename.name}")

        if processing_failed:
            print(f"Processing failed: {len(processing_failed)} file(s)")
            for filename in processing_failed:
                print(f"  ✗ {filename.name}")

        if success_count == len(file_selections) and not analysis_failed:
            print("✔ All files processed successfully!")
            return 0
        elif success_count > 0:
            print("⚠ Some files failed to process")
            return 1
        else:
            print("✗ No files were processed successfully")
            return 1

    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        return 1

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
