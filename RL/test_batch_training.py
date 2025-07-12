#!/usr/bin/env python3
"""
Test batch training vs sequential training performance
"""

import time
import torch
from train import train_qlearning_agent, train_qlearning_agent_batch

def test_batch_vs_sequential():
    """Compare batch training against sequential training for both CPU and GPU"""

    print("="*80)
    print("CPU vs GPU BATCH vs SEQUENTIAL TRAINING COMPARISON")
    print("="*80)

    # Test parameters
    num_games = 1000
    batch_sizes = [1, 50, 100, 200]

    results = {}

    print(f"Testing {num_games} games with different batch sizes...")
    print(f"GPU Available: {torch.cuda.is_available()}")

    # Test CPU Sequential (baseline)
    print(f"\n🔄 Testing CPU SEQUENTIAL training...")
    start_time = time.time()
    agent_cpu_seq, stats_cpu_seq = train_qlearning_agent(
        num_games=num_games,
        verbose=False,
        use_gpu=False,  # Force CPU
        progress_report_interval=200
    )
    cpu_seq_time = time.time() - start_time
    cpu_seq_states, cpu_seq_entries = agent_cpu_seq.get_q_table_size()

    results['cpu_sequential'] = {
        'time': cpu_seq_time,
        'games_per_sec': num_games / cpu_seq_time,
        'states': cpu_seq_states,
        'entries': cpu_seq_entries,
        'win_rate': stats_cpu_seq['wins'] / num_games
    }

    print(f"CPU Sequential: {cpu_seq_time:.2f}s ({num_games/cpu_seq_time:.1f} games/sec)")

    # Test CPU Batch Training
    for batch_size in batch_sizes:
        if batch_size == 1:
            continue  # Skip, already tested sequential

        print(f"\n🔄 Testing CPU BATCH training (batch_size={batch_size})...")
        start_time = time.time()
        agent_cpu_batch, stats_cpu_batch = train_qlearning_agent_batch(
            num_games=num_games,
            batch_size=batch_size,
            verbose=False,
            use_gpu=False,  # Force CPU
            progress_report_interval=200
        )
        cpu_batch_time = time.time() - start_time
        cpu_batch_states, cpu_batch_entries = agent_cpu_batch.get_q_table_size()

        results[f'cpu_batch_{batch_size}'] = {
            'time': cpu_batch_time,
            'games_per_sec': num_games / cpu_batch_time,
            'states': cpu_batch_states,
            'entries': cpu_batch_entries,
            'win_rate': stats_cpu_batch['wins'] / num_games,
            'speedup_vs_cpu_seq': cpu_seq_time / cpu_batch_time
        }

        speedup = cpu_seq_time / cpu_batch_time
        print(f"CPU Batch {batch_size}: {cpu_batch_time:.2f}s ({num_games/cpu_batch_time:.1f} games/sec) - {speedup:.1f}x speedup")

    # Test GPU Sequential (if available)
    if torch.cuda.is_available():
        print(f"\n🚀 Testing GPU SEQUENTIAL training...")
        start_time = time.time()
        agent_gpu_seq, stats_gpu_seq = train_qlearning_agent(
            num_games=num_games,
            verbose=False,
            use_gpu=True,  # Use GPU
            progress_report_interval=200
        )
        gpu_seq_time = time.time() - start_time
        gpu_seq_states, gpu_seq_entries = agent_gpu_seq.get_q_table_size()

        results['gpu_sequential'] = {
            'time': gpu_seq_time,
            'games_per_sec': num_games / gpu_seq_time,
            'states': gpu_seq_states,
            'entries': gpu_seq_entries,
            'win_rate': stats_gpu_seq['wins'] / num_games,
            'speedup_vs_cpu_seq': cpu_seq_time / gpu_seq_time
        }

        speedup = cpu_seq_time / gpu_seq_time
        print(f"GPU Sequential: {gpu_seq_time:.2f}s ({num_games/gpu_seq_time:.1f} games/sec) - {speedup:.1f}x speedup vs CPU")

        # Test GPU Batch Training
        for batch_size in batch_sizes:
            if batch_size == 1:
                continue  # Skip, already tested sequential

            print(f"\n🚀 Testing GPU BATCH training (batch_size={batch_size})...")
            start_time = time.time()
            agent_gpu_batch, stats_gpu_batch = train_qlearning_agent_batch(
                num_games=num_games,
                batch_size=batch_size,
                verbose=False,
                use_gpu=True,  # Use GPU
                progress_report_interval=200
            )
            gpu_batch_time = time.time() - start_time
            gpu_batch_states, gpu_batch_entries = agent_gpu_batch.get_q_table_size()

            results[f'gpu_batch_{batch_size}'] = {
                'time': gpu_batch_time,
                'games_per_sec': num_games / gpu_batch_time,
                'states': gpu_batch_states,
                'entries': gpu_batch_entries,
                'win_rate': stats_gpu_batch['wins'] / num_games,
                'speedup_vs_cpu_seq': cpu_seq_time / gpu_batch_time,
                'speedup_vs_gpu_seq': gpu_seq_time / gpu_batch_time
            }

            speedup_vs_cpu = cpu_seq_time / gpu_batch_time
            speedup_vs_gpu = gpu_seq_time / gpu_batch_time
            print(f"GPU Batch {batch_size}: {gpu_batch_time:.2f}s ({num_games/gpu_batch_time:.1f} games/sec) - {speedup_vs_cpu:.1f}x vs CPU, {speedup_vs_gpu:.1f}x vs GPU seq")

    # Summary
    print(f"\n📊 COMPREHENSIVE PERFORMANCE SUMMARY")
    print(f"{'Method':<20} {'Time(s)':<8} {'Games/s':<8} {'States':<8} {'Entries':<9} {'Win%':<6} {'Speedup':<15}")
    print("-" * 100)

    # CPU Sequential (baseline)
    r = results['cpu_sequential']
    print(f"{'CPU Sequential':<20} {r['time']:<8.1f} {r['games_per_sec']:<8.1f} {r['states']:<8} {r['entries']:<9} {r['win_rate']*100:<6.1f} {'1.0x':<15}")

    # CPU Batch results
    for batch_size in batch_sizes:
        if batch_size == 1:
            continue
        key = f'cpu_batch_{batch_size}'
        if key in results:
            r = results[key]
            print(f"{'CPU Batch '+str(batch_size):<20} {r['time']:<8.1f} {r['games_per_sec']:<8.1f} {r['states']:<8} {r['entries']:<9} {r['win_rate']*100:<6.1f} {r['speedup_vs_cpu_seq']:<15.1f}x")

    # GPU results (if available)
    if torch.cuda.is_available():
        # GPU Sequential
        r = results['gpu_sequential']
        print(f"{'GPU Sequential':<20} {r['time']:<8.1f} {r['games_per_sec']:<8.1f} {r['states']:<8} {r['entries']:<9} {r['win_rate']*100:<6.1f} {r['speedup_vs_cpu_seq']:<15.1f}x")

        # GPU Batch results
        for batch_size in batch_sizes:
            if batch_size == 1:
                continue
            key = f'gpu_batch_{batch_size}'
            if key in results:
                r = results[key]
                print(f"{'GPU Batch '+str(batch_size):<20} {r['time']:<8.1f} {r['games_per_sec']:<8.1f} {r['states']:<8} {r['entries']:<9} {r['win_rate']*100:<6.1f} {r['speedup_vs_cpu_seq']:<15.1f}x")

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