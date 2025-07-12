#!/usr/bin/env python3
"""
Simple test of batch training functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch
from train import train_qlearning_agent_batch

def simple_batch_test():
    """Test batch training with a small number of games"""

    print("="*50)
    print("SIMPLE BATCH TRAINING TEST")
    print("="*50)

    print(f"GPU Available: {torch.cuda.is_available()}")

    # Test batch training with 50 games, batch size 10
    print(f"\n🚀 Testing batch training (50 games, batch_size=10)...")
    agent, stats = train_qlearning_agent_batch(
        num_games=50,
        batch_size=10,
        verbose=True,
        use_gpu=True,
        progress_report_interval=20
    )

    states, entries = agent.get_q_table_size()
    win_rate = stats['wins'] / 50

    print(f"\n✅ BATCH TRAINING COMPLETE!")
    print(f"   • Win rate: {win_rate:.2%} ({stats['wins']}/50)")
    print(f"   • Q-table: {states} states, {entries} entries")
    print(f"   • GPU used: {hasattr(agent, 'device')}")

    if hasattr(agent, 'device'):
        print(f"   • Device: {agent.device}")

if __name__ == "__main__":
    simple_batch_test()