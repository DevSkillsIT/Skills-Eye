#!/usr/bin/env python3
"""
Testes de Integração: SPEC-ARCH-001

Valida que a integração do sistema de categorização dinâmica está funcionando
corretamente conforme especificado no SPEC-ARCH-001.

Testes incluídos:
1. Engine de categorização carrega regras do KV
2. Tipos são categorizados corretamente pelo engine
3. form_schema foi removido das regras
4. Endpoints funcionam sem form_schema

AUTOR: Sistema de Refatoração Skills Eye v2.0
DATA: 2025-11-20
"""

import asyncio
import sys
import os
import logging

# Adicionar o diretório pai ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.consul_kv_config_manager import ConsulKVConfigManager
from core.categorization_rule_engine import CategorizationRuleEngine

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestSPECARCH001:
    """Testes para SPEC-ARCH-001"""

    def __init__(self):
        self.config_manager = ConsulKVConfigManager()
        self.engine = CategorizationRuleEngine(self.config_manager)
        self.passed = 0
        self.failed = 0
        self.errors = []

    def _assert(self, condition: bool, message: str):
        """Helper para assertions com log"""
        if condition:
            self.passed += 1
            logger.info(f"✅ PASS: {message}")
        else:
            self.failed += 1
            self.errors.append(message)
            logger.error(f"❌ FAIL: {message}")

    async def test_engine_loads_rules(self):
        """Teste 1: Engine carrega regras do KV"""
        logger.info("\n" + "=" * 60)
        logger.info("TEST 1: Engine carrega regras do KV")
        logger.info("=" * 60)

        success = await self.engine.load_rules(force_reload=True)

        self._assert(success, "Engine conseguiu carregar regras do KV")
        self._assert(len(self.engine.rules) > 0, f"Engine carregou {len(self.engine.rules)} regras")
        self._assert(self.engine.default_category == 'custom-exporters', f"default_category é 'custom-exporters'")

    async def test_categorization_blackbox_icmp(self):
        """Teste 2: Categorização de ICMP (network-probes)"""
        logger.info("\n" + "=" * 60)
        logger.info("TEST 2: Categorização de ICMP (network-probes)")
        logger.info("=" * 60)

        job_data = {
            'job_name': 'icmp',
            'metrics_path': '/probe',
            'module': 'icmp'
        }

        category, type_info = self.engine.categorize(job_data)

        self._assert(category == 'network-probes', f"Categoria é 'network-probes' (got: {category})")
        self._assert('display_name' in type_info, "type_info contém 'display_name'")
        self._assert('exporter_type' in type_info, "type_info contém 'exporter_type'")

        logger.info(f"   Resultado: category={category}, display_name={type_info.get('display_name')}")

    async def test_categorization_http_2xx(self):
        """Teste 3: Categorização de HTTP 2xx (web-probes)"""
        logger.info("\n" + "=" * 60)
        logger.info("TEST 3: Categorização de HTTP 2xx (web-probes)")
        logger.info("=" * 60)

        job_data = {
            'job_name': 'http_2xx',
            'metrics_path': '/probe',
            'module': 'http_2xx'
        }

        category, type_info = self.engine.categorize(job_data)

        self._assert(category == 'web-probes', f"Categoria é 'web-probes' (got: {category})")

        logger.info(f"   Resultado: category={category}, display_name={type_info.get('display_name')}")

    async def test_categorization_node_exporter(self):
        """Teste 4: Categorização de Node Exporter (system-exporters)"""
        logger.info("\n" + "=" * 60)
        logger.info("TEST 4: Categorização de Node Exporter (system-exporters)")
        logger.info("=" * 60)

        job_data = {
            'job_name': 'node_exporter',
            'metrics_path': '/metrics',
            'module': None
        }

        category, type_info = self.engine.categorize(job_data)

        self._assert(category == 'system-exporters', f"Categoria é 'system-exporters' (got: {category})")

        logger.info(f"   Resultado: category={category}, display_name={type_info.get('display_name')}")

    async def test_categorization_mysql(self):
        """Teste 5: Categorização de MySQL (database-exporters)"""
        logger.info("\n" + "=" * 60)
        logger.info("TEST 5: Categorização de MySQL (database-exporters)")
        logger.info("=" * 60)

        job_data = {
            'job_name': 'mysql_exporter',
            'metrics_path': '/metrics',
            'module': None
        }

        category, type_info = self.engine.categorize(job_data)

        self._assert(category == 'database-exporters', f"Categoria é 'database-exporters' (got: {category})")

        logger.info(f"   Resultado: category={category}, display_name={type_info.get('display_name')}")

    async def test_form_schema_not_in_rules(self):
        """Teste 6: form_schema não existe nas regras"""
        logger.info("\n" + "=" * 60)
        logger.info("TEST 6: form_schema não existe nas regras (deve existir apenas em monitoring-types)")
        logger.info("=" * 60)

        # Buscar regras diretamente do KV
        rules_data = await self.config_manager.get('monitoring-types/categorization/rules')

        if not rules_data:
            self._assert(False, "Regras não encontradas no KV")
            return

        rules_with_schema = 0
        for rule in rules_data.get('rules', []):
            if 'form_schema' in rule and rule['form_schema'] is not None:
                rules_with_schema += 1
                logger.warning(f"   ⚠️  Regra '{rule['id']}' ainda tem form_schema")

        self._assert(
            rules_with_schema == 0,
            f"Nenhuma regra deve ter form_schema (encontradas: {rules_with_schema})"
        )

        if rules_with_schema > 0:
            logger.info("   💡 Execute: python scripts/migrate_remove_form_schema_from_rules.py")

    async def test_categorization_default(self):
        """Teste 7: Jobs desconhecidos vão para custom-exporters"""
        logger.info("\n" + "=" * 60)
        logger.info("TEST 7: Jobs desconhecidos vão para custom-exporters")
        logger.info("=" * 60)

        job_data = {
            'job_name': 'unknown_job_xyz123',
            'metrics_path': '/metrics',
            'module': None
        }

        category, type_info = self.engine.categorize(job_data)

        self._assert(
            category == 'custom-exporters',
            f"Job desconhecido vai para 'custom-exporters' (got: {category})"
        )

        logger.info(f"   Resultado: category={category}, display_name={type_info.get('display_name')}")

    async def test_engine_summary(self):
        """Teste 8: Engine retorna resumo correto"""
        logger.info("\n" + "=" * 60)
        logger.info("TEST 8: Engine retorna resumo correto")
        logger.info("=" * 60)

        summary = self.engine.get_rules_summary()

        self._assert('total_rules' in summary, "Resumo contém 'total_rules'")
        self._assert('categories' in summary, "Resumo contém 'categories'")
        self._assert('default_category' in summary, "Resumo contém 'default_category'")

        logger.info(f"   Total de regras: {summary.get('total_rules')}")
        logger.info(f"   Categorias: {list(summary.get('categories', {}).keys())}")

    async def run_all_tests(self):
        """Executa todos os testes"""
        logger.info("\n" + "=" * 70)
        logger.info("SPEC-ARCH-001: TESTES DE INTEGRAÇÃO")
        logger.info("=" * 70)

        tests = [
            self.test_engine_loads_rules,
            self.test_categorization_blackbox_icmp,
            self.test_categorization_http_2xx,
            self.test_categorization_node_exporter,
            self.test_categorization_mysql,
            self.test_form_schema_not_in_rules,
            self.test_categorization_default,
            self.test_engine_summary,
        ]

        for test in tests:
            try:
                await test()
            except Exception as e:
                self.failed += 1
                self.errors.append(f"{test.__name__}: {str(e)}")
                logger.error(f"❌ ERRO em {test.__name__}: {e}")

        # Resumo final
        logger.info("\n" + "=" * 70)
        logger.info("RESUMO DOS TESTES")
        logger.info("=" * 70)
        logger.info(f"✅ Passed: {self.passed}")
        logger.info(f"❌ Failed: {self.failed}")

        if self.errors:
            logger.info("\nErros encontrados:")
            for error in self.errors:
                logger.info(f"   - {error}")

        total = self.passed + self.failed
        success_rate = (self.passed / total * 100) if total > 0 else 0
        logger.info(f"\nTaxa de sucesso: {success_rate:.1f}%")

        return self.failed == 0


async def main():
    """Função principal"""
    tester = TestSPECARCH001()
    success = await tester.run_all_tests()

    if success:
        logger.info("\n✅ TODOS OS TESTES PASSARAM!")
        sys.exit(0)
    else:
        logger.error("\n❌ ALGUNS TESTES FALHARAM!")
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
