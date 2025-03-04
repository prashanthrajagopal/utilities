import xml.etree.ElementTree as ET
import json
import csv
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import time
from requests.exceptions import ReadTimeout
import argparse

def parse_library_xml(xml_file):
    """
    Parses the Apple Music library XML file and extracts playlists and track details.

    Args:
        xml_file (str): Path to the Apple Music library XML file.

    Returns:
        list: A list of dictionaries, each containing playlist details and tracks.
    """
    tree = ET.parse(xml_file)
    root = tree.getroot()

    # Create a dictionary to map track IDs to track details
    track_details = {}
    tracks_dict = root.find(".//dict[key='Tracks']/dict")
    track_elements = list(tracks_dict)
    for i in range(0, len(track_elements), 2):
        track_id = track_elements[i].text
        track_dict = track_elements[i + 1]
        track_info = {}
        track_info_elements = list(track_dict)
        for j in range(0, len(track_info_elements), 2):
            key = track_info_elements[j].text
            value = track_info_elements[j + 1].text if track_info_elements[j + 1] is not None else None
            track_info[key] = value
        track_details[track_id] = track_info

    playlists = []
    playlists_array = root.find(".//dict[key='Playlists']/array")
    for playlist_dict in playlists_array.findall('dict'):
        playlist_name = None
        playlist_tracks = []
        playlist_elements = list(playlist_dict)
        for i in range(0, len(playlist_elements), 2):
            key = playlist_elements[i].text
            if key == 'Name':
                playlist_name = playlist_elements[i + 1].text
            elif key == 'Playlist Items':
                for track_dict in playlist_elements[i + 1].findall('dict'):
                    track_id = None
                    track_item_elements = list(track_dict)
                    for j in range(0, len(track_item_elements), 2):
                        if track_item_elements[j].text == 'Track ID':
                            track_id = track_item_elements[j + 1].text
                            break
                    if track_id and track_id in track_details:
                        track_info = track_details[track_id]
                        playlist_tracks.append(track_info)
        if playlist_name:
            playlists.append({
                "name": playlist_name,
                "track_count": len(playlist_tracks),
                "tracks": playlist_tracks
            })

    return playlists

def create_spotify_playlists(playlists, client_id, client_secret):
    """
    Creates Spotify playlists from the given list of playlists and adds tracks to them.

    Args:
        playlists (list): A list of dictionaries, each containing playlist details and tracks.
        client_id (str): Spotify client ID.
        client_secret (str): Spotify client secret.
    """
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri="http://localhost:8888/callback",
        scope="playlist-modify-private"
    ))

    user_id = sp.current_user()["id"]
    missing_tracks = []

    with open("/Users/prajagopal/Desktop/track_details.csv", "w", newline='') as csvfile:
        fieldnames = ['Track Name', 'Spotify URI', 'Spotify Track Name']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for playlist in playlists:
            playlist_name = playlist["name"]
            track_uris = []
            for track in playlist["tracks"]:
                track_name = track.get('Name')
                artist_name = track.get('Artist')
                if track_name:
                    # Remove everything after " - "
                    track_name = track_name.split(" - ")[0]
                    # Remove " by None"
                    track_name = track_name.replace(" by None", "")
                    # Remove everything after " by "
                    track_name = track_name.split(" by ")[0]
                    # Add wildcard to track name
                    track_name = f"{track_name}"
                query = f"track:{track_name} artist:{artist_name}"
                if len(query) > 250:
                    query = query[:250]  # Truncate the query if it exceeds the maximum length

                # Retry mechanism with exponential backoff
                retries = 5
                for attempt in range(retries):
                    try:
                        result = sp.search(q=query, type="track", limit=1)
                        break
                    except ReadTimeout:
                        if attempt < retries - 1:
                            time.sleep(2 ** attempt)  # Exponential backoff
                            continue
                        else:
                            raise

                if result["tracks"]["items"]:
                    spotify_track = result["tracks"]["items"][0]
                    writer.writerow({
                        'Track Name': track_name,
                        'Spotify URI': spotify_track["uri"],
                        'Spotify Track Name': spotify_track["name"]
                    })
                    track_uris.append(spotify_track["uri"])
                else:
                    missing_tracks.append({
                        "playlist": playlist_name,
                        "track": track
                    })

            if track_uris:
                new_playlist = sp.user_playlist_create(user=user_id, name=playlist_name, public=False)
                # Add tracks in batches of 100
                for i in range(0, len(track_uris), 100):
                    sp.playlist_add_items(new_playlist["id"], track_uris[i:i + 100])

    # Write missing tracks details to a JSON file
    with open("./missing.json", "w") as json_file:
        json.dump(missing_tracks, json_file, indent=4)

def main():
    """
    Main function to parse the Apple Music library XML file and create Spotify playlists.
    """
    parser = argparse.ArgumentParser(description="Convert Apple Music playlists to Spotify playlists.")
    parser.add_argument("xml_file", help="Path to the Apple Music library XML file")
    parser.add_argument("client_id", help="Spotify client ID")
    parser.add_argument("client_secret", help="Spotify client secret")
    args = parser.parse_args()

    playlists = parse_library_xml(args.xml_file)
    create_spotify_playlists(playlists, args.client_id, args.client_secret)

if __name__ == "__main__":
    main()
