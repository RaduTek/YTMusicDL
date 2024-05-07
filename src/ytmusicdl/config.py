from ytmusicdl.types import AudioFormats, CoverFormats

from dataclasses import dataclass


@dataclass
class Config:
    base_path: str = ""
    format: AudioFormats = "opus"
    quality: int = 0  # Maximum/optimized quality
    output_template: str = "{song_title} - {song_artist} [{song_id}].{ext}"
    auth_headers: dict = None
    cover_format: CoverFormats = "png"  # Can be 'png' or 'jpg'
    write_cover: bool = False
    write_lyrics: bool = False
    no_lyrics: bool = False
    skip_existing: bool = True
    skip_download: bool = False
    download_limit: int = 0  # 0 means no limit
    playlist_limit: int = 5000  # Default is YT's limit for playlist length
    skip_already_archive_message: bool = False
    verbose: bool = False
    log: str = None  # Path to file storing log
    log_verbose: bool = True

    # Gets album song instead of video when downloading album
    album_song_instead_of_video: bool = True
    artist_separator: str = "; "
    filename_separator: str = ", "
    filename_sanitize_placeholder: str = "_"
    library_limit: int = 250  # Limit for results from account specific requests
    library_order: str = "recently_added"  # 'a_to_z', 'z_to_a' or 'recently_added'
    library_songs_limit: int = 5000  # Limit for get_library_songs request
    supress_ytdlp_output: bool = True
    date_format: str = "%d-%m-%Y"
    time_format: str = "%H-%M-%S"
    datetime_format: str = "%d-%m-%Y %H-%M-%S"
    unknown_placeholder: str = "Unknown"
