from ytmusicdl.config import Config
from ytmusicdl.types import *
import json


def sourceable_str(sourceable: Sourceable) -> str:
    return f"'{sourceable['title']}' ({sourceable["id"]})"


def song_str(song: Song, config: Config) -> str:
    """Return a string representation of a song"""
    sep = config["artist_separator"]
    return f"{song["title"]} - {sep.join(artist["name"] for artist in song["artists"])}"


# Write dict to JSON file
def write_out_json(my_dict, file_name):
    s = json.dumps(my_dict, indent=2)
    with open(file_name, "w") as fo:
        fo.write(s)
        fo.close()
    return s


# Sanitize a string to be usable in file names
def sanitize_filename(filename: str, replace: chr):
    allowed_chars = " .,!@#$()[]-+=_"
    new_fn = ""
    for char in filename:
        if char.isalnum() or char in allowed_chars:
            new_fn += char
        else:
            new_fn += replace
    new_fn.strip()
    if new_fn[-1] == ".":
        new_fn = new_fn[:-1]
    return new_fn


# Join artist list with defined separator
def join_artists(artists: list[Artist], separator: str = ", "):
    artist_names = list()
    for artist in artists:
        artist_names.append(artist["name"])
    return separator.join(artist_names)


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
