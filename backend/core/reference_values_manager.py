"""
Reference Values Manager - Sistema de Auto-Cadastro/Retroalimentação

OBJETIVO:
Permitir que campos metadata tenham valores cadastrados automaticamente
quando o usuário digita um valor novo em um formulário.

EXEMPLO:
1. Usuário cadastra servidor com empresa="Ramada"
2. Sistema automaticamente cria registro em skills/cm/reference-values/company/ramada.json
3. Próximo cadastro: "Ramada" aparece como opção no select

CAMPOS SUPORTADOS (available_for_registration: true):
- company (Empresa)
- grupo_monitoramento (Grupo Monitoramento)
- localizacao (Localização)
- tipo (Tipo)
- modelo (Modelo)
- cod_localidade (Código da Localidade)
- tipo_dispositivo_abrev (Tipo Dispositivo Abrev)
- cidade (Cidade)
- provedor (Provedor)
- categoria (Categoria para metadata-fields) - NOVO
- tag (Tag) - NOVO

NORMALIZAÇÃO:
- Title Case: Primeira letra de cada palavra em maiúscula
- Exemplo: "empresa ramada" → "Empresa Ramada"
- Exemplo: "SAO PAULO" → "Sao Paulo"

PROTEÇÃO CONTRA DELEÇÃO:
- Bloqueia deleção se valor está em uso
- Mostra mensagem: "Valor 'X' está em uso em N instâncias"
"""

import re
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from .consul_manager import ConsulManager
from .kv_manager import KVManager

logger = logging.getLogger(__name__)


