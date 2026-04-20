# QA service for handling question-answer sessions with RAG integration
from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ..models.qa import (
    PendingQAExchange,
    QAMessage,
    QAReflectionSubmitRequest,
    QARequest,
    QAResponse,
    QASession,
    QASessionCreate,
    QASessionResponse,
    RAGContext,
)
from ..models.study import (
    AuditSummary,
    AnswerSegment,
    EvidenceRef,
    GapStep,
    QAGenerationMode,
    QAResponseState,
    ReflectionState,
    SourceLink,
    SupportLevel,
)
from .document import DocumentService
from .llm_service import llm_service
from .rag_pipeline import rag_pipeline_service

logger = logging.getLogger(__name__)

# Minimum substantive reflection before unlocking the full answer (reflective gate).
REFLECTION_MIN_WORDS = 8

# Excluded from overlap checks (too easy to fake a "connection").
_REFLECTION_OVERLAP_STOPWORDS = frozenset(
    {
        "what",
        "that",
        "this",
        "from",
        "with",
        "have",
        "your",
        "they",
        "when",
        "where",
        "which",
        "there",
        "their",
        "would",
        "could",
        "about",
        "into",
        "more",
        "than",
        "then",
        "some",
        "such",
        "very",
        "will",
        "been",
        "were",
        "also",
        "only",
        "other",
        "each",
        "both",
        "many",
        "much",
        "like",
        "just",
        "even",
        "does",
        "seem",
        "seems",
    }
)


