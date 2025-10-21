# Vector store service for storing and retrieving embeddings
try:
    from langchain_chroma import Chroma
except ImportError:
    from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings
from typing import List, Dict, Any, Optional, Tuple
import logging
import os
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

class VectorStoreService:
    """Service for managing vector storage using ChromaDB"""
    
    def __init__(self, 
                 persist_directory: str = "./chroma_db",
                 embedding_model: str = "nomic-embed-text",
                 collection_name: str = "documents"):
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(exist_ok=True)
        self.embedding_model = embedding_model
        self.collection_name = collection_name
        self.embeddings = OllamaEmbeddings(model=embedding_model)
        self.vector_store = None
        self._initialize_vector_store()
        logger.info(f"Initialized vector store service with directory: {persist_directory}")
    
    def _initialize_vector_store(self):
        """Initialize the ChromaDB vector store"""
        try:
            self.vector_store = Chroma(
                persist_directory=str(self.persist_directory),
                embedding_function=self.embeddings,
                collection_name=self.collection_name
            )
            logger.info(f"Vector store initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing vector store: {str(e)}")
            raise
    
    async def add_documents(self, 
                          texts: List[str], 
                          metadatas: List[Dict[str, Any]] = None,
                          ids: List[str] = None) -> Dict[str, Any]:
        """Add documents to the vector store"""
        try:
            if not texts:
                return {"success": False, "error": "No texts provided"}
            
            metadatas = metadatas or [{}] * len(texts)
            ids = ids or [f"doc_{i}_{datetime.now().timestamp()}" for i in range(len(texts))]
            
            # Add documents to vector store
            self.vector_store.add_texts(
                texts=texts,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"Successfully added {len(texts)} documents to vector store")
            
            return {
                "success": True,
                "documents_added": len(texts),
                "ids": ids
            }
            
        except Exception as e:
            error_msg = f"Error adding documents to vector store: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    async def add_document_chunks(self, 
                                file_id: str, 
                                chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Add document chunks to vector store with file metadata"""
        try:
            if not chunks:
                return {"success": False, "error": "No chunks provided"}
            
            texts = []
            metadatas = []
            ids = []
            
            for chunk in chunks:
                texts.append(chunk['content'])
                metadata = {
                    'file_id': file_id,
                    'chunk_id': chunk['chunk_id'],
                    'start_index': chunk['start_index'],
                    'end_index': chunk['end_index'],
                    'chunk_strategy': chunk['metadata'].get('strategy', 'unknown'),
                    'upload_time': datetime.now().isoformat(),
                    **chunk['metadata']
                }
                metadatas.append(metadata)
                ids.append(f"{file_id}_{chunk['chunk_id']}")
            
            result = await self.add_documents(texts, metadatas, ids)
            
            if result['success']:
                logger.info(f"Successfully added {len(chunks)} chunks for file {file_id}")
            
            return result
            
        except Exception as e:
            error_msg = f"Error adding document chunks for file {file_id}: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    async def search_similar(self, 
                           query: str, 
                           k: int = 5, 
                           filter_metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Search for similar documents"""
        try:
            # Perform similarity search
            results = self.vector_store.similarity_search_with_score(
                query=query,
                k=k,
                filter=filter_metadata
            )
            
            # Format results
            formatted_results = []
            for doc, score in results:
                formatted_results.append({
                    'content': doc.page_content,
                    'metadata': doc.metadata,
                    'similarity_score': float(score),
                    'id': doc.metadata.get('chunk_id', 'unknown')
                })
            
            logger.info(f"Found {len(formatted_results)} similar documents for query")
            return formatted_results
            
        except Exception as e:
            error_msg = f"Error searching similar documents: {str(e)}"
            logger.error(error_msg)
            return []
    
    async def search_by_file_id(self, file_id: str, query: str = None, k: int = 10) -> List[Dict[str, Any]]:
        """Search for documents/chunks by file ID"""
        try:
            filter_metadata = {"file_id": file_id}
            
            if query:
                # Search with query within the file
                return await self.search_similar(query, k, filter_metadata)
            else:
                # Get all chunks for the file
                results = self.vector_store.get(
                    where={"file_id": file_id},
                    limit=k
                )
                
                formatted_results = []
                for i, doc_id in enumerate(results['ids']):
                    formatted_results.append({
                        'content': results['documents'][i],
                        'metadata': results['metadatas'][i],
                        'id': doc_id
                    })
                
                return formatted_results
                
        except Exception as e:
            error_msg = f"Error searching by file ID {file_id}: {str(e)}"
            logger.error(error_msg)
            return []
    
    async def delete_file_documents(self, file_id: str) -> Dict[str, Any]:
        """Delete all documents/chunks for a specific file"""
        try:
            # Get all document IDs for the file
            results = self.vector_store.get(
                where={"file_id": file_id}
            )
            
            if not results['ids']:
                return {"success": True, "message": "No documents found for file"}
            
            # Delete documents
            self.vector_store.delete(ids=results['ids'])
            
            logger.info(f"Deleted {len(results['ids'])} documents for file {file_id}")
            
            return {
                "success": True,
                "documents_deleted": len(results['ids']),
                "ids": results['ids']
            }
            
        except Exception as e:
            error_msg = f"Error deleting documents for file {file_id}: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector store collection"""
        try:
            # Get all documents
            results = self.vector_store.get()
            
            total_documents = len(results['ids']) if results['ids'] else 0
            
            # Count unique files
            unique_files = set()
            for metadata in results['metadatas']:
                if metadata and 'file_id' in metadata:
                    unique_files.add(metadata['file_id'])
            
            return {
                "total_documents": total_documents,
                "unique_files": len(unique_files),
                "collection_name": self.collection_name,
                "embedding_model": self.embedding_model,
                "persist_directory": str(self.persist_directory)
            }
            
        except Exception as e:
            error_msg = f"Error getting collection stats: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}
    
    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the vector store"""
        try:
            # Try to get collection stats
            stats = await self.get_collection_stats()
            
            # Test embedding generation
            test_embedding = self.embeddings.embed_query("test")
            
            return {
                "status": "healthy",
                "embedding_model": self.embedding_model,
                "embedding_dimensions": len(test_embedding),
                "collection_stats": stats
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

# Initialize global vector store service
vector_store_service = VectorStoreService()
