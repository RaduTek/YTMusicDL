import math
from typing import Dict, Any, List
import json
import logging
import sys
from datetime import datetime
import argparse
import os
import io
import requests
import music_tag
from PIL import Image
from io import BytesIO
from ytmusicapi import YTMusic
from yt_dlp import YoutubeDL
from urllib.parse import urlparse
from urllib.parse import parse_qs


# Configuration and declarations

# Default configuration
config = {
    # Gets album song instead of video when downloading album
    'default_log_level': logging.INFO,
    'album_song_instead_of_video': True,
    'artist_separator': '; ',
    'default_format': 'opus',
    'default_quality': '0',
    'default_output_template': '{song_title} - {song_artist} [{song_id}].{ext}',
    'file_sanitize_replace_chr': '_',
    'supress_ytdlp_output': True,
    'cover_format': 'png',  # png or jpeg
    'date_format': '%d-%m-%Y',
    'time_format': '%H-%M-%S',
    'datetime_format': '%d-%m-%Y %H-%M-%S',
    'unknown_placeholder': "Unknown"
}

formats_ext = ['opus', 'm4a', 'mp3']
formats_ytdlp = {'opus': 'opus', 'm4a': 'm4a', 'mp3': 'mp3'}

song_types = {
    "MUSIC_VIDEO_TYPE_ATV": 'Song',
    "MUSIC_VIDEO_TYPE_OMV": 'Video',
    "MUSIC_VIDEO_TYPE_UGC": 'Video'
}

# Schemas for each data structure
song_schema = {
    'id': str, 'title': str, 'duration': str, 'year': int,
    'type': str, 'artists': list, 'cover': str, 'lyrics': str,
    'lyrics_source': str, 'album': dict, 'index': int
}
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
ytm: YTMusic
parser: argparse.ArgumentParser
args: dict
log: logging.Logger
stats: dict
archive = list()


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
    parser.add_argument('-f', '--format', type=str, choices=formats_ext, default=config['default_format'],
                        help="Audio output format")
    parser.add_argument('-q', '--quality', type=str, default=config['default_quality'],
                        help="Audio quality: VBR (best: 0 - worst: 9) or CBR (e.g. 256k)")
    parser.add_argument('-p', '--base-path', type=str, default=os.getcwd(), help="Base output path (default is current working directory)")
    parser.add_argument('-o', '--output-template', type=str, default=config['default_output_template'],
                        help="Output template for downloaded songs")
    parser.add_argument('-a', '--archive', type=str, help="Path to file that keeps record of the downloaded songs")
    # parser.add_argument('-b', '--batch', action='store_true', help="R|Treat URL arguments as paths to files containing a list of URLs or IDs\nSpecify \"-\" for input to be taken from console (stdin).")
    parser.add_argument('--write-json', action='store_true',
                        help="Write JSON with information about song(s) (follows output template)")
    parser.add_argument('--write-cover', action='store_true',
                        help="Write each song's album cover to a file (follows output template)")
    parser.add_argument('--no-lyrics', action='store_true', help="Don't obtain lyrics")
    parser.add_argument('--skip-download', action='store_true', help="Skip downloading songs")
    parser.add_argument('--log', type=str, help="Path to verbose log output file")
    parser.add_argument('-v', '--verbose', action='store_true', help="Show all debug messages on console")
    parser.add_argument('--about', action='store_true', help="Display version information (must specify at least one (dummy) URL)")

    args = vars(parser.parse_args())


def check_args():
    global args

    # Enable verbose logging
    if args['verbose']:
        log.setLevel(logging.DEBUG)

    # Check if base path is relative or absolute
    if not os.path.isabs(args['base_path']):
        # If relative, turn it into an absolute path
        args['base_path'] = os.path.join(os.getcwd(), args['base_path'])

    # If base path doesn't exist, create it
    if not os.path.isdir(args['base_path']):
        try:
            os.mkdir(args['base_path'])
        except Exception as e:
            log.error("Could not open base path! Execution halted!")
            log.debug(str(e))
            exit()

    # Set up logging to file
    if args['log']:
        log_handler = logging.FileHandler(combine_path_with_base(args['log']))
        log_handler.setLevel(logging.DEBUG)
        log_formatter = logging.Formatter('[%(asctime)s - %(levelname)s] [%(filename)s : %(funcName)s]: %(message)s')
        log_handler.setFormatter(log_formatter)
        log.addHandler(log_handler)

    # Check the output template
    if not check_output_template(args['output_template']):
        log.error("Specified output template: " + args['output_template'] + " is invalid.")
        exit()

    # Ensure format is lower case
    args['format'] = args['format'].lower()


