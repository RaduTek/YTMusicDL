import math
from typing import Dict, Any, List
import json
import logging
import sys
from datetime import datetime
from datetime import timedelta
import argparse
import os
import io
import requests
import music_tag
from traceback import format_exc
from PIL import Image
from io import BytesIO
from ytmusicapi import YTMusic
from yt_dlp import YoutubeDL
from urllib.parse import urlparse
from urllib.parse import parse_qs


# Configuration and declarations

__version = '1.1'

# Default configuration
default_config = {
    'default_log_level': logging.INFO,
    'album_song_instead_of_video': True,  # Gets album song instead of video when downloading album
    'artist_separator': '; ',
    'filename_separator': ', ',
    'format': 'opus',
    'quality': '0',  # Maximum/optimized quality
    'output_template': '{song_title} - {song_artist} [{song_id}].{ext}',
    'library_limit': 250,  # Limit for results from account specific requests
    'library_order': 'recently_added',  # 'a_to_z', 'z_to_a' or 'recently_added'
    'library_songs_limit': 5000,  # Limit for get_library_songs request
    'playlist_limit': 5000,  # Default is YT's limit for playlist length
    'download_limit': 0,  # 0 means no limit
    'file_sanitize_replace_chr': '_',
    'supress_ytdlp_output': True,
    'cover_format': 'png',  # Can be 'png' or 'jpg'
    'date_format': '%d-%m-%Y',
    'time_format': '%H-%M-%S',
    'datetime_format': '%d-%m-%Y %H-%M-%S',
    'unknown_placeholder': "Unknown",
    'skip_already_archive_message': False
}

formats_ext = ['opus', 'm4a', 'mp3']
formats_ytdlp = {'opus': 'opus', 'm4a': 'm4a', 'mp3': 'mp3'}
cover_formats = ['png', 'jpg']

song_types = {
    "MUSIC_VIDEO_TYPE_ATV": 'Song',
    "MUSIC_VIDEO_TYPE_OMV": 'Video',
    "MUSIC_VIDEO_TYPE_UGC": 'Video'
}

# Schemas for each data structure
song_schema = {
    'id': str, 'title': str, 'duration': str, 'year': int,
    'type': str, 'artists': list, 'cover': str, 'lyrics': str,
    'lyrics_source': str, 'index': int, 'album': dict,
    'playlist': dict, 'playlist_index': int
}
# 'playlist_index': int is only available for songs obtained from a playlist
# 'playlist': dict is only added to song when passing its data to download_audio
# when downloading a playlist, to provide playlist data to output template
album_schema = {
    'id': str, 'title': str, 'type': str, 'year': int,
    'duration': str, 'total': int, 'artists': list, 'cover': str
}
playlist_schema = {
    'id': str, 'title': str, 'authors': list, 'year': int,
    'duration': str, 'total': int, 'visibility': str, 'description': str,
    'songs': list
}
artist_schema = {
    'name': str, 'id': str
}

# Declare objects
ytm = None
parser: argparse.ArgumentParser
args: dict
log: logging.Logger
archive = list()
stats = {
    'songs': 0,
    'albums': 0,
    'playlists': 0,
    'errors': 0,
    'warnings': 0,
    'has_notified_limit_reached': False
}


# Set up argument parsing
def setup_argparse():
    global parser, args

    class SmartFormatter(argparse.HelpFormatter):
        def _split_lines(self, text, width):
            if text.startswith('R|'):
                return text[2:].splitlines()
            return argparse.HelpFormatter._split_lines(self, text, width)

    parser = argparse.ArgumentParser(
        prog="ytmusicdl.py",
        description="Downloads songs from YT Music with appropriate metadata",
        formatter_class=SmartFormatter
    )
    parser.add_argument('urls', metavar='URL', type=str, nargs='+', help="List of URL(s) to download")
    parser.add_argument('-f', '--format', type=str.lower, choices=formats_ext, default=default_config['format'],
                        help="Audio output format")
    parser.add_argument('-q', '--quality', type=int, default=default_config['quality'],
                        help="Audio quality: VBR (best: 0 - worst: 9) or CBR (e.g. 256)")
    parser.add_argument('-p', '--base-path', type=str, default=os.getcwd(), help="Base output path (default is current working directory)")
    parser.add_argument('-o', '--output-template', type=str, default=default_config['output_template'],
                        help="Output template for downloaded songs")
    parser.add_argument('-a', '--archive', type=str, help="Path to file that keeps record of the downloaded songs")
    parser.add_argument('-b', '--batch', action='store_true', help="R|Treat URL arguments as paths to files containing a list of URLs or IDs (one per line)" +
                                                                   "\nSpecify \"-\" for input to be taken from console (stdin)")
    parser.add_argument('--account-headers', type=str, help="R|Path to file containing authentication headers" +
                                                    "\nAllows special URL placeholder values to be used.")
    parser.add_argument('--write-json', action='store_true',
                        help="Write JSON with information about each song (follows output template)")
    parser.add_argument('--cover-format', type=str.lower, choices=cover_formats, default=default_config['cover_format'],
                        help=f"Set the cover image format (png or jpg)")
    parser.add_argument('--write-cover', action='store_true',
                        help="Write each song's album cover to a file (follows output template)")
    parser.add_argument('--write-lyrics', action='store_true',
                        help="Write each song's lyrics to a file (follows output template)")
    parser.add_argument('--no-lyrics', action='store_true', help="Don't obtain lyrics")
    parser.add_argument('--skip-existing', action='store_true', help="Skip over existing files")
    parser.add_argument('--skip-download', action='store_true', help="Skip downloading songs")
    parser.add_argument('--download-limit', type=int, default=default_config['download_limit'], help="Limit the number of songs to be downloaded in an instance")
    parser.add_argument('--playlist-limit', type=int, default=default_config['playlist_limit'], help="Limit the number of songs to be downloaded from a playlist")
    parser.add_argument('--skip-already-archive-message', action='store_true', default=default_config['skip_already_archive_message'],
                        help="Disables the \"Song is already in archive, skipping it...\" message")
    parser.add_argument('-v', '--verbose', action='store_true', help="Show all debug messages on console and log")
    parser.add_argument('--log', type=str, help="Path to verbose log output file")
    parser.add_argument('--log-verbose', action='store_true', help="Save all debug messages to the log")
    parser.add_argument('--about', action='store_true', help="Display version information (must specify at least one (dummy) URL)")

    args = vars(parser.parse_args())


