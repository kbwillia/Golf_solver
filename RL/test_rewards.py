from simulation import run_simulations_with_training

print("Running 100 games with improved reward system...")
stats = run_simulations_with_training(100, ['random', 'heuristic', 'qlearning', 'random'], verbose=False)

print("\n=== RESULTS ===")
print(f"Q-learning agent final average score: {stats['average_scores']['qlearning']:.2f}")
print(f"Q-learning agent win rate: {stats['win_rates']['qlearning']:.2%}")
print(f"Heuristic agent average score: {stats['average_scores']['heuristic']:.2f}")
print(f"Heuristic agent win rate: {stats['win_rates']['heuristic']:.2%}")
print(f"Random agent average score: {stats['average_scores']['random']:.2f}")
print(f"Random agent win rate: {stats['win_rates']['random']:.2%}")

# Show learning progress
if 'score_by_interval' in stats and 'qlearning' in stats['score_by_interval']:
    intervals = stats['score_by_interval']['qlearning']
    if len(intervals) >= 2:
        first_avg = intervals[0]['avg_score']
        last_avg = intervals[-1]['avg_score']
        improvement = first_avg - last_avg
        print(f"\nQ-learning improvement: {improvement:+.2f} points ({first_avg:.2f} → {last_avg:.2f})")