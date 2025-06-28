from game import GolfGame
from simulation import run_simulations_with_training, run_simulations, print_simulation_results, plot_learning_curves

def main():
    print("=== GOLF GAME SIMULATION SUITE WITH Q-LEARNING ===")

    # Example 1: Single game with different agents
    print("\n1. Single game example:")
    agent_types = ["heuristic", "random", "qlearning", "random"]
    game = GolfGame(num_players=4, agent_types=agent_types)
    game.play_game(verbose=True)

    # Example 2: Run simulations with Q-learning training
    print("\n2. Running simulations with Q-learning training...")
    stats = run_simulations_with_training(num_games=1000, agent_types=agent_types, verbose=True)
    print_simulation_results(stats)

    # Example 3: Plot learning curves
    print("\n3. Plotting learning curves...")
    plot_learning_curves(stats)

    # Example 4: Compare trained vs untrained Q-learning
    print("\n4. Comparing trained vs untrained Q-learning:")

    # Untrained Q-learning
    print("\nUntrained Q-learning vs Random:")
    stats_untrained = run_simulations(num_games=20000, agent_types=["qlearning", "random"], verbose=False)
    print_simulation_results(stats_untrained)

    # Trained Q-learning
    print("\nTrained Q-learning vs Random:")
    stats_trained = run_simulations_with_training(num_games=20000, agent_types=["qlearning", "random"], verbose=False)
    print_simulation_results(stats_trained)

if __name__ == "__main__":
    main()