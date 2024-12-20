import argparse
import ytmusicdl.config as config


def parse_args():
    class SmartFormatter(argparse.HelpFormatter):
        def _split_lines(self, text, width):
            if text.startswith("R|"):
                return text[2:].splitlines()
            return argparse.HelpFormatter._split_lines(self, text, width)

    parser = argparse.ArgumentParser(
        prog="ytmusicdl.py",
        description="Downloads songs from YT Music with appropriate metadata",
        formatter_class=SmartFormatter,
    )
    parser.add_argument(
        "urls", metavar="URL", type=str, nargs="+", help="List of URL(s) to download"
    )
    parser.add_argument(
        "-f",
        "--format",
        type=str.lower,
        choices=config.formats_ext,
        help="Audio output format",
    )
    parser.add_argument(
        "-q",
        "--quality",
        type=int,
        help="Audio quality: VBR (best: 0 - worst: 9) or CBR (e.g. 256)",
    )
    parser.add_argument(
        "-p",
        "--base-path",
        type=str,
        help="Base output path (default is current working directory)",
    )
    parser.add_argument(
        "-o", "--output-template", type=str, help="Output template for downloaded songs"
    )
    parser.add_argument(
        "-a",
        "--archive",
        type=str,
        help="Path to file that keeps record of the downloaded songs",
    )
    parser.add_argument(
        "-b",
        "--batch",
        action="store_true",
        help="R|Treat URL arguments as paths to files containing a list of URLs or IDs (one per line)"
        + '\nSpecify "-" for input to be taken from console (stdin)',
    )
    parser.add_argument(
        "--auth-headers",
        type=str,
        help="R|Path to file containing authentication headers"
        + "\nAllows special URL placeholder values to be used.",
    )
    parser.add_argument(
        "--write-json",
        action="store_true",
        help="Write JSON with information about each song (follows output template)",
    )
    parser.add_argument(
        "--cover-format",
        type=str.lower,
        choices=config.cover_formats,
        help=f"Set the cover image format (png or jpg)",
    )
    parser.add_argument(
        "--write-cover",
        action="store_true",
        help="Write each song's album cover to a file (follows output template)",
    )
    parser.add_argument(
        "--write-lyrics",
        action="store_true",
        help="Write each song's lyrics to a file (follows output template)",
    )
    parser.add_argument("--no-lyrics", action="store_true", help="Don't obtain lyrics")
    parser.add_argument(
        "--skip-existing", action="store_true", help="Skip over existing files"
    )
    parser.add_argument(
        "--skip-download", action="store_true", help="Skip downloading songs"
    )
    parser.add_argument(
        "--download-limit",
        type=int,
        help="Limit the number of songs to be downloaded in an instance",
    )
    parser.add_argument(
        "--playlist-limit",
        type=int,
        help="Limit the number of songs to be downloaded from a playlist",
    )
    parser.add_argument(
        "--skip-already-archive-message",
        action="store_true",
        help='Disables the "Song is already in archive, skipping it..." message',
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show all debug messages on console and log",
    )
    parser.add_argument("--log", type=str, help="Path to verbose log output file")
    parser.add_argument(
        "--log-verbose", action="store_true", help="Save all debug messages to the log"
    )
    parser.add_argument(
        "--about",
        action="store_true",
        help="Display version information (must specify at least one (dummy) URL)",
    )

    config_args = config.default_config.copy()
    config_args.update(vars(parser.parse_args()))

    return config_args
