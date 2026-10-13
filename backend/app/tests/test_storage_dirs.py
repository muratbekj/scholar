from langchain_core.embeddings import Embeddings

from app.services.document import DocumentService
from app.services.vector_store import VectorStoreService


class ConstantEmbeddings(Embeddings):
    def embed_documents(self, texts):
        return [[1.0, 0.0] for _ in texts]

    def embed_query(self, text):
        return [1.0, 0.0]


def test_nested_chroma_dir_is_created(tmp_path):
    target = tmp_path / "data" / "chroma_vertex"
    VectorStoreService(persist_directory=str(target), embeddings=ConstantEmbeddings())
    assert target.is_dir()


def test_nested_upload_dir_is_created(tmp_path):
    target = tmp_path / "data" / "uploads"
    DocumentService(upload_dir=str(target))
    assert target.is_dir()
