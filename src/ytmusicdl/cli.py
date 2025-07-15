import argparse
import sys
import json
from pathlib import Path
from typing import cast
from ytmusicdl import YTMusicDL
from ytmusicdl.config import (
    Config,
    default_config,
    validate_config,
    import_config,
    different_to_default,
    update_config,
)
from ytmusicdl.types import audio_formats, audio_qualities, cover_formats


def _format_error(message: str) -> str:
    return f"❌ {message}"


def _print_error(message: str):
    """Print an error message to stderr."""
    sys.stderr.write(f"{_format_error(message)}\n")
    sys.exit(1)


class CustomHelpFormatter(argparse.HelpFormatter):
    def _split_lines(self, text, width):
        if text.startswith("R|"):
            return text[2:].splitlines()
        return argparse.HelpFormatter._split_lines(self, text, width)


class CustomArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, formatter_class=CustomHelpFormatter, **kwargs)

    def print_usage(self, file=None):
        if file is None:
            file = sys.stderr
        file.write("📖 ")
        super().print_usage(file)

    def error(self, message):
        self.print_usage(sys.stderr)
        sys.stderr.write(f"\n{_format_error(message)}\n")
        sys.exit(2)


def main():
    config = default_config()

    parser = CustomArgumentParser(
        prog="ytmusicdl",
        description="Download music from YouTube Music using YTMusicDL.",
    )
    parser.add_argument(
        "urls", metavar="URL", type=str, nargs="*", help="List of URL(s) to download"
    )
    parser.add_argument(
        "-b",
        "--base-path",
        type=str,
        default=config["base_path"],
        metavar="PATH",
        help="Base path for downloads (default: current directory)",
    )
    parser.add_argument(
        "-f",
        "--format",
        type=str.lower,
        default=config["format"],
        choices=audio_formats,
        help=f"Audio output format (default: {config['format']})",
    )
    parser.add_argument(
        "-q",
        "--quality",
        type=str.lower,
        default=config["quality"],
        choices=audio_qualities,
        help=f"Audio quality (default: {config["quality"]})",
    )
    parser.add_argument(
        "-o",
        "--output-template",
        type=str,
        default=config["output_template"],
        help="Output file path template (see documentation for format)",
    )
    parser.add_argument(
        "-a",
        "--archive",
        type=str,
        dest="archive_file",
        default=config["archive_file"],
        metavar="FILE",
        help="Path to the archive file to keep track of downloaded items",
    )
    parser.add_argument(
        "--cover-format",
        type=str.lower,
        default=config["cover_format"],
        choices=cover_formats,
        help=f"Cover image format (default: {config['cover_format']})",
    )
    parser.add_argument(
        "--cover-size",
        type=int,
        default=config["cover_size"],
        metavar="SIZE",
        help=f"Size of the cover image in pixels (default: {config['cover_size']})",
    )
    parser.add_argument(
        "--auth-file",
        type=str,
        default=config["auth_file"],
        help="Path to the authentication file (refer to ytmusicapi documentation for generating this file)",
    )
    parser.add_argument(
        "--cookies",
        type=str,
        dest="cookies_file",
        default=config["cookies_file"],
        metavar="FILE",
        help="Path to the cookies file (used for yt-dlp audio download - check yt-dlp documentation for more info)",
    )
    parser.add_argument(
        "--cookies-from-browser",
        type=str,
        default=config["cookies_from_browser"],
        metavar="BROWSER",
        help="Browser to extract cookies from (used for yt-dlp audio download - check yt-dlp documentation for more info)",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        default=config["skip_download"],
        help="Skip the actual download, useful for testing or when you only want to generate metadata",
    )
    parser.add_argument(
        "--overwrite-existing",
        action="store_false",
        dest="skip_existing",
        default=config["skip_existing"],
        help="Overwrite existing files if they already exist",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=config["verbose"],
        help="Enable verbose output",
    )
    parser.add_argument(
        "--log",
        type=str,
        dest="log",
        default=config["log"],
        metavar="FILE",
        help="Path to the log file",
    )
    parser.add_argument(
        "--log-verbose",
        action="store_true",
        default=config["log_verbose"],
        help="Enable verbose output in the log file",
    )
    parser.add_argument(
        "--hide-archive-message",
        action="store_true",
        default=config["hide_archive_message"],
        help="Hide the 'already exists in archive' message when using the archive file",
    )
    parser.add_argument(
        "--print-config",
        action="store_true",
        help="Print the current configuration and exit",
    )

    # Parse command line arguments
    args = cast(Config, parser.parse_args().__dict__)

    # Load config from global file
    try:
        global_config_path = Path("~/.config/ytmusicdl.json").expanduser()
        if global_config_path.exists():
            import_config(global_config_path, config)
    except Exception as e:
        _print_error(f"Error loading global config:\n{e}")
        return

    # Load config from current working path
    try:
        config_path = Path(args["base_path"]) / "ytmusicdl.json"
        if config_path.exists():
            import_config(config_path, config)
    except Exception as e:
        _print_error(f"Error loading local config:\n{e}")
        return

    # Load config from arguments
    # Override with changes from default config
    update_config(config, different_to_default(args))

    if args["print_config"]:
        print(json.dumps(config, indent=4, ensure_ascii=False))
        return

    try:
        validate_config(config)
    except ValueError as e:
        _print_error(f"Configuration error: {e}")

    try:
        ytmusicdl = YTMusicDL(config)
    except Exception as e:
        _print_error(f"Error initializing YTMusicDL: {e}")

    try:
        ytmusicdl.download_many(config["urls"])
    except Exception as e:
        ytmusicdl.log.error("Error during download: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
