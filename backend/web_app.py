from flask import Flask, render_template, request, jsonify, session, send_from_directory, send_file
import uuid
import json
import random
import time
import logging
import os
from dotenv import load_dotenv
import requests
import threading

# Import from same directory
from game import GolfGame
from probabilities import get_probabilities, get_deck_counts, expected_value_draw_vs_discard
from chatbot import GolfChatbot, ChatHandler
from bot_personalities import enhance_custom_bot, save_bot_to_supabase
import json
import os
from game_state import get_game_state
from flask import send_file
from google_chipr_api import chirp3_voice
from data_upset import upload_game_state

# Load environment variables from .env file
load_dotenv()
# log = logging.getLogger('werkzeug')
# log.setLevel(logging.ERROR)  # Only show errors, not every request

# Get the absolute path to the backend directory
import os
backend_dir = os.path.dirname(os.path.abspath(__file__))
frontend_dir = os.path.join(backend_dir, '..', 'frontend')

# Debug logging for deployment
print(f"Backend directory: {backend_dir}")
print(f"Frontend directory: {frontend_dir}")
print(f"Template folder: {os.path.join(frontend_dir, 'templates')}")
print(f"Static folder: {os.path.join(frontend_dir, 'static')}")
print(f"Template folder exists: {os.path.exists(os.path.join(frontend_dir, 'templates'))}")
print(f"Static folder exists: {os.path.exists(os.path.join(frontend_dir, 'static'))}")

# Store active games
games = {}

chatbot = GolfChatbot()
chat_handler = ChatHandler(chatbot, games, get_game_state)
# Add error handling for imports
try:
    print("✅ All imports successful")
except Exception as e:
    print(f"❌ Import error: {e}")
    import traceback
    traceback.print_exc()

app = Flask(__name__,
           template_folder=os.path.join(frontend_dir, 'templates'),
           static_folder=os.path.join(frontend_dir, 'static'))
app.secret_key = 'your-secret-key-here'  # Change this in production

AI_TURN_DELAY = 01.50  # seconds

# Custom bot storage functions
def get_custom_bots_file_path():
    """Get the path to the custom_bot.json file"""
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_dir = os.path.join(backend_dir, '..', 'frontend')
    return os.path.join(frontend_dir, 'static', 'custom_bot.json')



custom_bot_cache = {} # cache of custom bots for frontend/backend communication (chatbot)

# todo function needd to be moved to game.py or game startup.py
def get_or_fetch_custom_bot(ai_bot_id):
    if ai_bot_id in custom_bot_cache:
        return custom_bot_cache[ai_bot_id]
    from supabase import create_client, Client
    import os, json
    url = os.environ.get("SUPABASE_URL")
    # Try legacy secret first, fall back to public key
    key = os.environ.get("SUPABASE_LEGACY_SECRET") or os.environ.get("SUPABASE_PUBLIC") or os.environ.get("SUPBAASE_PUBLIC")
    if not key or not url:
        raise ValueError("Missing Supabase credentials. Check SUPABASE_URL and SUPABASE_LEGACY_SECRET/SUPABASE_PUBLIC in .env")
    supabase: Client = create_client(url, key)
    response = supabase.table('custom_bots').select('*').eq('ai_bot_id', ai_bot_id).single().execute()
    if response.error or not response.data:
        print(f"❌ Error fetching bot {ai_bot_id} from Supabase: {response.error}")
        return None
    bot_data = response.data
    for field in ['emotional_state', 'proactive_config', 'response_config', 'gif_config']:
        if field in bot_data and isinstance(bot_data[field], str):
            try:
                bot_data[field] = json.loads(bot_data[field])
            except Exception:
                pass
    custom_bot_cache[ai_bot_id] = bot_data
    return bot_data


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/health')
def health_check():
    """Simple health check to verify the app is running"""
    return jsonify({
        'status': 'healthy',
        'message': 'Golf Card Game is running',
        'timestamp': time.time()
    })

@app.route('/test-static')
def test_static():
    """Test route to verify static files are being served"""
    return jsonify({
        'static_folder': app.static_folder,
        'template_folder': app.template_folder,
        'static_url_path': app.static_url_path
    })

