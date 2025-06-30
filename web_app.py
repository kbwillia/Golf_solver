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

AI_TURN_DELAY = 1.5  # seconds

def run_until_human_or_gameover(game, game_session=None):
    """Run AI turns until it's the human player's turn or game is over"""
    if game_session:
        game_session['ai_thinking'] = True

    while (game.turn != 0 and game.round <= game.max_rounds):
        player = game.players[game.turn]

        # Check if player has any moves available
        available_positions = [i for i, known in enumerate(player.known) if not known]
        if available_positions:
            # Use the actual game logic from game.py
            game.play_turn(player)
        else:
            # Player has no moves (all cards face-up), but still counts as a turn
            print(f"{player.name} has no moves available (all cards face-up)")
        time.sleep(AI_TURN_DELAY)
        print(f"AI turn delay: {AI_TURN_DELAY}")
        game.next_player()

    # Check if game is over
    if game.round > game.max_rounds:
        # Reveal all cards
        for p in game.players:
            p.reveal_all()
        if game_session:
            game_session['ai_thinking'] = False
        return True

    if game_session:
        game_session['ai_thinking'] = False
    return False

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

    # Run AI turns if game doesn't start with human player
    game_over = False
    if game.turn != 0:
        # Create a temporary game session for the initial AI turns
        temp_session = {'ai_thinking': False}
        game_over = run_until_human_or_gameover(game, temp_session)

    # Store game state, including cumulative scores and match info
    games[game_id] = {
        'game': game,
        'mode': game_mode,
        'game_over': game_over,
        'player_name': player_name,
        'num_games': num_games,
        'current_game': 1,
        'cumulative_scores': [0] * num_players,
        'match_winner': None
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

        # Move to next player
        game.next_player()

        # Run AI turns until it's human's turn again or game ends
        game_over = run_until_human_or_gameover(game, game_session)
        game_session['game_over'] = game_over

        # After move, check if game is over
        if game.round > game.max_rounds:
            # Reveal all cards
            for p in game.players:
                p.reveal_all()
            game_session['game_over'] = True
            # Update cumulative scores
            scores = [game.calculate_score(p.grid) for p in game.players]
            for i, s in enumerate(scores):
                game_session['cumulative_scores'][i] += s
            # Check if more games remain
            if game_session['current_game'] < game_session['num_games']:
                # Start next game
                game_session['current_game'] += 1
                # Create new game instance, keep names/agents
                agent_types = [p.agent_type for p in game.players]
                new_game = GolfGame(num_players=len(game.players), agent_types=agent_types)
                # Set names
                for i, p in enumerate(new_game.players):
                    p.name = game.players[i].name
                game_session['game'] = new_game
                game_session['game_over'] = False
            else:
                # Match is over, determine winner
                min_score = min(game_session['cumulative_scores'])
                winners = [i for i, s in enumerate(game_session['cumulative_scores']) if s == min_score]
                # If tie, all lowest scorers are winners
                game_session['match_winner'] = winners

        return jsonify({
            'success': True,
            'game_state': get_game_state(game_id)
        })

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
                    # Human player - show privately visible cards (bottom row) and publicly known cards
                    if player.known[j] or j >= 2:  # Bottom row (positions 2,3) or publicly known
                        player_data['grid'].append({
                            'rank': card.rank,
                            'suit': card.suit,
                            'visible': True,
                            'public': player.known[j],  # Whether this card is known to all players
                            'score': card.score()
                        })
                    else:
                        # Top row hidden cards for human
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
        'cumulative_scores': cumulative_scores,
        'current_game': current_game,
        'num_games': num_games,
        'match_winner': match_winner
    }
    # Set winner for current game if over
    if game_session['game_over']:
        scores = [game.calculate_score(p.grid) for p in game.players]
        state['winner'] = scores.index(min(scores))
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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)