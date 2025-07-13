import requests
import json
import time

def test_chatbot_integration():
    """Test the chatbot integration with the Flask app"""
    base_url = "http://localhost:5000"

    print("🧪 Testing Chatbot Integration")
    print("=" * 50)

    # Test 1: Get available personalities
    print("1. Testing personality loading...")
    try:
        response = requests.get(f"{base_url}/chatbot/personalities")
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                print("✅ Successfully loaded personalities:")
                for personality in data['personalities']:
                    print(f"   - {personality['name']}: {personality['description']}")
            else:
                print("❌ Failed to load personalities")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing personalities: {e}")

    # Test 2: Create a test game
    print("\n2. Creating test game...")
    try:
        game_data = {
            "mode": "1v1",
            "opponent": "random",
            "player_name": "TestPlayer",
            "num_games": 1
        }
        response = requests.post(f"{base_url}/create_game", json=game_data)
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                game_id = data['game_id']
                print(f"✅ Created test game: {game_id}")
            else:
                print("❌ Failed to create game")
                return
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Error creating game: {e}")
        return

    # Test 3: Send a message to the chatbot
    print("\n3. Testing chatbot message...")
    try:
        message_data = {
            "game_id": game_id,
            "message": "What should I do with my current hand?"
        }
        response = requests.post(f"{base_url}/chatbot/send_message", json=message_data)
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                print(f"✅ Chatbot response: {data['response'][:100]}...")
                print(f"   Bot name: {data['bot_name']}")
            else:
                print(f"❌ Chatbot error: {data.get('error', 'Unknown error')}")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing chatbot message: {e}")

    # Test 4: Test proactive comment
    print("\n4. Testing proactive comment...")
    try:
        comment_data = {
            "game_id": game_id,
            "event_type": "turn_start"
        }
        response = requests.post(f"{base_url}/chatbot/proactive_comment", json=comment_data)
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                if data['comment']:
                    print(f"✅ Proactive comment: {data['comment'][:100]}...")
                else:
                    print("✅ No proactive comment (this is normal - 30% chance)")
            else:
                print(f"❌ Proactive comment error: {data.get('error', 'Unknown error')}")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing proactive comment: {e}")

    # Test 5: Change personality
    print("\n5. Testing personality change...")
    try:
        personality_data = {
            "personality_type": "funny"
        }
        response = requests.post(f"{base_url}/chatbot/change_personality", json=personality_data)
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                print(f"✅ Changed to: {data['personality']['name']}")
                print(f"   Description: {data['personality']['description']}")
            else:
                print(f"❌ Personality change error: {data.get('error', 'Unknown error')}")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing personality change: {e}")

    print("\n" + "=" * 50)
    print("🎉 Chatbot integration test completed!")
    print("\nTo test the full interface:")
    print("1. Open your browser to http://localhost:5000")
    print("2. Start a game")
    print("3. Look for the chatbot panel in the left notification area")
    print("4. Try sending messages and changing personalities!")

if __name__ == "__main__":
    test_chatbot_integration()