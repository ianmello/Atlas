-- Script SQL para criação das tabelas no Supabase
-- Execute este script no SQL Editor do Supabase

-- Tabela de conversas
CREATE TABLE conversations (
  id BIGSERIAL PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  title VARCHAR(200) NOT NULL,
  origin VARCHAR(100),
  destination VARCHAR(100),
  start_date DATE,
  end_date DATE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabela de mensagens
CREATE TABLE messages (
  id BIGSERIAL PRIMARY KEY,
  conversation_id BIGINT REFERENCES conversations(id) ON DELETE CASCADE,
  content TEXT NOT NULL,
  is_bot BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para performance
CREATE INDEX idx_conversations_user_id ON conversations(user_id);
CREATE INDEX idx_conversations_created_at ON conversations(created_at DESC);
CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_messages_created_at ON messages(created_at DESC);

-- Habilitar RLS (Row Level Security)
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

-- Políticas de segurança para conversations
CREATE POLICY "Users can view own conversations" ON conversations
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own conversations" ON conversations
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own conversations" ON conversations
  FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own conversations" ON conversations
  FOR DELETE USING (auth.uid() = user_id);

-- Políticas de segurança para messages
CREATE POLICY "Users can view messages from own conversations" ON messages
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM conversations 
      WHERE conversations.id = messages.conversation_id 
      AND conversations.user_id = auth.uid()
    )
  );

CREATE POLICY "Users can insert messages to own conversations" ON messages
  FOR INSERT WITH CHECK (
    EXISTS (
      SELECT 1 FROM conversations 
      WHERE conversations.id = messages.conversation_id 
      AND conversations.user_id = auth.uid()
    )
  );

-- Trigger para atualizar updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_conversations_updated_at 
  BEFORE UPDATE ON conversations 
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Comentários nas tabelas
COMMENT ON TABLE conversations IS 'Armazena as conversas de planejamento de viagem dos usuários';
COMMENT ON TABLE messages IS 'Armazena as mensagens do chat entre usuário e bot';

-- Comentários nas colunas
COMMENT ON COLUMN conversations.user_id IS 'ID do usuário autenticado (referência ao auth.users)';
COMMENT ON COLUMN conversations.title IS 'Título gerado automaticamente baseado na consulta';
COMMENT ON COLUMN conversations.origin IS 'Cidade/país de origem da viagem';
COMMENT ON COLUMN conversations.destination IS 'Cidade/país de destino da viagem';
COMMENT ON COLUMN conversations.start_date IS 'Data de início da viagem';
COMMENT ON COLUMN conversations.end_date IS 'Data de fim da viagem (opcional)';

COMMENT ON COLUMN messages.conversation_id IS 'Referência à conversa pai';
COMMENT ON COLUMN messages.content IS 'Conteúdo da mensagem (texto ou HTML formatado)';
COMMENT ON COLUMN messages.is_bot IS 'Indica se a mensagem foi enviada pelo bot (true) ou usuário (false)';

-- Inserir dados de exemplo (opcional - remover em produção)
-- INSERT INTO conversations (user_id, title, origin, destination, start_date, end_date) 
-- VALUES (auth.uid(), 'Roteiro para Paris (5 dias)', 'São Paulo', 'Paris', '2024-06-01', '2024-06-05');

-- Verificar se tudo foi criado corretamente
SELECT 
  schemaname,
  tablename,
  tableowner
FROM pg_tables 
WHERE tablename IN ('conversations', 'messages');

-- Verificar políticas RLS
SELECT 
  schemaname,
  tablename,
  policyname,
  permissive,
  roles,
  cmd,
  qual
FROM pg_policies 
WHERE tablename IN ('conversations', 'messages');
