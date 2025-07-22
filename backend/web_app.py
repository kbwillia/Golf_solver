# Project file structure:
#   /static/css/golf.css              # All CSS styles for the Golf Card Game UI
#   /static/js/golf.js                # All JavaScript logic for the Golf Card Game UI
#   /static/golf_celebration_gifs.json # Celebration GIFs data (downsized_medium URLs)
#   /templates/index.html             # Main HTML template (structure only, links to CSS/JS)

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
from chatbot import chatbot, chat_handler
from bot_personalities import create_bot, register_custom_bot
import json
import os
from game_state import get_game_state
from flask import send_file
from google_chipr_api import chirp3_voice

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

# Store active games
games = {}

AI_TURN_DELAY = 0.50  # seconds

# Custom bot storage functions
def get_custom_bots_file_path():
    """Get the path to the custom_bot.json file"""
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_dir = os.path.join(backend_dir, '..', 'frontend')
    return os.path.join(frontend_dir, 'static', 'custom_bot.json')

def load_custom_bots_from_json():
    """Load custom bots from JSON file"""
    try:
        file_path = get_custom_bots_file_path()
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Extract custom bots (not placeholder_bots)
                custom_bots = data.get('custom_bots', {})
                print(f"✅ Loaded {len(custom_bots)} custom bots from JSON")
                return custom_bots
        else:
            print("📄 Custom bots JSON file not found, starting with empty storage")
            return {}
    except Exception as e:
        print(f"❌ Error loading custom bots from JSON: {e}")
        return {}

def save_custom_bots_to_json(custom_bots_dict):
    """Save custom bots to JSON file"""
    try:
        file_path = get_custom_bots_file_path()

        # Load existing data to preserve placeholder_bots
        existing_data = {}
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)

        # Update with new custom bots
        existing_data['custom_bots'] = custom_bots_dict

        # Save back to file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, indent=2, ensure_ascii=False)

        print(f"✅ Saved {len(custom_bots_dict)} custom bots to JSON")
        return True
    except Exception as e:
        print(f"❌ Error saving custom bots to JSON: {e}")
        return False

# Initialize custom bots from JSON
custom_bots = load_custom_bots_from_json()

# Register all loaded custom bots in the chatbot system
for bot_id, bot_data in custom_bots.items():
    try:
        register_custom_bot(bot_id, bot_data['name'], bot_data['description'], bot_data['difficulty'])
        print(f"✅ Registered custom bot from JSON: {bot_data['name']}")
    except Exception as e:
        print(f"❌ Error registering custom bot {bot_id}: {e}")



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

@app.route('/test_chatbot_simple.html')
def test_chatbot():
    return send_from_directory('../frontend', 'test_chatbot_simple.html')

