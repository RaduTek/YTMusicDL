# YTMusicDL
Command line tool to download music from YT Music with appropriate metadata.

Note: This tool is still in its infancy, expect bugs. Please report any issues encountered with this tool.

## Setup
**Prerequisites** (install using `pip`):

* `ytmusicapi` [(GitHub)](https://github.com/sigma67/ytmusicapi) [(Documentation)](https://ytmusicapi.readthedocs.io/en/latest/index.html)
* `music_tag` [(GitHub)](https://github.com/KristoforMaynard/music-tag) [(PyPI)](https://pypi.org/project/music-tag/)
* `yt_dlp` [(GitHub)](https://github.com/yt-dlp/yt-dlp/)
* `FFMPEG` (must be added to path - required by `yt_dlp`) [(GitHub - yt_dlp provided builds)](https://github.com/yt-dlp/FFmpeg-Builds)

## Usage

    ytmusicdl.py [-h] [-f {opus,m4a,mp3}] [-q QUALITY] [-p BASE_PATH] [-o OUTPUT_TEMPLATE] [-a ARCHIVE] [--write-json] [--write-cover] [--no-lyrics] [--skip-download]
                        [--log LOG] [-v] [--about]
                        URL [URL ...]
 
    positional arguments:
      URL                   List of URL(s) to download
    
    options:
      -h, --help            show this help message and exit
      -f {opus,m4a,mp3}, --format {opus,m4a,mp3}
                            Audio output format
      -q QUALITY, --quality QUALITY
                            Audio quality: VBR (best: 0 - worst: 9) or CBR (e.g. 256k)
      -p BASE_PATH, --base-path BASE_PATH
                            Base output path (default is current working directory)
      -o OUTPUT_TEMPLATE, --output-template OUTPUT_TEMPLATE
                            Output template for downloaded songs
      -a ARCHIVE, --archive ARCHIVE
                            Path to file that keeps record of the downloaded songs
      --write-json          Write JSON with information about song(s) (follows output template)
      --write-cover         Write each song's album cover to a file (follows output template)
      --no-lyrics           Don't obtain lyrics
      --skip-download       Skip downloading songs
      --log LOG             Path to verbose log output file
      -v, --verbose         Show all debug messages on console
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

## Archive file

The archive file will store a list of song IDs that have been previously downloaded.
The file is written to after every song download.

To enable, provide either an absolute path, or a path relative to the base path to the `-a` or `--archive` option.

## Download options

`--skip-download` will not download the audio, but will still perform other actions.<br>
Notice: any processed song will still be added to the archive even when using `--skip-download`.

`--no-lyrics` will not get the lyrics for songs, this skips an API request and speeds up the download slightly.

`--write-json` and `--write-cover` will write out a JSON file containing song information (the contents of the `song: dict` from source code) and the cover art respectively.<br>
The default cover art format is `PNG`.

## Example commands

### Basic use

`ytmusicdl.py URL`

Downloads the specified URL to the current working directory in the default format (OPUS) and quality(0 / best).

### Advanced use

`ytmusicdl.py -f "m4a" -p "Music" -a "archive.txt" -o "{album_artist|song_artist}/{album_title|song_title}/{song_index|+ - }{song_title}.{ext}" URL [URL ...]`

Downloads the specified URL(s) with the following options:
* Selected format: `m4a` 
* Base path: `Music` (relative to current working directory)
* Archive file `archive.txt` (relative to base path)
* Output template: `{album_artist|song_artist}/{album_title|song_title}/{song_index|+ - }{song_title}.{ext}`
  * Example for audio-only song: `Album Artist/Album Title/1 - Song Title.ext`
  * Example for music video: `Song Artist/Song Title/Song Title.ext`
