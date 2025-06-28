import numpy as np
from collections import defaultdict
from game import GolfGame
from agents import QLearningAgent

def run_simulations_with_training(num_games=1000, agent_types=None, verbose=False):
    """
    Run multiple simulations with Q-learning training

    Args:
        num_games: Number of games to simulate
        agent_types: List of agent types for each player
        verbose: Whether to print detailed output for each game

    Returns:
        Dictionary with simulation results and statistics
    """
    if agent_types is None:
        agent_types = ["random", "heuristic", "qlearning", "random"]

    num_players = len(agent_types)

    # Create persistent Q-learning agents
    q_agents = []
    for i, agent_type in enumerate(agent_types):
        if agent_type == "qlearning":
            q_agents.append(QLearningAgent(epsilon=0.2))  # Higher epsilon for more exploration
        else:
            q_agents.append(None)

    # Statistics tracking
    stats = {
        'total_games': num_games,
        'agent_types': agent_types,
        'wins_by_agent': defaultdict(int),
        'scores_by_agent': defaultdict(list),
        'average_scores': {},
        'win_rates': {},
        'score_distributions': defaultdict(list),
        'game_durations': [],
        'q_learning_progress': [],
        'learning_curves': defaultdict(list),  # Track scores over time
        'score_by_interval': defaultdict(list)  # Track average scores by intervals
    }

    print(f"Running {num_games} simulations with agents: {agent_types}")
    print("Q-learning agents will learn from experience!")

    # Track scores for learning curves
    interval_size = max(1, num_games // 20)  # 20 intervals for tracking

    for game_num in range(num_games):
        if verbose and game_num % 100 == 0:
            print(f"Game {game_num + 1}/{num_games}")

        # Create trajectories for Q-learning agents
        trajectories = []
        for i in range(num_players):
            if agent_types[i] == "qlearning":
                trajectories.append([])
            else:
                trajectories.append(None)

        # Create and play game
        game = GolfGame(num_players=num_players, agent_types=agent_types, q_agents=q_agents)
        scores = game.play_game(verbose=False, trajectories=trajectories)

        # Train Q-learning agents
        winner_idx = scores.index(min(scores))
        for i, agent_type in enumerate(agent_types):
            if agent_type == "qlearning" and trajectories[i]:
                # Calculate reward: stronger signals for learning
                if i == winner_idx:
                    reward = 10.0  # Big reward for winning
                else:
                    # Stronger negative reward based on score
                    # Lower scores should have higher rewards
                    if scores[i] <= 5:
                        reward = 2.0  # Good score
                    elif scores[i] <= 10:
                        reward = 0.0  # Average score
                    elif scores[i] <= 15:
                        reward = -2.0  # Bad score
                    else:
                        reward = -5.0  # Very bad score

                q_agents[i].train_on_trajectory(trajectories[i], reward, scores[i])

                # Decay epsilon for better learning
                if game_num % 100 == 0:  # Decay every 100 games
                    q_agents[i].decay_epsilon()

        # Record results
        winner_agent = agent_types[winner_idx]
        stats['wins_by_agent'][winner_agent] += 1

        # Record scores for each agent
        for i, score in enumerate(scores):
            agent_type = agent_types[i]
            stats['scores_by_agent'][agent_type].append(score)
            stats['score_distributions'][agent_type].append(score)

            # Track learning curves (every game)
            stats['learning_curves'][agent_type].append(score)

        # Record game duration (number of rounds)
        stats['game_durations'].append(game.round)

        # Track Q-learning progress and scores by intervals
        if game_num % 100 == 0 or game_num == num_games - 1:
            q_progress = {}
            for i, agent_type in enumerate(agent_types):
                if agent_type == "qlearning":
                    states, entries = q_agents[i].get_q_table_size()
                    q_progress[f"qlearning_{i}"] = {"states": states, "entries": entries}
            stats['q_learning_progress'].append((game_num, q_progress))

        # Track average scores by intervals
        if (game_num + 1) % interval_size == 0 or game_num == num_games - 1:
            interval_start = max(0, game_num - interval_size + 1)
            interval_end = game_num + 1

            for i, agent_type in enumerate(agent_types):
                if agent_type in stats['scores_by_agent']:
                    interval_scores = stats['scores_by_agent'][agent_type][interval_start:interval_end]
                    avg_score = np.mean(interval_scores)
                    stats['score_by_interval'][agent_type].append({
                        'interval': len(stats['score_by_interval'][agent_type]) + 1,
                        'games': f"{interval_start+1}-{interval_end}",
                        'avg_score': avg_score,
                        'min_score': min(interval_scores),
                        'max_score': max(interval_scores)
                    })

    # Calculate final statistics
    for agent_type in agent_types:
        if agent_type in stats['scores_by_agent']:
            scores = stats['scores_by_agent'][agent_type]
            stats['average_scores'][agent_type] = np.mean(scores)
            stats['win_rates'][agent_type] = stats['wins_by_agent'][agent_type] / num_games

    return stats

def run_simulations(num_games=1000, agent_types=None, verbose=False):
    """
    Run multiple simulations and collect statistics (without Q-learning training)

    Args:
        num_games: Number of games to simulate
        agent_types: List of agent types for each player
        verbose: Whether to print detailed output for each game

    Returns:
        Dictionary with simulation results and statistics
    """
    if agent_types is None:
        agent_types = ["random", "heuristic", "qlearning", "random"]

    num_players = len(agent_types)

    # Statistics tracking
    stats = {
        'total_games': num_games,
        'agent_types': agent_types,
        'wins_by_agent': defaultdict(int),
        'scores_by_agent': defaultdict(list),
        'average_scores': {},
        'win_rates': {},
        'score_distributions': defaultdict(list),
        'game_durations': []
    }

    print(f"Running {num_games} simulations with agents: {agent_types}")

    for game_num in range(num_games):
        if verbose and game_num % 100 == 0:
            print(f"Game {game_num + 1}/{num_games}")

        # Create and play game
        game = GolfGame(num_players=num_players, agent_types=agent_types)
        scores = game.play_game(verbose=False)

        # Record results
        winner_idx = scores.index(min(scores))
        winner_agent = agent_types[winner_idx]
        stats['wins_by_agent'][winner_agent] += 1

        # Record scores for each agent
        for i, score in enumerate(scores):
            agent_type = agent_types[i]
            stats['scores_by_agent'][agent_type].append(score)
            stats['score_distributions'][agent_type].append(score)

        # Record game duration (number of rounds)
        stats['game_durations'].append(game.round)

    # Calculate final statistics
    for agent_type in agent_types:
        if agent_type in stats['scores_by_agent']:
            scores = stats['scores_by_agent'][agent_type]
            stats['average_scores'][agent_type] = np.mean(scores)
            stats['win_rates'][agent_type] = stats['wins_by_agent'][agent_type] / num_games

    return stats

def print_simulation_results(stats):
    """Print formatted simulation results"""
    print("\n" + "="*60)
    print("SIMULATION RESULTS")
    print("="*60)
    print(f"Total games: {stats['total_games']}")
    print(f"Agents: {stats['agent_types']}")

    print("\nWIN RATES:")
    for agent_type in stats['agent_types']:
        win_rate = stats['win_rates'].get(agent_type, 0)
        wins = stats['wins_by_agent'].get(agent_type, 0)
        print(f"  {agent_type}: {win_rate:.2%} ({wins} wins)")

    print("\nAVERAGE SCORES:")
    for agent_type in stats['agent_types']:
        avg_score = stats['average_scores'].get(agent_type, 0)
        scores = stats['scores_by_agent'].get(agent_type, [])
        if scores:
            min_score = min(scores)
            max_score = max(scores)
            print(f"  {agent_type}: {avg_score:.2f} (range: {min_score}-{max_score})")

    print(f"\nAverage game duration: {np.mean(stats['game_durations']):.1f} rounds")

    # Show Q-learning progress if available
    if 'q_learning_progress' in stats and stats['q_learning_progress']:
        print("\nQ-LEARNING PROGRESS:")
        for game_num, progress in stats['q_learning_progress']:
            print(f"  Game {game_num}: {progress}")

    # Show learning curves and score intervals
    if 'score_by_interval' in stats:
        print("\nLEARNING CURVES (Score by Intervals):")
        for agent_type in stats['agent_types']:
            if agent_type in stats['score_by_interval'] and stats['score_by_interval'][agent_type]:
                print(f"\n  {agent_type.upper()} LEARNING PROGRESS:")
                intervals = stats['score_by_interval'][agent_type]

                # Show first few, middle, and last intervals
                to_show = []
                if len(intervals) <= 6:
                    to_show = intervals
                else:
                    to_show = intervals[:3] + intervals[len(intervals)//2-1:len(intervals)//2+1] + intervals[-3:]

                for interval in to_show:
                    print(f"    Interval {interval['interval']} (Games {interval['games']}): "
                          f"Avg={interval['avg_score']:.2f}, Range={interval['min_score']}-{interval['max_score']}")

                # Show overall improvement
                if len(intervals) >= 2:
                    first_avg = intervals[0]['avg_score']
                    last_avg = intervals[-1]['avg_score']
                    improvement = first_avg - last_avg
                    print(f"    Overall improvement: {improvement:+.2f} points "
                          f"({first_avg:.2f} → {last_avg:.2f})")

    # Show some interesting statistics
    print("\nDETAILED ANALYSIS:")
    for agent_type in stats['agent_types']:
        scores = stats['scores_by_agent'].get(agent_type, [])
        if scores:
            perfect_games = sum(1 for s in scores if s == 0)
            print(f"  {agent_type}: {perfect_games} perfect games (score = 0)")

            # Score distribution
            score_counts = defaultdict(int)
            for score in scores:
                score_counts[score] += 1
            most_common_score = max(score_counts.items(), key=lambda x: x[1])
            print(f"    Most common score: {most_common_score[0]} (occurred {most_common_score[1]} times)")

            # For Q-learning agents, show learning trend
            if agent_type == "qlearning" and 'learning_curves' in stats:
                learning_curve = stats['learning_curves'][agent_type]
                if len(learning_curve) >= 100:
                    first_100_avg = np.mean(learning_curve[:100])
                    last_100_avg = np.mean(learning_curve[-100:])
                    trend = first_100_avg - last_100_avg
                    print(f"    Learning trend: {trend:+.2f} points improvement "
                          f"({first_100_avg:.2f} → {last_100_avg:.2f})")

def plot_learning_curves(stats):
    """Plot learning curves for visualization (if matplotlib is available)"""
    try:
        import matplotlib.pyplot as plt

        plt.figure(figsize=(12, 8))

        for agent_type in stats['agent_types']:
            if agent_type in stats['learning_curves']:
                scores = stats['learning_curves'][agent_type]
                games = list(range(1, len(scores) + 1))

                # Plot individual scores with low alpha
                plt.scatter(games, scores, alpha=0.1, s=1, label=f'{agent_type} (individual)')

                # Plot moving average
                window_size = max(1, len(scores) // 50)  # 50 points for moving average
                if len(scores) >= window_size:
                    moving_avg = []
                    for i in range(len(scores)):
                        start = max(0, i - window_size // 2)
                        end = min(len(scores), i + window_size // 2 + 1)
                        moving_avg.append(np.mean(scores[start:end]))
                    plt.plot(games, moving_avg, linewidth=2, label=f'{agent_type} (moving avg)')

        plt.xlabel('Game Number')
        plt.ylabel('Score')
        plt.title('Learning Curves - Score vs Game Number')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.ylim(bottom=0)  # Scores can't be negative

        # Save plot
        plt.savefig('golf_learning_curves.png', dpi=300, bbox_inches='tight')
        print("\nLearning curves plot saved as 'golf_learning_curves.png'")
        plt.show()

    except ImportError:
        print("\nMatplotlib not available. Install with 'pip install matplotlib' to see learning curves plot.")