# File management API routes
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query
from fastapi.responses import JSONResponse, FileResponse
from typing import List, Optional
import logging
import os

from ...models.file import FileUploadResponse, FileInfo, UploadError, RAGProcessingInfo
from ...services.document import DocumentService
from ...services.extractor import DocumentExtractor
from ...services.rag_pipeline import rag_pipeline_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/files", tags=["files"])

# Initialize document service
document_service = DocumentService()

@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    study_mode: Optional[str] = Query(None, description="Study mode: 'qa', 'quiz', or 'flashcards'")
):
    """
    Upload a document file (PDF, DOCX, PPTX, TXT) with conditional embedding processing
    """
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        if not DocumentExtractor.is_supported_format(file.filename):
            supported_formats = document_service.get_supported_formats()
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file format. Supported formats: {', '.join(supported_formats)}"
            )
        
        # Read file content
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Empty file")
        
        # Determine if embedding is needed based on study mode
        # QA mode needs embeddings for RAG, Quiz/Flashcard modes need content extraction but not embeddings
        enable_embedding = study_mode == "qa"
        
        if enable_embedding:
            # Process file through RAG pipeline for QA mode
            logger.info(f"Processing file {file.filename} with RAG pipeline for QA mode")
            result = await rag_pipeline_service.process_document_upload(
                content, 
                file.filename, 
                enable_embedding=True
            )
            
            if result['status'] == 'failed':
                raise HTTPException(status_code=500, detail=result.get('error', 'Processing failed'))
            
            # Convert to FileUploadResponse format
            upload_response = FileUploadResponse(
                message="File uploaded and processed successfully with RAG for QA",
                file_id=result['file_id'],
                filename=file.filename,
                size=result['document_processing']['file_size'],
                upload_time=result['upload_time'],
                content_summary=result['document_processing']['content_summary']
            )
            
            # Add RAG processing details to response
            upload_response.rag_processing = RAGProcessingInfo(
                processing_time_seconds=result['processing_time_seconds'],
                chunking=result['chunking'],
                embedding=result['embedding'],
                vector_storage=result['vector_storage']
            )
            
        else:
            # Process file without embedding for Quiz/Flashcard modes
            logger.info(f"Processing file {file.filename} without embedding for {study_mode} mode")
            result = await rag_pipeline_service.process_document_upload(
                content, 
                file.filename, 
                enable_embedding=False
            )
            
            if result['status'] == 'failed':
                raise HTTPException(status_code=500, detail=result.get('error', 'Processing failed'))
            
            # Convert to FileUploadResponse format
            mode_specific_message = {
                "quiz": "File uploaded successfully! You can now generate a quiz based on this document.",
                "flashcards": "File uploaded successfully! You can now generate flashcards based on this document."
            }.get(study_mode, f"File uploaded and processed successfully for {study_mode} mode")
            
            upload_response = FileUploadResponse(
                message=mode_specific_message,
                file_id=result['file_id'],
                filename=file.filename,
                size=result['document_processing']['file_size'],
                upload_time=result['upload_time'],
                content_summary=result['document_processing']['content_summary']
            )
            
            # Add basic processing details
            upload_response.rag_processing = RAGProcessingInfo(
                processing_time_seconds=result['processing_time_seconds'],
                chunking=result['chunking'],
                embedding={"enabled": False, "reason": f"Not needed for {study_mode} mode"},
                vector_storage={"enabled": False, "reason": f"Not needed for {study_mode} mode"}
            )
        
        logger.info(f"File uploaded successfully: {file.filename} (mode: {study_mode}, embedding: {enable_embedding})")
        return upload_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file {file.filename}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/upload-with-embedding", response_model=FileUploadResponse)
