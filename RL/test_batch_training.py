#!/usr/bin/env python3
"""
Test batch training vs sequential training performance
"""

import time
import torch
from train import train_qlearning_agent, train_qlearning_agent_batch

def test_batch_vs_sequential():
    """Compare batch training against sequential training"""

    print("="*80)
    print("BATCH vs SEQUENTIAL TRAINING COMPARISON")
    print("="*80)

    # Test parameters
    num_games = 1000
    batch_sizes = [1, 10, 50, 100, 200]

    results = {}

    print(f"Testing {num_games} games with different batch sizes...")
    print(f"GPU Available: {torch.cuda.is_available()}")

    # Test sequential (batch_size=1 equivalent)
    print(f"\n🔄 Testing SEQUENTIAL training...")
    start_time = time.time()
    agent_seq, stats_seq = train_qlearning_agent(
        num_games=num_games,
        verbose=False,
        use_gpu=True,
        progress_report_interval=200
    )
    seq_time = time.time() - start_time
    seq_states, seq_entries = agent_seq.get_q_table_size()

    results['sequential'] = {
        'time': seq_time,
        'games_per_sec': num_games / seq_time,
        'states': seq_states,
        'entries': seq_entries,
        'win_rate': stats_seq['wins'] / num_games
    }

    print(f"Sequential: {seq_time:.2f}s ({num_games/seq_time:.1f} games/sec)")

    # Test different batch sizes
    for batch_size in batch_sizes:
        if batch_size == 1:
            continue  # Skip, already tested sequential

        print(f"\n🚀 Testing BATCH training (batch_size={batch_size})...")
        start_time = time.time()
        agent_batch, stats_batch = train_qlearning_agent_batch(
            num_games=num_games,
            batch_size=batch_size,
            verbose=False,
            use_gpu=True,
            progress_report_interval=200
        )
        batch_time = time.time() - start_time
        batch_states, batch_entries = agent_batch.get_q_table_size()

        results[f'batch_{batch_size}'] = {
            'time': batch_time,
            'games_per_sec': num_games / batch_time,
            'states': batch_states,
            'entries': batch_entries,
            'win_rate': stats_batch['wins'] / num_games,
            'speedup': seq_time / batch_time
        }

        speedup = seq_time / batch_time
        print(f"Batch {batch_size}: {batch_time:.2f}s ({num_games/batch_time:.1f} games/sec) - {speedup:.1f}x speedup")

    # Summary
    print(f"\n📊 PERFORMANCE SUMMARY")
    print(f"{'Method':<15} {'Time(s)':<8} {'Games/s':<8} {'States':<8} {'Entries':<9} {'Win%':<6} {'Speedup':<8}")
    print("-" * 80)

    # Sequential
    r = results['sequential']
    print(f"{'Sequential':<15} {r['time']:<8.1f} {r['games_per_sec']:<8.1f} {r['states']:<8} {r['entries']:<9} {r['win_rate']*100:<6.1f} {'1.0x':<8}")

    # Batch results
    for batch_size in batch_sizes:
        if batch_size == 1:
            continue
        key = f'batch_{batch_size}'
        if key in results:
            r = results[key]
            print(f"{'Batch '+str(batch_size):<15} {r['time']:<8.1f} {r['games_per_sec']:<8.1f} {r['states']:<8} {r['entries']:<9} {r['win_rate']*100:<6.1f} {r['speedup']:<8.1f}x")

    # Find best batch size
    best_batch = max([k for k in results.keys() if k.startswith('batch_')],
                     key=lambda x: results[x]['speedup'])
    best_speedup = results[best_batch]['speedup']
    best_size = best_batch.replace('batch_', '')

    print(f"\n🏆 BEST PERFORMANCE: Batch size {best_size} with {best_speedup:.1f}x speedup")

    return results

if __name__ == "__main__":
    results = test_batch_vs_sequential()