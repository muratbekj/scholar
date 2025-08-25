# Scholar Application Architecture Summary

## Overview

The Scholar application implements a **conditional RAG (Retrieval-Augmented Generation) system** where:
- **QA Feature**: Uses full RAG pipeline with embeddings and vector search
- **Quiz Feature**: Uses document text extraction only (no embeddings)
- **Flashcard Feature**: Uses document text extraction only (no embeddings)

## Architecture Flow

```
User Upload → Study Mode Selection → Conditional Processing → Feature-Specific Services
     ↓              ↓                        ↓                        ↓
File Upload → QA/Quiz/Flashcards → RAG Pipeline (QA only) → QA/Quiz/Flashcard Services
```

## Detailed Flow by Study Mode

### 1. QA Mode (RAG Enabled)
```
Upload → study_mode="qa" → RAG Pipeline → QA Service
  ↓           ↓                ↓              ↓
File → Embedding=True → Text+Chunks+Embeddings → Vector Search + LLM
```

**Components Used:**
- `DocumentService`: Text extraction and chunking
- `EmbeddingService`: LangChain Ollama embeddings
- `VectorStoreService`: ChromaDB storage
- `RAGPipelineService`: Orchestration
- `QAService`: Question answering with RAG

### 2. Quiz Mode (RAG Disabled)
```
Upload → study_mode="quiz" → Basic Processing → Quiz Service
  ↓           ↓                ↓              ↓
File → Embedding=False → Text extraction only → Quiz generation
```

**Components Used:**
- `DocumentService`: Text extraction only
- `QuizService`: Quiz generation (to be implemented)

### 3. Flashcard Mode (RAG Disabled)
```
Upload → study_mode="flashcards" → Basic Processing → Flashcard Service
  ↓           ↓                ↓              ↓
File → Embedding=False → Text extraction only → Flashcard generation
```

**Components Used:**
- `DocumentService`: Text extraction only
- `FlashcardService`: Flashcard generation (to be implemented)

## API Endpoints

### File Upload (Conditional Processing)
```http
POST /files/upload?study_mode={qa|quiz|flashcards}
```

**Behavior:**
- `study_mode=qa`: Full RAG processing with embeddings
- `study_mode=quiz`: Text extraction only
- `study_mode=flashcards`: Text extraction only

### QA Endpoints (RAG-Enabled)
```http
POST /qa/ask                    # Ask questions with RAG
POST /qa/sessions               # Create QA session
GET  /qa/sessions/{session_id}  # Get session with messages
GET  /qa/search                 # Vector similarity search
```

### File Management (Universal)
```http
GET  /files/info/{file_id}      # Get file information
GET  /files/{file_id}/text      # Get extracted text
GET  /files/{file_id}/chunks    # Get document chunks
DELETE /files/{file_id}         # Delete file and embeddings
```

## Service Architecture

### Core Services

#### 1. DocumentService
- **Purpose**: Universal text extraction and chunking
- **Used by**: All study modes
- **Features**: PDF, DOCX, PPTX, TXT support

#### 2. RAGPipelineService
- **Purpose**: Orchestrates RAG processing
- **Used by**: QA mode only
- **Features**: Embedding generation, vector storage

#### 3. QAService
- **Purpose**: Question answering with RAG
- **Used by**: QA mode only
- **Features**: Session management, RAG integration

#### 4. EmbeddingService
- **Purpose**: LangChain Ollama embeddings
- **Used by**: QA mode only
- **Features**: Batch processing, retry logic

#### 5. VectorStoreService
- **Purpose**: ChromaDB vector storage
- **Used by**: QA mode only
- **Features**: Similarity search, metadata management

## Data Flow Examples

### Example 1: QA Mode
```
1. User uploads "machine_learning.pdf" with study_mode="qa"
2. File processed through RAG pipeline:
   - Text extracted from PDF
   - Document chunked into 15 chunks
   - 15 embeddings generated using nomic-embed-text
   - Embeddings stored in ChromaDB
3. User asks: "What is supervised learning?"
4. QA service:
   - Searches vector database for relevant chunks
   - Finds 3 relevant chunks with similarity scores
   - Generates contextual answer
   - Returns answer with confidence score
```

### Example 2: Quiz Mode
```
1. User uploads "machine_learning.pdf" with study_mode="quiz"
2. File processed through basic pipeline:
   - Text extracted from PDF
   - Document chunked (for quiz generation)
   - No embeddings generated
   - No vector storage
3. Quiz service generates questions from extracted text
4. User takes quiz with generated questions
```

## Benefits of This Architecture

### 1. Resource Efficiency
- **QA Mode**: Full RAG processing when needed
- **Quiz/Flashcard**: Lightweight processing for faster uploads

### 2. Cost Optimization
- Embeddings only generated for QA mode
- Vector storage only used when necessary

### 3. Performance
- Faster uploads for Quiz/Flashcard modes
- RAG processing only when required

### 4. Scalability
- Different processing paths for different use cases
- Easy to add new study modes

## Configuration

### Environment Variables
```bash
# Embedding Model
EMBEDDING_MODEL=nomic-embed-text

# Vector Store
CHROMA_PERSIST_DIR=./chroma_db

# Processing Thresholds
LARGE_DOCUMENT_THRESHOLD=5000
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
```

### Service Configuration
```python
# QA Mode (Full RAG)
embedding_service = EmbeddingService(
    model_name="nomic-embed-text",
    batch_size=10,
    max_retries=3
)

# Quiz/Flashcard Mode (No RAG)
document_service = DocumentService(
    upload_dir="uploads",
    large_document_threshold=5000,
    chunk_size=1000,
    chunk_overlap=200
)
```

## Future Enhancements

### 1. Hybrid Processing
- Allow users to enable RAG for Quiz/Flashcard modes
- Configurable processing options

### 2. Caching
- Cache embeddings for frequently used documents
- Cache search results for common queries

### 3. Advanced Features
- Multi-document QA sessions
- Cross-document search
- Document comparison features

### 4. Performance Optimizations
- Async processing for large documents
- Progressive loading for long documents
- Background embedding generation

## Monitoring and Analytics

### Metrics to Track
- Processing time by study mode
- Embedding generation success rate
- Vector search performance
- User engagement by mode

### Health Checks
- Embedding service availability
- Vector store connectivity
- Document processing pipeline status

This architecture provides a flexible, efficient, and scalable solution that optimizes resources while providing powerful RAG capabilities specifically for the QA feature.