# Set up logging
def setup_logging():
    global log
    log = logging.getLogger("YTMusicDL")
    log.setLevel(config['default_log_level'])

    log_handler = logging.StreamHandler(sys.stdout)
    log_formatter = logging.Formatter('%(levelname)s: %(message)s')
    log_handler.setFormatter(log_formatter)
    log.addHandler(log_handler)


# Set up statistics
def setup_stats():
    global stats
    stats = {
        'songs': 0,
        'albums': 0,
        'playlists': 0,
        'errors': 0,
        'warnings': 0,
        'start_time': datetime.now(),
        'end_time': None,
        'duration': None
    }
    log.debug('Statistics started! Start time: ' + stats['start_time'].strftime(config['datetime_format']))


def finish_stats():
    stats['end_time'] = datetime.now()
    stats['duration'] = duration = stats['end_time'] - stats['start_time']
    log_msg = "Processed: "
    if stats['playlists'] > 0:
        log_msg += str(stats['playlists']) + " playlist" + ("s" if stats['playlists'] > 1 else "") + ", "
    if stats['albums'] > 0:
        log_msg += str(stats['albums']) + " album" + ("s" if stats['albums'] > 1 else "") + ", "
    log_msg += str(stats['songs']) + " song" + ("s" if stats['songs'] > 1 else "") + " in "
    secs = stats['duration'].total_seconds()
    if secs > 59:
        mins = math.floor(secs / 60)
        log_msg += str(mins) + " minute" + ("s" if mins > 1 else "") + " and "
        secs -= mins * 60
    log_msg += str(math.floor(secs)) + " second" + ("s" if secs > 1 else "")
    log.info(log_msg)


# Write dict to JSON file
def write_out_json(my_dict, file_name):
    try:
        s = json.dumps(my_dict, indent=2)
        with open(file_name, 'w') as fo:
            fo.write(s)
            fo.close()
        return s
    except Exception as e:
        log.error("Failed to write JSON!")
        log.debug(str(e))
        stats['errors'] += 1
        return


def sanitize_filename(filename: str, replace: chr = config['file_sanitize_replace_chr']):
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


def check_output_template(templ:str):
    # Check the output template for any errors:
    if not templ.endswith('.{ext}'):
        print("Template string must end with '.{ext}'!")
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
    # Generate dict of parameters for the template
    out_params = dict()
    for key in song.keys():
        if key != 'artists' and key != 'album':
            out_params['song_' + key] = sanitize_filename(str(song[key]))
    if 'artists' in song.keys() and len(song['artists']) > 0:
        out_params['song_artist'] = sanitize_filename(song['artists'][0]['name'])
    if 'album' in song.keys():
        for key in song['album'].keys():
            if key != 'artists':
                out_params['album_' + key] = sanitize_filename(str(song['album'][key]))
        if 'artists' in song['album'].keys() and  len(song['album']['artists']) > 0:
            out_params['album_artist'] = sanitize_filename(song['album']['artists'][0]['name'])
    out_params['ext'] = extension
    out_params['date_time'] = out_params['datetime'] = datetime.now().strftime(config['datetime_format'])
    out_params['date'] = datetime.now().strftime(config['date_format'])
    out_params['time'] = datetime.now().strftime(config['time_format'])

    # Parse the string manually
    # We assume the template is correct, as it has been checked previously
    out_str = ''
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
                if key in out_params:
                    val = out_params[key]
                    break
            if not val:
                if keys[-1] == '':
                    # The last key is empty and the previous keys haven't matched
                    # Supress the placeholder string
                    val = ''
                    after = ''
                else:
                    # No key has matched to available params, using placeholder instead
                    val = config['unknown_placeholder']
            out_str += val + after
            # Jump to the closing bracket position
            i = close_pos
        else:
            out_str += templ_str[i]
        i += 1
    return out_str


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
                log.debug("Load Archive: File: \"" + archive_fname + "\" loaded successfully!")
                file.close()
            return True
        except Exception as e:
            log.error("Load Archive: failed to open archive file!")
            log.debug(str(e))
            return False


def in_archive(song_id: str, show_message: bool = True):
    global archive
    if args['archive'] and song_id in archive:
        if show_message:
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
    except Exception as e:
        log.error("Save Archive: failed to open archive file!")
        log.debug(str(e))
        stats['errors'] += 1
        return False


