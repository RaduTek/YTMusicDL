import copy
import os
import logging
from ytmusicapi import YTMusic
import ytmusicdl.download as download
import ytmusicdl.parsers as parsers
import ytmusicdl.template as template
import ytmusicdl.url as url
import ytmusicdl.utils as utils
from ytmusicdl.types import *
from ytmusicdl.config import Config
from ytmusicdl.metadata import embed_metadata

__version__ = "2.0.0a0"


class YTMusicDL:
    """YouTube Music Downloader class"""

    album_data_cache: dict = {}
    config: Config
    last_raw_data: dict[str, AlbumList] = None
    log: logging.Logger
    ytmusic: YTMusic
    print_complete_message: bool = True

    def __init__(self, config: Config = Config()):
        """Create a new YTMusicDL object"""

        # Load default configuration
        self.config = config

        self.log = logging.getLogger("YTMusicDL")
        self.log.propagate = False
        self.log.setLevel(
            logging.DEBUG
            if self.config.log_verbose or self.config.verbose
            else logging.INFO
        )

        # Configure logger to show info messages on stdout
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG if self.config.verbose else logging.INFO)
        console_formatter = logging.Formatter("%(levelname)s: %(message)s")
        console_handler.setFormatter(console_formatter)
        self.log.addHandler(console_handler)

        # Setup logging to file
        if type(self.config.log) is str:
            log_file = os.path.join(self.config.base_path, self.config.log)
            log_level = logging.DEBUG if self.config.log_verbose else logging.INFO

            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            log_file_handler = logging.FileHandler(log_file)
            log_file_handler.setLevel(log_level)
            log_file_formatter = logging.Formatter(
                "%(asctime)s: %(levelname)s: %(message)s"
            )
            log_file_handler.setFormatter(log_file_formatter)
            self.log.addHandler(log_file_handler)

        self.log.info(f"YTMusicDL version {__version__}")

        if not os.path.isabs(self.config.base_path):
            self.config.base_path = os.path.join(os.getcwd(), self.config.base_path)
        self.log.debug(f"Base path: {self.config.base_path}")

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
                if album_id == result["album"]["id"]:
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


    def __get_album_audio_counterparts(self, album: AlbumList):
        """Find audio counterparts for each song in an album"""

        updated_songs = {}
        
        for id, song in album["songs"].items():
            if song["type"] == "audio":
                updated_songs[id] = song
                continue

            audio_id = self.find_audio_counterpart(song, album["id"])
            song["id"] = audio_id
            song["type"] = "audio"
            song["source"] = url.get_source(audio_id)
            updated_songs[audio_id] = Song(**song)

        album["songs"] = updated_songs


    def __get_album_info(self, source: Source | str, songs: bool) -> Album | AlbumList:
        """Get metadata for album source with or without songs"""
        
        source = url.get_source(source)

        browseId = source["id"]

        if source["type"] == "playlist" and source["subtype"] == "album":
            browseId = self.get_album_id_from_playlist(browseId)
        elif source["type"] != "album":
            raise ValueError(
                f"Invalid source type: '{source['type']}', expected type 'album' or 'playlist' with subtype 'album'."
            )

        self.last_raw_data = data = self.ytmusic.get_album(browseId)

        album = None

        if browseId in self.album_data_cache:
            # Retrieve album data from runtime cache
            album = self.album_data_cache[browseId]
        else:
            # Parse raw data from API
            album = parsers.parse_album_data_list(data, browseId)

            # Replace video versions with audio versions
            if self.config.album_song_instead_of_video:
                self.__get_album_audio_counterparts(album)

            album["source"] = source

            # Add album to cache, so it won't need to be loaded from the server again
            self.album_data_cache[browseId] = album

        # Remove songs field if required
        if not songs:
            album_only = copy.copy(album)
            album_only.pop("songs")
            return Album(**album_only)

        return album


    def get_album_info(self, source: Source | str) -> Album:
        """Get metadata for album source"""

        return self.__get_album_info(source, False)


    def get_album_list(self, source: Source | str) -> AlbumList:
        """Get metadata for album source, including songs"""

        return self.__get_album_info(source, True)


    def get_song_info(self, source: Source | str) -> Song:
        """Get metadata for song source"""

        source = url.get_source(source)
        id = source["id"]

        self.last_raw_data = data = self.ytmusic.get_watch_playlist(id, limit=2)

        song = parsers.parse_track_song(data["tracks"][0])
        song["source"] = source

        return song


    def get_song_with_album(self, source: Source | str) -> Song:
        """Get metadata for song source, including album data and song index"""

        song = self.get_song_info(source)

        album_id = song["album"]["id"]
        album = self.get_album_list(album_id)

        song["album"] = album

        if song["id"] in album["songs"]:
            # Find song index from album list
            song["index"] = album["songs"][song["id"]]["index"]
        else:
            # Try to find the song in the album song list by track name
            # Unlikely to reach this point
            parsers.find_song_in_albumlist(song)

        return song


    def download_song(self, song: Song | Source | str, output_path: str = None):
        """Download a song from a source to the output path"""

        if not isinstance(song, dict) and 'title' not in song:
            source = url.get_source(song)
            if self.config.song_full_metadata:
                song = self.get_song_with_album(source)
            else:
                song = self.get_song_info(source)

        if output_path == None:
            output_path = self.config.base_path

        output_file = template.parse_template(
            self.config.output_template, song, self.config
        )
        output_path = os.path.join(output_path, output_file)

        if "album" in song and "cover" in song["album"]:
            download.download_cover(song["album"], self.config)
        elif "cover" in song:
            download.download_cover(song, self.config)

        download.download_audio(song, output_path, self.config)

        embed_metadata(output_path, song, self.config)


    def download_album(self, album: AlbumList | Source | str, output_path: str = None):
        """Download all songs in an album"""

        if type(album) is not AlbumList:
            album = self.get_album_list(album)
        
        self.log.info(f"Downloading album: {utils.sourceable_str(album)}...")

        for song in album["songs"].values():
            dl_song = Song(**song)
            dl_song["album"] = album
            self.download_song(dl_song, output_path)
        
        self.log.info("Download complete!")