@app.route('/debug-static')
def debug_static():
    """Debug route to test if static files exist"""
    css_path = os.path.join(frontend_dir, 'static', 'css', 'layout.css')
    js_path = os.path.join(frontend_dir, 'static', 'js', 'game-core.js')

    return jsonify({
        'backend_dir': backend_dir,
        'frontend_dir': frontend_dir,
        'static_folder': app.static_folder,
        'template_folder': app.template_folder,
        'css_exists': os.path.exists(css_path),
        'js_exists': os.path.exists(js_path),
        'css_path': css_path,
        'js_path': js_path,
        'static_dir_contents': os.listdir(os.path.join(frontend_dir, 'static')) if os.path.exists(os.path.join(frontend_dir, 'static')) else 'Directory not found'
    })



@app.route('/create_game', methods=['POST'])
def create_game():
    data = request.json
    game_mode = data.get('mode', '1v1')
    player_name = data.get('player_name', 'Human')
    num_games = int(data.get('num_games', 1))
    selected_bots = data.get('selected_bots', [])  # Always an array of bot objects

    # Ensure Jim Nantz, Golf Pro, and Golf Bro are present exactly once using a loop
    from bot_personalities import JimNantzBot # deciding to only keep players in the chat with announcers
    core_bots = [
        {"name": "Jim Nantz", "ai_bot_id": "jim_nantz", "class": JimNantzBot, "difficulty": "announcer"},
        # {"name": "Golf Pro", "ai_bot_id": "golf_pro", "class": GolfProBot, "difficulty": "nonplayer"},
        # {"name": "Golf Bro", "ai_bot_id": "golf_bro", "class": GolfBroBot, "difficulty": "nonplayer"}
    ]
    for core in core_bots:
        if not any(bot.get('name') == core["name"] for bot in selected_bots):
            bot_instance = core["class"]()
            selected_bots.append({
                'ai_bot_id': core["ai_bot_id"],
                'name': bot_instance.name,
                'description': bot_instance.description,
                'difficulty': core["difficulty"],
                'proactive_config': bot_instance.proactive_config,
                'response_config': bot_instance.response_config
            })
    print(f"DEBUG: Selected bots data attributes from frontend:")
    for idx, bot in enumerate(selected_bots):
        print(f"  Bot {idx+1}: {json.dumps(bot, indent=2)}")
    # 1. Cache all selected custom bots
    for bot in selected_bots:
        if 'ai_bot_id' in bot:
            custom_bot_cache[bot['ai_bot_id']] = bot
            # print(f"DEBUG: Cached bot {bot['ai_bot_id']}: {bot}") # this works. both bot and nantz.

    # 2. Set up agent types and player names
    # Only add user-selected bots as players
    agent_types = ['human']
    player_names = [player_name]
    difficulty_to_agent = {'easy': 'random', 'medium': 'heuristic', 'hard': 'ev_ai'}
    for bot in selected_bots:
        # Only add as player if not an announcer or non-player bot
        if bot.get('difficulty') not in ('announcer', 'nonplayer', 'announcer_only'):
            agent_types.append(difficulty_to_agent.get(bot.get('difficulty', 'medium').lower(), 'heuristic'))
            player_names.append(bot.get('name', 'AI Opponent'))
            print(f' player_names: {player_names}')

    num_players = len(agent_types)

    # 3. Create the game
    game_id = str(uuid.uuid4())
    game = GolfGame(num_players=num_players, agent_types=agent_types)
    game.game_id = game_id  # Set the game_id attribute for internal use
    for i, name in enumerate(player_names):
        game.players[i].name = name

    # 4. Store the game session
    games[game_id] = {
        'game': game,
        'mode': game_mode,
        'game_over': False,
        'player_name': player_name,
        'num_games': num_games,
        'current_game': 1,
        'cumulative_scores': [0] * num_players,
        'round_cumulative_scores': [0] * num_players,
        'match_winner': None,
        'cumulative_updated_for_game': False,
        'conversation_history': [],
        'pending_proactive_comments': [],
        'selected_bots': selected_bots, # Store selected_bots in session
        'whos_first': 0,  # Human starts first. Kinda like dealer, but want the human to start.
    }

    print("Final player order:")
    for i, name in enumerate(player_names):
        print(f"  Index {i}: {name}")

    # Update ChatHandler with the new game
    chat_handler.update_games_reference(games, get_game_state)

    return jsonify({
        'success': True,
        'game_id': game_id,
        'game_state': get_game_state(game_id, games)
    })

