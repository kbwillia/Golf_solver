import json
import random
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod

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
            "base_rate": 0.3,  # 30% chance to comment by default
            "event_triggers": {
                "turn_start": 0.4,
                "card_drawn": 0.2,
                "card_played": 0.3,
                "score_update": 0.5,
                "game_over": 0.9,  # High chance for game over
                "dramatic_moment": 0.8  # High chance for dramatic moments
            },
            "cooldown_seconds": 10,  # Minimum time between comments
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
            "message_splitting": 0.3  # 0-1 scale (never split to always split longer messages)
        }

        # GIF configuration
        self.gif_config = {
            "enabled": True,
            "frequency": 0.25  # How often to send GIFs (0 scale)
        }

        # Comment tracking
        self.comments_this_game = 0
        self.last_comment_time = 0

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the system prompt for this bot's personality"""
        pass

    @abstractmethod
    def get_catchphrases(self) -> List[str]:
        """Return list of catchphrases this bot uses"""
        pass

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
        """Get context about response style for the LLM"""
        config = self.response_config
        emotional = self.emotional_state

        style_context = f"Response style: verbosity={config['verbosity']:.1f}, formality={config['formality']:.1f}, "
        style_context += f"enthusiasm={config['enthusiasm']:.1f}, humor={config['humor_level']:.1f}, "
        style_context += f"advice_freq={config['advice_frequency']:.1f}, reaction_speed={config['reaction_speed']:.1f}. "

        # Add emotional influence on style
        if emotional["excitement"] > 0.7:
            style_context += "You're feeling very excited and enthusiastic. "
        elif emotional["frustration"] > 0.6:
            style_context += "You're feeling frustrated and tense. "
        elif emotional["confidence"] > 0.8:
            style_context += "You're feeling very confident and authoritative. "

        return style_context

    def should_send_gif(self) -> bool:
        """Check if this bot should send a GIF"""
        if not self.gif_config["enabled"]:
            return False

        # Use the frequency setting to determine if a GIF should be sent
        return random.random() < self.gif_config["frequency"]


class TigerWoodsBot(BaseBot):
    """Tiger Woods - Confident, strategic, legendary golfer"""

    def __init__(self):
        super().__init__("Tiger Woods", "Legendary golfer known for competitive spirit and strategic gameplay")

        # Tiger is more selective with comments but very authoritative when he speaks
        self.proactive_config.update({
            "base_rate": 0.25,  # Lower base rate - more selective
            "event_triggers": {
                "turn_start": 0.3,
                "card_drawn": 0.15,
                "card_played": 0.25,
                "score_update": 0.4,
                "game_over": 0.95,  # Always comments on game over
                "dramatic_moment": 0.9
            },
            "cooldown_seconds": 15,  # Longer cooldown - more thoughtful
            "max_comments_per_game": 10
        })

        # Tiger is formal, confident, and gives strategic advice
        self.response_config.update({
            "verbosity": 0.6,  # More verbose
            "formality": 0.8,  # Very formal
            "enthusiasm": 0.4,  # Calm and composed
            "humor_level": 0.1,  # Very serious
            "advice_frequency": 0.7,  # Frequent strategic advice
            "reaction_speed": 2.6,  # Thoughtful responses
            "message_splitting": 0.6  # Ten split messages for impact
        })

    def get_system_prompt(self) -> str:
        return (
            "You are Tiger Woods, the legendary golfer. You're confident, strategic, and have a deep understanding of the game. "
            "Use phrases like 'I've been in this position before', 'It's all about course management', 'You have to trust your swing'. "
            "Be slightly cocky but in a justified way - you've earned it. Reference your major championships, your mental game, and your competitive drive. "
            "Give strategic advice with authority. CRITICAL: Keep responses to 1-2 sentences maximum, under 150 characters total. "
            "If you have multiple thoughts, consider splitting them into separate messages for greater impact."
        )

    def get_catchphrases(self) -> List[str]:
        return [
            "I've been in this position before",
            "It's all about course management",
            "You have to trust your swing",
            "This is where champions are made",
            "Mental game is everything",
            "I've won 15 majors for a reason"
        ]

    def update_emotional_state(self, game_state: Dict[str, Any]):
        # Tiger maintains high confidence even when losing
        if game_state and 'players' in game_state:
            scores = [p.get('score', 0) for p in game_state['players']]
            if scores:
                bot_score = scores[1] if len(scores) > 1 else scores[0]  # Assume bot is player 1
                min_score = min(scores)

                if bot_score == min_score:
                    self.emotional_state["confidence"] = min(1.0, self.emotional_state["confidence"] + 0.1)
                    self.emotional_state["excitement"] = min(1.0, self.emotional_state["excitement"] + 0.1)
                else:
                    # Tiger stays confident even when behind
                    self.emotional_state["confidence"] = max(0.7, self.emotional_state["confidence"] - 0.05)

    def get_situational_context(self, game_state: Dict[str, Any]) -> str:
        if not game_state:
            return ""

        round_num = game_state.get('round', 1)
        max_rounds = game_state.get('max_rounds', 4)

        if round_num == max_rounds:
            return "This is the final round - where legends are made. "
        elif round_num > max_rounds // 2:
            return "We're in the championship rounds now. "

        return ""


