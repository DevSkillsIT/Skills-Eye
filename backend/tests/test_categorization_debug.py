"""
Script de debug para testar categorização de serviços
"""
import asyncio
import logging
from core.consul_manager import ConsulManager
from core.categorization_rule_engine import CategorizationRuleEngine
from core.consul_kv_config_manager import ConsulKVConfigManager

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def main():
    # Inicializar componentes
    consul_manager = ConsulManager()
    kv_manager = ConsulKVConfigManager()
    categorization_engine = CategorizationRuleEngine(kv_manager)
    
    # Carregar regras
    await categorization_engine.load_rules()

    # Buscar serviços
    # ✅ SPRINT 1 CORREÇÃO (2025-11-15): Catalog API com fallback
    all_services = await consul_manager.get_all_services_catalog(use_fallback=True)

    # Remover metadata
    all_services.pop("_metadata", None)

    # Converter para lista
    services_list = []
    for node_name, services_dict in all_services.items():
        for service_id, service_data in services_dict.items():
            service_data['Node'] = node_name
            service_data['ID'] = service_id
            services_list.append(service_data)
    
    print(f"\n{'='*80}")
    print(f"Total de serviços: {len(services_list)}")
    print(f"{'='*80}\n")
    
    # Categorizar primeiros 5 serviços
    categories_count = {}
    
    for idx, svc in enumerate(services_list[:10]):
        svc_job_name = svc.get('Service', '')
        svc_module = svc.get('Meta', {}).get('module', '')
        svc_metrics_path = svc.get('Meta', {}).get('metrics_path', '/metrics')
        
        # Categorizar
        category, type_info = categorization_engine.categorize({
            'job_name': svc_job_name,
            'module': svc_module,
            'metrics_path': svc_metrics_path
        })
        
        categories_count[category] = categories_count.get(category, 0) + 1
        
        print(f"\n[{idx+1}] Service: {svc['ID'][:60]}")
        print(f"    job_name: {svc_job_name}")
        print(f"    module: {svc_module}")
        print(f"    metrics_path: {svc_metrics_path}")
        print(f"    → Categoria: {category}")
        print(f"    → Type Info: {type_info}")
    
    print(f"\n{'='*80}")
    print(f"Resumo de categorias (primeiros 10):")
    for cat, count in sorted(categories_count.items()):
        print(f"  {cat}: {count}")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    asyncio.run(main())