@app.route('/game_state/<game_id>')
def game_state(game_id):
    """Get current game state"""
    return jsonify(get_game_state(game_id, games))

@app.route('/make_move', methods=['POST'])
def make_move():
    """Process a human player move"""
    data = request.json
    game_id = data.get('game_id')
    action = data.get('action')

    if game_id not in games:
        return jsonify({'error': 'Game not found'}), 404

    game_session = games[game_id]
    game = game_session['game']

    # Check if game is already over
    if game_session['game_over']:
        return jsonify({'error': 'Game is already over'}), 400

    # Check if it's the human player's turn (always player 0)
    if game.turn != 0:
        return jsonify({'error': 'Not your turn'}), 400

    player = game.players[0]  # Human player

    try:
        # Convert frontend action to game action format
        game_action = None

        if action['type'] == 'take_discard':
            pos = action['position']
            if player.known[pos]:
                return jsonify({'error': 'Position already revealed'}), 400
            game_action = {'type': 'take_discard', 'position': pos}

        elif action['type'] == 'draw_deck':
            if action.get('keep', False):
                pos = action['position']
                if player.known[pos]:
                    return jsonify({'error': 'Position already revealed'}), 400
                game_action = {'type': 'draw_deck', 'position': pos, 'keep': True}
            else:
                # Drawing and discarding, with optional flip
                game_action = {'type': 'draw_deck', 'position': -1, 'keep': False}
                if 'flip_position' in action:
                    flip_pos = action['flip_position']
                    if not player.known[flip_pos]:
                        game_action['flip_position'] = flip_pos

        if not game_action:
            return jsonify({'error': 'Invalid action'}), 400

        # Temporarily override the human agent to return our action
        original_agent = game.agents[0]

        class MockAgent:
            def choose_action(self, player, game_state, trajectory=None):
                return game_action

        game.agents[0] = MockAgent()

        # Use the game's built-in play_turn method
        game.play_turn(player)

        # Restore original agent
        game.agents[0] = original_agent

        # Mark that human has made at least one move (for AI delay logic)
        game_session['human_has_played'] = True

        # Update cumulative scores for all players BEFORE advancing to next player
        # This ensures scores are recorded for the current round before it advances
        update_round_cumulative_scores(game_session, game)

        # Check for game over by all cards revealed
        if game.all_players_done():
            game_session['game_over'] = True
        # Set waiting_for_next_game flag for multigame matches
        if game_session['game_over'] and game_session['current_game'] < game_session['num_games']:
            game_session['waiting_for_next_game'] = True
        else:
            game_session['waiting_for_next_game'] = False

        # --- Upload game state after every turn ---
        upload_game_state(
            game_id=game_id,
            game_state=get_game_state(game_id, games)
        )

        # Return game state BEFORE advancing to next player
        response = jsonify({
            'success': True,
            'game_state': get_game_state(game_id, games)
        })

        # Move to next player (this may advance the round)
        game.next_player()

        return response

    except Exception as e:
        print(f"Error processing move: {e}")
        return jsonify({'error': str(e)}), 400

@app.route('/draw_card/<game_id>')
def draw_card(game_id):
    """Draw a card from deck to show to human player for decision making"""
    if game_id not in games:
        return jsonify({'error': 'Game not found'}), 404

    game_session = games[game_id]
    game = game_session['game']

    # Check if it's the human player's turn and deck has cards
    if game.turn != 0 or game_session['game_over']:
        return jsonify({'error': 'Not your turn or game is over'}), 400

    if not game.deck:
        return jsonify({'error': 'No cards left in deck'}), 400

    # Peek at the top card without removing it
    drawn_card = game.deck[-1]

    return jsonify({
        'success': True,
        'drawn_card': {
            'rank': drawn_card.rank,
            'suit': drawn_card.suit,
            'score': drawn_card.score()
        }
    })




