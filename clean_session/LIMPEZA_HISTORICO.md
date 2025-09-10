# 🧹 Limpeza do Histórico do Atlas

Este documento explica como limpar todo o histórico de requisições do seu Atlas.

## 📋 O que será removido

- **Banco de dados SQLite**: Todas as conversas e mensagens armazenadas
- **Arquivos JSON**: Histórico de buscas na pasta `historico/`
- **Sessões Flask**: Arquivos de sessão ativa na pasta `flask_session/`
- **Cache Python**: Arquivos `__pycache__` e cache do ambiente virtual

## 🚀 Métodos de Limpeza

### 1. Script Interativo (Recomendado)

```bash
python limpar_historico.py
```

Este script:
- ✅ Mostra uma confirmação detalhada
- ✅ Exibe progresso da limpeza
- ✅ Fornece relatório completo
- ✅ É mais seguro (requer confirmação)

### 2. Script Rápido

```bash
python limpar_rapido.py --confirmar
```

Este script:
- ⚡ Execução mais rápida
- ⚠️ Requer flag `--confirmar` para executar
- 📝 Menos detalhado

### 3. Limpeza Manual

Se preferir fazer manualmente:

```bash
# Limpar arquivos JSON
rm historico/*.json

# Limpar banco de dados (via Python)
python -c "
import sqlite3
conn = sqlite3.connect('instance/atlas.db')
cursor = conn.cursor()
cursor.execute('DELETE FROM message')
cursor.execute('DELETE FROM conversation')
conn.commit()
conn.close()
print('Banco limpo!')
"

# Limpar sessões Flask
rm flask_session/*

# Limpar cache Python
rm -rf __pycache__ venv/__pycache__
```

## ⚠️ Avisos Importantes

1. **Irreversível**: A limpeza não pode ser desfeita
2. **Sessões Ativas**: Usuários logados serão desconectados
3. **Backup**: Considere fazer backup antes da limpeza

## 🔄 Após a Limpeza

Após executar a limpeza:

1. Reinicie o servidor Flask:
   ```bash
   python app.py
   ```

2. Acesse o Atlas - ele estará completamente limpo
3. Novas conversas serão criadas normalmente

## 🆘 Problemas Comuns

### Erro de Permissão
```bash
# No Windows (PowerShell como Administrador)
python limpar_historico.py

# No Linux/Mac
sudo python limpar_historico.py
```

### Banco de Dados Bloqueado
- Pare o servidor Flask primeiro
- Execute a limpeza
- Reinicie o servidor

### Arquivos Não Removidos
- Verifique se o servidor Flask está parado
- Execute o script como administrador
- Verifique permissões da pasta

## 📊 Verificação

Para verificar se a limpeza foi bem-sucedida:

```bash
# Verificar arquivos de histórico
ls historico/

# Verificar banco de dados
python -c "
import sqlite3
conn = sqlite3.connect('instance/atlas.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM conversation')
print(f'Conversas: {cursor.fetchone()[0]}')
cursor.execute('SELECT COUNT(*) FROM message')
print(f'Mensagens: {cursor.fetchone()[0]}')
conn.close()
"

# Verificar sessões Flask
ls flask_session/
```

## 🎯 Resultado Esperado

Após a limpeza bem-sucedida:
- ✅ Pasta `historico/` vazia ou sem arquivos `.json`
- ✅ Banco de dados com 0 conversas e 0 mensagens
- ✅ Pasta `flask_session/` vazia
- ✅ Cache Python removido

---

**💡 Dica**: Use o script interativo (`limpar_historico.py`) para maior segurança e controle sobre o processo.
