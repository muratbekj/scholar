# Scholar Backend API Documentation

## Overview

The Scholar Backend API provides AI-powered document processing and study tools. It supports file uploads, question-answering with RAG (Retrieval-Augmented Generation), quiz generation, and flashcard creation.

**Base URL**: `http://localhost:8000` (default)

## Table of Contents

- [File Management](#file-management)
- [Question & Answer (QA)](#question--answer-qa)
- [Quiz Generation](#quiz-generation)
- [Flashcard Generation](#flashcard-generation)
- [Health Checks](#health-checks)
- [Error Handling](#error-handling)

---

## File Management

### Upload File

**POST** `/files/upload`

Upload a document file with conditional embedding processing based on study mode.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file` | `UploadFile` | Yes | Document file (PDF, DOCX, PPTX, TXT) |
| `study_mode` | `string` | No | Study mode: `'qa'`, `'quiz'`, or `'flashcards'` |

#### Supported File Formats

- PDF (.pdf)
- Microsoft Word (.docx)
- Plain Text (.txt)

#### Request Example

```bash
curl -X POST "http://localhost:8000/files/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf" \
  -F "study_mode=qa"
```

#### Response Example

```json
{
  "message": "File uploaded and processed successfully with RAG for QA",
  "file_id": "f137978b-951c-4e27-ae27-a32cca37b184",
  "filename": "document.pdf",
  "size": 1024000,
  "upload_time": "2024-01-15T10:30:00Z",
  "content_summary": {
    "word_count": 5000,
    "character_count": 25000,
    "format": "pdf"
  },
  "rag_processing": {
    "processing_time_seconds": 15.5,
    "chunking": {
      "total_chunks": 25,
      "chunk_size": 1000
    },
    "embedding": {
      "enabled": true,
      "total_embeddings": 25
    },
    "vector_storage": {
      "enabled": true,
      "vectors_stored": 25
    }
  }
}
```

### Upload File with Explicit Embedding Control

**POST** `/files/upload-with-embedding`

Upload a document file with explicit control over embedding generation.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file` | `UploadFile` | Yes | Document file |
| `enable_embedding` | `boolean` | No | Enable embedding generation (default: true) |

### Get File Information

**GET** `/files/info/{file_id}`

Get information about an uploaded file.

#### Response Example

```json
{
  "filename": "document.pdf",
  "size": 1024000,
  "file_id": "f137978b-951c-4e27-ae27-a32cca37b184",
  "upload_time": "2024-01-15T10:30:00Z",
  "file_type": "pdf",
  "content_summary": {
    "word_count": 5000,
    "character_count": 25000
  }
}
```

### Get Extracted Text

**GET** `/files/{file_id}/text`

Get the extracted text content from an uploaded file.

#### Response Example

```json
{
  "file_id": "f137978b-951c-4e27-ae27-a32cca37b184",
  "extracted_text": "This is the extracted text content from the document..."
}
```

### Get Document Chunks

**GET** `/files/{file_id}/chunks`

Get all chunks for a document (if it was chunked due to large size).

#### Response Example

```json
{
  "file_id": "f137978b-951c-4e27-ae27-a32cca37b184",
  "chunks": [
    {
      "id": "chunk_1",
      "content": "First chunk content...",
      "metadata": {}
    }
  ],
  "total_chunks": 25
}
```

### Get Specific Chunk

**GET** `/files/{file_id}/chunks/{chunk_id}`

Get a specific chunk by its ID.

### Delete File

**DELETE** `/files/{file_id}`

Delete an uploaded file and its associated embeddings.

#### Response Example

```json
{
  "message": "File and embeddings deleted successfully",
  "file_id": "f137978b-951c-4e27-ae27-a32cca37b184",
  "vector_store_deleted": true,
  "document_deleted": true
}
```

### Get Supported Formats

**GET** `/files/formats`

Get list of supported file formats.

#### Response Example

```json
["pdf", "docx", "pptx", "txt"]
```

### Search Documents

**GET** `/files/search`

Search documents using vector similarity (only works for files processed with embeddings).

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | `string` | Yes | Search query |
| `k` | `integer` | No | Number of results to return (default: 5) |
| `file_id` | `string` | No | Search within specific file only |

#### Response Example

```json
{
  "success": true,
  "query": "machine learning",
  "results": [
    {
      "content": "Machine learning is a subset of artificial intelligence...",
      "metadata": {
        "file_id": "f137978b-951c-4e27-ae27-a32cca37b184",
        "chunk_id": "chunk_5"
      },
      "similarity_score": 0.95,
      "id": "result_1"
    }
  ],
  "total_results": 1,
  "search_time": "0.15s"
}
```

### Get Processing Stats

**GET** `/files/stats`

Get processing statistics and system health.

---

## Question & Answer (QA)

### Ask Question

**POST** `/qa/ask`

Ask a question about an uploaded document using RAG.

#### Request Body

```json
{
  "question": "What is machine learning?",
  "file_id": "f137978b-951c-4e27-ae27-a32cca37b184",
  "session_id": "optional_session_id",
  "generation_mode": "standard"
}
```

`generation_mode` accepts `standard` or `reasoning_gap`.

#### Response Example: pending reflective gate

```json
{
  "answer": "Before I reveal the full answer, write 1-2 sentences about what you think the document supports.",
  "session_id": "qa_session_123",
  "message_id": "msg_2",
  "response_state": "pending_reflection",
  "reflection_state": "required",
  "pending_question_id": "pending_123",
  "generation_mode": "standard",
  "reflection_prompt": "Before I reveal the full answer...",
  "visible_cue": "Machine learning systems improve when they train on labeled examples.",
  "hidden_evidence_count": 2,
  "visible_evidence_refs": [
    {
      "chunk_id": "chunk_5",
      "score": 0.95,
      "support_tier": "high",
      "score_band": "high"
    }
  ],
  "processing_time": 1.2
}
```

#### Submit Reflection

**POST** `/qa/reflect`

```json
{
  "session_id": "qa_session_123",
  "pending_question_id": "pending_123",
  "reflection": "I think the document argues that labels give the model a reliable signal."
}
```

Reflection validation ( **`400`** if unmet): whitespace-only is rejected; the text must be at least **8 words**. It must also tie to the pending question, visible cue, or start of the retrieved chunk: either **two** meaningful token overlaps (4+ chars, high-frequency words excluded) or **one** overlap plus at least **10** words total (inflections like *labels* / *labeled* count via a short prefix match). Generic rambling with no connection still fails.

When the LLM is enabled, the **visible cue** for `pending_reflection` is generated with instructions to quote relevant passage without summarizing the direct answer (e.g. omit resolving facts the question asks for). With `use_llm=false`, the cue is a short verbatim slice of the chunk only (weaker anti-leak guarantee).

When the critic’s label disagrees with the retrieval heuristic on a sentence, the backend logs `critic_heuristic_disagreement` (index, levels, sentence preview) for auditing dual-agent behavior.

#### Response Example: completed answer with audit metadata

```json
{
  "answer": "Based on the document, labeled examples provide the training signal that supports later generalization.",
  "session_id": "qa_session_123",
  "message_id": "msg_3",
  "response_state": "answered",
  "reflection_state": "submitted",
  "intuition_text": "I think the document argues that labels give the model a reliable signal.",
  "generation_mode": "standard",
  "processing_time": 2.5,
  "answer_segments": [
    {
      "text": "Based on the document, labeled examples provide the training signal that supports later generalization.",
      "support_level": "grounded",
      "support_tier": "direct_citation",
      "support_label_ui": "Direct citation",
      "source_match_percent": 88,
      "evidence_refs": [
        {
          "chunk_id": "chunk_5",
          "score": 0.95,
          "support_tier": "high",
          "score_band": "high"
        }
      ]
    }
  ],
  "audit_summary": {
    "summary": "1 grounded, 0 inferred, 0 weak-support segment(s).",
    "source_links": [
      {
        "excerpt": "Machine learning systems improve when they train on labeled examples.",
        "page_number": null,
        "chunk_id": "chunk_5",
        "segment_index": 0,
        "support_level": "grounded"
      }
    ]
  }
}
```

`intuition_text` echoes the learner’s reflection from **`POST /qa/reflect`** so the client can show **human intuition vs model answer** side by side. `audit_summary.source_links` lists **grounded** spans with excerpt and optional **page** / **chunk_id** for verification (e.g. jump-to-page in a PDF viewer).

**Answer segment fields (transparency / heatmap)**

| Field | Meaning |
|-------|--------|
| `support_level` | `grounded` \| `inferred` \| `weak_support` — machine label after retrieval alignment and (when LLM is enabled) a **second-pass critic** on the same local model. The critic may internally use a `statistical_shortcut` notion (treated as `weak_support`) when the answer is not semantically anchored in the evidence. |
| `support_tier` | Stable slug: `direct_citation`, `inference`, `weak_filler` — maps to UI green / yellow / red styling. |
| `support_label_ui` | Short human-readable tier for tooltips: e.g. “Direct citation”, “Logical inference”, “Weakly supported (possible filler)”. |
| `source_match_percent` | Integer **0–100** heuristic: combines tier anchor (~62%) with the strongest retrieval score on linked evidence (~38%). **Not** a calibrated probability—use for bands and comparison, not guarantees. |
| `evidence_refs` | Chunk id, excerpt, optional `page_number`, and retrieval `score` / `score_band`. |

When `generation_mode` is `reasoning_gap`, the completed response also includes `gap_steps` with ordered prompts, placeholders, rubric hints, and evidence references.

### Create QA Session

**POST** `/qa/sessions`

Create a new QA session for a document.

#### Request Body

```json
{
  "file_id": "f137978b-951c-4e27-ae27-a32cca37b184",
  "filename": "document.pdf"
}
```

#### Response Example

```json
{
  "session_id": "qa_session_123",
  "file_id": "f137978b-951c-4e27-ae27-a32cca37b184",
  "filename": "document.pdf",
  "created_at": "2024-01-15T10:30:00Z",
  "message_count": 0
}
```

### Get QA Session

**GET** `/qa/sessions/{session_id}`

Get a specific QA session with all messages.

### Get Session Messages

**GET** `/qa/sessions/{session_id}/messages`

Get all messages for a specific QA session.

#### Response Example

```json
[
  {
    "message_id": "msg_1",
    "session_id": "qa_session_123",
    "role": "user",
    "content": "What is machine learning?",
    "timestamp": "2024-01-15T10:30:00Z"
  },
  {
    "message_id": "msg_2",
    "session_id": "qa_session_123",
    "role": "assistant",
    "content": "Machine learning is a subset of artificial intelligence...",
    "timestamp": "2024-01-15T10:30:05Z"
  }
]
```

### Get All QA Sessions

**GET** `/qa/sessions`

Get all active QA sessions.

### Delete QA Session

**DELETE** `/qa/sessions/{session_id}`

Delete a QA session.

---

## Quiz Generation

### Generate Quiz

**POST** `/quiz/generate`

Generate a quiz from an uploaded document.

#### Request Body

```json
{
  "file_id": "f137978b-951c-4e27-ae27-a32cca37b184",
  "filename": "document.pdf",
  "num_questions": 10,
  "difficulty": "medium",
  "question_types": ["multiple_choice", "true_false"],
  "mode": "standard"
}
```

`mode` accepts `standard`, `reasoning_gap`, or `ai_oversight`.

**Grading for `reasoning_gap` and `ai_oversight`:** When the quiz service runs with LLM enabled, each submitted short answer can be scored with a **model judge** (equivalent conceptual bridges for gaps; valid critique plus evidence anchoring for oversight). If the LLM is off or the judge call fails, scoring falls back to **deterministic heuristics** (keyword overlap, excerpt overlap, and simple citation markers). `question_results` always includes `review_note` and often `review_details` for the learner.

- **Reasoning gap — wrong answer:** `review_details` adds the **document logic path** (source sentence from metadata, rubric lines, gap steps) so feedback is not only “incorrect.”
- **AI oversight — human agency:** Critiques that cite a **specific page** (e.g. `page 5`, `p.12`) can earn a **score boost** and `human_agency_bonus_applied: true` on that item; aggregate feedback may mention how many responses showed that habit.

#### Response Example

```json
{
  "quiz_id": "quiz_123",
  "title": "Reasoning Gap Quiz on document.pdf",
  "file_id": "f137978b-951c-4e27-ae27-a32cca37b184",
  "filename": "document.pdf",
  "total_questions": 10,
  "total_points": 12,
  "difficulty": "medium",
  "mode": "reasoning_gap",
  "processing_time": 8.5
}
```

### Create Quiz Session

**POST** `/quiz/sessions`

Create a new quiz session.

#### Request Body

```json
{
  "quiz_id": "quiz_123",
  "user_name": "John Doe"
}
```

### Get Quiz Questions

**GET** `/quiz/{quiz_id}/questions`

Get quiz questions without correct answers (for user display).

#### Response Example

```json
[
  {
    "id": "q1",
    "question": "Complete the missing step in the reasoning from the document.",
    "mode": "reasoning_gap",
    "gap_prompt": "Machine learning models improve as they process more _____ training examples.",
    "gap_steps": [
      {
        "order": 1,
        "prompt": "Machine learning models improve as they process more _____ training examples.",
        "placeholder": "Fill the missing concept",
        "rubric_hint": "Recover the missing bridge from the source sentence, not outside intuition."
      }
    ],
    "grading_rubric": [
      "Names the missing concept or causal link from the document.",
      "Stays within the evidence instead of adding outside claims."
    ],
    "evidence_refs": [
      {
        "chunk_id": "derived-1",
        "support_tier": "high"
      }
    ]
  }
]
```

### Submit Quiz

**POST** `/quiz/submit`

Submit quiz answers and get results.

#### Request Body

```json
{
  "session_id": "quiz_session_123",
  "answers": {
    "q1": 0,
    "q2": 1,
    "q3": 2
  }
}
```

#### Response Example

```json
{
  "session_id": "quiz_session_123",
  "score": 85.0,
  "total_questions": 10,
  "correct_answers": 8,
  "question_results": [
    {
      "question_id": "q1",
      "user_answer": "labeled",
      "correct_answer": "labeled",
      "is_correct": true,
      "review_note": "Accepted equivalent intermediate reasoning.",
      "review_details": [
        "Equivalent reasoning is accepted when it preserves the document's causal link."
      ]
    }
  ]
}
```

### Get Quiz Session

**GET** `/quiz/sessions/{session_id}`

Get a specific quiz session.

### Get All Quiz Sessions

**GET** `/quiz/sessions`

Get all active quiz sessions.

### Delete Quiz Session

**DELETE** `/quiz/sessions/{session_id}`

Delete a quiz session.

---

## Flashcard Generation

### Generate Flashcards

**POST** `/flashcards/generate`

Generate flashcards from an uploaded document.

#### Request Body

```json
{
  "file_id": "f137978b-951c-4e27-ae27-a32cca37b184",
  "filename": "document.pdf",
  "num_cards": 20,
  "card_type": "question_answer"
}
```

#### Response Example

```json
{
  "flashcard_set_id": "flashcards_123",
  "file_id": "f137978b-951c-4e27-ae27-a32cca37b184",
  "filename": "document.pdf",
  "total_cards": 20,
  "processing_time": 12.5,
  "cards": [
    {
      "card_id": "card_1",
      "front": "What is machine learning?",
      "back": "Machine learning is a subset of artificial intelligence that enables computers to learn and improve from experience without being explicitly programmed.",
      "category": "definitions"
    }
  ]
}
```

---

## Health Checks

### Main Health Check

**GET** `/health`

Check the overall health of the backend service.

#### Response Example

```json
{
  "status": "healthy",
  "service": "scholar-backend"
}
```

### File Service Health

**GET** `/files/health`

Check the health of the file processing service.

### QA Service Health

**GET** `/qa/health`

Check the health of the QA service.

#### Response Example

```json
{
  "status": "healthy",
  "service": "qa-with-rag",
  "active_sessions": 5,
  "rag_integration": "enabled"
}
```

### Quiz Service Health

**GET** `/quiz/health`

Check the health of the quiz service.

#### Response Example

```json
{
  "status": "healthy",
  "service": "quiz-generation",
  "active_quizzes": 3,
  "active_sessions": 8,
  "llm_integration": "enabled"
}
```

### Flashcard Service Health

**GET** `/flashcards/health`

Check the health of the flashcard service.

---

## Error Handling

The API uses standard HTTP status codes and returns error responses in the following format:

```json
{
  "detail": "Error message description"
}
```

### Common Status Codes

- **200**: Success
- **400**: Bad Request - Invalid input parameters
- **404**: Not Found - Resource not found
- **500**: Internal Server Error - Server-side error

### Error Examples

#### 400 Bad Request
```json
{
  "detail": "Question cannot be empty"
}
```

#### 404 Not Found
```json
{
  "detail": "File not found"
}
```

#### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

---

## Rate Limiting

Currently, there are no rate limits implemented on the API endpoints.

---

## CORS

The API supports CORS for the following origins:
- `http://localhost:3000`
- `http://localhost:3001`

---

## Versioning

Current API version: `1.0.0`

The API version is included in the FastAPI application metadata and can be accessed via the OpenAPI documentation at `/docs`.

---

## OpenAPI Documentation

Interactive API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## Support

For issues or questions about the API, please refer to the project documentation or create an issue in the repository.