# Set up logging
def setup_logging():
    global log
    log = logging.getLogger("YTMusicDL")
    log.setLevel(default_config['default_log_level'])

    log_handler = logging.StreamHandler(sys.stdout)
    log_handler.setLevel(default_config['default_log_level'])
    log_formatter = logging.Formatter('%(levelname)s: %(message)s')
    log_handler.setFormatter(log_formatter)
    log.addHandler(log_handler)


# Set up statistics
def setup_stats():
    global stats
    stats['start_time'] = datetime.now()
    log.debug('Statistics started! Start time: ' + str(stats['start_time'].strftime(default_config['datetime_format'])))


def finish_stats():
    stats['end_time'] = datetime.now()
    stats['duration'] = stats['end_time'] - stats['start_time']
    log_msg = "Processed: "
    if stats['playlists'] > 0:
        log_msg += str(stats['playlists']) + " playlist" + ("s" if stats['playlists'] != 1 else "") + ", "
    if stats['albums'] > 0:
        log_msg += str(stats['albums']) + " album" + ("s" if stats['albums'] != 1 else "") + ", "
    log_msg += str(stats['songs']) + " song" + ("s" if stats['songs'] != 1 else "") + " in "
    secs = stats['duration'].total_seconds()
    if secs > 59:
        mins = math.floor(secs / 60)
        log_msg += str(mins) + " minute" + ("s" if mins != 1 else "") + " and "
        secs -= mins * 60
    log_msg += str(math.floor(secs)) + " second" + ("s" if secs != 1 else "")
    if stats['errors'] > 0 or stats['warnings'] > 0:
        log_msg += " with "
    if stats['errors'] > 0:
        log_msg += str(stats['errors']) + " error" + ("" if stats['errors'] == 1 else "s")
        if stats['warnings'] > 0:
            log_msg += " and "
    if stats['warnings'] > 0:
        log_msg += str(stats['warnings']) + " warning" + ("" if stats['warnings'] == 1 else "s")
    log.info(log_msg)


def check_args():
    global args

    # Enable verbose logging for all handlers
    if args['verbose'] or args['log_verbose']:
        log.setLevel(logging.DEBUG)
    if args['verbose']:
        for handler in log.handlers:
            handler.setLevel(logging.DEBUG)

    # Check if base path is relative or absolute
    if not os.path.isabs(args['base_path']):
        # If relative, turn it into an absolute path
        args['base_path'] = os.path.join(os.getcwd(), args['base_path'])

    # If base path doesn't exist, create it
    if not os.path.isdir(args['base_path']):
        try:
            os.mkdir(args['base_path'])
        except Exception:
            log.error("Could not open base path! Execution halted!")
            log.debug(format_exc())
            exit()

    # Set up logging to file
    if args['log']:
        log_handler = logging.FileHandler(combine_path_with_base(args['log']), encoding='utf-8')
        if args['verbose'] or args['log_verbose']:
            log_handler.setLevel(logging.DEBUG)
        log_formatter = logging.Formatter('[%(asctime)s :: %(levelname)s :: %(filename)s :: %(funcName)s]:\n%(message)s\n')
        log_handler.setFormatter(log_formatter)
        log.addHandler(log_handler)

    # Check the output template
    if not check_output_template(args['output_template']):
        log.error("Specified output template: " + args['output_template'] + " is invalid.")
        exit()


# Write dict to JSON file
def write_out_json(my_dict, file_name):
    try:
        s = json.dumps(my_dict, indent=2)
        with open(file_name, 'w') as fo:
            fo.write(s)
            fo.close()
        return s
    except Exception:
        log.error("Failed to write JSON!")
        log.debug(format_exc())
        stats['errors'] += 1
        return


def sanitize_filename(filename: str, replace: chr = default_config['file_sanitize_replace_chr']):
    allowed_chars = ' .,!@#$()[]-+=_'
    new_fn = ''
    for char in filename:
        if char.isalnum() or char in allowed_chars:
            new_fn += char
        else:
            new_fn += replace
    new_fn.strip()
    if new_fn[-1] == '.':
        new_fn = new_fn[:-1]
    return new_fn


