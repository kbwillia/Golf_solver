# Project file structure:
#   /static/css/golf.css              # All CSS styles for the Golf Card Game UI
#   /static/js/golf.js                # All JavaScript logic for the Golf Card Game UI
#   /static/golf_celebration_gifs.json # Celebration GIFs data (downsized_medium URLs)
#   /templates/index.html             # Main HTML template (structure only, links to CSS/JS)

from flask import Flask, render_template, request, jsonify, session
import uuid
import json
from game import GolfGame
from probabilities import get_probabilities
import time

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this in production

# Store active games
games = {}

AI_TURN_DELAY = 0.5  # seconds

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/create_game', methods=['POST'])
def create_game():
    """Create a new game session"""
    data = request.json
    game_mode = data.get('mode', '1v1')  # '1v1' or '1v3'
    opponent = data.get('opponent', 'random')
    player_name = data.get('player_name', 'Human')
    num_games = int(data.get('num_games', 1))

    # Generate unique game ID
    game_id = str(uuid.uuid4())

    # Create game based on mode
    if game_mode == '1v1':
        agent_types = ["human", opponent]
        num_players = 2
    else:  # 1v3
        agent_types = ["human", "random", "heuristic", "qlearning"]
        num_players = 4

    # Create the game
    game = GolfGame(num_players=num_players, agent_types=agent_types)
    # Set the human player's name
    game.players[0].name = player_name
    # set AI names with proper display names
    if game_mode == '1v1':
        # In 1v1, second player gets the opponent type name
        if opponent == "random":
            game.players[1].name = "Random AI"
        elif opponent == "heuristic":
            game.players[1].name = "Basic Logic AI"
        elif opponent == "qlearning":
            game.players[1].name = "Q-Learning AI"
    else:
        # In 1v3, give proper names to each AI
        ai_names = ["Random AI", "Basic Logic AI", "Q-Learning AI"]
        for i in range(1, num_players):
            game.players[i].name = ai_names[i-1]

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
        'cumulative_updated_for_game': False  # NEW: Track if cumulative updated for this game
    }

    return jsonify({
        'success': True,
        'game_id': game_id,
        'game_state': get_game_state(game_id)
    })

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

def get_game_state(game_id):
    """Get formatted game state for frontend"""
    if game_id not in games:
        return None

    game_session = games[game_id]
    game = game_session['game']

    # Format player grids - show what the human player can see
    players_data = []
    for i, player in enumerate(game.players):
        player_data = {
            'name': player.name,
            'agent_type': player.agent_type,
            'grid': [],
            'is_human': player.agent_type == 'human'
        }

        # Format grid cards based on what human player can see
        for j in range(4):
            card = player.grid[j]
            if card:
                if i == 0:
                    # Human player - show privately visible cards and publicly known cards
                    if player.known[j] or player.privately_visible[j]:
                        player_data['grid'].append({
                            'rank': card.rank,
                            'suit': card.suit,
                            'visible': True,
                            'public': player.known[j],  # Whether this card is known to all players
                            'score': card.score()
                        })
                    else:
                        # Hidden cards for human (top row that aren't publicly known)
                        player_data['grid'].append({
                            'rank': None,
                            'suit': None,
                            'visible': False,
                            'public': False,
                            'score': None
                        })
                else:
                    # AI players - only show publicly known cards
                    if player.known[j] or game_session['game_over']:
                        player_data['grid'].append({
                            'rank': card.rank,
                            'suit': card.suit,
                            'visible': True,
                            'public': True,
                            'score': card.score()
                        })
                    else:
                        player_data['grid'].append({
                            'rank': None,
                            'suit': None,
                            'visible': False,
                            'public': False,
                            'score': None
                        })
            else:
                player_data['grid'].append(None)

        players_data.append(player_data)

    # Get discard pile top card
    discard_top = None
    if game.discard_pile:
        card = game.discard_pile[-1]
        discard_top = {
            'rank': card.rank,
            'suit': card.suit,
            'score': card.score()
        }

    # Always calculate scores (not just at game over)
    scores = [game.calculate_score(p.grid) for p in game.players]
    public_scores = [get_public_score(p, game) for p in game.players]
    private_scores = [get_private_score(p, game) for p in game.players]
    winner = None
    if game_session['game_over']:
        winner = scores.index(min(scores))

    # Probabilities/statistics from probabilities.py
    probabilities = get_probabilities(game)

    # Add cumulative scores and match info
    cumulative_scores = game_session.get('cumulative_scores')
    current_game = game_session.get('current_game', 1)
    num_games = game_session.get('num_games', 1)
    match_winner = game_session.get('match_winner')

    # Use round_cumulative_scores if available (during game), otherwise cumulative_scores (between games)
    display_cumulative_scores = game_session.get('round_cumulative_scores', cumulative_scores)

    print(f"DEBUG: get_game_state: current_game={current_game}, game_over={game_session['game_over']}, cumulative_scores={game_session['cumulative_scores']}, round_cumulative_scores={game_session.get('round_cumulative_scores')}, cumulative_updated_for_game={game_session.get('cumulative_updated_for_game')}")

    deck_top_card = None
    if len(game.deck) > 0:
        card = game.deck[-1]
        deck_top_card = {
            'rank': card.rank,
            'suit': card.suit,
            'score': card.score()
        }

    state = {
        'players': players_data,
        'current_turn': game.turn,
        'round': game.round,
        'max_rounds': game.max_rounds,
        'discard_top': discard_top,
        'deck_size': len(game.deck),
        'game_over': game_session['game_over'],
        'scores': scores,
        'public_scores': public_scores,
        'private_scores': private_scores,
        'winner': winner,
        'mode': game_session['mode'],
        'probabilities': probabilities,
        'ai_thinking': game_session.get('ai_thinking', False),
        'cumulative_scores': display_cumulative_scores,
        'current_game': current_game,
        'num_games': num_games,
        'match_winner': match_winner,
        'deck_top_card': deck_top_card,
        'waiting_for_next_game': game_session.get('waiting_for_next_game', False)
    }
    # Set winner for current game if over
    if game_session['game_over']:
        scores = [game.calculate_score(p.grid) for p in game.players]
        state['winner'] = scores.index(min(scores))
    if game_session['game_over'] and game_session['current_game'] < game_session['num_games']:
        # Add final game scores to cumulative totals ONLY IF NOT ALREADY DONE
        if not game_session.get('cumulative_updated_for_game', False):
            scores = [game.calculate_score(p.grid) for p in game.players]
            for i, s in enumerate(scores):
                game_session['cumulative_scores'][i] += s
            game_session['cumulative_updated_for_game'] = True
            print(f"DEBUG: get_game_state: Added final game scores to cumulative_scores: {game_session['cumulative_scores']}")
        else:
            print("DEBUG: get_game_state: Cumulative scores already updated for this game.")
        # Set flag that we're waiting for user to continue to next game
        game_session['waiting_for_next_game'] = True
    else:
        game_session['waiting_for_next_game'] = False

    return state

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
        else:
            agent_types = ["human", "random", "heuristic", "qlearning"]
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

    print(f"DEBUG: Updated cumulative scores for round {current_round}: {game_session['round_cumulative_scores']}")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)