@app.route('/get_available_actions/<game_id>')
def get_available_actions(game_id):
    """Get available actions for human player"""
    if game_id not in games:
        return jsonify({'error': 'Game not found'}), 404

    game_session = games[game_id]
    game = game_session['game']

    if game.turn != 0 or game_session['game_over']:
        return jsonify({'actions': []})

    player = game.players[0]  # Human player
    actions = []

    # Available positions (face-down cards that aren't privately visible)
    available_positions = [i for i, known in enumerate(player.known) if not known]

    if not available_positions:
        return jsonify({'actions': []})

    # Can take from discard pile
    if game.discard_pile:
        for pos in available_positions:
            actions.append({
                'type': 'take_discard',
                'position': pos,
                'description': f'Take {game.discard_pile[-1].rank}{game.discard_pile[-1].suit} from discard and place at position {pos+1}'
            })

    # Can draw from deck
    if game.deck:
        actions.append({
            'type': 'draw_deck',
            'description': 'Draw from deck'
        })

    return jsonify({'actions': actions})

@app.route('/next_game', methods=['POST'])
def next_game():
    data = request.json
    game_id = data.get('game_id')

    if game_id not in games:
        return jsonify({'error': 'Game not found'}), 404

    game_session = games[game_id]

    # Check if there are more games to play
    if game_session['current_game'] >= game_session['num_games']:
        return jsonify({'error': 'No more games in this match'}), 400

    try:
        # Increment game number
        game_session['current_game'] += 1

        # Use stored agent_types and player_names from the session
        agent_types = ['human']
        player_names = [game_session['player_name']]
        selected_bots = game_session.get('selected_bots', [])
        difficulty_to_agent = {'easy': 'random', 'medium': 'heuristic', 'hard': 'ev_ai'}
        for bot in selected_bots:
            # Only add as player if not an announcer or non-player bot
            if bot.get('difficulty') not in ('announcer', 'nonplayer', 'announcer_only'):
                agent_types.append(difficulty_to_agent.get(bot.get('difficulty', 'medium').lower(), 'heuristic'))
                player_names.append(bot.get('name', 'AI Opponent'))
        num_players = len(agent_types)

        # Rotate whos_first
        game_session['whos_first'] = (game_session.get('whos_first', 0) + 1) % num_players

        # Re-create the game
        new_game = GolfGame(num_players=num_players, agent_types=agent_types)
        for i, name in enumerate(player_names):
            new_game.players[i].name = name

        # Set the starting player for this game
        new_game.turn = game_session['whos_first']
        # Ensure round is set to 1 for new game
        new_game.round = 1

        # Update session
        game_session['game'] = new_game
        game_session['game_over'] = False
        game_session['match_winner'] = None
        game_session['waiting_for_next_game'] = False
        game_session['cumulative_updated_for_game'] = False
        game_session['round_cumulative_scores'] = game_session['cumulative_scores'].copy()
        game_session['conversation_history'] = []
        game_session['pending_proactive_comments'] = []

        return jsonify({
            'success': True,
            'game_state': get_game_state(game_id, games)
        })

    except Exception as e:
        print(f"Error starting next game: {e}")
        return jsonify({'error': str(e)}), 400

def get_public_score(player, game):
    # Only sum cards that are public (face-up to all), using calculate_score for pair cancellation
    visible_grid = [card if (card and player.known[i]) else None for i, card in enumerate(player.grid)]
    return game.calculate_score(visible_grid)

def get_private_score(player, game):
    # For human: use calculate_score, but only with visible cards (public or privately visible)
    if player.agent_type == 'human':
        visible_grid = [
            card if (card and (player.known[i] or (hasattr(player, 'privately_visible') and player.privately_visible[i])))
            else None
            for i, card in enumerate(player.grid)
        ]
        return game.calculate_score(visible_grid)
    else:
        return None

