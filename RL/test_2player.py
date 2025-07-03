from simulation import run_simulations_with_training, print_simulation_results

print("=== TESTING 2-PLAYER Q-LEARNING ===")

# Test 1: Q-learning vs Random
print("\n1. Q-learning vs Random (2 players):")
stats1 = run_simulations_with_training(5000, ['qlearning', 'random'], verbose=False)
print(f"Q-learning win rate: {stats1['win_rates']['qlearning']:.2%}")
print(f"Q-learning average score: {stats1['average_scores']['qlearning']:.2f}")
print(f"Random average score: {stats1['average_scores']['random']:.2f}")

# Test 2: Q-learning vs Heuristic
print("\n2. Q-learning vs Heuristic (2 players):")
stats2 = run_simulations_with_training(5000, ['qlearning', 'heuristic'], verbose=False)
print(f"Q-learning win rate: {stats2['win_rates']['qlearning']:.2%}")
print(f"Q-learning average score: {stats2['average_scores']['qlearning']:.2f}")
print(f"Heuristic average score: {stats2['average_scores']['heuristic']:.2f}")

# Test 3: Q-learning vs Q-learning (self-play)
print("\n3. Q-learning vs Q-learning (self-play, 2 players):")
stats3 = run_simulations_with_training(5000, ['qlearning', 'qlearning'], verbose=False)
print(f"Q-learning 1 win rate: {stats3['win_rates']['qlearning']:.2%}")
print(f"Q-learning average score: {stats3['average_scores']['qlearning']:.2f}")

# Show learning progress for first test
if 'score_by_interval' in stats1 and 'qlearning' in stats1['score_by_interval']:
    intervals = stats1['score_by_interval']['qlearning']
    if len(intervals) >= 2:
        first_avg = intervals[0]['avg_score']
        last_avg = intervals[-1]['avg_score']
        improvement = first_avg - last_avg
        print(f"\nQ-learning improvement vs Random: {improvement:+.2f} points ({first_avg:.2f} → {last_avg:.2f})")

print("\n=== SUMMARY ===")
print("If Q-learning can't beat random in 2-player games, there's a fundamental issue.")
print("If it can beat random but not heuristic, the learning is working but needs improvement.")
print("If it can beat heuristic, the approach is working well!")