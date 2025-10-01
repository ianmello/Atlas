"""
Configuração do Supabase para o projeto Atlas
"""
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Configurações do Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

def get_supabase_client() -> Client:
    """
    Retorna cliente Supabase configurado
    """
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise ValueError("Variáveis SUPABASE_URL e SUPABASE_ANON_KEY são obrigatórias")
    
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

def get_supabase_admin_client() -> Client:
    """
    Retorna cliente Supabase com privilégios administrativos
    """
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise ValueError("Variáveis SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY são obrigatórias")
    
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# Cliente global
supabase: Client = get_supabase_client()