class QAService:
    """Service for handling QA sessions with reflection-gated RAG integration."""

    def __init__(self, document_service: DocumentService = None, use_llm: bool = True):
        self.document_service = document_service or DocumentService()
        self.active_sessions: Dict[str, QASession] = {}
        self.use_llm = use_llm
        self.reflection_min_words = REFLECTION_MIN_WORDS
        logger.info("Initialized QA Service with reflection-aware RAG integration")

    async def create_session(self, session_data: QASessionCreate) -> QASessionResponse:
        """Create a new QA session."""
        session_id = str(uuid.uuid4())
        session = QASession(
            session_id=session_id,
            file_id=session_data.file_id,
            filename=session_data.filename,
            created_at=datetime.now(),
        )
        self.active_sessions[session_id] = session
        logger.info("Created QA session %s for file %s", session_id, session_data.filename)
        return self._build_session_response(session)

    async def ask_question(self, request: QARequest) -> QAResponse:
        """Ask a question and either return a pending reflection step or the final audited answer."""
        start_time = datetime.now()

        try:
            session = await self._get_or_create_session(request)
            user_message = QAMessage(
                id=str(uuid.uuid4()),
                type="user",
                content=request.question,
                timestamp=datetime.now(),
            )
            session.messages.append(user_message)
            session.total_messages += 1

            complexity_score = self._classify_question_complexity(request.question)
            rag_context = await self._retrieve_rag_context(
                question=request.question,
                file_id=session.file_id,
                use_rag=request.use_rag,
                search_k=request.search_k,
            )
            recent_history_summary = self._summarize_recent_turns(session.messages[:-1])

            if self._should_require_reflection(complexity_score, rag_context, request.generation_mode):
                response = await self._build_pending_response(
                    session=session,
                    question=request.question,
                    complexity_score=complexity_score,
                    rag_context=rag_context,
                    generation_mode=request.generation_mode,
                    recent_history_summary=recent_history_summary,
                    processing_time=(datetime.now() - start_time).total_seconds(),
                )
                logger.info(
                    "Question gated for reflection in session %s with pending id %s",
                    session.session_id,
                    response.pending_question_id,
                )
                return response

            return await self._finalize_answer(
                session=session,
                question=request.question,
                rag_context=rag_context,
                reflection=None,
                complexity_score=complexity_score,
                reflection_state=ReflectionState.BYPASSED,
                pending_question_id=None,
                generation_mode=request.generation_mode,
                recent_history_summary=recent_history_summary,
                processing_time=(datetime.now() - start_time).total_seconds(),
            )
        except Exception as exc:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.error("Error generating answer: %s", exc)
            return QAResponse(
                answer=f"I'm sorry, I encountered an error while processing your question: {exc}",
                session_id=request.session_id or "error",
                message_id=str(uuid.uuid4()),
                timestamp=datetime.now(),
                processing_time=processing_time,
                confidence_score=0.0,
                response_state=QAResponseState.ANSWERED,
                reflection_state=ReflectionState.BYPASSED,
            )

    async def submit_reflection(self, request: QAReflectionSubmitRequest) -> QAResponse:
        """Submit the reflection step for a pending answer."""
        start_time = datetime.now()
        session = await self.get_session(request.session_id)
        if not session:
            raise ValueError("Session not found")

        pending_exchange = self._resolve_pending_exchange(session, request.pending_question_id)
        if not pending_exchange:
            raise ValueError("No matching pending reflection step exists")

        self._validate_reflection_for_gate(
            request.reflection,
            pending_exchange.question,
            pending_exchange.visible_cue,
            pending_exchange.rag_context,
        )

        reflection_message = QAMessage(
            id=str(uuid.uuid4()),
            type="user",
            content=request.reflection,
            timestamp=datetime.now(),
            metadata={
                "role": "reflection",
                "pending_question_id": pending_exchange.pending_question_id,
            },
        )
        session.messages.append(reflection_message)
        session.total_messages += 1

        response = await self._finalize_answer(
            session=session,
            question=pending_exchange.question,
            rag_context=pending_exchange.rag_context,
            reflection=request.reflection,
            complexity_score=pending_exchange.complexity_score,
            reflection_state=ReflectionState.SUBMITTED,
            pending_question_id=pending_exchange.pending_question_id,
            generation_mode=pending_exchange.generation_mode,
            recent_history_summary=self._summarize_recent_turns(session.messages[:-1]),
            processing_time=(datetime.now() - start_time).total_seconds(),
            visible_cue=pending_exchange.visible_cue,
        )

        session.pending_questions.pop(pending_exchange.pending_question_id, None)
        return response

    async def _get_or_create_session(self, request: QARequest) -> QASession:
        if request.session_id and request.session_id in self.active_sessions:
            return self.active_sessions[request.session_id]

        if not request.file_id:
            raise ValueError("File ID is required for new sessions")

        filename = request.filename or f"file_{request.file_id}"
        session_response = await self.create_session(
            QASessionCreate(file_id=request.file_id, filename=filename)
        )
        return self.active_sessions[session_response.session_id]

    async def _retrieve_rag_context(
        self,
        question: str,
        file_id: str,
        use_rag: bool,
        search_k: int,
    ) -> Optional[RAGContext]:
        if not use_rag:
            return None

        try:
            search_result = await rag_pipeline_service.search_documents(
                query=question,
                k=search_k,
                file_id=file_id,
            )
            if not search_result.get("success") or not search_result.get("results"):
                return None

            relevant_chunks: List[Dict[str, Any]] = []
            similarity_scores: List[float] = []
            for result in search_result["results"]:
                metadata = dict(result.get("metadata") or {})
                relevant_chunks.append(
                    {
                        "content": result["content"],
                        "metadata": metadata,
                        "id": result.get("id") or metadata.get("chunk_id"),
                    }
                )
                similarity_scores.append(float(result.get("similarity_score", 0.0)))

            return RAGContext(
                relevant_chunks=relevant_chunks,
                similarity_scores=similarity_scores,
                source_file=file_id,
                chunk_count=len(relevant_chunks),
                search_query=question,
                search_results_count=len(search_result["results"]),
            )
        except Exception as exc:
            logger.error("Error in RAG retrieval: %s", exc)
            return None

    def _classify_question_complexity(self, question: str) -> int:
        score = 1
        normalized = question.lower()
        word_count = len(re.findall(r"\w+", normalized))

        if word_count >= 8:
            score += 1
        if word_count >= 16:
            score += 1

        complex_markers = [
            "why",
            "how",
            "tradeoff",
            "compare",
            "contrast",
            "analyze",
            "explain",
            "implication",
            "relationship",
            "evaluate",
        ]
        if any(marker in normalized for marker in complex_markers):
            score += 1
        if " and " in normalized or " versus " in normalized or " vs " in normalized:
            score += 1

        return max(1, min(score, 5))

    def _should_require_reflection(
        self,
        complexity_score: int,
        rag_context: Optional[RAGContext],
        generation_mode: QAGenerationMode,
    ) -> bool:
        if generation_mode == QAGenerationMode.REASONING_GAP:
            return rag_context is not None and rag_context.chunk_count > 0
        return complexity_score >= 3 and rag_context is not None and rag_context.chunk_count > 0

    def _validate_reflection_for_gate(
        self,
        reflection: str,
        question: str,
        visible_cue: Optional[str],
        rag_context: RAGContext,
    ) -> None:
        """Reject empty, too-short, or disconnected 'intuition' so the gate cannot be bypassed."""
        text = (reflection or "").strip()
        if not text:
            raise ValueError("Reflection cannot be empty.")
        words = text.split()
        if len(words) < self.reflection_min_words:
            raise ValueError(
                f"Reflection is too short: write at least {self.reflection_min_words} words "
                "that connect your thinking to the cue or question."
            )
        first_chunk = ""
        if rag_context.relevant_chunks:
            first_chunk = str(rag_context.relevant_chunks[0].get("content") or "")[:500]
        anchor_tokens = (
            self._tokenize(question)
            | self._tokenize(visible_cue or "")
            | self._tokenize(first_chunk)
        )
        ref_tokens = self._tokenize(text)
        anchor_meaningful = {t for t in anchor_tokens if t not in _REFLECTION_OVERLAP_STOPWORDS}
        ref_meaningful = {t for t in ref_tokens if t not in _REFLECTION_OVERLAP_STOPWORDS}
        overlap = len(ref_meaningful & anchor_meaningful)
        stem_overlap = self._reflection_stem_overlap(ref_meaningful, anchor_meaningful)
        effective = max(overlap, stem_overlap)
        if effective >= 2:
            return
        if len(words) >= 10 and effective >= 1:
            return
        raise ValueError(
            "Reflection does not connect clearly to the document cue or question. "
            "Mention specific ideas from the cue or explain how you interpret the passage."
        )

    def _reflection_stem_overlap(self, ref_toks: set[str], anchor_toks: set[str]) -> int:
        """Count loose matches (e.g. labels ↔ labeled) so learners aren't punished for inflections."""
        extra = 0
        for r in ref_toks:
            if len(r) < 5:
                continue
            prefix = r[:5]
            for a in anchor_toks:
                if len(a) < 5:
                    continue
                if a.startswith(prefix) or r.startswith(a[:5]):
                    extra += 1
                    break
        return extra

    async def _resolve_visible_cue(self, question: str, rag_context: RAGContext) -> str:
        """Cue shown before reflection: prefer non-leaking LLM excerpt; else verbatim window."""
        if not rag_context.relevant_chunks:
            return ""
        passage = str(rag_context.relevant_chunks[0].get("content") or "").strip()
        if not passage:
            return ""
        if self.use_llm:
            try:
                cue = await llm_service.generate_reflection_cue(question, passage)
                if cue.strip():
                    return cue.strip()[:400]
            except Exception as exc:
                logger.warning("LLM reflection cue failed, using heuristic fallback: %s", exc)
        return self._reflection_cue_heuristic_fallback(passage)

    def _reflection_cue_heuristic_fallback(self, passage: str) -> str:
        """Non-LLM: verbatim slice only (no summarization); may still leak—enable LLM for stronger gates."""
        flat = " ".join(passage.split())
        if len(flat) <= 200:
            return flat
        return flat[:200].rsplit(" ", 1)[0] + "…"

    async def _build_pending_response(
        self,
        session: QASession,
        question: str,
        complexity_score: int,
        rag_context: RAGContext,
        generation_mode: QAGenerationMode,
        recent_history_summary: Optional[str],
        processing_time: float,
    ) -> QAResponse:
        pending_question_id = str(uuid.uuid4())
        visible_cue = await self._resolve_visible_cue(question, rag_context)
        reflection_prompt = self._build_reflection_prompt(question, visible_cue)
        visible_evidence_refs = self._build_evidence_refs(
            rag_context.relevant_chunks[:1],
            rag_context.similarity_scores[:1],
            rag_context.source_file,
        )
        hidden_evidence_count = max(rag_context.chunk_count - len(visible_evidence_refs), 0)

        pending_exchange = PendingQAExchange(
            pending_question_id=pending_question_id,
            question=question,
            created_at=datetime.now(),
            complexity_score=complexity_score,
            reflection_prompt=reflection_prompt,
            visible_cue=visible_cue,
            hidden_evidence_count=hidden_evidence_count,
            visible_evidence_refs=visible_evidence_refs,
            rag_context=rag_context,
            generation_mode=generation_mode,
        )
        session.pending_questions[pending_question_id] = pending_exchange

        assistant_message = QAMessage(
            id=str(uuid.uuid4()),
            type="assistant",
            content=reflection_prompt,
            timestamp=datetime.now(),
            metadata={
                "response_state": QAResponseState.PENDING_REFLECTION.value,
                "reflection_state": ReflectionState.REQUIRED.value,
                "pending_question_id": pending_question_id,
                "generation_mode": generation_mode.value,
                "visible_cue": visible_cue,
                "hidden_evidence_count": hidden_evidence_count,
                "visible_evidence_refs": [ref.model_dump() for ref in visible_evidence_refs],
                "rag_context": rag_context.model_dump(),
            },
        )
        session.messages.append(assistant_message)
        session.total_messages += 1
        session.session_duration = (datetime.now() - session.created_at).total_seconds()

        return QAResponse(
            answer=reflection_prompt,
            session_id=session.session_id,
            message_id=assistant_message.id,
            timestamp=assistant_message.timestamp,
            rag_context=rag_context,
            processing_time=processing_time,
            confidence_score=self._calculate_confidence_score(rag_context),
            response_state=QAResponseState.PENDING_REFLECTION,
            reflection_state=ReflectionState.REQUIRED,
            reflection_prompt=reflection_prompt,
            visible_cue=visible_cue,
            hidden_evidence_count=hidden_evidence_count,
            pending_question_id=pending_question_id,
            visible_evidence_refs=visible_evidence_refs,
            complexity_score=complexity_score,
            recent_history_summary=recent_history_summary,
            generation_mode=generation_mode,
        )

    async def _finalize_answer(
        self,
        session: QASession,
        question: str,
        rag_context: Optional[RAGContext],
        reflection: Optional[str],
        complexity_score: int,
        reflection_state: ReflectionState,
        pending_question_id: Optional[str],
        generation_mode: QAGenerationMode,
        recent_history_summary: Optional[str],
        processing_time: float,
        visible_cue: Optional[str] = None,
    ) -> QAResponse:
        answer, gap_steps = await self._generate_answer_payload(
            question=question,
            rag_context=rag_context,
            reflection=reflection,
            generation_mode=generation_mode,
            recent_history_summary=recent_history_summary,
        )
        answer_segments = await self._finalize_audited_segments(
            answer, rag_context, recent_history_summary
        )
        audit_summary = self._build_audit_summary(answer_segments, recent_history_summary)
        visible_evidence_refs = self._build_evidence_refs(
            rag_context.relevant_chunks if rag_context else [],
            rag_context.similarity_scores if rag_context else [],
            rag_context.source_file if rag_context else session.file_id,
        )

        intuition_text = (
            reflection.strip()
            if reflection and reflection_state == ReflectionState.SUBMITTED
            else None
        )

        assistant_message = QAMessage(
            id=str(uuid.uuid4()),
            type="assistant",
            content=answer,
            timestamp=datetime.now(),
            metadata={
                "response_state": QAResponseState.ANSWERED.value,
                "reflection_state": reflection_state.value,
                "pending_question_id": pending_question_id,
                "intuition_text": intuition_text,
                "answer_segments": [segment.model_dump() for segment in answer_segments],
                "audit_summary": audit_summary.model_dump(),
                "visible_cue": visible_cue,
                "visible_evidence_refs": [ref.model_dump() for ref in visible_evidence_refs],
                "rag_context": rag_context.model_dump() if rag_context else None,
                "generation_mode": generation_mode.value,
                "gap_steps": [step.model_dump() for step in gap_steps],
            },
        )
        session.messages.append(assistant_message)
        session.total_messages += 1
        session.session_duration = (datetime.now() - session.created_at).total_seconds()

        return QAResponse(
            answer=answer,
            session_id=session.session_id,
            message_id=assistant_message.id,
            timestamp=assistant_message.timestamp,
            rag_context=rag_context,
            processing_time=processing_time,
            confidence_score=self._calculate_confidence_score(rag_context),
            response_state=QAResponseState.ANSWERED,
            reflection_state=reflection_state,
            reflection_prompt=None,
            visible_cue=visible_cue,
            hidden_evidence_count=0,
            pending_question_id=pending_question_id,
            answer_segments=answer_segments,
            audit_summary=audit_summary,
            visible_evidence_refs=visible_evidence_refs,
            complexity_score=complexity_score,
            recent_history_summary=recent_history_summary,
            generation_mode=generation_mode,
            gap_steps=gap_steps,
            intuition_text=intuition_text,
        )

    async def _generate_answer_payload(
        self,
        question: str,
        rag_context: Optional[RAGContext],
        reflection: Optional[str],
        generation_mode: QAGenerationMode,
        recent_history_summary: Optional[str],
    ) -> Tuple[str, List[GapStep]]:
        if not rag_context or not rag_context.relevant_chunks:
            return self._generate_generic_answer(question), []

        if generation_mode == QAGenerationMode.REASONING_GAP:
            gap_steps = self._build_gap_steps_from_chunks(rag_context)
            return self._render_gap_answer(question, reflection, gap_steps), gap_steps

        context = "\n\n".join(chunk["content"] for chunk in rag_context.relevant_chunks)
        if not self.use_llm:
            cue = self._extract_cue_sentence(rag_context.relevant_chunks[0]["content"])
            reflection_note = f"Learner reflection: {reflection}\n\n" if reflection else ""
            return (
                f"{reflection_note}Based on the document, the strongest cue is: {cue}\n\n"
                f"This answer draws on {rag_context.chunk_count} relevant sections related to "
                f"the question: \"{question}\"."
            ), []

        system_prompt = (
            "You are a study assistant answering from retrieved document evidence.\n"
            "Use only the supplied context.\n"
            "Keep the answer concise and clear.\n"
            "If learner reflection is present, compare it to the evidence and refine it.\n"
            "If recent conversation context is present, keep the answer consistent with confirmed facts only.\n\n"
            f"Recent history summary: {recent_history_summary or 'None'}\n"
            f"Learner reflection: {reflection or 'None'}\n\n"
            f"Context:\n{context}\n\nQuestion: {question}\n\nAnswer:"
        )
        return await llm_service.generate_answer(question, context, system_prompt=system_prompt), []

    async def _finalize_audited_segments(
        self,
        answer: str,
        rag_context: Optional[RAGContext],
        recent_history_summary: Optional[str],
    ) -> List[AnswerSegment]:
        """Heuristic alignment + optional LLM critic pass; then UI percent / labels."""
        segments = self._heuristic_answer_segments(answer, rag_context, recent_history_summary)
        if not segments:
            return []

        if not self.use_llm or not rag_context or not rag_context.relevant_chunks:
            return self._annotate_segments(segments)

        context = "\n\n".join(chunk["content"] for chunk in rag_context.relevant_chunks[:6])
        sentences = [seg.text for seg in segments]
        try:
            levels_raw = await llm_service.audit_sentence_support_levels(
                sentences=sentences,
                evidence_context=context,
                recent_history_summary=recent_history_summary,
            )
        except Exception as exc:
            logger.warning("Critic audit skipped: %s", exc)
            levels_raw = None

        if not levels_raw or len(levels_raw) != len(segments):
            return self._annotate_segments(segments)

        merged: List[AnswerSegment] = []
        for index, (segment, raw) in enumerate(zip(segments, levels_raw)):
            heuristic_level = segment.support_level
            level = self._coerce_support_level(raw)
            if heuristic_level != level:
                logger.info(
                    "critic_heuristic_disagreement index=%s heuristic=%s critic=%s sentence=%r",
                    index,
                    heuristic_level.value,
                    level.value,
                    segment.text[:120],
                )
            merged.append(
                segment.model_copy(
                    update={
                        "support_level": level,
                        "support_tier": self._support_tier_label(level),
                    }
                )
            )
        return self._annotate_segments(merged)

    def _coerce_support_level(self, raw: str) -> SupportLevel:
        label = str(raw).lower().strip().replace(" ", "_").replace("-", "_")
        if label == "grounded":
            return SupportLevel.GROUNDED
        if label == "inferred":
            return SupportLevel.INFERRED
        if label in (
            "statistical_shortcut",
            "training_shortcut",
            "shortcut",
            "hallucination",
            "ungrounded",
        ):
            return SupportLevel.WEAK_SUPPORT
        return SupportLevel.WEAK_SUPPORT

    def _annotate_segments(self, segments: List[AnswerSegment]) -> List[AnswerSegment]:
        annotated: List[AnswerSegment] = []
        for segment in segments:
            best_sim = segment.evidence_refs[0].score if segment.evidence_refs else None
            annotated.append(
                segment.model_copy(
                    update={
                        "support_label_ui": self._ui_support_label(segment.support_level),
                        "source_match_percent": self._source_match_percent(
                            segment.support_level, best_sim
                        ),
                    }
                )
            )
        return annotated

    def _ui_support_label(self, support_level: SupportLevel) -> str:
        return {
            SupportLevel.GROUNDED: "Direct citation",
            SupportLevel.INFERRED: "Logical inference",
            SupportLevel.WEAK_SUPPORT: "Weakly supported (possible filler)",
        }[support_level]

    def _source_match_percent(
        self, support_level: SupportLevel, best_similarity: Optional[float]
    ) -> int:
        """Composite 0–100 for heatmap hover; tier + retrieval, not calibrated probability."""
        sim = max(0.0, min(1.0, best_similarity if best_similarity is not None else 0.0))
        anchors = {
            SupportLevel.GROUNDED: 0.82,
            SupportLevel.INFERRED: 0.52,
            SupportLevel.WEAK_SUPPORT: 0.18,
        }
        blended = anchors[support_level] * 0.62 + sim * 0.38
        return int(round(100 * min(1.0, blended)))

    def _heuristic_answer_segments(
        self,
        answer: str,
        rag_context: Optional[RAGContext],
        recent_history_summary: Optional[str],
    ) -> List[AnswerSegment]:
        sentences = [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])\s+", answer.strip())
            if sentence.strip()
        ]
        if not sentences:
            sentences = [answer.strip()] if answer.strip() else []

        if not sentences:
            return []

        if not rag_context or not rag_context.relevant_chunks:
            return [
                AnswerSegment(
                    text=sentence,
                    support_level=SupportLevel.WEAK_SUPPORT,
                    support_tier=self._support_tier_label(SupportLevel.WEAK_SUPPORT),
                    evidence_refs=[],
                )
                for sentence in sentences
            ]

        history_tokens = self._tokenize(recent_history_summary or "")
        segments: List[AnswerSegment] = []
        for sentence in sentences:
            sentence_tokens = self._tokenize(sentence)
            best_score = 0.0
            best_chunk: Optional[Dict[str, Any]] = None
            best_similarity = 0.0

            for index, chunk in enumerate(rag_context.relevant_chunks):
                chunk_score = self._overlap_score(sentence_tokens, self._tokenize(chunk["content"]))
                similarity = rag_context.similarity_scores[index] if index < len(rag_context.similarity_scores) else 0.0
                combined_score = max(chunk_score, similarity * 0.5)
                if sentence.lower() in chunk["content"].lower():
                    combined_score = max(combined_score, 0.95)
                if combined_score > best_score:
                    best_score = combined_score
                    best_chunk = chunk
                    best_similarity = similarity

            if best_chunk and best_score >= 0.28:
                support_level = SupportLevel.GROUNDED
            elif best_chunk and (best_score >= 0.12 or (sentence_tokens & history_tokens)):
                support_level = SupportLevel.INFERRED
            elif sentence_tokens & history_tokens:
                support_level = SupportLevel.INFERRED
            else:
                support_level = SupportLevel.WEAK_SUPPORT

            evidence_refs = []
            if best_chunk:
                evidence_refs = [
                    self._make_evidence_ref(
                        chunk=best_chunk,
                        source_file=rag_context.source_file,
                        similarity_score=best_similarity,
                    )
                ]

            segments.append(
                AnswerSegment(
                    text=sentence,
                    support_level=support_level,
                    support_tier=self._support_tier_label(support_level),
                    evidence_refs=evidence_refs,
                )
            )

        return segments

    def _build_audit_summary(
        self,
        segments: List[AnswerSegment],
        recent_history_summary: Optional[str],
    ) -> AuditSummary:
        grounded_segments = sum(1 for segment in segments if segment.support_level == SupportLevel.GROUNDED)
        inferred_segments = sum(1 for segment in segments if segment.support_level == SupportLevel.INFERRED)
        weak_support_segments = sum(
            1 for segment in segments if segment.support_level == SupportLevel.WEAK_SUPPORT
        )

        summary = (
            f"{grounded_segments} grounded, {inferred_segments} inferred, "
            f"{weak_support_segments} weak-support segment(s)."
        )
        if weak_support_segments:
            summary += " Review the weak-support segments against the evidence."

        return AuditSummary(
            summary=summary,
            grounded_segments=grounded_segments,
            inferred_segments=inferred_segments,
            weak_support_segments=weak_support_segments,
            recent_history_summary=recent_history_summary,
            source_links=self._source_links_for_grounded(segments),
        )

    def _source_links_for_grounded(self, segments: List[AnswerSegment]) -> List[SourceLink]:
        """Tie grounded segments to evidence for verification (client can map page → PDF)."""
        seen: set[tuple] = set()
        links: List[SourceLink] = []
        for idx, segment in enumerate(segments):
            if segment.support_level != SupportLevel.GROUNDED:
                continue
            for ref in segment.evidence_refs[:1]:
                excerpt = (ref.excerpt or "").strip()
                key = (ref.chunk_id, ref.page_number, excerpt[:100])
                if key in seen or not (excerpt or ref.page_number or ref.chunk_id):
                    continue
                seen.add(key)
                links.append(
                    SourceLink(
                        excerpt=excerpt[:600],
                        page_number=ref.page_number,
                        chunk_id=ref.chunk_id,
                        source_file=ref.source_file,
                        segment_index=idx,
                        support_level="grounded",
                    )
                )
        return links[:16]

    def _build_reflection_prompt(self, question: str, visible_cue: Optional[str]) -> str:
        if visible_cue:
            return (
                "Before I reveal the full answer, write a short intuition in your own words.\n\n"
                "The cue below is only a relevant excerpt from your document—it is not a summary "
                "of the answer, and it may omit resolving facts on purpose.\n\n"
                f"Cue (excerpt): {visible_cue}\n\nQuestion: {question}"
            )
        return (
            "Before I reveal the full answer, write 1-2 sentences about what you think the "
            f"document supports for this question:\n\n{question}"
        )

    def _extract_cue_sentence(self, content: str) -> str:
        sentences = re.split(r"(?<=[.!?])\s+", content.strip())
        cue = sentences[0].strip() if sentences and sentences[0].strip() else content.strip()
        return cue[:220]

    def _make_evidence_ref(
        self,
        chunk: Dict[str, Any],
        source_file: str,
        similarity_score: float = 0.0,
    ) -> EvidenceRef:
        metadata = chunk.get("metadata") or {}
        return EvidenceRef(
            chunk_id=chunk.get("id") or metadata.get("chunk_id"),
            excerpt=chunk.get("content", "")[:220],
            source_file=source_file,
            start_index=metadata.get("start_index"),
            end_index=metadata.get("end_index"),
            page_number=metadata.get("page") or metadata.get("page_number"),
            score=similarity_score,
            label=metadata.get("strategy"),
            support_tier=self._score_band(similarity_score),
            score_band=self._score_band(similarity_score),
        )

    def _build_evidence_refs(
        self,
        relevant_chunks: List[Dict[str, Any]],
        similarity_scores: List[float],
        source_file: str,
    ) -> List[EvidenceRef]:
        evidence_refs: List[EvidenceRef] = []
        for index, chunk in enumerate(relevant_chunks[:3]):
            evidence_refs.append(
                self._make_evidence_ref(
                    chunk=chunk,
                    source_file=source_file,
                    similarity_score=similarity_scores[index] if index < len(similarity_scores) else 0.0,
                )
            )
        return evidence_refs

    def _generate_generic_answer(self, question: str) -> str:
        return (
            f"I understand you're asking about \"{question}\". "
            "I don't have enough document evidence to provide a grounded answer yet."
        )

    def _build_gap_steps_from_chunks(self, rag_context: RAGContext) -> List[GapStep]:
        steps: List[GapStep] = []
        for index, chunk in enumerate(rag_context.relevant_chunks[:3], start=1):
            sentence = self._extract_cue_sentence(chunk["content"])
            keyword = self._select_gap_keyword(sentence) or f"step_{index}"
            prompt = re.sub(re.escape(keyword), "_____", sentence, count=1, flags=re.IGNORECASE)
            score = rag_context.similarity_scores[index - 1] if index - 1 < len(rag_context.similarity_scores) else 0.0
            steps.append(
                GapStep(
                    order=index,
                    prompt=prompt,
                    placeholder="Fill the missing reasoning step",
                    expected_concept=keyword,
                    rubric_hint=(
                        "Leave gaps at logical transitions or conceptual conclusions—not isolated "
                        "numbers, dates, or single data points unless they are the conceptual hinge."
                    ),
                    evidence_refs=[
                        self._make_evidence_ref(
                            chunk=chunk,
                            source_file=rag_context.source_file,
                            similarity_score=score,
                        )
                    ],
                )
            )
        return steps

    def _render_gap_answer(
        self,
        question: str,
        reflection: Optional[str],
        gap_steps: List[GapStep],
    ) -> str:
        reflection_prefix = f"Learner reflection: {reflection}\n\n" if reflection else ""
        if not gap_steps:
            return f"{reflection_prefix}The document did not yield stable reasoning steps for \"{question}\"."
        rendered_steps = "\n".join(f"Step {step.order}: {step.prompt}" for step in gap_steps)
        return (
            f"{reflection_prefix}Complete the evidence-backed reasoning scaffold for \"{question}\":\n\n"
            f"{rendered_steps}"
        )

    _GAP_DATAPOINT_RE = re.compile(
        r"^(?:\d+(?:\.\d+)?%?$|\$?\d[\d,]*$|(?:19|20)\d{2}s?)$", re.IGNORECASE
    )

    def _is_datapoint_gap_token(self, word: str) -> bool:
        w = word.strip()
        if not w:
            return True
        if self._GAP_DATAPOINT_RE.match(w):
            return True
        return bool(re.fullmatch(r"\d{1,3}", w))

    def _select_gap_keyword(self, sentence: str) -> Optional[str]:
        stopwords = {
            "about",
            "after",
            "before",
            "between",
            "document",
            "during",
            "their",
            "there",
            "those",
            "these",
            "which",
            "where",
            "while",
        }
        causal_pref = (
            "because",
            "therefore",
            "thus",
            "hence",
            "implies",
            "suggests",
            "consequently",
            "generalization",
            "mechanism",
            "underlying",
            "relationship",
            "inference",
        )
        lower = sentence.lower()
        candidates = [w for w in re.findall(r"\b[a-zA-Z]{5,}\b", sentence) if w.lower() not in stopwords]
        for w in candidates:
            if self._is_datapoint_gap_token(w):
                continue
            if w.lower() in causal_pref:
                return w
        if any(c in lower for c in causal_pref):
            for w in candidates:
                if not self._is_datapoint_gap_token(w):
                    return w
        for w in candidates:
            if not self._is_datapoint_gap_token(w):
                return w
        return None

    def _summarize_recent_turns(self, messages: List[QAMessage], limit: int = 5) -> Optional[str]:
        if not messages:
            return None
        summary_parts = []
        for message in messages[-limit:]:
            label = "learner" if message.type == "user" else "assistant"
            condensed = " ".join(message.content.strip().split())
            summary_parts.append(f"{label}: {condensed[:120]}")
        return " | ".join(summary_parts)

    def _resolve_pending_exchange(
        self,
        session: QASession,
        pending_question_id: Optional[str],
    ) -> Optional[PendingQAExchange]:
        if pending_question_id:
            return session.pending_questions.get(pending_question_id)
        if not session.pending_questions:
            return None
        return sorted(
            session.pending_questions.values(),
            key=lambda pending: pending.created_at,
        )[-1]

    def _tokenize(self, text: str) -> set[str]:
        return {token for token in re.findall(r"\b[a-z0-9]{4,}\b", text.lower())}

    def _overlap_score(self, left: set[str], right: set[str]) -> float:
        if not left or not right:
            return 0.0
        return len(left & right) / max(len(left), 1)

    def _support_tier_label(self, support_level: SupportLevel) -> str:
        labels = {
            SupportLevel.GROUNDED: "direct_citation",
            SupportLevel.INFERRED: "inference",
            SupportLevel.WEAK_SUPPORT: "weak_filler",
        }
        return labels[support_level]

    def _score_band(self, score: float) -> str:
        if score >= 0.8:
            return "high"
        if score >= 0.45:
            return "medium"
        return "low"

    def _calculate_confidence_score(self, rag_context: Optional[RAGContext]) -> Optional[float]:
        if not rag_context or not rag_context.similarity_scores:
            return None
        avg_score = sum(rag_context.similarity_scores) / len(rag_context.similarity_scores)
        return min(max(avg_score, 0.0), 1.0)

    def _build_session_response(self, session: QASession) -> QASessionResponse:
        last_activity = session.messages[-1].timestamp if session.messages else None
        return QASessionResponse(
            session_id=session.session_id,
            file_id=session.file_id,
            filename=session.filename,
            created_at=session.created_at,
            message_count=session.total_messages,
            last_activity=last_activity,
            pending_questions=len(session.pending_questions),
        )

    async def get_session(self, session_id: str) -> Optional[QASession]:
        return self.active_sessions.get(session_id)

    async def get_session_messages(self, session_id: str) -> List[QAMessage]:
        session = await self.get_session(session_id)
        return session.messages if session else []

    async def delete_session(self, session_id: str) -> bool:
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            logger.info("Deleted QA session %s", session_id)
            return True
        return False

    async def get_all_sessions(self) -> List[QASessionResponse]:
        return [self._build_session_response(session) for session in self.active_sessions.values()]


qa_service = QAService()
