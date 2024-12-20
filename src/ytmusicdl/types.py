from typing import TypedDict, Literal

AudioFormat = Literal["opus", "m4a"]
CoverFormat = Literal["png", "jpg"]
SongType = Literal["audio", "video"]
UrlType = Literal["watch", "playlist", "album", "artist", "library"]


# formats_ext = ["opus", "m4a", "mp3"]
# formats_ytdlp = {"opus": "opus", "m4a": "m4a", "mp3": "mp3"}
# cover_formats = ["png", "jpg"]

song_types: dict[str, SongType] = {
    "MUSIC_VIDEO_TYPE_ATV": "audio",
    "MUSIC_VIDEO_TYPE_OMV": "video",
    "MUSIC_VIDEO_TYPE_UGC": "video",
    "MUSIC_VIDEO_TYPE_OFFICIAL_SOURCE_MUSIC": "video",
}


class Artist(TypedDict):
    name: str
    id: str


ArtistList = dict[str, Artist]


class Album(TypedDict):
    id: str
    playlist_id: str
    title: str
    type: str
    year: int
    duration: int
    total: int
    artists: list[Artist]
    cover: str


class Song(TypedDict):
    id: str
    title: str
    duration: int
    year: int
    type: SongType
    artists: list[Artist]
    cover: str
    lyrics: str
    lyrics_source: str
    index: int
    album: Album
    playlist: dict
    playlist_index: int


SongList = dict[str, Song]


class AlbumList(Album):
    songs: SongList


class PlayList(TypedDict):
    id: str
    title: str
    authors: list[Artist]
    year: int
    duration: int
    total: int
    visibility: str
    description: str
    songs: list[Song]


class Source(TypedDict):
    url: str
    type: UrlType
    subtype: UrlType
    id: str
