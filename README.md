# Golf Game Simulation Suite with Q-Learning

A comprehensive simulation framework for the 4-card Golf card game, featuring multiple AI agents including reinforcement learning.

## Project Structure

The codebase is organized into modular components for better maintainability:

### Core Files

- **`models.py`** - Core data structures
  - `Card` class: Represents playing cards with scoring logic
  - `Player` class: Manages player state, grid, and memory tracking

- **`agents.py`** - AI agent implementations
  - `RandomAgent`: Makes random legal moves
  - `HeuristicAgent`: Uses probability-based strategy from original solver
  - `QLearningAgent`: Reinforcement learning agent that learns from experience

- **`game.py`** - Game logic and simulation
  - `GolfGame` class: Manages game state, turns, and scoring
  - Handles deck creation, dealing, and turn execution

- **`simulation.py`** - Simulation and statistics
  - `run_simulations_with_training()`: Runs games with Q-learning training
  - `run_simulations()`: Runs games without training
  - `print_simulation_results()`: Displays formatted results
  - `plot_learning_curves()`: Visualizes learning progress

- **`main.py`** - Main entry point
  - Demonstrates all features with examples
  - Single game example, training simulations, and comparisons

## Features

### Multiple Agent Types

1. **Random Agent**: Makes random legal moves
2. **Heuristic Agent**: Uses sophisticated probability calculations and memory tracking
3. **Q-Learning Agent**: Learns optimal strategies through reinforcement learning

### Q-Learning Implementation

- **State Representation**: Simplified, position-agnostic states for better generalization
- **Reward System**: Strong signals (+10 for winning, -5 to +2 based on score)
- **Training**: Persistent Q-tables with epsilon-greedy exploration
- **Learning Curves**: Track performance improvements over time

### Advanced Statistics

- Win rates and average scores by agent type
- Learning progress tracking with intervals
- Q-table size monitoring
- Perfect game counts and score distributions
- Optional matplotlib visualization

## Usage

### Basic Usage

```python
from game import GolfGame
from simulation import run_simulations_with_training

# Single game example
game = GolfGame(num_players=4, agent_types=["heuristic", "random", "qlearning", "random"])
scores = game.play_game(verbose=True)

# Run training simulations
stats = run_simulations_with_training(num_games=1000, agent_types=["heuristic", "random", "qlearning", "random"])
```

### Command Line

```bash
# Run main demonstration
python main.py

# Run specific test
python test_rewards.py
```

## Game Rules

4-Card Golf is a card game where:
- Each player has a 2x2 grid of cards
- Bottom two cards are face-up initially
- Players take turns drawing from deck or taking from discard pile
- Goal: Minimize total score (pairs cancel each other out)
- A=1, J=0, Q/K=10, number cards = face value
- Game lasts exactly 4 rounds

## Key Improvements

### Reward System
- **Original**: Weak rewards (+1 win, -0.25 to -1.0 for losing)
- **Improved**: Strong signals (+10 win, -5 to +2 based on score)

### State Representation
- **Original**: Complex, position-specific states with suits
- **Improved**: Simplified, position-agnostic states (ranks only)

### Learning Progress
- Detailed tracking of Q-table growth
- Interval-based average score monitoring
- Learning curve visualization

## Results

The improved Q-learning agent shows:
- **Learning**: Consistent improvement over time (+0.22 to +0.70 points)
- **Performance**: Competitive with random agents (18-19 average score)
- **Win Rate**: ~20% in 4-player games
- **Memory**: Efficient state representation (1500+ states learned)

## Dependencies

- Python 3.6+
- numpy
- matplotlib (optional, for plotting)
- collections (built-in)
- itertools (built-in)
- random (built-in)

## Installation

```bash
pip install numpy matplotlib
```

## Future Enhancements

- Deep Q-Learning with neural networks
- Multi-agent competitive training
- Tournament-style evaluations
- Strategy analysis tools
- Web interface for game visualization