import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import os

# Create output directory if it doesn't exist
output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')
os.makedirs(output_dir, exist_ok=True)

def get_output_path(filename):
    """Helper function to get full path for output files"""
    return os.path.join(output_dir, filename)

def plot_qtable_growth(games, states, entries, scores, save_filename="qtable_growth.png"):
    """Plot Q-table growth charts"""
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 10))

    # Plot 1: States over time
    ax1.plot(games, states, 'b-', linewidth=2, marker='o', markersize=4)
    ax1.set_xlabel('Games Played')
    ax1.set_ylabel('Number of States')
    ax1.set_title('Q-table State Count Growth')
    ax1.grid(True, alpha=0.3)

    # Plot 2: Entries over time
    ax2.plot(games, entries, 'g-', linewidth=2, marker='s', markersize=4)
    ax2.set_xlabel('Games Played')
    ax2.set_ylabel('Number of State-Action Pairs')
    ax2.set_title('Q-table Entry Count(SA Pairs) Growth')
    ax2.grid(True, alpha=0.3)

    # Plot 3: Performance over time (moving average)
    if len(scores) > 5:
        # Calculate moving average
        window = min(5, len(scores))
        moving_avg = np.convolve(scores, np.ones(window)/window, mode='valid')
        games_avg = games[window-1:]
        ax3.plot(games, scores, 'r-', alpha=0.3, label='Individual')
        ax3.plot(games_avg, moving_avg, 'r-', linewidth=2, label='Moving Avg')
        ax3.legend()
    else:
        ax3.plot(games, scores, 'r-', linewidth=2, marker='^', markersize=4)

    ax3.set_xlabel('Games Played')
    ax3.set_ylabel('Score')
    ax3.set_title('Performance Over Time')
    ax3.grid(True, alpha=0.3)
    ax3.invert_yaxis()  # Lower scores are better

    # Plot 4: Actions per state
    actions_per_state = [e/s if s > 0 else 0 for e, s in zip(entries, states)]
    ax4.plot(games, actions_per_state, 'm-', linewidth=2, marker='d', markersize=4)
    ax4.set_xlabel('Games Played')
    ax4.set_ylabel('Actions per State')
    ax4.set_title('Q-table Density')
    ax4.grid(True, alpha=0.3)

    plt.tight_layout()
    output_path = get_output_path(save_filename)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\nPlots saved to {output_path}")
    plt.show()

def plot_qtable_state_and_entry_growth(games, states, entries, save_filename="qtable_state_entry_growth.png"):
    """
    Plot Q-table state count and entry count growth on the same plot.
    """
    import matplotlib.pyplot as plt
    output_path = get_output_path(save_filename)
    fig, ax1 = plt.subplots(figsize=(10, 6))

    color1 = 'tab:blue'
    color2 = 'tab:green'

    ax1.set_xlabel('Games Played')
    ax1.set_ylabel('Number of States', color=color1)
    l1 = ax1.plot(games, states, color=color1, linewidth=2, marker='o', markersize=4, label='Number of States')
    ax1.tick_params(axis='y', labelcolor=color1)
    ax1.set_title('Q-table State and Entry Count Growth')
    ax1.grid(True, alpha=0.3)

    ax2 = ax1.twinx()
    ax2.set_ylabel('Number of State-Action Pairs', color=color2)
    l2 = ax2.plot(games, entries, color=color2, linewidth=2, marker='s', markersize=4, label='State-Action Pairs')
    ax2.tick_params(axis='y', labelcolor=color2)

    # Combine legends
    lines = l1 + l2
    labels = [line.get_label() for line in lines]
    ax1.legend(lines, labels, loc='upper left')

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\nCombined state/entry growth plot saved to {output_path}")
    plt.show()

def plot_qvalue_distribution(q_table, save_filename="qvalue_distribution.png"):
    """Plot Q-value distribution"""
    if not q_table:
        print("No Q-table data to plot!")
        return

    # Extract all Q-values
    all_qvalues = [q for actions in q_table.values() for q in actions.values()]

    if not all_qvalues:
        print("No Q-values found!")
        return

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    # Histogram of Q-values
    ax1.hist(all_qvalues, bins=30, alpha=0.7, edgecolor='black')
    ax1.set_xlabel('Q-value')
    ax1.set_ylabel('Frequency')
    ax1.set_title('Q-value Distribution')
    ax1.grid(True, alpha=0.3)

    # Box plot of Q-values
    ax2.boxplot(all_qvalues)
    ax2.set_ylabel('Q-value')
    ax2.set_title('Q-value Box Plot')
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    output_path = get_output_path(save_filename)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Q-value distribution plots saved to {output_path}")
    plt.show()

