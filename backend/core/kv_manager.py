"""
KV Manager - Centralized Consul KV operations with standardized namespacing
Inspired by TenSunS patterns but adapted for async FastAPI architecture
"""
import asyncio
import base64
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from .consul_manager import ConsulManager

logger = logging.getLogger(__name__)


class KVManager:
    """
    Manages Consul KV operations with standardized namespace structure.
    All app data is stored under 'skills/cm/' prefix to avoid conflicts.
    """

    # Root namespace
    PREFIX = "skills/cm"

    # Blackbox namespaces
    BLACKBOX_TARGETS = f"{PREFIX}/blackbox/targets"
    BLACKBOX_GROUPS = f"{PREFIX}/blackbox/groups"
    BLACKBOX_MODULES = f"{PREFIX}/blackbox/modules.json"

    # Service namespaces
    SERVICE_PRESETS = f"{PREFIX}/services/presets"
    SERVICE_TEMPLATES = f"{PREFIX}/services/templates"

    # Settings namespaces
    UI_SETTINGS = f"{PREFIX}/settings/ui.json"
    USER_PREFERENCES = f"{PREFIX}/settings/users"

    # Import/Export tracking
    IMPORTS_LAST = f"{PREFIX}/imports/last.json"
    EXPORTS_HISTORY = f"{PREFIX}/exports/history"

    # Audit logging
    AUDIT_LOG = f"{PREFIX}/audit"

    def __init__(self, consul: Optional[ConsulManager] = None):
        self.consul = consul or ConsulManager()

    # =========================================================================
    # Core KV Operations (with namespacing safety)
    # =========================================================================

    async def get_json(self, key: str, default: Any = None) -> Any:
        """
        Get and decode JSON value from KV store.

        Args:
            key: Full key path (must start with skills/cm/)
            default: Value to return if key doesn't exist

        Returns:
            Decoded JSON object or default value
        """
        self._validate_namespace(key)
        result = await self.consul.get_kv_json(key)
        return result if result is not None else default

    async def put_json(self, key: str, value: Any, metadata: Optional[Dict] = None) -> bool:
        """
        Store JSON value in KV with optional metadata.

        Args:
            key: Full key path (must start with skills/cm/)
            value: Data to store (will be JSON-encoded)
            metadata: Optional metadata (created_at, updated_by, version, etc.)

        Returns:
            True if successful
        """
        self._validate_namespace(key)

        # Wrap value with metadata if provided
        if metadata:
            payload = {
                "data": value,
                "meta": {
                    "created_at": metadata.get("created_at", datetime.utcnow().isoformat()),
                    "updated_at": datetime.utcnow().isoformat(),
                    "updated_by": metadata.get("updated_by", "system"),
                    "version": metadata.get("version", 1),
                    **{k: v for k, v in metadata.items() if k not in ["created_at", "updated_by", "version"]}
                }
            }
        else:
            payload = value

        return await self.consul.put_kv_json(key, payload)

    async def delete_key(self, key: str) -> bool:
        """
        Delete a single key from KV store.

        Args:
            key: Full key path (must start with skills/cm/)

        Returns:
            True if successful
        """
        self._validate_namespace(key)
        return await self.consul.delete_key(key)

    async def delete_tree(self, prefix: str) -> bool:
        """
        Delete all keys under a prefix (recursive delete).

        Args:
            prefix: Prefix path (must start with skills/cm/)

        Returns:
            True if successful
        """
        self._validate_namespace(prefix)
        try:
            await self.consul._request("DELETE", f"/kv/{prefix}?recurse=true")
            return True
        except Exception as exc:
            logger.error("Failed to delete tree %s: %s", prefix, exc)
            return False

    async def list_keys(self, prefix: str) -> List[str]:
        """
        List all keys under a prefix.

        Args:
            prefix: Prefix path (must start with skills/cm/)

        Returns:
            List of key paths
        """
        self._validate_namespace(prefix)
        return await self.consul.list_keys(prefix)

    async def get_tree(self, prefix: str, unwrap_metadata: bool = True) -> Dict[str, Any]:
        """
        Get all key-value pairs under a prefix (recursive).

        Args:
            prefix: Prefix path (must start with skills/cm/)
            unwrap_metadata: If True, extract 'data' from metadata-wrapped values

        Returns:
            Dictionary mapping keys to values
        """
        self._validate_namespace(prefix)
        tree = await self.consul.get_kv_tree(prefix)

        if unwrap_metadata:
            unwrapped = {}
            for key, value in tree.items():
                if isinstance(value, dict) and "data" in value and "meta" in value:
                    unwrapped[key] = value["data"]
                else:
                    unwrapped[key] = value
            return unwrapped

        return tree

    # =========================================================================
    # Blackbox Target Operations
    # =========================================================================

    async def get_blackbox_target(self, target_id: str) -> Optional[Dict]:
        """Get a single blackbox target by ID."""
        key = f"{self.BLACKBOX_TARGETS}/{target_id}.json"
        return await self.get_json(key)

    async def put_blackbox_target(self, target_id: str, target_data: Dict, user: str = "system") -> bool:
        """
        Store a blackbox target in KV.

        Args:
            target_id: Unique target identifier
            target_data: Target configuration (see blueprint schema)
            user: User performing the operation
        """
        key = f"{self.BLACKBOX_TARGETS}/{target_id}.json"

        # Ensure required fields
        target_data.setdefault("id", target_id)
        target_data.setdefault("enabled", True)
        target_data.setdefault("interval", "30s")
        target_data.setdefault("timeout", "10s")

        metadata = {
            "updated_by": user,
            "resource_type": "blackbox_target"
        }

        return await self.put_json(key, target_data, metadata)

    async def delete_blackbox_target(self, target_id: str) -> bool:
        """Delete a blackbox target from KV."""
        key = f"{self.BLACKBOX_TARGETS}/{target_id}.json"
        return await self.delete_key(key)

    async def list_blackbox_targets(self, filters: Optional[Dict[str, str]] = None) -> List[Dict]:
        """
        List all blackbox targets with optional filtering.

        Args:
            filters: Optional dict with keys: group, module, enabled, etc.

        Returns:
            List of target configurations
        """
        tree = await self.get_tree(self.BLACKBOX_TARGETS)
        targets = []

        for key, value in tree.items():
            if not isinstance(value, dict):
                continue

            # Apply filters
            if filters:
                if "group" in filters and value.get("group") != filters["group"]:
                    continue
                if "module" in filters and value.get("module") != filters["module"]:
                    continue
                if "enabled" in filters and value.get("enabled") != filters["enabled"]:
                    continue
                if "labels" in filters:
                    # Check if all filter labels match
                    target_labels = value.get("labels", {})
                    if not all(target_labels.get(k) == v for k, v in filters["labels"].items()):
                        continue

            targets.append(value)

        return targets

    # =========================================================================
    # Blackbox Group Operations
    # =========================================================================

    async def get_blackbox_group(self, group_id: str) -> Optional[Dict]:
        """Get a blackbox target group configuration."""
        key = f"{self.BLACKBOX_GROUPS}/{group_id}.json"
        return await self.get_json(key)

    async def put_blackbox_group(self, group_id: str, group_data: Dict, user: str = "system") -> bool:
        """
        Store a blackbox group configuration.

        Args:
            group_id: Unique group identifier
            group_data: Group configuration (name, filters, labels, etc.)
            user: User performing the operation
        """
        key = f"{self.BLACKBOX_GROUPS}/{group_id}.json"

        group_data.setdefault("id", group_id)

        metadata = {
            "updated_by": user,
            "resource_type": "blackbox_group"
        }

        return await self.put_json(key, group_data, metadata)

    async def list_blackbox_groups(self) -> List[Dict]:
        """List all blackbox target groups."""
        tree = await self.get_tree(self.BLACKBOX_GROUPS)
        return [v for v in tree.values() if isinstance(v, dict)]

    # =========================================================================
    # Service Preset Operations
    # =========================================================================

    async def get_service_preset(self, preset_id: str) -> Optional[Dict]:
        """Get a service registration preset."""
        key = f"{self.SERVICE_PRESETS}/{preset_id}.json"
        return await self.get_json(key)

    async def put_service_preset(self, preset_id: str, preset_data: Dict, user: str = "system") -> bool:
        """
        Store a service preset template.

        Args:
            preset_id: Unique preset identifier (e.g., "node-exporter-linux")
            preset_data: Preset configuration (name, service_name, tags, meta_template, checks)
            user: User performing the operation
        """
        key = f"{self.SERVICE_PRESETS}/{preset_id}.json"

        preset_data.setdefault("id", preset_id)

        metadata = {
            "updated_by": user,
            "resource_type": "service_preset"
        }

        return await self.put_json(key, preset_data, metadata)

    async def list_service_presets(self) -> List[Dict]:
        """List all service presets."""
        tree = await self.get_tree(self.SERVICE_PRESETS)
        return [v for v in tree.values() if isinstance(v, dict)]

    # =========================================================================
    # UI Settings Operations
    # =========================================================================

    async def get_ui_settings(self, user: Optional[str] = None) -> Dict:
        """
        Get UI settings (global or user-specific).

        Args:
            user: Optional user identifier for user-specific settings

        Returns:
            Settings dictionary
        """
        if user:
            key = f"{self.USER_PREFERENCES}/{user}.json"
        else:
            key = self.UI_SETTINGS

        return await self.get_json(key, default={})

    async def put_ui_settings(self, settings: Dict, user: Optional[str] = None) -> bool:
        """
        Store UI settings (global or user-specific).

        Args:
            settings: Settings dictionary (columns, pagination, filters, etc.)
            user: Optional user identifier for user-specific settings
        """
        if user:
            key = f"{self.USER_PREFERENCES}/{user}.json"
        else:
            key = self.UI_SETTINGS

        metadata = {
            "updated_by": user or "system",
            "resource_type": "ui_settings"
        }

        return await self.put_json(key, settings, metadata)

    # =========================================================================
    # Audit Logging
    # =========================================================================

    async def log_audit_event(
        self,
        action: str,
        resource_type: str,
        resource_id: str,
        user: str = "system",
        details: Optional[Dict] = None
    ) -> bool:
        """
        Log an audit event to Consul KV.

        Args:
            action: Action performed (CREATE, UPDATE, DELETE, IMPORT, EXPORT)
            resource_type: Type of resource (service, blackbox_target, preset, etc.)
            resource_id: Identifier of the resource
            user: User who performed the action
            details: Additional details about the action

        Returns:
            True if logged successfully
        """
        now = datetime.utcnow()
        date_path = now.strftime("%Y/%m/%d")

        event = {
            "timestamp": now.isoformat(),
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "user": user,
            "details": details or {}
        }

        # Append to daily log (use timestamp as unique key component)
        key = f"{self.AUDIT_LOG}/{date_path}/{now.strftime('%H%M%S')}-{resource_type}-{resource_id}.json"

        return await self.put_json(key, event)

    async def get_audit_events(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        resource_type: Optional[str] = None,
        action: Optional[str] = None
    ) -> List[Dict]:
        """
        Get audit events with optional filtering.

        Args:
            start_date: Start date (YYYY-MM-DD format)
            end_date: End date (YYYY-MM-DD format)
            resource_type: Filter by resource type
            action: Filter by action

        Returns:
            List of audit events
        """
        # Get all audit logs
        tree = await self.get_tree(self.AUDIT_LOG)
        events = []

        for key, value in tree.items():
            if not isinstance(value, dict):
                continue

            # Apply filters
            if start_date and value.get("timestamp", "") < start_date:
                continue
            if end_date and value.get("timestamp", "") > end_date:
                continue
            if resource_type and value.get("resource_type") != resource_type:
                continue
            if action and value.get("action") != action:
                continue

            events.append(value)

        # Sort by timestamp descending
        events.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        return events

    # =========================================================================
    # Import/Export Tracking
    # =========================================================================

    async def record_import(
        self,
        import_type: str,
        filename: str,
        user: str,
        summary: Dict
    ) -> bool:
        """
        Record details of an import operation.

        Args:
            import_type: Type of import (blackbox_targets, services, etc.)
            filename: Name of the imported file
            user: User who performed the import
            summary: Summary of the import (created, failed, total)
        """
        record = {
            "type": import_type,
            "filename": filename,
            "user": user,
            "timestamp": datetime.utcnow().isoformat(),
            "summary": summary
        }

        # Store as last import
        await self.put_json(self.IMPORTS_LAST, record)

        # Also log to audit
        await self.log_audit_event(
            "IMPORT",
            import_type,
            filename,
            user,
            summary
        )

        return True

    async def get_last_import(self) -> Optional[Dict]:
        """Get details of the last import operation."""
        return await self.get_json(self.IMPORTS_LAST)

    # =========================================================================
    # Utilities
    # =========================================================================

    def _validate_namespace(self, key: str) -> None:
        """
        Ensure key is within the app's namespace.

        Args:
            key: Key path to validate

        Raises:
            ValueError: If key is outside the allowed namespace
        """
        if not key.startswith(self.PREFIX):
            raise ValueError(
                f"Key '{key}' is outside the allowed namespace. "
                f"All keys must start with '{self.PREFIX}/'"
            )

    async def migrate_from_old_namespace(
        self,
        old_prefix: str = "ConsulManager/record/blackbox"
    ) -> Dict[str, int]:
        """
        Migrate data from TenSunS-style namespace to new standardized namespace.

        Args:
            old_prefix: Old KV prefix to migrate from

        Returns:
            Migration summary (migrated count, failed count)
        """
        logger.info("Starting migration from %s to %s", old_prefix, self.PREFIX)

        migrated = 0
        failed = 0

        try:
            # Get all keys from old namespace
            old_tree = await self.consul.get_kv_tree(old_prefix)

            for old_key, value in old_tree.items():
                try:
                    # Map old key to new key structure
                    # Example: ConsulManager/record/blackbox/module_list -> skills/cm/blackbox/modules.json
                    if "module_list" in old_key:
                        new_key = self.BLACKBOX_MODULES
                    else:
                        # Extract relevant path component
                        suffix = old_key.replace(old_prefix, "").lstrip("/")
                        new_key = f"{self.BLACKBOX_TARGETS}/{suffix}"

                    # Store in new namespace
                    success = await self.put_json(new_key, value)

                    if success:
                        migrated += 1
                        logger.debug("Migrated %s -> %s", old_key, new_key)
                    else:
                        failed += 1
                        logger.warning("Failed to migrate %s", old_key)

                except Exception as exc:
                    failed += 1
                    logger.error("Error migrating %s: %s", old_key, exc)

        except Exception as exc:
            logger.error("Migration failed: %s", exc)

        summary = {
            "migrated": migrated,
            "failed": failed,
            "total": migrated + failed
        }

        logger.info("Migration complete: %s", summary)

        return summary
