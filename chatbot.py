import json
from typing import Dict, List, Optional, Any
from llm_cerebras import call_cerebras_llm
import random
import os
from bot_personalities import create_bot, BaseBot

class GolfChatbot:
    """Chatbot for the Golf card game with different personalities"""

    def __init__(self, bot_type: str = "Jim Nantz"):
        self.bot_type = bot_type
        self.current_bot = create_bot(bot_type)  # Create bot instance
        self.base_prompt = (
            "CRITICAL: Keep your response to 2 sentences maximum and under 150 characters total.Be extremely concise and direct. This is a chat environment, not an essay.         If your response is too long, it will be truncated."
        )

        # Load rules once
        rules_path = os.path.join(os.path.dirname(__file__), 'game_rules.txt')
        try:
            with open(rules_path, 'r', encoding='utf-8') as f:
                self.game_rules = f.read().strip()
        except Exception as e:
            self.game_rules = "(Game rules unavailable)"

    def get_bot_info(self) -> Dict[str, str]:
        """Get information about the current bot"""
        return {
            "name": self.current_bot.name,
            "description": self.current_bot.description,
            "system_prompt": self.current_bot.get_system_prompt()
        }

    def format_game_state_for_prompt(self, game_state: Dict[str, Any]) -> str:
        """Format the current game state into a readable prompt for the LLM"""
        try:
            # Extract key information from game state
            current_player = game_state.get('current_player', 0)
            players = game_state.get('players', [])
            discard_pile = game_state.get('discard_pile', [])
            deck_size = game_state.get('deck_size', 0)
            round_num = game_state.get('round', 1)
            max_rounds = game_state.get('max_rounds', None)
            game_over = game_state.get('game_over', False)
            scores = game_state.get('scores', [])
            winner_index = game_state.get('winner', None)
            action_history = game_state.get('action_history', [])
            num_actions = len(action_history)
            last_action_str = ""
            if action_history:
                last_action = action_history[-1]
                if isinstance(last_action, dict):
                    player = last_action.get('player', 'Unknown')
                    action_type = last_action.get('action', 'action')
                    card = last_action.get('card', None)
                    card_str = f"{card['rank']}{card['suit']}" if card else ""
                    last_action_str = f"- Most recent action: {player} {action_type} {card_str}".strip()
                else:
                    # If it's a string, just use it directly
                    last_action_str = f"- Most recent action: {last_action}"

            # Format player information
            player_info = []
            for i, player in enumerate(players):
                name = player.get('name', f'Player {i+1}')
                grid = player.get('grid', [])
                score = player.get('score', 0)
                is_current = i == current_player

                # Format grid cards (show only face-up cards for other players)
                if i == 0:  # Human player - show only public cards (no private peeks)
                    grid_str = ", ".join(
                        f"{card['rank']}{card['suit']}" if card and card.get('public') else "?" for card in grid
                    )
                else:  # AI players - show only public cards
                    grid_str = ", ".join(
                        f"{card['rank']}{card['suit']}" if card and card.get('public') else "?" for card in grid
                    )

                player_info.append(f"{name}: {grid_str} (Score: {score}){' [CURRENT TURN]' if is_current else ''}")

            # Format discard pile
            discard_str = "None" if not discard_pile else f"{discard_pile[-1]['rank']}{discard_pile[-1]['suit']}"

            # Winner info
            winner_name = None
            if game_over and winner_index is not None and 0 <= winner_index < len(players):
                winner_name = players[winner_index].get('name', f'Player {winner_index+1}')

            # Build the game state text
            game_state_text = f"""
                Current Game State:
                - Round: {round_num}{f' / {max_rounds}' if max_rounds else ''}
                - Deck size: {deck_size} cards
                - Discard pile top card: {discard_str}
                - Number of actions taken: {num_actions}
                - Players:
                {chr(10).join(f'  {info}' for info in player_info)}
"""
            if scores:
                game_state_text += f"- Scores: {', '.join(str(s) for s in scores)}\n"
            if game_over:
                game_state_text += "- GAME OVER\n"
                if winner_name:
                    game_state_text += f"- Winner: {winner_name}\n"
                else:
                    game_state_text += "- Winner: Unknown\n"
                game_state_text += f"- Total rounds played: {round_num}\n"
                game_state_text += f"- Final scores: {', '.join(f'{players[i].get('name', f'Player {i+1}')}={scores[i]}' for i in range(len(players)))}\n"
                game_state_text += f"- Total actions taken: {num_actions}\n"
            if last_action_str:
                game_state_text += last_action_str + "\n"

            return game_state_text

        except Exception as e:
            return f"Error formatting game state: {str(e)}"

    def generate_response(self, user_message: str, game_state: Optional[Dict[str, Any]] = None, personality: str = None, proactive: bool = False, return_prompt: bool = False) -> str:
        """Generate a chatbot response based on user input and game state"""

        if personality is None:
            personality = self.bot_type  # fallback to default

        # Update the current bot if personality changed
        if personality != self.bot_type:
            self.current_bot = create_bot(personality)
            self.bot_type = personality

        bot_info = self.get_bot_info()
        system_prompt = bot_info["system_prompt"]

        # Update emotional state based on current game performance
        if game_state:
            self.current_bot.update_emotional_state(game_state)

        # Build the context
        context = system_prompt + "\n\n" + "Game Rules:\n" + self.game_rules + "\n\n"

        if game_state:
            context += self.format_game_state_for_prompt(game_state) + "\n\n"

        # Add emotional context for more realistic responses
        emotional_context = self.current_bot.get_emotional_context()
        context += emotional_context + "\n\n"

        # Add situational context
        situational_context = self.current_bot.get_situational_context(game_state)
        if situational_context:
            context += situational_context + "\n\n"

        # Add response style context for personality-driven responses
        style_context = self.current_bot.get_response_style_context()
        context += style_context + "\n\n"

        # Always add the base prompt
        context += self.base_prompt + "\n"

        if proactive:
            # For proactive responses, we don't have a user message
            context += "Provide a brief, relevant comment about the current game situation."
        else:
            # Add conversation history for context
            if self.current_bot.conversation_history:
                context += "Recent conversation:\n"
                for msg in self.current_bot.conversation_history[-3:]:  # Last 3 messages
                    context += f"{msg['role']}: {msg['content']}\n"
                context += "\n"

            context += f"User: {user_message}\n"
            context += f"{bot_info['name']}:"

        try:
            # Call the LLM
            response = call_cerebras_llm(
                prompt=context,
                model="llama3.1-8b",
                structured=False,
                stream=True,
                temperature=0.7
            )

            # Clean up the response
            if response.startswith(f"{bot_info['name']}:"):
                response = response[len(f"{bot_info['name']}:"):].strip()

            # Enforce character limit (150 characters)
            if len(response) > 150:
                response = response[:147] + "..."

            # Ensure response ends with proper punctuation
            if response and not response[-1] in '.!?:':
                response += "."

            # Store in conversation history
            if not proactive:
                self.current_bot.conversation_history.append({"role": "user", "content": user_message})
                self.current_bot.conversation_history.append({"role": "assistant", "content": response})

                # Keep only last 10 messages to prevent context from getting too long
                if len(self.current_bot.conversation_history) > 10:
                    self.current_bot.conversation_history = self.current_bot.conversation_history[-10:]

            if return_prompt:
                return response, context
            else:
                return response

        except Exception as e:
            if return_prompt:
                return f"Sorry, I'm having trouble responding right now. Error: {str(e)}", context
            else:
                return f"Sorry, I'm having trouble responding right now. Error: {str(e)}"

    def generate_proactive_comment(self, game_state: Dict[str, Any], event_type: str = "general", return_prompt: bool = False) -> Optional[str]:
        """Generate a proactive comment based on game events"""

        print(f"DEBUG: generate_proactive_comment called with event_type: {event_type}")
        print(f"DEBUG: Current bot_type: {self.bot_type}")

        # Use the bot's proactive behavior system
        import time
        current_time = time.time()

        if not self.current_bot.should_make_proactive_comment(event_type, game_state, current_time):
            print("DEBUG: Bot decided not to make a proactive comment")
            return None

        print("DEBUG: Bot decided to make a proactive comment")

        # Record the comment
        self.current_bot.record_proactive_comment(current_time)

        bot_info = self.get_bot_info()

        # Create event-specific prompts
        event_prompts = {
            "turn_start": f"Comment briefly on the start of {bot_info['name']}'s turn. Be encouraging or strategic.",
            "card_drawn": "Comment briefly on the card that was just drawn. Give a quick strategic insight.",
            "card_played": "Comment briefly on the card that was just played. Note if it was a good or risky move.",
            "score_update": "Comment briefly on the score change. Be encouraging or analytical.",
            "game_over": (
                "The game has ended. Summarize the game, announce the winner by name, "
                "and provide a brief, memorable closing comment in the style of a Masters broadcast."
            ),
            "general": "Provide a brief, relevant comment about the current game situation. Focus more on the current and latest moves"
        }

        prompt = event_prompts.get(event_type, event_prompts["general"])

        try:
            context = f"{bot_info['system_prompt']}\n\n"
            context += self.format_game_state_for_prompt(game_state) + "\n\n"

            # Add emotional and situational context
            emotional_context = self.current_bot.get_emotional_context()
            context += emotional_context + "\n\n"

            situational_context = self.current_bot.get_situational_context(game_state)
            if situational_context:
                context += situational_context + "\n\n"

            # Add response style context
            style_context = self.current_bot.get_response_style_context()
            context += style_context + "\n\n"

            context += prompt

            # Always add the base prompt
            context += self.base_prompt + "\n"

            response = call_cerebras_llm(
                prompt=context,
                model="llama3.1-8b",
                structured=False,
                stream=False,
                temperature=0.8
            )

            print(f"DEBUG: Generated proactive comment: {response.strip()}")
            if return_prompt:
                return response.strip(), context
            else:
                return response.strip()

        except Exception as e:
            print(f"DEBUG: Error generating proactive comment: {e}")
            if return_prompt:
                return None, ""
            else:
                return None

    def change_personality(self, new_type: str) -> bool:
        """Change the chatbot personality"""
        print(f"DEBUG: Attempting to change personality to: {new_type}")
        try:
            self.current_bot = create_bot(new_type)
            self.bot_type = new_type
            print(f"DEBUG: Successfully changed personality to: {new_type}")
            return True
        except Exception as e:
            print(f"DEBUG: Failed to change personality - {new_type}: {e}")
            return False

    def reset_for_new_game(self):
        """Reset bot state for a new game"""
        self.current_bot.reset_for_new_game()

    def get_available_personalities(self) -> List[Dict[str, str]]:
        """Get list of available personalities"""
        # Define the allowed personalities
        allowed_bots = ["Jim Nantz", "Tiger Woods", "Happy Gilmore", "Peter Parker", "Shooter McGavin"]
        return [
            {
                "type": bot_name,
                "name": bot_name,
                "description": create_bot(bot_name).description
            }
            for bot_name in allowed_bots
        ]

# Create a global chatbot instance
chatbot = GolfChatbot("Jim Nantz")