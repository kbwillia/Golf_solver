#!/usr/bin/env python3
"""
Test script for AdvancedEVAgent
Demonstrates the advanced features like pair-aware flipping and trajectory recording
"""

from game import GolfGame
from agents import AdvancedEVAgent
import json

def test_advanced_ev_agent():
    """Test the AdvancedEVAgent with a simple game scenario"""
    print("=== Testing AdvancedEVAgent ===\n")

    # Create a game with AdvancedEVAgent
    game = GolfGame(num_players=2, agent_types=["advanced_ev", "random"])

    # Set up a specific scenario for testing pair awareness
    print("Setting up test scenario...")

    # Manually set up a scenario where the AdvancedEVAgent has a potential pair
    # This is just for demonstration - in real games the cards would be dealt randomly

    # Let's look at what the agent can see and analyze
    advanced_agent = game.agents[0]
    player = game.players[0]

    print(f"Player: {player.name}")
    print(f"Agent type: {player.agent_type}")
    print(f"Current grid: {player.grid}")
    print(f"Known cards: {player.known}")

    # Test the pair analysis feature
    print("\n=== Testing Pair Analysis ===")
    pair_analysis = advanced_agent._analyze_potential_pairs(player)
    print(f"Pair analysis: {json.dumps(pair_analysis, indent=2, default=str)}")

    # Test the visible cards feature
    print("\n=== Testing Visible Cards ===")
    visible_cards = advanced_agent._get_visible_cards(player)
    print(f"Visible cards: {json.dumps(visible_cards, indent=2, default=str)}")

    # Test decision making
    print("\n=== Testing Decision Making ===")
    available_positions = [i for i, known in enumerate(player.known) if not known]
    print(f"Available positions: {available_positions}")

    if available_positions:
        # Get EV analysis
        from probabilities import expected_value_draw_vs_discard
        ev = expected_value_draw_vs_discard(game, player)
        print(f"EV analysis: {json.dumps(ev, indent=2, default=str)}")

        # Test advanced decision making
        action = advanced_agent._advanced_decision_making(player, game, ev, available_positions)
        print(f"Chosen action: {action}")

        # Check decision history
        print(f"\nDecision history length: {len(advanced_agent.decision_history)}")
        if advanced_agent.decision_history:
            print(f"Latest decision: {json.dumps(advanced_agent.decision_history[-1], indent=2, default=str)}")

    print("\n=== AdvancedEVAgent Test Complete ===")

def test_trajectory_recording():
    """Test that the AdvancedEVAgent properly records trajectories"""
    print("\n=== Testing Trajectory Recording ===")

    game = GolfGame(num_players=2, agent_types=["advanced_ev", "random"])
    advanced_agent = game.agents[0]
    player = game.players[0]

    # Create a trajectory list
    trajectory = []

    # Simulate a few turns to see trajectory recording
    for turn in range(3):
        print(f"\nTurn {turn + 1}:")

        # Get available positions
        available_positions = [i for i, known in enumerate(player.known) if not known]
        if not available_positions:
            print("No available positions")
            break

        # Choose action with trajectory recording
        action = advanced_agent.choose_action(player, game, trajectory)
        print(f"Action chosen: {action}")
        print(f"Trajectory length: {len(trajectory)}")

        # Simulate the action (simplified)
        if action and action['type'] == 'take_discard' and game.discard_pile:
            pos = action['position']
            if pos < len(player.grid) and not player.known[pos]:
                player.known[pos] = True
                print(f"Revealed card at position {pos}: {player.grid[pos]}")

        # Check decision history
        print(f"Decision history entries: {len(advanced_agent.decision_history)}")

    print(f"\nFinal trajectory: {json.dumps(trajectory, indent=2, default=str)}")
    print(f"Final decision history: {len(advanced_agent.decision_history)} entries")

if __name__ == "__main__":
    test_advanced_ev_agent()
    test_trajectory_recording()