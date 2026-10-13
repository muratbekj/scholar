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
| `VECTOR_BACKEND` | `chroma` | `chroma` or `pgvector` |
| `DATABASE_URL` | none | SQLAlchemy psycopg URL; required for `pgvector` or `SESSION_BACKEND=postgres` |
| `STORAGE_BACKEND` | `local` | `local` (UPLOAD_DIR) or `gcs` |
| `GCS_BUCKET` | none | required for `gcs` |
| `SESSION_BACKEND` | `memory` | `memory` or `postgres` (Q&A and quiz sessions) |
| `MAX_UPLOAD_MB` | `20` | cloud mode only; larger uploads get 413 |
| `MAX_CHUNKS_PER_DOC` | `500` | cloud mode only; larger documents get 413 |
| `RATE_LIMIT_PER_MIN` | `20` | cloud mode only; LLM/embedding calls per client per instance, then 429 |
| `RATE_LIMIT_GLOBAL_PER_MIN` | `100` | cloud mode only; LLM/embedding calls per instance across all clients (client ids are self-chosen) |
| `MAX_TEXT_CHARS` | `500000` | cloud mode only; documents with more extracted text get 413 (bounds LLM prompt size) |

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

## ☁️ Deploying to Google Cloud

The backend runs on Cloud Run with Vertex AI (Gemini), Cloud SQL Postgres + pgvector (vectors and
sessions) and Cloud Storage (uploads). Selecting any of these turns on **cloud mode**: every request
must send `X-Client-Id` (a UUID; the frontend sends one automatically) and each client only sees its
own documents and sessions. This is not authentication; Firebase Auth or IAP is the next step.

### Cloud Run environment

| Variable | Value |
|---|---|
| `LLM_PROVIDER` | `vertex` |
| `VERTEX_LLM_MODEL` | e.g. `gemini-3.8-flash` |
| `VERTEX_EMBED_MODEL` | `gemini-embedding-001` |
| `GOOGLE_CLOUD_PROJECT` | your project id (`GOOGLE_CLOUD_LOCATION` defaults to `global`) |
| `VECTOR_BACKEND` / `SESSION_BACKEND` | `pgvector` / `postgres` |
| `DATABASE_URL` | from Secret Manager (below) |
| `STORAGE_BACKEND` / `GCS_BUCKET` | `gcs` / your bucket |
| `CORS_ORIGINS` | your frontend URL(s); set it explicitly in the cloud |

Never set `GOOGLE_API_KEY` or `GEMINI_API_KEY`: Vertex uses the service account (startup fails if they are set).

### One-time setup

```bash
gcloud config set project PROJECT_ID
gcloud services enable run.googleapis.com aiplatform.googleapis.com sqladmin.googleapis.com \
  storage.googleapis.com secretmanager.googleapis.com cloudbuild.googleapis.com
# create a budget alert first: Billing > Budgets & alerts

# Postgres + pgvector (smallest tier)
gcloud sql instances create scholar-db --database-version=POSTGRES_16 --tier=db-f1-micro --region=us-central1
gcloud sql databases create scholar --instance=scholar-db
gcloud sql users create scholar --instance=scholar-db --password=CHOOSE_ONE
# connect once (e.g. gcloud sql connect scholar-db --user=postgres) and run: CREATE EXTENSION vector;
# the app creates its tables (langchain_pg_*, sessions) on first start

# uploads bucket
gcloud storage buckets create gs://PROJECT_ID-scholar-uploads --location=us-central1

# database URL as a secret (Cloud Run connects over the Cloud SQL unix socket)
printf 'postgresql+psycopg://scholar:PASSWORD@/scholar?host=/cloudsql/PROJECT_ID:us-central1:scholar-db' | \
  gcloud secrets create scholar-db-url --data-file=-

# permissions for the Cloud Run runtime service account
for r in roles/aiplatform.user roles/cloudsql.client roles/storage.objectAdmin roles/secretmanager.secretAccessor; do
  gcloud projects add-iam-policy-binding PROJECT_ID --member=serviceAccount:SA_EMAIL --role=$r
done
```

### Deploy

```bash
gcloud run deploy scholar-api --source ./backend --region us-central1 \
  --set-env-vars LLM_PROVIDER=vertex,VERTEX_LLM_MODEL=gemini-3.8-flash,VERTEX_EMBED_MODEL=gemini-embedding-001,GOOGLE_CLOUD_PROJECT=PROJECT_ID,VECTOR_BACKEND=pgvector,SESSION_BACKEND=postgres,STORAGE_BACKEND=gcs,GCS_BUCKET=PROJECT_ID-scholar-uploads,CORS_ORIGINS=https://YOUR_FRONTEND_URL \
  --add-cloudsql-instances PROJECT_ID:us-central1:scholar-db \
  --set-secrets DATABASE_URL=scholar-db-url:latest \
  --min-instances 0 --max-instances 2
```

Frontend: deploy `frontend/` (e.g. to Vercel) with `NEXT_PUBLIC_API_URL` set to the Cloud Run URL,
then put that frontend URL in `CORS_ORIGINS` and redeploy the backend.

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
