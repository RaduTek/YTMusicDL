import re
from datetime import datetime
from ytmusicdl.types import *
from ytmusicdl.config import Config


def get_template_key(key: str, song: Song, config: Config) -> str:
    """Get a key from the song data"""

    if key == "ext":
        return config["format"]

    elif key in ["date_time", "datetime"]:
        return datetime.now().strftime(config["datetime_format"])

    elif key == "date":
        return datetime.now().strftime(config["date_format"])

    elif key == "time":
        return datetime.now().strftime(config["time_format"])

    elif key.startswith("song_"):
        key = key[5:]

        if key == "artist":
            return song["artists"][0]["name"]
        elif key == "artists":
            return config["artist_separator"].join(
                [artist["name"] for artist in song["artists"]]
            )
        return str(song[key])

    elif key.startswith("album_"):
        if not "album" in song:
            raise KeyError("Album data not available")
        key = key[6:]

        if key == "artist":
            return song["artists"][0]["name"]
        elif key == "artists":
            return config["artist_separator"].join(
                [artist["name"] for artist in song["album"]["artists"]]
            )

        return str(song["album"][key])

    elif key.startswith("playlist_"):
        if not "playlist" in song:
            raise KeyError("Playlist data not available")
        key = key[9:]

        return str(song["playlist"][key])


def check_template(template: str):
    """Check if the output template string is correct."""
    if not template.endswith(".{ext}"):
        raise ValueError("Template string must end with '.{ext}'.")

    # Remove the extension placeholder
    template = template[:-6]

    if template.count("{") != template.count("}"):
        raise ValueError("Mismatched braces count.")

    i = 0
    while i < len(template):
        if template[i] == "{":
            open_pos = i  # Position in string where bracket was open
            close_pos = template.find("}", i + 1)  # Position where bracket is closed

            if close_pos == -1:
                raise ValueError("Braces are not properly closed.")

            if open_pos == close_pos - 1:
                raise ValueError("Empty braces are not allowed.")

            keys = template[open_pos + 1 : close_pos]
            if "{" in keys:
                raise ValueError("Nested braces are not allowed.")

            i = close_pos
        i += 1


def parse_template(template: str, song: Song, config: Config) -> str:
    """Parse and replace keys in the template string using song data."""

    def replace_key(match):
        expr = str(match.group(1))

        # Check for optional separator
        sep = expr.split("+")
        expr = sep[0]
        # Will be empty if no optional separator
        sep = sep[1] if len(sep) > 1 else ""

        keys = expr.split("|")
        for key in keys:
            try:
                value = get_template_key(key, song, config)
                if type(value) is str:
                    return value + sep
            except KeyError:
                pass

        # Supress the placeholder:
        #   - if the last key is empty
        #   - if the last key is an optional separator
        if keys[-1] == "" or (len(keys[-1]) > 0 and keys[-1][0] == "+"):
            return ""

        # No matching key found, return placeholder
        return config["unknown_placeholder"]

    pattern = r"\{([^{}]+)\}?"
    return re.sub(pattern, replace_key, template)
