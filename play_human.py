from game import GolfGame

def play_human_vs_ai():
    print("=== HUMAN vs AI GOLF GAME ===")
    print("You will play against AI agents to test the gameplay rules.")
    print("Rules: All cards start face-down, each flip makes card public to all players\n")

    # Choose opponent
    print("Choose your opponent:")
    print("1. Random Agent")
    print("2. Heuristic Agent")
    print("3. Q-Learning Agent")

    while True:
        try:
            choice = input("Enter 1, 2, or 3: ").strip()
            if choice == "1":
                opponent = "random"
                break
            elif choice == "2":
                opponent = "heuristic"
                break
            elif choice == "3":
                opponent = "qlearning"
                break
            else:
                print("Invalid choice! Enter 1, 2, or 3.")
        except:
            print("Invalid input! Please try again.")

    # Create game with human vs chosen AI
    agent_types = ["human", opponent]
    game = GolfGame(num_players=2, agent_types=agent_types)

    print(f"\nYou are playing against: {opponent.upper()} agent")
    print("You are Player 1 (P1)")
    print("Game starting...\n")

    # Play the game
    scores = game.play_game(verbose=True)

    print(f"\n=== GAME OVER ===")
    print(f"Your score: {scores[0]}")
    print(f"AI score: {scores[1]}")

    if scores[0] < scores[1]:
        print("🎉 YOU WIN! 🎉")
    elif scores[0] > scores[1]:
        print("😔 AI wins 😔")
    else:
        print("🤝 It's a tie! 🤝")

def play_human_vs_multiple_ai():
    print("=== HUMAN vs MULTIPLE AI GOLF GAME ===")
    print("You will play against multiple AI agents in a 4-player game.")
    print("Rules: All cards start face-down, each flip makes card public to all players\n")

    # Create 4-player game with human and 3 AI agents
    agent_types = ["human", "random", "heuristic", "qlearning"]
    game = GolfGame(num_players=4, agent_types=agent_types)

    print("You are Player 1 (P1)")
    print("Other players: Random, Heuristic, Q-Learning")
    print("Game starting...\n")

    # Play the game
    scores = game.play_game(verbose=True)

    print(f"\n=== GAME OVER ===")
    print(f"Your score: {scores[0]}")
    print(f"Random AI score: {scores[1]}")
    print(f"Heuristic AI score: {scores[2]}")
    print(f"Q-Learning AI score: {scores[3]}")

    winner_idx = scores.index(min(scores))
    if winner_idx == 0:
        print("🎉 YOU WIN! 🎉")
    else:
        print(f"😔 {agent_types[winner_idx].upper()} agent wins 😔")

if __name__ == "__main__":
    print("Choose game mode:")
    print("1. Human vs 1 AI (2 players)")
    print("2. Human vs 3 AI (4 players)")

    while True:
        try:
            choice = input("Enter 1 or 2: ").strip()
            if choice == "1":
                play_human_vs_ai()
                break
            elif choice == "2":
                play_human_vs_multiple_ai()
                break
            else:
                print("Invalid choice! Enter 1 or 2.")
        except:
            print("Invalid input! Please try again.")