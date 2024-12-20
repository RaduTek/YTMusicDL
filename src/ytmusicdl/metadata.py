from ytmusicdl.types import *
import ytmusicdl.utils as utils


def parse_artist(data: dict) -> Artist:
    """Parse an artist from a YouTube Music track response"""
    artist = Artist()

    artist["name"] = data["name"]
    artist["id"] = data["id"]

    return artist


def parse_artists(data: list[dict]) -> list[Artist]:
    """Parse a list of artists from a YouTube Music track response"""
    return [parse_artist(artist) for artist in data]


def parse_wp_track_album(data: dict) -> Album:
    """Parse an album from a YouTube Music watch playlist track response"""
    album = Album()

    album["id"] = data["id"]
    album["title"] = data["name"]

    return album


def parse_cover_art(data: dict) -> str:
    """Parse the cover art URL from a YouTube Music track response"""
    return data[-1]["url"]


def parse_track_song(data: dict) -> Song:
    """Parse a song from a YouTube Music response"""
    song = Song()

    song["id"] = data["videoId"]
    song["title"] = data["title"]
    song["type"] = song_types[data["videoType"]]

    if "thumbnail" in data and data["thumbnail"]:
        # Response from watch playlist
        song["cover"] = parse_cover_art(data["thumbnail"])
    elif "thumbnails" in data and data["thumbnails"]:
        song["cover"] = parse_cover_art(data["thumbnails"])

    if "duration_seconds" in data:
        # Available in album tracks
        song["duration"] = data["duration_seconds"]
    elif "duration" in data:
        # Available in album tracks
        song["duration"] = utils.length_to_seconds(data["duration"])
    elif "length" in data:
        # Available in watch playlist
        song["duration"] = utils.length_to_seconds(data["length"])

    if "trackNumber" in data:
        # Available in album tracks
        song["index"] = data["trackNumber"]

    if "year" in data:
        # Available in watch playlist
        song["year"] = data["year"]

    if "album" in data and type(data["album"]) == dict:
        # Available in watch playlist
        # On album tracks, it is a string, we ignore it
        song["album"] = parse_wp_track_album(data["album"])

    if "artists" in data:
        # Available in watch playlist and album tracks
        song["artists"] = parse_artists(data["artists"])

    return song


def parse_album_data(data: dict, id: str) -> Album:
    """Parse album data from a YouTube Music album response"""
    album = Album()

    album["id"] = id
    album["playlist_id"] = data["audioPlaylistId"]
    album["title"] = data["title"]
    album["type"] = data["type"]
    album["year"] = data["year"]
    album["duration"] = data["duration_seconds"]
    album["total"] = data["trackCount"]
    album["artists"] = parse_artists(data["artists"])
    album["cover"] = parse_cover_art(data["thumbnails"])

    return album


def parse_album_data_list(data: dict, id: str) -> AlbumList:
    """Parse album data from a YouTube Music album list response"""
    album = parse_album_data(data, id)

    album_list = AlbumList(**album)
    album_list["songs"] = SongList()

    # Parse song list and add track indexes
    if "tracks" in data:
        for song_data in data["tracks"]:
            song = parse_track_song(song_data)
            album_list["songs"][song["id"]] = song
    else:
        raise ValueError("No tracks found in album data.")

    return album_list
