"""Interactive user interface for track selection."""

from __future__ import annotations

from langfilter.config import LangFilterConfig
from langfilter.parser import AudioTrack, SubtitleTrack


class UserCancelledError(Exception):
    """Raised when user cancels the operation."""


# ANSI color codes
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RESET = "\033[0m"
BOLD = "\033[1m"


def _parse_default_track_selection(input_str: str, max_tracks: int) -> int | None:
    """
    Parse default track selection input (e.g., 'd1' to set track 1 as default).

    Returns track index (0-based) if valid, None otherwise.
    """
    if not input_str.startswith("d"):
        return None

    try:
        track_num = int(input_str[1:])
        if 1 <= track_num <= max_tracks:
            return track_num - 1  # Convert to 0-based index
    except ValueError:
        pass

    return None


def _parse_track_selection(input_parts: list[str], max_tracks: int) -> tuple[list[int], bool]:
    """
    Parse track selection input supporting both individual numbers and ranges.

    Returns tuple of (track_indices, success).
    Track indices are 0-based.
    """
    indices = []

    for part in input_parts:
        # Check if it's a range (contains hyphen)
        if "-" in part:
            try:
                start_str, end_str = part.split("-", 1)
                start = int(start_str.strip())
                end = int(end_str.strip())

                # Validate range
                if start < 1 or end < 1 or start > max_tracks or end > max_tracks:
                    print(
                        f"{RED}Invalid range: {part}. Numbers must be between 1 and {max_tracks}.{RESET}"
                    )
                    return [], False

                if start > end:
                    print(f"{RED}Invalid range: {part}. Start must be <= end.{RESET}")
                    return [], False

                # Add all tracks in range (convert to 0-based indices)
                for track_num in range(start, end + 1):
                    indices.append(track_num - 1)

            except ValueError:
                print(f"{RED}Invalid range format: '{part}'. Use format like '1-5'.{RESET}")
                return [], False
        else:
            # Single track number
            try:
                track_num = int(part)
                if 1 <= track_num <= max_tracks:
                    indices.append(track_num - 1)  # Convert to 0-based index
                else:
                    print(
                        f"{RED}Invalid track number: {part}. Must be between 1 and {max_tracks}.{RESET}"
                    )
                    return [], False
            except ValueError:
                print(f"{RED}Invalid input: '{part}'. Please enter numbers or ranges.{RESET}")
                return [], False

    return indices, True


def select_subtitle_tracks_non_interactive(
    tracks: list[SubtitleTrack], config: LangFilterConfig
) -> list[SubtitleTrack]:
    """
    Non-interactive subtitle track selection using only configuration rules.

    Returns tracks to keep based on config rules.
    """
    if not config.keep_subtitle_languages and not config.remove_subtitle_languages:
        print(f"{YELLOW}No subtitle configuration rules found. Keeping all subtitle tracks.{RESET}")
        return tracks

    # Apply configuration rules
    tracks_to_remove = config.apply_subtitle_defaults(tracks)
    tracks_to_keep = [track for i, track in enumerate(tracks) if i not in tracks_to_remove]

    print(f"\n{BOLD}Applied subtitle configuration rules{RESET}")
    print(f"  Tracks to keep: {GREEN}{len(tracks_to_keep)}{RESET}")
    print(f"  Tracks to remove: {RED}{len(tracks_to_remove)}{RESET}")

    if tracks_to_keep:
        print(f"\n{GREEN}Keeping:{RESET}")
        for track in tracks_to_keep:
            print(f"  ✓ {track}")

    if tracks_to_remove:
        print(f"\n{RED}Removing:{RESET}")
        for i in sorted(tracks_to_remove):
            print(f"  ✗ {tracks[i]}")

    return tracks_to_keep


