from ytmusicdl.config import Config

presets = {
    "output_template": {
        "default": "{song_title} - {song_artist} [{song_id}].{ext}",
        "song_artist": "{song_title} - {song_artist}.{ext}",
        "artist_album_song": "{album_artist}/{album_title}/{song_index} - {song_title}.{ext}",
        "artist_albumyear_song": "{album_artist}/{album_title} ({album_year})/{song_index} - {song_title}.{ext}",
    }
}


def fill_presets(config: Config) -> None:
    """Replace preset placeholders in configuration options with the actual values"""

    for option, option_presets in presets.items():
        if config.get(option, "").startswith("preset"):
            preset_key = config["output_template"].split(":")[1]
            if preset_key in option_presets:
                config[option] = option_presets[preset_key]
            else:
                raise ValueError(
                    f"Unknown preset key: {preset_key} for option {option}!"
                )
