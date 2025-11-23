"""
Async Blackbox manager built on top of ConsulManager.

Responsible for listing, creating, updating and deleting blackbox_exporter
targets as well as generating auxiliary configuration snippets (rules,
blackbox.yml and Prometheus job configuration).
"""
from __future__ import annotations

import csv
import io
import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    import pandas as pd
except ImportError:  # pragma: no cover - optional dependency for XLSX import
    pd = None  # type: ignore

from .consul_manager import ConsulManager
from .config import Config
from .kv_manager import KVManager
from .naming_utils import apply_site_suffix, extract_site_from_metadata

logger = logging.getLogger(__name__)

INVALID_FIELD_PATTERN = re.compile(r'[\[\] `~!\\/#$^&*=|"{}\':;?\t\n]')


class BlackboxManager:
    """
    Enhanced Blackbox manager with dual storage:
    - Consul Services (for Prometheus service discovery)
    - Consul KV (for advanced configuration and grouping)

    Mirrors TenSunS blackbox features while maintaining async FastAPI architecture.
    """

    MODULE_KV_PATH = "ConsulManager/record/blackbox/module_list"  # Legacy path
    # NOTA: ENABLE_KV_STORAGE flag removida (2025-01-09) - dual storage eliminado
    # Targets agora gerenciados EXCLUSIVAMENTE via Services API

    def __init__(self, consul: Optional[ConsulManager] = None, kv: Optional[KVManager] = None) -> None:
        self.consul = consul or ConsulManager()
        self.kv = kv or KVManager(self.consul)

    # --------------------------------------------------------------------- #
    # Target listing helpers
    # --------------------------------------------------------------------- #

    async def list_targets(
        self,
        module: Optional[str] = None,
        company: Optional[str] = None,
        project: Optional[str] = None,
        env: Optional[str] = None,
        group: Optional[str] = None,
        node: Optional[str] = None,
        persist_modules: bool = False,
    ) -> Dict[str, Any]:
        """
        Returns blackbox targets plus metadata lists for filters.

        When persist_modules=True the discovered modules are written to Consul KV
        (replicating TenSunS behaviour).
        """
        services = await self._fetch_blackbox_services()
        metas = []
        detailed = []

        filters = {
            "module": module,
            "company": company,
            "project": project,
            "env": env,
            "group": group,
        }

        # NOTA: Código KV removido (2025-01-09) - dados agora exclusivamente no Services API

        for item in services:
            meta = item.get("Meta") or {}
            if not meta:
                continue
            if node and item.get("Node") != node:
                continue

            target_id = item.get("ID")
            kv_data = {}  # Mantido por compatibilidade, sempre vazio

            composed_meta = self._compose_meta(meta, kv_data)
            if item.get("Node"):
                composed_meta["node"] = item.get("Node")

            if not self._matches_filters(composed_meta, filters):
                continue

            metas.append(composed_meta)
            detailed.append(
                {
                    "service_id": target_id,
                    "service": item.get("Service"),
                    "tags": item.get("Tags") or [],
                    "address": item.get("Address"),
                    "port": item.get("Port"),
                    "meta": composed_meta,
                    "kv": kv_data,
                    "node": item.get("Node"),
                }
            )

        module_list = await self._build_module_list(metas, persist_modules)
        company_list = self._unique_values(metas, "company")
        project_list = self._unique_values(metas, "project")
        env_list = self._unique_values(metas, "env")
        group_list = self._unique_values(metas, "group")
        node_list = sorted({item.get("Node") for item in services if item.get("Node")})

        summary = self._build_summary(detailed)

        return {
            "all_list": metas,
            "services": detailed,
            "module_list": module_list,
            "company_list": company_list,
            "project_list": project_list,
            "env_list": env_list,
            "group_list": group_list,
            "node_list": node_list,
            "summary": summary,
        }

    async def list_all_targets(self) -> Dict[str, Any]:
        """Shortcut for list_targets without filters and persisting modules."""
        return await self.list_targets(persist_modules=True)

    async def _fetch_blackbox_services(self) -> List[Dict[str, Any]]:
        """
        Returns the raw Consul service entries for blackbox exporters across the cluster.

        ✅ SPRINT 1 CORREÇÃO (2025-11-15): Catalog API com fallback
        """
        all_services = await self.consul.get_all_services_catalog(use_fallback=True)

        # Extrair metadata de fallback
        metadata_info = all_services.pop("_metadata", None)
        if metadata_info:
            logger.info(
                f"[Blackbox] Dados obtidos via {metadata_info.get('source_name', 'unknown')} "
                f"em {metadata_info.get('total_time_ms', 0)}ms"
            )
            if not metadata_info.get('is_master', True):
                logger.warning(f"⚠️ [Blackbox] Master offline! Usando fallback")

        results: List[Dict[str, Any]] = []

        for node_name, services in (all_services or {}).items():
            for service in (services or {}).values():
                if service.get("Service") != "blackbox_exporter":
                    continue
                entry = service.copy()
                entry["Node"] = node_name
                results.append(entry)

        if not results:
            # Fallback to local agent if cluster query failed
            response = await self.consul.query_agent_services('Service == "blackbox_exporter"')
            for item in response.values():
                entry = item.copy()
                entry.setdefault("Node", self.consul.host)
                results.append(entry)

        return results

    @staticmethod
    def _matches_filters(meta: Dict[str, Any], filters: Dict[str, Optional[str]]) -> bool:
        for key, value in filters.items():
            if value and meta.get(key) != value:
                return False
        return True

    async def _build_module_list(self, metas: List[Dict[str, Any]], persist_modules: bool) -> List[str]:
        discovered = sorted({meta.get("module") for meta in metas if meta.get("module")})

        stored_modules: List[str] = []
        stored_value = await self.kv.get_json(self.kv.BLACKBOX_MODULES, None)
        if stored_value is None:
            stored_value = await self.consul.get_kv_json(self.MODULE_KV_PATH)

        if isinstance(stored_value, dict):
            stored_modules = stored_value.get("module_list", []) or []
        elif isinstance(stored_value, list):
            stored_modules = stored_value

        base_list = stored_modules or discovered
        missing = [m for m in Config.BLACKBOX_MODULES if m not in base_list]

        module_list = base_list.copy()
        if missing:
            module_list += ["---"] + missing

        if persist_modules and discovered:
            await self.kv.put_json(self.kv.BLACKBOX_MODULES, {"modules": sorted(discovered)})

        return module_list

    @staticmethod
    def _unique_values(metas: List[Dict[str, Any]], field: str) -> List[str]:
        return sorted({meta.get(field) for meta in metas if meta.get(field)})

    def _compose_meta(self, service_meta: Dict[str, Any], kv_meta: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normaliza metadados vindos do Consul e complementa com dados persistidos no KV.
        """
        meta: Dict[str, Any] = {
            "module": service_meta.get("module") or kv_meta.get("module"),
            "company": service_meta.get("company") or kv_meta.get("company"),
            "project": service_meta.get("project") or kv_meta.get("project"),
            "env": service_meta.get("env") or kv_meta.get("env"),
            "name": service_meta.get("name") or kv_meta.get("name"),
            "instance": service_meta.get("instance") or kv_meta.get("target") or kv_meta.get("instance"),
        }

        meta["group"] = service_meta.get("group") or kv_meta.get("group")
        meta["interval"] = service_meta.get("interval") or kv_meta.get("interval") or "30s"
        meta["timeout"] = service_meta.get("timeout") or kv_meta.get("timeout") or "10s"

        # IMPORTANTE: Incluir datacenter do service_meta (vem do Consul)
        if "datacenter" in service_meta:
            meta["datacenter"] = service_meta.get("datacenter")

        enabled_raw = kv_meta.get("enabled")
        if enabled_raw is None:
            enabled_raw = service_meta.get("enabled")
        meta["enabled"] = self._parse_bool(enabled_raw)

        labels_raw = kv_meta.get("labels") or service_meta.get("labels")
        if isinstance(labels_raw, str):
            try:
                meta["labels"] = json.loads(labels_raw)
            except json.JSONDecodeError:
                meta["labels"] = {}
        else:
            meta["labels"] = labels_raw or {}

        if "notes" in kv_meta:
            meta["notes"] = kv_meta.get("notes")

        return meta

    @staticmethod
    def _parse_bool(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() not in {"false", "0", "no"}
        if value is None:
            return True
        return bool(value)

    @staticmethod
    def _build_summary(detailed: List[Dict[str, Any]]) -> Dict[str, Any]:
        total = len(detailed)
        by_module: Dict[str, int] = {}
        by_group: Dict[str, int] = {}
        enabled_count = 0

        for item in detailed:
            meta = item.get("meta", {})
            module = meta.get("module") or "desconhecido"
            group = meta.get("group") or "sem-grupo"
            by_module[module] = by_module.get(module, 0) + 1
            by_group[group] = by_group.get(group, 0) + 1
            if meta.get("enabled", True):
                enabled_count += 1

        return {
            "total": total,
            "enabled": enabled_count,
            "disabled": total - enabled_count,
            "by_module": by_module,
            "by_group": by_group,
        }

    # --------------------------------------------------------------------- #
    # Target mutations
    # --------------------------------------------------------------------- #

    async def add_target(
        self,
        module: str,
        company: str,
        project: str,
        env: str,
        name: str,
        instance: str,
        group: Optional[str] = None,
        labels: Optional[Dict[str, str]] = None,
        interval: str = "30s",
        timeout: str = "10s",
        enabled: bool = True,
        notes: Optional[str] = None,
        user: str = "system",
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Registers a new blackbox target with dual storage.

        Args:
            module: Blackbox module (http_2xx, icmp, tcp_connect, etc.)
            company: Company name
            project: Project name
            env: Environment (prod, dev, staging, etc.)
            name: Friendly name for the target
            instance: Target URL/IP/hostname
            group: Optional group identifier for organizing targets
            labels: Optional additional labels for Prometheus
            interval: Scrape interval (default: 30s)
            timeout: Scrape timeout (default: 10s)
            enabled: Whether target is enabled (default: True)
            notes: Optional notes/description
            user: User performing the operation

        Returns:
            Tuple of (success, reason, detail)
        """
        try:
            service_id, service_payload = self._build_service_payload(
                module=module,
                company=company,
                project=project,
                env=env,
                name=name,
                instance=instance,
                group=group,
                labels=labels,
                interval=interval,
                timeout=timeout,
                enabled=enabled,
            )
        except ValueError as exc:
            return False, "validation_error", str(exc)

        # Register service for Prometheus service discovery
        success = await self.consul.register_service(service_payload)
        if not success:
            return False, "consul_error", "Failed to register service with Consul"

        # NOTA: Código KV removido (2025-01-09) - target agora apenas no Services API
        # Mantém apenas audit log
        await self.kv.log_audit_event(
            action="CREATE",
            resource_type="blackbox_target",
            resource_id=service_id,
            user=user,
            details={"module": module, "instance": instance, "group": group}
        )

        return True, "created", service_id

    async def delete_target(
        self,
        module: str,
        company: str,
        project: str,
        env: str,
        name: str,
        user: str = "system",
    ) -> Tuple[bool, str]:
        """
        Removes a blackbox target from both Consul service and KV storage.

        Args:
            module: Blackbox module
            company: Company name
            project: Project name
            env: Environment
            name: Target name
            user: User performing the operation

        Returns:
            Tuple of (success, message/service_id)
        """
        try:
            service_id = self._compose_service_id(module, company, project, env, name)
        except ValueError as exc:
            return False, str(exc)

        # Deregister service
        success = await self.consul.deregister_service(service_id)
        if not success:
            return False, "Failed to deregister service from Consul"

        # NOTA: Código KV removido (2025-01-09) - target agora apenas no Services API
        # Mantém apenas audit log
        await self.kv.log_audit_event(
            action="DELETE",
            resource_type="blackbox_target",
            resource_id=service_id,
            user=user,
            details={"module": module, "company": company, "project": project, "env": env, "name": name}
        )

        return True, service_id

    async def update_target(
        self,
        old_target: Dict[str, str],
        new_target: Dict[str, str],
    ) -> Tuple[bool, str]:
        """Updates a target by removing and re-adding it."""
        delete_ok, delete_msg = await self.delete_target(
            old_target["module"],
            old_target["company"],
            old_target["project"],
            old_target["env"],
            old_target["name"],
        )
        if not delete_ok:
            return False, f"delete_failed: {delete_msg}"

        add_ok, _, add_detail = await self.add_target(
            new_target["module"],
            new_target["company"],
            new_target["project"],
            new_target["env"],
            new_target["name"],
            new_target["instance"],
            new_target.get("group"),
            new_target.get("labels"),
            new_target.get("interval", "30s"),
            new_target.get("timeout", "10s"),
            new_target.get("enabled", True),
        )
        if add_ok:
            return True, add_detail or ""
        return False, add_detail or "Failed to recreate service"

    def _build_service_payload(
        self,
        module: str,
        company: str,
        project: str,
        env: str,
        name: str,
        instance: str,
        group: Optional[str],
        labels: Optional[Dict[str, str]],
        interval: str,
        timeout: str,
        enabled: bool,
    ) -> Tuple[str, Dict[str, Any]]:
        service_id = self._compose_service_id(module, company, project, env, name)
        meta: Dict[str, str] = {
            "module": module,
            "company": company,
            "project": project,
            "env": env,
            "name": name,
            "instance": instance,
            "interval": interval,
            "timeout": timeout,
            "enabled": "true" if enabled else "false",
        }
        if group:
            meta["group"] = group
        if labels:
            meta["labels"] = json.dumps(labels, ensure_ascii=False)
            # Adicionar labels adicionais ao Meta para suportar campos dinâmicos
            # (company, project, env, site, remote_site, etc)
            # IMPORTANTE: External labels do Prometheus NÃO devem ser injetados aqui!
            # External labels são configurados no prometheus.yml e aplicados GLOBALMENTE
            # pelo próprio Prometheus a todas as métricas coletadas.
            for label_key, label_value in labels.items():
                if label_key not in meta:  # Não sobrescrever campos existentes
                    meta[label_key] = label_value

        payload = {
            "id": service_id,
            "name": "blackbox_exporter",
            "tags": [tag for tag in {module, env, project, company} if tag],
            "Meta": meta,
        }
        if group:
            payload["tags"].append(group)

        # MULTI-SITE SUPPORT: Adicionar tag automática baseado no campo "site"
        # Se os labels contêm campo "site", adicionar como tag para filtros no prometheus.yml
        if labels and "site" in labels:
            site = labels["site"]
            if site and site not in payload["tags"]:
                payload["tags"].append(site)
                logger.info(f"Adicionada tag automática para site: {site}")

        # MULTI-SITE SUPPORT: Aplicar sufixo ao service name (Opção 2)
        # Se NAMING_STRATEGY=option2 e site != DEFAULT_SITE, adiciona sufixo _site
        # Exemplo: blackbox_exporter + site=rio → blackbox_exporter_rio
        if payload["name"]:
            original_name = payload["name"]
            site = extract_site_from_metadata(meta)
            cluster = meta.get("cluster")

            # Aplicar sufixo baseado na configuração
            suffixed_name = apply_site_suffix(original_name, site=site, cluster=cluster)

            if suffixed_name != original_name:
                payload["name"] = suffixed_name
                logger.info(f"[MULTI-SITE] Blackbox service name alterado: {original_name} → {suffixed_name} (site={site})")

        return service_id, payload

    @staticmethod
    def _compose_service_id(module: str, company: str, project: str, env: str, name: str) -> str:
        raw_id = f"{module}/{company}/{project}/{env}@{name}"
        return ConsulManager.sanitize_service_id(raw_id)

    # --------------------------------------------------------------------- #
    # Bulk import helpers
    # --------------------------------------------------------------------- #

    async def import_from_csv(self, content: bytes) -> Dict[str, Any]:
        rows = self._parse_csv(content)
        return await self._bulk_import(rows)

    async def import_from_excel(self, content: bytes) -> Dict[str, Any]:
        if pd is None:
            raise ValueError("Excel import requires pandas and openpyxl in the environment")
        rows = self._parse_excel(content)
        return await self._bulk_import(rows)

    async def _bulk_import(self, rows: List[List[str]]) -> Dict[str, Any]:
        created = 0
        failures: List[Dict[str, Any]] = []

        for index, row in enumerate(rows, start=1):
            try:
                target = self._normalize_row(row)
            except ValueError as exc:
                failures.append({"row": index, "error": str(exc), "values": row})
                continue

            success, reason, detail = await self.add_target(**target)
            if success:
                created += 1
            else:
                failures.append({"row": index, "error": reason, "detail": detail, "values": row})

        return {"created": created, "failed": failures, "total": len(rows)}

    def _normalize_row(self, row: Iterable[Any]) -> Dict[str, str]:
        cells = list(row)
        if len(cells) < 6:
            raise ValueError("Row must have at least 6 columns: module, company, project, env, name, instance")

        module = self._clean_generic_cell(cells[0])
        company = self._clean_generic_cell(cells[1])
        project = self._clean_generic_cell(cells[2])
        env = self._clean_generic_cell(cells[3])
        name = self._clean_generic_cell(cells[4])
        instance = self._clean_instance_cell(cells[5])

        group = ""
        interval = ""
        timeout = ""
        enabled_text = ""
        labels_text = ""

        if len(cells) > 6:
            group = self._stringify(cells[6]).strip()
        if len(cells) > 7:
            interval = self._stringify(cells[7]).strip()
        if len(cells) > 8:
            timeout = self._stringify(cells[8]).strip()
        if len(cells) > 9:
            enabled_text = self._stringify(cells[9]).strip()
        if len(cells) > 10:
            labels_text = self._stringify(cells[10]).strip()

        labels_dict: Dict[str, str] = {}
        if labels_text:
            if labels_text.startswith("{"):
                try:
                    labels_dict = json.loads(labels_text)
                except json.JSONDecodeError:
                    labels_dict = {}
            else:
                parts = re.split(r"[;,]", labels_text)
                for part in parts:
                    if "=" in part:
                        key, value = part.split("=", 1)
                        labels_dict[key.strip()] = value.strip()

        enabled_flag = enabled_text.lower() not in {"false", "0", "no"} if enabled_text else True

        return {
            "module": module,
            "company": company,
            "project": project,
            "env": env,
            "name": name,
            "instance": instance,
            "group": group or None,
            "interval": interval or "30s",
            "timeout": timeout or "10s",
            "enabled": enabled_flag,
            "labels": labels_dict or None,
        }

    @staticmethod
    def _stringify(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value).strip()

    def _clean_generic_cell(self, value: Any) -> str:
        text = self._stringify(value)
        text = text or "_"
        return INVALID_FIELD_PATTERN.sub("_", text)

    def _clean_instance_cell(self, value: Any) -> str:
        text = self._stringify(value)
        if not text:
            raise ValueError("Instance (target) can not be empty")
        return text

    @staticmethod
    def _parse_csv(content: bytes) -> List[List[str]]:
        csv_file = io.StringIO(content.decode("utf-8-sig"))
        reader = csv.reader(csv_file)
        rows: List[List[str]] = []
        for index, row in enumerate(reader):
            if index == 0:  # header
                continue
            if not any(row):
                continue
            rows.append(row)
        return rows

    @staticmethod
    def _parse_excel(content: bytes) -> List[List[str]]:
        buffer = io.BytesIO(content)
        dataframe = pd.read_excel(buffer, engine="openpyxl")  # type: ignore
        rows: List[List[str]] = []
        for _, record in dataframe.iterrows():
            row = [record.iloc[i] if i < len(record) else "" for i in range(11)]
            rows.append(row)
        return rows

    # --------------------------------------------------------------------- #
    # Group Management
    # --------------------------------------------------------------------- #

    async def create_group(
        self,
        group_id: str,
        name: str,
        filters: Optional[Dict[str, str]] = None,
        labels: Optional[Dict[str, str]] = None,
        description: Optional[str] = None,
        user: str = "system",
    ) -> Tuple[bool, str]:
        """
        Create a blackbox target group for organizing targets.

        Args:
            group_id: Unique group identifier
            name: Friendly group name
            filters: Optional filters to auto-include targets (e.g., {"company": "Ramada", "project": "web"})
            labels: Optional labels to apply to all group members
            description: Optional group description
            user: User creating the group

        Returns:
            Tuple of (success, message)
        """
        group_data = {
            "id": group_id,
            "name": name,
            "filters": filters or {},
            "labels": labels or {},
            "description": description,
            "created_at": datetime.utcnow().isoformat()
        }

        success = await self.kv.put_blackbox_group(group_id, group_data, user)

        if success:
            await self.kv.log_audit_event(
                action="CREATE",
                resource_type="blackbox_group",
                resource_id=group_id,
                user=user,
                details={"name": name, "filters": filters}
            )
            return True, f"Group '{name}' created successfully"

        return False, "Failed to create group"

    async def list_groups(self) -> List[Dict]:
        """List all blackbox target groups."""
        return await self.kv.list_blackbox_groups()

    async def get_group(self, group_id: str) -> Optional[Dict]:
        """Get a specific group configuration."""
        return await self.kv.get_blackbox_group(group_id)

    async def get_group_members(self, group_id: str) -> List[Dict]:
        """
        Get all targets belonging to a group.

        IMPORTANTE: Agora busca diretamente do Services API (source of truth).
        Grupos são armazenados em Meta.group dos services blackbox_exporter.

        Returns:
            List of target configurations (format: services from list_targets)
        """
        # Buscar todos os targets do grupo via Services API
        result = await self.list_targets(group=group_id)

        # Retornar lista de services (cada service tem: service_id, meta, tags, etc)
        return result.get("services", [])

    async def bulk_enable_disable(
        self,
        group_id: Optional[str] = None,
        target_ids: Optional[List[str]] = None,
        enabled: bool = True,
        user: str = "system",
    ) -> Dict[str, Any]:
        """
        Enable or disable multiple targets (by group or explicit list).

        IMPORTANTE: Agora atualiza diretamente nos Services API (source of truth).
        O campo enabled é armazenado em Meta.enabled do service.

        Args:
            group_id: Optional group ID to enable/disable all members
            target_ids: Optional explicit list of target IDs
            enabled: True to enable, False to disable
            user: User performing the operation

        Returns:
            Summary of operation (success_count, failed_count, details)
        """
        services_to_update = []

        # PASSO 1: Coletar targets do grupo OU da lista de IDs
        if group_id:
            # Buscar targets do grupo via Services API
            services_to_update = await self.get_group_members(group_id)
        elif target_ids:
            # Buscar cada target individualmente do Services API
            for tid in target_ids:
                service = await self.consul.get_service_by_id(tid)
                if service:
                    services_to_update.append({"service_id": tid, "meta": service.get("Meta", {})})

        success_count = 0
        failed_count = 0
        details = []

        # PASSO 2: Atualizar cada target via update_target()
        for service_item in services_to_update:
            try:
                # Extrair meta atual do service
                if "meta" in service_item:
                    meta = service_item["meta"]
                    target_id = service_item.get("service_id")
                else:
                    # Formato vindo de get_group_members (tem estrutura completa)
                    meta = service_item.get("meta", {})
                    target_id = service_item.get("service_id")

                # Montar target no formato esperado por update_target()
                old_target = {
                    "module": meta.get("module", ""),
                    "company": meta.get("company", ""),
                    "project": meta.get("project", ""),
                    "env": meta.get("env", ""),
                    "name": meta.get("name", ""),
                    "instance": meta.get("instance", ""),
                    "group": meta.get("group"),
                    "labels": meta.get("labels"),
                    "interval": meta.get("interval", "30s"),
                    "timeout": meta.get("timeout", "10s"),
                    "enabled": not enabled  # Valor antigo (invertido)
                }

                new_target = old_target.copy()
                new_target["enabled"] = enabled  # Novo valor

                # Atualizar via update_target() que já gerencia Services API
                update_success, update_msg = await self.update_target(old_target, new_target)

                if update_success:
                    success_count += 1
                    # Log audit event
                    await self.kv.log_audit_event(
                        action="UPDATE",
                        resource_type="blackbox_target",
                        resource_id=target_id,
                        user=user,
                        details={"enabled": enabled, "group": group_id}
                    )
                else:
                    failed_count += 1
                    details.append({"id": target_id, "error": update_msg})

            except Exception as e:
                failed_count += 1
                details.append({"id": service_item.get("service_id", "unknown"), "error": str(e)})

        return {
            "success_count": success_count,
            "failed_count": failed_count,
            "total": len(services_to_update),
            "details": details
        }

    # --------------------------------------------------------------------- #
    # Static configuration snippets
    # --------------------------------------------------------------------- #

    @staticmethod
    def get_rules_snippet() -> str:
        return """- name: Domain
  rules:
  - alert: EndpointDown
    expr: probe_success{job="blackbox_exporter"} == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      description: "{{ $labels.env }} {{ $labels.name }} ({{ $labels.project }}): endpoint unreachable\\n> {{ $labels.instance }}"

  - alert: AvailabilityBelow80
    expr: sum_over_time(probe_success{job="blackbox_exporter"}[1h])/count_over_time(probe_success{job="blackbox_exporter"}[1h]) * 100 < 80
    for: 3m
    labels:
      severity: warning
    annotations:
      description: "{{ $labels.env }} {{ $labels.name }} ({{ $labels.project }}): 1h availability {{ $value | humanize }}%\\n> {{ $labels.instance }}"

  - alert: HttpErrors
    expr: (probe_success{job="blackbox_exporter"} == 0 and probe_http_status_code > 499) or probe_http_status_code == 0
    for: 1m
    labels:
      severity: warning
    annotations:
      description: "{{ $labels.env }} {{ $labels.name }} ({{ $labels.project }}): HTTP status {{ $value }}\\n> {{ $labels.instance }}"

  - alert: SlowResponse
    expr: probe_duration_seconds > 0.5
    for: 2m
    labels:
      severity: warning
    annotations:
      description: "{{ $labels.env }} {{ $labels.name }} ({{ $labels.project }}): latency {{ $value | humanize }}s\\n> {{ $labels.instance }}"

  - alert: SSLCertificateExpiring
    expr: (probe_ssl_earliest_cert_expiry-time()) / 3600 / 24 < 15
    for: 2m
    labels:
      severity: warning
    annotations:
      description: "{{ $labels.env }} {{ $labels.name }} ({{ $labels.project }}): certificate expires in {{ $value | humanize }} days\\n> {{ $labels.instance }}"
"""

    @staticmethod
    def get_blackbox_config_snippet() -> str:
        return """modules:
  http_2xx:
    prober: http
    http:
      valid_status_codes: [200, 204]
      preferred_ip_protocol: ip4
      ip_protocol_fallback: false

  httpNoRedirect4ssl:
    prober: http
    http:
      valid_status_codes: [200, 204, 301, 302, 303]
      no_follow_redirects: true
      preferred_ip_protocol: ip4
      ip_protocol_fallback: false

  http200igssl:
    prober: http
    http:
      valid_status_codes:
      - 200
      tls_config:
        insecure_skip_verify: true

  http_4xx:
    prober: http
    http:
      valid_status_codes: [401, 403, 404]
      preferred_ip_protocol: ip4
      ip_protocol_fallback: false

  http_5xx:
    prober: http
    http:
      valid_status_codes: [500, 502]
      preferred_ip_protocol: ip4
      ip_protocol_fallback: false

  http_post_2xx:
    prober: http
    http:
      method: POST

  icmp:
    prober: icmp

  tcp_connect:
    prober: tcp

  ssh_banner:
    prober: tcp
    tcp:
      query_response:
      - expect: "^SSH-2.0-"
      - send: "SSH-2.0-blackbox-ssh-check"
"""

    @staticmethod
    def get_prometheus_config_snippet(consul_server: Optional[str] = None, consul_token: Optional[str] = None) -> str:
        server = consul_server or f"{Config.MAIN_SERVER}:{Config.CONSUL_PORT}"
        token = consul_token or Config.CONSUL_TOKEN
        return f"""  - job_name: 'blackbox_exporter'
    scrape_interval: 15s
    scrape_timeout: 5s
    metrics_path: /probe
    consul_sd_configs:
    - server: '{server}'
      token: '{token}'
      services: ['blackbox_exporter']
    relabel_configs:
    - source_labels: ["__meta_consul_service_metadata_instance"]
      target_label: __param_target
    - source_labels: [__meta_consul_service_metadata_module]
      target_label: __param_module
    - source_labels: [__meta_consul_service_metadata_module]
      target_label: module
    - source_labels: ["__meta_consul_service_metadata_company"]
      target_label: company
    - source_labels: ["__meta_consul_service_metadata_env"]
      target_label: env
    - source_labels: ["__meta_consul_service_metadata_name"]
      target_label: name
    - source_labels: ["__meta_consul_service_metadata_project"]
      target_label: project
    - source_labels: [__param_target]
      target_label: instance
    - target_label: __address__
      replacement: 127.0.0.1:9115
"""
