from typing import TypedDict

formats_ext = ['opus', 'm4a', 'mp3']
formats_ytdlp = {'opus': 'opus', 'm4a': 'm4a', 'mp3': 'mp3'}
cover_formats = ['png', 'jpg']

song_types = {
    "MUSIC_VIDEO_TYPE_ATV": 'Song',
    "MUSIC_VIDEO_TYPE_OMV": 'Video',
    "MUSIC_VIDEO_TYPE_UGC": 'Video',
    "MUSIC_VIDEO_TYPE_OFFICIAL_SOURCE_MUSIC": 'Video'
}

class Artist(TypedDict):
    name: str
    id: str

class Album(TypedDict):
    id: str
    title: str
    type: str
    year: int
    duration: str
    total: int
    artists: list[Artist]
    cover: str

class Song(TypedDict):
    id: str
    title: str
    duration: str
    year: int
    type: str
    artists: list[Artist]
    cover: str
    lyrics: str
    lyrics_source: str
    index: int
    album: Album
    playlist: dict
    playlist_index: int

class AlbumList(Album):
    songs: list[Song]

class PlayList(TypedDict):
    id: str
    title: str
    authors: list[Artist]
    year: int
    duration: str
    total: int
    visibility: str
    description: str
    songs: list[Song]