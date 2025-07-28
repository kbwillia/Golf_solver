from typing import Dict, List, Optional, Any
from llm_cerebras import call_cerebras_llm
from llama import call_llama
import random
import os
from bot_personalities import DataBot
from game_state import get_game_state
import re
import time
from data_upset import upload_chatbot_message, upload_llm_call_info
import threading
import time
# Create global instances. # TODO, not sue why???
# chatbot = GolfChatbot()
# chat_handler = ChatHandler(chatbot)

LAST_X_MESSAGES = 10
PROACTIVE_TIMER = 3 # (seconds)300 seconds = 5 minutes
CHAT_HISTORY_CHANGE_INTERVAL = 3

class GolfChatbot:
    """Chatbot for the Golf card game with different personalities
    Handles the content and logic of the bot’s responses.
    Knows about bot personalities, how to format game state, how to generate a message, and how to decide if/when a bot should respond (based on game state, personality, etc)."""

    def __init__(self, selected_bots: Optional[List[dict]] = None):
        print("GolfChatbot.__init__ called")
        self.base_prompt = ( "keep responses short and concise. Two sentences max and roughly 150 characters max")
        # TODO There are x people in the chatbot and in the game.
        self.off_topic_prompt = ( "You are in a conversation with a group playing cards, but dn't want to talk about the game. Create a response that is not about the game and about a topic that is related to the the bots personality or another interesting topic.")
        self.bots = {}  # Will hold bot objects keyed by ai_bot_id
        self.conversation_history = {} # converation history with timestamp.

        # if selected_bots: #making them a bot object. This starts at app start, so need to update when new game is called.
        #     from bot_personalities import DataBot
        #     for bot_dict in selected_bots:
        #         # Choose the right class based on bot_dict['name'] or another key. Nantz is from front
        #         bot_obj = DataBot(**bot_dict)
        #         self.bots[bot_dict['ai_bot_id']] = bot_obj

            #example:
            # self.bots = {
            # 'bot_id_1': DataBot(name="Charlie Day", description="...", ...),  # Bot OBJECT
            # 'bot_id_2': DataBot(name="Jim Nantz", description="...", ...),    # Bot OBJECT
            # 'bot_id_3': DataBot(name="Tiger Woods", description="...", ...)   # Bot OBJECT
            # }

        # Load rules once
        rules_path = os.path.join(os.path.dirname(__file__), 'game_rules.txt')
        try:
            with open(rules_path, 'r', encoding='utf-8') as f:
                self.game_rules = f.read().strip()
        except Exception as e:
            self.game_rules = "(Game rules unavailable)"

    def update_bots(self, selected_bots: List[dict]):
        """Update the bots dictionary with new bot objects at start of create game."""
        print(f"GolfChatbot.update_bots called with {len(selected_bots)} bots")
        if selected_bots:
            from bot_personalities import DataBot
            for bot_dict in selected_bots:
                # Choose the right class based on bot_dict['name'] or another key. Nantz is from front
                bot_obj = DataBot(**bot_dict)
                self.bots[bot_dict['ai_bot_id']] = bot_obj
                print(f"Added bot: {bot_dict['ai_bot_id']} -> {bot_obj.name}")

                # DEBUG: Print all attributes of the DataBot object
                print(f"🔍 DEBUG: DataBot attributes for {bot_obj.name}:")
                for attr in dir(bot_obj):
                    if not attr.startswith('_'):  # Skip private attributes
                        try:
                            value = getattr(bot_obj, attr)
                            print(f"  - {attr}: {value}")
                        except Exception as e:
                            print(f"  - {attr}: ERROR - {e}")

        print(f"Total bots in self.bots: {list(self.bots.keys())}")

    # def get_bot_info(self) -> Dict[str, str]: # TODO still unsure about this.....this is for dicts.
    #     print("GolfChatbot.get_bot_info called")
    #     """Get information about the current bot"""
    #     return {
    #         "ai_bot_id": self.current_bot.ai_bot_id,
    #         "name": self.current_bot.name,
    #         "description": self.current_bot.description,
    #         "emotional_state": self.current_bot.emotional_state
    #     }

    def format_game_state_for_prompt(self, game_state: Dict[str, Any]) -> str:
        print("GolfChatbot.format_game_state_for_prompt called")
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

    def will_bot_respond(self, game_state: Dict[str, Any], ai_bot_id: str) -> bool:
        print("GolfChatbot.will_bot_respond called")
        """Check if bot will respond to the user message based on the bot's response config."""

        # TODO add the response config to the bot object.
        try:
            response_probability = self.response_config.get("response_probability", 1.0)
            dramatic_event_comment_prob = self.response_config.get("dramatic_event_comment_prob", 1.0)
        except AttributeError:
            # If response_config doesn't exist, use defaults
            response_probability = 1.0
            dramatic_event_comment_prob = 1.0
            print("WARNING: response_config not found, using default probabilities")

        # Check if this is a dramatic event
        is_dramatic = self.is_dramatic_event(game_state)

        # Use the appropriate probability
        prob = dramatic_event_comment_prob if is_dramatic else response_probability

        roll = random.random()
        print(f"Using probability: {prob} (dramatic: {is_dramatic}), roll: {roll}")
        if roll < prob:
            print("Bot will respond.")
            return True
        else:
            print("Bot will not respond.")
            return False

    def is_dramatic_event(self, game_state: Dict[str, Any]) -> bool:
        print("GolfChatbot.is_dramatic_event called")
        """Check if the game state is a dramatic event."""
        # TODO add dramatic event logic here.
        return True # will need to update this function.

    def dramatic_event_prompt_builder(self, game_state: Dict[str, Any]) -> str:
        print("dramatic_event_prompt_builder called")
        """Build the dramatic event prompt for the bot."""
        # TODO add dramatic event logic here.
        return ""

    def difficulty_prompt_builder(self, ai_bot_id: str) -> str:
        print("difficulty_prompt_builder called")
        """Build the difficulty prompt for the bot."""
        # Get bot difficulty, default to 'medium'
        difficulty = self.bots[ai_bot_id].difficulty
        prompt = ""
        if difficulty == "easy":
            prompt += "You are friendly and encouraging. "
        elif difficulty == "medium":
            prompt += "You are balanced and strategic. "
        elif difficulty == "hard":
            prompt += "You are competitive and analytical. "
        else:
            prompt += "You are a thoughtful and interesting player. "
        return prompt

    def personality_prompt_builder(self, ai_bot_id: str) -> str:
        print("personality_prompt_builder called")
        """Build the personality prompt for the bot."""
        # Get bot personality, default to 'friendly'
        #TODO update personality config for bots
        # personality = self.bots[ai_bot_id].personality_config
        personality = "friendly"
        prompt = ""
        if personality == "friendly":
            prompt += "You are friendly and encouraging. "
        elif personality == "strategic":
            prompt += "You are balanced and strategic. "
        elif personality == "competitive":
            prompt += "You are competitive and analytical. "
        else:
            prompt += "You are a thoughtful and interesting player. "
        return prompt

    def emotional_state_prompt_builder(self, ai_bot_id: str) -> str:
        """Build the emotional state prompt for the bot."""
        # Get bot emotional state, default to 'neutral'
        print(f"🔍 EMOTIONAL_STATE DEBUG: Processing bot with ai_bot_id: {ai_bot_id}")

        # Check if bot exists
        if ai_bot_id not in self.bots:
            print(f"🔍 EMOTIONAL_STATE DEBUG: ERROR - Bot {ai_bot_id} not found in self.bots!")
            print(f"🔍 EMOTIONAL_STATE DEBUG: Available bots: {list(self.bots.keys())}")
            return "You are neutral. "

        bot = self.bots[ai_bot_id]
        print(f"🔍 EMOTIONAL_STATE DEBUG: Bot name: {bot.name}")
        print(f"🔍 EMOTIONAL_STATE DEBUG: Bot attributes: {[attr for attr in dir(bot) if not attr.startswith('_')]}")
        print(f"🔍 EMOTIONAL_STATE DEBUG: Bot has emotional_state: {hasattr(bot, 'emotional_state')}")

        if not hasattr(bot, 'emotional_state'):
            print(f"🔍 EMOTIONAL_STATE DEBUG: ERROR - Bot {bot.name} missing emotional_state attribute!")
            return "You are neutral. "

        emotional_state = bot.emotional_state
        print(f'🔍 EMOTIONAL_STATE DEBUG: emotional_state: {emotional_state}', 'type: ', type(emotional_state))

        prompt = ""
        if emotional_state == "confident":
            prompt += "You are confident and assertive. "
        elif emotional_state == "frustrated":
            prompt += "You are frstrated"
        elif emotional_state == "excitedt":
            prompt += "You are excited"
        elif emotional_state == "neutral":
            prompt += "You are neutral"
        else:
            prompt += "You are a thoughtful and interesting player. "
        return prompt

    def lucky_event(self, game_state: Dict[str, Any]) -> bool:
        print("GolfChatbot.lucky_unlucky_event called")
        """Check if the game state is a lucky or unlucky event."""
        # Example logic: check for a key in game_state
        # Replace with your actual game logic!
        if not game_state:
            return False
        # Example: if the last card drawn is an Ace or a 2 (lucky/unlucky)
        last_card = game_state.get("last_card_drawn")
        if last_card in ["A", "2"]:
            return True
        # Add more conditions as needed
        return False

    def generate_response(self, conversation_history: List[Dict[str, Any]],
                          game_state: Optional[Dict[str, Any]] = None,
                          ai_bot_id: str = None) -> str:

        print(f"🔍 GENERATE_RESPONSE DEBUG: Called with ai_bot_id={ai_bot_id}")
        print(f"🔍 GENERATE_RESPONSE DEBUG: ai_bot_id in self.bots: {ai_bot_id in self.bots}")
        """Generate a chatbot response based on conversation history and game state"""

        game_id = game_state["game_id"]

        # Get bot from self.bots using ai_bot_id
        if ai_bot_id and ai_bot_id in self.bots:
            bot_obj = self.bots[ai_bot_id]
            bot_name = bot_obj.name # do i need the bot
            bot_description = bot_obj.description
            difficulty = bot_obj.difficulty

        else:
            # Fallback if bot not found
            bot_name = 'AI Bot'
            bot_description = 'A helpful AI assistant'
            difficulty = 'medium'

        # Create system prompt using bot description
        system_prompt = f"You are {bot_name}. "
        if bot_description:
            system_prompt += f"Your personality: {bot_description}. "


        system_prompt += "This is a chat conversation while playing a card game.Keep responses under 2 sentences and 200 characters. Stay in character and respond naturally to the game situation."

        print(f"🤖 Bot: {bot_name}")
        print(f"🤖 Description: {bot_description}")
        print(f"🤖 Difficulty: {difficulty}")

        # Always add system prompt and rules ONCE at the top
        context = system_prompt + "\n\n" + "Game Rules:\n" + self.game_rules + "\n\n"

        if game_state:
            context += self.format_game_state_for_prompt(game_state) + "\n\n"

        # Add conversation history for context
        if conversation_history:
            context += "Recent conversation:\n"
            for msg in conversation_history[-3:]:  # Last 3 messages
                context += f"{msg.get('sender', 'unknown')}: {msg.get('content', '')}\n"
            context += "\n"

        # For proactive comments, we don't have a specific user message
        context += f"{bot_name}:"

        try:
            print(f"🔍 GENERATE_RESPONSE DEBUG: About to call prompt builders for ai_bot_id: {ai_bot_id}")
            print(f"🔍 GENERATE_RESPONSE DEBUG: Bot exists in self.bots: {ai_bot_id in self.bots}")
            if ai_bot_id in self.bots:
                print(f"🔍 GENERATE_RESPONSE DEBUG: Bot name: {self.bots[ai_bot_id].name}")
                print(f"🔍 GENERATE_RESPONSE DEBUG: Bot has emotional_state: {hasattr(self.bots[ai_bot_id], 'emotional_state')}")

            context += self.dramatic_event_prompt_builder(game_state) + "\n\n"
            context += self.difficulty_prompt_builder(ai_bot_id) + "\n\n"
            context += self.personality_prompt_builder(ai_bot_id) + "\n\n"
            context += self.emotional_state_prompt_builder(ai_bot_id) + "\n\n"

            # Add conversation history for context
            if conversation_history:
                context += "Recent conversation:\n"
                for msg in conversation_history[-LAST_X_MESSAGES:]:  # Last 10 messages
                    context += f"{msg['sender']}: {msg['content']}\n"
                context += "\n"

            # TODO call understand_gif for the botto add to the context
            # TODO call gif config for the botto add to the context
            # TODO  can adjust temperature for emotional state

            print(f' ---------------callling the llm ---------------')
            print(f'🔍 LLM DEBUG: Context length: {len(context)} characters')
            print(f'🔍 LLM DEBUG: About to call call_llama...')

            response, usage = call_cerebras_llm(
                prompt=context,
                model="llama3.1-8b",
                structured=False,
                stream=False,
                temperature=0.8
            )

            # try:
            #     response = call_llama(
            #         prompt=context,
            #         model="llama3.1",
            #         structured=False,
            #         stream=False,
            #         temperature=0.8
            #     )
            #     print(f'🔍 LLM DEBUG: call_llama returned successfully')
            #     print(f'🔍 LLM DEBUG: Response length: {len(response) if response else 0}')
            #     print(f'🔍 LLM DEBUG: Response preview: {response[:100] if response else "None"}')
            # except Exception as e:
            #     print(f'🔍 LLM DEBUG: Error calling call_llama: {e}')
            #     import traceback
            #     traceback.print_exc()
            #     response = f"Sorry, I'm having trouble responding right now. LLM Error: {str(e)}"

            print(f"🤖 {bot_name}: 'response from LLM': {response}")
            if usage:
                print(f"🤖 Token usage: {usage}")

            #add to conversation history
            self.add_message_to_history(bot_name, response, game_id)

            upload_chatbot_message(game_id, ai_bot_id, bot_name, response, "bot", media=None, metadata=None)

            return response

        except Exception as e:
            error_msg = f"Sorry, I'm having trouble responding right now. Error: {str(e)}"
            self.add_message_to_history('bot', error_msg, None)
            return error_msg

    def generate_off_topic_proactive_context(self, game_state: Dict[str, Any], event_type: str = "general") -> Optional[str]:
        print(f"GolfChatbot.generate_off_topic_proactive_context called with event_type={event_type}")
        """Generate a proactive comment context based on game events. Returns the context that would be sent to the LLM."""

        context = self.base_prompt + "\n"

        print(f"DEBUG: generate_proactive_comment called with event_type: {event_type}")

        # Use the bot's proactive behavior system to see if they are going to comment on game state or off topic message. TODO. might need to update proactive config for game state vs off topic.

        if not self.is_on_topic(game_state): # so if on topic, general response, if off topic, continue.
            return self.generate_response(game_state) # could put more speciifc gamestate response instead of general...
        # continue with rest of OFF topicfunction logic here

        context += self.off_topic_prompt + "\n"
        # so if we are here, then we are going to generate a proactive comment.

        try:
            # Print the system prompt for investigation

            context += self.format_game_state_for_prompt(game_state) + "\n\n"

            # Add emotional and situational context
            context += emotional_context + "\n\n"

            if situational_context:
                context += situational_context + "\n\n"

            # Always add the base prompt

            # Print the full prompt that would be sent to the LLM
            print(f"🤖 CONTEXT (would be sent to llama3.1-8b, structured: False, stream: False, temp: 0.8):")
            print(f"🤖 {'='*80}")
            print(f"🤖 {context[-200:]}")
            print(f"🤖 {'='*80}")

            # Return just the last 200 characters of the context instead of calling the LLM
            return context

        except Exception as e:
            print(f"DEBUG: Error generating proactive context: {e}")
            return None

    def bot_personality_prompt_builder(self) -> str:
        print("GolfChatbot.bot_personality_prompt_builder called")
        """Build the personality prompt for the bot."""
        # TODO build the personality prompt for the bot.
                    # Add emotional and situational context
        context += emotional_context + "\n\n"
        return ""

    def bot_memory_update_for_new_game(self):
        print("GolfChatbot.bot_memory_update_for_new_game called")
        """Reset bot state for a new game. maybe not reset, but have a variance and mean that it pulls to. Eh, I think I like bot memory better."""
        # TODO add bot memory to the bot object in the bot_personalities.py file.
        pass

    def should_send_gif(self):
        print("GolfChatbot.should_send_gif called")
        """Check if bot should send a GIF. might be a function in the chat handler tho."""
        return False

    def is_on_topic(self, game_state: Optional[Dict[str, Any]]) -> bool:
        print("GolfChatbot.is_on_topic called")
        """Check if the user message is on or off topic between game state"""
        # TODO if dramatic event, then return true.
        # TODO if user is talking about the game then return true..
        return True # will need to update this function.

    def generate_response_with_gif(self, user_message: str, game_state: Optional[Dict[str, Any]] = None, personality: str = None) -> Dict[str, Any]:
        print(f"GolfChatbot.generate_response_with_gif called with user_message={user_message}")
        """Generate an enhanced response that may include GIF suggestions"""

        # Generate the normal response
        response = self.generate_response(user_message, game_state, personality)

        # Check if bot should send a GIF
        if self.should_send_gif():
            gif_context = self._get_gif_context(user_message, game_state)


        return response

    # TODO will update this for an advanced gif system by calling llm.
    def _get_gif_context(self, message: str, game_state: Dict[str, Any] = None) -> str:
        print("GolfChatbot._get_gif_context called")
        """Generate context for what type of GIF would be appropriate"""



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




    def _get_turn_start_prompt(self, game_state: Dict[str, Any]) -> str:
        print("GolfChatbot._get_turn_start_prompt called")
        """Generate turn start specific prompts based on personality"""

        if advice_freq > 0.6:
            return "A new turn is starting. Offer strategic advice or commentary on the player's position."
        else:
            return "A new turn is starting. Make a brief encouraging comment."

    def _get_card_drawn_prompt(self, game_state: Dict[str, Any]) -> str:
        print("GolfChatbot._get_card_drawn_prompt called")
        """Generate card drawn specific prompts"""

        if humor_level > 0.6:
            return "A card was just drawn. Make a witty or humorous comment about the draw."
        else:
            return "A card was drawn. Comment on the player's luck or strategy."

    def _get_card_played_prompt(self, game_state: Dict[str, Any]) -> str:
        print("GolfChatbot._get_card_played_prompt called")
        """Generate card played specific prompts"""

        if advice_freq > 0.6:
            return "A card was played. Analyze the move and offer strategic commentary related to the EV."
        else:
            return "A card was played. React to the move briefly."

    def _get_score_update_prompt(self, game_state: Dict[str, Any]) -> str:
        print("GolfChatbot._get_score_update_prompt called")
        """Generate score update specific prompts"""

        if excitement > 0.7:
            return "Scores have been updated! React with enthusiasm to the score changes."
        else:
            return "Scores have been updated. Comment on the current standings."

    def _get_game_over_prompt(self, game_state: Dict[str, Any]) -> str:
        print("GolfChatbot._get_game_over_prompt called")
        """Generate game over specific prompts"""
        return "The game has ended. React to the final results and congratulate or commiserate as appropriate."

    def _get_dramatic_moment_prompt(self, game_state: Dict[str, Any]) -> str:
        print("GolfChatbot._get_dramatic_moment_prompt called")
        """Generate dramatic moment specific prompts"""

        if excitement > 0.7:
            return "This is a dramatic moment in the game! React with high energy and excitement."
        else:
            return "This is a tense moment in the game. Comment on the drama unfolding."

    def _generate_gif_search_terms(self, bot_name: str, message: str) -> str:
        print("GolfChatbot._generate_gif_search_terms called")
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
        print(f"GolfChatbot.add_message_to_history called with sender={sender}, game_id={game_id}")
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

        print(f' chat history: {self.conversation_history}')




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
    Acts as the "glue" between the web server/game state and the GolfChatbot."""

    def __init__(self, chatbot_instance: GolfChatbot, games_dict: Dict = None, get_game_state_func=None):
        self.chatbot = chatbot_instance
        self.games = games_dict or {}  # Reference to global games dictionary
        self.get_game_state_func = get_game_state_func  # Function to get game state
        # Track conversation history changes per game
        self._game_tracking = {}  # {game_id: {'last_msg_signature': tuple, 'last_check_time': float}}

        # Start the proactive comment timer in a background thread
        threading.Thread(
            target=self.proactive_comment_timer,
            args=('global', PROACTIVE_TIMER),  # Monitor all games for inactivity
            daemon=True
        ).start()

    def update_games_reference(self, games_dict: Dict, get_game_state_func=None):
        """Update the reference to the games dictionary (useful for dependency injection)."""
        self.games = games_dict
        if get_game_state_func:
            self.get_game_state_func = get_game_state_func

        # Update the chatbot with bot objects from all games
        all_bots = []
        for game_session in games_dict.values():
            selected_bots = game_session.get('selected_bots', [])
            all_bots.extend(selected_bots)

        # Remove duplicates based on ai_bot_id
        unique_bots = {}
        for bot in all_bots:
            ai_bot_id = bot.get('ai_bot_id')
            if ai_bot_id and ai_bot_id not in unique_bots:
                unique_bots[ai_bot_id] = bot

        # Update the chatbot with unique bots
        if unique_bots:
            self.chatbot.update_bots(list(unique_bots.values()))

        print(f"ChatHandler updated with {len(games_dict)} games and {len(unique_bots)} unique bots")

    def _get_or_create_game_tracking(self, game_id: str) -> dict:
        """Get or create tracking data for a specific game."""
        if game_id not in self._game_tracking:
            self._game_tracking[game_id] = {
                'last_msg_signature': None,
                'last_check_time': 0
            }
        return self._game_tracking[game_id]

    def proactive_comment_timer(self, game_id='global', time_interval=PROACTIVE_TIMER):
        """
        Waits for inactivity (no conversation history change) for time_interval seconds,
        then triggers proactive comment logic.
        Resets timer every time conversation history changes.

        Args:
            game_id: 'global' to monitor all games, or specific game_id for single game
            time_interval: Seconds to wait for inactivity before triggering proactive comment
        """
        print(f"ChatHandler.proactive_comment_timer started for {game_id}")

        while True:
            # Get list of games to monitor
            games_to_check = list(self.games.keys()) if game_id == 'global' else [game_id]

            for active_game_id in games_to_check:
                game_state = self.get_game_state_func(active_game_id, self.games)
                game_session = self.games[active_game_id]
                # Skip if conversation history changed recently (activity detected)
                if self.has_conversation_history_changed(active_game_id):
                    print(f"[Proactive Timer 720] converstiaon history has changed. {active_game_id}, resetting timer.")
                    continue

                # Check if enough time has passed since last conversation activity
                # last_message_time = 0
                if active_game_id is not None and active_game_id in self.chatbot.conversation_history:
                    last_message = self.chatbot.conversation_history[active_game_id][-1]
                    print(f"[Proactive Timer 717] last message: {last_message}")
                    last_message_time = last_message.get('timestamp', 0)
                    print(f"[Proactive Timer 720] last message time: {last_message_time}")

                # If enough time passed, call should_generate_proactive_comment () which checks dramatic events and variability for each bot timing.
                    if time.time() - last_message_time >= time_interval:
                        print(f"[Proactive Timer 723] No conversation activity in game {active_game_id} for {time_interval}s. Generating proactive comment.")
                        if self.should_generate_proactive_comment(game_state, game_session):
                            # Get bot info and generate proactive response directly
                            selected_bots = game_session.get('selected_bots', [])
                            if selected_bots:
                                # Only 1-2 bots respond per user message
                                max_responses = min(1, len(selected_bots))
                                responding_bots = random.sample(selected_bots, max_responses)

                                for bot_dict in responding_bots:
                                    # Generate a proactive response using generate_response with ai_bot_id
                                    ai_bot_id = bot_dict.get('ai_bot_id')
                                    bot_name = bot_dict.get('name', 'Unknown')
                                    print(f"🔍 PROACTIVE DEBUG: Trying to generate response for bot: {bot_name} (ai_bot_id: {ai_bot_id})")
                                    print(f"🔍 PROACTIVE DEBUG: Available bots in chatbot: {list(self.chatbot.bots.keys())}")
                                    print(f"🔍 PROACTIVE DEBUG 738: Bot exists in chatbot.bots: {ai_bot_id in self.chatbot.bots}")

                                    # Only generate response if bot exists in chatbot.bots
                                    if ai_bot_id in self.chatbot.bots:
                                        conversation_history = self.chatbot.conversation_history.get(active_game_id, [])
                                        print(f' Proactive comment timer calling generate_response 740')
                                        self.chatbot.generate_response(conversation_history, game_state, ai_bot_id)
                                    else:
                                        print(f"🔍 PROACTIVE DEBUG: Skipping bot {bot_name} (ai_bot_id: {ai_bot_id}) - not found in chatbot.bots")


            time.sleep(4)  # Check every second

    def should_generate_proactive_comment(self, game_state: Dict, game_session: Dict) -> bool:
        """Determine if a proactive comment should be generated."""
        # Check for dramatic events
        print(f' [DEBUG] should_generate_proactive_comment called.')
        print(f' [DEBUG] Available bots in chatbot: {list(self.chatbot.bots.keys())}')
        if self.chatbot.is_dramatic_event(game_state):
            print(f' [DEBUG] Dramatic event detected, checking if any bot wants to respond')
            # Check if any bot wants to respond to dramatic events
            for ai_bot_id, bot in self.chatbot.bots.items():
                print(f' [DEBUG] Checking bot: {bot.name} (ai_bot_id: {ai_bot_id})')
                print(f' [DEBUG] Bot has emotional_state: {hasattr(bot, "emotional_state")}')
                if self.chatbot.will_bot_respond(game_state, ai_bot_id):
                    print(f' [DEBUG] Bot {bot.name} wants to respond to dramatic event')
                    return True
            print(f' [DEBUG] No bots want to respond to dramatic event')
            return False

        # Check for inactivity (this is handled by proactive_comment_timer)
        if self.has_conversation_history_changed(game_id):
            return True

        return False



        # TODO
        # (e.g., new round, score changes, etc.)

        # Check for inactivity (this is handled by proactive_comment_timer)

        return True

    def has_conversation_history_changed(self, game_id: str = None, interval: int = CHAT_HISTORY_CHANGE_INTERVAL) -> bool:
        print(f" [DEBUG] conversation_history_changed called.")
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

        # Get per-game tracking data
        tracking = self._get_or_create_game_tracking(game_id or 'global')

        if (
            tracking['last_msg_signature'] != last_msg_signature and
            (current_time - tracking['last_check_time']) >= interval
        ):
            tracking['last_msg_signature'] = last_msg_signature
            tracking['last_check_time'] = current_time
            return True
        return False

    def get_game_id_from_memory(self, user_id: str = None) -> Optional[str]:
        """Get the most recent game_id from memory for a user."""
        print(f"ChatHandler.get_game_id_from_memory called for user_id={user_id}")

        # If we have access to the games dict, we could find the most recent game
        # For now, this is a placeholder for future implementation
        # You could implement logic like:
        # - Find the most recent game for this user
        # - Find the game with the most recent activity
        # - Find the game with unread messages

        # For now, return None to force explicit game_id
        return None

    def handle_user_message(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle send message requests from user. from front end api call. adds conversation history and triggers bot response pipeline."""
        print("DEBUG:handle_user_message Received data:", data)

        # Try to get game_id from request first
        game_id = data.get('game_id')
        message = data.get('message')
        game_state = self.get_game_state_func(game_id, self.games)

        if not message:
            return {'error': 'Message cannot be empty'}, 400

        # Add user message to conversation history
        self.chatbot.add_message_to_history('user', message, game_id)

        # Get bot information from game session
        game_session = self.games.get(game_id)
        bot_responses = []

        if game_session:
            selected_bots = game_session.get('selected_bots', [])
            if selected_bots:
                # Only 1-2 bots respond per user message
                max_responses = min(2, len(selected_bots))
                responding_bots = random.sample(selected_bots, max_responses)

                for bot_dict in responding_bots:
                    # Generate response - bot_dict is a dictionary from game session
                    ai_bot_id = bot_dict.get('ai_bot_id')
                    bot_name = bot_dict.get('name', 'AI Bot')
                    conversation_history = self.chatbot.conversation_history.get(game_id, [])
                    bot_response = self.chatbot.generate_response(conversation_history, game_state, ai_bot_id)
                    self.chatbot.add_message_to_history('bot', bot_response, game_id)

                    # Add bot response to the list to return to frontend
                    bot_responses.append({
                        'bot_name': bot_name,
                        'message': bot_response,
                        'reading_delay': self.calculate_bot_response_delay(ai_bot_id),
                        'should_send_gif': False,  # TODO: implement GIF logic
                        'gif_context': ""
                    })

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
            'game_id': game_id,
            'responses': bot_responses
        }



    def _handle_bot_message(self, message: str, game_state: Dict[str, Any], str, mentioned_bots: List[str]) -> Dict[str, Any]:
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

    def get_bot_reaction_speed(self, ai_bot_id: str) -> float:
        print(f"GolfChatbot.get_bot_reaction_speed called for ai_bot_id={ai_bot_id}")
        """Get the reaction speed for a bot by ai_bot_id from its response_config."""
        bot = self.bots.get(ai_bot_id)
        if bot and hasattr(bot, 'response_config'):
            return bot.response_config.get('reaction_speed', 0.5)
        return 0.5  # default if not found

    def calculate_bot_response_delay(self, ai_bot_id: str) -> float:
        print(f"GolfChatbot.calculate_bot_response_delay called for ai_bot_id={ai_bot_id}")
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




# Example usage:
# chat_handler = ChatHandler(chatbot)
# threading.Thread(target=periodic_conversation_check, args=(chat_handler, 'your_game_id', 5), daemon=True).start()

