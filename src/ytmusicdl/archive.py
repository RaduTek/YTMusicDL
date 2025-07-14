from pathlib import Path
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, TypedDict
from ytmusicdl.config import Config
from ytmusicdl.template import sanitize_value
from ytmusicdl.types import PlayList

ISO_FMT = "%Y-%m-%dT%H:%M:%S%z"


class ArchiveSong(TypedDict):
    """Metadata for a single song in the archive."""

    title: str
    duration: int
    file: str
    downloaded: str


class ArchivePlayList(TypedDict):
    """Metadata for a playlist in the archive."""

    title: str
    file: str
    downloaded: datetime
    updated: datetime
    songs: List[str]
    songs_data: Optional[List[ArchiveSong]] = None


class ArchiveData(TypedDict):
    """Top-level structure of the archive JSON file."""

    songs: Dict[str, ArchiveSong] = {}
    playlists: Dict[str, ArchivePlayList] = {}


def _iso_now() -> str:
    """Return current time in ISO‑8601 format with UTC offset."""
    return datetime.now(timezone.utc).strftime(ISO_FMT)


def _iso_parse(date_str: str) -> datetime:
    """Parse an ISO‑8601 date string into a UTC datetime object."""
    return datetime.strptime(date_str, ISO_FMT).replace(tzinfo=timezone.utc)


def playlist_to_archive(
    playlist: PlayList, songs_files: dict[str, str], config: Config
) -> ArchivePlayList:
    """Convert a PlayList object to an ArchivePlayList dictionary."""

    songs = songs_files.keys()
    songs_data: list[ArchiveSong] = [
        {
            "title": song["title"],
            "duration": song["duration"],
            "file": songs_files.get(song["id"], ""),
            "downloaded": _iso_now(),
        }
        for song in playlist["songs"].values()
    ]

    playlist_file = sanitize_value(playlist["title"], config) + ".m3u8"

    return ArchivePlayList(
        title=playlist["title"],
        file=playlist_file,
        songs=songs,
        songs_data=songs_data,
        downloaded=_iso_now(),
        updated=_iso_now(),
    )


class Archive:
    """A class to manage the archive of downloaded songs and playlists."""

    def __init__(self, archive_file: str | Path, save_on_change: bool = True):
        """Initialize the archive with the given file path."""

        self.archive_file = Path(archive_file)
        self.committed = True
        self.save_on_change = save_on_change
        self._data = ArchiveData(songs={}, playlists={})

        if self.archive_file.exists():
            data = json.loads(self.archive_file.read_text())
            if not isinstance(data, dict):
                raise ValueError(f"Invalid archive format in {self.archive_file}")
            self._data = ArchiveData(
                songs=data.get("songs", {}),
                playlists=data.get("playlists", {}),
            )

    def save(self, indent: int = 4):
        """Commit changes to the archive file."""

        if self.committed:
            return

        self.archive_file.write_text(
            json.dumps(self._data, indent=indent, ensure_ascii=False)
        )
        self.committed = True

    def song_exists(self, song_id: str) -> bool:
        """Return *True* if *song_id* is present in the archive."""

        return song_id in self._data["songs"]

    def add_song(
        self,
        song_id: str,
        title: str,
        duration: int,
        file_path: str | Path,
        downloaded: Optional[str] = None,
        overwrite: bool = False,
        exception_on_exists: bool = True,
    ):
        """Add or update a song entry in the archive."""

        if not overwrite and self.song_exists(song_id):
            if exception_on_exists:
                raise ValueError(
                    f"Song '{song_id}' already exists; use overwrite=True to replace."
                )
            return

        self._data["songs"][song_id] = {
            "title": title,
            "duration": duration,
            "file": str(file_path),
            "downloaded": downloaded or _iso_now(),
        }
        self.committed = False

        if self.save_on_change:
            self.save()

    def get_song(self, song_id: str) -> ArchiveSong:
        """Return the song entry for *song_id*."""

        try:
            return self._data["songs"][song_id]
        except KeyError:
            raise KeyError(f"Song '{song_id}' not found in archive.") from None

    def playlist_exists(self, playlist_id: str) -> bool:
        """Return *True* if *playlist_id* exists."""

        return playlist_id in self._data["playlists"]

    def add_playlist(
        self,
        *,
        playlist_id: str,
        title: str,
        file_path: str | Path,
        song_ids: List[str],
        downloaded: Optional[str] = None,
        updated: Optional[str] = None,
    ):
        """Create or update a playlist entry."""

        now = _iso_now()
        exists = self.playlist_exists(playlist_id)
        if not exists:
            self._data["playlists"][playlist_id] = {
                "title": title,
                "file": str(file_path),
                "downloaded": downloaded or now,
                "updated": updated or now,
                "songs": list(song_ids),
            }
        else:
            pl = self._data["playlists"][playlist_id]
            pl.update(
                {
                    "title": title,
                    "file": str(file_path),
                    "updated": updated or now,
                    "songs": list(song_ids),
                }
            )

        self.committed = False

        if self.save_on_change:
            self.save()

    def get_playlist(self, playlist_id: str) -> ArchivePlayList:
        """Return the raw playlist entry without song details."""

        try:
            return self._data["playlists"][playlist_id]
        except KeyError:
            raise KeyError(f"Playlist '{playlist_id}' not found in archive.") from None

    def get_playlist_with_songs(self, playlist_id: str) -> ArchivePlayList:
        """Return playlist entry *including* expanded song metadata."""
        playlist = self.get_playlist(playlist_id)
        songs = [self.get_song(sid) for sid in playlist["songs"]]
        out: ArchivePlayList = {**playlist, "songs_data": songs}
        return out