def check_output_template(templ: str):
    # Check the output template for any errors:
    if not templ.endswith('.{ext}'):
        log.error("Template string must end with '.{ext}'!")
        return False
    if templ.count('{') != templ.count('}'):
        # Number of opened brackets is not equal to number of closed brackets
        return False
    i = 0
    while i < len(templ):
        if templ[i] == '{':
            open_pos = i  # Position in string where bracket was open
            close_pos = templ.find('}', i + 1)  # Position where bracket is closed
            if close_pos == -1 or open_pos == close_pos - 1:
                # Bracket is not closed or there is nothing between the brackets
                return False
            keys = templ[open_pos + 1:close_pos]
            if '{' in keys:
                # Another bracket is opened inside the pair
                return False
            i = close_pos
        i += 1
    return True


def parse_output_template(templ_str: str, extension: str, song: dict):
    # Generate dict of values for the template
    templ_values = dict()
    # Parse values for song data
    for key in song.keys():
        if key not in ['artists', 'album', 'lyrics', 'lyrics_source', 'playlist', 'cover'] \
                and key is not list and key is not dict:
            templ_values['song_' + key] = str(song[key])
    # Parse artists separately
    if 'artists' in song.keys() and len(song['artists']) > 0:
        templ_values['song_artist'] = song['artists'][0]['name']  # First artist only
        templ_values['song_artists'] = join_artists(song['artists'], default_config['filename_separator'])

    # Parse values for album data
    if 'album' in song.keys():
        album = song['album']
        for key in album.keys():
            if key not in ['artists', 'songs', 'cover'] and key is not list and key is not dict:
                templ_values['album_' + key] = str(album[key])
        # Parse artists separately
        if 'artists' in album.keys() and len(album['artists']) > 0:
            templ_values['album_artist'] = album['artists'][0]['name']  # First artist only
            templ_values['album_artist'] = join_artists(album['artists'])

    # Parse values for playlist data
    if 'playlist' in song.keys():
        playlist = song['playlist']
        for key in playlist.keys():
            if key not in ['authors', 'songs', 'description'] and key is not list and key is not dict:
                templ_values['playlist_' + key] = str(playlist[key])
        # Parse authors separately
        if 'authors' in playlist.keys() and len(playlist['authors']) > 0:
            templ_values['playlist_author'] = playlist['authors'][0]['name']  # First author only
            templ_values['playlist_authors'] = join_artists(playlist['authors'], default_config['filename_separator'])

    # Additional values
    templ_values['date_time'] = templ_values['datetime'] = datetime.now().strftime(default_config['datetime_format'])
    templ_values['date'] = datetime.now().strftime(default_config['date_format'])
    templ_values['time'] = datetime.now().strftime(default_config['time_format'])

    # Sanitize all template values for file names
    for key, value in templ_values.items():
        templ_values[key] = sanitize_filename(str(value))

    # Extension shall not be sanitized
    templ_values['ext'] = extension

    # log.debug("Output template values: " + str(templ_values))

    # Parse the string manually
    # We assume the template is correct, as it has been checked previously
    parsed_str = ''
    i = 0
    while i < len(templ_str):
        if templ_str[i] == '{':
            # Find bracket open-close pair
            open_pos = i
            close_pos = templ_str.find('}', i + 1)
            keys = templ_str[open_pos+1:close_pos]
            after = ''
            # '+' operator specifies text to be added after a valid parameter
            # Must be preceded by '|' to work (last key in list is empty)
            if '+' in keys:
                keys = keys.split('+')
                after = keys[1]
                keys = keys[0]
            keys = keys.split('|')
            val = None
            for key in keys:
                if key in templ_values:
                    val = templ_values[key]
                    break
            if not val:
                if keys[-1] == '':
                    # The last key is empty and the previous keys haven't matched
                    # Supress the placeholder string
                    val = ''
                    after = ''
                else:
                    # No key has matched to available params, using placeholder instead
                    val = default_config['unknown_placeholder']
            parsed_str += val + after
            # Jump to the closing bracket position
            i = close_pos
        else:
            parsed_str += templ_str[i]
        i += 1
    return parsed_str


def combine_path_with_base(path: str):
    if os.path.isabs(path):
        return path
    return os.path.join(os.path.expandvars(args['base_path']), path)


def load_archive():
    global archive
    archive = list()
    if not args['archive']:
        return False
    archive_fname = combine_path_with_base(args['archive'])
    if os.path.exists(archive_fname):
        try:
            with open(archive_fname, 'r') as file:
                archive = file.read().splitlines()
                log.debug("Load Archive: File: \"" + str(archive_fname) + "\" loaded successfully!")
                file.close()
            return True
        except Exception:
            log.error("Load Archive: failed to open archive file!")
            log.debug(format_exc())
            return False


def in_archive(song_id: str, show_message: bool = True):
    global archive
    if args['archive'] and song_id in archive:
        if show_message and not args['skip_already_archive_message']:
            log.info("Song ID: " + song_id + " is already in archive, skipping it.")
        return True
    return False


def add_to_archive(song_id: str):
    global archive
    if not args['archive']:
        return False
    archive.append(song_id)
    archive_fname = combine_path_with_base(args['archive'])
    try:
        with open(archive_fname, 'a') as file:
            file.write('\n' + song_id)
            file.close()
        return True
    except Exception:
        log.error("Save Archive: failed to open archive file!")
        log.debug(format_exc())
        stats['errors'] += 1
        return False


def check_download_limit():
    global stats
    if 0 < args['download_limit'] <= stats['songs']:
        if not stats['has_notified_limit_reached']:
            log.info(f"Download limit reached: {args['download_limit']}!")
            stats['has_notified_limit_reached'] = True
        return True
    return False


