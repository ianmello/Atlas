"""
Modelos de dados para Supabase - Atlas
"""
from datetime import datetime, date
from typing import List, Dict, Optional, Any
from config.supabase_config import supabase
import uuid

class SupabaseModel:
    """Classe base para modelos Supabase"""
    
    @classmethod
    def create(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Criar novo registro"""
        try:
            result = supabase.table(cls.table_name).insert(data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Erro ao criar {cls.table_name}: {e}")
            raise
    
    @classmethod
    def get_by_id(cls, id: int) -> Optional[Dict[str, Any]]:
        """Buscar por ID"""
        try:
            result = supabase.table(cls.table_name).select("*").eq("id", id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Erro ao buscar {cls.table_name} por ID: {e}")
            return None
    
    @classmethod
    def update(cls, id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Atualizar registro"""
        try:
            result = supabase.table(cls.table_name).update(data).eq("id", id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Erro ao atualizar {cls.table_name}: {e}")
            raise
    
    @classmethod
    def delete(cls, id: int) -> bool:
        """Deletar registro"""
        try:
            supabase.table(cls.table_name).delete().eq("id", id).execute()
            return True
        except Exception as e:
            print(f"Erro ao deletar {cls.table_name}: {e}")
            return False

class User:
    """Modelo para usuários (usa auth.users do Supabase)"""
    
    @staticmethod
    def get_current_user():
        """Obtém usuário atual autenticado"""
        try:
            user = supabase.auth.get_user()
            return user.user if user else None
        except Exception as e:
            print(f"Erro ao obter usuário atual: {e}")
            return None
    
    @staticmethod
    def sign_up(email: str, password: str, full_name: str = None):
        """Cadastrar novo usuário"""
        try:
            user_data = {"email": email, "password": password}
            if full_name:
                user_data["options"] = {"data": {"full_name": full_name}}
            
            result = supabase.auth.sign_up(user_data)
            return result
        except Exception as e:
            print(f"Erro ao cadastrar usuário: {e}")
            raise
    
    @staticmethod
    def sign_in(email: str, password: str):
        """Login do usuário"""
        try:
            result = supabase.auth.sign_in_with_password({"email": email, "password": password})
            return result
        except Exception as e:
            print(f"Erro ao fazer login: {e}")
            raise
    
    @staticmethod
    def sign_out():
        """Logout do usuário"""
        try:
            supabase.auth.sign_out()
            return True
        except Exception as e:
            print(f"Erro ao fazer logout: {e}")
            return False

class Conversation(SupabaseModel):
    """Modelo para conversas"""
    table_name = "conversations"
    
    @classmethod
    def create_conversation(cls, user_id: str, title: str, origin: str = None, 
                          destination: str = None, start_date: date = None, 
                          end_date: date = None) -> Optional[Dict[str, Any]]:
        """Criar nova conversa"""
        data = {
            "user_id": user_id,
            "title": title,
            "origin": origin,
            "destination": destination,
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None
        }
        return cls.create(data)
    
    @classmethod
    def get_user_conversations(cls, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Buscar conversas do usuário"""
        try:
            result = supabase.table(cls.table_name)\
                .select("*")\
                .eq("user_id", user_id)\
                .order("created_at", desc=True)\
                .limit(limit)\
                .execute()
            return result.data
        except Exception as e:
            print(f"Erro ao buscar conversas do usuário: {e}")
            return []
    
    @classmethod
    def get_conversation_with_messages(cls, conversation_id: int, user_id: str) -> Optional[Dict[str, Any]]:
        """Buscar conversa com mensagens"""
        try:
            # Buscar conversa
            conversation = supabase.table(cls.table_name)\
                .select("*")\
                .eq("id", conversation_id)\
                .eq("user_id", user_id)\
                .execute()
            
            if not conversation.data:
                return None
            
            conv_data = conversation.data[0]
            
            # Buscar mensagens
            messages = Message.get_conversation_messages(conversation_id)
            conv_data["messages"] = messages
            
            return conv_data
        except Exception as e:
            print(f"Erro ao buscar conversa com mensagens: {e}")
            return None

class Message(SupabaseModel):
    """Modelo para mensagens"""
    table_name = "messages"
    
    @classmethod
    def create_message(cls, conversation_id: int, content: str, is_bot: bool = False) -> Optional[Dict[str, Any]]:
        """Criar nova mensagem"""
        data = {
            "conversation_id": conversation_id,
            "content": content,
            "is_bot": is_bot
        }
        return cls.create(data)
    
    @classmethod
    def get_conversation_messages(cls, conversation_id: int) -> List[Dict[str, Any]]:
        """Buscar mensagens de uma conversa"""
        try:
            result = supabase.table(cls.table_name)\
                .select("*")\
                .eq("conversation_id", conversation_id)\
                .order("created_at", desc=False)\
                .execute()
            return result.data
        except Exception as e:
            print(f"Erro ao buscar mensagens da conversa: {e}")
            return []

def generate_conversation_title(message: str) -> str:
    """Gera um título apropriado baseado na mensagem do usuário"""
    message = message.lower()
    
    # Identificar destino
    from app import extrair_destino
    destino = extrair_destino(message)
    if destino == "Destino não informado":
        # Tenta identificar destino de outras formas
        destinations = [
            'frança', 'eua', 'estados unidos', 'paris', 'nova york', 'rio de janeiro', 
            'são paulo', 'portugal', 'espanha', 'itália', 'alemanha', 'japão', 'china'
        ]
        for dest in destinations:
            if dest in message:
                destino = dest
                break
        
        if destino == "Destino não informado":
            # Tenta extrair destino após palavras comuns
            common_prefixes = ['para', 'em', 'sobre', 'na', 'no', 'conhecer', 'visitar']
            for prefix in common_prefixes:
                if prefix + ' ' in message:
                    destino = message.split(prefix + ' ')[1].split()[0:3]
                    destino = ' '.join(destino)
                    break
    
    # Formata o destino
    if destino and destino != "Destino não informado":
        destino = destino.title()
    else:
        destino = "Destino não especificado"
    
    # Montar o título
    title = f"Roteiro para {destino}"
    
    # Adicionar duração se mencionada
    duration_words = ['dias', 'semanas', 'meses']
    for word in duration_words:
        if word in message:
            try:
                duration = message.split(word)[0].split()[-1]
                if duration.isdigit():
                    title += f" ({duration} {word})"
            except:
                pass
    
    return title
