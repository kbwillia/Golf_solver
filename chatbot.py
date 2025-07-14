import json
from typing import Dict, List, Optional, Any
from llm_cerebras import call_cerebras_llm
import random

class GolfChatbot:
    """Chatbot for the Golf card game with different personalities"""

    def __init__(self, bot_type: str = "helpful"):
        self.bot_type = bot_type
        self.conversation_history = []
        self.base_prompt = (
            "Respond in 2 sentences or less. Be concise and clear. Limit your answer to 200 characters."
        )
        self.personalities = {

            "helpful": {
                "name": "Golf Coach",
                "description": "A helpful golf coach who provides guidance and encouragement",
                "system_prompt": "You are a helpful golf coach assistant for the Golf card game. You provide clear guidance, explain strategies, and encourage players to improve their game. Be supportive, educational, and focus on helping players understand the game better."
            },
            "competitive": {
                "name": "Pro Golfer",
                "description": "A competitive professional golfer who gives tactical advice",
                "system_prompt": "You are a competitive professional golfer assistant for the Golf card game. You provide tactical advice, analyze game situations, and help players think strategically. Be confident, analytical, and focus on winning strategies."
            },
            "funny": {
                "name": "Golf Buddy",
                "description": "A fun and entertaining golf buddy who makes jokes and keeps spirits high",
                "system_prompt": "You are a fun golf buddy assistant for the Golf card game. You provide advice with humor, make jokes about the game, and keep the player entertained. Be witty, encouraging, and make the game more enjoyable."
            },
            "analytical": {
                "name": "Game Analyst",
                "description": "A data-driven analyst who provides detailed statistical insights",
                "system_prompt": "You are a game analyst assistant for the Golf card game. You provide detailed statistical analysis, probability calculations, and data-driven insights. Be precise, analytical, and focus on the mathematical aspects of the game."
            },
            "nantz": {
                "name": "Jim Nantz",
                "description": "Legendary golf broadcaster, known for poetic, warm, and iconic Masters commentary.",
                "system_prompt": (
                    "You are Jim Nantz, the legendary golf broadcaster. "
                    "Your commentary is poetic, warm, and full of iconic Masters phrases. "
                    "Use phrases like 'A tradition unlike any other', 'Hello friends', and 'The Masters on CBS'. "
                    "Offer insightful, gentle, and memorable golf commentary, as if narrating the Masters. "
                    "Speak directly to the audience, never to a player. "
                    "Keep it brief, elegant, and in the style of a live broadcast."
                )
            }
        }

    def get_bot_info(self) -> Dict[str, str]:
        """Get information about the current bot"""
        return self.personalities.get(self.bot_type, self.personalities["helpful"])

    def format_game_state_for_prompt(self, game_state: Dict[str, Any]) -> str:
        """Format the current game state into a readable prompt for the LLM"""
        try:
            # Extract key information from game state
            current_player = game_state.get('current_player', 0)
            players = game_state.get('players', [])
            discard_pile = game_state.get('discard_pile', [])
            deck_size = game_state.get('deck_size', 0)
            round_num = game_state.get('round', 1)

            # Format player information
            player_info = []
            for i, player in enumerate(players):
                name = player.get('name', f'Player {i+1}')
                hand = player.get('hand', [])
                score = player.get('score', 0)
                is_current = i == current_player

                # Format hand cards (show only face-up cards for other players)
                if i == 0:  # Human player - show all cards
                    hand_str = ", ".join([f"{card['rank']}{card['suit']}" for card in hand])
                else:  # AI players - show only face-up cards
                    visible_cards = [f"{card['rank']}{card['suit']}" for card in hand if card.get('visible', False)]
                    hidden_cards = ["?"] * (len(hand) - len(visible_cards))
                    hand_str = ", ".join(visible_cards + hidden_cards)

                player_info.append(f"{name}: {hand_str} (Score: {score}){' [CURRENT TURN]' if is_current else ''}")

            # Format discard pile
            discard_str = "None" if not discard_pile else f"{discard_pile[-1]['rank']}{discard_pile[-1]['suit']}"

            game_state_text = f"""
Current Game State:
- Round: {round_num}
- Deck size: {deck_size} cards
- Discard pile top card: {discard_str}
- Players:
{chr(10).join(f"  {info}" for info in player_info)}
"""
            return game_state_text

        except Exception as e:
            return f"Error formatting game state: {str(e)}"

    def generate_response(self, user_message: str, game_state: Optional[Dict[str, Any]] = None, proactive: bool = False) -> str:
        """Generate a chatbot response based on user input and game state"""

        bot_info = self.get_bot_info()
        system_prompt = bot_info["system_prompt"]

        # Build the context
        context = system_prompt + "\n\n"

        if game_state:
            context += self.format_game_state_for_prompt(game_state) + "\n\n"

        # Always add the base prompt
        context += self.base_prompt + "\n"

        if proactive:
            # For proactive responses, we don't have a user message
            context += "Provide a brief, relevant comment about the current game situation."
        else:
            # Add conversation history for context
            if self.conversation_history:
                context += "Recent conversation:\n"
                for msg in self.conversation_history[-3:]:  # Last 3 messages
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
                stream=False,
                temperature=0.7
            )

            # Clean up the response
            if response.startswith(f"{bot_info['name']}:"):
                response = response[len(f"{bot_info['name']}:"):].strip()

            # Store in conversation history
            if not proactive:
                self.conversation_history.append({"role": "user", "content": user_message})
                self.conversation_history.append({"role": "assistant", "content": response})

                # Keep only last 10 messages to prevent context from getting too long
                if len(self.conversation_history) > 10:
                    self.conversation_history = self.conversation_history[-10:]

            return response

        except Exception as e:
            return f"Sorry, I'm having trouble responding right now. Error: {str(e)}"

    def generate_proactive_comment(self, game_state: Dict[str, Any], event_type: str = "general") -> Optional[str]:
        """Generate a proactive comment based on game events"""

        print(f"DEBUG: generate_proactive_comment called with event_type: {event_type}")
        print(f"DEBUG: Current bot_type: {self.bot_type}")

        # Define when to make proactive comments (80% chance for Jim Nantz)
        random_val = random.random()
        print(f"DEBUG: Random value: {random_val}, threshold: 0.2")
        if random_val > 0.2:
            print("DEBUG: Skipping comment due to random chance")
            return None

        bot_info = self.get_bot_info()

        # Create event-specific prompts
        event_prompts = {
            "turn_start": f"Comment briefly on the start of {bot_info['name']}'s turn. Be encouraging or strategic.",
            "card_drawn": "Comment briefly on the card that was just drawn. Give a quick strategic insight.",
            "card_played": "Comment briefly on the card that was just played. Note if it was a good or risky move.",
            "score_update": "Comment briefly on the score change. Be encouraging or analytical.",
            "game_over": "Comment briefly on the game ending. Congratulate the winner or encourage improvement.",
            "general": "Provide a brief, relevant comment about the current game situation."
        }

        prompt = event_prompts.get(event_type, event_prompts["general"])

        try:
            context = f"{bot_info['system_prompt']}\n\n"
            context += self.format_game_state_for_prompt(game_state) + "\n\n"
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
            return response.strip()

        except Exception as e:
            print(f"DEBUG: Error generating proactive comment: {e}")
            return None

    def change_personality(self, new_type: str) -> bool:
        """Change the chatbot personality"""
        print(f"DEBUG: Attempting to change personality to: {new_type}")
        if new_type in self.personalities:
            self.bot_type = new_type
            self.conversation_history = []  # Clear history when changing personality
            print(f"DEBUG: Successfully changed personality to: {new_type}")
            return True
        else:
            print(f"DEBUG: Failed to change personality - {new_type} not found in {list(self.personalities.keys())}")
            return False

    def get_available_personalities(self) -> List[Dict[str, str]]:
        """Get list of available personalities"""
        return [
            {"type": bot_type, "name": info["name"], "description": info["description"]}
            for bot_type, info in self.personalities.items()
        ]

# Global chatbot instance
chatbot = GolfChatbot("helpful")