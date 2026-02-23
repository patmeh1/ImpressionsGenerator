"""Azure Cosmos DB service for data persistence."""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any

from azure.cosmos import ContainerProxy, CosmosClient, PartitionKey
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from azure.identity import DefaultAzureCredential

from app.config import settings

logger = logging.getLogger(__name__)


class CosmosDBService:
    """Manages CRUD operations against Azure Cosmos DB."""

    def __init__(self) -> None:
        self._client: CosmosClient | None = None
        self._database = None
        self._containers: dict[str, ContainerProxy] = {}

    async def initialize(self) -> None:
        """Initialize Cosmos DB client and ensure containers exist."""
        credential = DefaultAzureCredential()
        self._client = CosmosClient(
            url=settings.COSMOS_ENDPOINT,
            credential=credential,
        )
        self._database = self._client.create_database_if_not_exists(
            id=settings.COSMOS_DATABASE_NAME
        )

        container_configs = [
            ("doctors", "/id"),
            ("notes", "/doctor_id"),
            ("reports", "/doctor_id"),
            ("style_profiles", "/doctor_id"),
            ("retention_policies", "/id"),
            ("audit_logs", "/id"),
        ]
        for name, pk_path in container_configs:
            self._containers[name] = self._database.create_container_if_not_exists(
                id=name,
                partition_key=PartitionKey(path=pk_path),
            )

        logger.info("Cosmos DB initialized with database '%s'", settings.COSMOS_DATABASE_NAME)

    def _container(self, name: str) -> ContainerProxy:
        if name not in self._containers:
            raise RuntimeError(f"Container '{name}' not initialized")
        return self._containers[name]

    # --- Doctor operations ---

    async def create_doctor(self, data: dict[str, Any]) -> dict[str, Any]:
        doc = {
            "id": str(uuid.uuid4()),
            **data,
            "created_at": datetime.utcnow().isoformat(),
        }
        self._container("doctors").create_item(body=doc)
        logger.info("Created doctor %s", doc["id"])
        return doc

    async def get_doctor(self, doctor_id: str) -> dict[str, Any] | None:
        try:
            return self._container("doctors").read_item(
                item=doctor_id, partition_key=doctor_id
            )
        except CosmosResourceNotFoundError:
            return None

    async def list_doctors(self) -> list[dict[str, Any]]:
        query = "SELECT * FROM c ORDER BY c.created_at DESC"
        return list(self._container("doctors").query_items(
            query=query, enable_cross_partition_query=True
        ))

    async def update_doctor(
        self, doctor_id: str, data: dict[str, Any]
    ) -> dict[str, Any] | None:
        existing = await self.get_doctor(doctor_id)
        if existing is None:
            return None
        existing.update({k: v for k, v in data.items() if v is not None})
        self._container("doctors").replace_item(item=doctor_id, body=existing)
        logger.info("Updated doctor %s", doctor_id)
        return existing

    async def delete_doctor(self, doctor_id: str) -> bool:
        try:
            self._container("doctors").delete_item(
                item=doctor_id, partition_key=doctor_id
            )
            logger.info("Deleted doctor %s", doctor_id)
            return True
        except CosmosResourceNotFoundError:
            return False

    # --- Note operations ---

    async def create_note(self, doctor_id: str, data: dict[str, Any]) -> dict[str, Any]:
        doc = {
            "id": str(uuid.uuid4()),
            "doctor_id": doctor_id,
            **data,
            "created_at": datetime.utcnow().isoformat(),
        }
        self._container("notes").create_item(body=doc)
        logger.info("Created note %s for doctor %s", doc["id"], doctor_id)
        return doc

    async def list_notes(self, doctor_id: str) -> list[dict[str, Any]]:
        query = "SELECT * FROM c WHERE c.doctor_id = @doctor_id ORDER BY c.created_at DESC"
        params = [{"name": "@doctor_id", "value": doctor_id}]
        return list(self._container("notes").query_items(
            query=query, parameters=params, partition_key=doctor_id
        ))

    async def get_note(self, doctor_id: str, note_id: str) -> dict[str, Any] | None:
        try:
            return self._container("notes").read_item(
                item=note_id, partition_key=doctor_id
            )
        except CosmosResourceNotFoundError:
            return None

    async def delete_note(self, doctor_id: str, note_id: str) -> bool:
        try:
            self._container("notes").delete_item(
                item=note_id, partition_key=doctor_id
            )
            logger.info("Deleted note %s for doctor %s", note_id, doctor_id)
            return True
        except CosmosResourceNotFoundError:
            return False

    # --- Report operations ---

    async def create_report(self, data: dict[str, Any]) -> dict[str, Any]:
        now = datetime.utcnow().isoformat()
        doc = {
            "id": str(uuid.uuid4()),
            **data,
            "status": "draft",
            "versions": [],
            "created_at": now,
            "updated_at": now,
        }
        self._container("reports").create_item(body=doc)
        logger.info("Created report %s", doc["id"])
        return doc

    async def get_report(self, report_id: str, doctor_id: str) -> dict[str, Any] | None:
        try:
            return self._container("reports").read_item(
                item=report_id, partition_key=doctor_id
            )
        except CosmosResourceNotFoundError:
            return None

    async def list_reports(
        self, doctor_id: str | None = None
    ) -> list[dict[str, Any]]:
        if doctor_id:
            query = "SELECT * FROM c WHERE c.doctor_id = @doctor_id ORDER BY c.created_at DESC"
            params = [{"name": "@doctor_id", "value": doctor_id}]
            return list(self._container("reports").query_items(
                query=query, parameters=params, partition_key=doctor_id
            ))
        else:
            query = "SELECT * FROM c ORDER BY c.created_at DESC"
            return list(self._container("reports").query_items(
                query=query, enable_cross_partition_query=True
            ))

    async def update_report(
        self, report_id: str, doctor_id: str, data: dict[str, Any]
    ) -> dict[str, Any] | None:
        existing = await self.get_report(report_id, doctor_id)
        if existing is None:
            return None

        # Save current state as a version
        version = {
            "version": len(existing.get("versions", [])) + 1,
            "findings": existing.get("findings", ""),
            "impressions": existing.get("impressions", ""),
            "recommendations": existing.get("recommendations", ""),
            "status": existing.get("status", "draft"),
            "edited_at": datetime.utcnow().isoformat(),
        }
        existing.setdefault("versions", []).append(version)
        existing.update({k: v for k, v in data.items() if v is not None})
        existing["status"] = "edited"
        existing["updated_at"] = datetime.utcnow().isoformat()

        self._container("reports").replace_item(item=report_id, body=existing)
        logger.info("Updated report %s", report_id)
        return existing

    async def approve_report(
        self, report_id: str, doctor_id: str
    ) -> dict[str, Any] | None:
        existing = await self.get_report(report_id, doctor_id)
        if existing is None:
            return None
        existing["status"] = "final"
        existing["updated_at"] = datetime.utcnow().isoformat()
        self._container("reports").replace_item(item=report_id, body=existing)
        logger.info("Approved report %s", report_id)
        return existing

    # --- Style Profile operations ---

    async def get_style_profile(self, doctor_id: str) -> dict[str, Any] | None:
        query = "SELECT * FROM c WHERE c.doctor_id = @doctor_id"
        params = [{"name": "@doctor_id", "value": doctor_id}]
        items = list(self._container("style_profiles").query_items(
            query=query, parameters=params, partition_key=doctor_id
        ))
        return items[0] if items else None

    async def upsert_style_profile(self, data: dict[str, Any]) -> dict[str, Any]:
        data["updated_at"] = datetime.utcnow().isoformat()
        if "id" not in data:
            data["id"] = str(uuid.uuid4())
        self._container("style_profiles").upsert_item(body=data)
        logger.info("Upserted style profile for doctor %s", data.get("doctor_id"))
        return data

    # --- Admin statistics ---

    async def get_stats(self) -> dict[str, Any]:
        doctor_count = len(await self.list_doctors())
        report_query = "SELECT VALUE COUNT(1) FROM c"
        report_count = list(self._container("reports").query_items(
            query=report_query, enable_cross_partition_query=True
        ))
        note_count = list(self._container("notes").query_items(
            query=report_query, enable_cross_partition_query=True
        ))
        return {
            "total_doctors": doctor_count,
            "total_reports": report_count[0] if report_count else 0,
            "total_notes": note_count[0] if note_count else 0,
        }

    async def get_doctors_with_stats(self) -> list[dict[str, Any]]:
        doctors = await self.list_doctors()
        for doctor in doctors:
            doctor_id = doctor["id"]
            notes = await self.list_notes(doctor_id)
            reports = await self.list_reports(doctor_id)
            doctor["note_count"] = len(notes)
            doctor["report_count"] = len(reports)
        return doctors

    # --- Retention policy operations ---

    async def get_retention_policy(self) -> dict[str, Any] | None:
        """Get the current retention policy (singleton document)."""
        query = "SELECT * FROM c WHERE c.id = 'default'"
        items = list(self._container("retention_policies").query_items(
            query=query, partition_key="default"
        ))
        return items[0] if items else None

    async def upsert_retention_policy(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create or update the retention policy."""
        data["id"] = "default"
        data["updated_at"] = datetime.utcnow().isoformat()
        self._container("retention_policies").upsert_item(body=data)
        logger.info("Updated retention policy")
        return data

    # --- Audit log operations ---

    async def create_audit_log(self, entry: dict[str, Any]) -> dict[str, Any]:
        """Record an audit log entry."""
        doc = {
            "id": str(uuid.uuid4()),
            **entry,
            "created_at": datetime.utcnow().isoformat(),
        }
        self._container("audit_logs").create_item(body=doc)
        logger.info("Created audit log: %s", doc.get("action", "unknown"))
        return doc

    # --- Soft delete & purge operations ---

    async def soft_delete_expired_items(
        self, container_name: str, retention_days: int
    ) -> list[dict[str, Any]]:
        """Mark items older than retention_days as soft-deleted. Returns affected items."""
        if retention_days <= 0:
            return []
        cutoff = (datetime.utcnow() - timedelta(days=retention_days)).isoformat()
        query = (
            "SELECT * FROM c WHERE c.created_at < @cutoff "
            "AND (NOT IS_DEFINED(c.deleted_at) OR c.deleted_at = null)"
        )
        params = [{"name": "@cutoff", "value": cutoff}]
        items = list(self._container(container_name).query_items(
            query=query, parameters=params, enable_cross_partition_query=True
        ))
        now = datetime.utcnow().isoformat()
        for item in items:
            item["deleted_at"] = now
            self._container(container_name).upsert_item(body=item)
        logger.info(
            "Soft-deleted %d items from '%s' (older than %d days)",
            len(items), container_name, retention_days,
        )
        return items

    async def purge_soft_deleted_items(
        self, container_name: str, grace_period_days: int
    ) -> int:
        """Permanently delete items that were soft-deleted beyond the grace period."""
        cutoff = (datetime.utcnow() - timedelta(days=grace_period_days)).isoformat()
        query = (
            "SELECT * FROM c WHERE IS_DEFINED(c.deleted_at) "
            "AND c.deleted_at != null AND c.deleted_at < @cutoff"
        )
        params = [{"name": "@cutoff", "value": cutoff}]
        items = list(self._container(container_name).query_items(
            query=query, parameters=params, enable_cross_partition_query=True
        ))
        count = 0
        for item in items:
            pk = item.get("doctor_id", item["id"])
            try:
                self._container(container_name).delete_item(
                    item=item["id"], partition_key=pk
                )
                count += 1
            except CosmosResourceNotFoundError:
                pass
        logger.info(
            "Purged %d items from '%s' (grace period %d days)",
            count, container_name, grace_period_days,
        )
        return count


# Singleton instance
cosmos_service = CosmosDBService()
