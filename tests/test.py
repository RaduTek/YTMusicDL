import json
from ytmusicdl import YTMusicDL

ytmdl = YTMusicDL()

album_playlist_id = 'OLAK5uy_mQ2JwANB6PPycuAKc0BiiTdf0M5-FPr6M'

album_id = ytmdl.get_album_id_from_playlist(album_playlist_id)

album, orig_req = ytmdl.get_album_info(album_id)

print(json.dumps(album, indent=2))
print(json.dumps(orig_req, indent=2))