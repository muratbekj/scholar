# Text chunking service for breaking large documents into manageable pieces
from typing import List, Dict, Any, Optional
import re
import uuid
from dataclasses import dataclass

@dataclass
class TextChunk:
    content: str
    chunk_id: str
    start_index: int
    end_index: int
    metadata: Dict[str, Any]

class TextChunkingService:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def chunk_text(self, text: str, strategy: str = "fixed_size") -> List[TextChunk]:
        """Chunk text using specified strategy"""
        if strategy == "fixed_size":
            return self._chunk_by_fixed_size(text)
        elif strategy == "sentences":
            return self.chunk_by_sentences(text)
        elif strategy == "paragraphs":
            return self.chunk_by_paragraphs(text)
        elif strategy == "semantic":
            return self.chunk_by_semantic_units(text)
        else:
            raise ValueError(f"Unknown chunking strategy: {strategy}")
    
    def _chunk_by_fixed_size(self, text: str) -> List[TextChunk]:
        """Chunk text by fixed character size with overlap"""
        chunks = []
        start = 0
        
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            
            # Try to break at word boundary if not at the end
            if end < len(text):
                # Look for the last space within the last 100 characters
                last_space = text.rfind(' ', start, end)
                if last_space > start + self.chunk_size - 100:
                    end = last_space
            
            chunk_content = text[start:end].strip()
            if chunk_content:
                chunk = TextChunk(
                    content=chunk_content,
                    chunk_id=str(uuid.uuid4()),
                    start_index=start,
                    end_index=end,
                    metadata={
                        "strategy": "fixed_size",
                        "chunk_size": self.chunk_size,
                        "overlap": self.chunk_overlap
                    }
                )
                chunks.append(chunk)
            
            # Move start position with overlap
            start = max(start + 1, end - self.chunk_overlap)
            
            # Prevent infinite loop
            if start >= end:
                break
        
        return chunks
    
    def chunk_by_sentences(self, text: str) -> List[TextChunk]:
        """Chunk text by sentence boundaries"""
        # Split text into sentences using regex
        sentence_pattern = r'(?<=[.!?])\s+'
        sentences = re.split(sentence_pattern, text)
        
        chunks = []
        current_chunk = ""
        chunk_start = 0
        
        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Check if adding this sentence would exceed chunk size
            if len(current_chunk) + len(sentence) > self.chunk_size and current_chunk:
                # Create chunk from current content
                chunk = TextChunk(
                    content=current_chunk.strip(),
                    chunk_id=str(uuid.uuid4()),
                    start_index=chunk_start,
                    end_index=chunk_start + len(current_chunk),
                    metadata={
                        "strategy": "sentences",
                        "sentence_count": len(current_chunk.split('.')),
                        "chunk_size": self.chunk_size
                    }
                )
                chunks.append(chunk)
                
                # Start new chunk with overlap
                overlap_text = self._get_overlap_text(current_chunk, self.chunk_overlap)
                current_chunk = overlap_text + " " + sentence
                chunk_start = chunk_start + len(current_chunk) - len(overlap_text) - len(sentence) - 1
            else:
                if current_chunk:
                    current_chunk += " " + sentence
                else:
                    current_chunk = sentence
        
        # Add the last chunk if there's content
        if current_chunk.strip():
            chunk = TextChunk(
                content=current_chunk.strip(),
                chunk_id=str(uuid.uuid4()),
                start_index=chunk_start,
                end_index=chunk_start + len(current_chunk),
                metadata={
                    "strategy": "sentences",
                    "sentence_count": len(current_chunk.split('.')),
                    "chunk_size": self.chunk_size
                }
            )
            chunks.append(chunk)
        
        return chunks
    
    def chunk_by_paragraphs(self, text: str) -> List[TextChunk]:
        """Chunk text by paragraph boundaries"""
        # Split by double newlines (paragraphs)
        paragraphs = re.split(r'\n\s*\n', text)
        
        chunks = []
        current_chunk = ""
        chunk_start = 0
        
        for i, paragraph in enumerate(paragraphs):
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            
            # Check if adding this paragraph would exceed chunk size
            if len(current_chunk) + len(paragraph) > self.chunk_size and current_chunk:
                # Create chunk from current content
                chunk = TextChunk(
                    content=current_chunk.strip(),
                    chunk_id=str(uuid.uuid4()),
                    start_index=chunk_start,
                    end_index=chunk_start + len(current_chunk),
                    metadata={
                        "strategy": "paragraphs",
                        "paragraph_count": len(current_chunk.split('\n\n')),
                        "chunk_size": self.chunk_size
                    }
                )
                chunks.append(chunk)
                
                # Start new chunk with overlap
                overlap_text = self._get_overlap_text(current_chunk, self.chunk_overlap)
                current_chunk = overlap_text + "\n\n" + paragraph
                chunk_start = chunk_start + len(current_chunk) - len(overlap_text) - len(paragraph) - 2
            else:
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
        
        # Add the last chunk if there's content
        if current_chunk.strip():
            chunk = TextChunk(
                content=current_chunk.strip(),
                chunk_id=str(uuid.uuid4()),
                start_index=chunk_start,
                end_index=chunk_start + len(current_chunk),
                metadata={
                    "strategy": "paragraphs",
                    "paragraph_count": len(current_chunk.split('\n\n')),
                    "chunk_size": self.chunk_size
                }
            )
            chunks.append(chunk)
        
        return chunks
    
    def chunk_by_semantic_units(self, text: str) -> List[TextChunk]:
        """Chunk text by semantic units (headers, sections, etc.)"""
        # Define patterns for semantic boundaries
        header_patterns = [
            r'^#{1,6}\s+',  # Markdown headers
            r'^[A-Z][A-Z\s]+\n[-=]+\n',  # Underlined headers
            r'^\d+\.\s+[A-Z]',  # Numbered sections
            r'^[A-Z][a-z]+:\s*$',  # Section labels
        ]
        
        # Split text into lines for processing
        lines = text.split('\n')
        chunks = []
        current_chunk = ""
        chunk_start = 0
        current_section = "main"
        
        for i, line in enumerate(lines):
            # Check if this line is a header/section boundary
            is_header = any(re.match(pattern, line) for pattern in header_patterns)
            
            # If it's a header and we have content, create a chunk
            if is_header and current_chunk.strip():
                chunk = TextChunk(
                    content=current_chunk.strip(),
                    chunk_id=str(uuid.uuid4()),
                    start_index=chunk_start,
                    end_index=chunk_start + len(current_chunk),
                    metadata={
                        "strategy": "semantic",
                        "section": current_section,
                        "chunk_size": self.chunk_size
                    }
                )
                chunks.append(chunk)
                
                # Start new chunk
                current_chunk = line + "\n"
                chunk_start = chunk_start + len(current_chunk)
                current_section = line.strip()
            else:
                # Check if adding this line would exceed chunk size
                if len(current_chunk) + len(line) > self.chunk_size and current_chunk.strip():
                    # Create chunk from current content
                    chunk = TextChunk(
                        content=current_chunk.strip(),
                        chunk_id=str(uuid.uuid4()),
                        start_index=chunk_start,
                        end_index=chunk_start + len(current_chunk),
                        metadata={
                            "strategy": "semantic",
                            "section": current_section,
                            "chunk_size": self.chunk_size
                        }
                    )
                    chunks.append(chunk)
                    
                    # Start new chunk with overlap
                    overlap_text = self._get_overlap_text(current_chunk, self.chunk_overlap)
                    current_chunk = overlap_text + "\n" + line
                    chunk_start = chunk_start + len(current_chunk) - len(overlap_text) - len(line) - 1
                else:
                    current_chunk += line + "\n"
        
        # Add the last chunk if there's content
        if current_chunk.strip():
            chunk = TextChunk(
                content=current_chunk.strip(),
                chunk_id=str(uuid.uuid4()),
                start_index=chunk_start,
                end_index=chunk_start + len(current_chunk),
                metadata={
                    "strategy": "semantic",
                    "section": current_section,
                    "chunk_size": self.chunk_size
                }
            )
            chunks.append(chunk)
        
        return chunks
    
    def _get_overlap_text(self, text: str, overlap_size: int) -> str:
        """Get the last portion of text for overlap"""
        if len(text) <= overlap_size:
            return text
        
        # Try to break at word boundary
        last_space = text.rfind(' ', len(text) - overlap_size)
        if last_space > len(text) - overlap_size - 100:
            return text[last_space + 1:]
        
        return text[-overlap_size:]
    
    def get_chunk_statistics(self, chunks: List[TextChunk]) -> Dict[str, Any]:
        """Get statistics about the chunks"""
        if not chunks:
            return {}
        
        chunk_sizes = [len(chunk.content) for chunk in chunks]
        total_text_length = sum(chunk_sizes)
        
        return {
            "total_chunks": len(chunks),
            "total_text_length": total_text_length,
            "average_chunk_size": sum(chunk_sizes) / len(chunk_sizes),
            "min_chunk_size": min(chunk_sizes),
            "max_chunk_size": max(chunk_sizes),
            "chunk_size_distribution": {
                "small": len([s for s in chunk_sizes if s < 500]),
                "medium": len([s for s in chunk_sizes if 500 <= s < 1000]),
                "large": len([s for s in chunk_sizes if s >= 1000])
            }
        }
