"""
Service Preset Manager
Manages reusable service registration templates with variable substitution.
Inspired by TenSunS patterns but enhanced for Skills Consul Manager.
"""
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from string import Template

from .consul_manager import ConsulManager
from .kv_manager import KVManager


class ServicePresetManager:
    """
    Manages service registration presets (templates) for common service types.

    Presets allow quick registration of services with predefined:
    - Health checks
    - Tags
    - Metadata structure
    - Port defaults
    - Common configurations

    Examples:
    - node_exporter (Linux)
    - windows_exporter (Windows)
    - blackbox_exporter
    - Custom application services
    """

    def __init__(self, consul: Optional[ConsulManager] = None, kv: Optional[KVManager] = None):
        self.consul = consul or ConsulManager()
        self.kv = kv or KVManager(self.consul)

    # =========================================================================
    # Preset CRUD Operations
    # =========================================================================

    async def create_preset(
        self,
        preset_id: str,
        name: str,
        service_name: str,
        port: Optional[int] = None,
        tags: Optional[List[str]] = None,
        meta_template: Optional[Dict[str, str]] = None,
        checks: Optional[List[Dict[str, Any]]] = None,
        description: Optional[str] = None,
        category: str = "custom",
        user: str = "system",
    ) -> Tuple[bool, str]:
        """
        Create a new service preset template.

        Args:
            preset_id: Unique preset identifier (e.g., "node-exporter-linux")
            name: Friendly name (e.g., "Node Exporter (Linux)")
            service_name: Consul service name (e.g., "node_exporter")
            port: Default port (e.g., 9100)
            tags: Default tags (e.g., ["monitoring", "linux"])
            meta_template: Metadata template with variables (e.g., {"env": "${env}"})
            checks: Health check definitions
            description: Preset description
            category: Category (exporter, application, database, etc.)
            user: User creating the preset

        Returns:
            Tuple of (success, message)
        """
        # PASSO 1: Verificar se preset já existe (evitar audit logs duplicados)
        existing_preset = await self.get_preset(preset_id)
        is_update = existing_preset is not None

        preset_data = {
            "id": preset_id,
            "name": name,
            "service_name": service_name,
            "port": port,
            "tags": tags or [],
            "meta_template": meta_template or {},
            "checks": checks or [],
            "description": description,
            "category": category,
        }

        # PASSO 2: Preservar created_at se for update, ou criar novo timestamp
        if is_update and "created_at" in existing_preset:
            preset_data["created_at"] = existing_preset["created_at"]
            preset_data["updated_at"] = datetime.utcnow().isoformat()
        else:
            preset_data["created_at"] = datetime.utcnow().isoformat()

        # PASSO 3: Validar estrutura do preset
        is_valid, errors = self._validate_preset(preset_data)
        if not is_valid:
            return False, f"Validation failed: {', '.join(errors)}"

        # PASSO 4: Salvar no KV
        success = await self.kv.put_service_preset(preset_id, preset_data, user)

        if success:
            # PASSO 5: Logar audit event APENAS se for criação nova
            # Isso evita centenas de logs duplicados durante desenvolvimento/testes
            if not is_update:
                await self.kv.log_audit_event(
                    action="CREATE",
                    resource_type="service_preset",
                    resource_id=preset_id,
                    user=user,
                    details={"name": name, "category": category}
                )
                return True, f"Preset '{name}' created successfully"
            else:
                # Update silencioso - não loga para evitar poluição do audit
                return True, f"Preset '{name}' already exists (updated silently)"

        return False, "Failed to create preset"

    async def get_preset(self, preset_id: str) -> Optional[Dict]:
        """Get a specific preset by ID."""
        return await self.kv.get_service_preset(preset_id)

    async def list_presets(self, category: Optional[str] = None) -> List[Dict]:
        """
        List all presets, optionally filtered by category.

        Args:
            category: Optional category filter (exporter, application, etc.)

        Returns:
            List of preset definitions
        """
        presets = await self.kv.list_service_presets()

        if category:
            presets = [p for p in presets if p.get("category") == category]

        return presets

    async def update_preset(
        self,
        preset_id: str,
        updates: Dict[str, Any],
        user: str = "system"
    ) -> Tuple[bool, str]:
        """
        Update an existing preset.

        Args:
            preset_id: Preset to update
            updates: Fields to update
            user: User performing update

        Returns:
            Tuple of (success, message)
        """
        # Get existing preset
        preset = await self.get_preset(preset_id)
        if not preset:
            return False, f"Preset '{preset_id}' not found"

        # Merge updates
        preset.update(updates)
        preset["updated_at"] = datetime.utcnow().isoformat()

        # Validate
        is_valid, errors = self._validate_preset(preset)
        if not is_valid:
            return False, f"Validation failed: {', '.join(errors)}"

        # Store
        success = await self.kv.put_service_preset(preset_id, preset, user)

        if success:
            await self.kv.log_audit_event(
                action="UPDATE",
                resource_type="service_preset",
                resource_id=preset_id,
                user=user,
                details={"updates": list(updates.keys())}
            )
            return True, "Preset updated successfully"

        return False, "Failed to update preset"

    async def delete_preset(self, preset_id: str, user: str = "system") -> Tuple[bool, str]:
        """Delete a preset."""
        # Check if preset exists
        preset = await self.get_preset(preset_id)
        if not preset:
            return False, f"Preset '{preset_id}' not found"

        # Delete from KV
        key = f"{self.kv.SERVICE_PRESETS}/{preset_id}.json"
        success = await self.kv.delete_key(key)

        if success:
            await self.kv.log_audit_event(
                action="DELETE",
                resource_type="service_preset",
                resource_id=preset_id,
                user=user,
                details={"name": preset.get("name")}
            )
            return True, "Preset deleted successfully"

        return False, "Failed to delete preset"

    # =========================================================================
    # Service Registration from Preset
    # =========================================================================

    async def register_from_preset(
        self,
        preset_id: str,
        variables: Dict[str, str],
        node_addr: Optional[str] = None,
        user: str = "system"
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Register a service using a preset with variable substitution.

        Args:
            preset_id: Preset to use
            variables: Variables to substitute (e.g., {"address": "10.0.0.1", "env": "prod"})
            node_addr: Optional specific node to register on
            user: User performing registration

        Returns:
            Tuple of (success, message, service_id)

        Example:
            success, msg, sid = await manager.register_from_preset(
                preset_id="node-exporter-linux",
                variables={
                    "address": "10.0.0.5",
                    "env": "prod",
                    "datacenter": "palmas",
                    "hostname": "web-server-01"
                }
            )
        """
        # Get preset
        preset = await self.get_preset(preset_id)
        if not preset:
            return False, f"Preset '{preset_id}' not found", None

        try:
            # Build service payload from preset
            service_data = self._apply_preset(preset, variables)

            # Validate service data
            is_valid, errors = await self.consul.validate_service_data(service_data)
            if not is_valid:
                return False, f"Service validation failed: {', '.join(errors)}", None

            # Register service
            success = await self.consul.register_service(service_data, node_addr)

            if success:
                service_id = service_data["id"]

                # Log audit event
                await self.kv.log_audit_event(
                    action="CREATE",
                    resource_type="service_from_preset",
                    resource_id=service_id,
                    user=user,
                    details={
                        "preset_id": preset_id,
                        "preset_name": preset.get("name"),
                        "variables": variables,
                        "node": node_addr or "local"
                    }
                )

                return True, f"Service registered successfully", service_id

            return False, "Failed to register service with Consul", None

        except Exception as exc:
            return False, f"Error applying preset: {str(exc)}", None

    def _apply_preset(self, preset: Dict, variables: Dict[str, str]) -> Dict[str, Any]:
        """
        Apply variable substitution to a preset template.

        Supports:
        - ${variable} - Required variables
        - ${variable:default} - Optional with default value
        - Nested substitution in meta, checks, etc.

        Args:
            preset: Preset template
            variables: Variable values

        Returns:
            Service registration payload
        """
        # Build base service data
        service_data = {
            "name": preset["service_name"],
            "tags": preset.get("tags", []).copy(),
        }

        # Generate service ID from preset + variables
        # Format: {service_name}_{hostname/address}_{env}
        hostname = variables.get("hostname", variables.get("address", "unknown"))
        env = variables.get("env", "default")
        service_id = f"{preset['service_name']}_{hostname}_{env}"
        service_id = self.consul.sanitize_service_id(service_id)
        service_data["id"] = service_id

        # Add address if provided
        if "address" in variables:
            service_data["address"] = variables["address"]

        # Add port (can be overridden by variable)
        if "port" in variables:
            service_data["port"] = int(variables["port"])
        elif preset.get("port"):
            service_data["port"] = preset["port"]

        # Apply meta template with variable substitution
        if preset.get("meta_template"):
            service_data["Meta"] = self._substitute_variables(
                preset["meta_template"],
                variables
            )

        # Apply health checks with variable substitution
        if preset.get("checks"):
            service_data["Check"] = self._substitute_check_variables(
                preset["checks"][0] if len(preset["checks"]) == 1 else None,
                variables,
                service_data.get("address"),
                service_data.get("port")
            )

            if len(preset["checks"]) > 1:
                service_data["Checks"] = [
                    self._substitute_check_variables(check, variables, service_data.get("address"), service_data.get("port"))
                    for check in preset["checks"]
                ]

        return service_data

    def _substitute_variables(self, template: Dict[str, str], variables: Dict[str, str]) -> Dict[str, str]:
        """
        Substitute variables in a dictionary template.

        Supports:
        - ${var} - Simple substitution
        - ${var:default} - With default value
        """
        result = {}

        for key, value in template.items():
            if isinstance(value, str) and "${" in value:
                # Use Template for safe substitution
                try:
                    # Handle ${var:default} syntax
                    processed = value
                    for match in re.finditer(r'\$\{(\w+)(?::([^}]+))?\}', value):
                        var_name = match.group(1)
                        default_value = match.group(2)

                        if var_name in variables:
                            processed = processed.replace(match.group(0), variables[var_name])
                        elif default_value is not None:
                            processed = processed.replace(match.group(0), default_value)
                        else:
                            raise ValueError(f"Missing required variable: {var_name}")

                    result[key] = processed
                except Exception as exc:
                    raise ValueError(f"Error substituting variable in '{key}': {exc}")
            else:
                result[key] = value

        return result

    def _substitute_check_variables(
        self,
        check_template: Optional[Dict[str, Any]],
        variables: Dict[str, str],
        address: Optional[str],
        port: Optional[int]
    ) -> Optional[Dict[str, Any]]:
        """
        Substitute variables in a health check template.

        Auto-substitutes ${address} and ${port} if not provided in variables.
        """
        if not check_template:
            return None

        check = check_template.copy()

        # Add address and port to variables if not already present
        enhanced_vars = variables.copy()
        if address and "address" not in enhanced_vars:
            enhanced_vars["address"] = address
        if port and "port" not in enhanced_vars:
            enhanced_vars["port"] = str(port)

        # Substitute in string fields
        for key, value in check.items():
            if isinstance(value, str) and "${" in value:
                for match in re.finditer(r'\$\{(\w+)(?::([^}]+))?\}', value):
                    var_name = match.group(1)
                    default_value = match.group(2)

                    if var_name in enhanced_vars:
                        value = value.replace(match.group(0), enhanced_vars[var_name])
                    elif default_value is not None:
                        value = value.replace(match.group(0), default_value)

                check[key] = value

        return check

    # =========================================================================
    # Built-in Preset Definitions
    # =========================================================================

    async def create_builtin_presets(self, user: str = "system") -> Dict[str, bool]:
        """
        Create built-in preset templates for common exporters.

        Returns:
            Dictionary mapping preset_id to success status
        """
        results = {}

        # Node Exporter (Linux)
        results["node-exporter-linux"] = (await self.create_preset(
            preset_id="node-exporter-linux",
            name="Node Exporter (Linux)",
            service_name="node_exporter",
            port=9100,
            tags=["monitoring", "linux", "exporter"],
            meta_template={
                "module": "node_exporter",
                "env": "${env}",
                "datacenter": "${datacenter:unknown}",
                "hostname": "${hostname}",
                "os": "linux"
            },
            checks=[{
                "HTTP": "http://${address}:${port}/metrics",
                "Interval": "30s",
                "Timeout": "5s"
            }],
            description="Prometheus Node Exporter for Linux systems",
            category="exporter",
            user=user
        ))[0]

        # Windows Exporter
        results["windows-exporter"] = (await self.create_preset(
            preset_id="windows-exporter",
            name="Windows Exporter",
            service_name="windows_exporter",
            port=9182,
            tags=["monitoring", "windows", "exporter"],
            meta_template={
                "module": "windows_exporter",
                "env": "${env}",
                "datacenter": "${datacenter:unknown}",
                "hostname": "${hostname}",
                "os": "windows"
            },
            checks=[{
                "HTTP": "http://${address}:${port}/metrics",
                "Interval": "30s",
                "Timeout": "5s"
            }],
            description="Prometheus Windows Exporter",
            category="exporter",
            user=user
        ))[0]

        # Blackbox Exporter (ICMP)
        results["blackbox-icmp"] = (await self.create_preset(
            preset_id="blackbox-icmp",
            name="Blackbox ICMP Probe",
            service_name="blackbox_exporter",
            port=9115,
            tags=["monitoring", "blackbox", "icmp"],
            meta_template={
                "module": "icmp",
                "company": "${company}",
                "project": "${project}",
                "env": "${env}",
                "name": "${name}",
                "instance": "${target}"
            },
            description="Blackbox Exporter ICMP probe template",
            category="blackbox",
            user=user
        ))[0]

        # Redis Exporter
        results["redis-exporter"] = (await self.create_preset(
            preset_id="redis-exporter",
            name="Redis Exporter",
            service_name="redis_exporter",
            port=9121,
            tags=["monitoring", "redis", "database"],
            meta_template={
                "module": "redis_exporter",
                "env": "${env}",
                "instance": "${address}:${redis_port:6379}",
                "database": "redis"
            },
            checks=[{
                "HTTP": "http://${address}:${port}/metrics",
                "Interval": "30s",
                "Timeout": "5s"
            }],
            description="Redis database exporter",
            category="database",
            user=user
        ))[0]

        return results

    # =========================================================================
    # Validation
    # =========================================================================

    def _validate_preset(self, preset: Dict) -> Tuple[bool, List[str]]:
        """
        Validate preset structure.

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Required fields
        if not preset.get("id"):
            errors.append("Preset ID is required")
        if not preset.get("name"):
            errors.append("Preset name is required")
        if not preset.get("service_name"):
            errors.append("Service name is required")

        # Validate port if specified
        if preset.get("port"):
            try:
                port = int(preset["port"])
                if port < 1 or port > 65535:
                    errors.append("Port must be between 1 and 65535")
            except (ValueError, TypeError):
                errors.append("Port must be a valid integer")

        # Validate checks structure
        if preset.get("checks"):
            if not isinstance(preset["checks"], list):
                errors.append("Checks must be a list")
            else:
                for idx, check in enumerate(preset["checks"]):
                    if not isinstance(check, dict):
                        errors.append(f"Check {idx} must be a dictionary")

        return len(errors) == 0, errors
