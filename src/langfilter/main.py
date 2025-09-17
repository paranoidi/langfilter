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
    select_tracks_non_interactive,
    select_tracks_to_keep,
)
from langfilter.parser import AudioTrack, get_audio_tracks
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
    error_message: str | None = None

    @property
    def should_process(self) -> bool:
        """Whether this file should be processed (has tracks to filter)."""
        return self.status == TrackSelectionResult.SUCCESS and self.selected_tracks is not None

    @property
    def needs_filtering(self) -> bool:
        """Whether this file needs filtering (not all tracks selected)."""
        return (
            self.should_process
            and self.all_tracks is not None
            and self.selected_tracks is not None
            and len(self.selected_tracks) < len(self.all_tracks)
        )


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

        if not audio_tracks:
            print("No audio tracks found in the file.")
            return FileAnalysisResult(
                status=TrackSelectionResult.SKIPPED_NO_TRACKS, all_tracks=None, selected_tracks=None
            )

        # Track selection (interactive or non-interactive)
        if non_interactive:
            if config is None or not config.has_rules():
                print(f"{YELLOW}Non-interactive mode requires configuration rules.{RESET}")
                print("No tracks will be removed. File will be skipped.")
                return FileAnalysisResult(
                    status=TrackSelectionResult.SKIPPED_NO_SELECTION,
                    all_tracks=audio_tracks,
                    selected_tracks=None,
                )
            selected_tracks = select_tracks_non_interactive(audio_tracks, config)
        else:
            selected_tracks = select_tracks_to_keep(audio_tracks, config)

        if not selected_tracks:
            print("No tracks selected. File will be skipped.")
            return FileAnalysisResult(
                status=TrackSelectionResult.SKIPPED_NO_SELECTION,
                all_tracks=audio_tracks,
                selected_tracks=None,
            )

        # Check if all tracks are selected (no filtering needed)
        if len(selected_tracks) == len(audio_tracks):
            print("All tracks selected. No filtering needed for this file.")
            return FileAnalysisResult(
                status=TrackSelectionResult.SKIPPED_ALL_SELECTED,
                all_tracks=audio_tracks,
                selected_tracks=selected_tracks,
            )

        print(
            f"Selection complete: {len(selected_tracks)} track(s) to keep, {len(audio_tracks) - len(selected_tracks)} to remove"
        )
        return FileAnalysisResult(
            status=TrackSelectionResult.SUCCESS,
            all_tracks=audio_tracks,
            selected_tracks=selected_tracks,
        )

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
) -> bool:
    """
    Process a file with predetermined track selection.

    Returns success status.
    """
    print(f"\nProcessing: {filename}")

    try:
        # Process the file
        filtered_file = remove_unwanted_tracks(filename, selected_tracks, output_path)

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

            result = analyze_and_select_tracks(filename, config, args.non_interactive)

            if result.should_process:
                file_selections.append((filename, result.selected_tracks))
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

        for i, (filename, selected_tracks) in enumerate(file_selections):
            print(f"\n--- Processing {i + 1}/{len(file_selections)}: {filename.name} ---")
            print(f"Keeping {len(selected_tracks)} track(s)...")

            success = process_file_with_selection(
                filename,
                selected_tracks,
                args.output if len(valid_files) == 1 else None,
                True,  # Always replace original file (new default behavior)
                not args.no_backup,
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