# Join artist list with defined separator
def join_artists(artists: list, separator: str = default_config['artist_separator']):
    artist_names = list()
    for artist in artists:
        artist_names.append(artist['name'])
    return separator.join(artist_names)


# Join song information with album information
def join_song_album(song: dict, album: dict):
    album_info = album.copy()
    if 'songs' in album_info:
        album_info.pop('songs')
    song_info = song.copy()
    song_info['album'] = album_info
    return song_info


# Join song information with playlist information
# For use when calling download_audio from download_playlist
def join_song_playlist(song: dict, playlist: dict):
    playlist_info = playlist.copy()
    if 'songs' in playlist_info:
        playlist_info.pop('songs')
    song_info = song.copy()
    song_info['playlist'] = playlist_info
    return song_info


def load_album_yt_playlist(album_playlist_id: str):
    album_yt_playlist = dict()
    log.debug("Loading album playlist from YT: " + str(album_playlist_id) + "...")
    album_playlist_url = "https://youtube.com/playlist?list=" + str(album_playlist_id)
    ytdl_config = {'extract_flat': True, 'quiet': True}
    with YoutubeDL(ytdl_config) as ytdl:
        album_playlist = ytdl.extract_info(album_playlist_url, download=False)
        if 'entries' in album_playlist:
            index = 0
            for entry in album_playlist['entries']:
                index += 1
                if entry['id']:
                    album_yt_playlist['track' + str(index)] = {
                        'index': index,
                        'id': entry['id'],
                        'title': entry['title']
                    }
    # log.debug(json.dumps(album_yt_playlist))
    return album_yt_playlist if len(album_yt_playlist) > 0 else None


def get_album(album_id: str, return_original_request: bool = False):
    log.debug("Getting information for album ID: " + album_id + "...")
    # Get album information
    album = dict()
    album_info = dict()
    album_info['id'] = album_id

    data_album = None
    try:
        data_album = ytm.get_album(album_info['id'])
    except Exception:
        log.error("API Error: album request failed for album ID " + album_info['id'] + ".")
        log.debug(format_exc())
        stats['errors'] += 1
        return

    if data_album:
        album_info['title'] = data_album['title']
        album_info['type'] = data_album['type']
        album_info['year'] = data_album['year']
        album_info['duration'] = data_album['duration']
        if 'description' in data_album:
            album_info['description'] = data_album['description']
        album_info['total'] = data_album['trackCount']
        album_info['artists'] = data_album['artists']

        # Get the largest song cover/thumbnail (always the last in the dict)
        if 'thumbnails' in data_album:
            album_info['cover'] = data_album['thumbnails'][-1]['url']

        album['album'] = album_info
        if return_original_request:
            album['original_request'] = data_album

        log.debug("Title: " + str(album_info['title']) + ", Artists: " + str(join_artists(
            album_info['artists'])) + ", Total: " + str(album_info['total']))
        return album


def get_song(song_id: str, get_album_info: bool = True, track_index: int = None, show_info: bool = True):
    # Get song info from its ID
    log.debug(f"Getting details about song ID: {song_id}")
    song = dict()
    song['id'] = song_id

    # Get watch playlist for specific song ID
    # We need this to get most of the song info
    data_wp = None
    try:
        data_wp = ytm.get_watch_playlist(song_id)
    except Exception:
        log.error(f"API Error: getting watch playlist for song ID {song_id} failed!")
        log.debug(format_exc())
        stats['errors'] += 1
        return

    # Find our track in the watch playlist response
    data_track = None
    if data_wp and 'tracks' in data_wp:
        for data_track in data_wp['tracks']:
            if data_track['videoId'] == song_id:
                break

    if not data_track:
        log.error(f"API Error: bad response from watch playlist request for song ID: {song_id}!")
        stats['errors'] += 1
        return
    try:
        # Copy data from API response to our song dict
        song['title'] = data_track['title']
        song['duration'] = data_track['length']
        if 'year' in data_track:
            song['year'] = data_track['year']

        # Song type: 'Song' or 'Video'
        if data_track['videoType'] in song_types.keys():
            song['type'] = song_types[data_track['videoType']]

        # Add artists collection
        song['artists'] = data_track['artists']

        # Get the largest song cover/thumbnail (always the last in the dict)
        if 'thumbnail' in data_track:
            song['cover'] = data_track['thumbnail'][-1]['url']

        # Get lyrics data from lyric API
        if not args['no_lyrics'] and 'lyrics' in data_wp and data_wp['lyrics']:
            log.debug("Song has lyrics available")
            try:
                data_lyrics = ytm.get_lyrics(data_wp['lyrics'])
                if 'lyrics' in data_lyrics:
                    log.debug("Song lyrics added successfully!")
                    song['lyrics'] = data_lyrics['lyrics']
                    song['lyrics_source'] = data_lyrics['source']
            except Exception:
                log.error(f"API Error: lyrics request error for song ID {song_id}!")
                log.debug(format_exc())
                stats['errors'] += 1

        # Add album information (only for songs)
        if get_album_info and 'album' in data_track and song['type'] == 'Song':
            log.debug("Requesting album information for song...")
            # Find the album related data the hard way
            album = get_album(data_track['album']['id'], True)
            if album:
                song['album'] = album['album']
                data_album = album['original_request']

                track_count = 0
                track_found = 0
                # Find track in album to get its index
                log.debug("Finding song in album to get it's index")
                for album_track in data_album['tracks']:
                    track_count += 1
                    if album_track['videoId'] == song['id']:
                        track_found = track_count
                        break
                if track_found == 0:
                    # If track not found by ID, find by name
                    # Happens when track in album is a video instead of song
                    log.debug("Finding song in album using alternative method 1")
                    track_count = 0
                    for album_track in data_album['tracks']:
                        track_count += 1
                        if album_track['title'] == song['title']:
                            track_found = track_count
                            break
                if track_found == 0:
                    # Last hope of finding track: by length
                    log.debug("Finding song in album using alternative method 2")
                    track_count = 0
                    for album_track in data_album['tracks']:
                        track_count += 1
                        if album_track['duration'] == song['duration']:
                            track_found = track_count
                            break

                if track_found > 0:
                    # Hooray, we found the track on the album
                    song['index'] = track_found
                else:
                    # I'm done with this, I give up :(
                    log.debug("Unable to determine song index, defaulting to 1")
                    song['index'] = 1
            else:
                log.error(f"Failed to get album data about song ID: {song_id} and album ID: {str(data_track['album']['id'])}!")
        elif track_index:
            song['index'] = track_index

        if show_info:
            log.info("Song data complete!")
        return song
    except Exception:
        log.error(f"Failed to get data about song ID: {song_id}!")
        log.debug(format_exc())
        stats['errors'] += 1
        return


