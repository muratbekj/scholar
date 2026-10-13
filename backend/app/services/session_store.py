"""Q&A and quiz session persistence: process memory (local) or Postgres (cloud), scoped per client.

Kinds: "qa" (QASession), "quiz" (QuizSession), "quiz_def" (Quiz). Services load a session, change it,
and put it back; concurrent writes to one session are last-write-wins.
"""
import asyncio
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple, Type

from pydantic import BaseModel

from ..core import request_context
from ..core.config import Settings, get_settings


class SessionStore(ABC):
    @abstractmethod
    async def get(self, kind: str, session_id: str) -> Optional[Any]: ...

    @abstractmethod
    async def put(self, kind: str, session_id: str, obj: Any) -> None: ...

    @abstractmethod
    async def delete(self, kind: str, session_id: str) -> bool: ...

    @abstractmethod
    async def list(self, kind: str) -> List[Any]: ...


class MemorySessionStore(SessionStore):
    """Keeps the objects themselves, like the dicts it replaces. Lost on restart (local default)."""

    def __init__(self):
        self._buckets: Dict[Tuple[Optional[str], str], Dict[str, Any]] = {}

    def _bucket(self, kind: str) -> Dict[str, Any]:
        return self._buckets.setdefault((request_context.scope_client_id(), kind), {})

    async def get(self, kind: str, session_id: str) -> Optional[Any]:
        return self._bucket(kind).get(session_id)

    async def put(self, kind: str, session_id: str, obj: Any) -> None:
        self._bucket(kind)[session_id] = obj

    async def delete(self, kind: str, session_id: str) -> bool:
        return self._bucket(kind).pop(session_id, None) is not None

    async def list(self, kind: str) -> List[Any]:
        return list(self._bucket(kind).values())


def _model_for(kind: str) -> Type[BaseModel]:
    from ..models.qa import QASession
    from ..models.quiz import Quiz, QuizSession

    return {"qa": QASession, "quiz": QuizSession, "quiz_def": Quiz}[kind]


class PostgresSessionStore(SessionStore):
    """One `sessions` table (client_id, kind, id, data JSONB, created_at, updated_at), created if missing."""

    def __init__(self, database_url: str):
        from sqlalchemy import Column, DateTime, MetaData, String, Table, create_engine, func
        from sqlalchemy.dialects.postgresql import JSONB

        self.engine = create_engine(database_url, pool_pre_ping=True)
        metadata = MetaData()
        self.table = Table(
            "sessions", metadata,
            Column("client_id", String, primary_key=True),
            Column("kind", String, primary_key=True),
            Column("id", String, primary_key=True),
            Column("data", JSONB, nullable=False),
            Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
            Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
        )
        metadata.create_all(self.engine)

    @staticmethod
    def _client() -> str:
        return request_context.scope_client_id() or ""

    def _match(self, client_id: str, kind: str):
        return (self.table.c.client_id == client_id) & (self.table.c.kind == kind)

    async def get(self, kind: str, session_id: str) -> Optional[Any]:
        from sqlalchemy import select

        client_id = self._client()

        def load():
            stmt = select(self.table.c.data).where(self._match(client_id, kind) & (self.table.c.id == session_id))
            with self.engine.connect() as conn:
                return conn.execute(stmt).scalar_one_or_none()

        data = await asyncio.to_thread(load)
        return None if data is None else _model_for(kind).model_validate(data)

    async def put(self, kind: str, session_id: str, obj: Any) -> None:
        from sqlalchemy import func
        from sqlalchemy.dialects.postgresql import insert

        client_id = self._client()
        data = obj.model_dump(mode="json")

        def save():
            stmt = insert(self.table).values(client_id=client_id, kind=kind, id=session_id, data=data)
            stmt = stmt.on_conflict_do_update(
                index_elements=["client_id", "kind", "id"],
                set_={"data": stmt.excluded.data, "updated_at": func.now()},
            )
            with self.engine.begin() as conn:
                conn.execute(stmt)

        await asyncio.to_thread(save)

    async def delete(self, kind: str, session_id: str) -> bool:
        client_id = self._client()

        def remove() -> bool:
            stmt = self.table.delete().where(self._match(client_id, kind) & (self.table.c.id == session_id))
            with self.engine.begin() as conn:
                return conn.execute(stmt).rowcount > 0

        return await asyncio.to_thread(remove)

    async def list(self, kind: str) -> List[Any]:
        from sqlalchemy import select

        client_id = self._client()

        def load():
            stmt = select(self.table.c.data).where(self._match(client_id, kind)).order_by(self.table.c.created_at)
            with self.engine.connect() as conn:
                return conn.execute(stmt).scalars().all()

        model = _model_for(kind)
        return [model.model_validate(data) for data in await asyncio.to_thread(load)]


@lru_cache(maxsize=None)
def _postgres_store(database_url: str) -> PostgresSessionStore:
    return PostgresSessionStore(database_url)


def build_session_store(settings: Optional[Settings] = None) -> SessionStore:
    """A new in-memory store per service (as before), or the shared Postgres store (SESSION_BACKEND)."""
    s = settings or get_settings()
    if s.session_backend == "postgres":
        return _postgres_store(s.database_url)
    return MemorySessionStore()
