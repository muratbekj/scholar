# Phase 1: File Upload Integration

## Overview
This phase connects the frontend file upload functionality to the backend API, enabling real file processing with RAG pipeline integration.

## What's Implemented

### 1. API Service Layer (`lib/api.ts`)
- Centralized API communication with TypeScript interfaces
- File upload with study mode selection
- QA session management
- Error handling and type safety

### 2. File Upload Hook (`lib/hooks/useFileUpload.ts`)
- React hook for managing upload state
- Progress tracking and error handling
- Integration with backend upload endpoint

### 3. Enhanced UI Components
- Loading component with progress bar
- Error states with retry functionality
- Success states with processing details
- Real-time upload feedback

### 4. Backend Integration
- File upload to `/files/upload` endpoint
- Study mode parameter (`qa`, `quiz`, `flashcards`)
- RAG processing for QA mode
- Processing statistics display

## Key Features

### File Upload Flow
1. User selects file (drag & drop or browse)
2. User chooses study mode
3. File uploads to backend with study mode parameter
4. Backend processes file (with/without RAG based on mode)
5. Frontend displays processing results and success state

### Study Mode Handling
- **QA Mode**: Enables RAG processing (chunking, embedding, vector storage)
- **Quiz Mode**: Basic processing without embeddings
- **Flashcard Mode**: Basic processing without embeddings

### Error Handling
- Network errors with retry options
- File format validation
- Processing failures with detailed error messages
- Graceful fallbacks

## Testing the Integration

### Prerequisites
1. Backend server running on `http://localhost:8000`
2. Frontend development server running on `http://localhost:3000`

### Test Steps
1. Start the backend server:
   ```bash
   cd backend
   source .venv/bin/activate
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. Start the frontend server:
   ```bash
   cd frontend
   npm run dev
   ```

3. Test the integration:
   - Open `http://localhost:3000`
   - Use the API Connection Test component to verify backend connectivity
   - Upload a PDF, DOCX, PPTX, or TXT file
   - Choose a study mode and observe the upload process
   - Verify processing details are displayed for QA mode

### Expected Behavior
- **QA Mode**: Shows processing time, chunks created, and embedding status
- **Quiz/Flashcard Mode**: Shows basic processing without embedding details
- **Error Handling**: Displays meaningful error messages with retry options
- **Success State**: Shows file details and ready-to-study options

## API Endpoints Used

- `POST /files/upload` - File upload with study mode
- `GET /health` - Backend health check
- `POST /qa/sessions` - Create QA session (Phase 2)
- `POST /qa/ask` - Ask questions (Phase 2)

## Next Steps (Phase 2)
- QA session creation and management
- Real-time chat interface with AI responses
- Session persistence and history
- Enhanced error handling and retry mechanisms

## Troubleshooting

### Common Issues
1. **Backend not running**: Check if uvicorn server is started on port 8000
2. **CORS errors**: Verify CORS configuration in backend/main.py
3. **File upload fails**: Check file format and size limits
4. **Processing errors**: Check backend logs for detailed error messages

### Debug Information
- API base URL: `http://localhost:8000` (configurable via `NEXT_PUBLIC_API_URL`)
- Supported file formats: PDF, DOCX, PPTX, TXT
- Maximum file size: Backend configuration dependent
