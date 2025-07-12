#!/usr/bin/env python3
"""
Test batch training vs sequential training performance
"""

import time
import torch
from train import train_qlearning_agent_batch

def test_batch_vs_sequential():
    """Compare batch training against sequential training for both CPU and GPU"""

    print("="*80)
    print("CPU vs GPU BATCH vs SEQUENTIAL TRAINING COMPARISON")
    print("="*80)

    # Test parameters
    num_games = 1000
    batch_sizes = [100, 200, 500, 1000]  # batch_size=1 is sequential

    results = {}

    print(f"Testing {num_games} games with different batch sizes...")
    print(f"GPU Available: {torch.cuda.is_available()}")

    # Test CPU training with different batch sizes
    for batch_size in batch_sizes:
        method_name = "Sequential" if batch_size == 1 else f"Batch {batch_size}"
        print(f"\n🔄 Testing CPU {method_name} training...")

        start_time = time.time()
        agent_cpu, stats_cpu = train_qlearning_agent_batch(
            num_games=num_games,
            batch_size=batch_size,
            verbose=False,
            use_gpu=False,  # Force CPU
            progress_report_interval=200
        )
        cpu_time = time.time() - start_time
        cpu_states, cpu_entries = agent_cpu.get_q_table_size()

        results[f'cpu_batch_{batch_size}'] = {
            'time': cpu_time,
            'games_per_sec': num_games / cpu_time,
            'states': cpu_states,
            'entries': cpu_entries,
            'win_rate': stats_cpu['wins'] / num_games
        }

        print(f"CPU {method_name}: {cpu_time:.2f}s ({num_games/cpu_time:.1f} games/sec)")

    # Test GPU training with different batch sizes (if available)
    if torch.cuda.is_available():
        for batch_size in batch_sizes:
            method_name = "Sequential" if batch_size == 1 else f"Batch {batch_size}"
            print(f"\n🚀 Testing GPU {method_name} training...")

            start_time = time.time()
            agent_gpu, stats_gpu = train_qlearning_agent_batch(
                num_games=num_games,
                batch_size=batch_size,
                verbose=False,
                use_gpu=True,  # Use GPU
                progress_report_interval=200
            )
            gpu_time = time.time() - start_time
            gpu_states, gpu_entries = agent_gpu.get_q_table_size()

            results[f'gpu_batch_{batch_size}'] = {
                'time': gpu_time,
                'games_per_sec': num_games / gpu_time,
                'states': gpu_states,
                'entries': gpu_entries,
                'win_rate': stats_gpu['wins'] / num_games
            }

            print(f"GPU {method_name}: {gpu_time:.2f}s ({num_games/gpu_time:.1f} games/sec)")

    # Calculate speedups only if cpu_batch_1 exists
    if 'cpu_batch_1' in results:
        cpu_seq_time = results['cpu_batch_1']['time']
        for key in results:
            if key != 'cpu_batch_1':
                results[key]['speedup_vs_cpu_seq'] = cpu_seq_time / results[key]['time']
    else:
        for key in results:
            results[key]['speedup_vs_cpu_seq'] = None  # Or skip this field

    # Summary
    print(f"\n📊 COMPREHENSIVE PERFORMANCE SUMMARY")
    print(f"{'Method':<20} {'Time(s)':<8} {'Games/s':<8} {'States':<8} {'Entries':<9} {'Win%':<6} {'Speedup':<15}")
    print("-" * 100)

    # CPU results
    for batch_size in batch_sizes:
        key = f'cpu_batch_{batch_size}'
        r = results[key]
        method_name = "Sequential" if batch_size == 1 else f"Batch {batch_size}"
        speedup = r.get('speedup_vs_cpu_seq', 1.0)
        print(f"{'CPU '+method_name:<20} {r['time']:<8.1f} {r['games_per_sec']:<8.1f} {r['states']:<8} {r['entries']:<9} {r['win_rate']*100:<6.1f} {speedup:<15.1f}x")

    # GPU results (if available)
    if torch.cuda.is_available():
        for batch_size in batch_sizes:
            key = f'gpu_batch_{batch_size}'
            r = results[key]
            method_name = "Sequential" if batch_size == 1 else f"Batch {batch_size}"
            speedup = r.get('speedup_vs_cpu_seq', 1.0)
            print(f"{'GPU '+method_name:<20} {r['time']:<8.1f} {r['games_per_sec']:<8.1f} {r['states']:<8} {r['entries']:<9} {r['win_rate']*100:<6.1f} {speedup:<15.1f}x")

    # Find best overall method
    best_method = min(results.keys(), key=lambda x: results[x]['time'])
    best_result = results[best_method]

    print(f"\n🏆 BEST OVERALL PERFORMANCE: {best_method}")
    print(f"   • Time: {best_result['time']:.1f}s")
    print(f"   • Speed: {best_result['games_per_sec']:.1f} games/sec")
    print(f"   • Speedup vs CPU Sequential: {best_result.get('speedup_vs_cpu_seq', 1.0):.1f}x")

    # Find best CPU method
    cpu_methods = [k for k in results.keys() if k.startswith('cpu_')]
    if cpu_methods:
        best_cpu = min(cpu_methods, key=lambda x: results[x]['time'])
        best_cpu_result = results[best_cpu]
        print(f"\n🥇 BEST CPU METHOD: {best_cpu}")
        print(f"   • Speedup vs CPU Sequential: {best_cpu_result.get('speedup_vs_cpu_seq', 1.0):.1f}x")

    # Find best GPU method (if available)
    if torch.cuda.is_available():
        gpu_methods = [k for k in results.keys() if k.startswith('gpu_')]
        if gpu_methods:
            best_gpu = min(gpu_methods, key=lambda x: results[x]['time'])
            best_gpu_result = results[best_gpu]
            print(f"\n🚀 BEST GPU METHOD: {best_gpu}")
            print(f"   • Speedup vs CPU Sequential: {best_gpu_result['speedup_vs_cpu_seq']:.1f}x")

    return results

if __name__ == "__main__":
    results = test_batch_vs_sequential()