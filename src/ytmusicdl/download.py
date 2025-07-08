import logging
import requests
from io import BytesIO
from PIL import Image
from yt_dlp import YoutubeDL
from ytmusicdl.types import Song, Sourceable
from ytmusicdl.config import Config
from ytmusicdl.types import AudioFormat, AudioQuality
import ytmusicdl.url as url
import ytmusicdl.utils as utils


ytdlp_format_map: dict[AudioFormat, dict[AudioQuality, str]] = {
    "opus": {
        "medium": "251",
        "high": "774/251",
    },
    "m4a": {
        "medium": "140",
        "high": "141/140",
    },
}


log = logging.getLogger("YTMusicDL")


def generate_ytdlp_opts(config: Config, output_path: str) -> dict:
    """Generate options for youtube-dl"""

    output_path = output_path.replace("{ext}", "%(ext)s")

    ytdlp_opts = {
        "format": ytdlp_format_map[config["format"]][config["quality"]],
        "extractaudio": True,
        "quiet": config["supress_ytdlp_output"],
        "outtmpl": output_path,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": config["format"],
            }
        ],
    }

    log.debug(f"Generated ytdlp_opts: {ytdlp_opts}")

    return ytdlp_opts


def download_audio(song: Song, output_path: str, config: Config):
    """Download audio from a song to the output path"""

    log.debug(f"Downloading {song['title']} to {output_path}")

    format = config["format"]
    output_path = output_path.replace(f".{format}", "")

    ytdlp_opts = generate_ytdlp_opts(config, output_path)

    with YoutubeDL(ytdlp_opts) as ytdlp:
        status = ytdlp.download([song["source"]["url"]])
        if status != 0:
            log.error(f"Failed to download {song['title']}")
            raise Exception(f"Failed to download {song['title']}")
        else:
            log.debug(f"Downloaded {song['title']}")


def download_cover(sourceable: Sourceable, config: Config):
    """Download cover for a sourceable object"""

    if "cover" not in sourceable:
        raise RuntimeError("Sourceable object does not have a cover art URL")

    if "cover_data" in sourceable:
        log.debug(f"Cover already downloaded for {utils.sourceable_str(sourceable)}")
        return

    cover_format = config["cover_format"]
    log.debug(
        f"Downloading cover for {utils.sourceable_str(sourceable)} in format {cover_format}"
    )

    cover_url = sourceable["cover"]
    cover_data = requests.get(cover_url).content

    if cover_format not in ["png", "jpg"]:
        raise ValueError("Invalid cover format specified in config")

    if cover_format == "jpg":
        cover_format = "jpeg"

    image = Image.open(BytesIO(cover_data))
    output = BytesIO()
    image.save(output, format=cover_format)
    cover_data = output.getvalue()

    log.debug(f"Downloaded cover for '{sourceable['title']}'")

    sourceable["cover_data"] = cover_data


def get_playlist_items(playlist_url: str) -> list[Sourceable]:
    ytdlp_opts = {
        "quiet": True,
        "extract_flat": True,
        "skip_download": True,
    }

    with YoutubeDL(ytdlp_opts) as ydl:
        info = ydl.extract_info(playlist_url, download=False)
        if type(info) == dict and "entries" in info:
            entries = info["entries"]
            videos = []

            for entry in entries:
                if "id" in entry and "title" in entry:
                    videos.append(
                        Sourceable(
                            id=entry["id"],
                            title=entry["title"],
                            source=url.get_source(entry["id"]),
                        )
                    )

            return videos
        else:
            return []
