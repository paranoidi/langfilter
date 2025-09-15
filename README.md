# LangFilter

Command-line tool to remove unwanted audio language tracks from MKV files.

## Overview

LangFilter helps you clean up MKV video files by removing audio tracks in unwanted languages. It provides both interactive and automated modes, with configuration file support for batch processing.

## Features

- **Interactive mode**: Choose which audio tracks to keep from a visual menu
- **Non-interactive mode**: Apply predefined rules from configuration files
- **Batch processing**: Process multiple MKV files at once
- **Flexible configuration**: Remove specific languages or keep only desired ones
- **Safe operations**: Creates backups by default when replacing files
- **Track analysis**: Uses `mkvinfo` to analyze audio tracks before processing

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

### Replace Original Files (with backup)
```bash
langfilter --replace movie.mkv
```

## Configuration

Create a configuration file to automate track selection. LangFilter looks for config files in:
- `./langfilter.ini` (current directory)
- `./.langfilter.ini` (current directory, hidden)
- `~/.config/langfilter/config.ini` (user config directory)
- `~/.langfilter.ini` (user home directory)

### Example Configuration
```ini
[DEFAULT]
# Remove Russian and Ukrainian tracks
remove=rus,ukr

# Or keep only English and unknown tracks
# keep=eng,unknown
```

## Usage

```
langfilter [OPTIONS] FILES...

Options:
  -o, --output PATH       Output file path (single file only)
  -n, --non-interactive   Non-interactive mode using config rules
  --replace              Replace original file (creates backup)
  --no-backup            Don't create backup when using --replace
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
