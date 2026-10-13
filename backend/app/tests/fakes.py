"""Deterministic stand-ins shared by tests (no Ollama or Vertex needed)."""
from langchain_core.embeddings import Embeddings


class KeywordEmbeddings(Embeddings):
    """Bag-of-keywords vectors: texts sharing more keywords are closer."""

    VOCAB = ["chloroplast", "light", "calvin", "stroma", "mitochondria", "glucose", "oxygen", "enzyme"]

    def _vector(self, text):
        lowered = text.lower()
        return [float(lowered.count(word)) + 0.01 for word in self.VOCAB]

    def embed_documents(self, texts):
        return [self._vector(t) for t in texts]

    def embed_query(self, text):
        return self._vector(text)


def chunk(chunk_id, content):
    return {"chunk_id": chunk_id, "content": content, "start_index": 0, "end_index": len(content),
            "metadata": {"strategy": "test"}}
