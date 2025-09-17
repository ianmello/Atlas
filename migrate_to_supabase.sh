#!/bin/bash

echo "🚀 Iniciando migração para Supabase..."

# 1. Fazer backup dos arquivos atuais
echo "📦 Fazendo backup dos arquivos atuais..."
if [ -f "app.py" ]; then
    mv app.py app_sqlite_backup.py
    echo "✅ app.py -> app_sqlite_backup.py"
fi

if [ -f "models.py" ]; then
    mv models.py models_sqlite_backup.py
    echo "✅ models.py -> models_sqlite_backup.py"
fi

# 2. Renomear arquivos do Supabase
echo "🔄 Ativando arquivos do Supabase..."
if [ -f "app_supabase.py" ]; then
    mv app_supabase.py app.py
    echo "✅ app_supabase.py -> app.py"
fi

if [ -f "models_supabase.py" ]; then
    mv models_supabase.py models.py
    echo "✅ models_supabase.py -> models.py"
fi

# 3. Instalar dependências
echo "📦 Instalando dependências do Supabase..."
pip install supabase

# 4. Verificar se .env existe
if [ ! -f ".env" ]; then
    echo "⚠️  ATENÇÃO: Arquivo .env não encontrado!"
    echo "📝 Crie o arquivo .env com as configurações do Supabase"
    echo "📋 Use o arquivo .env.example como referência"
else
    echo "✅ Arquivo .env encontrado"
fi

echo ""
echo "🎉 Migração concluída!"
echo ""
echo "📋 PRÓXIMOS PASSOS:"
echo "1. Configure seu projeto no Supabase (https://supabase.com)"
echo "2. Execute o SQL do arquivo supabase_schema.sql no SQL Editor"
echo "3. Configure as variáveis no arquivo .env"
echo "4. Execute: python app.py"
echo "5. Acesse: http://localhost:8000"
echo ""
echo "🔍 TESTE:"
echo "- Cadastro de usuário"
echo "- Login"
echo "- Criação de roteiro"
echo "- Histórico"
echo ""