def download_cover_art(url: str, cover_file: str = None):
    try:
        response = requests.get(url)
        img = Image.open(BytesIO(response.content))
        img_format = ('jpeg' if args['cover_format'] == 'jpg' else args['cover_format']).upper()
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format=img_format)
        if cover_file:
            try:
                img.save(cover_file, format=img_format)
                log.info(f"Download Art: Cover art saved: {cover_file}")
            except Exception:
                log.error(f"Download Art: Failed to write cover art to file: {cover_file}")
                log.debug(format_exc())
                stats['errors'] += 1
        img_byte_arr = img_byte_arr.getvalue()
        return img_byte_arr
    except Exception:
        log.error("Download Art: Failed to get cover art!")
        log.debug(format_exc())
        stats['errors'] += 1
        return


def download_audio(song: dict, show_info: bool = True):
    if in_archive(song['id']):
        return 'skip_archive'

    if check_download_limit():
        return 'skip_download_limit'

    if show_info:
        log.info(f"Downloading song: {song['title']} - {join_artists(song['artists'])} [{song['id']}]...")

    out_format = formats_ytdlp[args['format']]
    # Output template of YT DLP must end in '%(ext)s' otherwise FFMPEG will fail.
    out_file_rel = str(parse_output_template(args['output_template'], '%(ext)s', song))
    out_file = str(combine_path_with_base(out_file_rel))
    out_file_ext_rel = out_file_rel % {'ext': args['format']}
    out_file_ext = str(combine_path_with_base(out_file_ext_rel))

    log.debug(f'Output filename: "{out_file_rel}", output filename with extension: "{out_file_ext_rel}"')

    if os.path.exists(out_file_ext):
        if args['skip_existing']:
            log.info(f"Output file already exists: {out_file_ext_rel}, skipping over it!")
            return 'skip_existing'
        if not os.path.isfile(out_file_ext):
            log.warning(f"Output file already exists: {out_file_ext_rel}, is a directory or link, skipping over it!")
            stats['warnings'] += 1
            return 'skip_existing'
        else:
            log.warning(f"Output file already exists: {out_file_ext_rel}, it will be overwritten!")
            stats['warnings'] += 1
            # Delete file before writing over
            try:
                os.remove(out_file_ext)
            except Exception:
                log.error(f"Failed to delete existing file: {out_file_ext_rel}, file is either in use or you do not have enough permissions to delete it.")
                stats['errors'] += 1
                return 'fail_ioerr'

    cover_bin = None
    if 'cover' in song:
        cover_file = None
        if args['write_cover']:
            cover_file = out_file % {'ext': args['cover_format']}
        cover_bin = download_cover_art(song['cover'], cover_file)

    if args['write_json']:
        if write_out_json(song, out_file % {'ext': 'json'}):
            if show_info:
                log.info("Song data JSON written successfully!")

    if args['write_lyrics']:
        if 'lyrics' in song and song['lyrics']:
            try:
                with open(out_file % {'ext': 'txt'}, 'w') as fo:
                    fo.write(song['lyrics'] + "\n\nLyrics " + song['lyrics_source'])
                    fo.close()
            except Exception:
                log.error("Failed to write lyrics to file!")
                stats['errors'] += 1
        else:
            log.warning("Lyrics unavailable!")
            stats['warnings'] += 1

    if not args['skip_download']:
        ytdlp_options = {
            'format': out_format + '/bestaudio/best',
            'quiet': default_config['supress_ytdlp_output'],
            'outtmpl': out_file,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': out_format,
                'preferredquality': args['quality']
            }]
        }
        try:
            with YoutubeDL(ytdlp_options) as ytdlp:
                error_code = ytdlp.download(song['id'])
            if error_code or not os.path.exists(out_file_ext):
                log.error(f"Failed to download song ID: {song['id']} from YouTube!")
                stats['errors'] += 1
                return 'fail_download'
        except Exception:
            log.error(f"Failed to download song ID: {song['id']} from YouTube!")
            log.debug(format_exc())
            stats['errors'] += 1
            return 'fail_download'

        try:
            # Add metadata to song file
            song_metadata = music_tag.load_file(out_file_ext)

            song_comment = f"Song ID: {str(song['id'])}\n"
            if 'type' in song:
                song_comment += f"Type: {str(song['type'])}\n"
            song_metadata['track_title'] = song['title']
            song_metadata['artist'] = str(join_artists(song['artists']))

            if 'year' in song:
                song_metadata['year'] = str(song['year'])

            if 'lyrics' in song and song['lyrics']:
                lyrics_str = str(song['lyrics'])
                if song['lyrics_source']:
                    lyrics_str += f"\n\nLyrics {str(song['lyrics_source'])}"
                song_metadata['lyrics'] = lyrics_str

            if 'album' in song:
                song_comment += f"Album ID: {str(song['album']['id'])}\n"
                song_comment += f"Album Type: {str(song['album']['type'])}\n"
                song_metadata['album'] = str(song['album']['title'])
                song_metadata['album_artist'] = str(join_artists(song['album']['artists']))
                song_metadata['year'] = str(song['album']['year'])
                song_metadata['total_tracks'] = song['album']['total']
                song_metadata['track_number'] = song['index']

            # Add cover art
            if cover_bin:
                song_metadata['artwork'] = cover_bin

            # Add comment with details
            song_metadata['comment'] = song_comment

            # Save everything
            song_metadata.save()
            add_to_archive(song['id'])
            stats['songs'] += 1
            if show_info:
                log.info(f"Song downloaded successfully!")
            return 'ok_download'
        except Exception:
            log.error(f"Failed to add metadata to file: {out_file_ext_rel}!")
            log.debug(format_exc())
            return 'fail_metadata'
    else:
        log.info("Download skipped as specified by '--skip-download' argument!")
        stats['songs'] += 1
        add_to_archive(song['id'])
        return 'skip_download'