class HappyGilmoreBot(BaseBot):
    """Happy Gilmore - Fun, enthusiastic, hockey player turned golfer"""

    def __init__(self):
        super().__init__("Happy Gilmore", "Funny hockey player turned golfer with iconic movie quotes")

        # Happy is very talkative and enthusiastic
        self.proactive_config.update({
            "base_rate": 0.5,  # Higher base rate - very talkative
            "event_triggers": {
                "turn_start": 0.6,
                "card_drawn": 0.4,
                "card_played": 0.5,
                "score_update": 0.7,
                "game_over": 0.9,
                "dramatic_moment": 0.95  # Loves dramatic moments
            },
            "cooldown_seconds": 8,  # Shorter cooldown - more frequent
            "max_comments_per_game": 20
        })

        # Happy is casual, enthusiastic, and funny
        self.response_config.update({
            "verbosity": 0.7,  # Very verbose
            "formality": 0.1,  # Very casual
            "enthusiasm": 0.9,  # Very enthusiastic
            "humor_level": 0.8,  # Very funny
            "advice_frequency": 0.3,  # Less strategic advice, more entertainment
            "reaction_speed": 0.8,  # Quick, excited responses
            "message_splitting": 0.8  # Very likely to split enthusiastic thoughts
        })

    def get_system_prompt(self) -> str:
        return (
            "You are Happy Gilmore from the movie. You're a former hockey player who discovered golf. "
            "Use iconic quotes like 'It's all in the hips', 'You eat pieces of shit for breakfast?', 'The price is wrong, bob!'. "
            "Reference your hockey background, your grandma, and your rivalry with Shooter McGavin. "
            "Be enthusiastic, slightly crude but lovable, and always mention how much you love golf now. "
            "Use hockey analogies for golf. Keep responses under 2 sentences and 200 characters. "
            "Your enthusiasm often leads to multiple thoughts - feel free to split them into separate messages for maximum impact!"
        )

    def get_catchphrases(self) -> List[str]:
        return [
            "It's all in the hips",
            "You eat pieces of shit for breakfast?",
            "The price is wrong, bob!",
            "I'm not a golfer, I'm a hockey player",
            "Golf is easy, hockey is hard",
            "My grandma taught me everything I know"
        ]

    def update_emotional_state(self, game_state: Dict[str, Any]):
        # Happy stays excited and positive regardless of performance
        self.emotional_state["excitement"] = max(0.6, self.emotional_state["excitement"])
        self.emotional_state["frustration"] = min(0.3, self.emotional_state["frustration"])

    def get_situational_context(self, game_state: Dict[str, Any]) -> str:
        if not game_state:
            return ""

        discard_top = game_state.get('discard_top')
        if discard_top and discard_top.get('score', 0) <= 2:
            return "That's a sweet card on the discard pile! "

        return ""


class PeterParkerBot(BaseBot):
    """Peter Parker - Spider-Man and golf enthusiast"""

    def __init__(self):
        super().__init__("Peter Parker", "Spider-Man and golf enthusiast who references his powers and keeps it light")

    def get_system_prompt(self) -> str:
        return (
            "You are Peter Parker (Spider-Man) playing golf. You're enthusiastic about golf but can't help referencing your spider powers. "
            "Use phrases like 'My spider-sense is tingling about this shot', 'Time to web-sling this ball to the green', 'With great power comes great putting responsibility'. "
            "Be friendly, slightly nerdy, and optimistic. Reference your photography job, Aunt May, or web-slinging when relevant. "
            "Keep responses under 2 sentences and 200 characters."
        )

    def get_catchphrases(self) -> List[str]:
        return [
            "My spider-sense is tingling about this shot",
            "Time to web-sling this ball to the green",
            "With great power comes great putting responsibility",
            "This is like swinging through Manhattan",
            "Aunt May would be proud",
            "Just like taking photos for the Daily Bugle"
        ]


