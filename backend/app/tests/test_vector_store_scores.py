import math

from langchain_core.embeddings import Embeddings

from app.services.vector_store import VectorStoreService, chroma_distance_to_relevance

# Deliberately NOT unit length, like Vertex vectors with a reduced output_dimensionality.
VECTORS = {
    "query": [3.0, 0.0, 0.0],
    "near": [2.0, 0.2, 0.0],
    "middle": [1.0, 1.0, 0.0],
    "far": [0.0, 0.0, 5.0],
}


class TableEmbeddings(Embeddings):
    def embed_documents(self, texts):
        return [VECTORS[t] for t in texts]

    def embed_query(self, text):
        return VECTORS[text]


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    return dot / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))


async def test_closer_chunk_gets_higher_relevance_in_unit_range(tmp_path):
    store = VectorStoreService(persist_directory=str(tmp_path / "chroma"), embeddings=TableEmbeddings())
    await store.add_documents(
        texts=["near", "middle", "far"],
        metadatas=[{"file_id": "f", "chunk_id": name} for name in ("near", "middle", "far")],
        ids=["near", "middle", "far"],
    )
    results = await store.search_similar("query", k=3)
    scores = {r["id"]: r["similarity_score"] for r in results}

    assert all(0.0 <= s <= 1.0 for s in scores.values())
    assert scores["near"] > scores["middle"] > scores["far"]
    assert math.isclose(scores["near"], cosine(VECTORS["query"], VECTORS["near"]), abs_tol=1e-4)
    assert math.isclose(scores["far"], 0.0, abs_tol=1e-6)  # orthogonal -> cosine 0


def test_distance_conversion_is_clamped():
    assert chroma_distance_to_relevance(0.0) == 1.0
    assert chroma_distance_to_relevance(4.0) == 0.0   # opposite unit vectors
    assert chroma_distance_to_relevance(-1e-9) == 1.0  # float noise below zero
