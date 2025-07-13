from pathlib import Path
from typing import cast
from ytmusicdl.archive import ArchivePlayList, ArchiveSong


def write_playlist_file(
    base_path: Path, playlist: ArchivePlayList, unicode: bool = True
):
    """Write the playlist to a file in M3U format"""

    file_enc = "utf-8" if unicode else "ascii"
    file = base_path / playlist["file"]

    with open(file, "w", encoding=file_enc) as f:
        f.write("#EXTM3U\n")
        for song in playlist["songs_data"]:
            song = cast(ArchiveSong, song)

            f.write(f"#EXTINF:{song['duration']},{song["title"]}\n")
            f.write(f"{song["file"]}\n")
