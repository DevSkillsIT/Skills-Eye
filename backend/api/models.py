"""
Modelos Pydantic para validação e serialização de dados
"""
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any


class ServiceMetadata(BaseModel):
    """Metadados de um serviço Consul"""
    module: str = Field(..., description="Módulo de monitoramento (icmp, http_2xx, etc)")
    company: str = Field(..., description="Nome da empresa")
    project: str = Field(..., description="Nome do projeto")
    env: str = Field(..., description="Ambiente (prod, dev, staging, etc)")
    name: str = Field(..., description="Nome do serviço")
    instance: str = Field(..., description="Instância alvo (IP, URL, etc)")
    localizacao: Optional[str] = Field(None, description="Localização física")
    tipo: Optional[str] = Field(None, description="Tipo do dispositivo/serviço")
    cod_localidade: Optional[str] = Field(None, description="Código da localidade")
    cidade: Optional[str] = Field(None, description="Cidade")
    notas: Optional[str] = Field(None, description="Notas adicionais")
    provedor: Optional[str] = Field(None, description="Provedor do serviço")
    fabricante: Optional[str] = Field(None, description="Fabricante do equipamento")
    modelo: Optional[str] = Field(None, description="Modelo do equipamento")
    tipo_dispositivo_abrev: Optional[str] = Field(None, description="Tipo do dispositivo (abreviado)")
    glpi_url: Optional[str] = Field(None, description="URL do item no GLPI")

    class Config:
        json_schema_extra = {
            "example": {
                "module": "icmp",
                "company": "Skills IT",
                "project": "Monitoring",
                "env": "prod",
                "name": "Gateway Principal",
                "instance": "172.16.1.1",
                "localizacao": "Data Center",
                "tipo": "Network",
                "cidade": "São Paulo"
            }
        }


class ServiceData(BaseModel):
    """Dados completos de um serviço Consul"""
    id: str = Field(..., description="ID único do serviço")
    name: str = Field(..., description="Nome do serviço no Consul")
    tags: List[str] = Field(default_factory=list, description="Tags do serviço")
    port: Optional[int] = Field(None, description="Porta do serviço")
    address: Optional[str] = Field(None, description="Endereço do serviço")
    Meta: ServiceMetadata = Field(..., description="Metadados customizados")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "blackbox_icmp_gateway_prod",
                "name": "blackbox_exporter",
                "tags": ["monitoring", "icmp"],
                "port": 9115,
                "Meta": {
                    "module": "icmp",
                    "company": "Skills IT",
                    "project": "Monitoring",
                    "env": "prod",
                    "name": "Gateway Principal",
                    "instance": "172.16.1.1"
                }
            }
        }


class ServiceCreateRequest(BaseModel):
    """Requisição para criar um novo serviço"""
    id: str = Field(..., description="ID único do serviço")
    name: str = Field(..., description="Nome do serviço no Consul")
    tags: List[str] = Field(default_factory=list, description="Tags do serviço")
    port: Optional[int] = Field(None, description="Porta do serviço")
    address: Optional[str] = Field(None, description="Endereço do serviço")
    Meta: Dict[str, str] = Field(..., description="Metadados customizados")
    node_addr: Optional[str] = Field(None, description="Endereço do nó onde registrar")


class ServiceUpdateRequest(BaseModel):
    """Requisição para atualizar um serviço existente"""
    name: Optional[str] = Field(None, description="Nome do serviço no Consul")
    tags: Optional[List[str]] = Field(None, description="Tags do serviço")
    port: Optional[int] = Field(None, description="Porta do serviço")
    address: Optional[str] = Field(None, description="Endereço do serviço")
    Meta: Optional[Dict[str, str]] = Field(None, description="Metadados customizados")
    node_addr: Optional[str] = Field(None, description="Endereço do nó")


class ConsulConfig(BaseModel):
    """Configuração de conexão com Consul"""
    host: str = Field(..., description="Endereço do servidor Consul")
    port: int = Field(8500, description="Porta do Consul")
    token: Optional[str] = Field(None, description="Token de autenticação")

    class Config:
        json_schema_extra = {
            "example": {
                "host": "172.16.1.26",
                "port": 8500,
                "token": "your-consul-token-here"
            }
        }


class ConsulConfigResponse(BaseModel):
    """Resposta com configuração atual do Consul"""
    host: str
    port: int
    has_token: bool = Field(..., description="Se há token configurado (não mostra o token)")
    main_server: str
    known_nodes: Dict[str, str]


