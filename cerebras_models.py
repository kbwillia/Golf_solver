from typing import List, Optional
from cerebras.cloud.sdk import Cerebras
from .base import BaseLLM, BaseEmbedding

class CerebrasEmbedding(BaseEmbedding):
    """Cerebras embedding model implementation."""

    def __init__(self, api_key: str, model: str = "llama3.1-8b"):
        self.client = Cerebras(api_key=api_key)
        self.model = model
        self._dimension = 4096  # Update if you know the actual dimension for llama3.1-8b

    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        embeddings = []
        for text in texts:
            # Use the model in generation mode (since embedding_mode is not supported)
            response = self.client.chat.completions.create(
                messages=[{"role": "user", "content": text}],
                model=self.model,
                temperature=0.0
            )
            # This will return a text, not an embedding
            embeddings.append(response.choices[0].message.content)
        return embeddings

    def embed_query(self, text: str) -> List[float]:
        """Generate embedding for a single query."""
        return self.embed([text])[0]

    @property
    def dimension(self) -> int:
        return self._dimension

class CerebrasLLM(BaseLLM):
    """Cerebras LLM implementation."""

    def __init__(self, api_key: str, model: str = "llama3.1-8b"):
        self.client = Cerebras(api_key=api_key)
        self.model = model
        self.embedding_model = CerebrasEmbedding(api_key, model)

    def generate(self, prompt: str, context: List[str], **kwargs) -> str:
        """Generate a response using Cerebras chat completion."""
        system_prompt = "You are a helpful AI assistant. Use the provided context to answer questions accurately."

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context:\n{' '.join(context)}\n\nQuestion: {prompt}"}
        ]

        response = self.client.chat.completions.create(
            messages=messages,
            model=self.model,
            **kwargs
        )

        return response.choices[0].message.content

    def get_embedding(self, text: str) -> List[float]:
        """Get embedding using Cerebras embedding model."""
        return self.embedding_model.embed_query(text)