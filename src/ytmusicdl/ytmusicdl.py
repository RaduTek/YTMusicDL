import os
import ytmusicdl.metadata as metadata
import ytmusicdl.url as url
import ytmusicdl.utils as utils
from ytmusicdl.types import *
from ytmusicdl.config import Config
from yt_dlp import YoutubeDL
from ytmusicapi import YTMusic


class YTMusicDL:
    """YouTube Music Downloader class"""

    ytmusic: YTMusic
    ytdlp: YoutubeDL

    config: Config

    last_raw_data: dict = None

    def __init__(self, config: Config = Config()):
        """Create a new YTMusicDL object"""

        # Load default configuration
        self.config = config

        if not os.path.isabs(self.config.base_path):
            self.config.base_path = os.path.join(os.getcwd(), self.config.base_path)

        # Spawn a ytmusicapi object with or without authentification headers
        self.ytmusic = YTMusic(auth=self.config.auth_headers)

        return

    def find_audio_counterpart(self, song: Song, album_id: str | None = None) -> str:
        """Find the audio counterpart of a music video song\n
        Workaround for free accounts, as YTM API forces music videos for songs in album playlists\n
        This is done by searching for the song on YTM and picking the matching result\n
        Only downside is that it takes a few seconds to fetch the data"""
        artist = song["artists"][0]["name"]

        # Search for the song on YouTube Music
        # Filter for audio only tracks
        self.last_raw_data = results = self.ytmusic.search(
            f"{song["title"]} {artist}", filter="songs", ignore_spelling=True
        )

        if len(results) > 0:
            if album_id == None:
                # No album ID provided, return the first result
                return results[0]["videoId"]

            for result in results:
                # Check if the song is in the album
                if album_id == result["browseId"]:
                    return result["videoId"]

        raise RuntimeError(
            f"Could not find audio counterpart for song '{song["title"]}'"
        )

    def get_last_raw_data(self):
        """Return the last fetched data from YouTube Music\n
        Only for testing purposes, do not use as a reliable data source"""
        return self.last_raw_data

    def get_album_id_from_playlist(self, playlist_id: str):
        """Get the album browseId from a playlist browseId"""
        return self.ytmusic.get_album_browse_id(playlist_id)

    def __get_album_info(self, source: Source | str, songs: bool) -> Album | AlbumList:
        """Get metadata for album source with or without songs"""

        if type(source) is str:
            source = url.parse_id(source)

        browseId = source["id"]

        if source["type"] == "playlist" and source["subtype"] == "album":
            browseId = self.get_album_id_from_playlist(browseId)
        elif source["type"] != "album":
            raise ValueError(
                f"Invalid source type: '{source['type']}', expected type 'album' or 'playlist' with subtype 'album'."
            )

        self.last_raw_data = data = self.ytmusic.get_album(browseId)

        if songs:
            return metadata.parse_album_data_list(data, browseId)
        else:
            return metadata.parse_album_data(data, browseId)

    def get_album_info(self, source: Source | str) -> Album:
        """Get metadata for album source"""

        return self.__get_album_info(source, False)

    def get_album_list(self, source: Source | str) -> AlbumList:
        """Get metadata for album source, including songs"""

        return self.__get_album_info(source, True)

    def get_song_info(self, source: Source | str) -> Song:
        """Get metadata for song source"""

        if type(source) is str:
            source = url.parse_id(source)

        if source["type"] != "watch":
            raise ValueError(
                f"Invalid source type: '{source['type']}', expected type 'watch'."
            )

        id = source["id"]

        self.last_raw_data = data = self.ytmusic.get_watch_playlist(id, limit=2)

        return metadata.parse_track_song(data["tracks"][0])

    def get_song_with_album(self, source: Source | str) -> Song:
        """Get metadata for song source, including album data and song index"""

        song = self.get_song_info(source)

        album_id = song["album"]["id"]
        album = self.get_album_list(album_id)

        song["album"] = album

        ## This will only work with Premium accounts right now
        ## as YTM API pushes music videos with different IDs for album playlists
        song["index"] = album["songs"][song["id"]]["index"]

        return song
