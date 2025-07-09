from typing import TypedDict, Literal, NotRequired, get_args

AudioFormat = Literal["opus", "m4a"]
audio_formats = list(get_args(AudioFormat))

AudioQuality = Literal["medium", "high"]
audio_qualities = list(get_args(AudioQuality))

CoverFormat = Literal["png", "jpg"]
cover_formats = list(get_args(CoverFormat))

SongType = Literal["audio", "video"]

UrlType = Literal["watch", "playlist", "album", "artist", "library"]

song_types: dict[str, SongType] = {
    "MUSIC_VIDEO_TYPE_ATV": "audio",
    "MUSIC_VIDEO_TYPE_OMV": "video",
    "MUSIC_VIDEO_TYPE_UGC": "video",
    "MUSIC_VIDEO_TYPE_OFFICIAL_SOURCE_MUSIC": "video",
}


class Source(TypedDict):
    url: str
    type: UrlType
    subtype: UrlType
    id: str


class Sourceable(TypedDict):
    id: str
    title: str
    source: Source
    cover: NotRequired[str]
    cover_data: NotRequired[bytes]


class Artist(TypedDict):
    name: str
    id: str


ArtistList = dict[str, Artist]


class Album(Sourceable):
    playlist_id: str
    type: str
    year: int
    duration: int
    total: int
    artists: list[Artist]


class Song(Sourceable):
    duration: int
    year: int
    type: SongType
    artists: list[Artist]
    lyrics: str
    lyrics_source: str
    index: int
    album: Album
    playlist: dict
    playlist_index: int
    metadataFull: NotRequired[bool]


SongList = dict[str, Song]


class AlbumList(Album):
    songs: SongList


class PlayList(Sourceable):
    authors: list[Artist]
    year: int
    duration: int
    total: int
    visibility: str
    description: str
    songs: list[Song]


class ArchiveSong(TypedDict):
    id: str
    title: str
    artists: str
    file_name: str


class Archive(TypedDict):
    downloaded_songs: list[ArchiveSong]