def parse_url(url: str):
    url_props = dict()
    url_props['original'] = url

    # Check if string is a valid URL
    if url.startswith('https://') or url.startswith('http://'):
        url_props['is_url'] = True
        parsed_url = urlparse(url)
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
            log.error("Parse URL: Invalid URL Address: \"" + url + "\"!")
            stats['errors'] += 1
            return
    else:
        # Assume given string is a plain ID
        if ' ' not in url:
            url_props['is_url'] = False
            url_props['id'] = url
        else:
            log.error("Parse URL: Invalid ID string: \"" + url + "\"!")
            stats['errors'] += 1
            return

    if url_props['id'].startswith('PLLL'):
        # ID represents a playlist
        url_props['type'] = 'Playlist'
    elif url_props['id'].startswith('OLAK5uy_'):
        # ID represents an album playlist
        # Get the album playlist ID for downloading
        url_props['type'] = 'Album Playlist'
        try:
            album_id = ytm.get_album_browse_id(url_props['playlist_id'])
            url_props['type'] = 'Album'
            url_props['id'] = album_id
        except Exception as e:
            log.warning("Parse URL: Failed to get album browse ID for playlist ID: \"" + url_props[
                'id'] + "\", using playlist ID instead")
            log.debug(str(e))
            stats['warnings'] += 1
    elif url_props['id'].startswith('MPREb_'):
        # ID represents an album
        url_props['type'] = 'Album'
    else:
        # ID represents a song
        url_props['type'] = 'Song'

    return url_props


# Join artist list with defined separator
def join_artists(artists: list):
    artist_names = list()
    for artist in artists:
        artist_names.append(artist['name'])
    return config['artist_separator'].join(artist_names)


# Join song information with album information
def join_song_album(song: dict, album: dict):
    album_info = album.copy()
    if 'songs' in album_info:
        album_info.pop('songs')
    song_info = song
    song_info['album'] = album_info
    return song_info


def get_album_song_instead_of_video(album: dict, song: dict):
    # Get song ID of music video (that lurks in album result because YT Music >:( )
    # This isn't required for premium accounts with song only mode enabled
    search_query = song['title'] + " " + album['album']['title'] + " " + song['artists'][0]['name']

    search_results = None
    try:
        log.debug("Getting search results for: \"" + search_query + "\"...")
        search_results = ytm.search(search_query, filter='songs', ignore_spelling=True)
    except Exception as e:
        log.error("API Error: failed to get search results for query: " + search_query + ".")
        log.debug(str(e))
        stats['errors'] += 1
        return

    if search_results:
        for search_result in search_results:
            if 'album' in search_result and search_result['album']['id'] == album['album']['id']:
                song_id = search_result['videoId']
                log.debug("Found song ID: " + song_id + "!")
                return song_id

    # Use the YouTube album playlist to get the song ID
    # This is the last resort
    audio_playlist_id = album['original_request']['audioPlaylistId']
    log.debug("Loading album playlist from YT: " + audio_playlist_id + "...")
    album_playlist_url = "https://youtube.com/playlist?list=" + audio_playlist_id
    ytdl_config = {'extract_flat': True, 'quiet': True}
    with YoutubeDL(ytdl_config) as ytdl:
        album_playlist = ytdl.extract_info(album_playlist_url, download=False)
        if len(album_playlist['entries']) > 0:
            song_id = album_playlist['entries'][song['index'] - 1]['id']
            log.debug("Found song ID: " + song_id + "!")
            return song_id

    log.debug("Didn't find song version of music video!")
    return


def get_album(album_id: str, return_original_request: bool = False):
    log.debug("Getting information for album ID: " + album_id + "...")
    # Get album information
    album = dict()
    album_info = dict()
    album_info['id'] = album_id

    data_album = None
    try:
        data_album = ytm.get_album(album_info['id'])
    except Exception as e:
        log.error("API Error: album request failed for album ID " + album_info['id'] + ".")
        log.debug(str(e))
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

        log.debug("Title: " + album_info['title'] + ", Artists: " + join_artists(
            album_info['artists']) + ", Total: " + str(album_info['total']))
        return album


def get_song(song_id: str, get_album_info: bool = True, track_index: int = None, show_info: bool = True):
    # Get song info from its ID
    log.debug("Getting details about song ID: " + song_id)
    song = dict()
    song['id'] = song_id

    # Get watch playlist for specific song ID
    # We need this to get most of the song info
    data_wp = None
    try:
        data_wp = ytm.get_watch_playlist(song_id)
    except Exception as e:
        log.error("API Error: getting watch playlist for song ID " + song_id + " failed!")
        log.debug(str(e))
        stats['errors'] += 1
        return

    # Find our track in the watch playlist response
    data_track = None
    if data_wp and 'tracks' in data_wp:
        for data_track in data_wp['tracks']:
            if data_track['videoId'] == song_id:
                break

    if data_track:
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
            except Exception as e:
                log.error("API Error: lyrics request error for song ID " + song_id + ".")
                log.debug(str(e))
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
        elif track_index:
            song['index'] = track_index

        if show_info:
            log.info("Song: " + song['title'] + " - " + join_artists(song['artists']) + " [" + song['id'] + "] data complete!")
        return song
    else:
        log.error("API Error: bad response from watch playlist request for song ID " + song_id + ".")
        stats['errors'] += 1
        return


