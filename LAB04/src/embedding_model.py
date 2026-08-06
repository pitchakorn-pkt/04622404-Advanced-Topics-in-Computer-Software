





from sentence_transformers import SentenceTransformer

import config
from src.thai_text import normalize_text


class EmbeddingModel:
    def __init__(self):
        print(f"[embedding] Loading {config.EMBEDDING_MODEL_NAME}...")
        self.model = SentenceTransformer(config.EMBEDDING_MODEL_NAME)

    def encode(self, texts):
        texts = [normalize_text(text) for text in texts]

        return self.model.encode(
            texts,
            show_progress_bar=True,
            normalize_embeddings=True,
        )

    def encode_query(self, query):   #Convert a single query into an embedding vector
        return self.model.encode([normalize_text(query)], normalize_embeddings=True)[0]
