# LangFilter

Command-line tool to remove unwanted audio and subtitle language tracks from MKV files.

## Overview

LangFilter helps you clean up MKV video files by removing audio and subtitle tracks in unwanted languages. It provides both interactive and automated modes, with configuration file support for batch processing.

## Features

- **Interactive mode**: Choose which audio and subtitle tracks to keep from a visual menu
- **Non-interactive mode**: Apply predefined rules from configuration files
- **Batch processing**: Process multiple MKV files at once
- **Flexible configuration**: Remove specific languages or keep only desired ones for both audio and subtitles
- **Default track selection**: Set default audio and subtitle tracks by language
- **Safe operations**: Replaces original files with filtered versions, creates backups with `_original` prefix
- **Track analysis**: Uses `mkvinfo` to analyze audio and subtitle tracks before processing

## Installation

### Prerequisites

LangFilter requires `mkvtoolnix` for MKV file processing:

**Ubuntu/Debian:**
```bash
sudo apt install mkvtoolnix
```

**macOS (Homebrew):**
```bash
brew install mkvtoolnix
```

**Arch Linux:**
```bash
sudo pacman -S mkvtoolnix-cli
```

**Other platforms:** Download from [mkvtoolnix.download](https://mkvtoolnix.download/)

### Install LangFilter

This project uses [uv](https://docs.astral.sh/uv/) for dependency management.

1. Install uv:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. Install the project:
   ```bash
   uv sync
   ```

3. The `langfilter` command will be available after installation.

## Quick Start

### Interactive Mode
```bash
langfilter movie.mkv
```

### Non-Interactive Mode with Configuration
```bash
langfilter --non-interactive *.mkv
```

### Process Files (replaces originals with backup)
```bash
langfilter movie.mkv
```

### Process Without Creating Backup
```bash
langfilter --no-backup movie.mkv
```

## Configuration

Create a configuration file to automate track selection. LangFilter looks for config files in:
- `./langfilter.ini` (current directory)
- `./.langfilter.ini` (current directory, hidden)
- `~/.config/langfilter/config.ini` (user config directory)
- `~/.langfilter.ini` (user home directory)

### Example Configuration
```ini
[audio]
# Remove audio tracks with specific language codes (comma-separated)
remove=rus,ukr

# Or keep only audio tracks with specific language codes
# keep=eng,unknown

# Set default audio track by language code (first matching track becomes default)
# default_audio=eng

# Set default subtitle track by language code (first matching track becomes default)
# default_subtitle=eng

[subtitles]
# Subtitle track filtering (separate from audio tracks)
# Remove subtitle tracks with specific language codes (comma-separated)
remove=rus,ukr

# Or keep only subtitle tracks with specific language codes
# keep=eng,unknown
```

## Usage

```
langfilter [OPTIONS] FILES...

Options:
  -o, --output PATH       Output file path (single file only)
  -n, --non-interactive   Non-interactive mode using config rules
  --no-backup            Don't create backup (default: creates backup with _original prefix)
  -c, --config PATH      Path to configuration file
  --version              Show version
```

## Development

For development setup:
```bash
make install  # Install dependencies
make lint     # Run linting and formatting
make test     # Run tests
make          # Run all checks
```

## Dependencies

- Python 3.13+
- `mkvtoolnix` (for `mkvinfo` and `mkvmerge` commands)

## License

See LICENSE file for details.
