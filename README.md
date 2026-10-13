# Scholar - AI-Powered Desktop Study Assistant

An intelligent desktop application that transforms your study materials into interactive learning experiences using AI. Scholar works completely offline using your own documents and provides three powerful study modes: Q&A Chat, Quiz Generation, and Flashcard Creation.

## 🚀 Features

### 📚 Multi-Modal Study Tools
- **Q&A Chat**: Ask questions about your documents and get AI-powered answers using RAG (Retrieval-Augmented Generation)
- **Quiz Generation**: Automatically create quizzes from your study materials to test your knowledge
- **Flashcard Creation**: Generate interactive flashcards for effective memorization

### 🔒 Privacy-First & Offline
- **Complete Offline Operation**: All processing happens locally on your machine
- **No Cloud Dependencies**: Your documents never leave your computer
- **Local AI Models**: Uses Ollama for local LLM processing and embeddings

### 📄 Document Support
- **Multiple Formats**: PDF, DOCX, PPTX, and TXT files
- **Smart Processing**: Automatic text extraction and intelligent chunking
- **Large Document Handling**: Efficient processing of documents of any size

### 🎯 Intelligent Learning
- **RAG-Powered Q&A**: Advanced retrieval-augmented generation for accurate answers
- **Context-Aware Responses**: AI understands your document context
- **Session Management**: Save and resume study sessions
- **Progress Tracking**: Monitor your learning progress

## 🏗️ Architecture

Scholar is built with a modern, scalable architecture:

### Frontend (Next.js + Electron)
- **Next.js 14**: React-based frontend with TypeScript
- **Electron**: Cross-platform desktop application wrapper
- **Tailwind CSS**: Modern, responsive UI design
- **Radix UI**: Accessible component library

### Backend (FastAPI + Python)
- **FastAPI**: High-performance Python web framework
- **LangChain**: AI/LLM orchestration framework
- **ChromaDB**: Local vector database for embeddings
- **Ollama**: Local LLM inference

### Key Services
- **Document Service**: Text extraction and processing
- **Embedding Service**: Vector embeddings using nomic-embed-text
- **Vector Store Service**: ChromaDB integration for similarity search
- **RAG Pipeline Service**: End-to-end document processing
- **QA Service**: Question answering with RAG
- **Quiz Service**: Quiz generation from documents
- **Flashcard Service**: Flashcard creation

## 📦 Installation

### Prerequisites
- **Node.js 18+** and **npm**
- **Python 3.13+** and **uv**
- **Ollama** with `nomic-embed-text` model

### 1. Install Ollama
```bash
# Download from https://ollama.ai/download
```

### 2. Clone the Repository
```bash
git clone https://github.com/yourusername/scholar.git
cd scholar
```

### 3. Setup Backend
```bash
cd backend

# Install dependencies with uv
uv sync
```

### 4. Setup Frontend
```bash
cd frontend

# Install dependencies
npm install
```

### 5. Setup Electron (Desktop App)
```bash
cd electron

# Install dependencies
bun install
```

## 🚀 Usage

### Starting the Application

#### Development Mode
```bash
# Terminal 1: Start backend
cd backend && uv run uvicorn app.main:app --reload

# Terminal 2: Start frontend
cd frontend && bun run electron:dev
```

### Using Scholar

1. **Upload a Document**
   - Drag and drop or click to upload your study material
   - Supported formats: PDF, DOCX, PPTX, TXT

2. **Choose Study Mode**
   - **Q&A Chat**: Ask questions about your document
   - **Quiz**: Generate and take quizzes
   - **Flashcards**: Create interactive flashcards

3. **Start Learning**
   - Each mode provides a unique learning experience
   - Save sessions for later review
   - Track your progress over time

## 🔧 Configuration

### Environment Variables
All settings are optional. With none set, Scholar runs fully locally on Ollama + ChromaDB.

| Variable | Default | Meaning |
|---|---|---|
| `LLM_PROVIDER` | `ollama` | `ollama` or `vertex` |
| `OLLAMA_LLM_MODEL` | `gpt-oss:20b` | Ollama chat model |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | Ollama embedding model |
| `VERTEX_LLM_MODEL` | none | required for `vertex`, e.g. a current Gemini Flash model from the [Vertex model list](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/model-versions) |
| `VERTEX_EMBED_MODEL` | none | required for `vertex`, e.g. `gemini-embedding-001` |
| `VERTEX_THINKING_BUDGET` | model default | optional thinking-token budget for Gemini |
| `GOOGLE_CLOUD_PROJECT` | none | required for `vertex` |
| `GOOGLE_CLOUD_LOCATION` | `global` | Vertex location; Gemini 3.x models are served only from `global` |
| `CHROMA_DIR` | `./chroma_db` | Chroma storage directory |
| `UPLOAD_DIR` | `uploads` | uploaded files and extracted text |
| `CORS_ORIGINS` | localhost:3000/3001, 127.0.0.1:3000/3001, `null` | comma separated; `*` is not allowed |

### Running with Vertex AI (Gemini) locally

```bash
gcloud auth application-default login          # Vertex uses ADC; never set GOOGLE_API_KEY / GEMINI_API_KEY
cd backend && uv sync --extra cloud
LLM_PROVIDER=vertex GOOGLE_CLOUD_PROJECT=your-project \
VERTEX_LLM_MODEL=gemini-3.8-flash VERTEX_EMBED_MODEL=gemini-embedding-001 \
CHROMA_DIR=./chroma_db_vertex uv run uvicorn app.main:app --reload
```

Gemini 3.x models return 404 from regional locations such as `us-central1`, so keep the default `global`.
When a model call fails, the app falls back to non-AI heuristic answers and still returns 200,
so check the server log for `Error calling model` if output looks generic.

Use a separate `CHROMA_DIR` per provider: Vertex and Ollama embeddings have different
dimensions and must never share a collection.

### Ollama Configuration
```bash
# Ensure Ollama is running
ollama serve

# Pull required models
ollama pull nomic-embed-text
ollama pull gpt-oss:20b  # or your preferred LLM
```

## 🧪 Testing

### Backend Tests
```bash
cd backend
pytest
```

### Frontend Tests
```bash
cd frontend
npm test
```

## 📁 Project Structure

```
scholar/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/routes/     # API endpoints
│   │   ├── services/       # Business logic
│   │   ├── models/         # Data models
│   │   └── core/           # Configuration
│   ├── chroma_db/          # Vector database
│   └── uploads/            # Document storage
├── frontend/               # Next.js frontend
│   ├── app/               # App router pages
│   ├── components/        # React components
│   └── lib/               # Utilities and hooks
├── electron/              # Desktop app wrapper
│   ├── main.js           # Main process
│   └── preload.js        # Preload script
└── README.md
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the Apache License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **LangChain** for AI/LLM orchestration
- **FastApi** for backend framework
- **ChromaDB** for vector storage
- **Ollama** for local LLM inference
- **Next.js** for the frontend framework
- **Electron** for desktop app capabilities

## 🔮 Roadmap

- [ ] Multi-document Q&A sessions
- [ ] Advanced quiz customization
- [ ] Spaced repetition for flashcards
- [ ] Export study materials
- [ ] Mobile companion app
- [ ] Collaborative study sessions
- [ ] Advanced analytics and insights

---

**Scholar** - Transform your study materials into intelligent learning experiences. 📚✨
