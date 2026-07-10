import numpy as np

from .llm_client import embed


class LocalVectorStore:
    """In-memory cosine-similarity vector store.

    Same add()/query() interface Pinecone would need, so swapping in a real
    Pinecone index later (upsert/query) only touches this file.
    """

    def __init__(self):
        self._vectors: np.ndarray | None = None
        self._metadatas: list[dict] = []

    def add(self, texts: list[str], metadatas: list[dict]) -> None:
        vecs = np.array(embed(texts), dtype=np.float32)
        vecs /= np.linalg.norm(vecs, axis=1, keepdims=True)
        self._vectors = vecs if self._vectors is None else np.vstack([self._vectors, vecs])
        self._metadatas.extend(metadatas)

    def query(self, text: str, top_k: int = 3) -> list[dict]:
        if self._vectors is None or len(self._metadatas) == 0:
            return []
        qvec = np.array(embed([text])[0], dtype=np.float32)
        qvec /= np.linalg.norm(qvec)
        scores = self._vectors @ qvec
        top_idx = np.argsort(-scores)[:top_k]
        return [
            {**self._metadatas[i], "score": float(scores[i])}
            for i in top_idx
        ]