async def upload_file_with_embedding(
    file: UploadFile = File(...),
    enable_embedding: bool = Query(True, description="Enable embedding generation and vector storage")
):
    """
    Upload a document file with explicit embedding control (legacy endpoint)
    """
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        if not DocumentExtractor.is_supported_format(file.filename):
            supported_formats = document_service.get_supported_formats()
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file format. Supported formats: {', '.join(supported_formats)}"
            )
        
        # Read file content
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Empty file")
        
        # Process file through RAG pipeline
        result = await rag_pipeline_service.process_document_upload(
            content, 
            file.filename, 
            enable_embedding=enable_embedding
        )
        
        if result['status'] == 'failed':
            raise HTTPException(status_code=500, detail=result.get('error', 'Processing failed'))
        
        # Convert to FileUploadResponse format
        upload_response = FileUploadResponse(
            message="File uploaded and processed successfully",
            file_id=result['file_id'],
            filename=file.filename,
            size=result['document_processing']['file_size'],
            upload_time=result['upload_time'],
            content_summary=result['document_processing']['content_summary']
        )
        
        # Add RAG processing details to response
        upload_response.rag_processing = RAGProcessingInfo(
            processing_time_seconds=result['processing_time_seconds'],
            chunking=result['chunking'],
            embedding=result['embedding'],
            vector_storage=result['vector_storage']
        )
        
        logger.info(f"File uploaded successfully with explicit embedding control: {file.filename}")
        return upload_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file {file.filename}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/info/{file_id}", response_model=FileInfo)
