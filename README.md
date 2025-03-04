# Utilities

### Apple Music to Spotify Playlist Converter

The `apple_music_to_spotify.py` script allows you to convert your Apple Music playlists to Spotify playlists. This utility parses an Apple Music library XML file, extracts the playlists and track details, and creates corresponding playlists on Spotify. The script handles the following:

- Parses the Apple Music library XML file to extract playlists and track details.
- Uses the Spotify Web API to create private playlists on Spotify.
- Adds tracks to the Spotify playlists, handling up to 100 tracks per request to comply with Spotify's API limits.
- Implements a retry mechanism with exponential backoff to handle potential API request timeouts.
- Logs missing tracks that could not be found on Spotify to a JSON file for further review.

To use this script, you need to provide the path to your Apple Music library XML file, your Spotify client ID, and your Spotify client secret as command-line arguments.

Example usage:
```sh
python apple_music_to_spotify.py /path/to/Library.xml YOUR_SPOTIFY_CLIENT_ID YOUR_SPOTIFY_CLIENT_SECRET
