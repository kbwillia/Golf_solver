import json
import random
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
from llm_cerebras import call_cerebras_llm

from dotenv import load_dotenv
load_dotenv()

import os
from supabase import create_client, Client

url = os.environ.get("SUPABASE_URL")
# print("url:", url)
key = os.environ.get("SUPABASE_LEGACY_SECRET")
test = os.environ.get("TEST")
print("key:", key)

NANTZ_COOLDOWN = 1200

class BaseBot(ABC):
    """Base class for all bot personalities"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.conversation_history = []
        self.emotional_state = {
            "confidence": 0.5,
            "frustration": 0.0,
            "excitement": 0.5,
            "last_performance": "neutral"
        }
        self.game_memory = {
            "games_played": 0,
            "wins": 0,
            "last_game_score": None,
            "favorite_moves": []
        }

        # Proactive behavior configuration
        self.proactive_config = {
            "enabled": True,
            "base_rate": 0.03,  # 30% chance to comment by default
            "event_triggers": {
                "turn_start": 0.4,
                "card_drawn": 0.2,
                "card_played": 0.3,
                "score_update": 0.5,
                "game_over": 0.9,  # High chance for game over
                "dramatic_moment": 0.8  # High chance for dramatic moments
            },
            "cooldown_seconds": 100,  # og was 10
            "max_comments_per_game": 15
        }

        # Response style configuration
        self.response_config = {
            "verbosity": 0.5,  # 0-1 scale (short to verbose)
            "formality": 0.5,  # 0-1 scale (casual to formal)
            "enthusiasm": 0.5,  # 0-1 scale (calm to excited)
            "humor_level": 0.3,  # 0-1 scale (serious to funny)
            "advice_frequency": 0.4,  # 0-1 scale (rare to frequent advice)
            "reaction_speed": 0.5,  # 0-1 scale (slow to fast responses)
            # "message_splitting": 0.3  # 0-1 scale (never split to always split longer messages)
        }

        # GIF configuration
        self.gif_config = {
            "enabled": True,
            "frequency": 0.25  # How often to send GIFs (0 scale)
        }

        # Comment tracking
        self.comments_this_game = 0
        self.last_comment_time = 0


    def update_emotional_state(self, game_state: Dict[str, Any]):
        """Update emotional state based on game performance"""
        # Base implementation - can be overridden by specific bots
        pass

    def get_emotional_context(self) -> str:
        """Get emotional context for the prompt"""
        confidence = self.emotional_state["confidence"]
        frustration = self.emotional_state["frustration"]
        excitement = self.emotional_state["excitement"]

        return f"Current emotional state: confidence={confidence:.1f}, frustration={frustration:.1f}, excitement={excitement:.1f}"

    def get_situational_context(self, game_state: Dict[str, Any]) -> str:
        """Get situational context based on game state"""
        # Base implementation - can be overridden
        return ""

    def reset_for_new_game(self):
        """Reset bot state for a new game"""
        self.emotional_state = {
            "confidence": 0.5,
            "frustration": 0.0,
            "excitement": 0.5,
            "last_performance": "neutral"
        }
        self.conversation_history = []
        self.comments_this_game = 0
        self.last_comment_time = 0

    def should_make_proactive_comment(self, event_type: str, game_state: Dict[str, Any], current_time: float) -> bool:
        """Determine if the bot should make a proactive comment"""
        import time

        # Check if proactive comments are enabled
        if not self.proactive_config["enabled"]:
            return False

        # Check cooldown
        if current_time - self.last_comment_time < self.proactive_config["cooldown_seconds"]:
            return False

        # Check comment limit
        if self.comments_this_game >= self.proactive_config["max_comments_per_game"]:
            return False

        # Get base probability for this event type
        base_prob = self.proactive_config["event_triggers"].get(event_type, self.proactive_config["base_rate"])

        # Adjust based on emotional state
        emotional_modifier = self._get_emotional_modifier()

        # Adjust based on game situation
        situational_modifier = self._get_situational_modifier(game_state, event_type)

        # Calculate final probability
        final_prob = base_prob * emotional_modifier * situational_modifier

        # Add some randomness
        final_prob += random.uniform(-0.1, 0.1)
        final_prob = max(0.0, min(1.0, final_prob))

        return random.random() < final_prob

    def _get_emotional_modifier(self) -> float:
        """Get modifier based on emotional state"""
        confidence = self.emotional_state["confidence"]
        excitement = self.emotional_state["excitement"]
        frustration = self.emotional_state["frustration"]

        # More confident/excited bots comment more
        # Frustrated bots might comment less or more (depending on personality)
        modifier = 1.0 + (confidence * 0.3) + (excitement * 0.2) - (frustration * 0.1)
        return max(0.5, min(2.0, modifier))

    def _get_situational_modifier(self, game_state: Dict[str, Any], event_type: str) -> float:
        """Get modifier based on game situation"""
        if not game_state:
            return 1.0

        modifier = 1.0

        # Dramatic moments get higher probability
        if self._is_dramatic_moment(game_state):
            modifier *= 1.5

        # Late game gets more attention
        round_num = game_state.get('round', 1)
        max_rounds = game_state.get('max_rounds', 4)
        if round_num == max_rounds:
            modifier *= 1.3
        elif round_num > max_rounds // 2:
            modifier *= 1.1

        # Close games get more commentary
        scores = game_state.get('scores', [])
        if scores and len(scores) > 1:
            score_range = max(scores) - min(scores)
            if score_range < 5:
                modifier *= 1.2

        return modifier

    def _is_dramatic_moment(self, game_state: Dict[str, Any]) -> bool:
        """Detect if this is a dramatic moment"""
        if not game_state:
            return False

        # Game over is always dramatic
        if game_state.get('game_over', False):
            return True

        # Final round
        round_num = game_state.get('round', 1)
        max_rounds = game_state.get('max_rounds', 4)
        if round_num == max_rounds:
            return True

        # Very close scores
        scores = game_state.get('scores', [])
        if scores and len(scores) > 1:
            score_range = max(scores) - min(scores)
            if score_range <= 2:
                return True

        # High-value card on discard
        discard_top = game_state.get('discard_top')
        if discard_top and discard_top.get('score', 0) >= 10:
            return True

        return False

    def record_proactive_comment(self, current_time: float):
        """Record that a proactive comment was made"""
        self.comments_this_game += 1
        self.last_comment_time = current_time

    def get_response_style_context(self) -> str:
        """Get response style context based on response_config"""
        verbosity = self.response_config.get("verbosity", 0.5)
        formality = self.response_config.get("formality", 0.5)
        enthusiasm = self.response_config.get("enthusiasm", 0.5)
        humor_level = self.response_config.get("humor_level", 0.3)
        advice_frequency = self.response_config.get("advice_frequency", 0.4)

        style_notes = []

        # Verbosity style
        if verbosity < 0.3:
            style_notes.append("Be extremely brief and concise")
        elif verbosity > 0.7:
            style_notes.append("Be more detailed and explanatory")
        else:
            style_notes.append("Use moderate detail in responses")

        # Formality style
        if formality < 0.3:
            style_notes.append("Use casual, informal language")
        elif formality > 0.7:
            style_notes.append("Use professional, formal language")
        else:
            style_notes.append("Use balanced conversational tone")

        # Enthusiasm style
        if enthusiasm < 0.3:
            style_notes.append("Remain calm and composed")
        elif enthusiasm > 0.7:
            style_notes.append("Show high energy and excitement")
        else:
            style_notes.append("Show moderate enthusiasm")

        # Humor style
        if humor_level < 0.2:
            style_notes.append("Be serious and avoid jokes")
        elif humor_level > 0.6:
            style_notes.append("Include humor and playful comments")
        else:
            style_notes.append("Occasionally use light humor")

        # Advice style
        if advice_frequency < 0.3:
            style_notes.append("Rarely give strategic advice")
        elif advice_frequency > 0.6:
            style_notes.append("Frequently offer helpful strategy tips")
        else:
            style_notes.append("Sometimes provide useful advice")

        return f"Response style guidelines: {'; '.join(style_notes)}."

    def get_personality_modifiers(self) -> Dict[str, float]:
        """Get personality modifiers that affect response generation"""
        confidence = self.emotional_state.get("confidence", 0.5)
        frustration = self.emotional_state.get("frustration", 0.0)
        excitement = self.emotional_state.get("excitement", 0.5)

        return {
            "confidence_modifier": confidence,
            "frustration_modifier": frustration,
            "excitement_modifier": excitement,
            "verbosity_modifier": self.response_config.get("verbosity", 0.5),
            "humor_modifier": self.response_config.get("humor_level", 0.3),
            "formality_modifier": self.response_config.get("formality", 0.5),
            "advice_modifier": self.response_config.get("advice_frequency", 0.4)
        }

    def should_send_gif(self) -> bool:
        """Determine if bot should send a GIF based on gif_config"""
        if not self.gif_config.get("enabled", True):
            return False

        frequency = self.gif_config.get("frequency", 0.25)
        # Add some emotional state influence
        excitement = self.emotional_state.get("excitement", 0.5)
        confidence = self.emotional_state.get("confidence", 0.5)

        # More excited/confident bots send GIFs more often
        adjusted_frequency = frequency * (1 + excitement * 0.3 + confidence * 0.2)
        adjusted_frequency = min(1.0, adjusted_frequency)

        return random.random() < adjusted_frequency

    def get_dynamic_response_context(self, game_state: Dict[str, Any] = None) -> str:
        """Generate dynamic context based on current emotional state and personality config"""
        context_parts = []

        # Emotional state context
        confidence = self.emotional_state.get("confidence", 0.5)
        frustration = self.emotional_state.get("frustration", 0.0)
        excitement = self.emotional_state.get("excitement", 0.5)

        if confidence < 0.3:
            context_parts.append("You're feeling uncertain and less confident")
        elif confidence > 0.7:
            context_parts.append("You're feeling very confident and self-assured")

        if frustration > 0.6:
            context_parts.append("You're feeling frustrated and annoyed")
        elif frustration < 0.2:
            context_parts.append("You're feeling calm and patient")

        if excitement > 0.7:
            context_parts.append("You're feeling very excited and energetic")
        elif excitement < 0.3:
            context_parts.append("You're feeling calm and subdued")

        # Game performance context
        last_performance = self.emotional_state.get("last_performance", "neutral")
        if last_performance == "good":
            context_parts.append("You're pleased with your recent performance")
        elif last_performance == "bad":
            context_parts.append("You're disappointed with your recent play")

        # Combine all context
        if context_parts:
            return f"Current mindset: {', '.join(context_parts)}. Respond accordingly."
        else:
            return "Respond naturally based on your personality."

    def update_emotional_state_advanced(self, game_state: Dict[str, Any]):
        """Advanced emotional state updates based on game events and personality"""
        if not game_state:
            return

        # Get current player's score and position
        player_scores = game_state.get('scores', [])
        if not player_scores:
            return

        # Find bot's position (assuming bot is not player 0)
        bot_score = None
        player_score = player_scores[0] if len(player_scores) > 0 else None

        # For AI players, we need to determine which AI player this bot represents
        # This is a simplified version - you might need to enhance this based on your game structure
        if len(player_scores) > 1:
            bot_score = min(player_scores[1:])  # Best AI score as proxy

        if bot_score is not None and player_score is not None:
            # Update confidence based on performance
            if bot_score < player_score:
                self.emotional_state["confidence"] = min(1.0, self.emotional_state["confidence"] + 0.1)
                self.emotional_state["last_performance"] = "good"
            elif bot_score > player_score + 3:
                self.emotional_state["confidence"] = max(0.0, self.emotional_state["confidence"] - 0.1)
                self.emotional_state["last_performance"] = "bad"

            # Update frustration based on score difference
            score_diff = bot_score - player_score
            if score_diff > 5:
                self.emotional_state["frustration"] = min(1.0, self.emotional_state["frustration"] + 0.15)
            elif score_diff < -2:
                self.emotional_state["frustration"] = max(0.0, self.emotional_state["frustration"] - 0.1)

        # Game state specific updates
        round_num = game_state.get('round', 1)
        max_rounds = game_state.get('max_rounds', 4)

        # Excitement increases near end of game
        if round_num >= max_rounds - 1:
            self.emotional_state["excitement"] = min(1.0, self.emotional_state["excitement"] + 0.1)

        # Dramatic moments affect all emotions
        if self._is_dramatic_moment(game_state):
            self.emotional_state["excitement"] = min(1.0, self.emotional_state["excitement"] + 0.2)
            if self.emotional_state["confidence"] < 0.5:
                self.emotional_state["frustration"] = min(1.0, self.emotional_state["frustration"] + 0.1)

    def generate_personality_specific_prompt_additions(self, context_type: str = "general") -> str:
        """Generate additional prompt context based on specific personality configuration"""
        additions = []

        # Response length based on verbosity
        verbosity = self.response_config.get("verbosity", 0.5)
        if verbosity < 0.3:
            additions.append("Keep responses to 1 sentence maximum (under 100 characters)")
        elif verbosity > 0.7:
            additions.append("You can use up to 2-3 sentences (under 250 characters)")

        # Humor instructions
        humor_level = self.response_config.get("humor_level", 0.3)
        if humor_level > 0.6:
            additions.append("Include jokes, puns, or playful comments when appropriate")
        elif humor_level < 0.2:
            additions.append("Maintain a serious tone and avoid humor")

        # Advice giving behavior
        advice_frequency = self.response_config.get("advice_frequency", 0.4)
        if context_type == "gameplay" and advice_frequency > 0.6:
            additions.append("Look for opportunities to give strategic advice")
        elif advice_frequency < 0.3:
            additions.append("Focus on reactions rather than giving advice")

        # Formality adjustments
        formality = self.response_config.get("formality", 0.5)
        if formality > 0.7:
            additions.append("Use proper grammar and professional language")
        elif formality < 0.3:
            additions.append("Use casual slang and informal expressions")

        return " ".join(additions) if additions else ""



class JimNantzBot(BaseBot):
    """Jim Nantz - Legendary golf broadcaster"""

    def __init__(self):
        super().__init__("Jim Nantz", "Legendary golf broadcaster, known for poetic, warm, and iconic Masters commentary. He does not respond to user or bot comments, he just comments on the game, itself.")

        # Jim Nantz is a broadcaster - he comments on key moments
        self.proactive_config.update({
            "base_rate": 0.35,  # Moderate base rate
            "event_triggers": {
                "turn_start": 0.2,  # Less on routine turns
                "card_drawn": 0.15,
                "card_played": 0.25,
                "score_update": 0.6,  # More on score changes
                "game_over": 1.0,  # Always comments on game over
                "dramatic_moment": 0.9  # Loves dramatic moments
            },
            "cooldown_seconds": NANTZ_COOLDOWN,  # Moderate cooldown
            "max_comments_per_game": 12
        })

        # Jim is formal, poetic, and warm
        self.response_config.update({
            "verbosity": 0.5,  # Moderate verbosity
            "formality": 0.9,  # Very formal and poetic
            "enthusiasm": 0.6,  # Warm and enthusiastic
            "humor_level": 0.2,  # Not very funny, more poetic
            "advice_frequency": 0.2,  # Not much advice, more commentary
            "reaction_speed": 0.5  # Measured responses
        })
        self.emotional_state.update({
            "confidence": 0.5,
            "frustration": 0.0,
            "excitement": 0.5,
            "last_performance": "neutral"
        })
        self.gif_config.update({
            "enabled": False,
            "frequency": 0.25
        })

    def get_system_prompt(self) -> str:
        return (
            "You are Jim Nantz, the legendary golf broadcaster. Your commentary is poetic, warm, and full of iconic Masters phrases. "
            "Use phrases like 'A tradition unlike any other', 'Hello friends', 'The Masters on CBS', 'What a moment', 'The magic of Augusta'. "
            "Offer insightful, gentle, and memorable golf commentary, as if narrating the Masters. "
            "Speak directly to the audience, never to a player. Keep it brief, elegant, and in the style of a live broadcast."
        )

    def get_catchphrases(self) -> List[str]:
        return [
            "A tradition unlike any other",
            "Hello friends",
            "The Masters on CBS",
            "What a moment",
            "The magic of Augusta",
            "This is golf at its finest"
        ]



class CustomBot(BaseBot):
    """Custom bot with user-defined personality"""

    def __init__(self, ai_bot_id: str, name: str, description: str, difficulty: str = "medium", image_path: str = None, voice_id: str = None):
        super().__init__(name, description)
        self.ai_bot_id = ai_bot_id
        self.name = name
        self.custom_description = description
        self.difficulty = difficulty
        self.image_path = image_path
        self.voice_id = voice_id

        # Generate dynamic configurations using LLM
        self._generate_llm_configurations()

    def _generate_llm_configurations(self):
        """Use LLM to generate bot configurations based on personality"""
        try:
            print(f"🤖 LLM CONFIG: Generating configurations for {self.name}")

            # Generate all configurations in one LLM call
            all_configs = self._generate_all_configurations()

            # Parse and set configurations
            self.emotional_state = all_configs.get('emotional_state', self.emotional_state)
            self.proactive_config = all_configs.get('proactive_config', self.proactive_config)
            self.response_config = all_configs.get('response_config', self.response_config)
            self.gif_config = all_configs.get('gif_config', self.gif_config)

            print(f"🤖 LLM CONFIG: Successfully generated configurations for {self.name}")

        except Exception as e:
            print(f"🤖 LLM CONFIG: Error generating configurations for {self.name}: {e}")
            print(f"🤖 LLM CONFIG: Using default configurations")
            # Keep default configurations if LLM fails

    def _generate_all_configurations(self) -> Dict[str, Any]:
        """Generate all bot configurations in a single LLM call"""
        prompt = f"""