def select_tracks_non_interactive(
    tracks: list[AudioTrack], config: LangFilterConfig
) -> list[AudioTrack]:
    """
    Non-interactive track selection using only configuration rules.

    Returns tracks to keep based on config rules.
    """
    if not config.has_rules():
        print(f"{YELLOW}No configuration rules found. Keeping all tracks.{RESET}")
        return tracks

    # Apply configuration rules
    tracks_to_remove = config.apply_defaults(tracks)
    tracks_to_keep = [track for i, track in enumerate(tracks) if i not in tracks_to_remove]

    print(f"\n{BOLD}Applied configuration rules: {config}{RESET}")
    print(f"  Tracks to keep: {GREEN}{len(tracks_to_keep)}{RESET}")
    print(f"  Tracks to remove: {RED}{len(tracks_to_remove)}{RESET}")

    if tracks_to_keep:
        print(f"\n{GREEN}Keeping:{RESET}")
        for track in tracks_to_keep:
            print(f"  ✓ {track}")

    if tracks_to_remove:
        print(f"\n{RED}Removing:{RESET}")
        for i in sorted(tracks_to_remove):
            print(f"  ✗ {tracks[i]}")

    return tracks_to_keep


def select_tracks_to_keep(
    tracks: list[AudioTrack],
    config: LangFilterConfig | None = None,
    default_track_index: int | None = None,
) -> tuple[list[AudioTrack], int | None]:
    """
    Interactively ask user which tracks to keep.

    Returns tuple of (tracks_to_keep, default_track_index).
    """
    if not tracks:
        print("No audio tracks found in the file.")
        return [], None

    # Track which tracks are selected for removal (inverse of what we want to keep)
    tracks_to_remove = set()
    current_default = default_track_index

    # Apply default configuration if provided
    if config and config.has_rules():
        tracks_to_remove = config.apply_defaults(tracks)
        print(f"\n{YELLOW}Applied default configuration: {config}{RESET}")

    # Set default track from config if available
    if config and config.default_audio_language:
        default_track = config.find_default_audio_track(tracks)
        if default_track:
            current_default = next(
                (
                    i
                    for i, track in enumerate(tracks)
                    if track.mkvmerge_id == default_track.mkvmerge_id
                ),
                None,
            )

    print(f"\n{BOLD}Found {len(tracks)} audio track(s):{RESET}")
    print()

    while True:
        # Display all tracks with current selection status
        _display_tracks_with_selection(tracks, tracks_to_remove, current_default)

        print()
        print(f"{BOLD}Commands:{RESET}")
        print("  • Enter track number(s) to toggle selection for removal")
        print("  • Use ranges: 1-5 selects tracks 1, 2, 3, 4, 5")
        print("  • Mix numbers and ranges: 1 3-5 8 selects tracks 1, 3, 4, 5, 8")
        print("  • 'd1' to set track 1 as default (use 'dN' for track N)")
        print("  • 'n' or 'next' to proceed with current selection")
        print("  • 'q' or 'quit' to cancel")
        print("  • 'c' to clear all selections")
        print()

        try:
            user_input = input("Selection: ").strip().lower()

            if user_input in ("q", "quit"):
                raise UserCancelledError()

            if user_input in ("n", "next"):
                break

            if user_input == "c":
                tracks_to_remove.clear()
                current_default = None
                continue

            if not user_input:
                print(f"{YELLOW}Please enter a command or track number(s).{RESET}")
                continue

            # Check if it's a default track selection (e.g., 'd1')
            default_idx = _parse_default_track_selection(user_input, len(tracks))
            if default_idx is not None:
                if default_idx in tracks_to_remove:
                    print(f"{RED}Cannot set a track marked for removal as default.{RESET}")
                else:
                    current_default = default_idx
                    print(f"{GREEN}Track {default_idx + 1} set as default.{RESET}")
                continue

            # Parse track numbers and ranges
            input_parts = user_input.split()
            track_indices, success = _parse_track_selection(input_parts, len(tracks))

            if success and track_indices:
                # Toggle selection for all parsed indices
                for index in track_indices:
                    if index in tracks_to_remove:
                        tracks_to_remove.remove(index)
                    else:
                        tracks_to_remove.add(index)
                        # If this track was the default, clear default
                        if index == current_default:
                            current_default = None

                print(f"{GREEN}Selection updated.{RESET}")

        except KeyboardInterrupt:
            print(f"\n{YELLOW}Operation cancelled.{RESET}")
            return [], None
        except EOFError:
            print(f"\n{YELLOW}Operation cancelled.{RESET}")
            return [], None

    # Calculate tracks to keep (inverse of tracks to remove)
    tracks_to_keep = [track for i, track in enumerate(tracks) if i not in tracks_to_remove]

    if not tracks_to_keep:
        print(f"{RED}All tracks selected for removal. This would leave no audio tracks.{RESET}")
        confirm = input("Are you sure you want to continue? (y/N): ").strip().lower()
        if confirm not in ("y", "yes"):
            print("Operation cancelled.")
            return [], None

    # Validate default track is in tracks to keep
    if current_default is not None and current_default in tracks_to_remove:
        current_default = None

    # Find default track in tracks_to_keep if it exists
    default_track_id = None
    if current_default is not None and current_default < len(tracks):
        default_track_id = tracks[current_default].mkvmerge_id
        # Verify it's actually in tracks_to_keep
        if not any(track.mkvmerge_id == default_track_id for track in tracks_to_keep):
            default_track_id = None

    # Final selection summary
    print(f"\n{BOLD}Final selection:{RESET}")
    print(f"  Tracks to keep: {GREEN}{len(tracks_to_keep)}{RESET}")
    print(f"  Tracks to remove: {RED}{len(tracks_to_remove)}{RESET}")
    if default_track_id is not None and current_default is not None:
        print(f"  Default track: {GREEN}{BOLD}{current_default + 1}{RESET}")

    if tracks_to_keep:
        print(f"\n{GREEN}Keeping:{RESET}")
        for track in tracks_to_keep:
            default_marker = (
                f" {GREEN}{BOLD}[DEFAULT]{RESET}" if track.mkvmerge_id == default_track_id else ""
            )
            print(f"  ✓ {track}{default_marker}")

    if tracks_to_remove:
        print(f"\n{RED}Removing:{RESET}")
        for i in sorted(tracks_to_remove):
            print(f"  ✗ {tracks[i]}")

    return tracks_to_keep, current_default


