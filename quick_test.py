#!/usr/bin/env python3
"""
Quick test of Q-learning performance (100 games)
"""

from RL.simulation import run_simulations_with_training
import time

def quick_test():
    print("=== QUICK Q-LEARNING TEST (100 games) ===")

    start_time = time.time()

    stats = run_simulations_with_training(
        num_games=100,
        agent_types=['random', 'qlearning'],
        verbose=False
    )

    end_time = time.time()

    print(f"Completed in {end_time - start_time:.1f} seconds")

    # Results
    q_score = stats['average_scores']['qlearning']
    random_score = stats['average_scores']['random']
    q_wins = stats['win_rates']['qlearning']
    improvement = random_score - q_score

    print(f"\nRESULTS:")
    print(f"Q-learning: {q_score:.2f} avg score, {q_wins:.1%} win rate")
    print(f"Random:     {random_score:.2f} avg score")
    print(f"Improvement: {improvement:+.2f} points")

    # Learning curve
    if 'score_by_interval' in stats and 'qlearning' in stats['score_by_interval']:
        intervals = stats['score_by_interval']['qlearning']
        if len(intervals) >= 2:
            first_avg = intervals[0]['avg_score']
            last_avg = intervals[-1]['avg_score']
            learning = first_avg - last_avg
            print(f"Learning: {first_avg:.2f} → {last_avg:.2f} ({learning:+.2f})")

    # Q-table size
    if 'q_learning_progress' in stats and stats['q_learning_progress']:
        final_progress = stats['q_learning_progress'][-1][1]
        if 'qlearning_1' in final_progress:
            states = final_progress['qlearning_1']['states']
            entries = final_progress['qlearning_1']['entries']
            print(f"Q-table: {states:,} states, {entries:,} entries")

    # Assessment
    if improvement > 0.5:
        print("✓ Q-learning working well!")
    elif improvement > 0.1:
        print("⚠ Q-learning shows improvement")
    else:
        print("✗ Q-learning needs tuning")

if __name__ == "__main__":
    quick_test()