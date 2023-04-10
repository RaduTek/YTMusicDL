[//]: # "# YTMusicDL"

<div align="center">

![YTMusicDL](other/YTMusicDL.png)

</div>

**This branch is for version 2.0, where the app is moving from a simple script to an object based design.**

Command line tool to download music from YT Music with appropriate metadata.

**Note:** This tool is still in its infancy, expect bugs. Please report any issues encountered with this tool.

## Setup

`ytmusicdl.py` is easy to set up and has been tested on Windows and Linux. Make sure the prerequisites listed below are installed on your system.

### Prerequisites:

- **Python** 3.8+ [(Official Website)](https://www.python.org/downloads/)
- `pillow` [(Official Website)](https://python-pillow.org/) [(PyPI)](https://pypi.org/project/Pillow/) (install using `pip`)
- `ytmusicapi` [(GitHub)](https://github.com/sigma67/ytmusicapi) [(Documentation)](https://ytmusicapi.readthedocs.io/en/latest/index.html) [(PyPI)](https://pypi.org/project/ytmusicapi/) (install using `pip`)
- `music_tag` [(GitHub)](https://github.com/KristoforMaynard/music-tag) [(PyPI)](https://pypi.org/project/music-tag/) (install using `pip`)
- `yt-dlp` [(GitHub)](https://github.com/yt-dlp/yt-dlp/) [(PyPI)](https://pypi.org/project/yt-dlp/) (install using `pip`)
- `FFMPEG` (required by `yt-dlp`)
  - **For Windows**: must be added to `%PATH%` [(Recommended: yt_dlp provided builds - GitHub)](https://github.com/yt-dlp/FFmpeg-Builds)
  - **For Linux**: Install from your package manager

## Usage

    usage: ytmusicdl.py [-h] [-f {opus,m4a,mp3}] [-q QUALITY] [-p BASE_PATH] [-o OUTPUT_TEMPLATE] [-a ARCHIVE] [-b] [--account ACCOUNT] [--write-json] [--cover-format {png,jpg}] [--write-cover] [--write-lyrics] [--no-lyrics]
                    [--skip-existing] [--skip-download] [--download-limit DOWNLOAD_LIMIT] [--playlist-limit PLAYLIST_LIMIT] [-v] [--log LOG] [--log-verbose] [--about]
                    URL [URL ...]

    Downloads songs from YT Music with appropriate metadata

    positional arguments:
      URL                   List of URL(s) to download

    options:
      -h, --help            show this help message and exit
      -f {opus,m4a,mp3}, --format {opus,m4a,mp3}
                            Audio output format
      -q QUALITY, --quality QUALITY
                            Audio quality: VBR (best: 0 - worst: 9) or CBR (e.g. 256)
      -p BASE_PATH, --base-path BASE_PATH
                            Base output path (default is current working directory)
      -o OUTPUT_TEMPLATE, --output-template OUTPUT_TEMPLATE
                            Output template for downloaded songs
      -a ARCHIVE, --archive ARCHIVE
                            Path to file that keeps record of the downloaded songs
      -b, --batch           Treat URL arguments as paths to files containing a list of URLs or IDs (one per line)
                            Specify "-" for input to be taken from console (stdin)
      --account-headers ACCOUNT_HEADERS
                            Path to file containing authentication headers
                            Allows special URL placeholder values to be used.
      --write-json          Write JSON with information about each song (follows output template)
      --cover-format {png,jpg}
                            Set the cover image format (png or jpg)
      --write-cover         Write each song's album cover to a file (follows output template)
      --write-lyrics        Write each song's lyrics to a file (follows output template)
      --no-lyrics           Don't obtain lyrics
      --skip-existing       Skip over existing files
      --skip-download       Skip downloading songs
      --download-limit DOWNLOAD_LIMIT
                            Limit the number of songs to be downloaded in an instance
      --playlist-limit PLAYLIST_LIMIT
                            Limit the number of songs to be downloaded from a playlist
      -v, --verbose         Show all debug messages on console and log
      --log LOG             Path to verbose log output file
      --log-verbose         Save all debug messages to the log
      --about               Display version information (must specify at least one (dummy) URL)

## Format and quality selection

Specify the desired output format with the `-f` or `--format` option. The available formats are OPUS, M4A (AAC) and MP3.

OPUS and M4A are directly downloaded from YT Music, while MP3 will be trans-coded from the best available format using FFMPEG.

For unauthenticated or free accounts:

1. OPUS codec, OGG container, averaging 140 kbps variable bitrate
2. AAC-LC codec, M4A container, 128 kbps "constant" bitrate

To select a different output quality, specify either a variable bitrate (0-9) or a constant bitrate (e.g. 128k) with the `-q` or `--quality` option.
This will re-encode downloaded audio using FFMPEG.

## Base path

Any relative paths specified as an argument will be treated as relative to the path specified by the `-p` or `--base-path` option.
If not specified, the base path defaults to the current working directory of the terminal window.

## Output Template

The `-o` or `--output` option is used to indicate a template for the output file names, relative to the base path. The audio download, `--write-json` and `--write-cover` all follow the output template.

The template usually contains special sequences that are replaced with values for each download. <br>
The sequence is `{value_name}` and it can be combined with other characters, for example: `{song_title} - {song_artist} [{song_id}].{ext}` - this is the default output template.

Some values might not be available in certain cases, like music videos where album related data isn't available. If a value is not available, it will be replaced with the placeholder string `Unknown`.

If you wish to specify other values in case one isn't available, you can use the `|` character. <br>
Example: `{album_artist|song_artist}` will parse to either the album artist if available, song artist if available or the placeholder string `Unknown`.

If you want to supress the `Unknown` placeholder string, you can add an empty value to the end of the list. <br>
Example: `{album_artist|song_artist|}` will parse to an empty string if none of the values are available.

For more advanced templates, you can specify text to follow a value only if it is available using the `+` operator.
Notice that the value list ends in `|`, as we want to supress the placeholder string. <br>
Example: `{song_index|+ - }{song_title}.{ext}` will parse to `1 - Song Title.opus` if the song index is available, otherwise it will parse to `Song Title.opus`

Notice: The output template must end in `.{ext}`, as hard-coding a file extension would cause issues.

### Available values for template

- Song related
  - `song_id`, `song_title`, `song_duration`, `song_year`
  - `song_type` - `Song` or `Video`
  - `song_artist` - first song artist
  - `song_artists` - all song artists, separated by `,&nbsp;`
- Album related
  - `song_index` - song's index in an album
  - `album_total` - total number of songs in an album
  - `album_id`, `album_title`
  - `album_type` - `Album` or `Single`, as seen on YT Music album page
  - `album_duration`
  - `album_artist` - first album artist
  - `album_artists` - all album artists, separated by `,&nbsp;`
- **Playlist related**
  - `song_playlist_index` - song's index in a playlist
  - `playlist_total` - total number of songs in a playlist
  - `playlist_id`, `playlist_title`
  - `playlist_author` - first playlist author
  - `playlist_authors` - all playlist authors (collaborators), separated by `,&nbsp;`
  - `playlist_visibility` - `Public`, `Unlisted` or `Private`
- **Other**
  - `date`, `time`, `date_time` - date and/or approximate time of download
  - `ext` - **can only be used at the end of the template**

## Archive file

The archive file will store a list of song IDs that have been previously downloaded.
The file is written to after every song download.

To enable, provide either an absolute path, or a path relative to the base path to the `-a` or `--archive` option.

## Batch file

If the `-b` or `--batch` option is provided, URL arguments will be treated as paths to files containing URLs or IDs to download, separated by new lines.

If a relative path is provided, it will be taken as relative to the specified base path.

## Account options

Follow the instructions on [ytmusicapi documentation](https://ytmusicapi.readthedocs.io/en/latest/setup.html#authenticated-requests) to get your account headers ready for use with `ytmusicdl.py`.

Specify your JSON file containing account header data using the `--account-headers` argument. This lets you use special placeholder IDs to download songs from your library:

- `library_songs` - Download songs from the Songs tab on the Library page
- `library_albums` - Download each album on the Albums tab on the Library page
- `library_playlists` - Download each playlist on the Playlists tab on the Library page
- `liked_songs` - Download your liked songs playlist

Most of the time you will be using `library_songs` as it includes liked songs and all available songs from albums added to your library.

## Download options

- `--skip-existing` will skip over existing files without overwriting
- `--skip-download` will not download the audio, but will still perform other actions.<br>
  Notice: any processed song will still be added to the archive even when using `--skip-download`.
- `--playlist-limit` limits the number of songs to be downloaded from **each** playlist.
- `--download-limit` limits the number of songs to be downloaded in the current instance.
- `--no-lyrics` will not get the lyrics for songs, this skips an API request and speeds up the download slightly.
- `--write-json` and `--write-lyrics` will write out a JSON file containing song information (the contents of the `song: dict` from source code) and the song lyrics (if available) respectively.
- `--write-cover` will write out the song cover art in the selected format.
- `--cover-format` selects the cover format (`png` or `jpg`) to be embedded in metadata and to be writte out by `--write-cover`.

## Example commands

### Basic use

`ytmusicdl.py URL`

Downloads the specified URL to the current working directory in the default format (OPUS) and quality(0 / best).

### Advanced use

`ytmusicdl.py -f "m4a" -p "Music" -a "archive.txt" -o "{album_artist|song_artist}/{album_title|song_title}/{song_index|+ - }{song_title}.{ext}" URL [URL ...]`

Downloads the specified URL(s) with the following options:

- Selected format: `m4a`
- Base path: `Music` (relative to current working directory)
- Archive file `archive.txt` (relative to base path)
- Output template: `{album_artist|song_artist}/{album_title|song_title}/{song_index|+ - }{song_title}.{ext}`
  - Example for audio-only song: `Album Artist/Album Title/1 - Song Title.ext`
  - Example for music video: `Song Artist/Song Title/Song Title.ext`

## Notes

- `ytmusicdl.py` will download music videos as **audio only**.