class HealthCheckResponse(BaseModel):
    """Resposta do health check"""
    healthy: bool
    message: str
    consul_version: Optional[str] = None
    leader: Optional[str] = None
    nodes_count: Optional[int] = None


class ServiceListResponse(BaseModel):
    """Resposta da listagem de serviços"""
    success: bool
    data: Dict[str, Any]  # Para lista de um nó ou todos os nós
    total: int
    node: Optional[str] = Field(None, description="Nó específico se aplicável")


class ServiceResponse(BaseModel):
    """Resposta padrão de operações de serviço"""
    success: bool
    message: str
    service_id: Optional[str] = None
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    """Resposta de erro padrão"""
    success: bool = False
    error: str
    detail: Optional[str] = None


class BlackboxTarget(BaseModel):
    """Payload básico de um alvo blackbox"""
    module: str
    company: str
    project: str
    env: str
    name: str
    instance: str
    group: Optional[str] = Field(None, description="Grupo/categoria do alvo")
    interval: Optional[str] = Field("30s", description="Intervalo do probe")
    timeout: Optional[str] = Field("10s", description="Timeout do probe")
    enabled: bool = Field(True, description="Alvo habilitado")
    labels: Optional[Dict[str, str]] = Field(
        default=None,
        description="Rótulos extras (chave/valor) que serão enviados como meta",
    )
    notes: Optional[str] = Field(None, description="Notas/observações")


class BlackboxUpdateRequest(BaseModel):
    """Solicitação de atualização: remove um alvo antigo e cria outro"""
    current: BlackboxTarget
    replacement: BlackboxTarget


class BlackboxDeleteRequest(BaseModel):
    """
    Payload de remoção simplificado.
    Informações necessárias: service_id + service_name + node_addr + node_name + datacenter
    """
    service_id: str              # ID único (ex: icmp/Company/Project/Env@Name)
    service_name: Optional[str] = None  # Nome do serviço no Consul (ex: blackbox_remote_rmd_ldc) - para Método 2
    node_addr: Optional[str] = None     # IP do agente (ex: 172.16.1.26) - para Método 1
    node_name: Optional[str] = None     # Nome do node (ex: glpi-grafana-prometheus.skillsit.com.br) - para Método 2
    datacenter: Optional[str] = None    # Datacenter (ex: dtc-skills-local) - para Método 2


class KVPutRequest(BaseModel):
    """Requisição para escrita no Consul KV"""
    key: str = Field(..., description="Chave completa (prefixo skills/cm/)")
    value: Dict[str, Any] = Field(..., description="Valor JSON serializável")


class FieldConfigUpdate(BaseModel):
    """
    Modelo para atualização de configurações de campos metadata

    IMPORTANTE: Todos os campos são opcionais para permitir atualizações parciais
    """
    display_name: Optional[str] = Field(None, description="Nome amigável para exibição")
    description: Optional[str] = Field(None, description="Descrição do campo")
    category: Optional[str] = Field(None, description="Categoria do campo (vem da página Valores de Referência)")
    field_type: Optional[str] = Field(None, description="Tipo do campo (text, select, number, date)")
    order: Optional[int] = Field(None, description="Ordem de exibição")
    required: Optional[bool] = Field(None, description="Campo obrigatório?")
    show_in_table: Optional[bool] = Field(None, description="Mostrar em tabelas?")
    show_in_dashboard: Optional[bool] = Field(None, description="Mostrar no dashboard?")
    show_in_form: Optional[bool] = Field(None, description="Mostrar em formulários?")
    editable: Optional[bool] = Field(None, description="Campo editável?")
    show_in_services: Optional[bool] = Field(None, description="Mostrar na página Services?")
    show_in_exporters: Optional[bool] = Field(None, description="Mostrar na página Exporters?")
    show_in_blackbox: Optional[bool] = Field(None, description="Mostrar na página Blackbox?")

    class Config:
        json_schema_extra = {
            "example": {
                "display_name": "Sistema Operacional",
                "description": "Sistema operacional do servidor",
                "category": "Infraestrutura",
                "field_type": "select",
                "order": 10,
                "required": False,
                "show_in_table": True,
                "show_in_dashboard": True,
                "show_in_form": True,
                "editable": True,
                "show_in_services": True,
                "show_in_exporters": True,
                "show_in_blackbox": False
            }
        }
