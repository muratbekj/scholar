# Document processing service
import os
import uuid
import tempfile
import shutil
from typing import Dict, Any, Optional, List
from pathlib import Path
import logging
from datetime import datetime

from .extractor import DocumentExtractor
from ..models.file import FileInfo, FileUploadResponse, UploadError

logger = logging.getLogger(__name__)

class DocumentService:
    """Service for handling document uploads and processing"""
    
    def __init__(self, upload_dir: str = "uploads"):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(exist_ok=True)
    
    async def process_upload(self, file_content: bytes, filename: str) -> FileUploadResponse:
        """Process uploaded file and extract content"""
        try:
            # Validate file format
            if not DocumentExtractor.is_supported_format(filename):
                raise ValueError(f"Unsupported file format: {Path(filename).suffix}")
            
            # Generate unique file ID
            file_id = str(uuid.uuid4())
            file_ext = Path(filename).suffix.lower()
            stored_filename = f"{file_id}{file_ext}"
            file_path = self.upload_dir / stored_filename
            
            # Save file
            with open(file_path, 'wb') as f:
                f.write(file_content)
            
            # Extract content
            extracted_data = DocumentExtractor.extract_text(str(file_path), filename)
            
            # Create content summary
            content_summary = self._create_content_summary(extracted_data)
            
            # Save extracted text to a separate file
            text_file_path = self.upload_dir / f"{file_id}_extracted.txt"
            with open(text_file_path, 'w', encoding='utf-8') as f:
                f.write(content_summary['full_text'])
            
            logger.info(f"Successfully processed file {filename} with ID {file_id}")
            
            return FileUploadResponse(
                message="File uploaded and processed successfully",
                file_id=file_id,
                filename=filename,
                size=len(file_content),
                upload_time=datetime.now(),
                content_summary=content_summary
            )
            
        except Exception as e:
            logger.error(f"Error processing file {filename}: {str(e)}")
            # Clean up file if it was saved
            if 'file_path' in locals() and file_path.exists():
                file_path.unlink()
            raise
    
    def _create_content_summary(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a summary of extracted content"""
        content = extracted_data.get('content', [])
        metadata = extracted_data.get('metadata', {})
        format_type = extracted_data.get('format', 'unknown')
        
        # Combine all text content
        full_text = ""
        if format_type == 'pdf':
            full_text = '\n\n'.join([page['content'] for page in content])
        elif format_type in ['word', 'text']:
            full_text = '\n\n'.join([para['content'] for para in content])
        elif format_type == 'powerpoint':
            full_text = '\n\n'.join([slide['content'] for slide in content])
        
        return {
            'full_text': full_text,
            'word_count': len(full_text.split()),
            'character_count': len(full_text),
            'format': format_type,
            'metadata': metadata,
            'structure': {
                'total_items': len(content),
                'item_type': 'pages' if format_type == 'pdf' else 
                            'slides' if format_type == 'powerpoint' else 'paragraphs'
            }
        }
    
    async def get_file_info(self, file_id: str) -> Optional[FileInfo]:
        """Get file information by ID"""
        try:
            # Look for file in upload directory
            for file_path in self.upload_dir.glob(f"{file_id}.*"):
                if file_path.exists() and not file_path.name.endswith('_extracted.txt'):
                    stat = file_path.stat()
                    
                    # Try to load content summary if available
                    content_summary = None
                    text_file_path = self.upload_dir / f"{file_id}_extracted.txt"
                    if text_file_path.exists():
                        try:
                            with open(text_file_path, 'r', encoding='utf-8') as f:
                                full_text = f.read()
                                content_summary = {
                                    'full_text': full_text,
                                    'word_count': len(full_text.split()),
                                    'character_count': len(full_text),
                                    'format': file_path.suffix[1:] if file_path.suffix else 'unknown'
                                }
                        except Exception as e:
                            logger.warning(f"Could not load content summary for {file_id}: {str(e)}")
                    
                    return FileInfo(
                        filename=file_id,  # You might want to store original filename in a database
                        size=stat.st_size,
                        file_id=file_id,
                        upload_time=datetime.fromtimestamp(stat.st_mtime),
                        file_type=file_path.suffix[1:] if file_path.suffix else None,
                        content_summary=content_summary
                    )
            return None
        except Exception as e:
            logger.error(f"Error getting file info for {file_id}: {str(e)}")
            return None
    
    async def delete_file(self, file_id: str) -> bool:
        """Delete file by ID"""
        try:
            deleted_any = False
            for file_path in self.upload_dir.glob(f"{file_id}.*"):
                if file_path.exists():
                    file_path.unlink()
                    deleted_any = True
                    logger.info(f"Deleted file {file_path.name}")
            
            if deleted_any:
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting file {file_id}: {str(e)}")
            return False
    
    async def get_extracted_text(self, file_id: str) -> Optional[str]:
        """Get extracted text content for a file"""
        try:
            text_file_path = self.upload_dir / f"{file_id}_extracted.txt"
            if text_file_path.exists():
                with open(text_file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            return None
        except Exception as e:
            logger.error(f"Error getting extracted text for {file_id}: {str(e)}")
            return None
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported file formats"""
        return list(DocumentExtractor.SUPPORTED_FORMATS.keys())
