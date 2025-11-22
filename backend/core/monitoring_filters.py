"""
Funcoes de filtro, ordenacao e paginacao server-side - SPEC-PERF-002 FASE 1

RESPONSABILIDADES:
- Aplicar filtros dinamicos baseados em metadata dos servicos
- Ordenar dados no servidor (evita processamento no browser)
- Extrair opcoes unicas para dropdowns de filtro (filterOptions)
- Paginar dados de forma eficiente

OBJETIVO:
- Eliminar processamento client-side que trava browser com 5000+ registros
- Reduzir payload de resposta (apenas pagina atual)
- Melhorar UX com filtros rapidos

AUTOR: Backend Expert Agent
DATA: 2025-11-22
VERSION: 1.0.0
"""

import logging
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


def apply_node_filter(
    data: List[Dict[str, Any]],
    node: Optional[str]
) -> List[Dict[str, Any]]:
    """
    Filtra dados por IP do no (node_ip).

    Args:
        data: Lista de servicos
        node: IP do no para filtrar (None ou 'all' = sem filtro)

    Returns:
        Lista filtrada de servicos
    """
    # Se nao especificou no ou especificou 'all', retorna tudo
    if not node or node == 'all':
        return data

    # Filtrar por node_ip
    filtered = [
        item for item in data
        if item.get('node_ip') == node
    ]

    logger.debug(
        f"[Filter] node='{node}': {len(data)} -> {len(filtered)} servicos"
    )

    return filtered


def apply_metadata_filters(
    data: List[Dict[str, Any]],
    filters: Dict[str, str]
) -> List[Dict[str, Any]]:
    """
    Aplica filtros dinamicos vindos dos query params.

    Os filtros sao aplicados nos campos do Meta do servico.
    Exemplo: {"company": "Empresa X", "env": "prod"}

    Args:
        data: Lista de servicos
        filters: Dicionario com campo -> valor para filtrar

    Returns:
        Lista filtrada de servicos
    """
    if not filters:
        return data

    # Remover filtros vazios ou None
    active_filters = {
        k: v for k, v in filters.items()
        if v is not None and v != '' and v != 'all'
    }

    if not active_filters:
        return data

    filtered = []
    for item in data:
        meta = item.get('Meta', {})
        matches = True

        # Verificar cada filtro ativo
        for field, value in active_filters.items():
            # Tentar buscar no Meta primeiro
            meta_value = meta.get(field)

            # Se nao estiver no Meta, tentar no nivel raiz do item
            if meta_value is None:
                meta_value = item.get(field)

            # Comparacao case-insensitive para strings
            if isinstance(meta_value, str) and isinstance(value, str):
                if meta_value.lower() != value.lower():
                    matches = False
                    break
            elif meta_value != value:
                matches = False
                break

        if matches:
            filtered.append(item)

    logger.debug(
        f"[Filter] metadata_filters={active_filters}: "
        f"{len(data)} -> {len(filtered)} servicos"
    )

    return filtered


def apply_sort(
    data: List[Dict[str, Any]],
    field: Optional[str],
    order: Optional[str]
) -> List[Dict[str, Any]]:
    """
    Ordena dados no servidor.

    Args:
        data: Lista de servicos
        field: Campo para ordenacao (ex: 'Service', 'Meta.company')
        order: Direcao da ordenacao ('ascend' | 'descend')

    Returns:
        Lista ordenada de servicos
    """
    if not field or not order:
        return data

    # Determinar direcao da ordenacao
    reverse = order.lower() == 'descend'

    def get_sort_key(item: Dict[str, Any]) -> Any:
        """
        Extrai valor para ordenacao de um item.

        Suporta campos aninhados como 'Meta.company'.
        """
        # Se campo contem '.', e um campo aninhado
        if '.' in field:
            parts = field.split('.')
            value = item
            for part in parts:
                if isinstance(value, dict):
                    value = value.get(part)
                else:
                    value = None
                    break
        else:
            # Primeiro tenta no nivel raiz
            value = item.get(field)

            # Se nao encontrou, tenta no Meta
            if value is None:
                value = item.get('Meta', {}).get(field)

        # Normalizar valor para ordenacao
        # None vem por ultimo (ou primeiro se reverse)
        if value is None:
            return (1, '')  # Tupla para colocar None no final

        # Converter para string lowercase para ordenacao consistente
        if isinstance(value, str):
            return (0, value.lower())

        # Numeros
        if isinstance(value, (int, float)):
            return (0, value)

        # Outros tipos
        return (0, str(value).lower())

    try:
        sorted_data = sorted(data, key=get_sort_key, reverse=reverse)
        logger.debug(
            f"[Sort] field='{field}', order='{order}': "
            f"{len(sorted_data)} servicos ordenados"
        )
        return sorted_data
    except Exception as e:
        logger.error(f"[Sort] Erro ao ordenar por '{field}': {e}")
        return data


