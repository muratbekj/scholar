# RAG Pipeline Implementation

This document describes the complete RAG (Retrieval-Augmented Generation) pipeline implementation for the Scholar application.

## Overview

The RAG pipeline processes document uploads through the following stages:
1. **Document Upload & Validation**
2. **Text Extraction**
3. **Document Chunking** (if needed)
4. **Embedding Generation**
5. **Vector Storage**
6. **Search & Retrieval**

## Architecture

### Core Services

#### 1. EmbeddingService (`app/services/embedding.py`)
- **Purpose**: Generates embeddings using LangChain Ollama
- **Model**: `nomic-embed-text`
- **Features**:
  - Batch processing with configurable batch size
  - Retry logic with exponential backoff
  - Error handling and validation
  - Async processing for better performance

#### 2. VectorStoreService (`app/services/vector_store.py`)
- **Purpose**: Manages vector storage using ChromaDB
- **Features**:
  - Document storage with rich metadata
  - Similarity search capabilities
  - File-based organization
  - Collection statistics and health monitoring

#### 3. RAGPipelineService (`app/services/rag_pipeline.py`)
- **Purpose**: Orchestrates the complete document processing workflow
- **Features**:
  - End-to-end pipeline management
  - Progress tracking and error recovery
  - Integration with all other services
  - Comprehensive result reporting

### Data Flow

```
User Upload → DocumentService → TextChunkingService → EmbeddingService → VectorStoreService → ChromaDB
     ↓              ↓                    ↓                    ↓                    ↓
File Storage → Text Extraction → Chunk Generation → Vector Creation → Vector Storage
```

## API Endpoints

### Enhanced Upload Endpoint
```http
POST /files/upload
Content-Type: multipart/form-data

Parameters:
- file: UploadFile (required)
- enable_embedding: bool (optional, default: true)
```

**Response includes:**
- File processing results
- Chunking information
- Embedding statistics
- Vector storage status
- Processing time

### Search Endpoint
```http
GET /files/search?query={search_query}&k={num_results}&file_id={optional_file_id}
```

**Features:**
- Vector similarity search
- Optional file-specific search
- Configurable result count
- Rich metadata in results

### Statistics Endpoint
```http
GET /files/stats
```

**Returns:**
- Vector store statistics
- Embedding service health
- Collection information
- System status

## Configuration

### Embedding Service
```python
embedding_service = EmbeddingService(
    model_name="nomic-embed-text",
    batch_size=10,
    max_retries=3,
    retry_delay=1.0
)
```

### Vector Store Service
```python
vector_store_service = VectorStoreService(
    persist_directory="./chroma_db",
    embedding_model="nomic-embed-text",
    collection_name="documents"
)
```

### Document Service
```python
document_service = DocumentService(
    upload_dir="uploads",
    large_document_threshold=5000,  # characters
    chunk_size=1000,
    chunk_overlap=200
)
```

## Usage Examples

### 1. Upload Document with Embedding
```python
# Using the API
import requests

files = {'file': open('document.pdf', 'rb')}
data = {'enable_embedding': 'true'}

response = requests.post('http://localhost:8000/files/upload', 
                        files=files, data=data)
result = response.json()

print(f"Processing time: {result['rag_processing']['processing_time_seconds']}s")
print(f"Chunks created: {result['rag_processing']['chunking']['total_chunks']}")
print(f"Embeddings generated: {result['rag_processing']['embedding']['successful_embeddings']}")
```

### 2. Search Documents
```python
# Search across all documents
response = requests.get('http://localhost:8000/files/search', 
                       params={'query': 'machine learning', 'k': 5})
results = response.json()

for result in results['results']:
    print(f"Score: {result['similarity_score']}")
    print(f"Content: {result['content'][:100]}...")
    print(f"File: {result['metadata']['file_id']}")
```

### 3. Search Within Specific File
```python
# Search within a specific document
response = requests.get('http://localhost:8000/files/search', 
                       params={'query': 'specific topic', 
                               'file_id': 'your_file_id', 
                               'k': 3})
```

## Testing

Run the test script to verify the implementation:
```bash
cd backend
python test_rag_pipeline.py
```

The test script will:
1. Check service health
2. Process a sample document
3. Test embedding generation
4. Verify vector storage
5. Test search functionality
6. Display processing statistics

## Error Handling

The pipeline includes comprehensive error handling:

### Embedding Failures
- Automatic retry with exponential backoff
- Graceful degradation (continues with successful embeddings)
- Detailed error reporting

### Vector Store Issues
- Connection error handling
- Storage space monitoring
- Data integrity checks

### Document Processing
- Format validation
- Size limits enforcement
- Content extraction fallbacks

## Performance Considerations

### Batch Processing
- Embeddings are processed in configurable batches
- Reduces API calls and improves throughput
- Memory usage optimization

### Async Operations
- All I/O operations are asynchronous
- Concurrent processing where possible
- Non-blocking API responses

### Storage Optimization
- Efficient metadata storage
- Indexed searches for fast retrieval
- Configurable chunk sizes

## Monitoring

### Health Checks
- Embedding service validation
- Vector store connectivity
- Model availability checks

### Statistics
- Processing time metrics
- Success/failure rates
- Storage usage statistics
- Search performance metrics

## Dependencies

### Required Packages
- `langchain>=0.3.27`
- `langchain-ollama>=0.3.7`
- `langchain-community` (for ChromaDB integration)
- `chromadb>=1.0.20`

### External Services
- Ollama server running with `nomic-embed-text` model
- Sufficient disk space for ChromaDB storage

## Troubleshooting

### Common Issues

1. **Embedding Model Not Available**
   - Ensure Ollama is running
   - Pull the model: `ollama pull nomic-embed-text`

2. **ChromaDB Connection Issues**
   - Check disk space
   - Verify directory permissions
   - Restart the application

3. **Slow Processing**
   - Increase batch size for embeddings
   - Reduce chunk overlap
   - Monitor system resources

### Debug Mode
Enable detailed logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Future Enhancements

1. **Multiple Embedding Models**
   - Support for different embedding models
   - Model comparison and selection

2. **Advanced Chunking**
   - Semantic chunking strategies
   - Hierarchical document structure

3. **Caching Layer**
   - Embedding result caching
   - Search result caching

4. **Real-time Processing**
   - WebSocket updates for progress
   - Streaming responses

5. **Advanced Search**
   - Hybrid search (vector + keyword)
   - Filtering and faceting
   - Search result ranking
