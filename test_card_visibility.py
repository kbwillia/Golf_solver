from game import GolfGame

print("=== TESTING CARD VISIBILITY ===")
print("This will show how cards are visible to different players.\n")

# Create a 2-player game
game = GolfGame(num_players=2, agent_types=["human", "random"])

print("Initial state:")
print("P1 (you) - you can see your bottom two cards:")
print(game.players[0])
print("\nP2 (AI) - you can see their bottom two cards:")
print(game.players[1])

print(f"\nP1's known cards: {game.players[0].known}")
print(f"P2's known cards: {game.players[1].known}")

print("\n" + "="*50)
print("Golf Rules:")
print("1. Bottom two cards start face-down but are privately visible to each player")
print("2. When any card is flipped, it becomes public to all players")
print("3. Game progression: 0→1→2→3→4 face-up cards (one per turn)")