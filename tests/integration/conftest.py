"""Shared fixtures for integration tests."""

import json
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest


# ---------------------------------------------------------------------------
# Mock Azure Cosmos DB
# ---------------------------------------------------------------------------
class MockCosmosContainer:
    """In-memory mock of an Azure Cosmos DB container."""

    def __init__(self):
        self._items: dict[str, dict[str, Any]] = {}

    async def create_item(self, body: dict) -> dict:
        item_id = body.get("id", f"auto-{len(self._items)}")
        body["id"] = item_id
        self._items[item_id] = body
        return body

    async def read_item(self, item: str, partition_key: str) -> dict:
        if item not in self._items:
            raise Exception(f"NotFound: {item}")
        return self._items[item]

    def query_items(self, query: str, **kwargs) -> list[dict]:
        return list(self._items.values())

    async def upsert_item(self, body: dict) -> dict:
        self._items[body["id"]] = body
        return body

    async def delete_item(self, item: str, partition_key: str) -> None:
        self._items.pop(item, None)


class MockCosmosDatabase:
    def __init__(self):
        self._containers: dict[str, MockCosmosContainer] = {}

    def get_container_client(self, name: str) -> MockCosmosContainer:
        if name not in self._containers:
            self._containers[name] = MockCosmosContainer()
        return self._containers[name]


class MockCosmosClient:
    def __init__(self):
        self._databases: dict[str, MockCosmosDatabase] = {}

    def get_database_client(self, name: str) -> MockCosmosDatabase:
        if name not in self._databases:
            self._databases[name] = MockCosmosDatabase()
        return self._databases[name]


# ---------------------------------------------------------------------------
# Mock Azure Blob Storage
# ---------------------------------------------------------------------------
class MockBlobClient:
    def __init__(self):
        self._blobs: dict[str, bytes] = {}

    async def upload_blob(self, data: bytes, overwrite: bool = False) -> None:
        self._blobs["latest"] = data

    async def download_blob(self) -> MagicMock:
        mock = MagicMock()
        mock.readall = AsyncMock(return_value=self._blobs.get("latest", b""))
        return mock


class MockBlobContainerClient:
    def __init__(self):
        self._blobs: dict[str, MockBlobClient] = {}

    def get_blob_client(self, blob: str) -> MockBlobClient:
        if blob not in self._blobs:
            self._blobs[blob] = MockBlobClient()
        return self._blobs[blob]


class MockBlobServiceClient:
    def __init__(self):
        self._containers: dict[str, MockBlobContainerClient] = {}

    def get_container_client(self, name: str) -> MockBlobContainerClient:
        if name not in self._containers:
            self._containers[name] = MockBlobContainerClient()
        return self._containers[name]


# ---------------------------------------------------------------------------
# Mock OpenAI client
# ---------------------------------------------------------------------------
class MockOpenAIClient:
    """Returns canned generation and style-extraction responses."""

    def __init__(self):
        self.chat = MagicMock()
        self.chat.completions = MagicMock()
        self.chat.completions.create = AsyncMock(side_effect=self._generate)

    async def _generate(self, **kwargs) -> MagicMock:
        messages = kwargs.get("messages", [])
        system = messages[0]["content"] if messages else ""

        if "extract" in system.lower() or system.lower().startswith("extract"):
            payload = {
                "vocabulary_patterns": ["unremarkable", "within normal limits"],
                "abbreviation_map": {"CT": "computed tomography"},
                "sentence_structure": ["short declarative"],
                "section_ordering": ["findings", "impressions", "recommendations"],
                "sample_phrases": ["No acute abnormality."],
            }
        else:
            payload = {
                "findings": "Normal CT findings. Liver 14.5 cm.",
                "impressions": "No acute abnormality.",
                "recommendations": "No follow-up needed.",
            }

        choice = MagicMock()
        choice.message.content = json.dumps(payload)
        response = MagicMock()
        response.choices = [choice]
        return response


# ---------------------------------------------------------------------------
# Mock AI Search
# ---------------------------------------------------------------------------
class MockSearchClient:
    def __init__(self):
        self._documents: list[dict] = []

    async def search(self, search_text: str, **kwargs) -> list[dict]:
        return [d for d in self._documents if search_text.lower() in json.dumps(d).lower()]

    async def upload_documents(self, documents: list[dict]) -> None:
        self._documents.extend(documents)

    async def delete_documents(self, documents: list[dict]) -> None:
        ids = {d.get("id") for d in documents}
        self._documents = [d for d in self._documents if d.get("id") not in ids]


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------
@pytest.fixture()
def cosmos_client():
    return MockCosmosClient()


@pytest.fixture()
def blob_client():
    return MockBlobServiceClient()


@pytest.fixture()
def openai_client():
    return MockOpenAIClient()


@pytest.fixture()
def search_client():
    return MockSearchClient()


@pytest.fixture()
def sample_doctor():
    return {
        "id": "doctor-int-001",
        "name": "Dr. Integration Test",
        "specialty": "Radiology",
        "department": "Imaging",
        "created_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture()
def sample_notes():
    return [
        {
            "id": f"note-int-{i}",
            "doctor_id": "doctor-int-001",
            "content": f"Sample radiology note #{i}. Liver unremarkable. No acute abnormality.",
            "source_type": "paste",
            "file_name": None,
            "created_at": datetime.utcnow().isoformat(),
        }
        for i in range(1, 4)
    ]