def download_song(song_id: str, show_info: bool = True):
    if in_archive(song_id):
        return
    song = get_song(song_id, show_info=False)
    if song:
        download_audio(song, show_info=show_info)


def download_album_with_songs(album_id: str):
    # Get album with songs
    log.debug(f"Getting album ID: {album_id} and its songs...")
    album_result = get_album(album_id, True)
    if not album_result:
        return

    album_yt_playlist = None

    try:
        album_info = album_result['album'].copy()
        album = album_result['album'].copy()
        album['songs'] = list()
        log.info(f"Album title: {album['title']}, artists: {str(join_artists(album['artists']))}")
        track_count = 0
        # For each track in album result
        for track in album_result['original_request']['tracks']:
            track_count += 1
            if check_download_limit():
                break
            if not ('videoId' in track and track['videoId']):
                log.error(f"Failed to get data about album song {str(track_count)}: invalid or missing ID, song may be unavailable, skipping it...")
                stats['errors'] += 1
                continue
            song_id = str(track['videoId'])
            try:
                if in_archive(song_id):
                    continue
                # Try to get song info
                log.debug(f"Getting song ID: {song_id}...")
                song = get_song(song_id, get_album_info=False, track_index=track_count, show_info=False)
                if not song:
                    log.error(f"Failed to get data about song ID: {song_id}, skipping it...")
                    stats['errors'] += 1
                song_to_dl = song
                song_2 = None
                # If track in album is a music video, attempt to retrieve album version
                if song['type'] == 'Video' and default_config['album_song_instead_of_video']:
                    # Loading YT playlist:
                    if not album_yt_playlist:
                        album_playlist_id = album_result['original_request']['audioPlaylistId']
                        album_yt_playlist = load_album_yt_playlist(album_playlist_id)
                    # Get audio counterpart ID from YT playlist
                    if album_yt_playlist:
                        track_key = 'track' + str(track_count)
                        if track_key in album_yt_playlist:
                            song_2_id = album_yt_playlist[track_key]['id']
                            log.info(f"Song ID: {song_id} is a video, found its audio counterpart ID: {song_2_id}")
                            song_2 = get_song(song_2_id, get_album_info=False, track_index=track_count, show_info=False)
                        else:
                            log.debug(f"Track key: {track_key} not found in YT playlist!")
                    if not song_2:
                        log.warning("Song ID: " + song['id'] + " is a video, failed to find its audio counterpart, using video version instead!")
                        stats['warnings'] += 1
                elif song['type'] == 'Video' and not default_config['album_song_instead_of_video']:
                    log.info("Song ID: " + song_id + " is a video, but since 'album_song_instead_of_video' is set to false in config the video version will be used.")

                song_title = song_2['title'] if song_2 else song['title']
                log.info(f"Downloading album song {str(track_count)}: {song_title}...")

                download_ok = False
                if song_2:
                    # Download found audio counterpart
                    log.debug("Trying to download audio counterpart song...")
                    result = download_audio(join_song_album(song_2, album_info))
                    if result.startswith('fail'):
                        log.warning("Failed to download audio counterpart, reverting to video version!")
                    else:
                        download_ok = True
                        album['songs'].append(song_2)

                if not download_ok:
                    # Download song with ID from album
                    download_audio(join_song_album(song, album_info))
                    album['songs'].append(song)

                continue
            except Exception:
                log.error("Failed to download album song " + str(track_count) + ": " + song_id + " !")
                log.debug(format_exc())
                stats['errors'] += 1
                continue
        log.debug("Album and song data complete!")
        stats['albums'] += 1
        return album
    except Exception:
        log.error("Failed to download album ID: " + album_id + " !")
        log.debug(format_exc())
        stats['errors'] += 1
        return


