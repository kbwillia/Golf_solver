import json
from typing import Dict, List, Optional, Any
# Import from same directory
from llm_cerebras import call_cerebras_llm
import random
import os
from bot_personalities import create_bot, BaseBot
from game_state import get_game_state
import re
LAST_X_MESSAGES = 10

class GolfChatbot:
    """Chatbot for the Golf card game with different personalities"""

    def __init__(self, bot_type: str = "Jim Nantz"):
        self.bot_type = bot_type
        self.current_bot = create_bot(bot_type)  # Create bot instance
        self.base_prompt = (
            "CRITICAL: Keep your response to 2 sentences maximum and under 150 characters total.Be extremely concise. This is a chat environment, not an essay. ."
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
                - Discard pile top card: {discard_str}
                - Number of actions taken: {num_actions}
                - Players:
                {chr(10).join(f'  {info}' for info in player_info)}
"""
            if game_state.get('probabilities'):
                game_state_text += f"- Probabilities: {game_state['probabilities']}\n"

            if game_state.get('current_player_ev_analysis'):
                game_state_text += f"- EV Analysis: {game_state['current_player_ev_analysis']}\n"

            if game_state.get('action_history'):
                game_state_text += f"- Action History: {game_state['action_history']}\n"

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

        # Print the system prompt for investigation
        print(f"🔧 SYSTEM PROMPT for {bot_info['name']}:")
        print(f"🔧 {system_prompt}")
        print(f"🔧 Bot type: {self.bot_type}")
        print(f"🔧 Bot description: {self.current_bot.description}")

        # Update emotional state based on current game performance (enhanced version)
        if game_state:
            self.current_bot.update_emotional_state_advanced(game_state)

        # Always add system prompt and rules ONCE at the top
        context = system_prompt + "\n\n" + "Game Rules:\n" + self.game_rules + "\n\n"

        if game_state:
            context += self.format_game_state_for_prompt(game_state) + "\n\n"

        # Add dynamic emotional and personality context
        dynamic_context = self.current_bot.get_dynamic_response_context(game_state)
        context += dynamic_context + "\n\n"

        # Add enhanced response style context
        style_context = self.current_bot.get_response_style_context()
        context += style_context + "\n\n"

        # Add personality-specific prompt additions
        if game_state:
            personality_additions = self.current_bot.generate_personality_specific_prompt_additions("gameplay")
        else:
            personality_additions = self.current_bot.generate_personality_specific_prompt_additions("general")

        if personality_additions:
            context += personality_additions + "\n\n"

        # Add situational context
        situational_context = self.current_bot.get_situational_context(game_state)
        if situational_context:
            context += situational_context + "\n\n"

        # Always add the base prompt
        context += self.base_prompt + "\n"

        if proactive:
            # For proactive responses, we don't have a user message
            context += "Provide a brief, relevant comment about the current game situation."
        else:
            # Add conversation history for context (but never the rules again)
            if self.current_bot.conversation_history:
                context += "Recent conversation:\n"
                for msg in self.current_bot.conversation_history[-LAST_X_MESSAGES:]:  # Last 3 messages
                    context += f"{msg['role']}: {msg['content']}\n"
                context += "\n"

            context += f"User: {user_message}\n"
            context += f"{bot_info['name']}:"

        try:
            # Print the full prompt being sent to the LLM
            print(f"🤖 LLM PROMPT (model: llama3.1-8b, structured: False, stream: True, temp: 0.7):")
            print(f"🤖 {'='*80}")
            print(f"🤖 {context}")
            print(f"🤖 {'='*80}")

            # Adjust temperature based on personality
            personality_modifiers = self.current_bot.get_personality_modifiers()
            base_temperature = 0.7

            # More confident bots use lower temperature (more consistent)
            # More excited/humorous bots use higher temperature (more creative)
            temp_adjustment = (personality_modifiers["excitement_modifier"] +
                             personality_modifiers["humor_modifier"] -
                             personality_modifiers["confidence_modifier"]) * 0.2

            adjusted_temperature = max(0.3, min(1.0, base_temperature + temp_adjustment))

            # Call the LLM with personality-adjusted temperature
            response = call_cerebras_llm(
                prompt=context,
                model="llama3.1-8b",
                structured=False,
                stream=True,
                temperature=adjusted_temperature
            )

            # Clean up the response
            if response.startswith(f"{bot_info['name']}:"):
                response = response[len(f"{bot_info['name']}:"):].strip()

            # Apply personality-based response length limits
            verbosity = self.current_bot.response_config.get("verbosity", 0.5)
            if verbosity < 0.3:
                max_length = 100
            elif verbosity > 0.7:
                max_length = 250
            else:
                max_length = 150

            # Enforce character limit based on verbosity
            if len(response) > max_length:
                response = response[:max_length-3] + "..."

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
            # Print the system prompt for investigation
            print(f"🔧 PROACTIVE SYSTEM PROMPT for {bot_info['name']}:")
            print(f"🔧 {bot_info['system_prompt']}")
            print(f"🔧 Event type: {event_type}")

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

            # Print the full prompt being sent to the LLM
            print(f"🤖 LLM PROMPT (model: llama3.1-8b, structured: False, stream: False, temp: 0.8):")
            print(f"🤖 {'='*80}")
            print(f"🤖 {context}")
            print(f"🤖 {'='*80}")

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

    def reset_for_new_game(self):
        """Reset bot state for a new game"""
        self.current_bot.reset_for_new_game()

    def get_available_personalities(self) -> List[Dict[str, str]]:
        """Get list of available personalities"""
        from bot_personalities import get_all_custom_bots

        # Define the allowed personalities
        allowed_bots = ["Jim Nantz", "Tiger Woods", "Happy Gilmore", "Peter Parker", "Shooter McGavin"]
        personalities = [
            {
                "type": bot_name,
                "name": bot_name,
                "description": create_bot(bot_name).description
            }
            for bot_name in allowed_bots
        ]

        # Add custom bots
        custom_bots = get_all_custom_bots()
        for bot_id, bot_data in custom_bots.items():
            personalities.append({
                "type": bot_id,  # Use bot_id as the type
                "name": bot_data["name"],
                "description": bot_data["description"]
            })

        return personalities

    def generate_enhanced_response_with_gif(self, user_message: str, game_state: Optional[Dict[str, Any]] = None, personality: str = None) -> Dict[str, Any]:
        """Generate an enhanced response that may include GIF suggestions"""

        # Generate the normal response
        response = self.generate_response(user_message, game_state, personality)

        # Check if bot should send a GIF
        should_gif = self.current_bot.should_send_gif()

        result = {
            "message": response,
            "bot_name": self.current_bot.name,
            "should_send_gif": should_gif,
            "personality_info": {
                "confidence": self.current_bot.emotional_state.get("confidence", 0.5),
                "excitement": self.current_bot.emotional_state.get("excitement", 0.5),
                "frustration": self.current_bot.emotional_state.get("frustration", 0.0),
                "verbosity": self.current_bot.response_config.get("verbosity", 0.5),
                "humor_level": self.current_bot.response_config.get("humor_level", 0.3),
                "formality": self.current_bot.response_config.get("formality", 0.5)
            }
        }

        # Add GIF context if one should be sent
        if should_gif:
            gif_context = self._get_gif_context(user_message, game_state)
            result["gif_context"] = gif_context

        return result

    def _get_gif_context(self, message: str, game_state: Dict[str, Any] = None) -> str:
        """Generate context for what type of GIF would be appropriate"""

        excitement = self.current_bot.emotional_state.get("excitement", 0.5)
        confidence = self.current_bot.emotional_state.get("confidence", 0.5)
        humor_level = self.current_bot.response_config.get("humor_level", 0.3)

        # Determine GIF type based on context and personality
        if game_state and game_state.get('game_over', False):
            if confidence > 0.6:
                return "celebration"
            else:
                return "disappointed"
        elif excitement > 0.7:
            return "excited"
        elif humor_level > 0.6:
            return "funny"
        elif confidence > 0.8:
            return "confident"
        else:
            return "reaction"

    def generate_contextual_proactive_comment(self, game_state: Dict[str, Any], event_type: str = "general", specific_context: str = "") -> Optional[Dict[str, Any]]:
        """Generate enhanced proactive comments with personality-driven context"""

        bot_info = self.get_bot_info()

        # Check if bot should make a proactive comment
        import time
        current_time = time.time()

        if not self.current_bot.should_make_proactive_comment(event_type, game_state, current_time):
            return None

        # Generate event-specific prompts based on personality
        event_prompts = {
            "turn_start": self._get_turn_start_prompt(game_state),
            "card_drawn": self._get_card_drawn_prompt(game_state),
            "card_played": self._get_card_played_prompt(game_state),
            "score_update": self._get_score_update_prompt(game_state),
            "game_over": self._get_game_over_prompt(game_state),
            "dramatic_moment": self._get_dramatic_moment_prompt(game_state),
            "general": "Comment on the current game situation."
        }

        base_prompt = event_prompts.get(event_type, "Comment on the current game situation.")

        # Add specific context if provided
        if specific_context:
            base_prompt += f" Context: {specific_context}"

        try:
            context = f"{bot_info['system_prompt']}\n\n"
            context += self.format_game_state_for_prompt(game_state) + "\n\n"

            # Add enhanced personality context for proactive comments
            dynamic_context = self.current_bot.get_dynamic_response_context(game_state)
            context += dynamic_context + "\n\n"

            style_context = self.current_bot.get_response_style_context()
            context += style_context + "\n\n"

            personality_additions = self.current_bot.generate_personality_specific_prompt_additions("gameplay")
            if personality_additions:
                context += personality_additions + "\n\n"

            context += base_prompt + "\n\n"
            context += self.base_prompt + "\n"

            # Use personality-adjusted temperature
            personality_modifiers = self.current_bot.get_personality_modifiers()
            base_temperature = 0.8  # Slightly higher for proactive comments

            temp_adjustment = (personality_modifiers["excitement_modifier"] +
                             personality_modifiers["humor_modifier"] -
                             personality_modifiers["confidence_modifier"]) * 0.2

            adjusted_temperature = max(0.4, min(1.0, base_temperature + temp_adjustment))

            response = call_cerebras_llm(
                prompt=context,
                model="llama3.1-8b",
                structured=False,
                stream=False,
                temperature=adjusted_temperature
            )

            # Update comment tracking
            self.current_bot.last_comment_time = current_time
            self.current_bot.comments_this_game += 1

            # Apply personality-based response length
            verbosity = self.current_bot.response_config.get("verbosity", 0.5)
            if verbosity < 0.3:
                max_length = 100
            elif verbosity > 0.7:
                max_length = 200
            else:
                max_length = 150

            if len(response) > max_length:
                response = response[:max_length-3] + "..."

            # Check for GIF
            should_gif = self.current_bot.should_send_gif()

            result = {
                "message": response.strip(),
                "bot_name": self.current_bot.name,
                "event_type": event_type,
                "should_send_gif": should_gif,
                "personality_info": {
                    "confidence": self.current_bot.emotional_state.get("confidence", 0.5),
                    "excitement": self.current_bot.emotional_state.get("excitement", 0.5),
                    "frustration": self.current_bot.emotional_state.get("frustration", 0.0)
                }
            }

            if should_gif:
                result["gif_context"] = self._get_gif_context("", game_state)

            return result

        except Exception as e:
            print(f"DEBUG: Error generating contextual proactive comment: {e}")
            return None

    def check_for_proactive_comment(
        self,
        game_state: dict,
        conversation_history: list,
        last_proactive_comment_time: float,
        cooldown_seconds: int = 3 # 30 was default
    ) -> Optional[dict]:
        """
        Decide if a proactive comment should be generated, and return it if so.
        - Checks for dramatic events, silence, or other triggers.
        - Returns a proactive comment dict (same format as generate_contextual_proactive_comment), or None.
        """
        import time
        now = time.time()
        time_since_last = now - last_proactive_comment_time

        # Dramatic event trigger
        dramatic_event = False
        if game_state and game_state.get('last_action') and 'dramatic' in str(game_state['last_action']).lower():
            dramatic_event = True

        # Silence trigger (no user chat for X seconds)
        last_chat_time = 0
        if conversation_history:
            last_chat_time = max(
                msg.get('timestamp', 0)
                for msg in conversation_history if msg.get('role') == 'user'
            ) if any(msg.get('role') == 'user' for msg in conversation_history) else 0
        time_since_chat = now - last_chat_time if last_chat_time else float('inf')
        silence_trigger = time_since_chat > cooldown_seconds

        # Decide if we should generate a comment
        if dramatic_event or time_since_last > cooldown_seconds or silence_trigger:
            event_type = 'dramatic_moment' if dramatic_event else 'general'
            comment = self.generate_contextual_proactive_comment(game_state=game_state, event_type=event_type)
            if comment:
                return comment
        return None

    def _get_turn_start_prompt(self, game_state: Dict[str, Any]) -> str:
        """Generate turn start specific prompts based on personality"""
        advice_freq = self.current_bot.response_config.get("advice_frequency", 0.4)

        if advice_freq > 0.6:
            return "A new turn is starting. Offer strategic advice or commentary on the player's position."
        else:
            return "A new turn is starting. Make a brief encouraging comment."

    def _get_card_drawn_prompt(self, game_state: Dict[str, Any]) -> str:
        """Generate card drawn specific prompts"""
        humor_level = self.current_bot.response_config.get("humor_level", 0.3)

        if humor_level > 0.6:
            return "A card was just drawn. Make a witty or humorous comment about the draw."
        else:
            return "A card was drawn. Comment on the player's luck or strategy."

    def _get_card_played_prompt(self, game_state: Dict[str, Any]) -> str:
        """Generate card played specific prompts"""
        advice_freq = self.current_bot.response_config.get("advice_frequency", 0.4)

        if advice_freq > 0.6:
            return "A card was played. Analyze the move and offer strategic commentary."
        else:
            return "A card was played. React to the move briefly."

    def _get_score_update_prompt(self, game_state: Dict[str, Any]) -> str:
        """Generate score update specific prompts"""
        excitement = self.current_bot.emotional_state.get("excitement", 0.5)

        if excitement > 0.7:
            return "Scores have been updated! React with enthusiasm to the score changes."
        else:
            return "Scores have been updated. Comment on the current standings."

    def _get_game_over_prompt(self, game_state: Dict[str, Any]) -> str:
        """Generate game over specific prompts"""
        return "The game has ended. React to the final results and congratulate or commiserate as appropriate."

    def _get_dramatic_moment_prompt(self, game_state: Dict[str, Any]) -> str:
        """Generate dramatic moment specific prompts"""
        excitement = self.current_bot.emotional_state.get("excitement", 0.5)

        if excitement > 0.7:
            return "This is a dramatic moment in the game! React with high energy and excitement."
        else:
            return "This is a tense moment in the game. Comment on the drama unfolding."

# Create a global chatbot instance
chatbot = GolfChatbot("Jim Nantz")

def parse_mentions(message: str) -> list:
    """Extract @mentions from a message and map to bot names."""
    mention_regex = r'@(\w+)'
    matches = re.findall(mention_regex, message)
    bot_name_map = {
        'golfbro': 'Golf Bro',
        'golfpro': 'Golf Pro',
        'golf_bro': 'Golf Bro',
        'golf_pro': 'Golf Pro',
    }
    mentions = []
    for m in matches:
        key = m.lower()
        if key in bot_name_map:
            mentions.append(bot_name_map[key])
    return mentions

class ChatHandler:
    """Handler for all chat-related functionality"""

    def __init__(self, chatbot_instance: GolfChatbot):
        self.chatbot = chatbot_instance

    def calculate_bot_response_delay(self, bot_name: str) -> float:
        """Calculate response delay based on bot personality"""
        try:
            # Create bot instance to get its configuration
            from bot_personalities import create_bot
            bot = create_bot(bot_name)
            reaction_speed = bot.response_config.get('reaction_speed', 0.5)

            # Clamp reaction_speed to [0.0, 1.0]
            try:
                reaction_speed = float(reaction_speed)
            except Exception:
                reaction_speed = 0.5
            reaction_speed = max(0.0, min(1.0, reaction_speed))

            # Base delay range: 0.5-3.0 seconds
            min_delay = 0.5
            max_delay = 3.0
            # Invert the reaction_speed so that higher values = faster responses
            delay = min_delay + (1.0 - reaction_speed) * (max_delay - min_delay)

            # Add some randomness (±20%)
            variation = random.uniform(0.8, 1.2)
            final_delay = delay * variation

            # Ensure delay is never negative
            final_delay = max(min_delay, final_delay)

            print(f"DEBUG: Bot {bot_name} - reaction_speed: {reaction_speed:.2f}, calculated delay: {final_delay:.2f}s")

            return final_delay

        except Exception as e:
            print(f"DEBUG: Error calculating delay for {bot_name}: {e}")
            # Default delay if there's an error
            return 1.5

    def get_bot_id_from_display_name(self, game_session, display_name):
        """Convert display name to bot_id for custom bot lookup"""
        if not game_session:
            return display_name

        # Check if this is a custom bot
        for key, value in game_session.items():
            if key.startswith('custom_bot_name') and value == display_name:
                # Find corresponding bot_id
                bot_id_key = key.replace('custom_bot_name', 'custom_bot_id')
                if bot_id_key in game_session:
                    return game_session[bot_id_key]

        # If not a custom bot, return the display name
        return display_name

    def handle_send_message(self, data: Dict[str, Any], get_game_state_func, games: Dict) -> Dict[str, Any]:
        """Handle send message requests"""
        print("DEBUG: Received data:", data)
        game_id = data.get('game_id')
        message = data.get('message')
        personality_type = data.get('personality_type', 'Jim Nantz')

        if not message:
            return {'error': 'Message cannot be empty'}, 400

        # Get current game state if game_id is provided
        game_state = None
        if game_id and game_id in games:
            game_state = get_game_state_func(game_id)
            game_session = games[game_id]
        else:
            game_session = None

        # Parse mentions from the message
        mentioned_bots = parse_mentions(message)
        print(f"DEBUG: Mentioned bots: {mentioned_bots}")

        # Generate main bot responses (existing logic)
        if personality_type == 'opponent':
            main_result = self._handle_opponent_chat(game_id, message, game_state, games, mentioned_bots)
        else:
            main_result = self._handle_single_personality_chat(message, game_state, personality_type, mentioned_bots)

        # After updating conversation history, check for proactive comments for each bot
        proactive_comments = []
        if game_session and 'conversation_history' in game_session:
            # Use allowed bots from the main_result if available, else default to all AI players
            allowed_bots = [resp['bot_name'] for resp in main_result.get('responses', [])]
            for bot_name in allowed_bots:
                # Use each bot's own cooldown/attributes if needed
                last_time = game_session.get(f'last_proactive_comment_time_{bot_name}', 0)
                cooldown = game_session.get(f'proactive_comment_cooldown_{bot_name}', 10)
                print(f"[Timer] allowed_bots: {allowed_bots}", flush=True)
                print(f"[Timer] Proactive comment - Bot name: {bot_name}, Bot ID: {self.get_bot_id_from_display_name(game_session, bot_name)}", flush=True)
                comment = self.chatbot.check_for_proactive_comment(
                    game_state=game_state,
                    conversation_history=game_session['conversation_history'],
                    last_proactive_comment_time=last_time,
                    cooldown_seconds=cooldown
                )
                if comment:
                    proactive_comments.append({
                        'bot_name': bot_name,
                        **comment
                    })
                    game_session[f'last_proactive_comment_time_{bot_name}'] = time.time()
        # Return both main responses and proactive comments
        return {
            'success': True,
            'responses': main_result.get('responses', []),
            'proactive_comments': proactive_comments
        }

    def _handle_opponent_chat(self, game_id: str, message: str, game_state: Dict[str, Any], games: Dict, mentioned_bots: List[str]) -> Dict[str, Any]:
        """Handle chat with all opponent bots"""
        print("DEBUG: Handling opponent chat message")
        game_session = games[game_id]
        game = game_session['game']

        # Get responses from all AI players in the game ONLY (no chat-only bots)
        all_bots = list(game.players[1:])  # All AI players from the game

        # Generate enhanced responses from all bots
        responses = []

        for player in all_bots:
            print(f"DEBUG: Bot name: {player.name}")

            # Convert display name to bot_id if it's a custom bot
            bot_id_for_lookup = self.get_bot_id_from_display_name(game_session, player.name)
            print(f"DEBUG: Bot personality (after ID lookup): {bot_id_for_lookup}")

            try:
                # Use enhanced response generation with proper bot_id
                enhanced_response = self.chatbot.generate_enhanced_response_with_gif(
                    message,         # user_message
                    game_state,      # game_state
                    bot_id_for_lookup  # personality (use bot_id for lookup)
                )
                responses.append({
                    'bot_name': player.name,  # Keep original display name for frontend
                    'message': enhanced_response["message"],
                    'should_send_gif': enhanced_response.get("should_send_gif", False),
                    'gif_context': enhanced_response.get("gif_context", ""),
                    'personality_info': enhanced_response.get("personality_info", {})
                })
            except Exception as e:
                print("\n" + "="*40 + " CHATBOT ERROR " + "="*40)
                print(f"ERROR: Failed to generate response for {player.name}: {e}")
                import traceback
                traceback.print_exc()
                print("="*80 + "\n")
                responses.append({
                    'bot_name': player.name,
                    'message': f"Error: {e}",
                    'should_send_gif': False,
                    'gif_context': "",
                    'personality_info': {}
                })

        return {'success': True, 'responses': responses}

    def _handle_single_personality_chat(self, message: str, game_state: Dict[str, Any], personality_type: str, mentioned_bots: List[str]) -> Dict[str, Any]:
        """Handle chat with single personality"""
        # Enhanced response generation
        enhanced_response = self.chatbot.generate_enhanced_response_with_gif(
            message,          # user_message
            game_state,       # game_state
            personality_type  # personality
        )
        # Calculate reading delay for this bot
        delay = self.calculate_bot_response_delay(personality_type)
        return {
            'success': True,
            'responses': [{
                'bot_name': enhanced_response["bot_name"],
                'message': enhanced_response["message"],
                'reading_delay': delay,
                'should_send_gif': enhanced_response.get('should_send_gif', False),
                'gif_context': enhanced_response.get('gif_context', ""),
                'personality_info': enhanced_response.get('personality_info', {})
            }]
        }

    def handle_get_bot_response(self, data: Dict[str, Any], get_game_state_func, games: Dict) -> Dict[str, Any]:
        """Get a response from a specific bot with delay"""
        game_id = data.get('game_id')
        message = data.get('message')
        bot_name = data.get('bot_name')
        conversation_context = data.get('conversation_context', [])  # New parameter

        if not message or not bot_name:
            return {'error': 'Message and bot_name are required'}, 400

        # Get current game state if game_id is provided
        game_state = None
        game_session = None
        if game_id and game_id in games:
            game_state = get_game_state_func(game_id)
            game_session = games[game_id]

        try:
            # Convert display name to bot_id if it's a custom bot
            bot_id_for_lookup = self.get_bot_id_from_display_name(game_session, bot_name)

            # Calculate delay for this bot
            delay = self.calculate_bot_response_delay(bot_name)
            print(f"DEBUG: Calculated {delay:.2f}s delay for {bot_name}")
            # Do NOT sleep here; let frontend handle the delay for typing indicator

            # Create bot instance and add conversation context
            from bot_personalities import create_bot
            bot = create_bot(bot_id_for_lookup)

            # Add the conversation context to the bots history
            for ctx in conversation_context:
                bot.conversation_history.append(ctx)

            # Generate response with the enriched context
            response = self.chatbot.generate_response(
                message,     # user_message
                game_state,  # game_state
                bot_id_for_lookup  # personality (use bot_id for lookup)
            )

            print(f"Returning bot response: bot_name={bot_name}, reading_delay={delay}, message={response[:60]}")
            return {
                'success': True,
                'bot_name': bot_name,  # Return the original display name
                'message': response,
                'reading_delay': delay  # Renamed for clarity
            }

        except Exception as e:
            print(f"ERROR: Failed to generate response for {bot_name}: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'bot_name': bot_name,
                'message': f"Error: {e}"
            }

    def handle_proactive_comment(self, data: Dict[str, Any], get_game_state_func, games: Dict) -> Dict[str, Any]:
        """Handle proactive comment requests"""
        print("==== handle_proactive_comment called ====")
        print("Request data:", data)
        game_id = data.get('game_id')
        event_type = data.get('event_type', 'general')
        specific_context = data.get('specific_context', '')

        if not game_id or game_id not in games:
            return {'error': 'Game not found'}, 404

        try:
            game_state = get_game_state_func(game_id)
            game_session = games[game_id]
            game = game_session['game']

            # Determine allowed bots: all AI players except 'Golf Pro' and 'Golf Bro', unless overridden
            if 'allowed_bots' in data:
                allowed_bots = data['allowed_bots']
            else:
                allowed_bots = [p.name for p in game.players[1:] if p.name not in ('Golf Pro', 'Golf Bro')]
            print("ALLOWED BOTS:", allowed_bots)
            ai_players = [p for p in game.players[1:] if p.name in allowed_bots]
            print("AI PLAYERS SELECTED:", [p.name for p in ai_players])

            comments = []

            # Build the list of all allowed bots (including Jim Nantz if desired)
            all_bot_names = [p.name for p in game.players[1:] if p.name not in ('Golf Pro', 'Golf Bro')]
            if "Jim Nantz" in allowed_bots and "Jim Nantz" not in all_bot_names:
                all_bot_names.append("Jim Nantz")

            print(f"DEBUG: all_bot_names = {all_bot_names}")
            for bot_name in all_bot_names:
                bot_id_for_lookup = self.get_bot_id_from_display_name(game_session, bot_name)
                print(f"DEBUG: Proactive comment - Bot name: {bot_name}, Bot ID: {bot_id_for_lookup}", flush=True)

                bot_instance = create_bot(bot_id_for_lookup)
                from chatbot import GolfChatbot
                temp_chatbot = GolfChatbot(bot_id_for_lookup)
                temp_chatbot.current_bot = bot_instance

                enhanced_comment = temp_chatbot.generate_contextual_proactive_comment(
                    game_state,
                    event_type,
                    specific_context
                )

                if enhanced_comment:
                    comments.append({
                        'bot_name': bot_name,
                        'message': enhanced_comment["message"],
                        'event_type': enhanced_comment.get("event_type", event_type),
                        'should_send_gif': enhanced_comment.get("should_send_gif", False),
                        'gif_context': enhanced_comment.get("gif_context", ""),
                        'personality_info': enhanced_comment.get("personality_info", {})
                    })

            print(f"DEBUG: Generated {len(comments)} enhanced proactive comments")
            return {'success': True, 'comments': comments}

        except Exception as e:
            print(f"ERROR: Error generating proactive comments: {e}")
            import traceback
            traceback.print_exc()
            return {'error': str(e)}, 500



    def _generate_gif_search_terms(self, bot_name: str, message: str) -> str:
        """Generate GIF search terms based on bot's description, prompt, and message."""
        # Try to get the bot instance (use your bot registry/factory)
        bot = None
        try:
            bot = self.chatbot.create_bot(bot_name)
        except Exception:
            pass

        terms = []
        # Add bot's description keywords
        if bot and hasattr(bot, 'description') and bot.description:
            terms.extend([w for w in bot.description.lower().replace('.', '').replace(',', '').split() if len(w) > 3])
        # Add bot's prompt keywords
        if bot and hasattr(bot, 'get_system_prompt'):
            prompt = bot.get_system_prompt()
            terms.extend([w for w in prompt.lower().replace('.', '').replace(',', '').split() if len(w) > 3])
        # Add message keywords
        if message:
            terms.extend([w for w in message.lower().replace('.', '').replace(',', '').split() if len(w) > 3])
        # Remove duplicates, keep order
        seen = set()
        filtered_terms = []
        for t in terms:
            if t not in seen:
                seen.add(t)
                filtered_terms.append(t)
        # Fallback if nothing found
        if not filtered_terms:
            filtered_terms = ['golf', 'celebration']
        # Use up to 3 terms for Giphy
        return ' '.join(filtered_terms[:3])

    def handle_get_giphy_gif(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Get a relevant GIF from Giphy API based on message content and bot name"""
        try:
            message = data.get('message', '')
            bot_name = data.get('bot_name', '')
            print('gif message:', message)

            # Get API key from environment
            import os
            api_key = os.getenv('GIPHY_API_KEY')
            if not api_key:
                return {'error': 'GIPHY_API_KEY not found in environment variables'}, 500

            # Use new helper to generate search query
            search_query = self._generate_gif_search_terms(bot_name, message)
            print('gif search query:', search_query)

            # Call Giphy API
            import requests
            url = "https://api.giphy.com/v1/gifs/search"
            params = {
                'api_key': api_key,
                'q': search_query,
                'limit': 15,
                'rating': 'g'
            }

            response = requests.get(url, params=params)
            response.raise_for_status()

            response_data = response.json()

            if response_data.get('data'):
                # Return a random GIF from the results
                import random
                gif = random.choice(response_data['data'])

                # Clean the URL by removing tracking parameters
                gif_url = gif['images']['downsized_medium']['url']
                if '?' in gif_url:
                    gif_url = gif_url.split('?')[0]

                return {
                    'success': True,
                    'gif_url': gif_url,
                    'search_query': search_query
                }
            else:
                return {'error': 'No GIFs found'}, 404

        except Exception as e:
            return {'error': f'Server error: {str(e)}'}, 500

# Create global chat handler instance
chat_handler = ChatHandler(chatbot)