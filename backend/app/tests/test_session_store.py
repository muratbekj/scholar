import os
import uuid
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.core import request_context as rc
from app.models.qa import QAReflectionSubmitRequest, QARequest, RAGContext
from app.models.quiz import QuizRequest, QuizSessionCreate, QuizSubmission
from app.models.study import QAResponseState
from app.services.qa_service import QAService
from app.services.quiz_service import QuizService
from app.services.session_store import MemorySessionStore

A, B = str(uuid.uuid4()), str(uuid.uuid4())
DB_URL = os.environ.get("TEST_DATABASE_URL")


def rag_context():
    return RAGContext(
        relevant_chunks=[
            {"id": "chunk-1", "content": "Machine learning systems improve when they train on labeled examples.",
             "metadata": {"chunk_id": "chunk-1"}},
            {"id": "chunk-2", "content": "Those labeled examples help the model generalize to new tasks.",
             "metadata": {"chunk_id": "chunk-2"}},
        ],
        similarity_scores=[0.91, 0.77],
        source_file="file-1",
        chunk_count=2,
        search_query="Why do labeled examples matter?",
        search_results_count=2,
    )


def qa_with(store):
    service = QAService(document_service=Mock(), use_llm=False, sessions=store)

    async def fake_retrieve(*args, **kwargs):
        return rag_context()

    service._retrieve_rag_context = fake_retrieve
    return service


async def check_pending_reflection_survives_another_instance(store):
    """Ask on one instance, submit the reflection on another (Cloud Run scale-out / restart)."""
    pending = await qa_with(store).ask_question(QARequest(
        question="Explain the relationship between labeled data and model quality.",
        file_id="file-1", filename="notes.pdf"))
    assert pending.response_state == QAResponseState.PENDING_REFLECTION

    answered = await qa_with(store).submit_reflection(QAReflectionSubmitRequest(
        session_id=pending.session_id, pending_question_id=pending.pending_question_id,
        reflection="I think labeled data gives the system a reliable training signal."))
    assert answered.response_state == QAResponseState.ANSWERED

    session = await qa_with(store).get_session(pending.session_id)
    assert session.pending_questions == {}
    assert len(session.messages) >= 3


async def check_quiz_flow_survives_another_instance(store):
    documents = Mock()

    async def text(file_id):
        return "Machine learning models improve as they process more labeled training examples. " * 3

    documents.get_extracted_text = text
    first = QuizService(document_service=documents, use_llm=False, sessions=store)
    second = QuizService(document_service=documents, use_llm=False, sessions=store)
    quiz = await first.generate_quiz(QuizRequest(file_id="f", filename="n.txt", num_questions=2))
    session = await second.create_session(QuizSessionCreate(quiz_id=quiz.quiz_id, file_id="f", filename="n.txt"))
    questions = await first.get_quiz_questions(quiz.quiz_id)
    result = await second.submit_quiz(QuizSubmission(session_id=session.session_id,
                                                     answers={q.id: "x" for q in questions}))
    assert result.quiz_id == quiz.quiz_id
    assert (await first.get_session(session.session_id)).is_completed is True


async def check_sessions_are_scoped_per_client(store):
    rc.bind(A)
    await store.put("qa", "s1", SimpleNamespace(session_id="s1"))
    rc.bind(B)
    assert await store.get("qa", "s1") is None
    assert await store.list("qa") == []
    assert await store.delete("qa", "s1") is False
    rc.bind(A)
    assert (await store.get("qa", "s1")).session_id == "s1"
    assert [s.session_id for s in await store.list("qa")] == ["s1"]
    assert await store.get("quiz", "s1") is None  # kinds are separate
    assert await store.delete("qa", "s1") is True


async def test_memory_store_local_mode(monkeypatch):
    monkeypatch.setattr(rc, "cloud_mode", lambda: False)
    await check_pending_reflection_survives_another_instance(MemorySessionStore())
    await check_quiz_flow_survives_another_instance(MemorySessionStore())


async def test_memory_store_is_scoped_per_client_in_cloud_mode(monkeypatch):
    monkeypatch.setattr(rc, "cloud_mode", lambda: True)
    await check_sessions_are_scoped_per_client(MemorySessionStore())


async def test_memory_store_fails_closed_without_client(monkeypatch):
    monkeypatch.setattr(rc, "cloud_mode", lambda: True)
    rc.bind(None)
    with pytest.raises(rc.IsolationError):
        await MemorySessionStore().list("qa")


@pytest.mark.postgres
@pytest.mark.skipif(not DB_URL, reason="TEST_DATABASE_URL not set")
async def test_postgres_store_round_trips_and_scopes(monkeypatch):
    from app.services.session_store import PostgresSessionStore

    monkeypatch.setattr(rc, "cloud_mode", lambda: True)
    store = PostgresSessionStore(DB_URL)
    rc.bind(str(uuid.uuid4()))
    await check_pending_reflection_survives_another_instance(store)
    await check_quiz_flow_survives_another_instance(store)

    rc.bind(A)
    created = await qa_with(store).create_session(SimpleNamespace(file_id="f", filename="n.txt"))
    rc.bind(B)
    assert await qa_with(store).get_session(created.session_id) is None
    assert await qa_with(store).get_all_sessions() == []
    assert await qa_with(store).delete_session(created.session_id) is False
    rc.bind(A)
    assert [s.session_id for s in await qa_with(store).get_all_sessions()] == [created.session_id]
