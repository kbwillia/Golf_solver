#!/usr/bin/env python3
"""
Demonstrate performance benefits of batch training for millions of states
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import torch
from train import train_qlearning_agent_batch

def demonstrate_batch_performance():
    """Demonstrate how batch training performs with different batch sizes"""

    print("="*70)
    print("BATCH TRAINING PERFORMANCE DEMONSTRATION")
    print("="*70)

    print(f"GPU Available: {torch.cuda.is_available()}")

    # Test different batch sizes
    batch_sizes = [1, 10, 50, 100]
    num_games = 300

    results = []

    for batch_size in batch_sizes:
        print(f"\n{'='*50}")
        print(f"Testing batch_size = {batch_size}")
        print(f"{'='*50}")

        start_time = time.time()
        agent, stats = train_qlearning_agent_batch(
            num_games=num_games,
            batch_size=batch_size,
            verbose=False,  # Reduce output for cleaner comparison
            use_gpu=torch.cuda.is_available(),  # Use GPU if available
            progress_report_interval=max(100, batch_size * 2)
        )
        total_time = time.time() - start_time

        states, entries = agent.get_q_table_size()
        win_rate = stats['wins'] / num_games
        games_per_second = num_games / total_time

        result = {
            'batch_size': batch_size,
            'total_time': total_time,
            'games_per_second': games_per_second,
            'states': states,
            'entries': entries,
            'win_rate': win_rate
        }
        results.append(result)

        print(f"   Time: {total_time:.2f}s")
        print(f"   Games/sec: {games_per_second:.1f}")
        print(f"   States: {states:,}")
        print(f"   Entries: {entries:,}")
        print(f"   Win rate: {win_rate:.1%}")

    # Performance summary
    print(f"\n{'='*70}")
    print("PERFORMANCE SUMMARY")
    print(f"{'='*70}")
    print(f"{'Batch Size':<12} {'Time(s)':<10} {'Games/s':<10} {'States':<10} {'Speedup':<10}")
    print("-" * 70)

    baseline_time = results[0]['total_time']  # batch_size = 1

    for result in results:
        speedup = baseline_time / result['total_time']
        print(f"{result['batch_size']:<12} {result['total_time']:<10.2f} {result['games_per_second']:<10.1f} {result['states']:<10,} {speedup:<10.1f}x")

    # Key insights
    best_result = max(results, key=lambda x: x['games_per_second'])
    print(f"\n🚀 BEST PERFORMANCE: Batch size {best_result['batch_size']} achieved {best_result['games_per_second']:.1f} games/sec")
    print(f"📈 SPEEDUP: {baseline_time / best_result['total_time']:.1f}x faster than sequential training")

    # Memory efficiency insight
    states_per_game = best_result['states'] / num_games
    print(f"🧠 STATE GROWTH: ~{states_per_game:.1f} unique states per game")
    print(f"💾 TOTAL STATES: {best_result['states']:,} states explored")

    print(f"\n💡 For your millions of states scenario:")
    print(f"   • Batch training reduces GPU memory transfer overhead")
    print(f"   • Vectorized Q-table updates process multiple states simultaneously")
    print(f"   • Batch sizes of 50-100 games work well for most scenarios")
    print(f"   • GPU acceleration becomes more beneficial with larger state spaces")

    return results

if __name__ == "__main__":
    results = demonstrate_batch_performance()