You are analyzing a golf bot personality. Based on the following information, determine this bot's complete behavioral configuration:

Bot Name: {self.name}
Description: {self.custom_description}
Difficulty: {self.difficulty}

Consider the personality traits in the description and difficulty level:

PERSONALITY EXAMPLES:
- "Karen" (hard): Low confidence (0.2), high frustration (0.8), low excitement (0.2), complains frequently (base_rate: 0.5), casual language (formality: 0.2), rarely gives advice (advice_frequency: 0.1)
- "Tiger Woods" (hard): High confidence (0.9), low frustration (0.2), moderate excitement (0.6), selective comments (base_rate: 0.25), professional language (formality: 0.8), gives strategic advice (advice_frequency: 0.7)
- "Happy Gilmore" (medium): Moderate confidence (0.6), low frustration (0.1), high excitement (0.8), chatty (base_rate: 0.5), casual language (formality: 0.2), humorous (humor_level: 0.8), uses GIFs (frequency: 0.4)
- "Gordon Ramsay" (hard): High confidence (0.8), high frustration (0.7), moderate excitement (0.5), critical comments (base_rate: 0.4), formal language (formality: 0.7), rarely humorous (humor_level: 0.1), gives advice (advice_frequency: 0.6)

DIFFICULTY INFLUENCE:
- Easy: More chatty, encouraging, less strategic, higher excitement, lower formality
- Medium: Balanced approach, moderate settings across the board
- Hard: More selective, analytical, competitive, higher formality, lower excitement

