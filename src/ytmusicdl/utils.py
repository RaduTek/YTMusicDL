from ytmusicdl.config import Config
from ytmusicdl.types import *
import json


def sourceable_str(sourceable: Sourceable) -> str:
    """Return a string representation of a sourceable object (Song, Playlist, etc.)"""
    return f"'{sourceable['title']}' ({sourceable["id"]})"


def song_str(song: Song, config: Config) -> str:
    """Return a string representation of a song"""
    sep = config["artist_separator"]
    return f"{song["title"]} - {sep.join(artist["name"] for artist in song["artists"])}"


def length_to_seconds(length: str) -> int:
    """Converts a time string to seconds"""
    parts = length.split(":")
    parts.reverse()
    seconds = 0
    for i, part in enumerate(parts):
        seconds += int(part) * (60**i)
    return seconds


def seconds_to_length(seconds: int) -> str:
    """Converts seconds to a time string"""
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours == 0:
        return f"{minutes:02d}:{seconds:02d}"
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
