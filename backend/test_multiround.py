"""
Automated test for multi-round multi-bot gameplay.
Simulates full games through the Flask API without any UI.

Run from the backend directory:
    python test_multiround.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from unittest.mock import patch, MagicMock
import json

# Mock all external dependencies before any game modules import them
for mod_name in [
    'supabase', 'cerebras', 'cerebras.cloud', 'cerebras.cloud.sdk',
    'google_chipr_api', 'openai',
]:
    sys.modules[mod_name] = MagicMock()

import web_app
web_app.AI_TURN_DELAY = 0
web_app.upload_game_state = MagicMock(return_value=None)

# Also patch it in game.py which calls it directly
import game
game.upload_game_state = MagicMock(return_value=None)

app = web_app.app
app.config['TESTING'] = True


def create_game(client, num_bots, num_holes):
    bot_configs = [
        {'name': 'Bot_Easy', 'ai_bot_id': 'test_easy', 'difficulty': 'easy'},
        {'name': 'Bot_Medium', 'ai_bot_id': 'test_medium', 'difficulty': 'medium'},
        {'name': 'Bot_Hard', 'ai_bot_id': 'test_hard', 'difficulty': 'hard'},
    ]
    resp = client.post('/create_game', json={
        'player_name': 'TestHuman',
        'num_games': num_holes,
        'selected_bots': bot_configs[:num_bots],
    })
    data = resp.get_json()
    assert data['success'], f"create_game failed: {data}"
    return data['game_id'], data['game_state']


def find_unrevealed_position(game_state, player_index=0):
    player = game_state['players'][player_index]
    for pos in range(4):
        card = player['grid'][pos]
        if card and not card.get('public', False):
            return pos
    return None


def human_move(client, game_id, game_state):
    pos = find_unrevealed_position(game_state, 0)

    if pos is not None:
        action = {'type': 'take_discard', 'position': pos}
    else:
        # All human cards revealed -- draw from deck and discard to pass the turn
        action = {'type': 'draw_deck', 'keep': False}

    resp = client.post('/make_move', json={
        'game_id': game_id,
        'action': action,
    })
    data = resp.get_json()
    assert data.get('success'), f"Human move failed: {data.get('error')} action={action}"
    return data['game_state']


def run_ai_turn(client, game_id):
    resp = client.post('/run_ai_turn', json={'game_id': game_id})
    data = resp.get_json()
    assert data.get('success'), f"run_ai_turn failed: {data}"
    return data['game_state']


def play_one_hole(client, game_id, game_state, num_players):
    turn_log = []
    safety = num_players * 10  # Bots may not reveal every turn

    while not game_state['game_over'] and safety > 0:
        ct = game_state['current_turn']

        if ct == 0:
            turn_log.append(0)
            game_state = human_move(client, game_id, game_state)
        else:
            turn_log.append(ct)
            game_state = run_ai_turn(client, game_id)

        safety -= 1

    assert game_state['game_over'], f"Hole did not finish within safety limit. Turns: {turn_log}"
    return game_state, turn_log


def validate_turn_order(turn_log, num_players, hole_label):
    expected_cycle = list(range(num_players))
    errors = []
    for i, actual in enumerate(turn_log):
        expected = expected_cycle[i % num_players]
        if actual != expected:
            errors.append(f"  Move {i}: got player {actual}, expected {expected}")
    if errors:
        msg = f"{hole_label} turn order violated!\n"
        msg += f"  Full log: {turn_log}\n"
        msg += "\n".join(errors)
        return False, msg
    return True, ""


def advance_to_next_hole(client, game_id):
    resp = client.post('/next_game', json={'game_id': game_id})
    data = resp.get_json()
    assert data.get('success'), f"next_game failed: {data.get('error')}"
    return data['game_state']


def run_test(num_bots, num_holes, label):
    print(f"\n{'='*60}")
    print(f"TEST: {label}")
    print(f"  Players: 1 human + {num_bots} bot(s)  |  Holes: {num_holes}")
    print(f"{'='*60}")

    with app.test_client() as client:
        game_id, state = create_game(client, num_bots, num_holes)
        num_players = len(state['players'])
        assert num_players == 1 + num_bots, f"Expected {1+num_bots} players, got {num_players}"

        all_ok = True

        for hole in range(num_holes):
            hole_label = f"Hole {hole+1}/{num_holes}"

            assert state['current_turn'] == 0, \
                f"{hole_label}: Human should start first, but current_turn={state['current_turn']}"

            state, turns = play_one_hole(client, game_id, state, num_players)

            ok, msg = validate_turn_order(turns, num_players, hole_label)
            status = "PASS" if ok else "FAIL"
            print(f"  {hole_label}: {status}  turns={turns}  ({len(turns)} moves)")
            if not ok:
                print(msg)
                all_ok = False

            # Verify all cards revealed
            for pi, p in enumerate(state['players']):
                revealed = sum(1 for c in p['grid'] if c and c.get('visible'))
                assert revealed == 4, \
                    f"{hole_label}: Player {pi} ({p['name']}) only has {revealed}/4 cards revealed"

            if hole < num_holes - 1:
                state = advance_to_next_hole(client, game_id)

        if all_ok:
            print(f"\n  RESULT: ALL {num_holes} HOLES PASSED")
        else:
            print(f"\n  RESULT: FAILURES DETECTED")

        return all_ok


if __name__ == '__main__':
    results = []

    results.append(("1 bot, 3 holes",  run_test(num_bots=1, num_holes=3, label="1v1 -- 3 holes")))
    results.append(("2 bots, 3 holes", run_test(num_bots=2, num_holes=3, label="1v2 -- 3 holes")))
    results.append(("3 bots, 3 holes", run_test(num_bots=3, num_holes=3, label="1v3 -- 3 holes")))
    results.append(("2 bots, 9 holes", run_test(num_bots=2, num_holes=9, label="1v2 -- 9 holes")))

    print("\n" + "="*60)
    print("FINAL SUMMARY")
    print("="*60)
    all_passed = True
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("All tests passed.")
    else:
        print("Some tests FAILED.")
        sys.exit(1)