def select_subtitle_tracks_to_keep(
    tracks: list[SubtitleTrack],
    config: LangFilterConfig | None = None,
    default_track_index: int | None = None,
) -> tuple[list[SubtitleTrack], int | None]:
    """
    Interactively ask user which subtitle tracks to keep.

    Returns tuple of (tracks_to_keep, default_track_index).
    """
    if not tracks:
        return [], None

    # Track which tracks are selected for removal (inverse of what we want to keep)
    tracks_to_remove = set()
    current_default = default_track_index

    # Apply default configuration if provided
    if config and (config.keep_subtitle_languages or config.remove_subtitle_languages):
        tracks_to_remove = config.apply_subtitle_defaults(tracks)
        print(f"\n{YELLOW}Applied default subtitle configuration{RESET}")

    # Set default track from config if available
    if config and config.default_subtitle_language:
        default_track = config.find_default_subtitle_track(tracks)
        if default_track:
            current_default = next(
                (
                    i
                    for i, track in enumerate(tracks)
                    if track.mkvmerge_id == default_track.mkvmerge_id
                ),
                None,
            )

    print(f"\n{BOLD}Found {len(tracks)} subtitle track(s):{RESET}")
    print()

    while True:
        # Display all tracks with current selection status
        _display_tracks_with_selection(tracks, tracks_to_remove, current_default)

        print()
        print(f"{BOLD}Commands:{RESET}")
        print("  • Enter track number(s) to toggle selection for removal")
        print("  • Use ranges: 1-5 selects tracks 1, 2, 3, 4, 5")
        print("  • Mix numbers and ranges: 1 3-5 8 selects tracks 1, 3, 4, 5, 8")
        print("  • 'd1' to set track 1 as default (use 'dN' for track N)")
        print("  • 'n' or 'next' to proceed with current selection")
        print("  • 'q' or 'quit' to cancel")
        print("  • 'c' to clear all selections")
        print()

        try:
            user_input = input("Selection: ").strip().lower()

            if user_input in ("q", "quit"):
                raise UserCancelledError()

            if user_input in ("n", "next"):
                break

            if user_input == "c":
                tracks_to_remove.clear()
                current_default = None
                continue

            if not user_input:
                print(f"{YELLOW}Please enter a command or track number(s).{RESET}")
                continue

            # Check if it's a default track selection (e.g., 'd1')
            default_idx = _parse_default_track_selection(user_input, len(tracks))
            if default_idx is not None:
                if default_idx in tracks_to_remove:
                    print(f"{RED}Cannot set a track marked for removal as default.{RESET}")
                else:
                    current_default = default_idx
                    print(f"{GREEN}Track {default_idx + 1} set as default.{RESET}")
                continue

            # Parse track numbers and ranges
            input_parts = user_input.split()
            track_indices, success = _parse_track_selection(input_parts, len(tracks))

            if success and track_indices:
                # Toggle selection for all parsed indices
                for index in track_indices:
                    if index in tracks_to_remove:
                        tracks_to_remove.remove(index)
                    else:
                        tracks_to_remove.add(index)
                        # If this track was the default, clear default
                        if index == current_default:
                            current_default = None

                print(f"{GREEN}Selection updated.{RESET}")

        except KeyboardInterrupt:
            print(f"\n{YELLOW}Operation cancelled.{RESET}")
            return [], None
        except EOFError:
            print(f"\n{YELLOW}Operation cancelled.{RESET}")
            return [], None

    # Calculate tracks to keep (inverse of tracks to remove)
    tracks_to_keep = [track for i, track in enumerate(tracks) if i not in tracks_to_remove]

    # Validate default track is in tracks to keep
    if current_default is not None and current_default in tracks_to_remove:
        current_default = None

    # Find default track in tracks_to_keep if it exists
    default_track_id = None
    if current_default is not None and current_default < len(tracks):
        default_track_id = tracks[current_default].mkvmerge_id
        # Verify it's actually in tracks_to_keep
        if not any(track.mkvmerge_id == default_track_id for track in tracks_to_keep):
            default_track_id = None

    # Final selection summary
    print(f"\n{BOLD}Final subtitle selection:{RESET}")
    print(f"  Tracks to keep: {GREEN}{len(tracks_to_keep)}{RESET}")
    print(f"  Tracks to remove: {RED}{len(tracks_to_remove)}{RESET}")
    if default_track_id is not None and current_default is not None:
        print(f"  Default track: {GREEN}{BOLD}{current_default + 1}{RESET}")

    if tracks_to_keep:
        print(f"\n{GREEN}Keeping:{RESET}")
        for track in tracks_to_keep:
            default_marker = (
                f" {GREEN}{BOLD}[DEFAULT]{RESET}" if track.mkvmerge_id == default_track_id else ""
            )
            print(f"  ✓ {track}{default_marker}")

    if tracks_to_remove:
        print(f"\n{RED}Removing:{RESET}")
        for i in sorted(tracks_to_remove):
            print(f"  ✗ {tracks[i]}")

    return tracks_to_keep, current_default


