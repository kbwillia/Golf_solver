import requests
import json
import os
from dotenv import load_dotenv

def load_existing_gifs(filename='golf_celebration_gifs.json'):
    """Load existing GIFs from JSON file and return set of IDs"""
    if not os.path.exists(filename):
        return set(), {'data': []}

    try:
        with open(filename, 'r') as f:
            existing_data = json.load(f)

        # Extract existing GIF IDs
        existing_ids = {gif['id'] for gif in existing_data.get('data', [])}
        return existing_ids, existing_data
    except (json.JSONDecodeError, KeyError):
        print("Error reading existing file, starting fresh")
        return set(), {'data': []}

def get_giphy_data(search_term, limit=50, offset=0):
    """Fetch GIF data from Giphy API"""
    load_dotenv()
    api_key = os.getenv('GIPHY_API_KEY')

    if not api_key:
        raise ValueError("GIPHY_API_KEY not found in environment variables")

    url = f"https://api.giphy.com/v1/gifs/search"

    params = {
        'api_key': api_key,
        'q': search_term,
        'limit': limit,
        'offset': offset
    }

    response = requests.get(url, params=params)
    response.raise_for_status()  # Raise an error for bad status codes

    return response.json()

def filter_gif_data(gif):
    """Extract only the keys we want from each GIF"""
    return {
        'id': gif.get('id'),
        'title': gif.get('title'),
        'url': gif.get('url'),
        'rating': gif.get('rating'),
        'images': {
            'downsized_large': gif.get('images', {}).get('downsized_large', {}),
            'downsized_medium': gif.get('images', {}).get('downsized_medium', {}),
            'downsized_small': gif.get('images', {}).get('downsized_small', {})
        }
    }

def update_gif_collection(search_term, batch_size=50, max_requests=5):
    """Update GIF collection with only new GIFs"""
    filename = 'golf_celebration_gifs.json'

    # Load existing GIFs
    existing_ids, existing_data = load_existing_gifs(filename)
    print(f"Found {len(existing_ids)} existing GIFs")

    all_gifs = existing_data.get('data', [])
    new_gifs_count = 0
    total_processed = 0

    # Fetch new GIFs in batches
    for batch in range(max_requests):
        offset = batch * batch_size
        print(f"Fetching batch {batch + 1} (offset: {offset})...")

        try:
            new_data = get_giphy_data(search_term, limit=batch_size, offset=offset)
            new_gifs = new_data.get('data', [])

            if not new_gifs:
                print("No more GIFs found")
                break

            # Filter out existing GIFs and clean the data
            truly_new_gifs = [
                filter_gif_data(gif)
                for gif in new_gifs
                if gif['id'] not in existing_ids
            ]

            if truly_new_gifs:
                all_gifs.extend(truly_new_gifs)
                # Add new IDs to existing set
                existing_ids.update(gif['id'] for gif in truly_new_gifs)
                new_gifs_count += len(truly_new_gifs)
                print(f"Added {len(truly_new_gifs)} new GIFs from this batch")
            else:
                print("No new GIFs in this batch")

            total_processed += len(new_gifs)

        except requests.RequestException as e:
            print(f"Error fetching data: {e}")
            break

    # Save updated collection
    updated_data = {
        'data': all_gifs,
        'pagination': {
            'total_count': len(all_gifs),
            'count': len(all_gifs),
            'offset': 0
        },
        'meta': {
            'status': 200,
            'msg': 'OK',
            'response_id': 'updated_collection'
        }
    }

    with open(filename, 'w') as f:
        json.dump(updated_data, f, indent=2)

    print(f"\nSummary:")
    print(f"- Total GIFs processed: {total_processed}")
    print(f"- New GIFs added: {new_gifs_count}")
    print(f"- Total GIFs in collection: {len(all_gifs)}")
    print(f"- File saved: {filename}")

    return updated_data

# Usage
if __name__ == "__main__":
    # Update collection with new GIFs
    gif_data = update_gif_collection('golf-celebration', batch_size=50, max_requests=10)