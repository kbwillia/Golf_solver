from typing import List, Dict, Any, Optional
import torch
from sentence_transformers import SentenceTransformer
import numpy as np
import requests
import json
import os
from pathlib import Path
import time
import sys

class EmbeddingModel:
    """Class to handle different embedding models for RAG."""

    AVAILABLE_MODELS = {
        # Sentence Transformers Models
        'bge-large': {
            'name': 'BAAI/bge-large-en-v1.5',
            'dimension': 1024,
            'description': 'Best overall performance, 1024d',
            'type': 'sentence-transformers'
        },
        'bge-base': {
            'name': 'BAAI/bge-base-en-v1.5',
            'dimension': 768,
            'description': 'Good balance of performance and efficiency, 768d',
            'type': 'sentence-transformers'
        },
        'e5-large': {
            'name': 'intfloat/e5-large-v2',
            'dimension': 1024,
            'description': 'Strong retrieval performance, 1024d',
            'type': 'sentence-transformers'
        },
        'e5-base': {
            'name': 'intfloat/e5-base-v2',
            'dimension': 768,
            'description': 'Efficient production model, 768d',
            'type': 'sentence-transformers'
        },
        # Ollama Models
        'mxbai-embed-large': {
            'name': 'mxbai-embed-large',
            'dimension': 1024,
            'description': 'Large embedding model, 1024d',
            'type': 'ollama'
        },
        'nomic-embed-text': {
            'name': 'nomic-embed-text',
            'dimension': 768,
            'description': 'Medium embedding model, 768d',
            'type': 'ollama'
        },
        'all-MiniLM-L6-v2': {
            'name': 'all-MiniLM-L6-v2',
            'dimension': 384,
            'description': 'Small embedding model, 384d',
            'type': 'sentence-transformers'
        }
    }

    def __init__(
        self,
        model_name: str = 'bge-large',
        device: str = "cuda" if torch.cuda.is_available() else "cpu",
        base_url: str = "http://localhost:11434",
        cache_dir: str = "embedding_cache"
    ):
        """
        Initialize embedding model.

        Args:
            model_name: Name of the model to use
            device: Device to run model on (for sentence-transformers)
            base_url: Ollama API base URL (for Ollama models)
            cache_dir: Directory to store cached embeddings
        """
        if model_name not in self.AVAILABLE_MODELS:
            raise ValueError(
                f"Model {model_name} not found. Available models: {list(self.AVAILABLE_MODELS.keys())}"
            )

        self.model_info = self.AVAILABLE_MODELS[model_name]
        self.model_type = self.model_info['type']
        self.device = device
        self.base_url = base_url
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_file = self.cache_dir / f"{model_name}_cache.json"
        self.embedding_cache = self._load_cache()

        if self.model_type == 'sentence-transformers':
            self.model = SentenceTransformer(self.model_info['name']).to(device)
            print(f"[EmbeddingModel] Using device: {self.device}")
        else:  # ollama
            self.model = None  # Ollama models are accessed via API
            # print("[EmbeddingModel] Ollama manages device selection internally. To use CUDA, ensure Ollama is running with GPU support (check ollama logs for 'library=cuda').")

        print(f"Initialized {model_name} model:")
        print(f"Type: {self.model_type}")
        print(f"Dimension: {self.model_info['dimension']}") #1024
        # print(f"Description: {self.model_info['description']}") #Large embedding model, 1024d
        print(f"Cache size2: {len(self.embedding_cache)} embeddings") #70 and counting
        #print memory size of the cache
        print(f"Memory size of the cache: {sys.getsizeof(self.embedding_cache)} bytes")

    def _load_cache(self) -> Dict[str, List[float]]:
        """Load cached embeddings from disk."""
        if self.cache_file.exists():
            with open(self.cache_file, 'r') as f:
                cache = json.load(f)
                # print(f"[EmbeddingModel] Cache keys: {list(cache.keys())}")
                #print the first 10 keys
                # print(f"[EmbeddingModel] First 10 cache keys: {list(cache.keys())[:10]}")
                return cache
        print("[EmbeddingModel] No cache found. Creating new cache.")
        return {}

    def _save_cache(self):
        """Save cached embeddings to disk."""
        with open(self.cache_file, 'w') as f:
            json.dump(self.embedding_cache, f)

    def get_embedding(self, text: str) -> np.ndarray:
        # print(f"[EmbeddingModel] Embedding text: {text[:50]}") #works.
        # Check cache first
        if text in self.embedding_cache:
            # print(f"[EmbeddingModel] Cache hit for text: {text[:50]}") #works
            return np.array(self.embedding_cache[text])

        # Generate new embedding
        if self.model_type == 'sentence-transformers':
            embedding = self.model.encode(text, convert_to_tensor=False)
        else:  # ollama
            start = time.time()
            response = requests.post(
                f"{self.base_url}/api/embeddings",
                json={
                    "model": self.model_info['name'],
                    "prompt": text
                }
            )
            print(f"[EmbeddingModel] Ollama embedding request time: {time.time() - start:.3f} seconds")
            response.raise_for_status()
            embedding = np.array(response.json()['embedding'])

        # Cache the result
        self.embedding_cache[text] = embedding.tolist()
        self._save_cache()
        return embedding

    def get_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int = 32,
        show_progress_bar: bool = True
    ) -> np.ndarray:
        """Get embeddings for a batch of texts."""
        # Check cache first
        cached_embeddings = []
        texts_to_compute = []
        indices_to_compute = []

        for i, text in enumerate(texts):
            if text in self.embedding_cache:
                cached_embeddings.append(self.embedding_cache[text])
            else:
                texts_to_compute.append(text)
                indices_to_compute.append(i)

        # Compute embeddings for uncached texts
        if texts_to_compute:
            if self.model_type == 'sentence-transformers':
                new_embeddings = self.model.encode(
                    texts_to_compute,
                    batch_size=batch_size,
                    show_progress_bar=show_progress_bar,
                    convert_to_tensor=False
                )
            else:  # ollama
                new_embeddings = []
                for text in texts_to_compute:
                    embedding = self.get_embedding(text)
                    new_embeddings.append(embedding)
                new_embeddings = np.array(new_embeddings)

            # Cache new embeddings
            for text, embedding in zip(texts_to_compute, new_embeddings):
                self.embedding_cache[text] = embedding.tolist()
            self._save_cache()

            # Combine cached and new embeddings
            all_embeddings = [None] * len(texts)
            for i, idx in enumerate(indices_to_compute):
                all_embeddings[idx] = new_embeddings[i]
            for i, emb in enumerate(cached_embeddings):
                if all_embeddings[i] is None:
                    all_embeddings[i] = emb
            return np.array(all_embeddings)
        else:
            return np.array(cached_embeddings)

    def get_dimension(self) -> int:
        """Get the dimension of the embeddings."""
        return self.model_info['dimension']

    @classmethod
    def list_available_models(cls) -> Dict[str, Dict[str, Any]]:
        """List all available models and their details."""
        return cls.AVAILABLE_MODELS

if __name__ == "__main__":
    print(EmbeddingModel.list_available_models())