class ReferenceValuesManager:
    """
    Gerencia valores de referência (reference values) para campos metadata.

    Permite auto-cadastro: quando usuário digita valor novo em formulário,
    o valor é automaticamente cadastrado e fica disponível para próximos usos.
    """

    def __init__(self, consul: Optional[ConsulManager] = None, kv: Optional[KVManager] = None):
        self.consul = consul or ConsulManager()
        self.kv = kv or KVManager(self.consul)

        # Namespace para reference values
        self.PREFIX = f"{self.kv.PREFIX}/reference-values"

    # =========================================================================
    # Normalização (Title Case)
    # =========================================================================

    @staticmethod
    def normalize_value(value: str) -> str:
        """
        Normaliza valor para Title Case (primeira letra de cada palavra em maiúscula).

        Examples:
            "empresa ramada" → "Empresa Ramada"
            "SAO PAULO" → "Sao Paulo"
            "acme-corp" → "Acme-Corp"

        Args:
            value: Valor original

        Returns:
            Valor normalizado em Title Case
        """
        if not value:
            return value

        # Remove espaços extras
        value = value.strip()

        # Title Case
        # Preserva hífens e underscores
        return value.title()

    # =========================================================================
    # CRUD - Reference Values
    # =========================================================================

    async def ensure_value(
        self,
        field_name: str,
        value: str,
        user: str = "system",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str, str]:
        """
        Garante que valor existe no cadastro de referência.

        Se valor não existe → cria automaticamente (auto-cadastro)
        Se valor existe → retorna normalizado

        CRÍTICO: Este é o método usado ao salvar serviços/exporters/blackbox!

        Args:
            field_name: Nome do campo (company, localizacao, cidade, etc)
            value: Valor digitado pelo usuário
            user: Usuário que está cadastrando
            metadata: Metadata adicional (descrição, cor, ícone, etc)

        Returns:
            Tuple de (created, normalized_value, message)
            - created: True se foi criado agora, False se já existia
            - normalized_value: Valor normalizado (Title Case)
            - message: Mensagem de sucesso/erro
        """
        if not value or not field_name:
            return False, value, "Valor ou campo vazio"

        # Normalizar valor
        normalized = self.normalize_value(value)

        # Verificar se já existe
        existing = await self.get_value(field_name, normalized)

        if existing:
            # Já existe, apenas retorna normalizado
            return False, normalized, f"Valor '{normalized}' já existe"

        # Criar novo registro
        value_data = {
            "field_name": field_name,
            "value": normalized,
            "original_value": value,  # Valor original digitado pelo usuário
            "created_at": datetime.utcnow().isoformat(),
            "created_by": user,
            "usage_count": 0,  # Será incrementado quando usado
            "last_used_at": None,
            "metadata": metadata or {}
        }

        success = await self._put_value(field_name, normalized, value_data, user)

        if success:
            # Log audit event
            await self.kv.log_audit_event(
                action="CREATE",
                resource_type="reference_value",
                resource_id=f"{field_name}/{normalized}",
                user=user,
                details={"field": field_name, "value": normalized}
            )
            return True, normalized, f"Valor '{normalized}' cadastrado automaticamente"

        return False, normalized, "Erro ao cadastrar valor"

    async def create_value(
        self,
        field_name: str,
        value: str,
        user: str = "system",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str]:
        """
        Cria um novo valor de referência (cadastro manual via interface).

        Diferente do ensure_value, este método é usado quando o usuário
        cadastra valores diretamente na página de configurações.

        Args:
            field_name: Nome do campo
            value: Valor a ser cadastrado
            user: Usuário que está cadastrando
            metadata: Metadata adicional

        Returns:
            Tuple de (success, message)
        """
        if not value or not field_name:
            return False, "Valor ou campo vazio"

        # Normalizar
        normalized = self.normalize_value(value)

        # Verificar se já existe
        existing = await self.get_value(field_name, normalized)
        if existing:
            return False, f"Valor '{normalized}' já existe para campo '{field_name}'"

        # Criar registro
        value_data = {
            "field_name": field_name,
            "value": normalized,
            "original_value": value,
            "created_at": datetime.utcnow().isoformat(),
            "created_by": user,
            "usage_count": 0,
            "last_used_at": None,
            "metadata": metadata or {}
        }

        success = await self._put_value(field_name, normalized, value_data, user)

        if success:
            await self.kv.log_audit_event(
                action="CREATE",
                resource_type="reference_value",
                resource_id=f"{field_name}/{normalized}",
                user=user,
                details={"field": field_name, "value": normalized, "source": "manual"}
            )
            return True, f"Valor '{normalized}' criado com sucesso"

        return False, "Erro ao criar valor"

    async def get_value(self, field_name: str, value: str) -> Optional[Dict]:
        """
        Busca valor específico.

        Args:
            field_name: Nome do campo
            value: Valor (será normalizado antes da busca)

        Returns:
            Dicionário com dados do valor ou None se não encontrado
        """
        normalized = self.normalize_value(value)
        key = self._build_key(field_name, normalized)

        return await self.kv.get_json(key)

    async def list_values(self, field_name: str, include_stats: bool = False) -> List[Dict]:
        """
        Lista todos os valores de um campo.

        Args:
            field_name: Nome do campo (company, localizacao, etc)
            include_stats: Se True, inclui estatísticas de uso

        Returns:
            Lista de valores ordenados alfabeticamente
        """
        prefix = f"{self.PREFIX}/{field_name}"
        tree = await self.kv.get_tree(prefix, unwrap_metadata=True)

        values = []
        for key, data in tree.items():
            if isinstance(data, dict) and "value" in data:
                if include_stats:
                    values.append(data)
                else:
                    # Retorna apenas os dados essenciais
                    values.append({
                        "value": data["value"],
                        "created_at": data.get("created_at"),
                        "created_by": data.get("created_by"),
                    })

        # Ordenar alfabeticamente
        values.sort(key=lambda x: x["value"])

        return values

    async def update_value(
        self,
        field_name: str,
        value: str,
        updates: Dict[str, Any],
        user: str = "system"
    ) -> Tuple[bool, str]:
        """
        Atualiza metadata de um valor existente.

        IMPORTANTE: Não permite alterar o valor em si para evitar quebra de referências!
        Apenas permite atualizar metadata (descrição, cor, ícone, etc).

        Args:
            field_name: Nome do campo
            value: Valor existente
            updates: Campos a atualizar (apenas metadata)
            user: Usuário que está atualizando

        Returns:
            Tuple de (success, message)
        """
        normalized = self.normalize_value(value)

        # Buscar valor existente
        existing = await self.get_value(field_name, normalized)
        if not existing:
            return False, f"Valor '{normalized}' não encontrado"

        # Não permitir alterar campo 'value'
        if "value" in updates:
            return False, "Não é permitido alterar o valor para evitar quebra de referências"

        # Atualizar apenas metadata
        existing["metadata"].update(updates.get("metadata", {}))
        existing["updated_at"] = datetime.utcnow().isoformat()
        existing["updated_by"] = user

        # Salvar
        success = await self._put_value(field_name, normalized, existing, user)

        if success:
            await self.kv.log_audit_event(
                action="UPDATE",
                resource_type="reference_value",
                resource_id=f"{field_name}/{normalized}",
                user=user,
                details={"field": field_name, "value": normalized, "updates": updates}
            )
            return True, f"Valor '{normalized}' atualizado com sucesso"

        return False, "Erro ao atualizar valor"

    async def delete_value(
        self,
        field_name: str,
        value: str,
        user: str = "system",
        force: bool = False
    ) -> Tuple[bool, str]:
        """
        Deleta valor de referência.

        PROTEÇÃO: Bloqueia deleção se valor está em uso (a menos que force=True).

        Args:
            field_name: Nome do campo
            value: Valor a deletar
            user: Usuário que está deletando
            force: Se True, força deleção mesmo se em uso (NÃO RECOMENDADO!)

        Returns:
            Tuple de (success, message)
        """
        normalized = self.normalize_value(value)

        # Buscar valor existente
        existing = await self.get_value(field_name, normalized)
        if not existing:
            return False, f"Valor '{normalized}' não encontrado"

        # Verificar se está em uso
        if not force:
            usage_count = await self._check_usage(field_name, normalized)
            if usage_count > 0:
                return False, f"Valor '{normalized}' está em uso em {usage_count} instância(s). Não é possível deletar."

        # Deletar
        key = self._build_key(field_name, normalized)
        success = await self.kv.delete_key(key)

        if success:
            await self.kv.log_audit_event(
                action="DELETE",
                resource_type="reference_value",
                resource_id=f"{field_name}/{normalized}",
                user=user,
                details={"field": field_name, "value": normalized, "forced": force}
            )
            return True, f"Valor '{normalized}' deletado com sucesso"

        return False, "Erro ao deletar valor"

    # =========================================================================
    # Métodos Internos/Auxiliares
    # =========================================================================

    def _build_key(self, field_name: str, value: str) -> str:
        """
        Constrói chave do Consul KV para um valor.

        Args:
            field_name: Nome do campo
            value: Valor (já normalizado)

        Returns:
            Chave completa: skills/cm/reference-values/{field_name}/{value_slug}.json

        Examples:
            ("company", "Empresa Ramada") → "skills/cm/reference-values/company/empresa_ramada.json"
        """
        # Slugify: converte para lowercase, substitui espaços por _
        slug = re.sub(r'[^\w\s-]', '', value.lower())
        slug = re.sub(r'[\s]+', '_', slug)

        return f"{self.PREFIX}/{field_name}/{slug}.json"

    async def _put_value(
        self,
        field_name: str,
        value: str,
        data: Dict,
        user: str
    ) -> bool:
        """
        Salva valor no KV store.

        Args:
            field_name: Nome do campo
            value: Valor normalizado
            data: Dados completos
            user: Usuário

        Returns:
            True se sucesso
        """
        key = self._build_key(field_name, value)

        metadata = {
            "updated_by": user,
            "resource_type": "reference_value",
            "field_name": field_name
        }

        return await self.kv.put_json(key, data, metadata)

    async def _check_usage(self, field_name: str, value: str) -> int:
        """
        Verifica quantas vezes um valor está em uso.

        IMPLEMENTAÇÃO:
        - Busca todos os serviços no Consul
        - Conta quantos têm Meta.{field_name} == value

        Args:
            field_name: Nome do campo
            value: Valor normalizado

        Returns:
            Número de instâncias que usam este valor
        """
        try:
            # Buscar todos os serviços
            services_response = await self.consul.get_services()

            if not services_response or 'services' not in services_response:
                return 0

            count = 0

            # Iterar sobre todos os serviços
            for service_list in services_response['services'].values():
                if not isinstance(service_list, list):
                    continue

                for service in service_list:
                    meta = service.get('Meta', {})

                    # Verificar se o valor está presente
                    field_value = meta.get(field_name)

                    if field_value:
                        # Normalizar valor do serviço para comparação
                        normalized_service_value = self.normalize_value(str(field_value))

                        if normalized_service_value == value:
                            count += 1

            return count

        except Exception as exc:
            logger.error(f"Erro ao verificar uso de {field_name}={value}: {exc}")
            return 0  # Em caso de erro, não bloqueia deleção

    async def increment_usage(self, field_name: str, value: str) -> bool:
        """
        Incrementa contador de uso de um valor.

        Chamado automaticamente quando um serviço/exporter/blackbox é criado.

        Args:
            field_name: Nome do campo
            value: Valor usado

        Returns:
            True se sucesso
        """
        normalized = self.normalize_value(value)

        # Buscar valor existente
        existing = await self.get_value(field_name, normalized)

        if not existing:
            # Valor não existe, não incrementa
            return False

        # Incrementar contador
        existing["usage_count"] = existing.get("usage_count", 0) + 1
        existing["last_used_at"] = datetime.utcnow().isoformat()

        # Salvar
        return await self._put_value(field_name, normalized, existing, "system")
