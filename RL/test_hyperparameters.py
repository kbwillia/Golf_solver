#!/usr/bin/env python3
"""
Test different Q-learning hyperparameters to find optimal settings
"""

from simulation import run_simulations_with_training
from agents import QLearningAgent
from game import GolfGame
import itertools

def test_hyperparameters():
    """Test different combinations of hyperparameters"""
    print("=== HYPERPARAMETER TESTING ===\n")

    # Parameter ranges to test
    learning_rates = [0.05, 0.1, 0.2]
    discount_factors = [0.8, 0.9, 0.95]
    epsilons = [0.1, 0.2, 0.3]

    best_improvement = -999
    best_params = None
    best_stats = None

    print("Testing hyperparameter combinations...")
    print("lr=learning_rate, df=discount_factor, eps=epsilon\n")

    for lr, df, eps in itertools.product(learning_rates, discount_factors, epsilons):
        print(f"Testing lr={lr}, df={df}, eps={eps}...", end=" ")

        # Create custom Q-learning agent with these parameters
        custom_agent = QLearningAgent(
            learning_rate=lr,
            discount_factor=df,
            epsilon=eps
        )

        # Run shorter test (100 games for speed)
        stats = run_simulations_with_training(
            num_games=100,
            agent_types=['random', 'qlearning'],
            verbose=False
        )

        # Calculate improvement
        q_score = stats['average_scores']['qlearning']
        random_score = stats['average_scores']['random']
        improvement = random_score - q_score

        print(f"improvement: {improvement:+.2f}")

        if improvement > best_improvement:
            best_improvement = improvement
            best_params = (lr, df, eps)
            best_stats = stats

    print(f"\n=== BEST PARAMETERS ===")
    print(f"Learning Rate: {best_params[0]}")
    print(f"Discount Factor: {best_params[1]}")
    print(f"Epsilon: {best_params[2]}")
    print(f"Improvement: {best_improvement:+.2f} points")

    return best_params, best_stats

def test_reward_structures():
    """Test different reward structures"""
    print("\n=== REWARD STRUCTURE TESTING ===")

    # Note: This would require modifying the simulation code
    # For now, just document what we could test
    print("Potential reward structures to test:")
    print("1. Current: Win=+10, Good score=+2, Bad score=-5")
    print("2. Simple: Win=+1, Lose=-1")
    print("3. Score-based: reward = -(final_score)")
    print("4. Relative: reward based on rank among players")
    print("\nThis would require modifying simulation.py reward calculation")

if __name__ == "__main__":
    best_params, best_stats = test_hyperparameters()
    test_reward_structures()