# from RL_game import GolfGame

# print("=== SINGLE 2-PLAYER GOLF GAME (Updated Rules) ===")
# print("Rules: All cards start face-down, each flip makes card public to all players\n")

# # Create a 2-player game
# game = GolfGame(num_players=2, agent_types=["ev_ai", "random"])

# # Play the game with verbose output
# scores = game.play_game(verbose=True)

# print(f"\nFinal Scores:")
# print(f"Q-learning: {scores[0]}")
# print(f"Random: {scores[1]}")
# print(f"Winner: {'Q-learning' if scores[0] < scores[1] else 'Random'}")