@app.route('/run_ai_turn', methods=['POST'])
def run_ai_turn():
    data = request.json
    game_id = data['game_id']
    game_session = games[game_id]
    game = game_session['game']

    # Only add delay for actual AI turns, not new game setup
    if game.turn != 0 and not game_session['game_over']:
        game_session['ai_thinking'] = True
        player = game.players[game.turn]
        time.sleep(AI_TURN_DELAY)
        try:
            move_success = game.play_turn(player)
            update_round_cumulative_scores(game_session, game)
            if game.all_players_done():
                game_session['game_over'] = True
            game.next_player()  # Always advance the turn after a bot move
            print(f"After next_player: turn={game.turn}, player={game.players[game.turn].name}")
        except Exception as e:
            print(f"AI move failed: {e}")
            # Optionally, do not advance the turn
        game_session['ai_thinking'] = False

        # Mark waiting for next game if more games remain (don't auto-start)
        if game_session['game_over'] and game_session['current_game'] < game_session['num_games']:
            # Add final game scores to cumulative totals ONLY IF NOT ALREADY DONE
            if not game_session.get('cumulative_updated_for_game', False):
                public_scores = [get_public_score(p, game) for p in game.players]
                for i, s in enumerate(public_scores):
                    game_session['cumulative_scores'][i] += s
                game_session['cumulative_updated_for_game'] = True
                print(f"DEBUG: run_ai_turn: Added final game scores to cumulative_scores: {game_session['cumulative_scores']}")
            else:
                print("DEBUG: run_ai_turn: Cumulative scores already updated for this game.")
            # Set flag that we're waiting for user to continue to next game
            game_session['waiting_for_next_game'] = True
        else:
            game_session['waiting_for_next_game'] = False

        return jsonify({
            'success': True,
            'game_state': get_game_state(game_id, games)
        })

    # Mark waiting for next game if more games remain (don't auto-start)
    if game_session['game_over'] and game_session['current_game'] < game_session['num_games']:
        # Add final game scores to cumulative totals ONLY IF NOT ALREADY DONE
        if not game_session.get('cumulative_updated_for_game', False):
            public_scores = [get_public_score(p, game) for p in game.players]
            for i, s in enumerate(public_scores):
                game_session['cumulative_scores'][i] += s
            game_session['cumulative_updated_for_game'] = True
            print(f"DEBUG: run_ai_turn: Added final game scores to cumulative_scores: {game_session['cumulative_scores']}")
        else:
            print("DEBUG: run_ai_turn: Cumulative scores already updated for this game.")
        # Set flag that we're waiting for user to continue to next game
        game_session['waiting_for_next_game'] = True
    else:
        game_session['waiting_for_next_game'] = False

    return jsonify({
        'success': True,
        'game_state': get_game_state(game_id, games)
    })

def update_round_cumulative_scores(game_session, game):
    """Update round cumulative scores for all players after any move"""
    public_scores = [get_public_score(p, game) for p in game.players]

    # Initialize round_cumulative_scores if not exists, starting from cumulative_scores
    if 'round_cumulative_scores' not in game_session:
        game_session['round_cumulative_scores'] = game_session['cumulative_scores'].copy()

    # Update running totals for this game for all players
    # Important: Use the current round number when the scores are calculated,
    # not after the round has advanced
    current_round = game.round
    for i, score in enumerate(public_scores):
        if score is not None:
            # Always add current game score to cumulative total from previous games
            # This ensures cumulative scores always accumulate across games
            game_session['round_cumulative_scores'][i] = game_session['cumulative_scores'][i] + score

    # print(f"DEBUG: Updated cumulative scores for round {current_round}: {game_session['round_cumulative_scores']}")

@app.route('/test_chatbot_simple.html')
def test_chatbot():
    return send_from_directory('../frontend', 'test_chatbot_simple.html')

# Chatbot Routes
@app.route('/chatbot/send_message', methods=['POST'])
def send_chatbot_message():
    data = request.json
    result = chat_handler.handle_user_message(data)

    if isinstance(result, tuple):
        return jsonify(result[0]), result[1]
    return jsonify(result)

@app.route('/chatbot/get_bot_response', methods=['POST'])
def get_bot_response():
    """Get a response from a specific bot with delay"""
    data = request.json
    result = chat_handler.handle_get_bot_response(data, get_game_state, games)

    if isinstance(result, tuple):
        response_data, status_code = result
        return jsonify(response_data), status_code
    else:
        return jsonify(result)

