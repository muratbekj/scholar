# File management API routes
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import List
import logging

from ...models.file import FileUploadResponse, FileInfo, UploadError
from ...services.document import DocumentService
from ...services.extractor import DocumentExtractor

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/files", tags=["files"])

# Initialize document service
document_service = DocumentService()

@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a document file (PDF, DOCX, PPTX, TXT)
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
        
        # Process file
        result = await document_service.process_upload(content, file.filename)
        
        logger.info(f"File uploaded successfully: {file.filename}")
        return result
        
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
    Delete an uploaded file
    """
    try:
        success = await document_service.delete_file(file_id)
        if not success:
            raise HTTPException(status_code=404, detail="File not found")
        
        return {"message": "File deleted successfully"}
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

@router.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {"status": "healthy", "service": "file-upload"}
