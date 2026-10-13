# Vector store service: Chroma on local disk, or pgvector in Postgres (VECTOR_BACKEND)
import asyncio
import logging
import math
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from ..core import request_context
from ..core.config import get_settings
from ..core.providers import get_embeddings

logger = logging.getLogger(__name__)

def _unit(vector: List[float]) -> List[float]:
    norm = math.sqrt(sum(x * x for x in vector))
    return [x / norm for x in vector] if norm else list(vector)


class UnitNormalizedEmbeddings(Embeddings):
    """Scales every vector to unit length, so a squared-L2 distance d equals 2 - 2*cosine.

    Ollama's /api/embed and full-size Vertex embeddings are already unit length; this
    guarantees it for reduced output dimensions and other models.
    """

    def __init__(self, base: Embeddings):
        self.base = base

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [_unit(v) for v in self.base.embed_documents(texts)]

    def embed_query(self, text: str) -> List[float]:
        return _unit(self.base.embed_query(text))

    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        return [_unit(v) for v in await self.base.aembed_documents(texts)]

    async def aembed_query(self, text: str) -> List[float]:
        return _unit(await self.base.aembed_query(text))


def chroma_distance_to_relevance(distance: float) -> float:
    """Chroma's default squared-L2 distance on unit vectors -> cosine similarity clamped to [0, 1]."""
    return max(0.0, min(1.0, 1.0 - distance / 2.0))


def cosine_distance_to_relevance(distance: float) -> float:
    """PGVector's cosine distance (1 - cosine) -> cosine similarity clamped to [0, 1]."""
    return max(0.0, min(1.0, 1.0 - distance))


Row = Tuple[str, str, Dict[str, Any]]  # (id, content, metadata)