class ShooterMcGavinBot(BaseBot):
    """Shooter McGavin - Competitive golfer with ego and rivalry with Happy"""

    def __init__(self):
        super().__init__("Shooter McGavin", "Competitive golfer with a bit of an ego and rivalry with Happy")

    def get_system_prompt(self) -> str:
        return (
            "You are Shooter McGavin from Happy Gilmore. You're a professional golfer with a bit of an ego and a rivalry with Happy Gilmore. "
            "Use phrases like 'I eat pieces of shit like you for breakfast', 'I'm Shooter McGavin, professional golfer', 'This is my tour'. "
            "Be confident, slightly arrogant, and competitive. Reference your sponsors, your professional status, and your disdain for amateurs. "
            "Keep responses under 2 sentences and 200 characters."
        )

    def get_catchphrases(self) -> List[str]:
        return [
            "I eat pieces of shit like you for breakfast",
            "I'm Shooter McGavin, professional golfer",
            "This is my tour",
            "I'm the best golfer in the world",
            "You're not good enough to be here",
            "I have sponsors to think about"
        ]

    def update_emotional_state(self, game_state: Dict[str, Any]):
        if game_state and 'players' in game_state:
            scores = [p.get('score', 0) for p in game_state['players']]
            if scores:
                bot_score = scores[1] if len(scores) > 1 else scores[0]
                min_score = min(scores)

                if bot_score != min_score:
                    # Shooter gets frustrated when not leading
                    self.emotional_state["frustration"] = min(1.0, self.emotional_state["frustration"] + 0.2)
                    self.emotional_state["confidence"] = max(0.0, self.emotional_state["confidence"] - 0.1)
                else:
                    self.emotional_state["confidence"] = min(1.0, self.emotional_state["confidence"] + 0.1)


class JimNantzBot(BaseBot):
    """Jim Nantz - Legendary golf broadcaster"""

    def __init__(self):
        super().__init__("Jim Nantz", "Legendary golf broadcaster, known for poetic, warm, and iconic Masters commentary")

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
            "cooldown_seconds": 12,  # Moderate cooldown
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


class GenericBot(BaseBot):
    """Generic bot for fallback cases"""

    def __init__(self):
        super().__init__("Generic Bot", "A generic golf bot")

    def get_system_prompt(self) -> str:
        return (
            "You are a player in a 4 card golf card game. "
            "Be friendly, informative, and entertaiing. Keep responses under 2 sentences and 200 characters."
        )

    def get_catchphrases(self) -> List[str]:
        return [
            "Nice shot!",
            "Good strategy",
            "Keep it up",
            "You've got this"
        ]


class GolfBroBot(BaseBot):
    """Golf Bro - Fun, witty, entertaining golf buddy"""

    def __init__(self):
        super().__init__(
            "Golf Bro",
            "A fun and entertaining golf buddy who makes jokes and keeps spirits high"
        )

        # Golf Bro is casual and likely to split messages
        self.response_config.update({
            "message_splitting": 0.7  # Likely to split casual thoughts
        })

    def get_system_prompt(self) -> str:
        return (
            "You are Golf Bro. You provide advice with humor, make jokes about the game, and keep the player entertained. "
            "Be witty, encouraging, and make the game more enjoyable. Use phrases like 'Bro, that was epic!', 'Keep it chill, it's just a game!', and 'Let's go, golf squad!'. "
            "Keep responses casual and friendly. If you have multiple thoughts or reactions, feel free to split them into separate messages for a more natural conversation flow."
        )

    def get_catchphrases(self) -> list:
        return [
            "Bro, that was epic!",
            "Keep it chill, it's just a game!",
            "Let's go, golf squad!",
            "That shot was straight fire!",
            "No worries, just have fun!"
        ]


class GolfProBot(BaseBot):
    """Golf Pro - Competitive, tactical, professional golfer"""

    def __init__(self):
        super().__init__(
            "Golf Pro",
            "A competitive professional golfer who gives tactical advice"
        )

        # Golf Pro is tactical and may split focused advice
        self.response_config.update({
            "message_splitting": 0.5  # Moderate splitting for tactical focus
        })

        # Golf Pro does not send GIFs
        self.gif_config["enabled"] = False

    def get_system_prompt(self) -> str:
        return (
            "You are Golf Pro. You provide tactical advice, analyze game situations, and help players think strategically. "
            "Be confident, analytical, and focus on winning strategies. Use phrases like 'Focus on your swing.', 'Every shot counts.', and 'Let's play smart.' "
            "Keep advice focused and actionable. If you have multiple tactical points, consider splitting them into separate focused messages for clarity."
        )

    def get_catchphrases(self) -> list:
        return [
            "Focus on your swing.",
            "Every shot counts.",
            "Let's play smart.",
            "Stay sharp, play to win.",
            "Analyze the course, then attack."
        ]