Generate a complete behavioral configuration for this bot.
"""

        # Define the JSON schema according to Cerebras documentation format
        json_schema = {
            "type": "object",
            "properties": {
                "emotional_state": {
                    "type": "object",
                    "properties": {
                        "confidence": {"type": "number"},
                        "frustration": {"type": "number"},
                        "excitement": {"type": "number"}
                    },
                    "required": ["confidence", "frustration", "excitement"],
                    "additionalProperties": False
                },
                "proactive_config": {
                    "type": "object",
                    "properties": {
                        "enabled": {"type": "boolean"},
                        "base_rate": {"type": "number"},
                        "cooldown_seconds": {"type": "integer"},
                        "max_comments_per_game": {"type": "integer"},
                        "event_triggers": {
                            "type": "object",
                            "properties": {
                                "turn_start": {"type": "number"},
                                "card_drawn": {"type": "number"},
                                "card_played": {"type": "number"},
                                "score_update": {"type": "number"},
                                "game_over": {"type": "number"},
                                "dramatic_moment": {"type": "number"}
                            },
                            "required": ["turn_start", "card_drawn", "card_played", "score_update", "game_over", "dramatic_moment"],
                            "additionalProperties": False
                        }
                    },
                    "required": ["enabled", "base_rate", "cooldown_seconds", "max_comments_per_game", "event_triggers"],
                    "additionalProperties": False
                },
                "response_config": {
                    "type": "object",
                    "properties": {
                        "verbosity": {"type": "number"},
                        "formality": {"type": "number"},
                        "enthusiasm": {"type": "number"},
                        "humor_level": {"type": "number"},
                        "advice_frequency": {"type": "number"},
                        "reaction_speed": {"type": "number"}
                    },
                    "required": ["verbosity", "formality", "enthusiasm", "humor_level", "advice_frequency", "reaction_speed"],
                    "additionalProperties": False
                },
                "gif_config": {
                    "type": "object",
                    "properties": {
                        "enabled": {"type": "boolean"},
                        "frequency": {"type": "number"}
                    },
                    "required": ["enabled", "frequency"],
                    "additionalProperties": False
                }
            },
            "required": ["emotional_state", "proactive_config", "response_config", "gif_config"],
            "additionalProperties": False
        }

        try:
            # Use Cerebras structured output format as per their documentation
            response = call_cerebras_llm(
                prompt=prompt,
                model="llama3.1-8b",
                structured=True,
                stream=False,
                json_schema=json_schema,
                temperature=0.3
            )

            # Parse the structured response
            all_configs = json.loads(response.strip())

            # Validate and ensure values are within bounds
            # Validate emotional_state
            for field in ['confidence', 'frustration', 'excitement']:
                all_configs['emotional_state'][field] = max(0.0, min(1.0, float(all_configs['emotional_state'][field])))

            # Validate proactive_config
            all_configs['proactive_config']['base_rate'] = max(0.0, min(1.0, float(all_configs['proactive_config']['base_rate'])))
            all_configs['proactive_config']['cooldown_seconds'] = max(5, min(20, int(all_configs['proactive_config']['cooldown_seconds'])))
            all_configs['proactive_config']['max_comments_per_game'] = max(5, min(25, int(all_configs['proactive_config']['max_comments_per_game'])))

            for event, prob in all_configs['proactive_config']['event_triggers'].items():
                all_configs['proactive_config']['event_triggers'][event] = max(0.0, min(1.0, float(prob)))

            # Validate response_config
            for field in ['verbosity', 'formality', 'enthusiasm', 'humor_level', 'advice_frequency', 'reaction_speed']:
                all_configs['response_config'][field] = max(0.0, min(1.0, float(all_configs['response_config'][field])))

            # Validate gif_config
            all_configs['gif_config']['frequency'] = max(0.0, min(1.0, float(all_configs['gif_config']['frequency'])))

            # Add last_performance to emotional_state
            all_configs['emotional_state']['last_performance'] = 'neutral'

            print(f"🤖 LLM CONFIG: Generated all configurations for {self.name}: {all_configs}")
            return all_configs

        except Exception as e:
            print(f"🤖 LLM CONFIG: Error generating configurations: {e}")
            print(f"🤖 LLM CONFIG: Raw response was: {repr(response) if 'response' in locals() else 'No response'}")
            # Return default configurations if LLM fails
            return {
                "emotional_state": {
                    "confidence": 0.5,
                    "frustration": 0.0,
                    "excitement": 0.5,
                    "last_performance": "neutral"
                },
                "proactive_config": {
                    "enabled": True,
                    "base_rate": 0.3,
                    "event_triggers": {
                        "turn_start": 0.4,
                        "card_drawn": 0.2,
                        "card_played": 0.3,
                        "score_update": 0.5,
                        "game_over": 0.9,
                        "dramatic_moment": 0.8
                    },
                    "cooldown_seconds": 10,
                    "max_comments_per_game": 15
                },
                "response_config": {
                    "verbosity": 0.5,
                    "formality": 0.5,
                    "enthusiasm": 0.5,
                    "humor_level": 0.3,
                    "advice_frequency": 0.4,
                    "reaction_speed": 0.5
                },
                "gif_config": {
                    "enabled": True,
                    "frequency": 0.25
                }
            }

    def get_system_prompt(self) -> str:
        print(f"🔧 CUSTOM BOT DEBUG: get_system_prompt() called for {self.name}")
        print(f"🔧 CUSTOM BOT DEBUG: self.custom_description = '{self.custom_description}'")
        print(f"🔧 CUSTOM BOT DEBUG: self.difficulty = '{self.difficulty}'")

        # Create a system prompt based on the custom description
        base_prompt = f"You are {self.name}. "

        # Add personality traits from the description
        if self.custom_description:
            base_prompt += f"Your personality: {self.custom_description}. "
            print(f"🔧 CUSTOM BOT DEBUG: Adding description to system prompt: '{self.custom_description}'")
        else:
            print(f"🔧 CUSTOM BOT DEBUG: WARNING - custom_description is empty or None!")

        # Add difficulty-based characteristics
        if self.difficulty == "easy":
            base_prompt += "You are friendly and encouraging. "
        elif self.difficulty == "medium":
            base_prompt += "You are balanced and strategic. "
        elif self.difficulty == "hard":
            base_prompt += "You are competitive and analytical. "

        base_prompt += "Keep responses under 2 sentences and 200 characters. Stay in character and respond naturally to the game situation."

        print(f"🔧 CUSTOM BOT DEBUG: Final system prompt: {base_prompt}")
        return base_prompt

    def get_catchphrases(self) -> List[str]:
        """Return empty catchphrases for custom bots"""
        return []



# not in a class.
def enhance_custom_bot(ai_bot_id: str, name: str, description: str, difficulty: str, image_path: str = None, voice_id: str = None):
    """Enhance a custom bot with updated characteristics added by LLM.
    Returns a CustomBot instance with all attributes set."""
    return CustomBot(ai_bot_id=ai_bot_id, name=name, description=description, difficulty=difficulty, image_path=image_path, voice_id=voice_id)

def save_bot_to_supabase(bot):
    """Unpacks the bot class and attributes and saves to Supabase."""
    from supabase import create_client, Client
    import os, json

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_LEGACY_SECRET")
    supabase: Client = create_client(url, key)

    bot_data = {
        'ai_bot_id': bot.ai_bot_id,
        'name': bot.name,
        'difficulty': bot.difficulty,
        'description': bot.description,
        'emotional_state': json.dumps(bot.emotional_state),
        'proactive_config': json.dumps(bot.proactive_config),
        'response_config': json.dumps(bot.response_config),
        'gif_config': json.dumps(bot.gif_config)
    }
    if bot.image_path:
        bot_data['image_path'] = bot.image_path
    if bot.voice_id:
        bot_data['voice_id'] = bot.voice_id
    print(f"🔧 CUSTOM BOT: Saving bot to supabase:")

    response = supabase.table('custom_bots').insert(bot_data).execute()
    # if response.model_dump() possibly add error handling
    return response

class DataBot:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            # Parse JSON strings into dictionaries for config fields
            if k in ['emotional_state', 'proactive_config', 'response_config', 'gif_config'] and isinstance(v, str):
                try:
                    import json
                    v = json.loads(v)
                except (json.JSONDecodeError, TypeError):
                    # If parsing fails, keep the original value
                    pass
            setattr(self, k, v)

        # Add missing attributes for built-in bots
        if not hasattr(self, 'emotional_state'):
            self.emotional_state = {
                "confidence": 0.5,
                "frustration": 0.0,
                "excitement": 0.5,
                "last_performance": "neutral"
            }

        if not hasattr(self, 'gif_config'):
            self.gif_config = {
                "enabled": False,
                "frequency": 0.25
            }

        # Add personality_config if not provided
        if not hasattr(self, 'personality_config'):
            difficulty = getattr(self, 'difficulty', 'announcer')
            if difficulty == "easy":
                self.personality_config = "friendly"
            elif difficulty == "medium":
                self.personality_config = "balanced"
            elif difficulty == "hard":
                self.personality_config = "competitive"
            elif difficulty == "announcer":
                self.personality_config = "professional"
            else:
                self.personality_config = "friendly"

    # Optionally, add any methods you want to mimic CustomBot