def _display_tracks_with_selection(
    tracks: list[AudioTrack] | list[SubtitleTrack],
    tracks_to_remove: set[int],
    default_track_index: int | None = None,
) -> None:
    """Display tracks with visual indicators for selection status and default track."""
    for i, track in enumerate(tracks):
        default_marker = " [DEFAULT]" if i == default_track_index else ""
        if i in tracks_to_remove:
            # Track selected for removal - show in red with > marker
            print(f"  {RED}>{i + 1:2}. {track}{default_marker}{RESET}")
        else:
            # Track to keep - show normally
            default_color = f"{GREEN}{BOLD}" if i == default_track_index else ""
            default_reset = RESET if i == default_track_index else ""
            print(f"   {i + 1:2}. {default_color}{track}{default_marker}{default_reset}")

    removed_count = len(tracks_to_remove)
    kept_count = len(tracks) - removed_count

    print()
    print(
        f"  {GREEN}Tracks to keep: {kept_count}{RESET} | {RED}Tracks to remove: {removed_count}{RESET}"
    )
    if default_track_index is not None:
        print(f"  {GREEN}{BOLD}Default track: {default_track_index + 1}{RESET}")

    if removed_count == len(tracks):
        print(f"  {RED}{BOLD}⚠ All tracks selected for removal!{RESET}")