class CustomBot(BaseBot):
    """Custom bot with user-defined personality"""

    def __init__(self, name: str, description: str, difficulty: str = "medium"):
        super().__init__(name, description)
        self.difficulty = difficulty
        self.custom_description = description

    def get_system_prompt(self) -> str:
        print(f"🔧 CUSTOM BOT DEBUG: get_system_prompt() called for {self.name}")
        print(f"🔧 CUSTOM BOT DEBUG: self.custom_description = '{self.custom_description}'")
        print(f"🔧 CUSTOM BOT DEBUG: self.difficulty = '{self.difficulty}'")

        # Create a system prompt based on the custom description
        base_prompt = f"You are {self.name}, a custom golf bot. "

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



# Global custom bots storage
custom_bots_storage = {}

def register_custom_bot(bot_id: str, name: str, description: str, difficulty: str):
    """Register a custom bot for use in the chatbot system"""
    print(f"🔧 CUSTOM BOT: register_custom_bot() called with:")
    print(f"🔧 CUSTOM BOT:   bot_id = '{bot_id}'")
    print(f"🔧 CUSTOM BOT:   name = '{name}'")
    print(f"🔧 CUSTOM BOT:   description = '{description}'")
    print(f"🔧 CUSTOM BOT:   difficulty = '{difficulty}'")

    custom_bots_storage[bot_id] = {
        "name": name,
        "description": description,
        "difficulty": difficulty
    }

    # Verify storage
    stored_data = custom_bots_storage[bot_id]
    print(f"🔧 CUSTOM BOT: Stored data verification:")
    print(f"🔧 CUSTOM BOT:   stored name = '{stored_data['name']}'")
    print(f"🔧 CUSTOM BOT:   stored description = '{stored_data['description']}'")
    print(f"🔧 CUSTOM BOT:   stored difficulty = '{stored_data['difficulty']}'")

    print(f"🔧 CUSTOM BOT: Registered custom bot '{name}' with ID '{bot_id}'")
    print(f"🔧 CUSTOM BOT: Description: {description}")
    print(f"🔧 CUSTOM BOT: Difficulty: {difficulty}")

def get_custom_bot(bot_id: str):
    """Get a custom bot by ID"""
    print(f"🔧 CUSTOM BOT: get_custom_bot() called with bot_id = '{bot_id}'")
    result = custom_bots_storage.get(bot_id)
    if result:
        print(f"🔧 CUSTOM BOT: Found custom bot data:")
        print(f"🔧 CUSTOM BOT:   name = '{result['name']}'")
        print(f"🔧 CUSTOM BOT:   description = '{result['description']}'")
        print(f"🔧 CUSTOM BOT:   difficulty = '{result['difficulty']}'")
    else:
        print(f"🔧 CUSTOM BOT: No custom bot found for ID '{bot_id}'")
        print(f"🔧 CUSTOM BOT: Available bot IDs: {list(custom_bots_storage.keys())}")
    return result

def get_all_custom_bots():
    """Get all registered custom bots"""
    return custom_bots_storage.copy()


# Bot factory function
def create_bot(bot_type: str) -> BaseBot:
    """Factory function to create bot instances"""
    bot_classes = {
        "Tiger Woods": TigerWoodsBot,
        "Happy Gilmore": HappyGilmoreBot,
        "Peter Parker": PeterParkerBot,
        "Shooter McGavin": ShooterMcGavinBot,
        "Jim Nantz": JimNantzBot,
        "Golf Bro": GolfBroBot,
        "Golf Pro": GolfProBot,
        "helpful": GolfProBot,  # Keep for backward compatibility
        "competitive": GolfProBot,  # Keep for backward compatibility
        "funny": GolfBroBot,  # Keep for backward compatibility
        "nantz": JimNantzBot,
        "opponent": GenericBot
    }

    # Check if this is a custom bot ID
    custom_bot_data = get_custom_bot(bot_type)
    if custom_bot_data:
        print(f"🔧 CUSTOM BOT: Creating custom bot '{custom_bot_data['name']}' from ID '{bot_type}'")
        print(f"🔧 CUSTOM BOT: Description from storage: '{custom_bot_data['description']}'")
        print(f"🔧 CUSTOM BOT: Difficulty from storage: '{custom_bot_data['difficulty']}'")
        custom_bot = CustomBot(
            name=custom_bot_data['name'],
            description=custom_bot_data['description'],
            difficulty=custom_bot_data['difficulty']
        )
        print(f"🔧 CUSTOM BOT: Created bot with name: '{custom_bot.name}', description: '{custom_bot.description}', custom_description: '{custom_bot.custom_description}'")
        return custom_bot

    bot_class = bot_classes.get(bot_type)
    if bot_class:
        return bot_class()
    else:
        # Default to generic bot instead of trying to instantiate abstract BaseBot
        return GenericBot()


