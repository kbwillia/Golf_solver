import requests
import json

def get_giphy_data(search_term, limit=50):
    api_key = "YOUR_API_KEY"  # Get free key from developers.giphy.com
    url = f"https://api.giphy.com/v1/gifs/search"

    params = {
        'api_key': api_key,
        'q': search_term,
        'limit': limit,
        'offset': 0
    }

    response = requests.get(url, params=params)
    data = response.json()

    # Save to JSON file
    with open('golf_celebration_gifs.json', 'w') as f:
        json.dump(data, f, indent=2)

    return data

# Usage
gif_data = get_giphy_data('golf-celebration', limit=100)