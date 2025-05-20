from urllib.parse import urlparse, parse_qs
from ytmusicdl.types import Source, UrlType


valid_netlocs = [
    "music.youtube.com",
    "www.music.youtube.com",
    "youtube.com",
    "www.youtube.com",
    "youtu.be",
]


def parse_id_type(id: str) -> UrlType:
    """Parse a playlist or album source ID"""

    if id.startswith("OLAK5uy_") or id.startswith("MPRE"):
        return "album"
    elif id.startswith("PL"):
        return "playlist"

    return "watch"


def parse_id(id: str) -> Source:
    """Parse a source ID"""
    source = Source(id=id)

    source["type"] = parse_id_type(id)

    base_url = "https://music.youtube.com/"
    match source["type"]:
        case "watch":
            source["url"] = f"{base_url}watch?v={id}"
        case "playlist":
            source["url"] = f"{base_url}playlist?list={id}"
        case "album":
            source["url"] = f"{base_url}browse/{id}"

    return source


def parse_url(url: str) -> Source:
    """Parse a source URL"""
    source = Source(url=url)

    parsed = urlparse(url)
    path = parsed.path.split("/")
    query = parse_qs(parsed.query)

    if parsed.netloc not in valid_netlocs:
        raise ValueError("Not a YouTube URL")

    if parsed.netloc == "youtu.be":
        source["id"] = parsed.path.split("/")[-1]
        source["type"] = "watch"
    else:
        match path[1]:
            case "watch":
                source["id"] = query["v"][0]
                source["type"] = "watch"
            case "playlist":
                source["id"] = query["list"][0]
                source["type"] = "playlist"
                source["subtype"] = parse_id_type(source["id"])
                if source["subtype"] == "playlist":
                    source.pop("subtype")
            case "browse":
                source["id"] = parsed.path.split("/")[-1]
                source["type"] = "album"
            case _:
                raise ValueError("Invalid YouTube Music URL")

    return source


def parse_source(source: str) -> Source:
    """Parse a source URL or ID"""
    if source.startswith("http"):
        return parse_url(source)
    return parse_id(source)


def get_source(source: str | Source, source_type: UrlType | None = None) -> Source:
    """Get a source from an ID, URL or Source"""
    if type(source) is str:
        source = parse_source(source)

    if source_type and source["type"] != source_type:
        raise ValueError(
            f"Invalid source type: '{source['type']}', expected type '{source_type}'"
        )

    return source