class _ChromaBackend:
    def __init__(self, persist_directory: Path, embeddings: Embeddings, collection_name: str):
        from langchain_chroma import Chroma

        self.store = Chroma(
            persist_directory=str(persist_directory),
            embedding_function=embeddings,
            collection_name=collection_name,
        )

    @staticmethod
    def _where(filters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not filters:
            return None
        if len(filters) == 1:
            return dict(filters)
        return {"$and": [{key: value} for key, value in sorted(filters.items())]}

    def add(self, texts: List[str], metadatas: List[Dict[str, Any]], ids: List[str]) -> None:
        self.store.add_texts(texts=texts, metadatas=metadatas, ids=ids)

    def search(self, query: str, k: int, filters: Dict[str, Any]) -> List[Tuple[Document, float]]:
        results = self.store.similarity_search_with_score(query=query, k=k, filter=self._where(filters))
        return [(doc, chroma_distance_to_relevance(float(score))) for doc, score in results]

    def get(self, filters: Dict[str, Any], limit: Optional[int] = None) -> List[Row]:
        kwargs: Dict[str, Any] = {}
        where = self._where(filters)
        if where is not None:
            kwargs["where"] = where
        if limit is not None:
            kwargs["limit"] = limit
        results = self.store.get(**kwargs)
        return list(zip(results["ids"], results["documents"], results["metadatas"]))

    def delete(self, ids: List[str]) -> None:
        self.store.delete(ids=ids)


class _PGVectorBackend:
    def __init__(self, database_url: str, embeddings: Embeddings, collection_name: str):
        from langchain_postgres import PGVector
        from sqlalchemy import create_engine

        self.collection_name = collection_name
        self.engine = create_engine(database_url, pool_pre_ping=True)
        self.store = PGVector(
            embeddings=embeddings,
            collection_name=collection_name,
            connection=self.engine,
            use_jsonb=True,
        )

    def add(self, texts: List[str], metadatas: List[Dict[str, Any]], ids: List[str]) -> None:
        self.store.add_texts(texts=texts, metadatas=metadatas, ids=ids)

    def search(self, query: str, k: int, filters: Dict[str, Any]) -> List[Tuple[Document, float]]:
        results = self.store.similarity_search_with_score(query, k=k, filter=dict(filters) or None)
        return [(doc, cosine_distance_to_relevance(float(score))) for doc, score in results]

    def get(self, filters: Dict[str, Any], limit: Optional[int] = None) -> List[Row]:
        from sqlalchemy import text

        sql = (
            "SELECT e.id, e.document, e.cmetadata FROM langchain_pg_embedding e "
            "JOIN langchain_pg_collection c ON e.collection_id = c.uuid WHERE c.name = :collection"
        )
        params: Dict[str, Any] = {"collection": self.collection_name}
        for i, (key, value) in enumerate(sorted(filters.items())):
            sql += f" AND e.cmetadata ->> :key{i} = :value{i}"
            params[f"key{i}"] = key
            params[f"value{i}"] = str(value)
        sql += " ORDER BY e.id"
        if limit is not None:
            sql += " LIMIT :limit"
            params["limit"] = limit
        with self.engine.connect() as conn:
            rows = conn.execute(text(sql), params).all()
        return [(row[0], row[1], dict(row[2] or {})) for row in rows]

    def delete(self, ids: List[str]) -> None:
        self.store.delete(ids=ids)


class VectorStoreService:
    """Service for vector storage: Chroma on local disk, or pgvector in Postgres (VECTOR_BACKEND).

    In cloud mode every write carries the request's client_id and every read, delete and stats call
    filters on it (spec D5). Backend calls run in asyncio.to_thread so they don't block the event loop.
    """
    
    def __init__(self,
                 persist_directory: Optional[str] = None,
                 embedding_model: Optional[str] = None,
                 collection_name: str = "documents",
                 embeddings: Optional[Embeddings] = None,
                 backend: Optional[str] = None,
                 database_url: Optional[str] = None):
        settings = get_settings()
        self.backend_name = backend or settings.vector_backend
        self.embedding_model = embedding_model or settings.embed_model
        self.collection_name = collection_name
        # One collection must only ever hold vectors from one embedding model: Vertex and
        # nomic-embed-text vectors differ in dimension. Local (Chroma) and cloud (pgvector)
        # deployments use separate stores; use a separate CHROMA_DIR per provider.
        self.embeddings = UnitNormalizedEmbeddings(embeddings or get_embeddings(model=self.embedding_model))
        if self.backend_name == "pgvector":
            self.persist_directory = None
            self.backend = _PGVectorBackend(database_url or settings.database_url, self.embeddings, collection_name)
        else:
            self.persist_directory = Path(persist_directory or settings.chroma_dir)
            self.persist_directory.mkdir(parents=True, exist_ok=True)
            self.backend = _ChromaBackend(self.persist_directory, self.embeddings, collection_name)
        self.vector_store = self.backend.store
        logger.info(f"Initialized {self.backend_name} vector store (collection {collection_name})")

    @staticmethod
    def _scoped(filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Filters plus the request's client_id in cloud mode (raises IsolationError if none is bound)."""
        scoped = dict(filters or {})
        client_id = request_context.scope_client_id()
        if client_id is not None:
            scoped["client_id"] = client_id
        return scoped
    
    async def add_documents(self, 
                          texts: List[str], 
                          metadatas: List[Dict[str, Any]] = None,
                          ids: List[str] = None) -> Dict[str, Any]:
        """Add documents to the vector store"""
        try:
            if not texts:
                return {"success": False, "error": "No texts provided"}
            
            client_id = request_context.scope_client_id()
            metadatas = [dict(m) for m in (metadatas or [{}] * len(texts))]
            if client_id is not None:
                for metadata in metadatas:
                    metadata['client_id'] = client_id
            ids = ids or [f"doc_{i}_{datetime.now().timestamp()}" for i in range(len(texts))]
            
            await asyncio.to_thread(self.backend.add, texts, metadatas, ids)
            
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
        """Search for similar documents; similarity_score is a 0-1 relevance, higher is better"""
        try:
            results = await asyncio.to_thread(self.backend.search, query, k, self._scoped(filter_metadata))
            
            formatted_results = [
                {
                    'content': doc.page_content,
                    'metadata': doc.metadata,
                    'similarity_score': score,
                    'id': doc.metadata.get('chunk_id', 'unknown')
                }
                for doc, score in results
            ]
            
            logger.info(f"Found {len(formatted_results)} similar documents for query")
            return formatted_results
            
        except Exception as e:
            error_msg = f"Error searching similar documents: {str(e)}"
            logger.error(error_msg)
            return []
    
    async def search_by_file_id(self, file_id: str, query: str = None, k: int = 10) -> List[Dict[str, Any]]:
        """Search for documents/chunks by file ID"""
        try:
            if query:
                # Search with query within the file
                return await self.search_similar(query, k, {"file_id": file_id})
            
            # Get all chunks for the file
            rows = await asyncio.to_thread(self.backend.get, self._scoped({"file_id": file_id}), k)
            return [
                {'content': content, 'metadata': metadata, 'id': doc_id}
                for doc_id, content, metadata in rows
            ]
                
        except Exception as e:
            error_msg = f"Error searching by file ID {file_id}: {str(e)}"
            logger.error(error_msg)
            return []
    
    async def delete_file_documents(self, file_id: str) -> Dict[str, Any]:
        """Delete all documents/chunks for a specific file"""
        try:
            rows = await asyncio.to_thread(self.backend.get, self._scoped({"file_id": file_id}))
            ids = [doc_id for doc_id, _, _ in rows]
            
            if not ids:
                return {"success": True, "message": "No documents found for file"}
            
            await asyncio.to_thread(self.backend.delete, ids)
            
            logger.info(f"Deleted {len(ids)} documents for file {file_id}")
            
            return {
                "success": True,
                "documents_deleted": len(ids),
                "ids": ids
            }
            
        except Exception as e:
            error_msg = f"Error deleting documents for file {file_id}: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector store collection (the caller's documents in cloud mode)"""
        try:
            rows = await asyncio.to_thread(self.backend.get, self._scoped())
            unique_files = {metadata['file_id'] for _, _, metadata in rows if metadata and 'file_id' in metadata}
            
            return {
                "total_documents": len(rows),
                "unique_files": len(unique_files),
                "collection_name": self.collection_name,
                "embedding_model": self.embedding_model,
                "persist_directory": str(self.persist_directory) if self.persist_directory else self.backend_name
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
            test_embedding = await asyncio.to_thread(self.embeddings.embed_query, "test")
            
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
