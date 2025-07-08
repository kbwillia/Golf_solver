# #!/usr/bin/env python3
# """
# Quick test of Q-learning performance (100 games)
# """


# import time
# from game import GolfGame
# from models import Player
# from agents import RandomAgent, HeuristicAgent, QLearningAgent, EVAgent

# # create a function that input a list of agents and number of games and returns the average score of the agents
# def quick_test(agent_types, num_games):
#     num_agents = len(agent_types)
#     total_scores = [0] * num_agents

#     for _ in range(num_games):
#         game = GolfGame(num_players=num_agents, agent_types=agent_types)
#         scores = game.play_game(verbose=False)
#         for i, score in enumerate(scores):
#             total_scores[i] += score

#     avg_scores = [total / num_games for total in total_scores]
#     print(f"Average scores over {num_games} games:")
#     for agent, avg in zip(agent_types, avg_scores):
#         print(f"  {agent}: {avg:.2f}")





# if __name__ == "__main__":
#     quick_test(["ev_ai", "random", "ev_ai", "ev_ai"], 1000)