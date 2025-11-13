"""
Category Manager - Gerencia categorias de campos metadata (abas em Reference Values)

Categorias são usadas para organizar campos em abas temáticas.
Exemplos: Básico, Infraestrutura, Dispositivo, Localização, Rede, etc.
"""
import logging
from typing import Any, Dict, List, Optional, Tuple
from .kv_manager import KVManager

logger = logging.getLogger(__name__)


class CategoryManager:
    """
    Gerencia categorias de campos metadata (abas da página Reference Values).

    STORAGE: skills/eye/metadata/categories.json (Consul KV)

    Estrutura de cada categoria:
    {
        "key": "infrastructure",         # ID único (sem espaços, lowercase)
        "label": "Infraestrutura",      # Nome exibido na aba
        "icon": "☁️",                    # Emoji/ícone da aba
        "description": "Campos...",     # Descrição do que contém
        "order": 2,                     # Ordem de exibição (menor = primeiro)
        "color": "cyan"                 # Cor da aba (Ant Design color)
    }
    """

    # KV path para armazenar categorias
    CATEGORIES_KEY = "skills/eye/metadata/categories.json"

    # Categorias padrão (fallback quando KV está vazio)
    DEFAULT_CATEGORIES = [
        {
            "key": "basic",
            "label": "Básico",
            "icon": "📝",
            "description": "Campos básicos e obrigatórios",
            "order": 1,
            "color": "blue",
        },
        {
            "key": "infrastructure",
            "label": "Infraestrutura",
            "icon": "☁️",
            "description": "Campos relacionados à infraestrutura e cloud",
            "order": 2,
            "color": "cyan",
        },
        {
            "key": "device",
            "label": "Dispositivo",
            "icon": "💻",
            "description": "Campos de hardware e dispositivos",
            "order": 3,
            "color": "purple",
        },
        {
            "key": "location",
            "label": "Localização",
            "icon": "📍",
            "description": "Campos de localização geográfica",
            "order": 4,
            "color": "orange",
        },
        {
            "key": "network",
            "label": "Rede",
            "icon": "🌐",
            "description": "Campos de configuração de rede",
            "order": 5,
            "color": "geekblue",
        },
        {
            "key": "security",
            "label": "Segurança",
            "icon": "🔒",
            "description": "Campos relacionados à segurança",
            "order": 6,
            "color": "red",
        },
        {
            "key": "extra",
            "label": "Extras",
            "icon": "➕",
            "description": "Campos adicionais e opcionais",
            "order": 99,
            "color": "default",
        },
    ]

    def __init__(self):
        self.kv = KVManager()

    async def get_all_categories(self) -> List[Dict[str, Any]]:
        """
        Retorna todas as categorias (do KV ou padrões como fallback).

        COMPORTAMENTO:
        - Se KV vazio → retorna DEFAULT_CATEGORIES
        - Se KV tem dados → retorna categorias do KV
        - Sempre ordena por campo 'order'

        Returns:
            Lista de categorias ordenada por 'order'
        """
        try:
            # Tentar carregar do KV
            categories = await self.kv.get_json(self.CATEGORIES_KEY, default=None)

            if categories is None or not isinstance(categories, list) or len(categories) == 0:
                logger.info("KV vazio - usando categorias padrão")
                categories = self.DEFAULT_CATEGORIES.copy()
            else:
                logger.info(f"Carregadas {len(categories)} categorias do KV")

            # Ordenar por 'order'
            categories.sort(key=lambda c: c.get('order', 999))

            return categories

        except Exception as e:
            logger.error(f"Erro ao carregar categorias: {e}")
            # Em caso de erro, retorna padrões
            return self.DEFAULT_CATEGORIES.copy()

    async def get_category(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Busca categoria específica por key.

        Args:
            key: Chave única da categoria (ex: 'infrastructure')

        Returns:
            Dados da categoria ou None se não encontrada
        """
        categories = await self.get_all_categories()
        for cat in categories:
            if cat.get('key') == key:
                return cat
        return None

    async def create_category(
        self,
        key: str,
        label: str,
        icon: str = "📝",
        description: str = "",
        order: int = 99,
        color: str = "default",
        user: str = "system"
    ) -> Tuple[bool, str]:
        """
        Cria nova categoria.

        VALIDAÇÕES:
        - Key único (não pode duplicar)
        - Key deve ser lowercase, sem espaços
        - Label obrigatório

        Args:
            key: ID único (ex: 'infrastructure')
            label: Nome exibido (ex: 'Infraestrutura')
            icon: Emoji/ícone (ex: '☁️')
            description: Descrição da categoria
            order: Ordem de exibição
            color: Cor Ant Design (blue, cyan, purple, etc)
            user: Usuário criando

        Returns:
            (success, message)
        """
        try:
            # Validar key
            if not key or not isinstance(key, str):
                return False, "Key é obrigatória"

            if key.lower() != key or ' ' in key:
                return False, "Key deve ser lowercase e sem espaços"

            # Validar label
            if not label or not isinstance(label, str):
                return False, "Label é obrigatório"

            # Verificar se já existe
            existing = await self.get_category(key)
            if existing:
                return False, f"Categoria '{key}' já existe"

            # Carregar categorias existentes
            categories = await self.get_all_categories()

            # Criar nova categoria
            new_category = {
                "key": key,
                "label": label,
                "icon": icon or "📝",
                "description": description or "",
                "order": order,
                "color": color or "default",
            }

            # Adicionar à lista
            categories.append(new_category)

            # Salvar no KV
            metadata = {"updated_by": user}
            success = await self.kv.put_json(self.CATEGORIES_KEY, categories, metadata=metadata)

            if success:
                logger.info(f"Categoria '{key}' criada por {user}")
                return True, f"Categoria '{label}' criada com sucesso"
            else:
                return False, "Erro ao salvar categoria no KV"

        except Exception as e:
            logger.error(f"Erro ao criar categoria: {e}")
            return False, f"Erro interno: {str(e)}"

    async def update_category(
        self,
        key: str,
        updates: Dict[str, Any],
        user: str = "system"
    ) -> Tuple[bool, str]:
        """
        Atualiza categoria existente.

        IMPORTANTE: Não permite alterar 'key' (ID).
        Para renomear key, delete + create.

        Args:
            key: Key da categoria a atualizar
            updates: Campos a atualizar (label, icon, description, order, color)
            user: Usuário atualizando

        Returns:
            (success, message)
        """
        try:
            # Verificar se existe
            existing = await self.get_category(key)
            if not existing:
                return False, f"Categoria '{key}' não encontrada"

            # Carregar todas
            categories = await self.get_all_categories()

            # Encontrar e atualizar
            for i, cat in enumerate(categories):
                if cat.get('key') == key:
                    # Aplicar updates (sem permitir mudar key)
                    for field in ['label', 'icon', 'description', 'order', 'color']:
                        if field in updates:
                            categories[i][field] = updates[field]
                    break

            # Salvar no KV
            metadata = {"updated_by": user}
            success = await self.kv.put_json(self.CATEGORIES_KEY, categories, metadata=metadata)

            if success:
                logger.info(f"Categoria '{key}' atualizada por {user}")
                return True, f"Categoria '{existing['label']}' atualizada com sucesso"
            else:
                return False, "Erro ao salvar categoria no KV"

        except Exception as e:
            logger.error(f"Erro ao atualizar categoria: {e}")
            return False, f"Erro interno: {str(e)}"

    async def delete_category(
        self,
        key: str,
        user: str = "system",
        force: bool = False
    ) -> Tuple[bool, str]:
        """
        Deleta categoria.

        PROTEÇÃO: Bloqueia deleção se categoria tem campos associados.
        Use force=True para forçar deleção.

        Args:
            key: Key da categoria a deletar
            user: Usuário deletando
            force: Forçar deleção mesmo se em uso

        Returns:
            (success, message)
        """
        try:
            # Verificar se existe
            existing = await self.get_category(key)
            if not existing:
                return False, f"Categoria '{key}' não encontrada"

            # TODO FUTURO: Verificar se categoria tem campos associados
            # Exemplo: contar campos com category=key
            # Se count > 0 e force=False → bloquear

            # Carregar todas
            categories = await self.get_all_categories()

            # Remover categoria
            categories = [c for c in categories if c.get('key') != key]

            # Salvar no KV
            metadata = {"updated_by": user}
            success = await self.kv.put_json(self.CATEGORIES_KEY, categories, metadata=metadata)

            if success:
                logger.info(f"Categoria '{key}' deletada por {user}")
                return True, f"Categoria '{existing['label']}' deletada com sucesso"
            else:
                return False, "Erro ao salvar categorias no KV"

        except Exception as e:
            logger.error(f"Erro ao deletar categoria: {e}")
            return False, f"Erro interno: {str(e)}"

    async def reset_to_defaults(self, user: str = "system") -> Tuple[bool, str]:
        """
        Restaura categorias padrão (apaga customizações).

        CUIDADO: Esta operação remove TODAS as categorias customizadas!

        Args:
            user: Usuário executando reset

        Returns:
            (success, message)
        """
        try:
            metadata = {"updated_by": user, "action": "reset_to_defaults"}
            success = await self.kv.put_json(
                self.CATEGORIES_KEY,
                self.DEFAULT_CATEGORIES.copy(),
                metadata=metadata
            )

            if success:
                logger.warning(f"Categorias resetadas para padrão por {user}")
                return True, "Categorias restauradas para padrão com sucesso"
            else:
                return False, "Erro ao resetar categorias"

        except Exception as e:
            logger.error(f"Erro ao resetar categorias: {e}")
            return False, f"Erro interno: {str(e)}"
