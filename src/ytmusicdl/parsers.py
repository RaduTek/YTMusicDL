from logging import getLogger
from ytmusicdl.types import *
from ytmusicdl.config import Config
import re
import ytmusicdl.utils as utils
import ytmusicdl.url as url


class Parser:
    """Base class for parsers"""

    log = getLogger("YTMusicDL")
    config: Config = None

    def __init__(self, config: Config):
        self.config = config

    def parse_artist(self, data: dict) -> Artist:
        """Parse an artist from a YouTube Music track response"""
        artist = Artist()

        artist["name"] = data["name"]
        artist["id"] = data["id"]

        return artist

    def parse_artists(self, data: list[dict]) -> list[Artist]:
        """Parse a list of artists from a YouTube Music track response"""
        return [self.parse_artist(artist) for artist in data]

    def parse_wp_track_album(self, data: dict) -> Album:
        """Parse an album from a YouTube Music watch playlist track response"""
        album = Album()

        album["id"] = data["id"]
        album["title"] = data["name"]

        return album

    def parse_cover_art(self, data: list) -> str:
        """Parse the cover art URL from a YouTube Music track response"""

        # Shortcuts to handle common cover URL formats
        last_cover_url = data[-1]["url"]

        # Check if last_url ends with '=s' followed by digits (e.g., '=s196')
        if re.search(r"=s\d+$", last_cover_url):
            last_cover_url = re.sub(r"=s\d+$", "=s", last_cover_url)
            return last_cover_url + str(self.config["cover_size"])

        # Check if last_url ends with '=w*-h*-*' (e.g., '=w60-h60-l90-rj')
        if re.search(r"=w\d+-h\d+-.*$", last_cover_url):
            last_cover_url = re.sub(r"=w\d+-h\d+-.*$", "=s", last_cover_url)
            return last_cover_url + str(self.config["cover_size"])

        # Sort covers by width and return the largest one that fits the cover size
        all_covers = data.copy()
        all_covers.sort(key=lambda x: x["width"], reverse=True)

        for cover in all_covers:
            if cover["width"] <= self.config["cover_size"]:
                return cover["url"]

        return all_covers[0]["url"]

    def parse_track_song(self, data: dict) -> Song:
        """Parse a song from a YouTube Music response"""
        song = Song()

        song["id"] = data["videoId"]
        song["title"] = data["title"]

        if "videoType" in data and data["videoType"] in song_types:
            song["type"] = song_types[data["videoType"]]

        if "thumbnail" in data and data["thumbnail"]:
            # Response from watch playlist
            song["cover"] = self.parse_cover_art(data["thumbnail"])
        elif "thumbnails" in data and data["thumbnails"]:
            song["cover"] = self.parse_cover_art(data["thumbnails"])

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
            song["album"] = self.parse_wp_track_album(data["album"])

        if "artists" in data:
            # Available in watch playlist and album tracks
            song["artists"] = self.parse_artists(data["artists"])

        return song

    def parse_album_data(self, data: dict, id: str) -> Album:
        """Parse album data from a YouTube Music album response"""
        album = Album()

        album["id"] = id
        album["playlist_id"] = data["audioPlaylistId"]
        album["title"] = data["title"]
        album["type"] = data["type"]
        album["year"] = data["year"]
        album["duration"] = data["duration_seconds"]
        album["total"] = data["trackCount"]
        album["artists"] = self.parse_artists(data["artists"])
        album["cover"] = self.parse_cover_art(data["thumbnails"])

        return album

    def parse_album_data_list(self, data: dict, id: str) -> AlbumList:
        """Parse album data from a YouTube Music album list response"""
        album = self.parse_album_data(data, id)

        album_list = AlbumList(**album)
        album_list["songs"] = SongList()

        # Parse song list and add track indexes
        if "tracks" in data:
            for song_data in data["tracks"]:
                try:
                    song = self.parse_track_song(song_data)
                    song["source"] = url.get_source(song["id"])
                    song["metadataFull"] = True
                    album_list["songs"][song["id"]] = song
                except Exception as e:
                    song_txt = "unknown song"
                    if "title" in song_data:
                        song_txt = f"'{song_data["title"]}'"
                    if "videoId" in song_data:
                        song_txt += f" ({song_data['videoId']})"
                    self.log.warning(f"Failed to parse song data for {song_txt}: {e}")
        else:
            raise ValueError("No tracks found in album data.")

        return album_list

    def find_song_in_albumlist(self, song: Song, album: AlbumList = None) -> int:
        """Search for a song in album list to find it's index, and update ID in album if necessary"""

        if not album:
            album = song["album"]

        for id, s in album["songs"].items():
            if song["title"].lower() == s["title"].lower():
                # we found song in the album list
                # update album list to replace video with audio song

                old_song = album["songs"].pop(id)
                old_song["id"] = song["id"]
                old_song["type"] = song["type"]
                old_song["duration"] = song["duration"]
                album["songs"][song["id"]] = old_song

                song["index"] = old_song["index"]

                return old_song["index"]

        raise KeyError("Song not found in album!")

    def parse_playlist_data(self, data: dict) -> PlayList:
        """Parse playlist data from a YouTube Music playlist response"""
        playlist = PlayList()

        playlist["id"] = data["id"]
        playlist["title"] = data["title"]
        playlist["duration"] = data["duration_seconds"]
        playlist["total"] = data["trackCount"]
        playlist["cover"] = self.parse_cover_art(data["thumbnails"])
        playlist["songs"] = SongList()

        # Parse song list
        if "tracks" in data:
            for song_data in data["tracks"]:
                try:
                    song = self.parse_track_song(song_data)
                    song["source"] = url.get_source(song["id"])
                    playlist["songs"][song["id"]] = song
                except Exception as e:
                    song_txt = f"unknown song"
                    if "title" in song_data:
                        song_txt = f"'{song_data["title"]}'"
                    if "videoId" in song_data:
                        song_txt += f" ({song_data['videoId']})"
                    self.log.warning(f"Failed to parse song data for {song_txt}: {e}")
        else:
            raise ValueError("No tracks found in album data.")

        return playlist
