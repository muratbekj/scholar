# Document extractor service for reading PDF, Word, etc.
import os
import tempfile
from typing import Dict, Any, Optional
from pathlib import Path
import PyPDF2
from docx import Document
# TODO: install python-pptx for PowerPoint support
# from pptx import Presentation
import logging

logger = logging.getLogger(__name__)

class DocumentExtractor:
    """Extracts text content from various document formats"""
    
    SUPPORTED_FORMATS = {
        '.pdf': 'application/pdf',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.doc': 'application/msword',
        '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        '.ppt': 'application/vnd.ms-powerpoint',
        '.txt': 'text/plain'
    }
    
    @classmethod
    def is_supported_format(cls, filename: str) -> bool:
        """Check if file format is supported"""
        file_ext = Path(filename).suffix.lower()
        return file_ext in cls.SUPPORTED_FORMATS
    
    @classmethod
    def extract_text(cls, file_path: str, filename: str) -> Dict[str, Any]:
        """Extract text content from document"""
        try:
            file_ext = Path(filename).suffix.lower()
            
            if file_ext == '.pdf':
                return cls._extract_pdf(file_path)
            elif file_ext in ['.docx', '.doc']:
                return cls._extract_word(file_path)
            elif file_ext in ['.pptx', '.ppt']:
                return cls._extract_powerpoint(file_path)
            elif file_ext == '.txt':
                return cls._extract_text_file(file_path)
            else:
                raise ValueError(f"Unsupported file format: {file_ext}")
                
        except Exception as e:
            logger.error(f"Error extracting text from {filename}: {str(e)}")
            raise
    
    @staticmethod
    def _extract_pdf(file_path: str) -> Dict[str, Any]:
        """Extract text from PDF file"""
        text_content = []
        metadata = {}
        
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                # Extract metadata
                if pdf_reader.metadata:
                    metadata = {
                        'title': pdf_reader.metadata.get('/Title', ''),
                        'author': pdf_reader.metadata.get('/Author', ''),
                        'subject': pdf_reader.metadata.get('/Subject', ''),
                        'creator': pdf_reader.metadata.get('/Creator', ''),
                        'producer': pdf_reader.metadata.get('/Producer', ''),
                        'pages': len(pdf_reader.pages)
                    }
                
                # Extract text from each page
                for page_num, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    if page_text.strip():
                        text_content.append({
                            'page': page_num + 1,
                            'content': page_text.strip()
                        })
                
        except Exception as e:
            logger.error(f"Error reading PDF file: {str(e)}")
            raise
        
        return {
            'content': text_content,
            'metadata': metadata,
            'total_pages': len(text_content),
            'format': 'pdf'
        }
    
    @staticmethod
    def _extract_word(file_path: str) -> Dict[str, Any]:
        """Extract text from Word document"""
        try:
            doc = Document(file_path)
            
            # Extract metadata
            metadata = {
                'title': doc.core_properties.title or '',
                'author': doc.core_properties.author or '',
                'subject': doc.core_properties.subject or '',
                'creator': doc.core_properties.creator or '',
                'revision': doc.core_properties.revision or 0,
                'paragraphs': len(doc.paragraphs)
            }
            
            # Extract text content
            text_content = []
            for para_num, paragraph in enumerate(doc.paragraphs):
                if paragraph.text.strip():
                    text_content.append({
                        'paragraph': para_num + 1,
                        'content': paragraph.text.strip(),
                        'style': paragraph.style.name if paragraph.style else 'Normal'
                    })
            
            return {
                'content': text_content,
                'metadata': metadata,
                'total_paragraphs': len(text_content),
                'format': 'word'
            }
            
        except Exception as e:
            logger.error(f"Error reading Word document: {str(e)}")
            raise
    
    @staticmethod
    def _extract_powerpoint(file_path: str) -> Dict[str, Any]:
        """Extract text from PowerPoint presentation"""
        try:
            # For now, return a placeholder since python-pptx is not installed
            # TODO: Install python-pptx and implement proper extraction
            logger.warning("PowerPoint extraction not fully implemented - python-pptx not installed")
            
            return {
                'content': [{'slide': 1, 'content': 'PowerPoint extraction not implemented yet'}],
                'metadata': {'slides': 1, 'note': 'python-pptx not installed'},
                'total_slides': 1,
                'format': 'powerpoint'
            }
            
        except Exception as e:
            logger.error(f"Error reading PowerPoint presentation: {str(e)}")
            raise
    
    @staticmethod
    def _extract_text_file(file_path: str) -> Dict[str, Any]:
        """Extract text from plain text file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # Split into paragraphs
            paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
            
            text_content = []
            for para_num, paragraph in enumerate(paragraphs):
                text_content.append({
                    'paragraph': para_num + 1,
                    'content': paragraph
                })
            
            return {
                'content': text_content,
                'metadata': {
                    'encoding': 'utf-8',
                    'paragraphs': len(text_content)
                },
                'total_paragraphs': len(text_content),
                'format': 'text'
            }
            
        except Exception as e:
            logger.error(f"Error reading text file: {str(e)}")
            raise
