from typing import Dict, List, Optional, Any
from llm_cerebras import call_cerebras_llm
import random
import os
from bot_personalities import DataBot
from game_state import get_game_state
import re
import time
from data_upset import upload_chatbot_message
import threading
import time
# Create global instances. # TODO, not sue why???
# chatbot = GolfChatbot()
# chat_handler = ChatHandler(chatbot)

LAST_X_MESSAGES = 10
PROACTIVE_TIMER = 300 # 300 seconds = 5 minutes
CHAT_HISTORY_CHANGE_INTERVAL = 5

class GolfChatbot:
    """Chatbot for the Golf card game with different personalities
    Handles the content and logic of the bot’s responses.
    Knows about bot personalities, how to format game state, how to generate a message, and how to decide if/when a bot should respond (based on game state, personality, etc)."""

    def __init__(self, selected_bots: Optional[List[dict]] = None):
        self.base_prompt = ( "keep responses short and concise. Two sentences max and roughly 150 characters max")
        self.off_topic_prompt = ( "You are in a conversation with a group playing cards, but dn't want to talk about the game. Create a response that is not about the game and about a topic that is related to the the bots personality or another interesting topic.")
        self.bots = {}  # Will hold bot objects keyed by ai_bot_id
        self.conversation_history = {} # converation history with timestamp.

        if selected_bots:
            from bot_personalities import DataBot
            for bot_dict in selected_bots:
                # Choose the right class based on bot_dict['name'] or another key. Nantz is from front
                bot_obj = DataBot(**bot_dict)
                self.bots[bot_dict['ai_bot_id']] = bot_obj

        # Load rules once
        rules_path = os.path.join(os.path.dirname(__file__), 'game_rules.txt')
        try:
            with open(rules_path, 'r', encoding='utf-8') as f:
                self.game_rules = f.read().strip()
        except Exception as e:
            self.game_rules = "(Game rules unavailable)"

    def get_bot_info(self) -> Dict[str, str]: # TODO still unsure about this.....
        """Get information about the current bot"""
        return {
            "ai_bot_id": self.current_bot.ai_bot_id,
            "name": self.current_bot.name,
            "description": self.current_bot.description,
            "emotional_state": self.current_bot.emotional_state
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
            dramatic_event = is_dramatic_event(game_state)
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

    def will_bot_respond(self, game_state: Dict[str, Any]) -> bool:
        """Check if bot will respond to the user message."""
        # TODO add respnose config here to bot might not respons.
        #if they don't respond then update config to increase chance of responding next time.
        return True # will need to update this function.

    def is_dramatic_event(self, game_state: Dict[str, Any]) -> bool:
        """Check if the game state is a dramatic event."""
        # TODO add dramatic event logic here.
        return False # will need to update this function.

    def generate_response(self, user_message: str, game_state: Optional[Dict[str, Any]] = None, bot_info: Optional[Dict[str, Any]] = None) -> str:
        """Generate a chatbot response based on user input and game state"""

        # Use provided bot_info if available (from game session memory)
        ai_bot_id = bot_info.get('ai_bot_id', 'AI Bot')
        bot_name = bot_info.get('name', 'AI Bot')
        bot_description = bot_info.get('description', '')

        # Check if the bot will respond
        if not self.will_bot_respond(game_state):
            self.add_message_to_history('user', user_message, None)
            self.add_message_to_history('bot', "The bot chooses not to respond at this time.", None)
            return "The bot chooses not to respond at this time."

        # Create system prompt using bot description
        system_prompt = f"You are {bot_name}. "
        if bot_description:
            system_prompt += f"Your personality: {bot_description}. "

        # Add difficulty-based characteristics
        difficulty = bot_info.get('difficulty', 'medium')
        if difficulty == "easy":
            system_prompt += "You are friendly and encouraging. "
        elif difficulty == "medium":
            system_prompt += "You are balanced and strategic. "
        elif difficulty == "hard":
            system_prompt += "You are competitive and analytical. "

        system_prompt += "Keep responses under 2 sentences and 200 characters. Stay in character and respond naturally to the game situation."

        print(f"🔧 SYSTEM PROMPT for {bot_name} (from memory):")
        print(f"🔧 {system_prompt}")

        # Always add system prompt and rules ONCE at the top
        context = system_prompt + "\n\n" + "Game Rules:\n" + self.game_rules + "\n\n"

        if game_state:
            context += self.format_game_state_for_prompt(game_state) + "\n\n"

        # Always add the base prompt
        context += self.base_prompt + "\n"

        # Add conversation history for context (but never the rules again) -
        if not bot_info and self.current_bot.conversation_history:
            context += "Recent conversation:\n"
            for msg in self.current_bot.conversation_history[-LAST_X_MESSAGES:]:  # Last 3 messages
                context += f"{msg['role']}: {msg['content']}\n"
            context += "\n"

        context += f"User: {user_message}\n"

        # Use bot name from bot_info if available, otherwise from bot_info_obj
        bot_name = bot_info.get('name', 'AI Bot')

        context += f"{bot_name}:"

        try:
            # Print the full prompt being sent to the LLM
            print(f"🤖 LLM PROMPT (model: llama3.1-8b, structured: False, stream: True, temp: 0.7):")
            print(f"🤖 {'='*80}")
            print(f"🤖 {context}")
            print(f"🤖 {'='*80}")

            # TODO create response config for the botto add to the context (verbosity, humor, confidence, excitement, frustration)
            # TODO call gif config for the botto add to the context
            # TODO call emotional state for the botto add to the context ( can adjust temperature)
            # TODO call understand_gif for the botto add to the context

            # TODO check to see if its a dramatic event and add to the context.

            # Store in conversation history
            self.current_bot.conversation_history.append({"role": "user", "content": user_message})
            self.current_bot.conversation_history.append({"role": "assistant", "content": response})

            # Keep only last 10 messages to prevent context from getting too long
            if len(self.current_bot.conversation_history) > 10:
                self.current_bot.conversation_history = self.current_bot.conversation_history[-10:]

            response = call_cerebras_llm(
                prompt=context,
                model="llama3.1-8b",
                structured=False,
                stream=False,
                temperature=0.8
            )

            # Store bot response in conversation history
            self.add_message_to_history('bot', response, None)

            # TODO upload to supabase (uuid, game_id, user_id, timestamp, bot_name, message, sender, media, metadata)

            return response, context

        except Exception as e:
            error_msg = f"Sorry, I'm having trouble responding right now. Error: {str(e)}"
            self.add_message_to_history('bot', error_msg, None)
            return error_msg

    def generate_off_topic_proactive_response(self, game_state: Dict[str, Any], event_type: str = "general") -> Optional[str]:
        """Generate a proactive comment based on game events. if get proactive commment is true then then this function is called. This calls a function to see if the bot comments on/off topic."""

        context =+ self.base_prompt + "\n"

        print(f"DEBUG: generate_proactive_comment called with event_type: {event_type}")
        print(f"DEBUG: Current bot_type: {self.bot_type}")

        # Use the bot's proactive behavior system to see if they are going to comment on game state or off topic message. TODO. might need to update proactive config for game state vs off topic.

        if not self.is_on_topic(game_state): # so if on topic, general response, if off topic, continue.
            return self.generate_response(game_state) # could put more speciifc gamestate response instead of general...
        # continue with rest of OFF topicfunction logic here

        context += self.off_topic_prompt + "\n"
        # so if we are here, then we are going to generate a proactive comment.


        # context

        try:
            # Print the system prompt for investigation

            context += self.format_game_state_for_prompt(game_state) + "\n\n"

            # Add emotional and situational context
            emotional_context = self.current_bot.get_emotional_context()
            context += emotional_context + "\n\n"

            situational_context = self.current_bot.get_situational_context(game_state)
            if situational_context:
                context += situational_context + "\n\n"

            # Always add the base prompt

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
            if response:
                return response.strip(), context
            else:
                return response.strip()

        except Exception as e:
            print(f"DEBUG: Error generating proactive comment: {e}")
            if response:
                return None, ""
            else:
                return None

    def bot_memory_update_for_new_game(self):
        """Reset bot state for a new game. maybe not reset, but have a variance and mean that it pulls to. Eh, I think I like bot memory better."""
        # TODO add bot memory to the bot object in the bot_personalities.py file.
        pass

    def should_send_gif(self):
        """Check if bot should send a GIF. might be a function in the chat handler tho."""
        return False

    def is_on_topic(self, game_state: Optional[Dict[str, Any]]) -> bool:
        """Check if the user message is on or off topic between game state"""
        # TODO if dramatic event, then return true.
        return True # will need to update this function.

    def generate_response_with_gif(self, user_message: str, game_state: Optional[Dict[str, Any]] = None, personality: str = None) -> Dict[str, Any]:
        """Generate an enhanced response that may include GIF suggestions"""

        # Generate the normal response
        response = self.generate_response(user_message, game_state, personality)

        # Check if bot should send a GIF
        if self.should_send_gif():
            gif_context = self._get_gif_context(user_message, game_state)


        return result

    # TODO will update this for an advanced gif system by calling llm.
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


    def check_for_proactive_comment(
        self,
        game_state: dict,
        conversation_history: list,
        last_proactive_comment_time: float,
        cooldown_seconds: int = 300 # 30 was default
    ) -> Optional[dict]:
        """
        I"m currently confused if this should be in the handler or the chatbot. how to seperate the two??
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
            return "A card was played. Analyze the move and offer strategic commentary related to the EV."
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
        if bot and bot.get('description'):
            terms.extend([w for w in bot['description'].lower().replace('.', '').replace(',', '').split() if len(w) > 3])
        # Add bot's prompt keywords
        if bot and 'get_system_prompt' in bot:
            prompt = bot['get_system_prompt']()
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

    def add_message_to_history(self, sender: str, content: str, game_id: str = None):
        """Add a message to the conversation history with a timestamp."""
        import time
        message = {
            'sender': sender,
            'content': content,
            'timestamp': time.time()
        }
        if game_id:
            if game_id not in self.conversation_history:
                self.conversation_history[game_id] = []
            self.conversation_history[game_id].append(message)
        else:
            # If not using game_id, store in a global list
            if 'global' not in self.conversation_history:
                self.conversation_history['global'] = []
            self.conversation_history['global'].append(message)




    def parse_mentions(message: str) -> list:
        """Extract @mentions from a message and map to bot names."""
        mention_regex = r'@(\w+)'
        matches = re.findall(mention_regex, message)

        mentions = []
        # TODO implement this.
        return mentions

class ChatHandler:
    """Handler for all chat-related functionality.
    Handles the orchestration, timing, and triggering of chat events in the context of your web app/game.
    Acts as the “glue” between the web server/game state and the GolfChatbot."""

    def __init__(self, chatbot_instance: GolfChatbot):
        self.chatbot = chatbot_instance
        self._last_check_time = 0  # Track the last time the function returned True
        self._last_message_timestamp = 0  # Track the timestamp of the last message seen

    def proactive_comment_timer(self, game_id, time_interval=PROACTIVE_TIMER):
        """
        Waits for inactivity (no conversation history change) for time_interval seconds,
        then triggers proactive comment logic.
        Resets timer every time conversation history changes.
        """
        while True:
            start_time = time.time()
            while True:
                time.sleep(1)  # Check every second for responsiveness
                if self.has_conversation_history_changed(game_id):
                    # Activity detected, reset timer
                    print(f"[Proactive Timer] Activity detected in game {game_id}, resetting timer.")
                    start_time = time.time()
                elif time.time() - start_time >= time_interval:
                    # No activity for the interval, trigger proactive comment
                    print(f"[Proactive Timer] No activity in game {game_id} for {time_interval}s. Triggering proactive comment.")
                    # Example: trigger proactive comment logic here
                    # game_state = ... (fetch from your games dict or similar)
                    # comment = self.chatbot.check_for_proactive_comment(game_state, ...)
                    # if comment:
                    #     print(f"Proactive comment for {game_id}: {comment}")
                    start_time = time.time()  # Reset timer after triggering


    def has_conversation_history_changed(self, game_id: str = None, interval: int = CHAT_HISTORY_CHANGE_INTERVAL) -> bool:
        """
        Return True if the last message in conversation history is new (content or timestamp differs)
        AND at least `interval` seconds have passed since the last True.
        """
        import time
        current_time = time.time()
        # Use per-game or global conversation history
        if game_id:
            history = self.chatbot.conversation_history.get(game_id, [])
        else:
            history = self.chatbot.conversation_history.get('global', [])
        if not history:
            return False
        last_msg = history[-1]
        last_msg_signature = (last_msg.get('content', ''), last_msg.get('timestamp', 0))
        if (
            getattr(self, '_last_msg_signature', None) != last_msg_signature and
            (current_time - self._last_check_time) >= interval
        ):
            self._last_msg_signature = last_msg_signature
            self._last_check_time = current_time
            #call

            return True
        return False

    def get_bot_reaction_speed(self, ai_bot_id: str) -> float:
        """Get the reaction speed for a bot by ai_bot_id from its response_config."""
        bot = self.bots.get(ai_bot_id)
        if bot and hasattr(bot, 'response_config'):
            return bot.response_config.get('reaction_speed', 0.5)
        return 0.5  # default if not found

    def calculate_bot_response_delay(self, ai_bot_id: str) -> float:
        """Calculate response delay based on bot's reaction speed (from response_config) using ai_bot_id."""
        try:
            reaction_speed = self.get_bot_reaction_speed(ai_bot_id)

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

            print(f"DEBUG: Bot {ai_bot_id} - reaction_speed: {reaction_speed:.2f}, calculated delay: {final_delay:.2f}s")

            return final_delay

        except Exception as e:
            print(f"DEBUG: Error calculating delay for {ai_bot_id}: {e}")
            # Default delay if there's an error
            return 1.5



    def handle_user_message(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle send message requests from user. from front end api call."""
        print("DEBUG: Received data:", data)
        game_id = data.get('game_id')  # Always get game_id from the incoming data
        message = data.get('message')
        # personality_type = data.get('personality_type', 'Jim Nantz') # ?? what is this?

        if not message:
            return {'error': 'Message cannot be empty'}, 400

        # Add user message to conversation history
        self.chatbot.add_message_to_history('user', message, game_id)

        # TODO: Trigger bots to respond if needed (already done in the conversation history change check)
        # TODO: get the parse_mention

        # Log user message to Supabase
        upload_chatbot_message(
            game_id=game_id,
            user_id=data.get('user_id', None),
            bot_name=None,
            message=message,
            sender='user',
            media=None,  # If user can send GIFs/media, add here
            # metadata={"personality_type": personality_type}
        )

        return {
            'success': True,
            'message': 'User message received and logged.',
            'game_id': game_id
        }



    def _handle_bot_message(self, message: str, game_state: Dict[str, Any], personality_type: str, mentioned_bots: List[str]) -> Dict[str, Any]:
        """Handle """
        # Enhanced response generation
        enhanced_response = self.chatbot.generate_enhanced_response_with_gif(
            message,          # user_message
            game_state,       # game_state
            personality_type  # personality
        )
        # Calculate reading delay for this bot
        delay = self.calculate_bot_response_delay(personality_type)
        # Log bot message to Supabase
        upload_chatbot_message(
            game_id=None,  # If you have game_id in scope, use it
            user_id=None,
            bot_name=enhanced_response["bot_name"],
            message=enhanced_response["message"],
            sender='bot',
            media={"type": "gif", "context": enhanced_response.get("gif_context", "")} if enhanced_response.get("should_send_gif", False) else None,
            metadata=enhanced_response.get("personality_info", {})
        )
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
            # bot_name should already be the ai_bot_id from the frontend
            ai_bot_id = bot_name
            print(f"DEBUG: Looking up bot with ai_bot_id: '{ai_bot_id}'")

            # Get bot information directly from game session memory using ai_bot_id
            selected_bots = game_session.get('selected_bots', [])
            print(f"DEBUG: Available bots in memory: {[(b.get('ai_bot_id'), b.get('name')) for b in selected_bots]}")

            # Find bot by ai_bot_id
            bot_obj = next((b for b in selected_bots if b.get('ai_bot_id') == ai_bot_id), None)

            if bot_obj:
                bot_display_name = bot_obj.get('name', 'Unknown Bot')
                print(f"DEBUG: Found bot: ai_bot_id='{ai_bot_id}', name='{bot_display_name}'")
            else:
                print(f"DEBUG: Bot not found with ai_bot_id: '{ai_bot_id}'")

            # Calculate delay for this bot (use display name for delay calculation)
            delay_name = bot_obj.get('name', bot_name) if bot_obj else bot_name
            delay = self.calculate_bot_response_delay(delay_name)
            print(f"DEBUG: Calculated {delay:.2f}s delay for {delay_name}")
            # Do NOT sleep here; let frontend handle the delay for typing indicator

            if bot_obj:
                print(f"DEBUG: Found bot in memory: {bot_obj.get('name')} with description: {bot_obj.get('description', '')[:100]}...")

                # Generate response with bot info from memory
                response = self.chatbot.generate_response(
                    message,     # user_message
                    game_state,  # game_state
                    None,        # personality (not needed when using bot_info)
                    False,       # proactive
                    False,       # return_prompt
                    bot_obj      # bot_info from memory
                )
            else:
                print(f"DEBUG: Bot not found in memory, using fallback for {ai_bot_id}")
                # Fallback to old method for built-in bots
                response = self.chatbot.generate_response(
                    message,     # user_message
                    game_state,  # game_state
                    ai_bot_id    # personality (use ai_bot_id for lookup)
                )

            # Use bot display name for return, or ai_bot_id as fallback
            return_bot_name = bot_obj.get('name', ai_bot_id) if bot_obj else ai_bot_id

            print(f"Returning bot response: bot_name={return_bot_name}, reading_delay={delay}, message={response[:60]}")
            return {
                'success': True,
                'bot_name': return_bot_name,  # Return the display name for frontend
                'message': response,
                'reading_delay': delay  # Renamed for clarity
            }

        except Exception as e:
            # Try to get display name for error, fallback to ai_bot_id
            error_bot_name = ai_bot_id
            try:
                if 'bot_obj' in locals() and bot_obj:
                    error_bot_name = bot_obj.get('name', ai_bot_id)
            except:
                pass

            print(f"ERROR: Failed to generate response for {error_bot_name}: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'bot_name': error_bot_name,
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
            game_state = get_game_state_func(game_id, games)
            game_session = games[game_id]
            selected_bots = game_session.get('selected_bots', [])
            # Determine allowed bots: all AI players except 'Golf Pro' and 'Golf Bro', unless overridden
            if 'allowed_bots' in data:
                allowed_bots = data['allowed_bots']
            else:
                allowed_bots = [b.get('ai_bot_id') for b in selected_bots if b.get('name') not in ('Golf Pro', 'Golf Bro')]
            print("ALLOWED BOTS:", allowed_bots)
            comments = []
            for bot_id in allowed_bots:
                bot_obj = next((b for b in selected_bots if b.get('ai_bot_id') == bot_id), None)
                if not bot_obj:
                    continue
                bot_name = bot_obj.get('name', 'Unknown Bot chatbot.py 936')
                print(f"DEBUG: Proactive comment - Bot name: {bot_name}, Bot ID: {bot_id}", flush=True)
                # Use bot_obj attributes directly for proactive comment logic
                # If you need to instantiate a bot class for advanced logic, do so here (optional)
                # For now, just use the name and attributes directly
                last_time = game_session.get(f'last_proactive_comment_time_{bot_name}', 0)
                cooldown = game_session.get(f'proactive_comment_cooldown_{bot_name}', 10)
                comment = self.chatbot.check_for_proactive_comment(
                    game_state=game_state,
                    conversation_history=game_session['conversation_history'],
                    last_proactive_comment_time=last_time,
                    cooldown_seconds=cooldown
                )
                if comment:
                    comments.append({
                        'bot_name': bot_name,
                        **comment
                    })
                    game_session[f'last_proactive_comment_time_{bot_name}'] = time.time()
            print(f"DEBUG: Generated {len(comments)} enhanced proactive comments")
            return {'success': True, 'comments': comments}
        except Exception as e:
            print(f"ERROR: Error generating proactive comments: {e}")
            import traceback
            traceback.print_exc()
            return {'error': str(e)}, 500



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
                'limit': 20,
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

    # When retrieving conversation history for a bot, filter by ai_bot_id
    def get_conversation_history_for_bot(self, game_session, ai_bot_id):
        return [msg for msg in game_session.get('conversation_history', []) if msg.get('ai_bot_id') == ai_bot_id]


def periodic_conversation_check(chat_handler, game_id=None, interval=2):
    """
    Periodically check if the conversation history has changed every `interval` seconds.
    If changed, trigger your logic (e.g., proactive bot, notify frontend, etc.).
    """
    while True:
        if chat_handler.has_conversation_history_changed(game_id):
            print("Conversation history changed!")
            # Place your logic here (e.g., trigger proactive bot, notify frontend, etc.)
        time.sleep(interval)

# Example usage:
# chat_handler = ChatHandler(chatbot)
# threading.Thread(target=periodic_conversation_check, args=(chat_handler, 'your_game_id', 5), daemon=True).start()

