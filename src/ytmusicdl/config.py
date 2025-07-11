from ytmusicdl.types import AudioFormat, AudioQuality, CoverFormat
from typing import TypedDict


class Config(TypedDict, total=False):
    """Configuration settings for YTMusicDL."""

    base_path: str
    format: AudioFormat
    quality: AudioQuality

    auth_file: str | None
    archive_file: str | None
    skip_already_archive_message: bool

    output_template: str
    cover_format: CoverFormat
    cover_size: int
    write_cover: bool
    write_lyrics: bool
    write_playlist_file: bool
    no_lyrics: bool
    skip_existing: bool
    skip_download: bool
    download_limit: int
    playlist_limit: int
    verbose: bool
    emojis: bool
    log: str | None
    log_verbose: bool

    song_full_metadata: bool

    album_song_instead_of_video: bool
    artist_separator: str
    filename_separator: str
    filename_sanitize_placeholder: str

    library_limit: int
    library_order: str
    library_songs_limit: int

    supress_ytdlp_output: bool
    date_format: str
    time_format: str
    datetime_format: str
    unknown_placeholder: str


def default_config() -> Config:
    """Return a dictionary with default configuration settings."""

    return {
        "base_path": "",
        "format": "m4a",
        "quality": "medium",
        "auth_file": None,
        "archive_file": None,
        "skip_already_archive_message": False,
        "output_template": "{song_title} - {song_artist} [{song_id}].{ext}",
        "cover_format": "jpg",
        "cover_size": 500,
        "write_cover": False,
        "write_lyrics": False,
        "write_playlist_file": True,
        "no_lyrics": False,
        "skip_existing": True,
        "skip_download": False,
        "download_limit": 0,
        "playlist_limit": 5000,
        "emojis": True,
        "verbose": False,
        "log": None,
        "log_verbose": True,
        "song_full_metadata": True,
        "album_song_instead_of_video": True,
        "artist_separator": "; ",
        "filename_separator": ", ",
        "filename_sanitize_placeholder": "_",
        "library_limit": 250,
        "library_order": "recently_added",
        "library_songs_limit": 5000,
        "supress_ytdlp_output": True,
        "date_format": "%d-%m-%Y",
        "time_format": "%H-%M-%S",
        "datetime_format": "%d-%m-%Y %H-%M-%S",
        "unknown_placeholder": "Unknown",
    }


def validate_config(config: Config) -> None:
    """Validate the configuration settings."""

    if config["archive_file"] and not config["archive_file"].endswith(".json"):
        raise ValueError("Archive file must be a JSON file.")

    if config["auth_file"] and not config["auth_file"].endswith(".json"):
        raise ValueError("Auth file must be a JSON file.")

    if config["quality"] == "high" and not config["auth_file"]:
        raise ValueError(
            "High quality requires authentication. Please provide an auth file."
        )

    if config["cover_size"] < 50:
        raise ValueError("Cover size must be a positive integer >= 50.")