def download_playlist(playlist_id: str, limit: int = default_config['playlist_limit']):
    playlist = dict()
    playlist['id'] = playlist_id
    data_playlist = None
    try:
        if playlist_id == "LM":
            # Get liked songs playlist
            data_playlist = ytm.get_liked_songs(limit=limit)
        else:
            data_playlist = ytm.get_playlist(playlist_id, limit=limit)
    except Exception:
        log.error("Get Playlist: API request failed for playlist ID: " + playlist_id)
        log.debug(format_exc())
        stats['errors'] += 1
        return

    if not data_playlist:
        return

    try:
        playlist['title'] = str(data_playlist['title'])
        if 'author' in data_playlist:
            playlist['authors'] = list()
            if data_playlist['author'] is dict:
                playlist['authors'].append(str(data_playlist['author']))
            elif data_playlist['author'] is list:
                playlist['authors'] = str(data_playlist['author'])
        if 'year' in data_playlist:
            playlist['year'] = data_playlist['year']
        if 'duration' in data_playlist:
            playlist['duration'] = str(data_playlist['duration'])
        playlist['total'] = data_playlist['trackCount']
        playlist['visibility'] = str(data_playlist['privacy'])
        if 'description' in data_playlist and data_playlist['description']:
            playlist['description'] = str(data_playlist['description'])

    except Exception:
        log.error("Failed to get information about playlist ID: " + playlist_id + " !")
        log.debug(format_exc())
        stats['errors'] += 1
        return

    try:
        log.info("Downloading songs from playlist ID: " + playlist['id'] + " title: " + playlist['title'] + "...")
        playlist['songs'] = list()
        track_count = 0
        track_successful = 0
        for track in data_playlist['tracks']:
            track_count += 1
            if track_count > limit:
                log.info("Playlist limit reached: " + str(limit) + "!")
                break
            if check_download_limit():
                break
            if not('videoId' in track and track['videoId']):
                log.error("Failed to get data about playlist song: invalid or missing ID, song may be unavailable, skipping it...")
                stats['errors'] += 1
                continue
            song_id = str(track['videoId'])
            try:
                if in_archive(song_id):
                    track_successful += 1
                    continue
                log.debug("Getting song ID: " + song_id + "...")
                song = get_song(song_id, show_info=False)
                if not song:
                    log.error("Failed to get data about song ID: " + song_id + ", skipping it...")
                    stats['errors'] += 1
                    continue
                song['playlist_index'] = track_count
                log.debug("Downloading playlist song " + str(track_count) + ": " + song['title'] + " - " + join_artists(song['artists']) + "...")
                playlist['songs'].append(song)
                # Add playlist information to download audio
                result = download_audio(join_song_playlist(song, playlist))
                if result.startswith('ok') or result.startswith('skip'):
                    track_successful += 1
            except Exception:
                log.error("Failed to get data about song ID: " + song_id + ", skipping it...")
                log.debug(format_exc())
                stats['errors'] += 1

        if track_successful > 0:
            log.info("Playlist ID: " + playlist['id'] + " title: " + playlist['title'] + " downloaded successfully!")
        else:
            log.error("Failed to download songs from playlist ID: " + playlist['id'] + " title: " + playlist['title'] + "!")
        stats['playlists'] += 1
        return playlist
    except Exception:
        log.error("Failed to download songs from playlist ID: " + playlist_id + "!")
        log.debug(format_exc())
        stats['errors'] += 1
        return


def parse_url(url: str):
    url_props = dict()
    url_props['original'] = url

    # Check if string is a valid URL
    if url.startswith('https://') or url.startswith('http://'):
        url_props['is_url'] = True
        parsed_url = urlparse(url)
        if parsed_url.hostname.count('youtube.com') != 1:
            log.error(f"Parse URL: Invalid URL Address: {url}!")
            stats['errors'] += 1
            return
        parsed_qs = parse_qs(parsed_url.query)
        if 'watch' in url and 'v' in parsed_qs:
            # Watch URL for songs
            url_props['id'] = url_props['song_id'] = parsed_qs['v'][0]
        elif 'playlist' in url and 'list' in parsed_qs:
            # Playlist URL for playlists
            url_props['id'] = url_props['playlist_id'] = parsed_qs['list'][0]
        elif 'browse' in url:
            # Browse url is for album IDs (starting with 'MPREb_')
            url_props['id'] = parsed_url.path.rsplit('/', 1)[-1]
        else:
            log.error(f"Parse URL: Invalid URL Address: {url}!")
            stats['errors'] += 1
            return
    else:
        # Assume given string is a plain ID
        if any(char in url for char in " /\\'\"!@#$%^&*()`~+=[]{};:,.<>?"):
            log.error(f"Parse URL: Invalid ID string: {url}!")
            stats['errors'] += 1
            return
        url_props['is_url'] = False
        url_props['id'] = url

    if url_props['id'].startswith('PLLL') or url_props['id'] == "LM":
        # ID represents a playlist
        url_props['type'] = 'Playlist'
    elif url_props['id'].startswith('OLAK5uy_'):
        # ID represents an album playlist
        # Get the album playlist ID for downloading
        url_props['type'] = 'Album Playlist'
        try:
            album_id = ytm.get_album_browse_id(url_props['playlist_id'])
            if album_id:
                url_props['type'] = 'Album'
                url_props['id'] = album_id
        except Exception:
            log.warning(f"Parse URL: Failed to get album browse ID for playlist ID: {url_props['id']}, using playlist ID instead")
            log.debug(format_exc())
            stats['warnings'] += 1
    elif url_props['id'].startswith('MPREb_'):
        # ID represents an album
        url_props['type'] = 'Album'
    else:
        # ID represents a song
        url_props['type'] = 'Song'
    return url_props