@app.route('/create_game', methods=['POST'])
def create_game():
    """Create a new game session"""
    try:
        data = request.json
        print(f"🎯 Backend: create_game received data: {data}")

        game_mode = data.get('mode', '1v1')  # '1v1' or '1v3'
        opponent = data.get('opponent', 'random')
        player_name = data.get('player_name', 'Human')
        num_games = int(data.get('num_games', 1))
        bot_name = data.get('bot_name', 'peter_parker')
        custom_bot_info = data.get('custom_bot_info')
        custom_bots_1v3 = data.get('custom_bots_1v3', [])  # Array of custom bots for 1v3 mode
        custom_bots_1v2 = data.get('custom_bots_1v2', [])  # Array of custom bots for 1v2 mode

        print(f"🎯 Backend: Game mode: {game_mode}")
        print(f"🎯 Backend: Custom bots 1v3: {custom_bots_1v3}")
        print(f"🎯 Backend: Custom bots 1v2: {custom_bots_1v2}")

        # Generate unique game ID
        game_id = str(uuid.uuid4())

        # Initialize custom bot data storage
        custom_bot_data = []

        # Create game based on mode
        if game_mode == '1v1':
            agent_types = ["human", opponent]
            num_players = 2
        elif game_mode == '1v2':
            agent_types = ["human", "ev_ai", "random"]
            num_players = 3

            # Handle multiple custom bots for 1v2 mode
            if custom_bots_1v2 and len(custom_bots_1v2) > 0:
                print(f"🎯 Backend: Processing {len(custom_bots_1v2)} custom bots for 1v2 mode")
                print(f"🎯 Backend: Bot sources: {[bot.get('name', 'Unknown') for bot in custom_bots_1v2]}")

                # Map custom bot difficulties to agent types
                difficulty_to_agent = {
                    'easy': 'random',
                    'medium': 'heuristic',
                    'hard': 'ev_ai'
                }

                # Update agent types based on custom bot difficulties (up to 2)
                for i, custom_bot in enumerate(custom_bots_1v2[:2]):
                    difficulty = custom_bot.get('difficulty', 'medium').lower()
                    agent_type = difficulty_to_agent.get(difficulty, 'heuristic')
                    agent_types[i + 1] = agent_type  # +1 because index 0 is human

                    # Store bot_id for chatbot lookup
                    bot_id = 'custom_' + custom_bot['name'].lower().replace(' ', '_').replace('-', '_')
                    custom_bot_data.append((f'custom_bot_id_{i}', bot_id, f'custom_bot_name_{i}', custom_bot['name']))

                    # Register the bot in the chatbot system if it has a description
                    if 'description' in custom_bot:
                        try:
                            register_custom_bot(bot_id, custom_bot['name'], custom_bot['description'], difficulty)
                            print(f"🎯 Backend: Registered custom bot '{custom_bot['name']}' in chatbot system")
                        except Exception as reg_error:
                            print(f"🎯 Backend: Error registering custom bot {bot_id}: {reg_error}")

                    print(f"🎯 Backend: Custom bot {i+1}: {custom_bot['name']} ({difficulty}) -> {agent_type} (bot_id: {bot_id})")
            else:
                print(f"🎯 Backend: No custom bots provided for 1v2 mode, using default agents")
        else:  # 1v3
            # Default agent types for 1v3 mode
            agent_types = ["human", "ev_ai", "advanced_ev", "random", "heuristic"]
            num_players = 4

            # Handle multiple custom bots for 1v3 mode
            if custom_bots_1v3 and len(custom_bots_1v3) > 0:
                print(f"🎯 Backend: Processing {len(custom_bots_1v3)} custom bots for 1v3 mode")
                print(f"🎯 Backend: Bot sources: {[bot.get('name', 'Unknown') for bot in custom_bots_1v3]}")

                # Map custom bot difficulties to agent types
                difficulty_to_agent = {
                    'easy': 'random',
                    'medium': 'heuristic',
                    'hard': 'ev_ai'
                }

                # Update agent types based on custom bot difficulties (up to 3)
                for i, custom_bot in enumerate(custom_bots_1v3[:3]):
                    difficulty = custom_bot.get('difficulty', 'medium').lower()
                    agent_type = difficulty_to_agent.get(difficulty, 'heuristic')
                    agent_types[i + 1] = agent_type  # +1 because index 0 is human

                    # Store bot_id for chatbot lookup
                    bot_id = 'custom_' + custom_bot['name'].lower().replace(' ', '_').replace('-', '_')
                    custom_bot_data.append((f'custom_bot_id_{i}', bot_id, f'custom_bot_name_{i}', custom_bot['name']))

                    # Register the bot in the chatbot system if it has a description
                    if 'description' in custom_bot:
                        try:
                            register_custom_bot(bot_id, custom_bot['name'], custom_bot['description'], difficulty)
                            print(f"🎯 Backend: Registered random bot '{custom_bot['name']}' in chatbot system")
                        except Exception as reg_error:
                            print(f"🎯 Backend: Error registering random bot {bot_id}: {reg_error}")

                    print(f"🎯 Backend: Custom bot {i+1}: {custom_bot['name']} ({difficulty}) -> {agent_type} (bot_id: {bot_id})")
            else:
                print(f"🎯 Backend: No custom bots provided for 1v3 mode, using default agents")

        # Handle custom bot info for 1v1 mode
        custom_bot_info = data.get('custom_bot_info')
        if custom_bot_info:
            print(f"🎯 Backend: Processing custom bot for 1v1 mode: {custom_bot_info.get('name', 'Unknown')}")

            # Register the bot in the chatbot system
            bot_id = 'custom_' + custom_bot_info['name'].lower().replace(' ', '_').replace('-', '_')
            try:
                register_custom_bot(bot_id, custom_bot_info['name'], custom_bot_info['description'], custom_bot_info['difficulty'])
                print(f"🎯 Backend: Registered custom bot '{custom_bot_info['name']}' in chatbot system")
            except Exception as reg_error:
                print(f"🎯 Backend: Error registering custom bot {bot_id}: {reg_error}")

            # Store bot info for chatbot lookup
            custom_bot_data.append(('custom_bot_id_0', bot_id, 'custom_bot_name_0', custom_bot_info['name']))
        else:
            print(f"🎯 Backend: No custom bot info provided for 1v1 mode")

        # Create the game
        games.clear()  # Remove all previous games; only keep the current one
        game = GolfGame(num_players=num_players, agent_types=agent_types)
        # Set the human player's name
        game.players[0].name = player_name
        # set AI names with proper display names
        if game_mode == '1v1':
            # In 1v1, second player gets the opponent type name
            if opponent == "random":
                game.players[1].name = "Random move AI"
            elif opponent == "heuristic":
                game.players[1].name = "Basic Logic AI"
            elif opponent == "qlearning":
                game.players[1].name = "Q-Learning AI"
            elif opponent == "ev_ai":
                game.players[1].name = "EV AI"
            elif opponent == "advanced_ev":
                game.players[1].name = "Advanced EV AI"
        elif game_mode == '1v2':
            # In 1v2, set names for the two AIs from selected custom bots
            if custom_bots_1v2 and len(custom_bots_1v2) > 0:
                for i, custom_bot in enumerate(custom_bots_1v2[:2]):
                    game.players[i + 1].name = custom_bot['name']
            else:
                # Fallback to default names if no custom bots
                game.players[1].name = "EV AI"
                game.players[2].name = "Random move AI"
        else:
            # In 1v3, give custom names to each AI from selected custom bots
            if custom_bots_1v3 and len(custom_bots_1v3) > 0:
                for i, custom_bot in enumerate(custom_bots_1v3[:3]):
                    game.players[i + 1].name = custom_bot['name']
            else:
                # Fallback to default names if no custom bots
                ai_names = [
                    "Peter Parker",      # Easy (random)
                    "Happy Gilmore",    # Medium (basic logic)
                    "Tiger Woods",      # Hard (ev_ai)
                    "Shooter McGavin"   # Advanced (advanced_ev)
                ]
                for i in range(1, num_players):
                    game.players[i].name = ai_names[i-1]

        # Set the AI player's name
        if game_mode == '1v1':
            if custom_bot_info:
                # Use custom bot name for display, but store bot_id for chatbot lookup
                game.players[1].name = custom_bot_info['name']
                # Store the bot_id and name in the game session for chatbot lookup (will be added after games[game_id] is created)
                bot_id = 'custom_' + custom_bot_info['name'].lower().replace(' ', '_').replace('-', '_')
                custom_bot_data.append(('custom_bot_id', bot_id, 'custom_bot_name', custom_bot_info['name']))
            else:
                # Use built-in bot names
                game.players[1].name = {
                    'peter_parker': 'Peter Parker',
                    'happy_gilmore': 'Happy Gilmore',
                    'tiger_woods': 'Tiger Woods'
                }.get(bot_name, 'AI Opponent')
        elif game_mode == '1v2':
            # No custom bot support for 1v2 yet, but could be added here
            pass

        # No need to run AI turns here; handled by /run_ai_turn
        game_over = False

        # Store game state, including cumulative scores and match info
        games[game_id] = {
            'game': game,
            'mode': game_mode,
            'game_over': game_over,
            'player_name': player_name,
            'num_games': num_games,
            'current_game': 1,
            'cumulative_scores': [0] * num_players,
            'round_cumulative_scores': [0] * num_players,
            'match_winner': None,
            'cumulative_updated_for_game': False,  # NEW: Track if cumulative updated for this game
            'conversation_history': [],  # Initialize conversation history for chatbot
            'last_proactive_comment_time': time.time(),
            'proactive_comment_cooldown': 10,
            'pending_proactive_comments': [], # New: Store pending proactive comments
        }

        # Add custom bot data to the game session if any
        for bot_id_key, bot_id, bot_name_key, bot_name in custom_bot_data:
            games[game_id][bot_id_key] = bot_id
            games[game_id][bot_name_key] = bot_name
            print(f"🎯 Stored custom bot data: {bot_id_key}={bot_id}, {bot_name_key}={bot_name}")

        print(f"🎯 Final game session custom bot data: {[(k, v) for k, v in games[game_id].items() if 'custom_bot' in k]}")

        # Reset chatbot conversation history
        chatbot.conversation_history = []
        chatbot.reset_for_new_game()  # Reset bot state for new game

        # Now call get_game_state(game_id) after games[game_id] is set
        return jsonify({
            'success': True,
            'game_id': game_id,
            'game_state': get_game_state(game_id)
        })
    except Exception as e:
        print(f"ERROR in create_game: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/game_state/<game_id>')
def game_state(game_id):
    """Get current game state"""
    if game_id not in games:
        return jsonify({'error': 'Game not found'}), 404

    return jsonify(get_game_state(game_id))

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

        # Return game state BEFORE advancing to next player
        response = jsonify({
            'success': True,
            'game_state': get_game_state(game_id)
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
    """Start the next game in a multi-game match"""
    data = request.json
    game_id = data.get('game_id')

    if game_id not in games:
        return jsonify({'error': 'Game not found'}), 404

    game_session = games[game_id]

    # Check if we're actually waiting for next game
    if not game_session.get('waiting_for_next_game', False):
        return jsonify({'error': 'Not waiting for next game'}), 400

    # Check if there are more games to play
    if game_session['current_game'] >= game_session['num_games']:
        return jsonify({'error': 'No more games in this match'}), 400

    try:
        # Start next game
        game_session['current_game'] += 1
        if game_session['mode'] == '1v1':
            agent_types = ["human", game_session['game'].players[1].agent_type]
            num_players = 2
        elif game_session['mode'] == '1v2':
            agent_types = ["human", "ev_ai", "random"]
            num_players = 3
        else:
            agent_types = ["human", "ev_ai", "advanced_ev", "random", "heuristic"]
            num_players = 4

        new_game = GolfGame(num_players=num_players, agent_types=agent_types)
        for i, player in enumerate(new_game.players):
            player.name = game_session['game'].players[i].name
        game_session['game'] = new_game
        game_session['game_over'] = False
        game_session['match_winner'] = None
        game_session['waiting_for_next_game'] = False
        game_session['cumulative_updated_for_game'] = False  # NEW: Reset for new game

        # Reset round cumulative scores for new game
        game_session['round_cumulative_scores'] = game_session['cumulative_scores'].copy()
        print(f"DEBUG: next_game: Starting game {game_session['current_game']}, cumulative_scores={game_session['cumulative_scores']}")

        return jsonify({
            'success': True,
            'game_state': get_game_state(game_id)
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
        # Always add delay for all AI turns (not just after human)
        time.sleep(AI_TURN_DELAY)
        game.play_turn(player)

        # Update cumulative scores BEFORE advancing to next player
        update_round_cumulative_scores(game_session, game)

        # Return game state BEFORE advancing to next player
        response = jsonify({
            'success': True,
            'game_state': get_game_state(game_id)
        })

        # Move to next player (this may advance the round)
        game.next_player()

        # Check for game over
        if game.round > game.max_rounds:
            for p in game.players:
                p.reveal_all()
            game_session['game_over'] = True
            # If this is the last game, set match_winner
            if game_session['current_game'] == game_session['num_games']:
                min_score = min(game_session['cumulative_scores'])
                winners = [i for i, s in enumerate(game_session['cumulative_scores']) if s == min_score]
                game_session['match_winner'] = winners

        game_session['ai_thinking'] = False

        # Mark waiting for next game if more games remain (don't auto-start)
        if game_session['game_over'] and game_session['current_game'] < game_session['num_games']:
            # Add final game scores to cumulative totals ONLY IF NOT ALREADY DONE
            if not game_session.get('cumulative_updated_for_game', False):
                scores = [game.calculate_score(p.grid) for p in game.players]
                for i, s in enumerate(scores):
                    game_session['cumulative_scores'][i] += s
                game_session['cumulative_updated_for_game'] = True
                print(f"DEBUG: run_ai_turn: Added final game scores to cumulative_scores: {game_session['cumulative_scores']}")
            else:
                print("DEBUG: run_ai_turn: Cumulative scores already updated for this game.")
            # Set flag that we're waiting for user to continue to next game
            game_session['waiting_for_next_game'] = True
        else:
            game_session['waiting_for_next_game'] = False

        return response

    # Mark waiting for next game if more games remain (don't auto-start)
    if game_session['game_over'] and game_session['current_game'] < game_session['num_games']:
        # Add final game scores to cumulative totals ONLY IF NOT ALREADY DONE
        if not game_session.get('cumulative_updated_for_game', False):
            scores = [game.calculate_score(p.grid) for p in game.players]
            for i, s in enumerate(scores):
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
        'game_state': get_game_state(game_id)
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

# Chatbot Routes
@app.route('/chatbot/send_message', methods=['POST'])
def send_chatbot_message():
    data = request.json
    result = chat_handler.handle_send_message(data, get_game_state, games)

    if isinstance(result, tuple):
        response_data, status_code = result
        return jsonify(response_data), status_code
    else:
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


#         return jsonify(result)

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

@app.route('/chatbot/personalities', methods=['GET'])
def get_chatbot_personalities():
    """Get available chatbot personalities"""
    result = chat_handler.handle_get_personalities()

    if isinstance(result, tuple):
        response_data, status_code = result
        return jsonify(response_data), status_code
    else:
        return jsonify(result)

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

@app.route('/api/create_custom_bot', methods=['POST'])
def create_custom_bot():
    print("🔥 /api/create_custom_bot endpoint hit")
    data = request.get_json()
    name = data.get('name')
    difficulty = data.get('difficulty')
    description = data.get('description')
    if not name or not difficulty or not description:
        return jsonify({'success': False, 'error': 'Missing fields'}), 400

    bot_id = 'custom_' + name.lower().replace(' ', '_').replace('-', '_')
    bot_data = {
        'name': name,
        'difficulty': difficulty,
        'description': description
    }

    # Add to memory
    custom_bots[bot_id] = bot_data

    # Save to JSON file
    if save_custom_bots_to_json(custom_bots):
        print(f"✅ Custom bot '{name}' saved to JSON file")
    else:
        print(f"❌ Failed to save custom bot '{name}' to JSON file")

    # Register the custom bot for use in the chatbot system
    register_custom_bot(bot_id, name, description, difficulty)

    return jsonify({'success': True, 'bot_id': bot_id, 'bot': bot_data})

@app.route('/save_custom_bots', methods=['POST'])
def save_custom_bots():
    """Save multiple custom bots from the modal"""
    try:
        print("🔥 /save_custom_bots endpoint hit")
        print("🔥 Request method:", request.method)
        print("🔥 Request headers:", dict(request.headers))

        data = request.get_json()
        print("🔥 Request data:", data)

        bots = data.get('bots', [])
        print("🔥 Bots to save:", bots)

        if not bots:
            print("❌ No bots provided")
            return jsonify({'success': False, 'error': 'No bots provided'}), 400

        saved_bots = []
        for i, bot_data in enumerate(bots):
            print(f"🔥 Processing bot {i + 1}:", bot_data)

            name = bot_data.get('name', '').strip()
            description = bot_data.get('description', '').strip()
            difficulty = bot_data.get('difficulty', '').strip()

            print(f"🔥 Bot {i + 1} parsed - Name: '{name}', Description: '{description}', Difficulty: '{difficulty}'")

            if not name or not description or not difficulty:
                print(f"❌ Missing fields for bot {i + 1}: name='{name}', description='{description}', difficulty='{difficulty}'")
                return jsonify({'success': False, 'error': f'Missing fields for bot: {name}'}), 400

            # Create unique bot ID
            bot_id = 'custom_' + name.lower().replace(' ', '_').replace('-', '_')
            print(f"🔥 Generated bot_id: {bot_id}")

            # Store in memory
            custom_bots[bot_id] = {
                'name': name,
                'difficulty': difficulty,
                'description': description
            }

            # Register for chatbot system
            try:
                register_custom_bot(bot_id, name, description, difficulty)
                print(f"✅ Successfully registered bot: {bot_id}")
            except Exception as reg_error:
                print(f"❌ Error registering bot {bot_id}: {reg_error}")
                import traceback
                traceback.print_exc()

        # Save all bots to JSON file
        if save_custom_bots_to_json(custom_bots):
            print(f"✅ All {len(saved_bots)} custom bots saved to JSON file")
        else:
            print(f"❌ Failed to save custom bots to JSON file")

            saved_bots.append({
                'id': bot_id,
                'name': name,
                'difficulty': difficulty,
                'description': description
            })

        print(f"✅ Successfully saved {len(saved_bots)} custom bots: {[bot['name'] for bot in saved_bots]}")
        print(f"✅ Current custom_bots dict: {custom_bots}")

        return jsonify({
            'success': True,
            'message': f'Successfully saved {len(saved_bots)} custom bot(s)',
            'bots': saved_bots
        })

    except Exception as e:
        print(f"❌ Error saving custom bots: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'}), 500

@app.route('/get_custom_bots', methods=['GET'])
def get_custom_bots():
    """Get all existing custom bots for the dropdown"""
    try:
        print("🔥 /get_custom_bots endpoint hit")

        # Reload from JSON to ensure we have the latest data
        global custom_bots
        custom_bots = load_custom_bots_from_json()

        print(f"🔥 Current custom_bots dict: {custom_bots}")

        # Convert the custom_bots dict to a list format
        bots_list = []
        for bot_id, bot_data in custom_bots.items():
            bots_list.append({
                'id': bot_id,
                'name': bot_data['name'],
                'difficulty': bot_data['difficulty'],
                'description': bot_data['description']
            })

        print(f"✅ Returning {len(bots_list)} custom bots: {[bot['name'] for bot in bots_list]}")

        return jsonify({
            'success': True,
            'bots': bots_list
        })

    except Exception as e:
        print(f"❌ Error getting custom bots: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'}), 500

def proactive_comment_timer():
    from chatbot import create_bot, GolfChatbot
    while True:
        time.sleep(5)  # Check every 5 seconds
        for game_id, game_session in games.items():
            game = game_session['game']
            # Build allowed bots: all AI except Golf Pro and Golf Bro, plus Jim Nantz
            allowed_bots = [p.name for p in game.players[1:] if p.name not in ('Golf Pro', 'Golf Bro')]
            if "Jim Nantz" not in allowed_bots:
                allowed_bots.append("Jim Nantz")
            for bot_name in allowed_bots:
                # Debug: Show custom bot mappings in game session
                print(f"[DEBUG] Custom bot mappings in session:", flush=True)
                for k, v in game_session.items():
                    if 'custom_bot' in k:
                        print(f"[DEBUG]   {k}: {v}", flush=True)
                bot_id_for_lookup = chat_handler.get_bot_id_from_display_name(game_session, bot_name)
                print(f"[Timer] Proactive comment - Bot name: {bot_name}, Bot ID: {bot_id_for_lookup}", flush=True)
                bot_instance = create_bot(bot_id_for_lookup)
                temp_chatbot = GolfChatbot(bot_id_for_lookup)
                temp_chatbot.current_bot = bot_instance
                last_time = game_session.get(f'last_proactive_comment_time_{bot_name}', 0)
                cooldown = game_session.get(f'proactive_comment_cooldown_{bot_name}', 10)
                comment = temp_chatbot.check_for_proactive_comment(
                    game_state=get_game_state(game_id),
                    conversation_history=game_session['conversation_history'],
                    last_proactive_comment_time=last_time,
                    cooldown_seconds=cooldown
                )
                if comment:
                    if 'pending_proactive_comments' not in game_session:
                        game_session['pending_proactive_comments'] = []
                    game_session['pending_proactive_comments'].append({
                        'bot_name': bot_name,
                        **comment
                    })
                    game_session[f'last_proactive_comment_time_{bot_name}'] = time.time()
                    print(f"[Timer] Proactive comment generated for {bot_name}: {comment}", flush=True)

# Start the timer in a background thread (add this near your app startup)
threading.Thread(target=proactive_comment_timer, daemon=True).start()

if __name__ == '__main__':
    # Get port from environment variable (for deployment) or use 5000 for local development
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting Flask app on port {port}")
    print(f"Environment PORT: {os.environ.get('PORT', 'Not set')}")
    app.run(debug=False, host='0.0.0.0', port=port)