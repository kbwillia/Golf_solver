
def get_game_state(game_id, games):
    # print(f"DEBUG: get_game_state called with game_id={game_id}")
    """Get formatted game state for frontend"""
    from probabilities import get_probabilities, get_deck_counts, expected_value_draw_vs_discard
    from web_app import get_public_score, get_private_score
    if game_id not in games:
        # print(f"DEBUG: game_id {game_id} not found in games dict")
        return None
    # print(f"DEBUG: games[{game_id}] = {games[game_id]}")
    game_session = games[game_id]
    if 'game' not in game_session:
        print(f"DEBUG: 'game' key not found in games[{game_id}]")
        return None

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

        # Add pairs info for human player
        if i == 0:
            pairs = game.get_pairs(player.grid)
            player_data['pairs'] = pairs

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

    # Add deck counts (public cards only)
    deck_counts = get_deck_counts(game)

    # Calculate expected value analysis for current player only
    current_player_ev_analysis = None
    if not game_session['game_over'] and game.turn < len(game.players):
        current_player = game.players[game.turn]
        current_player_ev_analysis = expected_value_draw_vs_discard(game, current_player)

    # Add cumulative scores and match info
    cumulative_scores = game_session.get('cumulative_scores')
    current_game = game_session.get('current_game', 1)
    num_games = game_session.get('num_games', 1)
    match_winner = game_session.get('match_winner')

    # Use round_cumulative_scores if available (during game), otherwise cumulative_scores (between games)
    display_cumulative_scores = game_session.get('round_cumulative_scores', cumulative_scores)

    # print(f"DEBUG: get_game_state: current_game={current_game}, game_over={game_session['game_over']}, cumulative_scores={game_session['cumulative_scores']}, round_cumulative_scores={game_session.get('round_cumulative_scores')}, cumulative_updated_for_game={game_session.get('cumulative_updated_for_game')}")

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
        'dictionary_of_cards_left_in_deck': deck_counts,
        'current_player_ev_analysis': current_player_ev_analysis,
        'ai_thinking': game_session.get('ai_thinking', False),
        'cumulative_scores': display_cumulative_scores,
        'current_game': current_game,
        'num_games': num_games,
        'match_winner': match_winner,
        'deck_top_card': deck_top_card,
        'waiting_for_next_game': game_session.get('waiting_for_next_game', False),
        'last_action': getattr(game, 'last_action', None),
        'action_history': getattr(game, 'action_history', []),
        'game_id': game_id,  # where game_id is the UUID string
        'whos_first': game_session.get('whos_first', 0),
    }
        # Set winner for current game if over
    if game_session['game_over']:
        scores = [game.calculate_score(p.grid) for p in game.players]
        winner_index = scores.index(min(scores))
        state['winner'] = winner_index
    if game_session['game_over'] and game_session['current_game'] < game_session['num_games']:
        # Add final game scores to cumulative totals ONLY IF NOT ALREADY DONE
        if not game_session.get('cumulative_updated_for_game', False):
            scores = [game.calculate_score(p.grid) for p in game.players]
            for i, s in enumerate(scores):
                game_session['cumulative_scores'][i] += s
            game_session['cumulative_updated_for_game'] = True
            # print(f"DEBUG: get_game_state: Added final game scores to cumulative_scores: {game_session['cumulative_scores']}")
        else:
            # print("DEBUG: get_game_state: Cumulative scores already updated for this game.")
            pass
        # Set flag that we're waiting for user to continue to next game
        game_session['waiting_for_next_game'] = True
    else:
        game_session['waiting_for_next_game'] = False

    # print(f"DEBUG: get_game_state returning state for {game_id}")
    return state
