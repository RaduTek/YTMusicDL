import copy
import traceback
from pathlib import Path
from ytmusicapi import YTMusic
from ytmusicdl.download import Downloader
from ytmusicdl.parsers import Parser
import ytmusicdl.template as template
import ytmusicdl.url as url
import ytmusicdl.utils as utils
from ytmusicdl.logger import init_logger, CustomLogger, print_stats, print_versions
from ytmusicdl.types import *
from ytmusicdl.config import Config, default_config, validate_config
from ytmusicdl.metadata import embed_metadata
from ytmusicdl.archive import Archive, playlist_to_archive
from ytmusicdl.m3ufile import write_playlist_file


class YTMusicDL:
    """YouTube Music Downloader class"""

    album_data_cache: dict = {}
    config: Config
    last_raw_data = None
    log: CustomLogger
    ytmusic: YTMusic
    print_complete_message: bool = True
    base_path: Path = Path(".")

    # Components
    parser: Parser
    downloader: Downloader
    archive: Archive = None

    def __init__(self, config: Config = None):
        """Create a new YTMusicDL object"""

        # Load default configuration
        self.config = default_config()

        # Update configuration with provided values
        if config is not None:
            self.config.update(config)

        # Validate configuration
        validate_config(self.config)

        # Set up logger
        self.log = init_logger(self.config)
        print_versions()

        self.base_path = Path(self.config["base_path"]).absolute()
        self.log.debug(f"Base path: {self.base_path}")

        # Spawn a ytmusicapi object with or without authentification headers
        self.ytmusic = YTMusic(auth=self.config["auth_file"])

        self.parser = Parser(self.config)
        self.downloader = Downloader(self.config)

        if self.config["archive_file"]:
            self.archive = Archive(self.config["archive_file"])
            self.log.debug(f"Archive file: {self.config["archive_file"]}")

    def find_audio_counterpart(self, song: Song, album: Album | None = None) -> str:
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
            if album == None:
                # No album ID provided, return the first result
                return results[0]["videoId"]

            for result in results:
                # Find song by search and match the album ID
                if album["id"] == result["album"]["id"]:
                    return result["videoId"]

            for result in results:
                # Try to match the song by the name and album name
                if (
                    str(result["title"]).lower() == song["title"].lower()
                    and str(result["album"]["name"]).lower() == album["title"].lower()
                ):
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

        # Check if the album is already audio
        if all(song["type"] == "audio" for song in album["songs"].values()):
            return

        items = self.downloader.get_playlist_items(
            f"https://youtube.com/playlist?list={album['playlist_id']}"
        )

        updated_songs = {}

        for idx, song in enumerate(album["songs"].values()):
            if not song["id"] or not song["source"]:
                # If song does not have an ID or source, skip it
                self.log.warning(
                    f"Skipping song '{song["title"]}' with missing ID or source."
                )
                continue
            if song["type"] == "audio":
                updated_songs[song["id"]] = song
                continue

            audio_id = items[idx]["id"]
            song["id"] = audio_id
            song["type"] = "audio"
            song["source"] = items[idx]["source"]
            updated_songs[audio_id] = Song(**song)

        album["songs"] = updated_songs

    def __get_album_info(self, source: Source | str, songs: bool) -> Album | AlbumList:
        """Get metadata for album source with or without songs"""

        source = url.get_source(source)

        browse_id = source["id"]
        playlist_id = None

        if source["type"] == "playlist" and source["subtype"] == "album":
            playlist_id = browse_id
            browse_id = self.get_album_id_from_playlist(browse_id)
        elif source["type"] != "album":
            raise ValueError(
                f"Invalid source type: '{source['type']}', expected type 'album' or 'playlist' with subtype 'album'."
            )

        self.last_raw_data = data = self.ytmusic.get_album(browse_id)

        album = None

        if browse_id in self.album_data_cache:
            # Retrieve album data from runtime cache
            album = self.album_data_cache[browse_id]
        else:
            # Parse raw data from API
            album = self.parser.parse_album_data_list(data, browse_id)

            album["source"] = source
            if playlist_id:
                album["playlist_id"] = playlist_id

            # Replace video versions with audio versions
            if self.config["album_song_instead_of_video"]:
                self.__get_album_audio_counterparts(album)

            # Add album to cache, so it won't need to be loaded from the server again
            self.album_data_cache[browse_id] = album

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

        self.log.debug(f"Fetching song info for source: {source}")

        source = url.get_source(source)
        id = source["id"]

        self.last_raw_data = data = self.ytmusic.get_watch_playlist(id, limit=2)

        song = self.parser.parse_track_song(data["tracks"][0])
        song["source"] = source
        song["metadataFull"] = False

        return song

    def get_song_with_album(self, source: Source | str) -> Song:
        """Get metadata for song source, including album data and song index"""

        self.log.debug(f"Fetching song info with album data for source: {source}")

        song = self.get_song_info(source)

        if "album" not in song:
            return song

        album_id = song["album"]["id"]
        album = self.get_album_list(album_id)

        song["album"] = album

        if song["id"] in album["songs"]:
            # Find song index from album list
            song["index"] = album["songs"][song["id"]]["index"]
        else:
            # Try to find the song in the album song list by track name
            # Unlikely to reach this point
            self.parser.find_song_in_albumlist(song)

        song["metadataFull"] = True
        return song

    def get_playlist_info(self, source: Source | str) -> PlayList:
        """Get metadata for playlist source"""

        source = url.get_source(source, "playlist")

        self.last_raw_data = data = self.ytmusic.get_playlist(
            source["id"], limit=self.config["playlist_limit"]
        )

        playlist = self.parser.parse_playlist_data(data)
        playlist["source"] = source

        return playlist

    def download_song(self, song: Song | Source | str) -> str:
        """Download a song from a source to the output path"""

        if not is_source(song):
            song = url.get_source(song)

        if self.archive and self.archive.song_exists(song["id"]):
            song_archived = self.archive.get_song(song["id"])
            self.log.info(
                f"Song '{song_archived["title"]}' already exists in archive, skipping download."
            )
            return song_archived["file"]

        if not is_sourceable(song):
            self.log.status("Loading song info...")
            if self.config["song_full_metadata"]:
                song = self.get_song_with_album(song)
            else:
                song = self.get_song_info(song)

        if self.config["song_full_metadata"] and not song.get("metadataFull", False):
            song_extra = self.get_song_with_album(song["source"])
            song.update(song_extra)

        self.log.status(f"Downloading song: {utils.sourceable_str(song)}...")

        output_file = template.parse_template(
            self.config["output_template"], song, self.config
        )
        output_path = self.base_path / output_file

        if output_path.exists():
            if self.config["skip_existing"]:
                self.log.info(
                    f"File '{output_file}' already exists, skipping download."
                )
                if self.archive:
                    self.archive.add_song(
                        song_id=song["id"],
                        title=utils.song_str(song, self.config),
                        duration=song["duration"],
                        file_path=output_file,
                        exception_on_exists=False,
                    )
                return str(output_path)

            self.log.warning(f"File '{output_file}' already exists, overwriting.")

        if self.config["skip_download"]:
            self.log.warning("Skipped audio download (--skip-download option enabled).")
        else:
            if "album" in song and "cover" in song["album"]:
                self.downloader.download_cover(song["album"])
            elif "cover" in song:
                self.downloader.download_cover(song)

            self.downloader.download_audio(song, str(output_path))

            embed_metadata(str(output_path), song, self.config)

        if self.archive:
            self.archive.add_song(
                song_id=song["id"],
                title=utils.song_str(song, self.config),
                duration=song["duration"],
                file_path=output_file,
            )

        self.log.success(f"Downloaded {utils.sourceable_str(song)}")

        return str(output_path)

    def download_album(self, album: AlbumList | Source | str):
        """Download all songs in an album"""

        if not isinstance(album, dict) or "title" not in album:
            try:
                source = url.get_source(album, "album")
            except ValueError:
                try:
                    source = url.get_source(album, "playlist")
                except ValueError:
                    raise ValueError(
                        f"Invalid source type for album: {album}. Expected 'album' or 'playlist'."
                    )

            self.log.status("Loading album info...")
            album = self.get_album_list(source)

        self.log.status(f"Downloading album: {utils.sourceable_str(album)}...")
        self.log.debug(f"Album data: {album}")

        for song in album["songs"].values():
            try:
                dl_song = Song(**song)
                dl_song["album"] = album
                self.download_song(dl_song)
            except KeyboardInterrupt:
                raise
            except Exception as e:
                self.log.error(
                    f"Failed to download song: {utils.sourceable_str(dl_song)}"
                )
                if "ERROR" not in str(e):
                    self.log.error(e)
                self.log.debug(traceback.format_exc())
                continue

        self.log.success(f"Downloaded album: {utils.sourceable_str(album)}")

    def download_playlist(self, playlist: PlayList | Source | str):
        """Download all songs in a playlist"""
        if not isinstance(playlist, dict) or "title" not in playlist:
            source = url.get_source(playlist, "playlist")

            self.log.status(f"Loading playlist info...")
            playlist = self.get_playlist_info(source)

        self.log.info(f"Downloading playlist: {utils.sourceable_str(playlist)}...")

        downloaded = {}

        for song in dict(playlist["songs"]).values():
            try:
                dl_song = Song(**song)
                dl_song["playlist"] = playlist
                dl_song["source"] = url.get_source(dl_song["id"])
                dl_song["playlist_index"] = dl_song.get("index", 0)

                file = self.download_song(dl_song)

                downloaded[dl_song["id"]] = file
            except KeyboardInterrupt:
                raise
            except Exception as e:
                self.log.error(
                    f"Failed to download song: {utils.sourceable_str(song)}\n{e}"
                )
                self.log.debug(traceback.format_exc())
                continue

        if self.archive:
            self.archive.add_playlist(
                playlist_id=playlist["id"],
                title=playlist["title"],
                file_path=f"{playlist["title"]}.m3u8",
                song_ids=downloaded.keys(),
            )

        # Write the playlist file
        if self.config["write_playlist_file"]:
            self.log.status("Writing playlist file...")
            try:
                archive_playlist = None
                if self.archive:
                    archive_playlist = self.archive.get_playlist_with_songs(
                        playlist["id"]
                    )
                else:
                    archive_playlist = playlist_to_archive(playlist, downloaded)
                write_playlist_file(self.base_path, archive_playlist)
            except Exception as e:
                self.log.error(f"Failed to write playlist file: {e}")
                self.log.debug(traceback.format_exc())
            else:
                self.log.success("Playlist file written successfully.")

        self.log.success(f"Downloaded playlist: {utils.sourceable_str(playlist)}")

    def download(self, source: Source | str):
        """Download from a source"""

        source = url.get_source(source)

        if source["type"] == "album" or (
            "subtype" in source and source["subtype"] == "album"
        ):
            self.download_album(source)
        elif source["type"] == "watch":
            self.download_song(source)
        elif source["type"] == "playlist":
            self.download_playlist(source)
        else:
            raise ValueError(f"Invalid source type: {source['type']}")

    def download_many(self, sources: list[Source | str]):
        """Download from multiple sources"""

        if len(sources) == 0:
            self.log.warning("No sources provided for download.")
            return

        try:
            for source in sources:
                try:
                    self.download(source)
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    self.log.error(f"Failed to download source: {source}\n{e}")
                    self.log.debug(traceback.format_exc())
                    continue
        except KeyboardInterrupt:
            self.log.warning("Download interrupted by user.")

        print_stats(print_success=len(sources) > 1)