def download_cover_art(url: str, cover_file: str = None):
    try:
        response = requests.get(url)
        img = Image.open(BytesIO(response.content))
        img_format = config['cover_format'].upper()
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format=img_format)
        if cover_file:
            try:
                img.save(cover_file, format=img_format)
                log.info("Download Art: Cover art saved: " + cover_file)
            except Exception as e:
                log.error("Download Art: Failed to write cover art to file: " + cover_file)
                log.debug(str(e))
                stats['errors'] += 1
        img_byte_arr = img_byte_arr.getvalue()
        return img_byte_arr
    except Exception as e:
        log.error("Download Art: Failed to get cover art!")
        log.debug(str(e))
        stats['errors'] += 1
        return


def download_audio(song: dict, show_info: bool = True):
    if in_archive(song['id']):
        return 'skip_archive'

    if show_info:
        log.info("Downloading song: " + song['title'] + " - " + join_artists(song['artists']) + " [" + song['id'] + "]...")

    out_format = formats_ytdlp[args['format']]
    # Output template of YT DLP must end in '%(ext)s' otherwise FFMPEG will fail.
    out_file = parse_output_template(args['output_template'], '%(ext)s', song)
    # print("out_file=" + out_file)
    out_file = combine_path_with_base(out_file)
    out_file_ext = out_file % {'ext': args['format']}

    cover_bin = None
    if 'cover' in song:
        cover_file = None
        if args['write_cover']:
            cover_file = out_file % {'ext': config['cover_format']}
        cover_bin = download_cover_art(song['cover'], cover_file)

    if args['write_json']:
        if write_out_json(song, out_file % {'ext': 'json'}):
            if show_info:
                log.info("Song data JSON written successfully!")

    if not args['skip_download']:
        ytdlp_options = {
            'format': out_format + '/bestaudio/best',
            'quiet': config['supress_ytdlp_output'],
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
                log.error("Download Song: Failed to download song ID: " + song['id'] + " from YouTube!")
                stats['errors'] += 1
                return False
        except Exception as e:
            log.error("Download Song: Failed to download song ID: " + song['id'] + " from YouTube!")
            log.debug(str(e))
            stats['errors'] += 1
            return False

        try:
            # Add metadata to song file
            song_comment = "Song ID: " + song['id'] + "\n"
            if 'type' in song:
                song_comment += "Type: " + song['type'] + "\n"
            song_metadata = music_tag.load_file(out_file_ext)
            song_metadata['track_title'] = song['title']
            song_metadata['artist'] = join_artists(song['artists'])

            if 'year' in song:
                song_metadata['year'] = song['year']

            if 'lyrics' in song and song['lyrics']:
                song_metadata['lyrics'] = song['lyrics']
                song_comment = "Lyrics " + song['lyrics_source'] + "\n" + song_comment

            if 'album' in song:
                song_comment += "Album ID: " + song['album']['id'] + "\n"
                song_comment += "Album Type: " + song['album']['type'] + "\n"
                song_metadata['album'] = song['album']['title']
                song_metadata['album_artist'] = join_artists(song['album']['artists'])
                song_metadata['year'] = song['album']['year']
                song_metadata['total_tracks'] = song['album']['total']
                song_metadata['track_number'] = song['index']

            # Add cover art
            if cover_bin:
                song_metadata['artwork'] = cover_bin

            song_metadata['comment'] = song_comment
            song_metadata.save()

            stats['songs'] += 1
            add_to_archive(song['id'])
            if show_info:
                log.info("Song: " + song['title'] + " - " + join_artists(song['artists']) + " [" + song['id'] + "] downloaded successfully!")
            return 'download_ok'
        except Exception as e:
            log.error("Download Song: Failed to add metadata to file : \"" + out_file_ext + "\"!")
            log.debug(str(e))
            return 'metadata_fail'
    else:
        log.info("Download skipped as specified by '--skip-download' argument!")
        stats['songs'] += 1
        add_to_archive(song['id'])
        return 'skip_download'


def download_song(song_id: str, show_info: bool = True):
    song = get_song(song_id, show_info=False)
    if song:
        download_audio(song, show_info=show_info)


def download_album_with_songs(album_id: str):
    # Get album with songs
    log.debug("Getting album ID: " + album_id + " and its songs...")
    album_result = get_album(album_id, True)
    if album_result:
        album_info = album_result['album'].copy()
        album = album_result['album'].copy()
        album['songs'] = list()
        log.info("Album title: " + album['title'] + ", artists: " + join_artists(album['artists']))
        track_count = 0
        # For each track in album result
        for track in album_result['original_request']['tracks']:
            track_count += 1
            if in_archive(track['videoId']):
                continue
            # Try to get song info
            log.debug("Getting song ID: " + track['videoId'] + "...")
            song = get_song(track['videoId'], get_album_info=False, track_index=track_count, show_info=False)
            if song:
                song_2 = None
                # If track in album is a music video, attempt to retrieve album version
                if song['type'] == 'Video' and config['album_song_instead_of_video']:
                    song_2_id = get_album_song_instead_of_video(album_result, song)
                    if song_2_id:
                        log.info(
                                "Song ID: " + song['id'] + " is a video, found its audio counterpart ID: " + song_2_id)
                        song_2 = get_song(song_2_id, get_album_info=False, track_index=track_count, show_info=False)
                    else:
                        log.warning("Song ID: " + song[
                            'id'] + " is a video, failed to find its audio counterpart, using video version instead!")
                        stats['warnings'] += 1

                elif song['type'] == 'Video' and not config['album_song_instead_of_video']:
                    log.info("Song ID: " + album_id + " is a video, but since 'album_song_instead_of_video' is set to false in config the video version will be used.")

                if song_2:
                    song = song_2

                log.info("Downloading album song " + str(track_count) + ": " + song['title'] + "...")
                song_info = join_song_album(song, album_info)
                print(song_info)
                download_audio(song_info)
                album['songs'].append(song)
                continue
            else:
                log.error("Failed to get data about song ID: " + track['videoId'] + ", skipping it...")
                stats['errors'] += 1
        log.debug("Album and song data complete!")
        stats['albums'] += 1
        return album
    return


def download_playlist(playlist_id: str):
    playlist = dict()
    playlist['id'] = playlist_id
    data_playlist = None
    try:
        data_playlist = ytm.get_playlist(playlist_id, limit=5000)
    except Exception as e:
        log.error("Get Playlist: API request failed for playlist ID: " + playlist_id)
        log.debug(str(e))
        stats['errors'] += 1
        return

    if data_playlist:
        playlist['title'] = data_playlist['title']
        playlist['authors'] = list()
        if data_playlist['author'] is dict:
            playlist['authors'].append(data_playlist['author'])
        elif data_playlist['author'] is list:
            playlist['authors'] = data_playlist['author']
        playlist['year'] = data_playlist['year']
        playlist['duration'] = data_playlist['duration']
        playlist['total'] = data_playlist['trackCount']
        playlist['visibility'] = data_playlist['privacy']
        if 'description' in data_playlist and data_playlist['description']:
            playlist['description'] = data_playlist['description']

        log.info("Downloading playlist ID: " + playlist['id'] + " title: " + playlist['title'] + "...")

        playlist['songs'] = list()
        track_count = 0
        for track in data_playlist['tracks']:
            track_count += 1
            if in_archive(track['videoId']):
                continue
            log.debug("Getting song ID: " + track['videoId'] + "...")
            song = get_song(track['videoId'], show_info=False)
            if song:
                log.debug("Downloading playlist song " + str(track_count) + ": " + song['title'] + " - " + join_artists(song['artists']) + "...")
                download_audio(song)
                playlist['songs'].append(song)
            else:
                log.error("Failed to get data about song ID: " + track['videoId'] + ", skipping it...")
                stats['errors'] += 1

        log.info("Playlist ID: " + playlist['id'] + " title: " + playlist['title'] + " downloaded successfully!")
        stats['playlists'] += 1
        return playlist
    return


def main():
    print("YouTube Music Downloader")
    setup_logging()
    setup_argparse()

    if args['about']:
        print("YouTube Music Downloader by RaduTek")
        print("https://github.com/RaduTek/YTMusicDL")

    setup_stats()
    check_args()

    global ytm
    ytm = YTMusic()

    if args['archive']:
        load_archive()

    # print(args)
    urls = list()
    # Parse given URLs
    for url in args['urls']:
        urls.append(parse_url(url))
    for url in urls:
        if url['type'] == 'Song':
            download_song(url['id'])
        elif url['type'] == 'Playlist':
            download_playlist(url['id'])
        elif url['type'] == 'Album':
            download_album_with_songs(url['id'])

    finish_stats()


if __name__ == '__main__':
    main()
