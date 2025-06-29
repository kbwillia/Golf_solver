from flask import Flask, render_template, request, jsonify, session
from game import GolfGame
import json

app = Flask(__name__)
app.secret_key = 'golf_game_secret_key'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_game', methods=['POST'])
def start_game():
    data = request.get_json()
    num_players = data.get('num_players', 2)
    opponent_type = data.get('opponent_type', 'random')

    # Create game
    agent_types = ["human", opponent_type]
    if num_players == 4:
        agent_types = ["human", "random", "heuristic", "qlearning"]

    game = GolfGame(num_players=num_players, agent_types=agent_types)

    # Store game state in session
    session['game_state'] = {
        'num_players': num_players,
        'agent_types': agent_types,
        'players': [],
        'deck_size': len(game.deck),
        'discard_pile': [str(card) for card in game.discard_pile],
        'turn': game.turn,
        'round': game.round,
        'max_rounds': game.max_rounds
    }

    # Store player states
    for i, player in enumerate(game.players):
        player_state = {
            'name': player.name,
            'agent_type': player.agent_type,
            'grid': [str(card) if card else None for card in player.grid],
            'known': player.known.copy(),
            'privately_visible': player.privately_visible.copy()
        }
        session['game_state']['players'].append(player_state)

    # Store the actual game object (we'll need to recreate it)
    session['game_data'] = {
        'num_players': num_players,
        'agent_types': agent_types,
        'deck': [str(card) for card in game.deck],
        'discard_pile': [str(card) for card in game.discard_pile],
        'turn': game.turn,
        'round': game.round
    }

    return jsonify({
        'success': True,
        'game_state': session['game_state'],
        'message': f'Game started with {num_players} players'
    })

@app.route('/get_game_state')
def get_game_state():
    if 'game_state' not in session:
        return jsonify({'error': 'No game in progress'})

    return jsonify(session['game_state'])

@app.route('/take_action', methods=['POST'])
def take_action():
    data = request.get_json()
    action_type = data.get('action_type')
    position = data.get('position')

    if 'game_data' not in session:
        return jsonify({'error': 'No game in progress'})

    # Recreate the game from session data
    game_data = session['game_data']
    game = GolfGame(num_players=game_data['num_players'], agent_types=game_data['agent_types'])

    # Restore game state
    game.deck = [eval(f"Card('{card[0]}', '{card[1]}')") for card in game_data['deck']]
    game.discard_pile = [eval(f"Card('{card[0]}', '{card[1]}')") for card in game_data['discard_pile']]
    game.turn = game_data['turn']
    game.round = game_data['round']

    # Restore player states
    for i, player in enumerate(game.players):
        player_state = session['game_state']['players'][i]
        player.grid = [eval(f"Card('{card[0]}', '{card[1]}')") if card else None for card in player_state['grid']]
        player.known = player_state['known'].copy()
        player.privately_visible = player_state['privately_visible'].copy()

    # Take the action
    if action_type == 'take_discard':
        action = {'type': 'take_discard', 'position': position}
    elif action_type == 'draw_keep':
        action = {'type': 'draw_deck', 'position': position, 'keep': True}
    elif action_type == 'draw_discard':
        action = {'type': 'draw_deck', 'position': -1, 'keep': False, 'flip_position': position}
    else:
        return jsonify({'error': 'Invalid action type'})

    # Execute the action
    game.play_turn(game.players[game.turn], None)

    # Update session
    session['game_state']['deck_size'] = len(game.deck)
    session['game_state']['discard_pile'] = [str(card) for card in game.discard_pile]
    session['game_state']['turn'] = game.turn
    session['game_state']['round'] = game.round

    # Update player states
    for i, player in enumerate(game.players):
        session['game_state']['players'][i]['grid'] = [str(card) if card else None for card in player.grid]
        session['game_state']['players'][i]['known'] = player.known.copy()

    # Update game data
    session['game_data']['deck'] = [str(card) for card in game.deck]
    session['game_data']['discard_pile'] = [str(card) for card in game.discard_pile]
    session['game_data']['turn'] = game.turn
    session['game_data']['round'] = game.round

    return jsonify({
        'success': True,
        'game_state': session['game_state']
    })

@app.route('/draw_card')
def draw_card():
    if 'game_data' not in session:
        return jsonify({'error': 'No game in progress'})

    game_data = session['game_data']
    if not game_data['deck']:
        return jsonify({'error': 'No cards left in deck'})

    # Get the top card from deck
    drawn_card = game_data['deck'][-1]

    return jsonify({
        'success': True,
        'drawn_card': drawn_card
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)