from ytmusicdl.types import Artist
import json


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
