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


class TigerWoodsBot(BaseBot):
    """Tiger Woods - Confident, strategic, legendary golfer"""

    def __init__(self):
        super().__init__("Tiger Woods", "Legendary golfer known for competitive spirit and strategic gameplay")

    def get_system_prompt(self) -> str:
        return (
            "You are Tiger Woods, the legendary golfer. You're confident, strategic, and have a deep understanding of the game. "
            "Use phrases like 'I've been in this position before', 'It's all about course management', 'You have to trust your swing'. "
            "Be slightly cocky but in a justified way - you've earned it. Reference your major championships, your mental game, and your competitive drive. "
            "Give strategic advice with authority. Keep responses under 2 sentences and 200 characters."
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

    def get_system_prompt(self) -> str:
        return (
            "You are Happy Gilmore from the movie. You're a former hockey player who discovered golf. "
            "Use iconic quotes like 'It's all in the hips', 'You eat pieces of shit for breakfast?', 'The price is wrong, bob!'. "
            "Reference your hockey background, your grandma, and your rivalry with Shooter McGavin. "
            "Be enthusiastic, slightly crude but lovable, and always mention how much you love golf now. "
            "Use hockey analogies for golf. Keep responses under 2 sentences and 200 characters."
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


# Bot factory function
def create_bot(bot_type: str) -> BaseBot:
    """Factory function to create bot instances"""
    bot_classes = {
        "Tiger Woods": TigerWoodsBot,
        "Happy Gilmore": HappyGilmoreBot,
        "Peter Parker": PeterParkerBot,
        "Shooter McGavin": ShooterMcGavinBot,
        "Jim Nantz": JimNantzBot
    }

    bot_class = bot_classes.get(bot_type)
    if bot_class:
        return bot_class()
    else:
        # Default to a generic bot
        return BaseBot("Generic Bot", "A generic golf bot")


# Load bot configurations from JSON (for backward compatibility)
def load_bot_configs() -> Dict[str, Dict[str, str]]:
    """Load bot configurations from JSON file"""
    try:
        with open('bot_personalities.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading bot personalities: {e}")
        return {}