def apply_pagination(
    data: List[Dict[str, Any]],
    page: int,
    page_size: int
) -> List[Dict[str, Any]]:
    """
    Aplica paginacao aos dados.

    Args:
        data: Lista de servicos
        page: Numero da pagina (comeca em 1)
        page_size: Quantidade de itens por pagina

    Returns:
        Lista com apenas os itens da pagina solicitada
    """
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 50

    # Calcular indices
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size

    # Fatiar dados
    paginated = data[start_idx:end_idx]

    logger.debug(
        f"[Pagination] page={page}, page_size={page_size}: "
        f"indices [{start_idx}:{end_idx}], retornados {len(paginated)} de {len(data)}"
    )

    return paginated


def extract_filter_options(
    data: List[Dict[str, Any]],
    fields: Optional[List[str]] = None
) -> Dict[str, List[str]]:
    """
    Extrai opcoes unicas para dropdowns de filtro.

    Analisa todos os servicos e extrai valores unicos de cada campo
    especificado (ou campos comuns se nenhum especificado).

    Args:
        data: Lista de servicos
        fields: Lista de campos para extrair (None = campos comuns)

    Returns:
        Dicionario com campo -> lista de valores unicos ordenados
        Exemplo: {
            "company": ["Empresa A", "Empresa B"],
            "env": ["dev", "prod", "staging"],
            "site": ["palmas", "rio"]
        }
    """
    # Campos padrao para extrair se nenhum especificado
    if not fields:
        fields = [
            'company', 'site', 'env', 'project',
            'module', 'Service', 'node_ip'
        ]

    # Dicionario para acumular valores unicos
    options: Dict[str, Set[str]] = {field: set() for field in fields}

    # Iterar sobre todos os servicos
    for item in data:
        meta = item.get('Meta', {})

        for field in fields:
            value = None

            # Primeiro tenta no nivel raiz
            if field in item:
                value = item[field]
            # Depois tenta no Meta
            elif field in meta:
                value = meta[field]

            # Adicionar valor se for string nao vazia
            if value and isinstance(value, str) and value.strip():
                options[field].add(value.strip())

    # Converter sets para listas ordenadas e filtrar campos vazios
    result = {}
    for field, values in options.items():
        if values:  # Apenas incluir campos que tem valores
            # Ordenar valores (case-insensitive)
            sorted_values = sorted(values, key=lambda x: x.lower())
            result[field] = sorted_values

    logger.debug(
        f"[FilterOptions] Extraidos {len(result)} campos com opcoes de "
        f"{len(data)} servicos"
    )

    return result


def process_monitoring_data(
    data: List[Dict[str, Any]],
    node: Optional[str] = None,
    filters: Optional[Dict[str, str]] = None,
    sort_field: Optional[str] = None,
    sort_order: Optional[str] = None,
    page: Optional[int] = None,
    page_size: Optional[int] = None
) -> Dict[str, Any]:
    """
    Processa dados de monitoramento aplicando filtros, ordenacao e paginacao.

    Esta funcao encapsula todo o processamento server-side:
    1. Filtro por no (node_ip)
    2. Filtros por metadata
    3. Ordenacao
    4. Paginacao
    5. Extracao de filterOptions

    Args:
        data: Lista completa de servicos
        node: IP do no para filtrar
        filters: Filtros de metadata (campo -> valor)
        sort_field: Campo para ordenacao
        sort_order: Direcao ('ascend' | 'descend')
        page: Numero da pagina (1-based)
        page_size: Itens por pagina

    Returns:
        Dicionario com:
        - data: Lista paginada de servicos
        - total: Total de servicos apos filtros (antes da paginacao)
        - page: Pagina atual
        - page_size: Tamanho da pagina
        - filter_options: Opcoes para dropdowns de filtro
    """
    # PASSO 1: Aplicar filtro por no
    filtered_data = apply_node_filter(data, node)

    # PASSO 2: Aplicar filtros de metadata
    if filters:
        filtered_data = apply_metadata_filters(filtered_data, filters)

    # PASSO 3: Extrair filterOptions dos dados filtrados
    # (antes da paginacao para ter todas as opcoes)
    filter_options = extract_filter_options(filtered_data)

    # PASSO 4: Aplicar ordenacao
    sorted_data = apply_sort(filtered_data, sort_field, sort_order)

    # PASSO 5: Aplicar paginacao (se especificado)
    total = len(sorted_data)

    if page is not None and page_size is not None:
        paginated_data = apply_pagination(sorted_data, page, page_size)
    else:
        # Sem paginacao - retornar todos (compatibilidade backward)
        paginated_data = sorted_data
        page = 1
        page_size = total

    logger.info(
        f"[ProcessData] Processados: total={len(data)}, "
        f"filtrados={total}, retornados={len(paginated_data)}, "
        f"page={page}/{(total // page_size) + 1 if page_size else 1}"
    )

    return {
        "data": paginated_data,
        "total": total,
        "page": page,
        "page_size": page_size,
        "filter_options": filter_options
    }
