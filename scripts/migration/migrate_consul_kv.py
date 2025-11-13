"""
Migração dos dados do Consul KV de skills/eye/ para skills/eye/
IMPORTANTE: Esta operação copia e depois remove as chaves antigas
"""
import asyncio
import sys
from pathlib import Path

# Adicionar backend ao path
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

from core.consul_manager import ConsulManager


async def migrate_kv_data():
    """Migra dados do Consul KV de skills/eye/ para skills/eye/."""
    print("=" * 80)
    print("MIGRACAO DE DADOS DO CONSUL KV")
    print("=" * 80)
    print()

    consul = ConsulManager()

    # 1. Listar TODAS as chaves em skills/eye/
    print("[PASSO 1/4] Listando chaves em skills/eye/...")
    old_prefix = "skills/eye/"
    new_prefix = "skills/eye/"

    try:
        old_data = await consul.get_kv_tree(old_prefix)
        total_keys = len(old_data)

        if total_keys == 0:
            print("[OK] Nenhuma chave encontrada em skills/eye/")
            print("A migracao ja foi concluida anteriormente ou nao ha dados para migrar.")
            return

        print(f"[OK] Encontradas {total_keys} chaves para migrar")
        print()

        # Mostrar exemplos
        print("Exemplos de chaves a migrar:")
        for key in list(old_data.keys())[:5]:
            print(f"  - {key}")
        if total_keys > 5:
            print(f"  ... e mais {total_keys - 5} chaves")
        print()

    except Exception as e:
        print(f"[ERRO] Falha ao listar chaves: {e}")
        return

    # 2. Copiar para novo namespace
    print("[PASSO 2/4] Copiando dados para skills/eye/...")
    copied = 0
    errors = []

    for old_key, value in old_data.items():
        try:
            # Substituir prefixo
            new_key = old_key.replace(old_prefix, new_prefix, 1)

            # Gravar no novo namespace
            success = await consul.put_kv_json(new_key, value)

            if success:
                copied += 1
                if copied % 10 == 0 or copied == total_keys:
                    print(f"  Copiadas {copied}/{total_keys} chaves...")
            else:
                errors.append(f"Falha ao copiar {old_key}")

        except Exception as e:
            errors.append(f"Erro ao copiar {old_key}: {e}")

    print(f"[OK] Copiadas {copied}/{total_keys} chaves")

    if errors:
        print(f"[AVISO] {len(errors)} erros durante a copia:")
        for err in errors[:5]:
            print(f"  - {err}")
        if len(errors) > 5:
            print(f"  ... e mais {len(errors) - 5} erros")
        print()
        print("Deseja continuar e remover as chaves antigas? (s/N): ", end="")
        resp = input().strip().lower()
        if resp != 's':
            print("[CANCELADO] Migracao abortada pelo usuario")
            return

    # 3. Verificar novo namespace
    print()
    print("[PASSO 3/4] Verificando novo namespace skills/eye/...")
    try:
        new_data = await consul.get_kv_tree(new_prefix)
        new_total = len(new_data)
        print(f"[OK] Verificadas {new_total} chaves em skills/eye/")

        if new_total != total_keys:
            print(f"[AVISO] Total de chaves difere: origem={total_keys}, destino={new_total}")
            print("Deseja continuar? (s/N): ", end="")
            resp = input().strip().lower()
            if resp != 's':
                print("[CANCELADO] Migracao abortada pelo usuario")
                return
    except Exception as e:
        print(f"[ERRO] Falha ao verificar novo namespace: {e}")
        return

    # 4. Remover chaves antigas (OPCIONAL)
    print()
    print("[PASSO 4/4] Remover chaves antigas de skills/cm/?")
    print("[AVISO] Esta operacao e IRREVERSIVEL!")
    print()
    print("Digite 'CONFIRMO' para remover as chaves antigas: ", end="")
    confirmation = input().strip()

    if confirmation != 'CONFIRMO':
        print("[CANCELADO] Chaves antigas NAO foram removidas")
        print("Voce pode remove-las manualmente mais tarde se desejar")
        print()
        print("[OK] MIGRACAO CONCLUIDA (chaves antigas mantidas)")
        return

    # Remover chaves antigas
    print()
    print("Removendo chaves antigas...")
    deleted = 0
    delete_errors = []

    for old_key in old_data.keys():
        try:
            success = await consul.delete_key(old_key)
            if success:
                deleted += 1
                if deleted % 10 == 0 or deleted == total_keys:
                    print(f"  Removidas {deleted}/{total_keys} chaves...")
            else:
                delete_errors.append(f"Falha ao remover {old_key}")
        except Exception as e:
            delete_errors.append(f"Erro ao remover {old_key}: {e}")

    print(f"[OK] Removidas {deleted}/{total_keys} chaves antigas")

    if delete_errors:
        print(f"[AVISO] {len(delete_errors)} erros durante a remocao:")
        for err in delete_errors[:5]:
            print(f"  - {err}")

    print()
    print("=" * 80)
    print("[OK] MIGRACAO DO CONSUL KV CONCLUIDA!")
    print("=" * 80)
    print()
    print("Proximo passo: Reiniciar a aplicacao para usar o novo namespace")
    print("Execute: restart-app.bat")


async def main():
    print()
    print("ATENCAO: Esta operacao ira migrar TODOS os dados do Consul KV")
    print("de skills/eye/ para skills/eye/")
    print()
    print("Tem certeza que deseja continuar? (s/N): ", end="")

    response = input().strip().lower()
    if response != 's':
        print("[CANCELADO] Operacao cancelada pelo usuario")
        return

    await migrate_kv_data()


if __name__ == '__main__':
    asyncio.run(main())
