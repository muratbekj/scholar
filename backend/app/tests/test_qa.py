import app.services.qa_service as qa_service_mod
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.models.qa import QAReflectionSubmitRequest, QARequest, RAGContext
from app.models.study import QAGenerationMode, QAResponseState, ReflectionState, SupportLevel
from app.services.qa_service import REFLECTION_MIN_WORDS, QAService


@pytest.fixture
def qa_service():
    return QAService(document_service=Mock(), use_llm=False)


@pytest.fixture
def sample_rag_context():
    return RAGContext(
        relevant_chunks=[
            {
                "id": "chunk-1",
                "content": "Machine learning systems improve when they train on labeled examples.",
                "metadata": {"chunk_id": "chunk-1"},
            },
            {
                "id": "chunk-2",
                "content": "Those labeled examples help the model generalize to new tasks.",
                "metadata": {"chunk_id": "chunk-2"},
            },
        ],
        similarity_scores=[0.91, 0.77],
        source_file="file-1",
        chunk_count=2,
        search_query="Why do labeled examples matter?",
        search_results_count=2,
    )


class TestQAService:
    @pytest.mark.asyncio
    async def test_complex_question_requires_reflection(self, qa_service, sample_rag_context):
        async def fake_retrieve(*args, **kwargs):
            return sample_rag_context

        qa_service._retrieve_rag_context = fake_retrieve

        response = await qa_service.ask_question(
            QARequest(
                question="Why do labeled examples matter for model generalization?",
                file_id="file-1",
                filename="notes.pdf",
            )
        )

        assert response.response_state == QAResponseState.PENDING_REFLECTION
        assert response.reflection_state == ReflectionState.REQUIRED
        assert response.pending_question_id is not None
        assert response.visible_cue is not None
        assert response.hidden_evidence_count == 1

    @pytest.mark.asyncio
    async def test_reflection_submission_returns_audited_answer(self, qa_service, sample_rag_context):
        async def fake_retrieve(*args, **kwargs):
            return sample_rag_context

        qa_service._retrieve_rag_context = fake_retrieve

        pending = await qa_service.ask_question(
            QARequest(
                question="Explain the relationship between labeled data and model quality.",
                file_id="file-1",
                filename="notes.pdf",
            )
        )

        response = await qa_service.submit_reflection(
            QAReflectionSubmitRequest(
                session_id=pending.session_id,
                pending_question_id=pending.pending_question_id,
                reflection="I think labeled data gives the system a reliable training signal.",
            )
        )

        assert response.response_state == QAResponseState.ANSWERED
        assert response.reflection_state == ReflectionState.SUBMITTED
        assert response.intuition_text == "I think labeled data gives the system a reliable training signal."
        assert response.answer_segments
        assert response.audit_summary is not None
        assert response.visible_evidence_refs
        assert response.audit_summary.source_links is not None

    @pytest.mark.asyncio
    async def test_reflection_too_short_rejected(self, qa_service, sample_rag_context):
        async def fake_retrieve(*args, **kwargs):
            return sample_rag_context

        qa_service._retrieve_rag_context = fake_retrieve

        pending = await qa_service.ask_question(
            QARequest(
                question="Explain the relationship between labeled data and model quality.",
                file_id="file-1",
                filename="notes.pdf",
            )
        )
        assert pending.response_state == QAResponseState.PENDING_REFLECTION

        with pytest.raises(ValueError, match="too short"):
            await qa_service.submit_reflection(
                QAReflectionSubmitRequest(
                    session_id=pending.session_id,
                    pending_question_id=pending.pending_question_id,
                    reflection="labels help models learn",
                )
            )

    @pytest.mark.asyncio
    async def test_reflection_disconnected_rejected(self, qa_service, sample_rag_context):
        async def fake_retrieve(*args, **kwargs):
            return sample_rag_context

        qa_service._retrieve_rag_context = fake_retrieve

        pending = await qa_service.ask_question(
            QARequest(
                question="Explain the relationship between labeled data and model quality.",
                file_id="file-1",
                filename="notes.pdf",
            )
        )
        rambling = "completely unrelated musings about weather and breakfast and walking the dog daily"
        assert len(rambling.split()) >= REFLECTION_MIN_WORDS
        with pytest.raises(ValueError, match="does not connect"):
            await qa_service.submit_reflection(
                QAReflectionSubmitRequest(
                    session_id=pending.session_id,
                    pending_question_id=pending.pending_question_id,
                    reflection=rambling,
                )
            )

    @pytest.mark.asyncio
    async def test_low_complexity_question_bypasses_reflection(self, qa_service, sample_rag_context):
        async def fake_retrieve(*args, **kwargs):
            return sample_rag_context

        qa_service._retrieve_rag_context = fake_retrieve

        response = await qa_service.ask_question(
            QARequest(
                question="What are labeled examples?",
                file_id="file-1",
                filename="notes.pdf",
            )
        )

        assert response.response_state == QAResponseState.ANSWERED
        assert response.reflection_state == ReflectionState.BYPASSED
        assert response.answer_segments

    @pytest.mark.asyncio
    async def test_reasoning_gap_mode_returns_structured_gap_steps(self, qa_service, sample_rag_context):
        async def fake_retrieve(*args, **kwargs):
            return sample_rag_context

        qa_service._retrieve_rag_context = fake_retrieve

        response = await qa_service.ask_question(
            QARequest(
                question="What reasoning connects labeled examples to generalization?",
                file_id="file-1",
                filename="notes.pdf",
                generation_mode=QAGenerationMode.REASONING_GAP,
            )
        )

        assert response.response_state == QAResponseState.PENDING_REFLECTION
        assert response.generation_mode == QAGenerationMode.REASONING_GAP

        completed = await qa_service.submit_reflection(
            QAReflectionSubmitRequest(
                session_id=response.session_id,
                pending_question_id=response.pending_question_id,
                reflection="The labels seem to show the model what pattern matters.",
            )
        )

        assert completed.generation_mode == QAGenerationMode.REASONING_GAP
        assert completed.gap_steps
        assert completed.gap_steps[0].expected_concept is not None
        assert completed.answer.startswith("Learner reflection:")

    @pytest.mark.asyncio
    async def test_audited_segments_include_heatmap_fields(self, qa_service, sample_rag_context):
        async def fake_retrieve(*args, **kwargs):
            return sample_rag_context

        qa_service._retrieve_rag_context = fake_retrieve

        completed = await qa_service.ask_question(
            QARequest(
                question="What are labeled examples?",
                file_id="file-1",
                filename="notes.pdf",
            )
        )
        assert completed.answer_segments
        for seg in completed.answer_segments:
            assert seg.support_label_ui is not None
            assert seg.source_match_percent is not None
            assert 0 <= seg.source_match_percent <= 100

    @pytest.mark.asyncio
    async def test_critic_pass_can_override_heuristic(self, qa_service, sample_rag_context):
        qa_service.use_llm = True
        answer = "Labeled data improves generalization. The moon is made of cheese."

        with patch.object(
            qa_service_mod.llm_service,
            "audit_sentence_support_levels",
            new_callable=AsyncMock,
        ) as mock_critic:
            mock_critic.return_value = ["grounded", "weak_support"]
            segments = await qa_service._finalize_audited_segments(
                answer, sample_rag_context, "learner: prior question"
            )

        assert len(segments) == 2
        assert segments[0].support_level == SupportLevel.GROUNDED
        assert segments[1].support_level == SupportLevel.WEAK_SUPPORT
        mock_critic.assert_awaited_once()
