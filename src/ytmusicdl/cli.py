import argparse
import sys
from ytmusicdl import YTMusicDL
from ytmusicdl.config import default_config, validate_config
from ytmusicdl.types import audio_formats, audio_qualities, cover_formats


class SmartFormatter(argparse.HelpFormatter):
    def _split_lines(self, text, width):
        if text.startswith("R|"):
            return text[2:].splitlines()
        return argparse.HelpFormatter._split_lines(self, text, width)


class CustomArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, formatter_class=SmartFormatter, **kwargs)

    def print_usage(self, file=None):
        if file is None:
            file = sys.stderr
        # Add emoji and custom prefix
        file.write("📖 ")
        super().print_usage(file)

    def error(self, message):
        self.print_usage(sys.stderr)
        sys.stderr.write(f"\n❌ {message}\n")
        sys.exit(2)


def main():
    config = default_config()

    parser = CustomArgumentParser(
        prog="ytmusicdl",
        description="Download music from YouTube Music using YTMusicDL.",
    )
    parser.add_argument(
        "urls", metavar="URL", type=str, nargs="+", help="List of URL(s) to download"
    )
    parser.add_argument(
        "-b",
        "--base-path",
        type=str,
        default=config["base_path"],
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
        "-a",
        "--archive-file",
        type=str,
        default=config["archive_file"],
        help="Path to the archive file to keep track of downloaded items",
    )
    parser.add_argument(
        "--auth-file",
        type=str,
        default=config["auth_file"],
        help="Path to the authentication file",
    )
    parser.add_argument(
        "-c",
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
        help=f"Size of the cover image in pixels (default: {config['cover_size']})",
    )
    # parser.add_argument(
    #     "--config", default="config.json", help="Path to the configuration file."
    # )

    args = parser.parse_args()
    config.update(args.__dict__)

    try:
        validate_config(config)
    except ValueError as e:
        print(f"❌ Configuration error: {e}", file=sys.stderr)
        return

    try:
        ytmusicdl = YTMusicDL(config)
    except Exception as e:
        print("❌ Error initializing YTMusicDL:", e, file=sys.stderr)
        return

    log = ytmusicdl.log

    try:
        ytmusicdl.download_many(args.urls)
    except Exception as e:
        log.error("❌ Error during download: %s", e)
        return
