
# Default configuration
default_config = {
    'base_path': '',
    'format': 'opus',
    'quality': '0',  # Maximum/optimized quality
    'output_template': '{song_title} - {song_artist} [{song_id}].{ext}',
    'auth_headers': None,
    'cover_format': 'png',  # Can be 'png' or 'jpg'
    'write_cover': False,
    'write_lyrics': False,
    'no_lyrics': False,
    
    'skip_existing': True,
    'skip_download': False,
    'download_limit': 0,  # 0 means no limit
    'playlist_limit': 5000,  # Default is YT's limit for playlist length
    'skip_already_archive_message': False,

    'verbose': False,
    'log': None,    # Path to file storing log
    'log_verbose': True,

    'album_song_instead_of_video': True,  # Gets album song instead of video when downloading album
    'artist_separator': '; ',
    'filename_separator': ', ',
    'filename_sanitize_placeholder': '_',
    'library_limit': 250,  # Limit for results from account specific requests
    'library_order': 'recently_added',  # 'a_to_z', 'z_to_a' or 'recently_added'
    'library_songs_limit': 5000,  # Limit for get_library_songs request
    'supress_ytdlp_output': True,
    'date_format': '%d-%m-%Y',
    'time_format': '%H-%M-%S',
    'datetime_format': '%d-%m-%Y %H-%M-%S',
    'unknown_placeholder': "Unknown",
}
