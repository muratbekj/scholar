from app.api.routes import files
from app.services import (
    document,
    embedding,
    flashcard_service,
    qa_service,
    quiz_service,
    rag_pipeline,
    vector_store,
)


def test_every_consumer_shares_one_document_service():
    shared = document.document_service
    assert qa_service.qa_service.document_service is shared
    assert quiz_service.quiz_service.document_service is shared
    assert flashcard_service.flashcard_service.document_service is shared
    assert rag_pipeline.rag_pipeline_service.document_service is shared
    assert files.document_service is shared


def test_pipeline_shares_embedding_and_vector_store_singletons():
    pipeline = rag_pipeline.rag_pipeline_service
    assert pipeline.embedding_service is embedding.embedding_service
    assert pipeline.vector_store_service is vector_store.vector_store_service


def test_explicit_dependencies_still_win():
    sentinel = object()
    assert qa_service.QAService(document_service=sentinel, use_llm=False).document_service is sentinel
