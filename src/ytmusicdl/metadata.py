from ytmusicdl.types import Song
from ytmusicdl.config import Config
from mutagen.mp4 import MP4, MP4Cover
from mutagen.oggopus import OggOpus


def __embed_aac(file: str, song: Song, config: Config):
    imageformat = (
        MP4Cover.FORMAT_PNG if config["cover_format"] == "png" else MP4Cover.FORMAT_JPEG
    )

    audio = MP4(file)

    audio["\xa9nam"] = song["title"]

    if "artists" in song:
        audio["\xa9ART"] = [artist["name"] for artist in song["artists"]]

    if "year" in song:
        audio["\xa9day"] = str(song["year"])

    if "index" in song:
        audio["trkn"] = [(song["index"], 1)]

    if "album" in song:
        album = song["album"]
        audio["\xa9alb"] = album["title"]

        if "year" in album:
            audio["\xa9day"] = str(album["year"])
        if "artists" in album:
            audio["aART"] = [artist["name"] for artist in album["artists"]]
        if "total" in album:
            audio["trkn"] = [(song["index"], album["total"])]

        if "cover_data" in album:
            audio["covr"] = [MP4Cover(album["cover_data"], imageformat=imageformat)]

    if "cover_data" in song:
        audio["covr"] = [MP4Cover(song["cover_data"], imageformat=imageformat)]

    audio.save()


def __embed_opus(file: str, song: Song, config: Config):
    audio = OggOpus(file)

    audio["title"] = song["title"]

    audio.save()


def embed_metadata(file: str, song: Song, config: Config):
    if config["format"] == "m4a":
        __embed_aac(file, song, config)
    elif config["format"] == "opus":
        __embed_opus(file, song, config)
    else:
        raise ValueError("Invalid audio format specified in config")
