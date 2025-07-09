import argparse
from ytmusicdl import YTMusicDL
from ytmusicdl.config import Config, default_config
from ytmusicdl.types import audio_formats, audio_qualities, cover_formats


class SmartFormatter(argparse.HelpFormatter):
    def _split_lines(self, text, width):
        if text.startswith("R|"):
            return text[2:].splitlines()
        return argparse.HelpFormatter._split_lines(self, text, width)


def main():
    config = default_config()

    parser = argparse.ArgumentParser(
        prog="ytmusicdl",
        description="Download music from YouTube Music using YTMusicDL.",
        formatter_class=SmartFormatter,
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
        help="Audio quality",
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

    print(args)

    # config = Config.from_file(args.config)
    # ytmusicdl = YTMusicDL(config)

    # if "playlist" in args.url:
    #     ytmusicdl.download_playlist(args.url)
    # elif "watch" in args.url:
    #     ytmusicdl.download_song(args.url)
    # else:
    #     ytmusicdl.download_album(args.url)
