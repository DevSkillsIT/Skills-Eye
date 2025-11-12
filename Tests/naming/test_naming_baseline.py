#!/usr/bin/env python3
"""
BASELINE DE TESTES - PRÉ-MIGRAÇÃO

Testa TODOS os cenários atuais antes da migração para naming dinâmico.
Salva resultados detalhados para comparação pós-migração.

Data: 2025-11-12
"""

import asyncio
import json
import sys
import os
from datetime import datetime
from typing import Dict, List, Any

# Adicionar backend ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.core.naming_utils import (
    apply_site_suffix,
    extract_site_from_metadata,
    get_naming_config
)
from backend.core.kv_manager import KVManager


class NamingBaselineTests:
    """Testes de baseline para sistema de naming"""
    
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "tests": {},
            "summary": {
                "total_tests": 0,
                "passed": 0,
                "failed": 0
            }
        }
    
    def add_test_result(self, test_name: str, result: Dict[str, Any]):
        """Adiciona resultado de teste"""
        self.results["tests"][test_name] = result
        self.results["summary"]["total_tests"] += 1
        
        if result.get("passed", False):
            self.results["summary"]["passed"] += 1
        else:
            self.results["summary"]["failed"] += 1
        
        # Print resultado imediatamente
        status = "✅ PASS" if result.get("passed") else "❌ FAIL"
        print(f"{status} - {test_name}")
        if not result.get("passed"):
            print(f"  Expected: {result.get('expected')}")
            print(f"  Got: {result.get('actual')}")
    
    async def test_naming_config_from_env(self):
        """
        TEST 1: Configuração de naming vem do .env
        
        COMPORTAMENTO ATUAL:
        - NAMING_STRATEGY do .env
        - SITE_SUFFIX_ENABLED do .env
        - DEFAULT_SITE do .env
        """
        print("\n🔍 TEST 1: Naming config from .env")
        
        config = get_naming_config()
        
        result = {
            "actual": config,
            "expected": {
                "naming_strategy": "option2",
                "suffix_enabled": True,
                "default_site": "palmas"
            },
            "passed": (
                config.get("naming_strategy") == "option2" and
                config.get("suffix_enabled") == True and
                config.get("default_site") == "palmas"
            ),
            "notes": "Config atual vem de variáveis de ambiente"
        }
        
        self.add_test_result("test_naming_config_from_env", result)
    
    async def test_apply_site_suffix_default_site(self):
        """
        TEST 2: Sufixo NÃO aplicado para site padrão (palmas)
        
        COMPORTAMENTO ATUAL:
        - site='palmas' → sem sufixo
        - default_site='palmas' (hardcoded no .env)
        """
        print("\n🔍 TEST 2: Apply suffix - default site")
        
        service_name = "node_exporter"
        result_name = apply_site_suffix(service_name, site="palmas")
        
        result = {
            "input": {"service_name": service_name, "site": "palmas"},
            "actual": result_name,
            "expected": "node_exporter",
            "passed": result_name == "node_exporter",
            "notes": "Site padrão (palmas) não deve receber sufixo"
        }
        
        self.add_test_result("test_apply_site_suffix_default_site", result)
    
    async def test_apply_site_suffix_non_default_site(self):
        """
        TEST 3: Sufixo APLICADO para site não-padrão (rio)
        
        COMPORTAMENTO ATUAL:
        - site='rio' → com sufixo _rio
        - option2 ativo
        """
        print("\n🔍 TEST 3: Apply suffix - non-default site")
        
        service_name = "node_exporter"
        result_name = apply_site_suffix(service_name, site="rio")
        
        result = {
            "input": {"service_name": service_name, "site": "rio"},
            "actual": result_name,
            "expected": "node_exporter_rio",
            "passed": result_name == "node_exporter_rio",
            "notes": "Site remoto (rio) deve receber sufixo _rio"
        }
        
        self.add_test_result("test_apply_site_suffix_non_default_site", result)
    
    async def test_apply_site_suffix_dtc(self):
        """
        TEST 4: Sufixo APLICADO para DTC
        """
        print("\n🔍 TEST 4: Apply suffix - DTC site")
        
        service_name = "blackbox_exporter"
        result_name = apply_site_suffix(service_name, site="dtc")
        
        result = {
            "input": {"service_name": service_name, "site": "dtc"},
            "actual": result_name,
            "expected": "blackbox_exporter_dtc",
            "passed": result_name == "blackbox_exporter_dtc",
            "notes": "Site DTC deve receber sufixo _dtc"
        }
        
        self.add_test_result("test_apply_site_suffix_dtc", result)
    
    async def test_extract_site_from_cluster_rio(self):
        """
        TEST 5: Extração de site pelo cluster (Rio)
        
        COMPORTAMENTO ATUAL:
        - cluster='rmd-ldc-cliente' → site='rio' (hardcoded)
        """
        print("\n🔍 TEST 5: Extract site from cluster - Rio")
        
        metadata = {"cluster": "rmd-ldc-cliente"}
        site = extract_site_from_metadata(metadata)
        
        result = {
            "input": metadata,
            "actual": site,
            "expected": "rio",
            "passed": site == "rio",
            "notes": "Cluster 'rmd-ldc-cliente' deve inferir site='rio'"
        }
        
        self.add_test_result("test_extract_site_from_cluster_rio", result)
    
    async def test_extract_site_from_cluster_dtc(self):
        """
        TEST 6: Extração de site pelo cluster (DTC)
        """
        print("\n🔍 TEST 6: Extract site from cluster - DTC")
        
        metadata = {"cluster": "dtc-remote-skills"}
        site = extract_site_from_metadata(metadata)
        
        result = {
            "input": metadata,
            "actual": site,
            "expected": "dtc",
            "passed": site == "dtc",
            "notes": "Cluster 'dtc-remote-skills' deve inferir site='dtc'"
        }
        
        self.add_test_result("test_extract_site_from_cluster_dtc", result)
    
    async def test_extract_site_from_cluster_palmas(self):
        """
        TEST 7: Extração de site pelo cluster (Palmas)
        """
        print("\n🔍 TEST 7: Extract site from cluster - Palmas")
        
        metadata = {"cluster": "palmas-master"}
        site = extract_site_from_metadata(metadata)
        
        result = {
            "input": metadata,
            "actual": site,
            "expected": "palmas",
            "passed": site == "palmas",
            "notes": "Cluster 'palmas-master' deve inferir site='palmas'"
        }
        
        self.add_test_result("test_extract_site_from_cluster_palmas", result)
    
    async def test_extract_site_from_explicit_field(self):
        """
        TEST 8: Extração de site pelo campo 'site' explícito
        """
        print("\n🔍 TEST 8: Extract site from explicit field")
        
        metadata = {"site": "rio", "cluster": "outro-cluster"}
        site = extract_site_from_metadata(metadata)
        
        result = {
            "input": metadata,
            "actual": site,
            "expected": "rio",
            "passed": site == "rio",
            "notes": "Campo 'site' explícito tem prioridade sobre cluster"
        }
        
        self.add_test_result("test_extract_site_from_explicit_field", result)
    
    async def test_sites_from_kv(self):
        """
        TEST 9: Sites carregados do KV
        
        COMPORTAMENTO ATUAL:
        - KV: skills/eye/metadata/sites
        - 3 sites: palmas, rio, dtc
        - Cada site tem: code, name, is_default, color, cluster, prometheus_instance
        """
        print("\n🔍 TEST 9: Sites from KV")
        
        kv = KVManager()
        try:
            kv_data = await kv.get_json("skills/eye/metadata/sites")
            
            if kv_data and "data" in kv_data and "sites" in kv_data["data"]:
                sites = kv_data["data"]["sites"]
                
                # Validar estrutura de cada site
                site_validations = []
                for site in sites:
                    validation = {
                        "code": site.get("code"),
                        "name": site.get("name"),
                        "is_default": site.get("is_default"),
                        "color": site.get("color"),
                        "cluster": site.get("cluster"),
                        "prometheus_instance": site.get("prometheus_instance"),
                        "has_all_fields": all([
                            site.get("code"),
                            site.get("name"),
                            "is_default" in site,
                            site.get("color"),
                            site.get("cluster"),
                            site.get("prometheus_instance")
                        ])
                    }
                    site_validations.append(validation)
                
                result = {
                    "actual": {
                        "total_sites": len(sites),
                        "sites": site_validations
                    },
                    "expected": {
                        "total_sites": 3,
                        "all_sites_valid": True
                    },
                    "passed": len(sites) == 3 and all(s["has_all_fields"] for s in site_validations),
                    "notes": "KV deve conter 3 sites com todos os campos necessários"
                }
            else:
                result = {
                    "actual": "KV vazio ou estrutura inválida",
                    "expected": "3 sites no KV",
                    "passed": False,
                    "notes": "KV não contém sites"
                }
        
        except Exception as e:
            result = {
                "actual": f"Erro: {str(e)}",
                "expected": "3 sites no KV",
                "passed": False,
                "notes": "Erro ao acessar KV"
            }
        
        self.add_test_result("test_sites_from_kv", result)
    
    async def test_site_colors_in_kv(self):
        """
        TEST 10: Cores dos sites no KV
        
        COMPORTAMENTO ATUAL:
        - palmas: color='red'
        - rio: color='gold'
        - dtc: color='blue'
        
        PROBLEMA IDENTIFICADO:
        - Frontend tem cores HARDCODED ERRADAS:
          - palmas: 'blue' (deveria ser 'red')
          - rio: 'green' (deveria ser 'gold')
          - dtc: 'orange' (deveria ser 'blue')
        """
        print("\n🔍 TEST 10: Site colors in KV")
        
        kv = KVManager()
        try:
            kv_data = await kv.get_json("skills/eye/metadata/sites")
            
            if kv_data and "data" in kv_data and "sites" in kv_data["data"]:
                sites = kv_data["data"]["sites"]
                
                # Mapear cores por site
                colors_map = {site["code"]: site["color"] for site in sites}
                
                # Cores ESPERADAS do KV
                expected_colors = {
                    "palmas": "red",
                    "rio": "gold",
                    "dtc": "blue"
                }
                
                # Cores HARDCODED ERRADAS no frontend
                frontend_hardcoded = {
                    "palmas": "blue",
                    "rio": "green",
                    "dtc": "orange"
                }
                
                result = {
                    "actual": {
                        "kv_colors": colors_map,
                        "frontend_hardcoded": frontend_hardcoded
                    },
                    "expected": {
                        "kv_colors": expected_colors,
                        "should_match": True
                    },
                    "passed": colors_map == expected_colors,
                    "discrepancies": {
                        site: {
                            "kv": colors_map.get(site),
                            "frontend": frontend_hardcoded.get(site),
                            "matches": colors_map.get(site) == frontend_hardcoded.get(site)
                        }
                        for site in expected_colors.keys()
                    },
                    "notes": "KV tem cores corretas, mas frontend tem hardcoding errado"
                }
            else:
                result = {
                    "actual": "KV vazio",
                    "expected": "Cores dos sites",
                    "passed": False,
                    "notes": "Não foi possível carregar cores do KV"
                }
        
        except Exception as e:
            result = {
                "actual": f"Erro: {str(e)}",
                "expected": "Cores dos sites",
                "passed": False,
                "notes": "Erro ao acessar KV"
            }
        
        self.add_test_result("test_site_colors_in_kv", result)
    
    async def test_apply_suffix_with_cluster_inference(self):
        """
        TEST 11: Aplicar sufixo usando inferência de site pelo cluster
        
        COMPORTAMENTO ATUAL:
        - Passa cluster ao invés de site
        - apply_site_suffix() infere site do cluster
        - Aplica sufixo baseado no site inferido
        """
        print("\n🔍 TEST 11: Apply suffix with cluster inference")
        
        test_cases = [
            {
                "service_name": "mysql_exporter",
                "cluster": "rmd-ldc-cliente",
                "expected_site": "rio",
                "expected_name": "mysql_exporter_rio"
            },
            {
                "service_name": "postgres_exporter",
                "cluster": "dtc-remote-skills",
                "expected_site": "dtc",
                "expected_name": "postgres_exporter_dtc"
            },
            {
                "service_name": "redis_exporter",
                "cluster": "palmas-master",
                "expected_site": "palmas",
                "expected_name": "redis_exporter"  # Sem sufixo (site padrão)
            }
        ]
        
        results = []
        all_passed = True
        
        for case in test_cases:
            result_name = apply_site_suffix(case["service_name"], cluster=case["cluster"])
            passed = result_name == case["expected_name"]
            
            results.append({
                "input": {
                    "service_name": case["service_name"],
                    "cluster": case["cluster"]
                },
                "expected_site": case["expected_site"],
                "expected_name": case["expected_name"],
                "actual_name": result_name,
                "passed": passed
            })
            
            if not passed:
                all_passed = False
        
        result = {
            "test_cases": results,
            "passed": all_passed,
            "notes": "Inferência de site pelo cluster deve funcionar corretamente"
        }
        
        self.add_test_result("test_apply_suffix_with_cluster_inference", result)
    
    async def test_unknown_site_handling(self):
        """
        TEST 12: Comportamento com site desconhecido
        
        COMPORTAMENTO ATUAL:
        - Site não reconhecido → sem sufixo
        """
        print("\n🔍 TEST 12: Unknown site handling")
        
        service_name = "test_exporter"
        result_name = apply_site_suffix(service_name, site="saopaulo")
        
        result = {
            "input": {"service_name": service_name, "site": "saopaulo"},
            "actual": result_name,
            "expected": "test_exporter",
            "passed": result_name == "test_exporter",
            "notes": "Site desconhecido deve retornar nome sem sufixo"
        }
        
        self.add_test_result("test_unknown_site_handling", result)
    
    async def run_all_tests(self):
        """Executa todos os testes"""
        print("=" * 80)
        print("BASELINE DE TESTES - PRÉ-MIGRAÇÃO")
        print("=" * 80)
        print(f"Data: {self.results['timestamp']}")
        print("=" * 80)
        
        # Executar todos os testes
        await self.test_naming_config_from_env()
        await self.test_apply_site_suffix_default_site()
        await self.test_apply_site_suffix_non_default_site()
        await self.test_apply_site_suffix_dtc()
        await self.test_extract_site_from_cluster_rio()
        await self.test_extract_site_from_cluster_dtc()
        await self.test_extract_site_from_cluster_palmas()
        await self.test_extract_site_from_explicit_field()
        await self.test_sites_from_kv()
        await self.test_site_colors_in_kv()
        await self.test_apply_suffix_with_cluster_inference()
        await self.test_unknown_site_handling()
        
        # Salvar resultados
        output_file = "BASELINE_PRE_MIGRATION.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        # Print resumo
        print("\n" + "=" * 80)
        print("RESUMO DOS TESTES")
        print("=" * 80)
        print(f"Total de testes: {self.results['summary']['total_tests']}")
        print(f"✅ Passou: {self.results['summary']['passed']}")
        print(f"❌ Falhou: {self.results['summary']['failed']}")
        print(f"\n📄 Resultados salvos em: {output_file}")
        print("=" * 80)
        
        return self.results


async def main():
    """Função principal"""
    # CRÍTICO: Forçar atualização do cache ANTES dos testes
    from backend.core.naming_utils import _update_cache
    print("🔄 Atualizando cache de naming antes dos testes...")
    await _update_cache()
    print("✅ Cache atualizado\n")
    
    tests = NamingBaselineTests()
    results = await tests.run_all_tests()
    
    # Retornar código de saída baseado nos resultados
    if results['summary']['failed'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