# Returns list of URLs from console
def parse_from_stdin():
    print("Type in URLs or IDs to download, separated by new lines.\nSubmit blank line to confirm.")
    in_str = 'ignore'
    in_lines = list()
    while in_str:
        in_str = input()
        if in_str:
            in_lines.append(in_str)
    return in_lines


# Returns list of URLs from file
def parse_batch(batch_file: str):
    log.debug(f"Loading batch file: {batch_file} ...")
    batch_file_abs = combine_path_with_base(batch_file)
    # Check if file exists and is valid
    if not os.path.exists(batch_file_abs):
        log.error(f"Batch file: {batch_file} does not exist!")
        stats['errors'] += 1
        return
    if not os.path.isfile(batch_file_abs):
        log.error(f"Batch file: {batch_file} is not a file!")
        stats['errors'] += 1
        return

    batch_file_lines = None
    try:
        with open(batch_file_abs, 'r') as fin:
            batch_file_lines = fin.readlines()
    except Exception:
        log.error(f"Failed to open batch file: {batch_file} !")
        log.debug(format_exc())
        stats['errors'] += 1
        return

    log.info(f"Batch file: {batch_file} loaded successfully!")
    return batch_file_lines


def parse_special_account(key: str):
    urls = []
    if not args['account_headers']:
        return
    if key == 'library_playlists':
        try:
            log.info("Loading playlists from account library...")
            limit = default_config['library_limit']
            if args['download_limit'] != default_config['download_limit']:
                limit = args['download_limit']
            library_playlists = ytm.get_library_playlists(limit=limit)
            for playlist in library_playlists:
                if 'playlistId' in playlist and playlist['playlistId'] != "LM":
                    urls.append(playlist['playlistId'])
        except Exception:
            log.warning(f"Failed to get playlists from account library!")
            log.debug(format_exc())
            stats['errors'] += 1
    elif key == 'library_albums':
        try:
            log.info("Loading albums from account library...")
            library_albums = ytm.get_library_albums(limit=default_config['library_limit'], order=default_config['library_order'])
            for album in library_albums:
                if 'browseId' in album:
                    urls.append(album['browseId'])
        except Exception:
            log.warning(f"Failed to get playlists from account library!")
            log.debug(format_exc())
            stats['errors'] += 1
    elif key == 'library_songs':
        try:
            log.info("Loading songs from account library...")
            limit = default_config['library_songs_limit']
            if args['download_limit'] != default_config['download_limit']:
                limit = args['download_limit']
            library_songs = ytm.get_library_songs(limit=limit, order=default_config['library_order'])
            for song in library_songs:
                if 'videoId' in song and ('isAvailable' in song or song['isAvailable']):
                    urls.append(song['videoId'])
        except Exception:
            log.warning(f"Failed to get playlists from account library!")
            log.debug(format_exc())
            stats['errors'] += 1
    elif key == 'liked_songs':
        urls.append("LM")

    if len(urls) == 0:
        return
    return urls


def main():
    print(f"YouTube Music Downloader, version {__version}")
    setup_logging()
    setup_argparse()

    if args['about']:
        print("YouTube Music Downloader by RaduTek")
        print("https://github.com/RaduTek/YTMusicDL")

    check_args()

    global ytm

    # Open account headers
    if args['account_headers']:
        account_headers_path = combine_path_with_base(args['account_headers'])
        if os.path.isfile(account_headers_path):
            ytm = YTMusic(auth=account_headers_path)

    if not ytm:
        ytm = YTMusic()

    if args['archive']:
        load_archive()

    urls = list()
    if args['batch']:
        # Treat URL arguments as paths to batch files
        for batch in args['urls']:
            b_urls = parse_from_stdin() if batch == '-' else parse_batch(batch)
            if b_urls and len(b_urls) > 0:
                # Parse URLs from the batch file
                for url in b_urls:
                    parsed = parse_url(url)
                    if parsed:
                        urls.append(parsed)
    else:
        # Parse given URLs
        for url in args['urls']:
            parsed_special = parse_special_account(url)
            if parsed_special:
                for url2 in parsed_special:
                    parsed = parse_url(url2)
                    if parsed:
                        urls.append(parsed)
            else:
                parsed = parse_url(url)
                if parsed:
                    urls.append(parsed)

    # Start statistics timer after URLs have been entered
    setup_stats()

    # Recreate YTM object to not make more API calls on user ID
    # Just in case it may cause issues
    if args['account_headers']:
        ytm = YTMusic()

    for url in urls:
        if check_download_limit():
            break
        if url['type'] == 'Song':
            download_song(url['id'])
        elif url['type'] == 'Playlist':
            download_playlist(url['id'], args['playlist_limit'])
        elif url['type'] == 'Album':
            download_album_with_songs(url['id'])

    finish_stats()


if __name__ == '__main__':
    main()
