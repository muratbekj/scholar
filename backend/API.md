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
  "session_id": "optional_session_id"
}
```

#### Response Example

```json
{
  "answer": "Machine learning is a subset of artificial intelligence that enables computers to learn and improve from experience without being explicitly programmed...",
  "question": "What is machine learning?",
  "file_id": "f137978b-951c-4e27-ae27-a32cca37b184",
  "session_id": "qa_session_123",
  "processing_time": 2.5,
  "sources": [
    {
      "content": "Machine learning is a subset of AI...",
      "similarity_score": 0.95
    }
  ]
}
```

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
  "question_types": ["multiple_choice", "true_false"]
}
```

#### Response Example

```json
{
  "quiz_id": "quiz_123",
  "file_id": "f137978b-951c-4e27-ae27-a32cca37b184",
  "filename": "document.pdf",
  "num_questions": 10,
  "difficulty": "medium",
  "processing_time": 8.5,
  "questions": [
    {
      "question_id": "q1",
      "question": "What is machine learning?",
      "options": [
        "A subset of artificial intelligence",
        "A programming language",
        "A database system",
        "A web framework"
      ],
      "correct_answer": 0,
      "explanation": "Machine learning is indeed a subset of artificial intelligence..."
    }
  ]
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
    "question_id": "q1",
    "question": "What is machine learning?",
    "options": [
      "A subset of artificial intelligence",
      "A programming language",
      "A database system",
      "A web framework"
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
  "incorrect_answers": 2,
  "results": [
    {
      "question_id": "q1",
      "user_answer": 0,
      "correct_answer": 0,
      "is_correct": true,
      "explanation": "Correct! Machine learning is a subset of AI."
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
