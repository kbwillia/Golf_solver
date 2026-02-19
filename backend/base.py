from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class BaseLLM(ABC):
    """Base class for LLM implementations."""

    @abstractmethod
    def generate(self, prompt: str, context: List[str], **kwargs) -> str:
        """Generate a response given a prompt and context."""
        pass

    @abstractmethod
    def get_embedding(self, text: str) -> List[float]:
        """Get embedding vector for a piece of text."""
        pass

class BaseEmbedding(ABC):
    """Base class for embedding implementations."""

    @abstractmethod
    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        pass

    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        """Generate embedding for a single query text."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the dimension of the embedding vectors."""
        pass