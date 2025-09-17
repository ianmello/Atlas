# 🔧 Configuração do Supabase - Guia Rápido

## 1. Criar Projeto no Supabase (2 minutos)

1. **Acesse:** https://supabase.com
2. **Clique em:** "Start your project" 
3. **Faça login** (GitHub, Google, ou email)
4. **Clique:** "New Project"
5. **Preencha:**
   - Nome: `Atlas` 
   - Database Password: `sua-senha-forte`
   - Region: `South America (São Paulo)` ou mais próxima
6. **Clique:** "Create new project"
7. **Aguarde:** ~2 minutos para criar

## 2. Executar o SQL (1 minuto)

1. **No dashboard do Supabase, clique:** "SQL Editor" (ícone de banco de dados na lateral)
2. **Clique:** "New query"
3. **Cole TODO o conteúdo do arquivo `supabase_schema.sql`**
4. **Clique:** "Run" (ou Ctrl/Cmd + Enter)
5. **Verifique:** Deve aparecer "Success. No rows returned" ou similar

## 3. Obter as Chaves (1 minuto)

1. **Clique:** "Settings" → "API" (ícone de engrenagem na lateral)
2. **Copie:**
   - `Project URL` (ex: https://abcdefgh.supabase.co)
   - `anon public` (chave longa que começa com eyJ...)
   - `service_role secret` (⚠️ CUIDADO - é secreta!)

## 4. Criar arquivo .env

Crie o arquivo `.env` na raiz do projeto com:

```env
# Supabase - SUBSTITUA pelos seus valores
SUPABASE_URL=https://SEU-PROJETO.supabase.co
SUPABASE_ANON_KEY=SUA-CHAVE-ANONIMA-AQUI
SUPABASE_SERVICE_ROLE_KEY=SUA-CHAVE-SERVICE-ROLE-AQUI

# APIs existentes - MANTENHA as que você já tem
GEMINI_API_KEY=sua-chave-gemini
AMADEUS_CLIENT_ID=seu-client-id
AMADEUS_CLIENT_SECRET=seu-client-secret
OPENWEATHER_API_KEY=sua-chave-openweather
SECRET_KEY=sua-chave-secreta-flask
```

## 5. Pronto! 🎉

Execute: `python app.py` e acesse http://localhost:8000

---

## 🆘 Se algo der errado:

### Erro: "Module supabase not found"
```bash
pip install supabase
```

### Erro: "SUPABASE_URL not found"
- Verifique se o arquivo `.env` está na raiz do projeto
- Verifique se as variáveis estão corretas (sem espaços extras)

### Erro: "Invalid JWT"
- Verifique se copiou as chaves corretas do Supabase
- A chave `anon public` deve começar com `eyJ...`

### Erro: "relation does not exist"
- Execute novamente o SQL no Supabase SQL Editor
- Verifique se todas as tabelas foram criadas: `conversations` e `messages`