@app.route('/chatbot/proactive_comment', methods=['GET'])
def get_proactive_comment_get():
    game_id = request.args.get('game_id')
    if not game_id or game_id not in games:
        return jsonify({'comments': []})
    game_session = games[game_id]
    comments = game_session.get('pending_proactive_comments', [])
    game_session['pending_proactive_comments'] = []
    print(f"Returning proactive comments for {game_id}: {comments}")
    return jsonify({'comments': comments})



@app.route('/chatbot/get_giphy_gif', methods=['POST'])
def get_giphy_gif():
    """Get a relevant GIF from Giphy API based on message content and bot name"""
    data = request.json
    result = chat_handler.handle_get_giphy_gif(data)

    if isinstance(result, tuple):
        response_data, status_code = result
        return jsonify(response_data), status_code
    else:
        return jsonify(result)

@app.route('/gif/search', methods=['POST'])
def user_gif_search():
    """Simple GIF search for users - searches exactly what they type"""
    try:
        data = request.json
        search_query = data.get('query', '').strip()

        if not search_query:
            return jsonify({'error': 'Search query cannot be empty'}), 400

        # Get API key from environment
        api_key = os.getenv('GIPHY_API_KEY')
        if not api_key:
            return jsonify({'error': 'GIPHY_API_KEY not found in environment variables'}), 500

        print('User gif search query:', search_query)

        # Call Giphy API directly with user's search query
        url = "https://api.giphy.com/v1/gifs/search"
        params = {
            'api_key': api_key,
            'q': search_query,
            'limit': 11,  # Get 5 GIFs for user to choose from
            'rating': 'g'
        }

        response = requests.get(url, params=params)
        response.raise_for_status()

        data = response.json()

        if data.get('data'):
            # Return all GIFs found (up to 5)
            gif_urls = []
            for gif in data['data']:
                # Clean the URL by removing tracking parameters
                gif_url = gif['images']['downsized_medium']['url']
                # Remove everything after ?cid= to clean up tracking parameters
                if '?' in gif_url:
                    gif_url = gif_url.split('?')[0]
                gif_urls.append(gif_url)

            return jsonify({
                'success': True,
                'gif_urls': gif_urls,  # Return array of URLs
                'search_query': search_query
            })
        else:
            return jsonify({'error': 'No GIFs found'}), 404

    except requests.RequestException as e:
        return jsonify({'error': f'Giphy API error: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

# Voice mapping for logical names to Google voice names
GOOGLE_VOICE_MAPPING = {
    'nantz': 'en-AU-Chirp-HD-D',
    'female': 'en-US-Wavenet-F',
    'male': 'en-US-Wavenet-D',
    'default': 'en-AU-Chirp-HD-D',
    # Add more mappings as needed
}

@app.route('/api/tts', methods=['POST'])
def tts():
    try:
        data = request.get_json()
        text = data.get('text', '')
        voice = data.get('voice', 'default')

        if not text:
            return jsonify({'success': False, 'error': 'Text is required'}), 400

        # Map voice names to speaker IDs
        voice_mapping = {
            'default': "9a88ff6b-8788-11ee-a48b-e86f38d7ec1a",
            'jim_nantz': "9a88ff6b-8788-11ee-a48b-e86f38d7ec1a",  # Use same speaker for now
            'male': "9a88ff6b-8788-11ee-a48b-e86f38d7ec1a",
            'female': "9a88ff6b-8788-11ee-a48b-e86f38d7ec1a"  # You can add different speaker IDs
        }

        speaker_id = voice_mapping.get(voice, voice_mapping['default'])

        payload = {
            "text": text,
            "speaker": speaker_id,
            "emotion": "Friendly"
        }
        headers = {
            "x-api-key": os.getenv("TOP_MEDIA"),
            "Content-Type": "application/json"
        }
        print("🎤 TTS Request:", payload)
        response = requests.post("https://api.topmediai.com/v1/text2speech", json=payload, headers=headers)
        print("🎤 Raw response:", response.text)
        result = response.json()
        print("🎤 TopMediai API response:", result)

        if result.get("status") == 200 and "oss_url" in result.get("data", {}):
            audio_url = result["data"]["oss_url"]

            # Download the audio file and return it as a blob
            audio_response = requests.get(audio_url)
            if audio_response.status_code == 200:
                from flask import make_response
                response = make_response(audio_response.content)
                response.headers['Content-Type'] = 'audio/wav'
                response.headers['Content-Disposition'] = 'attachment; filename=speech.wav'
                return response
            else:
                return jsonify({"error": "Failed to download audio file"}), 500
        else:
            return jsonify({"error": "TTS failed", "details": result}), 500
    except Exception as e:
        import traceback
        print("🎤 Exception in /api/tts:", e)
        traceback.print_exc()
        return jsonify({"error": "Server error", "details": str(e)}), 500

@app.route('/api/tts_google', methods=['POST'])
def tts_google():
    data = request.json
    text = data['text']
    voice_name = data.get("en-AU-Chirp-HD-D", "en-AU-Chirp-HD-D")
    audio_base64 = chirp3_voice(text, voice_name)
    return jsonify({'audioContent': audio_base64})

# In your web_app.py or similar

from flask import request, jsonify

# custom_bots = {}  # In-memory store; use a database for persistence

@app.route('/api/test', methods=['POST'])
def test_route():
    print("Test route hit!")
    return {"success": True}

@app.route('/api/create_custom_bot', methods=['POST'])
def create_custom_bot():
    print("Route hit!")  # <--- Add this as the first line
    data = request.get_json()
    print(f"🔥 /api/create_custom_bot endpoint hit - data: {data}")
    ai_bot_id = data.get('ai_bot_id')
    name = data.get('name')
    difficulty = data.get('difficulty')
    description = data.get('description')
    image_path = data.get('image_path')
    voice_id = data.get('voice_id')  # <-- Add this line
    print(f' data is {data} and ai_bot_id is {ai_bot_id} and name is {name} and difficulty is {difficulty} and description is {description} and image_path is {image_path}')
    if not ai_bot_id or not name or not difficulty or not description:
        return jsonify({'success': False, 'error': 'Missing fields'}), 400

    from bot_personalities import enhance_custom_bot, save_bot_to_supabase

    # Set default image_path if not provided
    if not image_path:
        default_images = {
            'easy': 'AI_bot_images/gofer.png',
            'medium': 'AI_bot_images/joey_tribbiani.png',
            'hard': 'AI_bot_images/tiger_woods.png',
        }
        image_path = default_images.get(difficulty.lower(), 'AI_bot_images/gofer.png')

    # 1. Enhance the bot with LLM, now passing image_path
    enhanced_bot = enhance_custom_bot(ai_bot_id, name, description, difficulty, image_path=image_path, voice_id=voice_id)

    # 2. Save to Supabase (bot.image_path will always be set)
    response = save_bot_to_supabase(enhanced_bot)

    # Check for success
    if response.data and len(response.data) > 0:
        return jsonify({'success': True, 'bot': response.data[0]})
    else:
        # Optionally, log response.model_dump() for debugging
        details = response.model_dump()
        return jsonify({'success': False, 'error': 'Failed to save bot', 'details': details}), 500



@app.route('/api/upload_bot_image', methods=['POST'])
def upload_bot_image():
    if 'image' not in request.files:
        return jsonify({'success': False, 'error': 'No image part in the request'}), 400
    file = request.files['image']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No selected file'}), 400
    # Optionally, add allowed file type checks here
    import os
    from werkzeug.utils import secure_filename
    static_folder = os.path.join(os.path.dirname(__file__), '../frontend/static/AI_bot_images')
    os.makedirs(static_folder, exist_ok=True)
    filename = secure_filename(file.filename)
    save_path = os.path.join(static_folder, filename)
    file.save(save_path)
    # Return the relative path for frontend use
    image_path = f'AI_bot_images/{filename}'
    return jsonify({'success': True, 'image_path': image_path}), 200



if __name__ == '__main__':
    # Get port from environment variable (for deployment) or use 5000 for local development
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting Flask app on port {port}")
    print(f"Environment PORT: {os.environ.get('PORT', 'Not set')}")
    app.run(debug=False, host='0.0.0.0', port=port)