def plot_action_type_tracking(trajectory, round_info=False, save_filename="action_type_tracking.png"):
    """
    Track and visualize the count of each action type from the trajectory as a line graph.

    Args:
        trajectory: List of trajectory steps, each containing 'action', 'game', and 'round' keys
        round_info: If True, separate actions by round (12 action types). If False, just 3 action types.
        save_filename: Output filename for the plot
    """
    if not trajectory:
        print("No trajectory data to plot!")
        return

    # Extract action types and their counts over time
    action_counts = {}
    game_numbers = []

    if round_info:
        # Initialize 12 action type counters (3 actions × 4 rounds)
        current_counts = {}
        for action_type in ['take_discard', 'draw_deck_keep', 'draw_deck_discard_flip']:
            for round_num in range(1, 5):  # Rounds 1-4
                current_counts[f'{action_type}_r{round_num}'] = 0
    else:
        # Initialize 3 action type counters
        current_counts = {
            'take_discard': 0,
            'draw_deck_keep': 0,
            'draw_deck_discard_flip': 0
        }

    # Track cumulative counts for each game
    for step in trajectory:
        action = step['action']
        game_num = step.get('game', 0)
        round_num = step.get('round', 1)

        # Categorize action type
        if action['type'] == 'take_discard':
            if round_info:
                current_counts[f'take_discard_r{round_num}'] += 1
            else:
                current_counts['take_discard'] += 1
        elif action['type'] == 'draw_deck':
            if action.get('keep', True):
                if round_info:
                    current_counts[f'draw_deck_keep_r{round_num}'] += 1
                else:
                    current_counts['draw_deck_keep'] += 1
            else:
                if round_info:
                    current_counts[f'draw_deck_discard_flip_r{round_num}'] += 1
                else:
                    current_counts['draw_deck_discard_flip'] += 1

        # Store counts for this game
        if game_num not in game_numbers:
            game_numbers.append(game_num)
            action_counts[game_num] = current_counts.copy()

    # Convert to lists for plotting
    games = sorted(action_counts.keys())

    # Create the plot
    plt.figure(figsize=(15, 10) if round_info else (12, 8))

    # Define color shades for each action type by round
    blue_shades = ['#1f77b4', '#3399ff', '#0055cc', '#66b3ff']
    green_shades = ['#2ca02c', '#66cc66', '#228B22', '#98fb98']
    red_shades = ['#d62728', '#ff6666', '#b22222', '#ff9999']

    # Define markers for different rounds
    markers = ['o', 's', '^', 'd']

    if round_info:
        # Plot 12 action types (3 actions × 4 rounds)
        for i, action_type in enumerate(['take_discard', 'draw_deck_keep', 'draw_deck_discard_flip']):
            if action_type == 'take_discard':
                color_list = blue_shades
            elif action_type == 'draw_deck_keep':
                color_list = green_shades
            else:
                color_list = red_shades
            for round_num in range(1, 5):
                action_key = f'{action_type}_r{round_num}'
                counts = [action_counts[game][action_key] for game in games]

                # Create label
                if action_type == 'take_discard':
                    label = f'Take from Discard (R{round_num})'
                elif action_type == 'draw_deck_keep':
                    label = f'Draw & Keep (R{round_num})'
                else:
                    label = f'Draw, Discard & Flip (R{round_num})'

                plt.plot(games, counts, linewidth=2, marker=markers[round_num-1],
                        markersize=4, label=label, color=color_list[round_num-1],
                        alpha=0.9)
    else:
        # Plot 3 action types
        take_discard_counts = [action_counts[game]['take_discard'] for game in games]
        draw_keep_counts = [action_counts[game]['draw_deck_keep'] for game in games]
        draw_discard_flip_counts = [action_counts[game]['draw_deck_discard_flip'] for game in games]

        plt.plot(games, take_discard_counts, 'b-', linewidth=2, marker='o', markersize=4,
                 label='Take from Discard', color='blue')
        plt.plot(games, draw_keep_counts, 'g-', linewidth=2, marker='s', markersize=4,
                 label='Draw from Deck & Keep', color='green')
        plt.plot(games, draw_discard_flip_counts, 'r-', linewidth=2, marker='^', markersize=4,
                 label='Draw from Deck, Discard & Flip', color='red')

    plt.xlabel('Game Number')
    plt.ylabel('Cumulative Action Count')
    title = 'Action Type Usage Over Time'
    if round_info:
        title += ' (by Round)'
    plt.title(title)
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left') if round_info else plt.legend()
    plt.grid(True, alpha=0.3)

    # Add some statistics
    total_actions = len(trajectory)

    if round_info:
        # Calculate statistics for each round
        stats_text = f'Total Actions: {total_actions}\n\n'
        for round_num in range(1, 5):
            round_actions = [step for step in trajectory if step.get('round') == round_num]
            round_total = len(round_actions)
            if round_total > 0:
                take_discard = sum(1 for step in round_actions if step['action']['type'] == 'take_discard')
                draw_keep = sum(1 for step in round_actions
                               if step['action']['type'] == 'draw_deck' and step['action'].get('keep', True))
                draw_discard_flip = sum(1 for step in round_actions
                                       if step['action']['type'] == 'draw_deck' and not step['action'].get('keep', True))

                stats_text += f'Round {round_num}: {round_total} actions\n'
                stats_text += f'  Take: {take_discard} ({take_discard/round_total*100:.1f}%)\n'
                stats_text += f'  Draw&Keep: {draw_keep} ({draw_keep/round_total*100:.1f}%)\n'
                stats_text += f'  Draw&Flip: {draw_discard_flip} ({draw_discard_flip/round_total*100:.1f}%)\n\n'
    else:
        # Calculate overall statistics
        total_take_discard = sum(1 for step in trajectory if step['action']['type'] == 'take_discard')
        total_draw_keep = sum(1 for step in trajectory
                             if step['action']['type'] == 'draw_deck' and step['action'].get('keep', True))
        total_draw_discard_flip = sum(1 for step in trajectory
                                     if step['action']['type'] == 'draw_deck' and not step['action'].get('keep', True))

        stats_text = f'Total Actions: {total_actions}\n'
        stats_text += f'Take from Discard: {total_take_discard} ({total_take_discard/total_actions*100:.1f}%)\n'
        stats_text += f'Draw & Keep: {total_draw_keep} ({total_draw_keep/total_actions*100:.1f}%)\n'
        stats_text += f'Draw, Discard & Flip: {total_draw_discard_flip} ({total_draw_discard_flip/total_actions*100:.1f}%)'

    plt.text(0.02, 0.98, stats_text, transform=plt.gca().transAxes,
             verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8),
             fontsize=8 if round_info else 10)

    plt.tight_layout()
    output_path = get_output_path(save_filename)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Action type tracking plot saved to {output_path}")
    plt.show()

    return action_counts
