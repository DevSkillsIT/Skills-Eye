"""
Teste para verificar se correção de audit logs duplicados funcionou

ANTES DA CORREÇÃO:
- Criar preset 3x = 3 audit logs

DEPOIS DA CORREÇÃO:
- Criar preset 3x = 1 audit log (primeira criação)
- Chamadas subsequentes = update silencioso (sem audit log)
"""
import asyncio
import sys
sys.path.insert(0, '.')

from core.service_preset_manager import ServicePresetManager
from core.consul_manager import ConsulManager


async def test_audit_fix():
    """
    Testa se correção evita audit logs duplicados
    """
    print("=" * 80)
    print("TESTE: CORREÇÃO DE AUDIT LOGS DUPLICADOS")
    print("=" * 80)
    print()

    manager = ServicePresetManager()
    consul = ConsulManager()

    # Nome único para teste
    test_preset_id = "test-preset-audit-fix"

    print("[SETUP] Deletando preset de teste anterior (se existir)...")
    await manager.delete_preset(test_preset_id, user="test")
    print()

    # Contar audit logs ANTES do teste
    print("[BEFORE] Contando audit logs existentes...")
    audit_logs_before = await consul.get_kv_tree("skills/eye/audit")
    count_before = len(audit_logs_before)
    print(f"[BEFORE] Total de audit logs: {count_before}")
    print()

    # TESTE: Criar mesmo preset 5 vezes
    print("[TEST] Criando mesmo preset 5 vezes...")

    for i in range(1, 6):
        print(f"\n  Tentativa {i}/5:")
        success, message = await manager.create_preset(
            preset_id=test_preset_id,
            name="Test Preset for Audit Fix",
            service_name="test_service",
            port=9999,
            tags=["test"],
            meta_template={"env": "${env}"},
            description="Preset de teste para verificar audit logs",
            category="test",
            user="test_script"
        )

        if success:
            print(f"    [OK] {message}")
        else:
            print(f"    [ERRO] Falha: {message}")

    print()

    # Aguardar 1 segundo para garantir que audit logs foram escritos
    print("[WAIT] Aguardando 1 segundo para garantir escrita dos logs...")
    await asyncio.sleep(1)
    print()

    # Contar audit logs DEPOIS do teste
    print("[AFTER] Contando audit logs após teste...")
    audit_logs_after = await consul.get_kv_tree("skills/eye/audit")
    count_after = len(audit_logs_after)
    print(f"[AFTER] Total de audit logs: {count_after}")
    print()

    # Calcular diferença
    new_logs = count_after - count_before

    print("=" * 80)
    print("RESULTADO DO TESTE")
    print("=" * 80)
    print(f"Audit logs antes:       {count_before}")
    print(f"Audit logs depois:      {count_after}")
    print(f"Novos logs criados:     {new_logs}")
    print("=" * 80)
    print()

    # Verificar resultado
    if new_logs == 1:
        print("[SUCESSO] Correcao funcionou perfeitamente!")
        print("    Apenas 1 audit log foi criado (primeira criacao)")
        print("    As 4 tentativas seguintes foram updates silenciosos")
    elif new_logs == 0:
        print("[ATENCAO] Nenhum audit log foi criado")
        print("  Isso pode indicar que o preset ja existia antes do teste")
    else:
        print(f"[FALHA] Correcao NAO funcionou!")
        print(f"    Esperado: 1 novo audit log")
        print(f"    Obtido: {new_logs} novos audit logs")
        print(f"    Ainda ha criacao de logs duplicados!")

    print()

    # Cleanup: deletar preset de teste
    print("[CLEANUP] Deletando preset de teste...")
    await manager.delete_preset(test_preset_id, user="test")
    print()


if __name__ == "__main__":
    asyncio.run(test_audit_fix())
