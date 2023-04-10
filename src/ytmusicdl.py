import os
import utils
from localtypes import *
from config import default_config
from datetime import datetime
from yt_dlp import YoutubeDL
from ytmusicapi import YTMusic

class YTMusicDL:
    """YouTube Music Downloader class"""

    ytmusic: YTMusic
    ytdlp: YoutubeDL

    config: dict
    verbose: bool = False

    def __init__(self, ext_config: dict = dict()):
        """Create a new YTMusicDL object"""

        # Load default configuration
        self.config = default_config.copy()
        self.config.update(ext_config)

        self.verbose = self.config['verbose']

        if not os.path.isabs(self.config['base_path']):
            self.config['base_path'] = os.path.join(os.getcwd(), self.config['base_path'])

        # Spawn a ytmusicapi object with or without authentification headers
        self.ytmusic = YTMusic(auth=self.config['auth_headers'])

        return
    
    def parse_output_template(self, templ_str: str, extension: str, song: dict):
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
            templ_values['song_artists'] = utils.join_artists(song['artists'], self.config['filename_separator'])

        # Parse values for album data
        if 'album' in song.keys():
            album = song['album']
            for key in album.keys():
                if key not in ['artists', 'songs', 'cover'] and key is not list and key is not dict:
                    templ_values['album_' + key] = str(album[key])
            # Parse artists separately
            if 'artists' in album.keys() and len(album['artists']) > 0:
                templ_values['album_artist'] = album['artists'][0]['name']  # First artist only
                templ_values['album_artist'] = utils.join_artists(album['artists'], self.config['filename_separator'])

        # Parse values for playlist data
        if 'playlist' in song.keys():
            playlist = song['playlist']
            for key in playlist.keys():
                if key not in ['authors', 'songs', 'description'] and key is not list and key is not dict:
                    templ_values['playlist_' + key] = str(playlist[key])
            # Parse authors separately
            if 'authors' in playlist.keys() and len(playlist['authors']) > 0:
                templ_values['playlist_author'] = playlist['authors'][0]['name']  # First author only
                templ_values['playlist_authors'] = utils.join_artists(playlist['authors'],  self.config['filename_separator'])

        # Additional values
        templ_values['date_time'] = templ_values['datetime'] = datetime.now().strftime(default_config['datetime_format'])
        templ_values['date'] = datetime.now().strftime(default_config['date_format'])
        templ_values['time'] = datetime.now().strftime(default_config['time_format'])

        # Sanitize all template values for file names
        for key, value in templ_values.items():
            templ_values[key] = utils.sanitize_filename(str(value), self.config['filename_sanitize_placeholder'])

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

    def check_output_template(templ: str):
        # Check the output template for any errors:
        if not templ.endswith('.{ext}'):
            # log.error("Template string must end with '.{ext}'!")
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
    
    def find_song_counterpart(self, id: str):
        song_id: str = None

        return song_id

    def get_album_id_from_playlist(self, playlist_id: str):
        return self.ytmusic.get_album_browse_id(playlist_id)

    def get_album_info(self, id: str):
        """Get metadata for album ID"""
        album_info = Album()
        album_info['id'] = id
        ytm_album = None
        try:
            ytm_album = self.ytmusic.get_album(id)
        except Exception:
            return None, None

        if ytm_album:
            album_info['title'] = ytm_album['title']
            album_info['type'] = ytm_album['type']
            album_info['year'] = ytm_album['year']
            album_info['duration'] = ytm_album['duration']
            if 'description' in ytm_album:
                album_info['description'] = ytm_album['description']
            album_info['total'] = ytm_album['trackCount']
            album_info['artists'] = []
            for ytm_artist in ytm_album['artists']:
                artist = Artist(name=ytm_artist['name'], id=ytm_artist['id'])
                album_info['artists'].append(artist)

            # Get the largest song cover/thumbnail (always the last in the dict)
            if 'thumbnails' in ytm_album:
                album_info['cover'] = ytm_album['thumbnails'][-1]['url']
            return album_info, ytm_album
        
        return None, ytm_album
    
    def get_song_info(self, id: str):
        song_info = Song()



        return song_info
    

def main():
    return