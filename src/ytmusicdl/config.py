import json
from pathlib import Path
from typeguard import check_type, TypeCheckError
from ytmusicdl.types import AudioFormat, AudioQuality, CoverFormat
from typing import Literal, TypedDict, NotRequired


class Config(TypedDict, total=False):
    """Configuration settings for YTMusicDL."""

    urls: NotRequired[list[str]]

    base_path: str
    format: AudioFormat
    quality: AudioQuality

    auth_file: str | None
    cookies_file: str | None
    cookies_from_browser: str | None
    archive_file: str | None

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
    failed_download_threshold: int
    cooldown_duration: int

    song_full_metadata: bool

    album_song_instead_of_video: bool
    artist_separator: str
    filename_separator: str
    filename_sanitize_placeholder: str

    library_limit: int
    library_order: str
    library_songs_limit: int

    supress_ytdlp_output: bool
    hide_archive_message: bool
    date_format: str
    time_format: str
    datetime_format: str
    unknown_placeholder: str
    playlist_extension: Literal["m3u", "m3u8"]

    print_config: NotRequired[bool]
    ytdlp_config: NotRequired[dict]


def default_config() -> Config:
    """Return a dictionary with default configuration settings."""

    return {
        "base_path": ".",
        "format": "m4a",
        "quality": "medium",
        "auth_file": None,
        "cookies_file": None,
        "cookies_from_browser": None,
        "archive_file": None,
        "output_template": "preset:default",
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
        "failed_download_threshold": 0,
        "cooldown_duration": 0,
        "song_full_metadata": True,
        "album_song_instead_of_video": True,
        "artist_separator": "; ",
        "filename_separator": ", ",
        "filename_sanitize_placeholder": "_",
        "library_limit": 250,
        "library_order": "recently_added",
        "library_songs_limit": 5000,
        "supress_ytdlp_output": True,
        "hide_archive_message": False,
        "date_format": "%d-%m-%Y",
        "time_format": "%H-%M-%S",
        "datetime_format": "%d-%m-%Y %H-%M-%S",
        "unknown_placeholder": "Unknown",
        "playlist_extension": "m3u",
    }


def different_to_default(config: Config) -> dict[str, any]:
    """Return a dictionary with configuration options that differ from the default."""

    defaults = default_config()
    return {
        k: v
        for k, v in config.items()
        if k not in defaults or (k in defaults and v != defaults[k])
    }


def import_config(config_file: str | Path, config: Config = None) -> Config:
    """Import configuration from a JSON file and update the given configuration object."""

    config_file = Path(config_file)

    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file {config_file} does not exist.")

    with open(config_file, "r", encoding="utf-8") as f:
        try:
            imported_config = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format in {config_file}:\n{e}")

    try:
        validate_config(imported_config)
    except ValueError as e:
        raise ValueError(f"Invalid configuration options in {config_file}:\n{e}")

    config = config or default_config()

    return update_config(config, imported_config)


def update_config(config: Config, update: Config) -> Config:
    """Update an existing configuration with a new configuration"""

    existing_urls = config.get("urls", [])
    new_urls = update.get("urls", [])

    urls = existing_urls + new_urls

    config.update(update)
    config["urls"] = urls

    return config


def validate_config(config: Config) -> None:
    """Validate the configuration settings."""

    try:
        check_type(config, Config)
    except TypeCheckError as e:
        raise ValueError(e)

    defaults = default_config()
    defaults.update(config)
    config = defaults

    if config["archive_file"] and not config["archive_file"].endswith(".json"):
        raise ValueError("Archive file must be a JSON file.")

    if config["auth_file"] and not config["auth_file"].endswith(".json"):
        raise ValueError("Auth file must be a JSON file.")

    if config["quality"] == "high" and not (
        config["cookies_file"] or config["cookies_from_browser"]
    ):
        raise ValueError(
            """High quality formats require authentication for yt-dlp. \
Use --cookies-file or --cookies-from-browser options. \
Refer to yt-dlp documentation for more info."""
        )

    if config["cover_size"] < 50:
        raise ValueError("Cover size must be a positive integer >= 50.")
