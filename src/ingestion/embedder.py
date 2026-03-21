# src/ingestion/embedder.py

from typing import List
from dataclasses import dataclass
import torch
from transformers import AutoTokenizer, AutoModel


@dataclass
class EmbeddingModelConfig:
    model_name: str = "BAAI/bge-small-en-v1.5"
    device: str = "cpu"  # or "mps" for Apple Silicon


class Embedder:
    def __init__(self, config: EmbeddingModelConfig = EmbeddingModelConfig()):
        self.config = config

        print(f"[Embedder] Loading model: {config.model_name}")

        self.tokenizer = AutoTokenizer.from_pretrained(config.model_name)
        self.model = AutoModel.from_pretrained(config.model_name)

        self.model.to(config.device)
        self.model.eval()

    # ------------------------------------------------------------
    # Core embedding function
    # ------------------------------------------------------------
    @torch.no_grad()
    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a list of texts and return a list of vectors.
        """
        encoded = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            return_tensors="pt",
        ).to(self.config.device)

        model_output = self.model(**encoded)

        # Mean pooling
        embeddings = self._mean_pooling(model_output, encoded["attention_mask"])

        # Normalize (recommended for BGE models)
        embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)

        return embeddings.cpu().tolist()

    # ------------------------------------------------------------
    # Mean pooling helper
    # ------------------------------------------------------------
    def _mean_pooling(self, model_output, attention_mask):
        token_embeddings = model_output.last_hidden_state
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        return torch.sum(token_embeddings * input_mask_expanded, dim=1) / torch.clamp(
            input_mask_expanded.sum(dim=1), min=1e-9
        )
