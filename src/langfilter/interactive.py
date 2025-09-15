"""Interactive user interface for track selection."""

from __future__ import annotations

from langfilter.config import LangFilterConfig
from langfilter.parser import AudioTrack

# ANSI color codes
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RESET = "\033[0m"
BOLD = "\033[1m"


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
    tracks: list[AudioTrack], config: LangFilterConfig | None = None
) -> list[AudioTrack]:
    """Interactively ask user which tracks to keep."""
    if not tracks:
        print("No audio tracks found in the file.")
        return []

    # Track which tracks are selected for removal (inverse of what we want to keep)
    tracks_to_remove = set()

    # Apply default configuration if provided
    if config and config.has_rules():
        tracks_to_remove = config.apply_defaults(tracks)
        print(f"\n{YELLOW}Applied default configuration: {config}{RESET}")

    print(f"\n{BOLD}Found {len(tracks)} audio track(s):{RESET}")
    print()

    while True:
        # Display all tracks with current selection status
        _display_tracks_with_selection(tracks, tracks_to_remove)

        print()
        print(f"{BOLD}Commands:{RESET}")
        print("  • Enter track number(s) to toggle selection for removal")
        print("  • Use ranges: 1-5 selects tracks 1, 2, 3, 4, 5")
        print("  • Mix numbers and ranges: 1 3-5 8 selects tracks 1, 3, 4, 5, 8")
        print("  • 'd' or 'done' to proceed with current selection")
        print("  • 'q' or 'quit' to cancel")
        print("  • 'c' to clear all selections")
        print()

        try:
            user_input = input("Selection: ").strip().lower()

            if user_input in ("q", "quit"):
                print("Operation cancelled.")
                return []

            if user_input in ("d", "done"):
                break

            if user_input == "c":
                tracks_to_remove.clear()
                continue

            if not user_input:
                print(f"{YELLOW}Please enter a command or track number(s).{RESET}")
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

                print(f"{GREEN}Selection updated.{RESET}")

        except KeyboardInterrupt:
            print(f"\n{YELLOW}Operation cancelled.{RESET}")
            return []
        except EOFError:
            print(f"\n{YELLOW}Operation cancelled.{RESET}")
            return []

    # Calculate tracks to keep (inverse of tracks to remove)
    tracks_to_keep = [track for i, track in enumerate(tracks) if i not in tracks_to_remove]

    if not tracks_to_keep:
        print(f"{RED}All tracks selected for removal. This would leave no audio tracks.{RESET}")
        confirm = input("Are you sure you want to continue? (y/N): ").strip().lower()
        if confirm not in ("y", "yes"):
            print("Operation cancelled.")
            return []

    # Final selection summary
    print(f"\n{BOLD}Final selection:{RESET}")
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


def _display_tracks_with_selection(tracks: list[AudioTrack], tracks_to_remove: set[int]) -> None:
    """Display tracks with visual indicators for selection status."""
    for i, track in enumerate(tracks):
        if i in tracks_to_remove:
            # Track selected for removal - show in red with > marker
            print(f"  {RED}>{i + 1:2}. {track}{RESET}")
        else:
            # Track to keep - show normally
            print(f"   {i + 1:2}. {track}")

    removed_count = len(tracks_to_remove)
    kept_count = len(tracks) - removed_count

    print()
    print(
        f"  {GREEN}Tracks to keep: {kept_count}{RESET} | {RED}Tracks to remove: {removed_count}{RESET}"
    )

    if removed_count == len(tracks):
        print(f"  {RED}{BOLD}⚠ All tracks selected for removal!{RESET}")
