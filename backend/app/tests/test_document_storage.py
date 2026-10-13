import uuid

import pytest

import app.services.document as document_mod
from app.core import request_context as rc
from app.services.document import DocumentService
from app.services.storage import LocalStorage

TEXT = b"Chloroplasts convert light energy. " * 5


@pytest.fixture
def storage(tmp_path):
    return LocalStorage(tmp_path / "uploads")


@pytest.fixture
def service(storage):
    return DocumentService(storage=storage)


async def test_local_mode_keeps_the_flat_layout(service, storage, monkeypatch):
    monkeypatch.setattr(rc, "cloud_mode", lambda: False)
    up = await service.process_upload(TEXT, "notes.txt")
    assert sorted(await storage.list_prefix("")) == sorted([f"{up.file_id}.txt", f"{up.file_id}_extracted.txt"])
    assert (await service.get_extracted_text(up.file_id)).startswith("Chloroplasts")
    info = await service.get_file_info(up.file_id)
    assert info.size == len(TEXT) and info.file_type == "txt"


async def test_cloud_mode_prefixes_keys_with_the_client(service, storage, monkeypatch):
    monkeypatch.setattr(rc, "cloud_mode", lambda: True)
    client = str(uuid.uuid4())
    rc.bind(client)
    up = await service.process_upload(TEXT, "notes.txt")
    assert sorted(await storage.list_prefix("")) == sorted(
        [f"{client}/{up.file_id}.txt", f"{client}/{up.file_id}_extracted.txt"]
    )


async def test_other_client_cannot_read_or_delete(service, monkeypatch):
    monkeypatch.setattr(rc, "cloud_mode", lambda: True)
    rc.bind(str(uuid.uuid4()))
    up = await service.process_upload(TEXT, "notes.txt")
    rc.bind(str(uuid.uuid4()))
    assert await service.get_file_info(up.file_id) is None
    assert await service.get_extracted_text(up.file_id) is None
    assert await service.delete_file(up.file_id) is False


async def test_delete_also_removes_the_extracted_text(service, storage, monkeypatch):
    monkeypatch.setattr(rc, "cloud_mode", lambda: False)
    up = await service.process_upload(TEXT, "notes.txt")
    assert await service.delete_file(up.file_id) is True
    assert await storage.list_prefix("") == []


@pytest.mark.parametrize("bad_id", ["../x", "a/b", "..", "x.y", ""])
async def test_unsafe_file_ids_are_treated_as_missing(service, bad_id):
    assert await service.get_file_info(bad_id) is None
    assert await service.get_extracted_text(bad_id) is None
    assert await service.delete_file(bad_id) is False


async def test_a_failed_save_leaves_nothing_stored(tmp_path, monkeypatch):
    monkeypatch.setattr(rc, "cloud_mode", lambda: False)

    class FailingTextStorage(LocalStorage):
        async def save_bytes(self, key, data):
            if key.endswith("_extracted.txt"):
                raise OSError("disk full")
            await super().save_bytes(key, data)

    storage = FailingTextStorage(tmp_path / "uploads")
    with pytest.raises(OSError):
        await DocumentService(storage=storage).process_upload(TEXT, "notes.txt")
    assert await storage.list_prefix("") == []


async def test_extraction_runs_on_a_temporary_file(service, monkeypatch):
    monkeypatch.setattr(rc, "cloud_mode", lambda: False)
    seen = {}
    real = document_mod.DocumentExtractor.extract_text

    def spy(path, filename):
        seen["path"] = path
        return real(path, filename)

    monkeypatch.setattr(document_mod.DocumentExtractor, "extract_text", staticmethod(spy))
    await service.process_upload(TEXT, "notes.txt")
    assert not service_path_is_in_storage(seen["path"], service)


def service_path_is_in_storage(path, service):
    return str(service.storage.root) in str(path)
