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
npm install
```

## 🚀 Usage

### Starting the Application

#### Development Mode
```bash
# Terminal 1: Start backend
cd backend && uvicorn app.main:app --reload --port 8000

# Terminal 2: Start frontend
cd frontend && npm run electron:dev
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
```bash
# Backend configuration
EMBEDDING_MODEL=nomic-embed-text
CHROMA_PERSIST_DIR=./chroma_db
LARGE_DOCUMENT_THRESHOLD=5000
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
```

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
