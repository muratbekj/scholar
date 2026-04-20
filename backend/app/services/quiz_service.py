# Quiz service for generating and managing quizzes from documents
from __future__ import annotations

import logging
import re
import uuid
from inspect import isawaitable
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..models.quiz import (
    DifficultyLevel,
    QuestionType,
    Quiz,
    QuizQuestion,
    QuizQuestionResponse,
    QuizRequest,
    QuizResponse,
    QuizResult,
    QuizSession,
    QuizSessionCreate,
    QuizSessionResponse,
    QuizSubmission,
)
from ..models.study import EvidenceRef, GapStep, QuizMode
from .document import DocumentService
from .llm_service import llm_service

logger = logging.getLogger(__name__)


class QuizService:
    """Service for generating and managing quizzes from documents."""

    @staticmethod
    def _has_specific_page_citation(text: str) -> bool:
        """Detect explicit page references for human-agency / verification boosts (oversight mode)."""
        t = text.lower()
        return bool(
            re.search(r"\bpage\s*[:\s]?\s*\d+", t)
            or re.search(r"\bp\.?\s*\d+", t)
            or re.search(r"\bpp\.?\s*\d+", t)
            or re.search(r"\bpg\.?\s*\d+", t)
        )

    def _reasoning_gap_missed_logic(self, question: QuizQuestion) -> List[str]:
        """AfterMath: when the learner misses the gap, show the document logic path (not only the answer)."""
        lines: List[str] = []
        meta = question.metadata or {}
        revealed = meta.get("revealed_answer")
        if revealed:
            lines.append(f"How the document states it: {revealed}")
        if question.correct_answer:
            lines.append(f"Conceptual bridge the item targeted: {question.correct_answer}")
        if question.grading_rubric:
            lines.append("Rubric / expected logic:")
            for item in question.grading_rubric[:6]:
                lines.append(f"• {item}")
        if question.gap_steps:
            lines.append("Structured steps:")
            for step in question.gap_steps[:5]:
                hint = f" ({step.rubric_hint})" if step.rubric_hint else ""
                lines.append(f"{step.order}. {step.prompt}{hint}")
        return lines

    def __init__(self, document_service: DocumentService = None, use_llm: bool = True):
        self.document_service = document_service or DocumentService()
        self.active_quizzes: Dict[str, Quiz] = {}
        self.active_sessions: Dict[str, QuizSession] = {}
        self.use_llm = use_llm
        logger.info("Initialized Quiz Service with mode-aware generation")

    async def generate_quiz(self, request: QuizRequest) -> QuizResponse:
        start_time = datetime.now()
        logger.info(
            "Generating %s quiz for file %s with %s questions",
            request.mode.value,
            request.filename,
            request.num_questions,
        )

        document_content = await self._get_document_content(request.file_id)
        questions = await self._generate_questions(document_content, request)

        quiz_id = str(uuid.uuid4())
        total_points = sum(question.points for question in questions)
        quiz = Quiz(
            quiz_id=quiz_id,
            title=f"{request.mode.value.replace('_', ' ').title()} Quiz on {request.filename}",
            description=(
                f"Generated {request.mode.value.replace('_', ' ')} quiz with "
                f"{len(questions)} questions"
            ),
            file_id=request.file_id,
            filename=request.filename,
            questions=questions,
            total_questions=len(questions),
            total_points=total_points,
            difficulty=request.difficulty,
            mode=request.mode,
            estimated_time=request.estimated_time or self._estimate_quiz_time(len(questions), request.difficulty),
            created_at=datetime.now(),
        )
        self.active_quizzes[quiz_id] = quiz

        processing_time = (datetime.now() - start_time).total_seconds()
        return QuizResponse(
            quiz_id=quiz.quiz_id,
            title=quiz.title,
            description=quiz.description,
            file_id=quiz.file_id,
            filename=quiz.filename,
            total_questions=quiz.total_questions,
            total_points=quiz.total_points,
            difficulty=quiz.difficulty,
            mode=quiz.mode,
            estimated_time=quiz.estimated_time,
            created_at=quiz.created_at,
            processing_time=processing_time,
        )

    async def create_session(self, session_data: QuizSessionCreate) -> QuizSessionResponse:
        if session_data.quiz_id not in self.active_quizzes:
            raise ValueError(f"Quiz {session_data.quiz_id} not found")

        session_id = str(uuid.uuid4())
        session = QuizSession(
            session_id=session_id,
            quiz_id=session_data.quiz_id,
            file_id=session_data.file_id,
            filename=session_data.filename,
            started_at=datetime.now(),
        )
        self.active_sessions[session_id] = session
        return QuizSessionResponse(
            session_id=session_id,
            quiz_id=session_data.quiz_id,
            file_id=session_data.file_id,
            filename=session_data.filename,
            started_at=session.started_at,
            is_completed=False,
        )

    async def get_quiz_questions(self, quiz_id: str) -> List[QuizQuestionResponse]:
        if quiz_id not in self.active_quizzes:
            raise ValueError(f"Quiz {quiz_id} not found")

        return [
            QuizQuestionResponse(
                id=question.id,
                question=question.question,
                question_type=question.question_type,
                options=question.options,
                difficulty=question.difficulty,
                points=question.points,
                mode=question.mode,
                evidence_refs=question.evidence_refs,
                prior_ai_answer=question.prior_ai_answer,
                review_guidance=question.review_guidance,
                gap_prompt=question.gap_prompt,
                gap_steps=question.gap_steps,
                grading_rubric=question.grading_rubric,
            )
            for question in self.active_quizzes[quiz_id].questions
        ]

    async def submit_quiz(self, submission: QuizSubmission) -> QuizResult:
        if submission.session_id not in self.active_sessions:
            raise ValueError(f"Session {submission.session_id} not found")

        session = self.active_sessions[submission.session_id]
        if session.is_completed:
            raise ValueError("Quiz session already completed")
        if session.quiz_id not in self.active_quizzes:
            raise ValueError(f"Quiz {session.quiz_id} not found")

        quiz = self.active_quizzes[session.quiz_id]
        result = await self._calculate_results(quiz, submission.answers)
        result.session_id = submission.session_id
        result.time_taken = (datetime.now() - session.started_at).total_seconds()

        session.answers = submission.answers
        session.completed_at = datetime.now()
        session.score = result.score
        session.total_points_earned = result.total_points_earned
        session.total_possible_points = result.total_possible_points
        session.time_taken = result.time_taken
        session.is_completed = True
        return result

    async def get_session(self, session_id: str) -> Optional[QuizSession]:
        return self.active_sessions.get(session_id)

    async def get_all_sessions(self) -> List[QuizSessionResponse]:
        return [
            QuizSessionResponse(
                session_id=session.session_id,
                quiz_id=session.quiz_id,
                file_id=session.file_id,
                filename=session.filename,
                started_at=session.started_at,
                is_completed=session.is_completed,
                score=session.score,
                time_taken=session.time_taken,
            )
            for session in self.active_sessions.values()
        ]

    async def delete_session(self, session_id: str) -> bool:
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            return True
        return False

    async def _get_document_content(self, file_id: str) -> str:
        full_text = self.document_service.get_extracted_text(file_id)
        if isawaitable(full_text):
            full_text = await full_text
        if full_text and full_text.strip():
            return full_text

        chunks = self.document_service.get_document_chunks(file_id)
        if isawaitable(chunks):
            chunks = await chunks
        if chunks:
            content = "\n\n".join(chunk["content"] for chunk in chunks)
            if content.strip():
                return content

        file_info = self.document_service.get_file_info(file_id)
        if isawaitable(file_info):
            file_info = await file_info
        if file_info and file_info.content_summary:
            full_text = file_info.content_summary.get("full_text", "")
            if full_text and full_text.strip():
                return full_text

        raise ValueError(f"No content found in document {file_id}")

    async def _generate_questions(self, content: str, request: QuizRequest) -> List[QuizQuestion]:
        if request.mode == QuizMode.REASONING_GAP:
            return self._build_reasoning_gap_questions(content, request)
        if request.mode == QuizMode.AI_OVERSIGHT:
            return self._build_ai_oversight_questions(content, request)
        return await self._build_standard_questions(content, request)

    async def _build_standard_questions(self, content: str, request: QuizRequest) -> List[QuizQuestion]:
        question_types = request.question_types or [QuestionType.MULTIPLE_CHOICE, QuestionType.TRUE_FALSE]

        if self.use_llm:
            try:
                questions_data = await llm_service.generate_quiz_questions(
                    content=content,
                    num_questions=request.num_questions,
                    difficulty=request.difficulty.value,
                    question_types=[question_type.value for question_type in question_types],
                    include_explanations=request.include_explanations,
                )
                questions: List[QuizQuestion] = []
                for question_data in questions_data[: request.num_questions]:
                    questions.append(
                        QuizQuestion(
                            id=str(uuid.uuid4()),
                            question=question_data["question"],
                            question_type=QuestionType(question_data["type"]),
                            options=question_data.get("options"),
                            correct_answer=question_data["correct_answer"],
                            explanation=question_data.get("explanation") if request.include_explanations else None,
                            difficulty=request.difficulty,
                            points=1,
                            mode=QuizMode.STANDARD,
                        )
                    )
                if questions:
                    return questions
            except Exception as exc:
                logger.warning("Falling back to heuristic quiz generation: %s", exc)

        sentences = self._extract_candidate_sentences(content, request.num_questions + 3)
        if not sentences:
            sentences = ["The document did not include enough content for detailed questions."]

        questions: List[QuizQuestion] = []
        for index in range(request.num_questions):
            sentence = sentences[index % len(sentences)]
            question_type = question_types[index % len(question_types)]
            evidence_refs = [self._make_sentence_evidence_ref(sentence, request.file_id, index)]

            if question_type == QuestionType.TRUE_FALSE:
                correct_answer = "True"
                question_text = f"True or false: {sentence}"
                options = ["True", "False"]
            elif question_type == QuestionType.SHORT_ANSWER:
                keyword = self._select_keyword(sentence) or "concept"
                question_text = f"According to the document, what key concept completes this idea: {sentence[:100]}?"
                correct_answer = keyword
                options = None
            else:
                options = self._build_multiple_choice_options(sentences, sentence)
                correct_answer = sentence
                question_text = "Which of the following statements is directly supported by the document?"

            questions.append(
                QuizQuestion(
                    id=str(uuid.uuid4()),
                    question=question_text,
                    question_type=question_type,
                    options=options,
                    correct_answer=correct_answer,
                    explanation=f"This question is grounded in the document excerpt: {sentence[:140]}",
                    difficulty=request.difficulty,
                    points=1,
                    mode=QuizMode.STANDARD,
                    evidence_refs=evidence_refs,
                )
            )

        return questions

    def _build_reasoning_gap_questions(self, content: str, request: QuizRequest) -> List[QuizQuestion]:
        sentences = self._extract_candidate_sentences(content, request.num_questions + 5)
        questions: List[QuizQuestion] = []

        for index in range(request.num_questions):
            sentence = sentences[index % len(sentences)]
            keyword = self._select_keyword(sentence) or "concept"
            masked_sentence = re.sub(
                re.escape(keyword),
                "_____",
                sentence,
                flags=re.IGNORECASE,
                count=1,
            )
            accepted_reasoning = [keyword, keyword.lower()]
            evidence_refs = [self._make_sentence_evidence_ref(sentence, request.file_id, index)]
            gap_steps = self._build_gap_steps(sentence, request.file_id, index)
            questions.append(
                QuizQuestion(
                    id=str(uuid.uuid4()),
                    question="Complete the missing step in the reasoning from the document.",
                    question_type=QuestionType.SHORT_ANSWER,
                    correct_answer=keyword,
                    explanation=f"The missing reasoning step is recovered from the original sentence: {sentence}",
                    difficulty=request.difficulty,
                    points=1,
                    mode=QuizMode.REASONING_GAP,
                    evidence_refs=evidence_refs,
                    gap_prompt=masked_sentence,
                    accepted_reasoning=accepted_reasoning,
                    gap_steps=gap_steps,
                    grading_rubric=[
                        "Names the missing concept or causal link from the document (not a bare number or date unless it is the conceptual hinge).",
                        "Stays within the evidence instead of adding outside claims.",
                    ],
                    metadata={"revealed_answer": sentence},
                )
            )

        return questions

    def _build_ai_oversight_questions(self, content: str, request: QuizRequest) -> List[QuizQuestion]:
        sentences = self._extract_candidate_sentences(content, request.num_questions + 5)
        questions: List[QuizQuestion] = []
        flaw_types = ["overclaim", "contradiction"]

        for index in range(request.num_questions):
            sentence = sentences[index % len(sentences)]
            flaw_type = flaw_types[index % len(flaw_types)]
            prior_ai_answer, expected_issues = self._build_flawed_claim(sentence, flaw_type)
            evidence_refs = [self._make_sentence_evidence_ref(sentence, request.file_id, index)]
            questions.append(
                QuizQuestion(
                    id=str(uuid.uuid4()),
                    question="Critique the AI answer using the document evidence. Identify what is flawed or unsupported.",
                    question_type=QuestionType.SHORT_ANSWER,
                    correct_answer="Any valid evidence-backed critique identifying the flaw earns credit.",
                    explanation="A strong answer explains why the AI claim goes beyond or contradicts the source evidence.",
                    difficulty=request.difficulty,
                    points=2,
                    mode=QuizMode.AI_OVERSIGHT,
                    evidence_refs=evidence_refs,
                    prior_ai_answer=prior_ai_answer,
                    review_guidance="Reference the provided excerpt, chunk, or page when explaining the flaw.",
                    grading_rubric=[
                        "Identifies a concrete flaw in the prior AI answer.",
                        "Anchors the critique in the provided document evidence.",
                    ],
                    metadata={"expected_issues": expected_issues, "source_sentence": sentence},
                )
            )

        return questions

    async def _calculate_results(self, quiz: Quiz, answers: Dict[str, str]) -> QuizResult:
        total_points_earned = 0
        correct_answers = 0
        question_results: List[Dict[str, Any]] = []

        agency_boost_count = 0
        for question in quiz.questions:
            user_answer = answers.get(question.id, "")
            grading = await self._grade_answer(question, user_answer)
            total_points_earned += grading["points_earned"]
            if grading["is_correct"]:
                correct_answers += 1
            if grading.get("human_agency_bonus_applied"):
                agency_boost_count += 1

            question_results.append(
                {
                    "question_id": question.id,
                    "question": question.question,
                    "mode": question.mode.value,
                    "user_answer": user_answer,
                    "correct_answer": question.correct_answer,
                    "is_correct": grading["is_correct"],
                    "points_earned": grading["points_earned"],
                    "points_possible": question.points,
                    "explanation": question.explanation,
                    "review_note": grading["review_note"],
                    "review_details": grading.get("review_details", []),
                    "evidence_refs": [ref.model_dump() for ref in question.evidence_refs],
                    "prior_ai_answer": question.prior_ai_answer,
                    "gap_steps": [step.model_dump() for step in question.gap_steps],
                    "human_agency_bonus_applied": grading.get("human_agency_bonus_applied", False),
                }
            )

        score = (total_points_earned / quiz.total_points) * 100 if quiz.total_points > 0 else 0
        feedback = self._generate_feedback(score, correct_answers, quiz.total_questions)
        if agency_boost_count > 0:
            feedback += (
                f" Human agency: {agency_boost_count} oversight response(s) cited a specific page — "
                "strong verification habit."
            )

        return QuizResult(
            session_id="",
            quiz_id=quiz.quiz_id,
            score=score,
            total_points_earned=total_points_earned,
            total_possible_points=quiz.total_points,
            correct_answers=correct_answers,
            total_questions=quiz.total_questions,
            time_taken=0,
            completed_at=datetime.now(),
            question_results=question_results,
            feedback=feedback,
        )

    async def _grade_answer(self, question: QuizQuestion, user_answer: str) -> Dict[str, Any]:
        if question.mode == QuizMode.AI_OVERSIGHT:
            if self.use_llm:
                llm_graded = await self._llm_grade_oversight(question, user_answer)
                if llm_graded is not None:
                    return llm_graded
            return self._score_ai_oversight_answer(question, user_answer)
        if question.mode == QuizMode.REASONING_GAP:
            if self.use_llm:
                llm_graded = await self._llm_grade_reasoning_gap(question, user_answer)
                if llm_graded is not None:
                    return llm_graded
            return self._score_reasoning_gap_answer(question, user_answer)

        is_correct = self._check_answer(question, user_answer)
        return {
            "is_correct": is_correct,
            "points_earned": question.points if is_correct else 0,
            "review_note": "Matched the expected answer." if is_correct else "Did not match the expected answer.",
            "human_agency_bonus_applied": False,
        }

    async def _llm_grade_oversight(
        self, question: QuizQuestion, user_answer: str
    ) -> Optional[Dict[str, Any]]:
        excerpt = ""
        if question.evidence_refs:
            excerpt = (question.evidence_refs[0].excerpt or "") or ""
        meta = question.metadata or {}
        if not excerpt and meta.get("source_sentence"):
            excerpt = str(meta["source_sentence"])

        result = await llm_service.grade_oversight_critique(
            prior_ai_answer=question.prior_ai_answer or "",
            evidence_excerpt=excerpt or "No excerpt available.",
            user_critique=user_answer,
        )
        if not result:
            return None

        raw_points = int(result.get("points", 0))
        points_earned = max(0, min(question.points, raw_points))
        note = str(result.get("note", "")).strip() or "Model review complete."

        details = [
            "Graded with oversight model: valid critique and evidence anchoring considered.",
            f"Model flags — valid critique: {result.get('valid_critique')}, "
            f"evidence anchored: {result.get('evidence_anchored')}.",
        ]
        bonus_applied = False
        if result.get("valid_critique") and self._has_specific_page_citation(user_answer):
            if points_earned < question.points:
                points_earned = min(question.points, points_earned + 1)
            bonus_applied = True
            details.append(
                "Human agency boost: explicit page reference — verification over shortcut trust."
            )

        return {
            "is_correct": points_earned > 0,
            "points_earned": points_earned,
            "review_note": note,
            "review_details": details,
            "human_agency_bonus_applied": bonus_applied,
        }

    async def _llm_grade_reasoning_gap(
        self, question: QuizQuestion, user_answer: str
    ) -> Optional[Dict[str, Any]]:
        excerpt = ""
        if question.evidence_refs:
            excerpt = (question.evidence_refs[0].excerpt or "") or ""
        meta = question.metadata or {}
        if not excerpt and meta.get("revealed_answer"):
            excerpt = str(meta["revealed_answer"])

        concepts = list(question.accepted_reasoning) + [question.correct_answer]
        result = await llm_service.grade_reasoning_gap_submission(
            gap_prompt=question.gap_prompt or question.question,
            expected_concepts=concepts,
            rubric=question.grading_rubric,
            user_answer=user_answer,
            source_excerpt=excerpt or "No excerpt available.",
        )
        if not result:
            return None

        accept = bool(result.get("accept"))
        note = str(result.get("note", "")).strip() or "Model review complete."
        details: List[str] = [
            "Graded with reasoning-gap model judge (equivalent concepts accepted).",
        ]
        if not accept:
            details.extend(self._reasoning_gap_missed_logic(question))
        return {
            "is_correct": accept,
            "points_earned": question.points if accept else 0,
            "review_note": note,
            "review_details": details,
            "human_agency_bonus_applied": False,
        }

    def _score_reasoning_gap_answer(self, question: QuizQuestion, user_answer: str) -> Dict[str, Any]:
        if not user_answer.strip():
            return {"is_correct": False, "points_earned": 0, "review_note": "No reasoning step was provided."}

        normalized_user = user_answer.lower().strip()
        accepted = {item.lower().strip() for item in question.accepted_reasoning + [question.correct_answer]}
        is_correct = any(
            candidate in normalized_user or normalized_user in candidate
            for candidate in accepted
            if candidate
        )
        details: List[str] = [
            "Equivalent reasoning is accepted when it preserves the document's causal link.",
            f"Expected anchor terms: {', '.join(sorted(accepted))}" if accepted else "No anchor terms available.",
        ]
        if not is_correct:
            details.extend(self._reasoning_gap_missed_logic(question))
        return {
            "is_correct": is_correct,
            "points_earned": question.points if is_correct else 0,
            "review_note": (
                "Accepted equivalent intermediate reasoning."
                if is_correct
                else "The submitted reasoning step did not match the accepted intermediate reasoning."
            ),
            "review_details": details,
            "human_agency_bonus_applied": False,
        }

    def _score_ai_oversight_answer(self, question: QuizQuestion, user_answer: str) -> Dict[str, Any]:
        normalized_user = user_answer.lower().strip()
        expected_issues = set((question.metadata or {}).get("expected_issues", []))
        critique_terms = {
            "unsupported",
            "not supported",
            "contradiction",
            "overclaim",
            "too broad",
            "omission",
            "omits",
            "wrong",
        }
        valid_issue = bool(
            normalized_user
            and (
                any(issue in normalized_user for issue in expected_issues)
                or any(term in normalized_user for term in critique_terms)
            )
        )
        evidence_match = any(
            (ref.excerpt or "").lower()[:40] in normalized_user
            for ref in question.evidence_refs
            if ref.excerpt
        )
        cited = any(marker in normalized_user for marker in ["page", "chunk", "excerpt", "\"", "'"])
        evidence_backed = valid_issue and (evidence_match or cited)
        page_cite = self._has_specific_page_citation(normalized_user)

        if evidence_backed:
            points_earned = question.points
            review_note = "Valid critique with concrete evidence reference."
        elif valid_issue:
            points_earned = max(question.points - 1, 1)
            review_note = "Valid critique, but it needs a clearer evidence citation for full credit."
        else:
            points_earned = 0
            review_note = "The critique did not clearly identify a supported flaw in the AI answer."

        human_agency_bonus_applied = False
        if valid_issue and page_cite and points_earned < question.points:
            points_earned = min(question.points, points_earned + 1)
            human_agency_bonus_applied = True
            review_note = "Human agency boost: page-specific citation upgraded your score."
        elif valid_issue and page_cite and points_earned >= question.points:
            human_agency_bonus_applied = True

        details = [
            "Full credit requires a valid critique plus a concrete citation, excerpt, chunk, or page reference.",
            f"Expected issue types: {', '.join(sorted(expected_issues))}" if expected_issues else "No expected issue metadata available.",
        ]
        if page_cite and valid_issue:
            details.append(
                "Human agency: citing a page number supports verification (anti–automation bias)."
            )

        return {
            "is_correct": points_earned > 0,
            "points_earned": points_earned,
            "review_note": review_note,
            "review_details": details,
            "human_agency_bonus_applied": human_agency_bonus_applied,
        }

    def _check_answer(self, question: QuizQuestion, user_answer: str) -> bool:
        if not user_answer.strip():
            return False

        correct = question.correct_answer.lower().strip()
        user = user_answer.lower().strip()

        if question.question_type == QuestionType.TRUE_FALSE:
            true_variants = ["true", "t", "yes", "y", "1"]
            false_variants = ["false", "f", "no", "n", "0"]
            if correct in true_variants and user in true_variants:
                return True
            if correct in false_variants and user in false_variants:
                return True
            return False

        if question.question_type == QuestionType.MULTIPLE_CHOICE:
            return user == correct

        return user == correct or correct in user or user in correct

    def _generate_feedback(self, score: float, correct_answers: int, total_questions: int) -> str:
        if score >= 90:
            return f"Excellent! You got {correct_answers}/{total_questions} questions correct. Great job!"
        if score >= 80:
            return f"Good work! You got {correct_answers}/{total_questions} questions correct. Keep it up!"
        if score >= 70:
            return (
                f"Not bad! You got {correct_answers}/{total_questions} questions correct. "
                "Review the material for better understanding."
            )
        if score >= 60:
            return (
                f"You got {correct_answers}/{total_questions} questions correct. "
                "Consider reviewing the material more thoroughly."
            )
        return (
            f"You got {correct_answers}/{total_questions} questions correct. "
            "This material needs more study time."
        )

    def _estimate_quiz_time(self, num_questions: int, difficulty: DifficultyLevel) -> int:
        base_time_per_question = {
            DifficultyLevel.EASY: 1,
            DifficultyLevel.MEDIUM: 2,
            DifficultyLevel.HARD: 3,
        }
        return num_questions * base_time_per_question[difficulty]

    def _extract_candidate_sentences(self, content: str, limit: int) -> List[str]:
        sentences = []
        for candidate in re.split(r"(?<=[.!?])\s+|\n+", content):
            normalized = " ".join(candidate.strip().split())
            if 35 <= len(normalized) <= 220:
                sentences.append(normalized)
        return sentences[:limit] or ["The document content was too short to extract sentence-level evidence."]

    def _is_datapoint_token(self, word: str) -> bool:
        w = word.strip()
        if re.fullmatch(r"\d+(?:\.\d+)?%?", w):
            return True
        if re.fullmatch(r"\$?\d[\d,]*", w):
            return True
        if re.fullmatch(r"(?:19|20)\d{2}s?", w, re.IGNORECASE):
            return True
        if re.fullmatch(r"\d{1,3}", w):
            return True
        return False

    def _select_keyword(self, sentence: str) -> Optional[str]:
        stopwords = {
            "about",
            "after",
            "before",
            "between",
            "document",
            "during",
            "their",
            "there",
            "these",
            "those",
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
        words = [w for w in re.findall(r"\b[a-zA-Z]{5,}\b", sentence) if w.lower() not in stopwords]
        for word in words:
            if self._is_datapoint_token(word):
                continue
            if word.lower() in causal_pref:
                return word
        if any(c in lower for c in causal_pref):
            for word in words:
                if not self._is_datapoint_token(word):
                    return word
        for word in words:
            if not self._is_datapoint_token(word):
                return word
        return words[0] if words else None

    def _build_multiple_choice_options(self, sentences: List[str], correct_sentence: str) -> List[str]:
        distractors = [sentence for sentence in sentences if sentence != correct_sentence][:3]
        options = [correct_sentence, *distractors]
        while len(options) < 4:
            options.append(f"Distractor option {len(options)}")
        return options[:4]

    def _build_flawed_claim(self, sentence: str, flaw_type: str) -> tuple[str, List[str]]:
        if flaw_type == "contradiction":
            if " is " in sentence:
                return sentence.replace(" is ", " is not ", 1), ["contradiction", "not supported"]
            if " are " in sentence:
                return sentence.replace(" are ", " are not ", 1), ["contradiction", "not supported"]
            return f"The document denies that {sentence.lower()}", ["contradiction", "not supported"]
        return f"{sentence} This always applies in every case.", ["overclaim", "too broad", "unsupported"]

    def _make_sentence_evidence_ref(self, sentence: str, file_id: str, index: int) -> EvidenceRef:
        return EvidenceRef(
            chunk_id=f"derived-{index + 1}",
            excerpt=sentence[:220],
            source_file=file_id,
            score=1.0,
            label="derived_sentence",
            support_tier="high",
            score_band="high",
        )

    def _build_gap_steps(self, sentence: str, file_id: str, index: int) -> List[GapStep]:
        phrases = [phrase.strip(" ,") for phrase in re.split(r",| because | so that | which ", sentence) if phrase.strip()]
        if not phrases:
            phrases = [sentence]

        gap_steps: List[GapStep] = []
        for step_index, phrase in enumerate(phrases[:3], start=1):
            keyword = self._select_keyword(phrase) or f"step_{step_index}"
            prompt = re.sub(re.escape(keyword), "_____", phrase, flags=re.IGNORECASE, count=1)
            gap_steps.append(
                GapStep(
                    order=step_index,
                    prompt=prompt,
                    placeholder="Fill the missing concept",
                    expected_concept=keyword,
                    rubric_hint=(
                        "Recover the logical or conceptual bridge—avoid gaps that are only isolated data points."
                    ),
                    evidence_refs=[self._make_sentence_evidence_ref(sentence, file_id, index)],
                )
            )
        return gap_steps


quiz_service = QuizService()