async def get_file_info(file_id: str):
    """
    Get information about an uploaded file
    """
    try:
        file_info = await document_service.get_file_info(file_id)
        if not file_info:
            raise HTTPException(status_code=404, detail="File not found")
        return file_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting file info for {file_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{file_id}/text")
async def get_extracted_text(file_id: str):
    """
    Get extracted text content from an uploaded file
    """
    try:
        extracted_text = await document_service.get_extracted_text(file_id)
        if extracted_text is None:
            raise HTTPException(status_code=404, detail="Extracted text not found")
        return {"file_id": file_id, "extracted_text": extracted_text}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting extracted text for {file_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{file_id}/chunks")
async def get_document_chunks(file_id: str):
    """
    Get chunks for a document (if it was chunked due to large size)
    """
    try:
        chunks = await document_service.get_document_chunks(file_id)
        if chunks is None:
            raise HTTPException(status_code=404, detail="Document chunks not found")
        return {
            "file_id": file_id,
            "chunks": chunks,
            "total_chunks": len(chunks)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document chunks for {file_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{file_id}/chunks/{chunk_id}")
async def get_chunk_by_id(file_id: str, chunk_id: str):
    """
    Get a specific chunk by its ID
    """
    try:
        chunk = await document_service.get_chunk_by_id(file_id, chunk_id)
        if chunk is None:
            raise HTTPException(status_code=404, detail="Chunk not found")
        return {
            "file_id": file_id,
            "chunk_id": chunk_id,
            "chunk": chunk
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chunk {chunk_id} for file {file_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/{file_id}")
async def delete_file(file_id: str):
    """
    Delete an uploaded file and its embeddings
    """
    try:
        # Use RAG pipeline to delete both file and embeddings
        result = await rag_pipeline_service.delete_document(file_id)
        
        if not result['success']:
            raise HTTPException(status_code=404, detail="File not found or deletion failed")
        
        return {
            "message": "File and embeddings deleted successfully",
            "file_id": file_id,
            "vector_store_deleted": result['vector_store_deleted'],
            "document_deleted": result['document_deleted']
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting file {file_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/formats", response_model=List[str])
async def get_supported_formats():
    """
    Get list of supported file formats
    """
    return document_service.get_supported_formats()

@router.get("/search")
async def search_documents(
    query: str = Query(..., description="Search query"),
    k: int = Query(5, description="Number of results to return"),
    file_id: Optional[str] = Query(None, description="Search within specific file only")
):
    """
    Search documents using vector similarity (only works for files processed with embeddings)
    """
    try:
        result = await rag_pipeline_service.search_documents(query, k, file_id)
        
        if not result['success']:
            raise HTTPException(status_code=500, detail=result.get('error', 'Search failed'))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching documents: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/stats")
async def get_processing_stats():
    """
    Get processing statistics and system health
    """
    try:
        stats = await rag_pipeline_service.get_processing_stats()
        
        if 'error' in stats:
            raise HTTPException(status_code=500, detail=stats['error'])
        
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting processing stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{file_id}/content")
async def get_document_content(file_id: str):
    """
    Get document content with structure information for highlighting
    """
    try:
        content_data = await document_service.get_document_content_with_structure(file_id)
        if not content_data:
            raise HTTPException(status_code=404, detail="Document content not found")
        
        return content_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document content for {file_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{file_id}/file")
async def get_document_file(file_id: str):
    """
    Get the actual document file (PDF, DOCX, etc.) for viewing
    """
    try:
        logger.info(f"Requesting file: {file_id}")
        file_info = await document_service.get_file_info(file_id)
        if not file_info:
            logger.error(f"File info not found for: {file_id}")
            raise HTTPException(status_code=404, detail="File not found")
        
        # Construct file path - check uploads directory
        uploads_dir = "uploads"
        file_path = os.path.join(uploads_dir, f"{file_id}.pdf")
        logger.info(f"Trying file path: {file_path}")
        
        # Check if PDF exists, otherwise try other formats
        if not os.path.exists(file_path):
            # Try other common formats
            for ext in ['.docx', '.pptx', '.txt']:
                alt_path = os.path.join(uploads_dir, f"{file_id}{ext}")
                if os.path.exists(alt_path):
                    file_path = alt_path
                    break
        
        # If still not found, try with absolute path
        if not os.path.exists(file_path):
            # Try with absolute path from current working directory
            current_dir = os.getcwd()
            absolute_uploads_dir = os.path.join(current_dir, "uploads")
            file_path = os.path.join(absolute_uploads_dir, f"{file_id}.pdf")
            
            if not os.path.exists(file_path):
                # Try other formats with absolute path
                for ext in ['.docx', '.pptx', '.txt']:
                    alt_path = os.path.join(absolute_uploads_dir, f"{file_id}{ext}")
                    if os.path.exists(alt_path):
                        file_path = alt_path
                        break
        
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_id}. Tried paths: {uploads_dir}/{file_id}.pdf, {absolute_uploads_dir}/{file_id}.pdf")
            raise HTTPException(status_code=404, detail=f"File not found on disk: {file_id}")
        
        # Determine media type based on file extension
        file_ext = os.path.splitext(file_path)[1].lower()
        media_types = {
            '.pdf': 'application/pdf',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            '.txt': 'text/plain'
        }
        
        media_type = media_types.get(file_ext, 'application/octet-stream')
        
        return FileResponse(
            path=file_path,
            media_type=media_type,
            filename=file_info.filename if hasattr(file_info, 'filename') else f"{file_id}{file_ext}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document file for {file_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {"status": "healthy", "service": "file-upload-with-conditional-rag"}

@router.get("/test-file/{file_id}")
async def test_file_exists(file_id: str):
    """
    Test endpoint to check if a file exists
    """
    try:
        # Check relative path
        relative_path = os.path.join("uploads", f"{file_id}.pdf")
        relative_exists = os.path.exists(relative_path)
        
        # Check absolute path
        current_dir = os.getcwd()
        absolute_path = os.path.join(current_dir, "uploads", f"{file_id}.pdf")
        absolute_exists = os.path.exists(absolute_path)
        
        return {
            "file_id": file_id,
            "current_dir": current_dir,
            "relative_path": relative_path,
            "relative_exists": relative_exists,
            "absolute_path": absolute_path,
            "absolute_exists": absolute_exists
        }
    except Exception as e:
        return {"error": str(e)}
