# File model for storing uploaded document metadata
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

class FileUploadResponse(BaseModel):
    message: str
    file_id: str
    filename: str
    size: int
    upload_time: datetime = datetime.now()
    content_summary: Optional[Dict[str, Any]] = None

class FileInfo(BaseModel):
    filename: str
    size: int
    file_id: Optional[str] = None
    upload_time: Optional[datetime] = None
    file_type: Optional[str] = None
    content_summary: Optional[Dict[str, Any]] = None

class UploadError(BaseModel):
    error: str
    detail: str

class DocumentContent(BaseModel):
    """Model for extracted document content"""
    full_text: str
    word_count: int
    character_count: int
    format: str
    metadata: Dict[str, Any]
    structure: Dict[str, Any]

class ProcessingStatus(BaseModel):
    """Model for file processing status"""
    file_id: str
    status: str  # "processing", "completed", "failed"
    progress: Optional[float] = None
    error_message: Optional[str] = None
    completed_at: Optional[datetime] = None