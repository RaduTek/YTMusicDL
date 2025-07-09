from ytmusicdl.config import Config
from ytmusicdl.template import check_template, parse_template
from ytmusicdl.types import Song


# Load default config
config = Config()

# List of templates to test
templates = [
    # Default template from config
    config["output_template"],
    # Default template
    "{song_title} - {song_artist} [{song_id}].{ext}",
    # Multiple artists merged with separator
    "{song_title} - {song_artists} [{song_id}].{ext}",
    # Album data
    "{album_title} [{album_id}] - {song_title} [{song_id}].{ext}",
    # Unknown, invalid fields
    "{unknown|song_title} - {foo} {bar|} [{bar|song_id}].{ext}",
    # Template with optional separator
    "{song_index|+ - }{song_title}.{ext}",
    "{unknown|+ - }{song_title}.{ext}",
    # Invalid templates
    # Must end in '.{ext}'
    "{song_title} - {song_artist}",
    # Invalid syntax
    "{{{{{{song_title}.{ext}",
    "{{song_title}}.{ext}",
    "{song_title.{ext}",
    "}song_title{.{ext}",
    "{}.{ext}",
]


# Create dummy song object
song = Song(
    id="qwertyuiop",
    title="Song Title",
    artists=[
        {"name": "Artist 1", "id": "asdfghjkl"},
        {"name": "Artist 2", "id": "zxcvbnm"},
    ],
    album={"id": "qwertyuiop", "title": "Album Title"},
    cover="about:blank",
    duration=123,
    year=2021,
    type="audio",
    index=2,
)

good_templates = []

print("Checking templates...")
for template in templates:
    try:
        check_template(template)
        good_templates.append(template)
    except ValueError as e:
        print("\t Invalid template:", f"'{template}'")
        print("\t\t Error:", e)

print("\nParsing templates...")
for template in good_templates:
    parsed = parse_template(template, song, config)
    print("\t", f"'{parsed}'", "   from   ", f"'{template}'")
