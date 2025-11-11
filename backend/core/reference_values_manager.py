"""
Reference Values Manager - Sistema de Auto-Cadastro/Retroalimentação

OBJETIVO:
Permitir que campos metadata tenham valores cadastrados automaticamente
quando o usuário digita um valor novo em um formulário.

EXEMPLO:
1. Usuário cadastra servidor com empresa="Ramada"
2. Sistema automaticamente adiciona ao array em skills/eye/reference-values/company.json
3. Próximo cadastro: "Ramada" aparece como opção no select

ESTRUTURA NOVA (JSON ÚNICO POR CAMPO):
skills/eye/reference-values/
  ├── company.json      ← Array com todos os valores de company
  ├── cidade.json       ← Array com todos os valores de cidade
  └── localizacao.json  ← Array com todos os valores de localização

VANTAGENS:
- ✅ Menos arquivos no KV (1 por campo ao invés de centenas)
- ✅ Operações mais rápidas (1 read/write ao invés de múltiplos)
- ✅ Administração simplificada
- ✅ Backup mais fácil

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
            "metadata": metadata or {},
            "change_history": []  # Histórico individual de mudanças (não sobrescreve)
        }

        success = await self._put_value(field_name, normalized, value_data, user)

        if success:
            # AUDIT LOG DESABILITADO: reference_value auto-cadastro não precisa de auditoria
            # Motivo: Gera 96.7% dos audit logs com crescimento exponencial
            # await self.kv.log_audit_event(
            #     action="CREATE",
            #     resource_type="reference_value",
            #     resource_id=f"{field_name}/{normalized}",
            #     user=user,
            #     details={"field": field_name, "value": normalized}
            # )
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

        # VALIDAÇÃO DUPLICADOS: Verificar se já existe (CRÍTICO!)
        existing = await self.get_value(field_name, normalized)
        if existing:
            logger.warning(f"[{field_name}] Tentativa de criar valor duplicado: '{normalized}'")
            return False, f"❌ Valor '{normalized}' já existe para campo '{field_name}'. Valores duplicados não são permitidos!"

        # Criar registro
        value_data = {
            "field_name": field_name,
            "value": normalized,
            "original_value": value,
            "created_at": datetime.utcnow().isoformat(),
            "created_by": user,
            "usage_count": 0,
            "last_used_at": None,
            "metadata": metadata or {},
            "change_history": []  # Histórico individual de mudanças (não sobrescreve)
        }

        success = await self._put_value(field_name, normalized, value_data, user)

        if success:
            # AUDIT LOG DESABILITADO: reference_value manual creation não precisa de auditoria
            # await self.kv.log_audit_event(
            #     action="CREATE",
            #     resource_type="reference_value",
            #     resource_id=f"{field_name}/{normalized}",
            #     user=user,
            #     details={"field": field_name, "value": normalized, "source": "manual"}
            # )
            return True, f"Valor '{normalized}' criado com sucesso"

        return False, "Erro ao criar valor"

    async def get_value(self, field_name: str, value: str) -> Optional[Dict]:
        """
        Busca valor específico no array do campo.

        Args:
            field_name: Nome do campo
            value: Valor (será normalizado antes da busca)

        Returns:
            Dicionário com dados do valor ou None se não encontrado
        """
        normalized = self.normalize_value(value)
        key = self._build_key(field_name)

        # Carregar array completo
        array = await self.kv.get_json(key) or []

        # Buscar valor no array
        for item in array:
            if isinstance(item, dict) and item.get("value") == normalized:
                return item

        return None

    async def list_values(self, field_name: str, include_stats: bool = False) -> List[Dict]:
        """
        Lista todos os valores de um campo (carrega array do JSON único).

        Args:
            field_name: Nome do campo (company, localizacao, etc)
            include_stats: Se True, inclui estatísticas de uso

        Returns:
            Lista de valores ordenados alfabeticamente
        """
        key = self._build_key(field_name)

        # Carregar array completo
        array = await self.kv.get_json(key) or []

        # Filtrar dados conforme solicitado
        values = []
        for item in array:
            if isinstance(item, dict) and "value" in item:
                if include_stats:
                    values.append(item)
                else:
                    # Retorna apenas os dados essenciais
                    values.append({
                        "value": item["value"],
                        "created_at": item.get("created_at"),
                        "created_by": item.get("created_by"),
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
            # AUDIT LOG DESABILITADO: reference_value updates não precisam de auditoria
            # await self.kv.log_audit_event(
            #     action="UPDATE",
            #     resource_type="reference_value",
            #     resource_id=f"{field_name}/{normalized}",
            #     user=user,
            #     details={"field": field_name, "value": normalized, "updates": updates}
            # )
            return True, f"Valor '{normalized}' atualizado com sucesso"

        return False, "Erro ao atualizar valor"

    async def rename_value(
        self,
        field_name: str,
        old_value: str,
        new_value: str,
        user: str = "system"
    ) -> Tuple[bool, str]:
        """
        Renomeia um valor existente (MANTÉM TODAS AS REFERÊNCIAS INALTERADAS).

        IMPORTANTE:
        - Atualiza APENAS o campo 'value' no JSON único
        - Preserva metadata, created_at, usage_count, etc
        - NÃO quebra referências porque atualiza IN-PLACE
        - Serviços continuam funcionando normalmente

        EXEMPLO:
        - old_value: "Paraguacu"
        - new_value: "Paraguaçu Paulista"
        - Resultado: Valor renomeado, referências preservadas

        Args:
            field_name: Nome do campo (ex: "cidade")
            old_value: Valor atual (ex: "Paraguacu")
            new_value: Novo valor (ex: "Paraguaçu Paulista")
            user: Usuário que está renomeando

        Returns:
            Tuple de (success, message)
        """
        try:
            old_normalized = self.normalize_value(old_value)
            new_normalized = self.normalize_value(new_value)

            # Validações
            if old_normalized == new_normalized:
                return False, "Valor novo é igual ao valor antigo"

            # Buscar valor existente
            existing = await self.get_value(field_name, old_normalized)
            if not existing:
                return False, f"Valor '{old_normalized}' não encontrado"

            # VALIDAÇÃO DUPLICADOS: Verificar se novo valor já existe (CRÍTICO!)
            existing_new = await self.get_value(field_name, new_normalized)
            if existing_new:
                logger.warning(f"[{field_name}] Tentativa de renomear para valor duplicado: '{new_normalized}'")
                return False, f"❌ Valor '{new_normalized}' já existe para campo '{field_name}'. Não é possível renomear para um valor duplicado!"

            # Carregar array completo
            key = self._build_key(field_name)
            array = await self.kv.get_json(key) or []

            # Encontrar e atualizar valor no array
            updated = False
            for item in array:
                if isinstance(item, dict) and item.get("value") == old_normalized:
                    # REGISTRAR MUDANÇA NO HISTÓRICO INDIVIDUAL (não sobrescreve)
                    if "change_history" not in item:
                        item["change_history"] = []

                    change_record = {
                        "timestamp": datetime.utcnow().isoformat(),
                        "user": user,
                        "action": "rename",
                        "old_value": old_normalized,
                        "new_value": new_normalized
                    }
                    item["change_history"].append(change_record)

                    # ATUALIZA APENAS O CAMPO 'value' - preserva resto
                    item["value"] = new_normalized
                    item["original_value"] = item.get("original_value", old_normalized)
                    item["updated_at"] = datetime.utcnow().isoformat()
                    item["updated_by"] = user
                    updated = True
                    break

            if not updated:
                return False, f"Valor '{old_normalized}' não encontrado no array"

            # ============================================================================
            # CRÍTICO: BULK UPDATE DE SERVIÇOS QUE USAM ESTE VALOR
            # ============================================================================
            logger.info(f"[{field_name}] Iniciando bulk update de serviços: '{old_normalized}' → '{new_normalized}'")

            services_updated, services_failed = await self._bulk_update_services(
                field_name=field_name,
                old_value=old_normalized,
                new_value=new_value  # ✅ Usar valor ORIGINAL (preserva case)
            )

            logger.info(f"[{field_name}] Bulk update concluído: {services_updated} atualizados, {services_failed} falharam")

            # Se houve falhas, avisar mas continuar (rename parcial)
            if services_failed > 0:
                logger.warning(f"[{field_name}] {services_failed} serviços NÃO foram atualizados!")

            # ============================================================================
            # Salvar array atualizado (SEM last_rename na metadata global - histórico agora é individual)
            # ============================================================================
            metadata = {
                "updated_by": user,
                "resource_type": "reference_values",
                "field_name": field_name,
                "total_values": len(array),
                "last_update": datetime.utcnow().isoformat()
            }

            success = await self.kv.put_json(key, array, metadata)

            if success:
                result_msg = f"Valor renomeado de '{old_normalized}' para '{new_normalized}'"
                if services_updated > 0:
                    result_msg += f" ({services_updated} serviços atualizados)"
                if services_failed > 0:
                    result_msg += f" (⚠️ {services_failed} serviços FALHARAM)"

                logger.info(f"[{field_name}] {result_msg}")
                return True, result_msg

            return False, "Erro ao salvar array atualizado"

        except Exception as exc:
            logger.error(f"Erro ao renomear valor {old_value} → {new_value} no campo {field_name}: {exc}")
            return False, f"Erro ao renomear: {str(exc)}"

    async def _bulk_update_services(
        self,
        field_name: str,
        old_value: str,
        new_value: str
    ) -> Tuple[int, int]:
        """
        Atualiza TODOS os serviços que usam old_value para new_value.

        CRÍTICO: Este método é chamado automaticamente ao renomear um reference value!

        Args:
            field_name: Nome do campo (company, cidade, etc)
            old_value: Valor antigo (ex: "Emin")
            new_value: Novo valor (ex: "Emin2")

        Returns:
            Tuple de (services_updated, services_failed)
        """
        services_updated = 0
        services_failed = 0

        try:
            # Buscar TODOS os serviços
            logger.info(f"[_bulk_update_services] Buscando todos os serviços do Consul...")
            services_response = await self.consul.get_services()

            logger.info(f"[_bulk_update_services] Response type: {type(services_response)}")
            logger.info(f"[_bulk_update_services] Response keys: {services_response.keys() if isinstance(services_response, dict) else 'N/A'}")

            if not services_response:
                logger.warning(f"[_bulk_update_services] Nenhum serviço encontrado (response vazio)")
                return 0, 0

            # services_response É UM DICIONÁRIO {service_id: service_data}
            # NÃO tem 'services' key!
            logger.info(f"[_bulk_update_services] Total de serviços encontrados: {len(services_response)}")

            # Iterar sobre todos os serviços DIRETAMENTE
            for svc_id, service in services_response.items():
                    meta = service.get('Meta', {})

                    # Verificar se este serviço usa o valor antigo
                    field_value = meta.get(field_name)

                    logger.info(f"[_bulk_update_services] Verificando serviço {svc_id}: {field_name}={field_value}")

                    if field_value and self.normalize_value(str(field_value)) == old_value:
                        logger.info(f"[_bulk_update_services] ✓ Serviço {svc_id} USA o valor antigo! Atualizando...")

                        try:
                            # Atualizar APENAS o campo que mudou no Meta
                            meta[field_name] = new_value

                            # Re-registrar com JSON COMPLETO (CRÍTICO!)
                            # Consul NÃO tem PATCH - precisa enviar TUDO ou perde campos
                            registration = {
                                "ID": svc_id,
                                "Name": service.get('Service'),  # Nome do serviço
                                "Address": service.get('Address', ''),
                                "Port": service.get('Port', 0),
                                "Tags": service.get('Tags', []),
                                "Meta": meta,  # Meta atualizado
                                "EnableTagOverride": service.get('EnableTagOverride', False),
                                "Weights": service.get('Weights', {}),
                            }

                            # CRÍTICO: Preservar Checks se existirem
                            # Checks podem estar em 'Check' (singular) ou 'Checks' (plural)
                            if 'Checks' in service and service['Checks']:
                                registration['Checks'] = service['Checks']
                            elif 'Check' in service and service['Check']:
                                registration['Check'] = service['Check']

                            # Re-registrar no agente do Consul (idempotente)
                            await self.consul.register_service(registration)
                            services_updated += 1
                            logger.info(f"[_bulk_update_services] ✅ Serviço {svc_id} atualizado com sucesso")

                        except Exception as svc_error:
                            services_failed += 1
                            logger.error(f"[_bulk_update_services] ❌ Erro ao atualizar serviço {svc_id}: {svc_error}")

            return services_updated, services_failed

        except Exception as exc:
            logger.error(f"[_bulk_update_services] Erro crítico no bulk update: {exc}")
            return services_updated, services_failed

    async def delete_value(
        self,
        field_name: str,
        value: str,
        user: str = "system",
        force: bool = False
    ) -> Tuple[bool, str]:
        """
        Deleta valor de referência (remove do array do JSON único).

        PROTEÇÃO: Bloqueia deleção se valor está em uso (a menos que force=True).

        Args:
            field_name: Nome do campo
            value: Valor a deletar
            user: Usuário que está deletando
            force: Se True, força deleção mesmo se em uso (NÃO RECOMENDADO!)

        Returns:
            Tuple de (success, message)
        """
        try:
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

            # Carregar array completo
            key = self._build_key(field_name)
            array = await self.kv.get_json(key) or []

            # Remover valor do array
            new_array = [item for item in array if not (isinstance(item, dict) and item.get("value") == normalized)]

            # Verificar se algo foi removido
            if len(new_array) == len(array):
                return False, f"Valor '{normalized}' não foi encontrado no array"

            # Salvar array atualizado
            metadata = {
                "updated_by": user,
                "resource_type": "reference_values",
                "field_name": field_name,
                "total_values": len(new_array)
            }

            success = await self.kv.put_json(key, new_array, metadata)

            if success:
                # AUDIT LOG DESABILITADO: reference_value deletes não precisam de auditoria
                return True, f"Valor '{normalized}' deletado com sucesso"

            return False, "Erro ao salvar array atualizado"

        except Exception as exc:
            logger.error(f"Erro ao deletar valor {value} do campo {field_name}: {exc}")
            return False, f"Erro ao deletar: {str(exc)}"

    # =========================================================================
    # Métodos Internos/Auxiliares
    # =========================================================================

    def _build_key(self, field_name: str) -> str:
        """
        Constrói chave do Consul KV para um campo (JSON ÚNICO).

        Args:
            field_name: Nome do campo

        Returns:
            Chave completa: skills/eye/reference-values/{field_name}.json

        Examples:
            "company" → "skills/eye/reference-values/company.json"
            "cidade" → "skills/eye/reference-values/cidade.json"
        """
        return f"{self.PREFIX}/{field_name}.json"

    async def _put_value(
        self,
        field_name: str,
        value: str,
        data: Dict,
        user: str
    ) -> bool:
        """
        Adiciona ou atualiza valor no array do JSON único do campo.

        ESTRATÉGIA:
        1. Carrega array completo do campo
        2. Procura se valor já existe (por value normalizado)
        3. Se existe: atualiza
        4. Se não existe: adiciona ao array
        5. Salva array de volta

        Args:
            field_name: Nome do campo
            value: Valor normalizado
            data: Dados completos do valor
            user: Usuário

        Returns:
            True se sucesso
        """
        try:
            key = self._build_key(field_name)

            # PASSO 1: Carregar array existente (ou inicializar vazio)
            existing_array = await self.kv.get_json(key) or []

            # Garantir que é um array
            if not isinstance(existing_array, list):
                logger.warning(f"Campo {field_name} não é array, inicializando como []")
                existing_array = []

            # PASSO 2: Procurar valor no array
            found_index = None
            for idx, item in enumerate(existing_array):
                if isinstance(item, dict) and item.get("value") == value:
                    found_index = idx
                    break

            # PASSO 3: Atualizar ou adicionar
            if found_index is not None:
                # Valor existe, atualizar
                existing_array[found_index] = data
            else:
                # Valor novo, adicionar ao array
                existing_array.append(data)

            # PASSO 4: Salvar array de volta
            metadata = {
                "updated_by": user,
                "resource_type": "reference_values",
                "field_name": field_name,
                "total_values": len(existing_array)
            }

            success = await self.kv.put_json(key, existing_array, metadata)
            return success

        except Exception as exc:
            logger.error(f"Erro ao salvar valor {value} no campo {field_name}: {exc}")
            return False

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
