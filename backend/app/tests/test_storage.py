from datetime import datetime, timezone

import pytest

from app.core.config import Settings
from app.services.storage import GCSStorage, LocalStorage, build_storage


@pytest.fixture
def local(tmp_path):
    return LocalStorage(tmp_path / "uploads")


async def test_local_roundtrip(local):
    data = "héllo".encode()
    await local.save_bytes("a/b.txt", data)
    assert await local.exists("a/b.txt")
    assert await local.read_text("a/b.txt") == "héllo"
    assert (await local.info("a/b.txt")).size == len(data)


async def test_local_missing_objects(local):
    assert await local.read_text("nope.txt") is None
    assert not await local.exists("nope.txt")
    assert await local.info("nope.txt") is None
    assert await local.delete("nope.txt") is False


async def test_local_list_prefix_and_delete(local):
    for key in ("f1.pdf", "f1_extracted.txt", "f2.pdf", "c/f1.pdf"):
        await local.save_bytes(key, b"x")
    assert await local.list_prefix("f1.") == ["f1.pdf"]
    assert await local.list_prefix("c/") == ["c/f1.pdf"]
    assert await local.delete("f1.pdf") is True
    assert not await local.exists("f1.pdf")


async def test_local_rejects_keys_escaping_the_root(local):
    with pytest.raises(ValueError):
        await local.save_bytes("../escape.txt", b"x")


class FakeBlob:
    def __init__(self, bucket, name):
        self.bucket, self.name = bucket, name

    def upload_from_string(self, data):
        self.bucket.objects[self.name] = (bytes(data), datetime.now(timezone.utc))

    def exists(self):
        return self.name in self.bucket.objects

    def delete(self):
        del self.bucket.objects[self.name]

    def download_as_text(self, encoding="utf-8"):
        return self.bucket.objects[self.name][0].decode(encoding)

    @property
    def size(self):
        return len(self.bucket.objects[self.name][0])

    @property
    def updated(self):
        return self.bucket.objects[self.name][1]


class FakeBucket:
    def __init__(self):
        self.objects = {}

    def blob(self, name):
        return FakeBlob(self, name)

    def get_blob(self, name):
        return FakeBlob(self, name) if name in self.objects else None


class FakeGCSClient:
    def __init__(self):
        self.buckets = {}

    def bucket(self, name):
        return self.buckets.setdefault(name, FakeBucket())

    def list_blobs(self, bucket_name, prefix=""):
        bucket = self.buckets[bucket_name]
        return [FakeBlob(bucket, name) for name in sorted(bucket.objects) if name.startswith(prefix)]


async def test_gcs_roundtrip_against_a_fake_client():
    store = GCSStorage("bkt", client=FakeGCSClient())
    await store.save_bytes("c1/f1.pdf", b"%PDF")
    await store.save_bytes("c1/f1_extracted.txt", "text".encode())
    assert await store.read_text("c1/f1_extracted.txt") == "text"
    assert await store.list_prefix("c1/f1.") == ["c1/f1.pdf"]
    assert (await store.info("c1/f1.pdf")).size == 4
    assert await store.exists("c1/f1.pdf")
    assert await store.delete("c1/f1.pdf") is True
    assert await store.read_text("c1/f1.pdf") is None
    assert await store.info("c1/f1.pdf") is None
    assert await store.delete("c1/f1.pdf") is False


def test_build_storage_defaults_to_local(tmp_path):
    store = build_storage(Settings.from_env({"UPLOAD_DIR": str(tmp_path / "u")}))
    assert isinstance(store, LocalStorage)
