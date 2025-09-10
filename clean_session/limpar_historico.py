#!/usr/bin/env python3
"""
Script para limpar todo o histórico de requisições do Atlas
Este script remove:
1. Todos os arquivos JSON da pasta historico/
2. Todos os dados do banco de dados SQLite (conversas e mensagens)
3. Sessões do Flask (arquivos na pasta flask_session/)
"""

import os
import shutil
import sqlite3
from pathlib import Path

def limpar_arquivos_historico():
    """Remove todos os arquivos JSON da pasta historico/"""
    print("🗂️  Limpando arquivos de histórico...")
    
    historico_dir = Path("historico")
    if historico_dir.exists():
        arquivos_removidos = 0
        for arquivo in historico_dir.glob("*.json"):
            try:
                arquivo.unlink()
                arquivos_removidos += 1
                print(f"   ✅ Removido: {arquivo.name}")
            except Exception as e:
                print(f"   ❌ Erro ao remover {arquivo.name}: {e}")
        
        print(f"   📊 Total de arquivos removidos: {arquivos_removidos}")
    else:
        print("   ℹ️  Pasta historico/ não encontrada")

def limpar_banco_dados():
    """Remove todos os dados do banco SQLite"""
    print("🗄️  Limpando banco de dados...")
    
    db_path = Path("instance/atlas.db")
    if db_path.exists():
        try:
            # Conecta ao banco
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # Remove todas as mensagens
            cursor.execute("DELETE FROM message")
            mensagens_removidas = cursor.rowcount
            
            # Remove todas as conversas
            cursor.execute("DELETE FROM conversation")
            conversas_removidas = cursor.rowcount
            
            # Confirma as alterações
            conn.commit()
            conn.close()
            
            print(f"   ✅ Mensagens removidas: {mensagens_removidas}")
            print(f"   ✅ Conversas removidas: {conversas_removidas}")
            
        except Exception as e:
            print(f"   ❌ Erro ao limpar banco de dados: {e}")
    else:
        print("   ℹ️  Banco de dados não encontrado")

def limpar_sessoes_flask():
    """Remove todos os arquivos de sessão do Flask"""
    print("🔐 Limpando sessões do Flask...")
    
    flask_session_dir = Path("flask_session")
    if flask_session_dir.exists():
        arquivos_removidos = 0
        for arquivo in flask_session_dir.iterdir():
            if arquivo.is_file():
                try:
                    arquivo.unlink()
                    arquivos_removidos += 1
                    print(f"   ✅ Removido: {arquivo.name}")
                except Exception as e:
                    print(f"   ❌ Erro ao remover {arquivo.name}: {e}")
        
        print(f"   📊 Total de sessões removidas: {arquivos_removidos}")
    else:
        print("   ℹ️  Pasta flask_session/ não encontrada")

def limpar_cache_python():
    """Remove arquivos de cache do Python"""
    print("🐍 Limpando cache do Python...")
    
    cache_dirs = ["__pycache__", "venv/__pycache__"]
    for cache_dir in cache_dirs:
        cache_path = Path(cache_dir)
        if cache_path.exists():
            try:
                shutil.rmtree(cache_path)
                print(f"   ✅ Cache removido: {cache_dir}")
            except Exception as e:
                print(f"   ❌ Erro ao remover cache {cache_dir}: {e}")

def main():
    """Função principal que executa toda a limpeza"""
    print("🧹 ATLAS - LIMPEZA COMPLETA DO HISTÓRICO")
    print("=" * 50)
    
    # Confirmação do usuário
    resposta = input("⚠️  ATENÇÃO: Esta ação irá remover TODOS os dados de histórico.\n"
                    "   - Conversas e mensagens do banco de dados\n"
                    "   - Arquivos de histórico JSON\n"
                    "   - Sessões ativas do Flask\n"
                    "   - Cache do Python\n\n"
                    "Tem certeza que deseja continuar? (digite 'SIM' para confirmar): ")
    
    if resposta.upper() != 'SIM':
        print("❌ Operação cancelada pelo usuário.")
        return
    
    print("\n🚀 Iniciando limpeza...\n")
    
    # Executa todas as limpezas
    limpar_banco_dados()
    print()
    
    limpar_arquivos_historico()
    print()
    
    limpar_sessoes_flask()
    print()
    
    limpar_cache_python()
    print()
    
    print("✅ LIMPEZA CONCLUÍDA COM SUCESSO!")
    print("=" * 50)
    print("📋 Resumo da limpeza:")
    print("   • Banco de dados SQLite: Limpo")
    print("   • Arquivos de histórico JSON: Removidos")
    print("   • Sessões do Flask: Removidas")
    print("   • Cache do Python: Removido")
    print("\n🎉 Seu Atlas está agora com histórico completamente limpo!")

if __name__ == "__main__":
    main()
