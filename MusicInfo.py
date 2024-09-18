import os
from tkinter import Tk, filedialog
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
import requests

def select_folder():
    # Use Tkinter to create a file dialog for selecting a folder
    root = Tk()
    root.withdraw()  # Hide the root window
    folder_path = filedialog.askdirectory(title="Select a Folder")
    root.destroy()
    return folder_path

def find_mp3_files(folder_path):
    # Walk through the folder and its subfolders to find MP3 files
    mp3_files = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith('.mp3'):
                mp3_files.append(os.path.join(root, file))
    return mp3_files

def fetch_metadata_from_musicbrainz(title, artist):
    # Fetch metadata from MusicBrainz with refined query
    query = f'{title} AND artistname:{artist}'
    url = f'https://musicbrainz.org/ws/2/recording/?query={query}&fmt=json'
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        recordings = data.get('recordings', [])
        if recordings:
            recording = recordings[0]  # Take the first match
            return {
                'title': recording.get('title', 'Unknown'),
                'artist': ', '.join(artist['name'] for artist in recording.get('artist-credit', [])),
                'album': recording.get('releases', [{}])[0].get('title', 'Unknown'),
                'year': recording.get('first-release-date', 'Unknown')[:4],
                'composer': 'Unknown',  # Placeholder if not directly available
                'genre': 'Unknown',     # Placeholder if not directly available
            }
    except requests.exceptions.RequestException as e:
        print(f"Error fetching metadata from MusicBrainz: {e}")
    return None

def fetch_metadata_from_wikipedia(title, artist):
    # Fetch additional details from Wikipedia
    search_query = f'{title} {artist}'
    search_url = f'https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={search_query}&format=json'
    try:
        search_response = requests.get(search_url)
        search_response.raise_for_status()
        search_data = search_response.json()
        search_results = search_data.get('query', {}).get('search', [])
        if search_results:
            # Assume the first result is the most relevant
            page_title = search_results[0]['title']
            page_url = f'https://en.wikipedia.org/wiki/{page_title.replace(" ", "_")}'
            # Fetch page content
            detail_url = f'https://en.wikipedia.org/w/api.php?action=query&prop=extracts&exintro&explaintext&titles={page_title}&format=json'
            detail_response = requests.get(detail_url)
            detail_response.raise_for_status()
            detail_data = detail_response.json()
            pages = detail_data.get('query', {}).get('pages', {})
            page_content = next(iter(pages.values())).get('extract', '')
            
            # Parse the page content to extract more detailed metadata (requires more sophisticated parsing)
            genre = extract_genre_from_content(page_content)
            composer = extract_composer_from_content(page_content)
            
            return {
                'genre': genre or 'Unknown',
                'composer': composer or 'Unknown',
                'source': page_url  # You might want to log the source of the information
            }
    except requests.exceptions.RequestException as e:
        print(f"Error fetching details from Wikipedia: {e}")
    return None

def extract_genre_from_content(content):
    # Dummy function to simulate extraction of genre from Wikipedia content
    # You would replace this with actual parsing logic
    if 'rock' in content.lower():
        return 'Rock'
    elif 'pop' in content.lower():
        return 'Pop'
    return 'Unknown'

def extract_composer_from_content(content):
    # Dummy function to simulate extraction of composer from Wikipedia content
    # You would replace this with actual parsing logic
    if 'composer' in content.lower():
        return 'Some Composer'  # Replace with actual parsing result
    return 'Unknown'

def update_mp3_metadata(file_path, metadata):
    # Update MP3 metadata using mutagen
    try:
        audio = MP3(file_path, ID3=EasyID3)

        # Clear all existing comments
        if 'comment' in audio:
            del audio['comment']
        
        # Update metadata fields
        audio['title'] = metadata.get('title', 'Unknown')
        audio['artist'] = metadata.get('artist', 'Unknown')
        audio['album'] = metadata.get('album', 'Unknown')
        audio['date'] = metadata.get('year', 'Unknown')
        audio['composer'] = metadata.get('composer', 'Unknown')
        audio['genre'] = metadata.get('genre', 'Unknown')
        
        # Ensure fields that aren't handled get removed (optional)
        fields_to_remove = ['comment', 'unsynchronised lyrics', 'lyrics']
        for field in fields_to_remove:
            if field in audio:
                del audio[field]

        audio.save()
        print(f"Updated metadata for {file_path}")
    except Exception as e:
        print(f"Error updating {file_path}: {e}")

def extract_info_from_filename(file_path):
    # Extract title and artist from the filename as a fallback
    filename = os.path.basename(file_path)
    filename = os.path.splitext(filename)[0]  # Remove the file extension
    
    # Split by common separators and attempt to infer artist/title
    separators = [' - ', '_', ' by ', '-', '–', '|']
    for sep in separators:
        if sep in filename:
            parts = filename.split(sep)
            if len(parts) >= 2:
                # Assume parts[0] is artist and parts[1] is title or vice versa
                return parts[0].strip(), parts[1].strip()
    
    # If no clear format is found, return filename as title
    return filename.strip(), ""

def prompt_for_metadata(file_path):
    # Ask user to manually enter metadata if extraction fails
    print(f"\nManual input required for {file_path}")
    title = input("Enter the song title: ").strip()
    artist = input("Enter the artist name: ").strip()
    return title, artist

def main():
    # Main function to run the app
    print("Select a folder containing MP3 files:")
    folder_path = select_folder()
    
    if not folder_path:
        print("No folder selected. Exiting.")
        return
    
    mp3_files = find_mp3_files(folder_path)
    
    if not mp3_files:
        print("No MP3 files found in the selected folder.")
        return
    
    print(f"Found {len(mp3_files)} MP3 files.")
    for file_path in mp3_files:
        # Extract current metadata to use as a base for searching
        try:
            audio = MP3(file_path, ID3=EasyID3)
            current_title = audio.get('title', [''])[0]
            current_artist = audio.get('artist', [''])[0]
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            continue
        
        # Use filename as fallback if metadata is missing
        if not current_title or not current_artist:
            print(f"No sufficient metadata in file; trying to use filename for {file_path}")
            current_artist, current_title = extract_info_from_filename(file_path)
        
        # If still insufficient, prompt the user for input
        if not current_title or not current_artist:
            current_title, current_artist = prompt_for_metadata(file_path)
        
        # Fetch real metadata from external services
        if current_title and current_artist:
            musicbrainz_metadata = fetch_metadata_from_musicbrainz(current_title, current_artist) or {}
            wikipedia_metadata = fetch_metadata_from_wikipedia(current_title, current_artist) or {}

            # Combine dictionaries, prioritizing MusicBrainz data
            combined_metadata = {**wikipedia_metadata, **musicbrainz_metadata}

            if combined_metadata:
                update_mp3_metadata(file_path, combined_metadata)
            else:
                print(f"No metadata found for {file_path}.")
        else:
            print(f"Insufficient data to search for {file_path}.")
    
if __name__ == "__main__":
    main()
