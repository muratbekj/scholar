# RAG Pipeline service for end-to-end document processing
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime
import asyncio

from .document import DocumentService
from .embedding import EmbeddingService, EmbeddingResult
from .vector_store import VectorStoreService

logger = logging.getLogger(__name__)

class RAGPipelineService:
    """Service for orchestrating the complete RAG pipeline"""
    
    def __init__(self, 
                 document_service: DocumentService = None,
                 embedding_service: EmbeddingService = None,
                 vector_store_service: VectorStoreService = None):
        self.document_service = document_service or DocumentService()
        self.embedding_service = embedding_service or EmbeddingService()
        self.vector_store_service = vector_store_service or VectorStoreService()
        
        logger.info("Initialized RAG Pipeline Service")
    
    async def process_document_upload(self, 
                                    file_content: bytes, 
                                    filename: str,
                                    enable_embedding: bool = True) -> Dict[str, Any]:
        """Complete pipeline for processing document upload"""
        start_time = datetime.now()
        
        try:
            logger.info(f"Starting RAG pipeline for file: {filename}")
            
            # Step 1: Document processing and text extraction
            logger.info("Step 1: Processing document and extracting text")
            upload_result = await self.document_service.process_upload(file_content, filename)
            file_id = upload_result.file_id
            
            # Step 2: Prepare chunks for embedding
            logger.info("Step 2: Preparing chunks for embedding")
            chunks = await self._prepare_chunks_for_embedding(upload_result)
            
            # Step 3: Generate embeddings (if enabled)
            embedding_results = None
            if enable_embedding and chunks:
                logger.info("Step 3: Generating embeddings")
                embedding_results = await self._generate_embeddings_for_chunks(chunks, file_id)
            
            # Step 4: Store in vector database (if embeddings successful)
            vector_store_result = None
            if embedding_results and any(result.success for result in embedding_results):
                logger.info("Step 4: Storing in vector database")
                vector_store_result = await self._store_chunks_in_vector_db(chunks, file_id)
            
            # Step 5: Compile final result
            processing_time = (datetime.now() - start_time).total_seconds()
            
            result = {
                "file_id": file_id,
                "filename": filename,
                "processing_time_seconds": processing_time,
                "document_processing": {
                    "success": True,
                    "file_size": upload_result.size,
                    "content_summary": upload_result.content_summary
                },
                "chunking": {
                    "total_chunks": len(chunks) if chunks else 0,
                    "chunking_strategy": upload_result.content_summary.get('chunking_info', {}).get('chunking_strategy', 'none')
                },
                "embedding": {
                    "enabled": enable_embedding,
                    "success": embedding_results is not None,
                    "total_embeddings": len(embedding_results) if embedding_results else 0,
                    "successful_embeddings": len([r for r in embedding_results if r.success]) if embedding_results else 0,
                    "failed_embeddings": len([r for r in embedding_results if not r.success]) if embedding_results else 0
                },
                "vector_storage": {
                    "success": vector_store_result.get('success', False) if vector_store_result else False,
                    "documents_stored": vector_store_result.get('documents_added', 0) if vector_store_result else 0
                },
                "upload_time": upload_result.upload_time,
                "status": "completed"
            }
            
            logger.info(f"RAG pipeline completed for file {filename} in {processing_time:.2f} seconds")
            return result
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            error_msg = f"Error in RAG pipeline for file {filename}: {str(e)}"
            logger.error(error_msg)
            
            return {
                "file_id": getattr(upload_result, 'file_id', None) if 'upload_result' in locals() else None,
                "filename": filename,
                "processing_time_seconds": processing_time,
                "status": "failed",
                "error": error_msg
            }
    
    async def _prepare_chunks_for_embedding(self, upload_result) -> List[Dict[str, Any]]:
        """Prepare chunks for embedding processing"""
        try:
            content_summary = upload_result.content_summary
            chunking_info = content_summary.get('chunking_info', {})
            
            if chunking_info.get('is_chunked', False):
                # Document was chunked, use the chunks
                chunks = content_summary.get('chunks', [])
                logger.info(f"Using {len(chunks)} pre-generated chunks")
                return chunks
            else:
                # Document was not chunked, create a single chunk
                full_text = content_summary.get('full_text', '')
                if full_text:
                    single_chunk = {
                        'chunk_id': f"{upload_result.file_id}_full",
                        'content': full_text,
                        'start_index': 0,
                        'end_index': len(full_text),
                        'metadata': {
                            'strategy': 'full_document',
                            'is_chunked': False
                        }
                    }
                    logger.info("Using single chunk for small document")
                    return [single_chunk]
                else:
                    logger.warning("No text content found for embedding")
                    return []
                    
        except Exception as e:
            logger.error(f"Error preparing chunks for embedding: {str(e)}")
            return []
    
    async def _generate_embeddings_for_chunks(self, 
                                            chunks: List[Dict[str, Any]], 
                                            file_id: str) -> List[EmbeddingResult]:
        """Generate embeddings for document chunks"""
        try:
            texts = [chunk['content'] for chunk in chunks]
            metadata_list = []
            
            for chunk in chunks:
                metadata = {
                    'file_id': file_id,
                    'chunk_id': chunk['chunk_id'],
                    'start_index': chunk['start_index'],
                    'end_index': chunk['end_index'],
                    'chunk_strategy': chunk['metadata'].get('strategy', 'unknown'),
                    'upload_time': datetime.now().isoformat()
                }
                metadata_list.append(metadata)
            
            # Generate embeddings in batches
            embedding_results = await self.embedding_service.embed_batch(texts, metadata_list)
            
            # Log embedding statistics
            successful = len([r for r in embedding_results if r.success])
            failed = len([r for r in embedding_results if not r.success])
            logger.info(f"Generated embeddings: {successful} successful, {failed} failed")
            
            return embedding_results
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {str(e)}")
            return []
    
    async def _store_chunks_in_vector_db(self, 
                                       chunks: List[Dict[str, Any]], 
                                       file_id: str) -> Dict[str, Any]:
        """Store document chunks in vector database"""
        try:
            result = await self.vector_store_service.add_document_chunks(file_id, chunks)
            
            if result['success']:
                logger.info(f"Successfully stored {result.get('documents_added', 0)} chunks in vector database")
            else:
                logger.error(f"Failed to store chunks in vector database: {result.get('error', 'Unknown error')}")
            
            return result
            
        except Exception as e:
            error_msg = f"Error storing chunks in vector database: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    async def search_documents(self, 
                             query: str, 
                             k: int = 5, 
                             file_id: str = None) -> Dict[str, Any]:
        """Search documents using vector similarity"""
        try:
            if file_id:
                # Search within a specific file
                results = await self.vector_store_service.search_by_file_id(file_id, query, k)
            else:
                # Search across all documents
                results = await self.vector_store_service.search_similar(query, k)
            
            return {
                "success": True,
                "query": query,
                "results": results,
                "total_results": len(results),
                "search_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            error_msg = f"Error searching documents: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    async def delete_document(self, file_id: str) -> Dict[str, Any]:
        """Delete document and its embeddings from the system"""
        try:
            # Delete from vector store
            vector_result = await self.vector_store_service.delete_file_documents(file_id)
            
            # Delete from document service
            document_result = await self.document_service.delete_file(file_id)
            
            return {
                "success": vector_result.get('success', False) and document_result,
                "file_id": file_id,
                "vector_store_deleted": vector_result.get('success', False),
                "document_deleted": document_result,
                "vector_store_result": vector_result
            }
            
        except Exception as e:
            error_msg = f"Error deleting document {file_id}: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    async def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        try:
            # Get vector store stats
            vector_stats = await self.vector_store_service.get_collection_stats()
            
            # Get embedding service health
            embedding_health = await self.embedding_service.validate_embedding_model()
            
            return {
                "vector_store": vector_stats,
                "embedding_service": embedding_health,
                "pipeline_status": "healthy"
            }
            
        except Exception as e:
            error_msg = f"Error getting processing stats: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}

# Initialize global RAG pipeline service
rag_pipeline_service = RAGPipelineService()
