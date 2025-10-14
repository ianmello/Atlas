from flask import Flask, request, jsonify, render_template, session, redirect, url_for, send_from_directory
from flask_cors import CORS
import datetime
import requests
import os
import json
from dotenv import load_dotenv
import warnings
import re
from geopy.distance import geodesic
from flask_session import Session
import uuid
from datetime import timedelta, datetime, date
from functools import wraps

# Importações do Supabase
from config.supabase_config import supabase
from models_supabase import User, Conversation, Message, generate_conversation_title

app = Flask(__name__)
CORS(app)
app.config["SESSION_PERMANENT"] = True
app.config["SESSION_TYPE"] = "filesystem"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)
app.secret_key = os.getenv("SECRET_KEY", "chave_secreta_temporaria")

Session(app)

warnings.filterwarnings("ignore")
load_dotenv()

# APIs URLs (mantém as mesmas)
EXCHANGE_API_URL = "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoMoedaDia(moeda=@moeda,dataCotacao=@dataCotacao)"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
FLIGHT_API_URL = "https://test.api.amadeus.com/v2/shopping/flight-offers"
HOTEL_API_URL = "https://test.api.amadeus.com/v1/reference-data/locations/hotels/by-city"
WEATHER_API_URL = "https://api.openweathermap.org/data/2.5/forecast"
WEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

chat_context = {}

# Mantém todos os dados de cidades e códigos IATA (copiando do app.py original)
CITY_COORDINATES = {
    "sao paulo": (-23.5505, -46.6333),
    "campinas": (-22.9099, -47.0626),
    "rio de janeiro": (-22.9068, -43.1729),
    "curitiba": (-25.4284, -49.2733),
    "belo horizonte": (-19.9167, -43.9345),
    "brasilia": (-15.7801, -47.9292),
    "salvador": (-12.9716, -38.5016),
    "recife": (-8.0476, -34.8770),
    "fortaleza": (-3.7319, -38.5267),
    "porto alegre": (-30.0277, -51.2287)
}

CITY_IATA_CODES = {
    "sao paulo": "GRU",
    "são paulo": "GRU",
    "campinas": "VCP",
    "rio de janeiro": "GIG",
    "curitiba": "CWB",
    "belo horizonte": "CNF",
    "brasilia": "BSB",
    "brasília": "BSB",
    "salvador": "SSA",
    "recife": "REC",
    "fortaleza": "FOR",
    "porto alegre": "POA",
    "manaus": "MAO",
    "natal": "NAT",
    "florianopolis": "FLN",
    "florianópolis": "FLN",
    "goiania": "GYN",
    "goiânia": "GYN",
    # Adicionando cidades internacionais comuns
    "nova york": "JFK",
    "new york": "JFK",
    "paris": "CDG",
    "londres": "LHR",
    "london": "LHR",
    "roma": "FCO",
    "rome": "FCO",
    "tokyo": "HND",
    "tóquio": "HND",
    "madrid": "MAD",
    "barcelona": "BCN",
    "berlim": "BER",
    "berlin": "BER",
    "lisboa": "LIS",
    "lisbon": "LIS",
    "miami": "MIA",
    "orlando": "MCO",
    "los angeles": "LAX",
    "toronto": "YYZ",
    "mexico": "MEX",
    "mexico city": "MEX",
    "cidade do méxico": "MEX",
    "buenos aires": "EZE",
    "santiago": "SCL",
    "lima": "LIM",
    "bogota": "BOG",
    "bogotá": "BOG",
    # Códigos IATA adicionais de países/cidades famosas
    # Europa
    "frança": "CDG", # Paris
    "espanha": "MAD", # Madrid
    "itália": "FCO", # Roma
    "alemanha": "FRA", # Frankfurt
    "reino unido": "LHR", # Londres
    "turquia": "IST", # Istambul
    "grécia": "ATH", # Atenas
    "países baixos": "AMS", # Amsterdã
    "áustria": "VIE", # Viena
    "dublin": "DUB", # Irlanda
    "zurique": "ZRH", # Suíça
    "bruxelas": "BRU", # Bélgica
    "copenhague": "CPH", # Dinamarca
    "estocolmo": "ARN", # Suécia
    "oslo": "OSL", # Noruega
    "helsinque": "HEL", # Finlândia
    "praga": "PRG", # República Tcheca
    "budapeste": "BUD", # Hungria
    "varsóvia": "WAW", # Polônia
    "moscou": "SVO", # Rússia
    # Ásia
    "tailândia": "BKK", # Bangkok
    "japão": "HND", # Tóquio
    "china": "PEK", # Pequim
    "malásia": "KUL", # Kuala Lumpur
    "índia": "DEL", # Nova Deli
    "indonésia": "CGK", # Jacarta
    "vietnã": "SGN", # Ho Chi Minh
    "coreia do sul": "ICN", # Seul
    "singapura": "SIN", # Singapura
    "emirados árabes unidos": "DXB", # Dubai
    "hong kong": "HKG",
    "xangai": "PVG",
    "pequim": "PEK",
    "seul": "ICN",
    "deli": "DEL",
    "bangkok": "BKK",
    "kuala lumpur": "KUL",
    "jacarta": "CGK",
    "saigon": "SGN",
    "ho chi minh": "SGN",
    "manila": "MNL",
    "taipei": "TPE",
    "abu dhabi": "AUH",
    "doha": "DOH",
    # África
    "áfrica do sul": "JNB", # Joanesburgo
    "egito": "CAI", # Cairo
    "marrocos": "CMN", # Casablanca
    "quênia": "NBO", # Nairobi
    "nigéria": "LOS", # Lagos
    # América do Sul (mais algumas)
    "colômbia": "BOG", # Bogotá
    "peru": "LIM", # Lima
    "argentina": "EZE", # Buenos Aires
    "chile": "SCL", # Santiago
    "uruguai": "MVD", # Montevidéu
    "paraguai": "ASU", # Assunção
    "equador": "UIO", # Quito
    "venezuela": "CCS", # Caracas
    # América do Norte (mais algumas)
    "méxico": "MEX", # Cidade do México
    "canadá": "YYZ", # Toronto
    "estados unidos": "JFK", # Nova York
    "vancouver": "YVR",
    "montreal": "YUL",
    "chicago": "ORD",
    "são francisco": "SFO",
    "seattle": "SEA",
    # Oceania
    "austrália": "SYD", # Sydney
    "nova zelândia": "AKL", # Auckland
    "sydney": "SYD",
    "melbourne": "MEL",
    "auckland": "AKL"
}

PALAVRAS_DESCARTAR = [
    "para", "até", "e", "com", "por", "durante", "no", "na", "do", "da", "dos", "das", 
    "de", "em", "ao", "aos", "às", "as", "os", "o", "a", "um", "uma", "uns", "umas"
]

# Decorator para autenticação
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = User.get_current_user()
        if not user:
            if request.is_json:
                return jsonify({"error": "Autenticação necessária"}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user_id():
    """Obtém ID do usuário atual"""
    user = User.get_current_user()
    return user.id if user else None

# Mantém todas as funções auxiliares do app.py original
def limpar_nome_cidade(texto):
    palavras = texto.strip().split()
    resultado = []
    for palavra in palavras:
        if palavra.lower() not in PALAVRAS_DESCARTAR:
            resultado.append(palavra)
        else:
            break
    return " ".join(resultado)

def get_exchange_rate(currency: str = "USD") -> float:
    try:
        today = datetime.now().strftime("%m-%d-%Y")
        params = {
            "@moeda": f"'{currency}'",
            "@dataCotacao": f"'{today}'",
            "$format": "json"
        }
        response = requests.get(EXCHANGE_API_URL, params=params, timeout=10)
        if response.status_code != 200:
            return 5.0
        data = response.json()
        if 'value' in data and len(data['value']) > 0:
            return float(data['value'][0]['cotacaoVenda'])
        else:
            return 5.0
    except:
        return 5.0

# Mantém todas as outras funções do app.py original (get_ai_response, format_flights_response, etc.)
# Por brevidade, vou incluir apenas as principais e indicar onde copiar o resto

def get_ai_response(messages, origem=None, destino=None, datas=None):
    try:
        print(f"[DEBUG] get_ai_response chamada com {len(messages)} mensagens")
        last_message = messages[-1]["content"].lower()
        print(f"[DEBUG] Última mensagem: {last_message[:100]}...")
        
        # Se origem e destino não foram fornecidos, tenta extrair da mensagem
        if not origem:
            origem = extrair_origem(last_message)
        if not destino:
            destino = extrair_destino(last_message)
        if not datas:
            datas = extrair_datas(last_message)
        
        print(f"[DEBUG] Origem extraída: {origem}")
        print(f"[DEBUG] Destino extraído: {destino}")
        print(f"[DEBUG] Datas extraídas: {datas}")

        roteiro = ""
        # Sempre gera um roteiro com Gemini primeiro
        headers = {"Content-Type": "application/json"}
        if GEMINI_API_KEY:
            url = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"
            
            # Adiciona instruções específicas para formatação
            system_prompt = """Você é um assistente de viagens especializado. 
            IMPORTANTE: Sempre formate suas respostas com quebras de linha adequadas:
            - Use ## para títulos principais
            - Use ** para subtítulos
            - Use * para itens de lista
            - Separe parágrafos com linhas em branco
            - Use formatação markdown para melhor legibilidade
            
            Exemplo de formatação:
            ## Roteiro de 3 Dias em Paris
            
            **Dia 1: Chegada e Centro Histórico**
            * Manhã: Check-in no hotel
            * Tarde: Visita à Torre Eiffel
            * Noite: Jantar no Marais
            
            **Dia 2: Museus e Arte**
            * Manhã: Louvre
            * Tarde: Museu d'Orsay
            * Noite: Passeio pelo Sena
            
            **Considerações Importantes**
            * Transporte: Metrô eficiente
            * Ingressos: Comprar com antecedência
            * Hospedagem: Centro da cidade recomendado"""
            
            # Prepara as mensagens do usuário
            user_messages = [{"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["content"]}]} for m in messages]
            
            # Adiciona o system prompt como contexto na primeira mensagem do usuário
            if user_messages and user_messages[0]["role"] == "user":
                first_user_message = user_messages[0]["parts"][0]["text"]
                user_messages[0]["parts"][0]["text"] = f"{system_prompt}\n\n{first_user_message}"
            
            # Prepara os dados para a API
            data = {
                "contents": user_messages,
                "generationConfig": {
                    "temperature": 0.7,
                    "topK": 40,
                    "topP": 0.95,
                    "maxOutputTokens": 3072,  # Aumentei para roteiros mais completos
                }
            }
            
            print(f"[DEBUG] Enviando requisição para Gemini API...")
            try:
                response = requests.post(url, headers=headers, data=json.dumps(data), timeout=30)
                print(f"[DEBUG] Resposta da API Gemini: {response.status_code}")
                
                if response.status_code == 200:
                    resposta = response.json()
                    try:
                        roteiro = resposta["candidates"][0]["content"]["parts"][0]["text"]
                        print(f"[DEBUG] Resposta do Gemini recebida com sucesso. Tamanho: {len(roteiro)} caracteres")
                        print(f"[DEBUG] Primeiros 200 caracteres: {roteiro[:200]}...")
                    except Exception as e:
                        print(f"[ERROR] Erro ao processar resposta do Gemini: {e}")
                        print(f"[DEBUG] Resposta completa: {resposta}")
                        roteiro = "Desculpe, não consegui gerar um roteiro agora."
                else:
                    print(f"[ERROR] Erro na API Gemini: {response.status_code} - {response.text}")
                    roteiro = "Desculpe, não consegui gerar um roteiro agora."
            except requests.exceptions.Timeout:
                print("[ERROR] Timeout na API Gemini")
                roteiro = "Desculpe, a API demorou muito para responder. Por favor, tente novamente."
            except Exception as e:
                print(f"[ERROR] Erro inesperado na API Gemini: {e}")
                roteiro = "Desculpe, ocorreu um erro inesperado. Por favor, tente novamente."
        else:
            print("[ERROR] Chave da API Gemini não configurada")
            roteiro = "Desculpe, a chave da API Gemini não está configurada."

        # Se tem origem e destino válidos, busca voos e adiciona ao roteiro
        if origem != "Origem não informada" and destino != "Destino não informado":
            print(f"[DEBUG] Buscando voos para {origem} -> {destino}")
            try:
                origem_iata = buscar_codigo_iata(origem)
                destino_iata = buscar_codigo_iata(destino)
                
                print(f"[DEBUG] Códigos IATA: {origem_iata} -> {destino_iata}")
                
                if origem_iata and destino_iata:
                    voos = get_flights(origem_iata, destino_iata, datas.get('data_inicio') if datas else None)
                    
                    if voos and 'data' in voos and voos['data']:
                        try:
                            voos_html = format_flights_response(voos['data'])
                            # Adiciona separação adequada entre roteiro e voos
                            if roteiro.strip():
                                roteiro += "\n\n---\n\n" + voos_html
                            else:
                                roteiro = voos_html
                            print(f"[DEBUG] Voos adicionados ao roteiro")
                        except Exception as voo_error:
                            print(f"[ERROR] Erro ao formatar voos: {voo_error}")
                            roteiro += "\n\n---\n\n⚠️ Encontrei voos disponíveis, mas houve um erro ao exibir as informações detalhadas."
                    elif voos and 'error' in voos:
                        print(f"[WARN] Erro na busca de voos: {voos['error']}")
                        roteiro += "\n\n---\n\n⚠️ Não foi possível buscar informações de voos no momento."
                    else:
                        print(f"[DEBUG] Nenhum voo encontrado")
                        roteiro += "\n\n---\n\n✈️ Não encontrei voos disponíveis para esta rota na data especificada."
                else:
                    print(f"[WARN] Códigos IATA não encontrados")
                    roteiro += "\n\n---\n\n⚠️ Não consegui identificar os códigos dos aeroportos para buscar voos."
            except Exception as voo_error:
                print(f"[ERROR] Erro ao buscar voos: {voo_error}")
                roteiro += "\n\n---\n\n⚠️ Houve um erro ao buscar informações de voos."

        print(f"[DEBUG] Roteiro final gerado. Tamanho: {len(roteiro)} caracteres")
        return roteiro

    except Exception as e:
        print(f"[ERROR] Erro geral em get_ai_response: {str(e)}")
        import traceback
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        return "Desculpe, ocorreu um erro ao processar sua mensagem. Por favor, tente novamente."

# Copia todas as outras funções auxiliares do app.py original
def extrair_destino(texto: str) -> str:
    # Copia a função completa do app.py
    try:
        padroes = [
            r'(?:roteiro|viagem|viajar|ir)\s+para\s+([A-Za-zÀ-ÿ\s]+?)(?:\s+saindo|\s+partindo|\s+no dia|\s+em|\s+com|\s+por|\s+durante|\s*$|,)',
            r'(?:roteiro|viagem|viajar)\s+(?:em|no|na|para)\s+([A-Za-zÀ-ÿ\s]+?)(?:\s+saindo|\s+partindo|\s+no dia|\s+em|\s+com|\s+por|\s+durante|\s*$|,)',
            r'conhecer\s+([A-Za-zÀ-ÿ\s]+?)(?:\s+saindo|\s+partindo|\s+no dia|\s+em|\s+com|\s+por|\s+durante|\s*$|,)',
            r'visitar\s+([A-Za-zÀ-ÿ\s]+?)(?:\s+saindo|\s+partindo|\s+no dia|\s+em|\s+com|\s+por|\s+durante|\s*$|,)',
            r'para\s+([A-Za-zÀ-ÿ\s]+?)\s+saindo\s+de',
            r'de\s+[A-Za-zÀ-ÿ\s]+?\s+para\s+([A-Za-zÀ-ÿ\s]+?)(?:\s+no dia|\s+em|\s+com|\s+por|\s+durante|\s*$|,)'
        ]
        
        palavras_invalidas = ['casal', 'familia', 'amigos', 'sozinho', 'grupo', 'dias', 'semanas', 'meses', 'voos', 'roteiro', 'viagem']
        
        for padrao in padroes:
            match = re.search(padrao, texto, re.IGNORECASE)
            if match:
                destino = match.group(1).strip()
                if destino.lower() not in palavras_invalidas:
                    return destino
                    
        return "Destino não informado"
    except Exception as e:
        return "Destino não informado"

def extrair_origem(texto: str) -> str:
    # Copia a função completa do app.py
    try:
        padroes = [
            r'saindo de\s+([A-Za-zÀ-ÿ\s]+?)(?:\s+para|\s+no dia|\s+em|\s+e|\s+com|\s+por|\s+durante|\s*$|,)',
            r'partindo de\s+([A-Za-zÀ-ÿ\s]+?)(?:\s+para|\s+no dia|\s+em|\s+e|\s+com|\s+por|\s+durante|\s*$|,)',
            r'desde\s+([A-Za-zÀ-ÿ\s]+?)(?:\s+para|\s+no dia|\s+em|\s+e|\s+com|\s+por|\s+durante|\s*$|,)',
            r'de\s+([A-Za-zÀ-ÿ\s]+?)\s+(?:para|até|no dia)',
            r'de\s+([A-Za-zÀ-ÿ\s]+?)\s+para\s+[A-Za-zÀ-ÿ\s]+'
        ]
        
        palavras_invalidas = ['casal', 'familia', 'amigos', 'sozinho', 'grupo', 'dias', 'semanas', 'meses', 'voos', 'roteiro', 'viagem']
        
        for padrao in padroes:
            match = re.search(padrao, texto, re.IGNORECASE)
            if match:
                origem = limpar_nome_cidade(match.group(1))
                if origem.lower() not in palavras_invalidas:
                    return origem
                    
        return "Origem não informada"
    except Exception as e:
        return "Origem não informada"

def extrair_datas(texto: str):
    # Copia a função completa do app.py
    meses = {
        'janeiro': '01', 'jan': '01', 
        'fevereiro': '02', 'fev': '02',
        'março': '03', 'mar': '03',
        'abril': '04', 'abr': '04',
        'maio': '05', 'mai': '05',
        'junho': '06', 'jun': '06',
        'julho': '07', 'jul': '07',
        'agosto': '08', 'ago': '08',
        'setembro': '09', 'set': '09',
        'outubro': '10', 'out': '10',
        'novembro': '11', 'nov': '11',
        'dezembro': '12', 'dez': '12'
    }
    
    resultado = {"data_inicio": None, "data_fim": None}
    
    if not resultado["data_inicio"]:
        padrao_duracao = r'(\d+)\s+dias?'
        match_duracao = re.search(padrao_duracao, texto, re.IGNORECASE)
        
        if match_duracao:
            dias = int(match_duracao.group(1))
            hoje = datetime.now()
            data_inicio = hoje + timedelta(days=7)
            data_fim = data_inicio + timedelta(days=dias)
            
            resultado["data_inicio"] = data_inicio.strftime("%Y-%m-%d")
            resultado["data_fim"] = data_fim.strftime("%Y-%m-%d")
            resultado["duracao"] = dias
    
    return resultado

# Copia as outras funções auxiliares (buscar_codigo_iata, get_flights, format_flights_response, etc.)
def buscar_codigo_iata(nome_destino: str) -> str:
    try:
        nome_normalizado = nome_destino.lower().strip()
        
        if nome_normalizado in CITY_IATA_CODES:
            return CITY_IATA_CODES[nome_normalizado]
        
        for cidade, codigo in CITY_IATA_CODES.items():
            if nome_normalizado in cidade or cidade in nome_normalizado:
                return codigo
                
        return nome_destino[:3].upper()
    except Exception as e:
        return nome_destino[:3].upper()

def get_flights(origin: str, destination: str, date: str):
    # Copia a função completa do app.py
    try:
        client_id = os.getenv("AMADEUS_CLIENT_ID")
        client_secret = os.getenv("AMADEUS_CLIENT_SECRET")
        
        if not client_id or not client_secret:
            return {"data": [], "error": "Credenciais da API não configuradas"}
        
        if not origin or not destination:
            return {"data": [], "error": "Códigos IATA inválidos"}
            
        origin = origin.strip().upper()
        destination = destination.strip().upper()
        
        if len(origin) != 3 or len(destination) != 3:
            return {"data": [], "error": "Formato de código IATA inválido"}
            
        try:
            parsed_date = datetime.strptime(date, "%Y-%m-%d")
            if parsed_date.date() < datetime.now().date():
                data_atual = datetime.now() + timedelta(days=7)
                date = data_atual.strftime("%Y-%m-%d")
        except ValueError:
            data_atual = datetime.now() + timedelta(days=7)
            date = data_atual.strftime("%Y-%m-%d")
        
        # Autenticação na API
        auth_url = "https://test.api.amadeus.com/v1/security/oauth2/token"
        auth_data = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret
        }
        
        try:
            auth_response = requests.post(auth_url, data=auth_data, verify=False, timeout=10)
            auth_response.raise_for_status()
        except requests.exceptions.RequestException as e:
            return {"data": [], "error": "Erro de autenticação na API"}
            
        if auth_response.status_code != 200:
            return {"data": [], "error": "Erro de autenticação na API"}
            
        token = auth_response.json().get("access_token")
        if not token:
            return {"data": [], "error": "Token de acesso não encontrado"}

        # Busca de voos
        params = {
            "originLocationCode": origin,
            "destinationLocationCode": destination,
            "departureDate": date,
            "adults": 1,
            "max": 5,
            "currencyCode": "USD"
        }
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }
        
        try:
            response = requests.get(FLIGHT_API_URL, headers=headers, params=params, verify=False, timeout=15)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            return {"data": [], "error": "Erro na busca de voos"}
        
        if response.status_code != 200:
            return {"data": [], "error": "Erro na API de voos"}
            
        result = response.json()
        
        # Formata os preços antes de retornar
        if "data" in result:
            for voo in result["data"]:
                if "price" in voo:
                    voo["price"]["formatted"] = format_price(voo["price"])
        
        return result
    except Exception as e:
        return {"data": [], "error": str(e)}

def format_price(price_data):
    try:
        if not price_data or not isinstance(price_data, dict):
            return "Preço não disponível"
            
        total = price_data.get("total")
        if not total:
            return "Preço não disponível"
            
        if isinstance(total, str):
            try:
                total = float(total)
            except ValueError:
                return "Preço não disponível"
        
        if total <= 0:
            return "Preço não disponível"
        
        try:
            cotacao_dolar = get_exchange_rate("USD")
            if cotacao_dolar <= 0:
                cotacao_dolar = 5.0  # Valor padrão caso falhe
                
            preco_brl = float(total) * cotacao_dolar
            
            if preco_brl <= 0 or not isinstance(preco_brl, (int, float)) or not (preco_brl < 1000000):
                return "Preço não disponível"
            
            valor_formatado = f"R$ {preco_brl:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            return valor_formatado
        except Exception as e:
            print(f"[ERROR] Erro ao formatar preço: {e}")
            return "Preço não disponível"
    except Exception as e:
        print(f"[ERROR] Erro geral ao formatar preço: {e}")
        return "Preço não disponível"

from dateutil import parser

def format_flights_response(flights):
    """Formata a resposta dos voos em cards HTML horizontais e compactos"""
    try:
        if not isinstance(flights, (list, tuple)):
            return "Erro ao processar dados dos voos. Por favor, tente novamente."
        
        if not flights:
            return "Desculpe, não encontrei voos disponíveis para esta rota."
        
        response = '<div class="flights-section">'
        response += '<h3 style="color: #4285f4; margin-bottom: 15px; font-size: 1.2rem; font-weight: 600;">✈️ Voos Disponíveis</h3>'
        response += '<div class="flights-grid">'
        
        for i, flight in enumerate(flights, 1):
            try:
                if not isinstance(flight, dict):
                    continue
                if 'itineraries' not in flight or not flight['itineraries']:
                    continue
                
                segments = flight['itineraries'][0].get('segments', [])
                if not segments:
                    continue
                
                price_data = flight.get('price', {})
                if not price_data:
                    continue
                
                price_formatted = format_price(price_data)
                
                first_segment = segments[0]
                last_segment = segments[-1]
                
                if not first_segment.get('departure') or not last_segment.get('arrival'):
                    continue
                
                # Parse robusto com dateutil
                try:
                    departure_str = first_segment['departure']['at']
                    arrival_str = last_segment['arrival']['at']
                    
                    first_departure = parser.parse(departure_str)
                    last_arrival = parser.parse(arrival_str)
                    
                    duration = last_arrival - first_departure
                    duration_hours = duration.total_seconds() // 3600
                    duration_minutes = (duration.total_seconds() % 3600) // 60
                    duration_str = f"{int(duration_hours)}h {int(duration_minutes)}m"
                except Exception as e:
                    print(f"[ERROR] Falha ao parsear datas do voo: {e}")
                    duration_str = "Duração não disponível"
                    first_departure = None
                    last_arrival = None
                
                is_direct = len(segments) == 1
                connections = max(len(segments) - 1, 0)
                connection_text = (
                    "Direto" if is_direct
                    else (f"{connections} conexão" if connections == 1 else f"{connections} conexões")
                )
                
                airline_code = first_segment.get('carrierCode', 'N/A')
                departure_iata = first_segment['departure'].get('iataCode', 'N/A')
                arrival_iata = last_segment['arrival'].get('iataCode', 'N/A')
                
                # Formatar horários com datas para evitar confusão em voos noturnos
                departure_time = first_departure.strftime('%d/%m %H:%M') if first_departure else 'N/A'
                arrival_time = last_arrival.strftime('%d/%m %H:%M') if last_arrival else 'N/A'
                
                response += f'''
                <div class="flight-card">
                    <div class="flight-header">
                        <div class="price-badge">{price_formatted}</div>
                        <div class="flight-number">Voo {i}</div>
                    </div>
                    <div class="flight-main">
                        <div class="flight-route-horizontal">
                            <div class="route-info">
                                <div class="time-large">{departure_time}</div>
                                <div class="airport-code">{departure_iata}</div>
                            </div>
                            <div class="route-arrow">
                                <i class="fas fa-plane"></i>
                            </div>
                            <div class="route-info">
                                <div class="time-large">{arrival_time}</div>
                                <div class="airport-code">{arrival_iata}</div>
                            </div>
                        </div>
                        <div class="flight-details">
                            <div class="flight-airline">
                                <i class="fas fa-plane-departure"></i>
                                <span>{airline_code}</span>
                            </div>
                            <div class="flight-duration">
                                <i class="fas fa-clock"></i>
                                <span>{duration_str}</span>
                            </div>
                            <div class="flight-type">
                                <i class="fas fa-exchange-alt"></i>
                                <span>{connection_text}</span>
                            </div>
                        </div>
                    </div>'''
                
                if len(segments) > 1:
                    response += '''
                    <div class="flight-connections-horizontal">'''
                    
                    for idx, segment in enumerate(segments[1:], 1):
                        try:
                            if segment.get('departure') and segment['departure'].get('at'):
                                connection_departure = parser.parse(segment['departure']['at'])
                                connection_airline = segment.get('carrierCode', 'N/A')
                                connection_iata = segment['departure'].get('iataCode', 'N/A')
                                
                                response += f'''
                                <div class="connection-item-horizontal">
                                    <span class="connection-label">Conexão {idx}:</span>
                                    <span class="connection-time">{connection_departure.strftime('%H:%M')} - {connection_iata} ({connection_airline})</span>
                                </div>'''
                        except Exception as e:
                            print(f"[WARN] Falha ao processar conexão {idx}: {e}")
                            response += f'''
                            <div class="connection-item-horizontal">
                                <span class="connection-label">Conexão {idx}:</span>
                                <span class="connection-time">Informações não disponíveis</span>
                            </div>'''
                    
                    response += '''
                    </div>'''
                
                response += '''
                </div>'''
            
            except Exception as e:
                print(f"[ERROR] Erro ao processar voo {i}: {e}")
                response += f'''
                <div class="flight-card" style="border-left: 3px solid #f44336;">
                    <div class="flight-header">
                        <div class="price-badge" style="background: #f44336;">Erro</div>
                        <div class="flight-number">Voo {i}</div>
                    </div>
                    <div class="flight-main">
                        <div style="text-align: center; color: #666; padding: 20px;">
                            Erro ao processar informações deste voo
                        </div>
                    </div>
                </div>'''
                continue
        
        response += '</div></div>'
        return response
    
    except Exception as e:
        print(f"[ERROR] Erro geral ao formatar voos: {e}")
        return "Erro ao processar dados dos voos. Por favor, tente novamente."

# (Removida a versão antiga de format_flights_response com classes 'voo-*' e CSS inline)

def format_message_content(content):
    # Copia a função completa do app.py original
    try:
        if not content or not isinstance(content, str):
            return content or ""
        
        if '<div' in content or '<html' in content or '<body' in content or '<h3' in content or '<ul' in content:
            return content
        
        content = content.replace('\r\n', '\n').replace('\r', '\n')

        # Une linhas quebradas em parágrafos, preservando estruturas (títulos, listas e HTML)
        try:
            def _is_structural(lt):
                return (
                    lt == '' or
                    lt.startswith('<') or
                    re.match(r'^##\s', lt) or
                    re.match(r'^\*\s', lt) or
                    re.match(r'^-\s', lt) or
                    re.match(r'^\d+\.\s', lt) or
                    re.match(r'.+:\s*$', lt)
                )
            _lines = content.split('\n')
            _joined = []
            _para = []
            for _line in _lines:
                lt = _line.strip()
                if _is_structural(lt):
                    if _para:
                        _joined.append(' '.join(_para).strip())
                        _para = []
                    _joined.append(_line)
                else:
                    _para.append(lt)
            if _para:
                _joined.append(' '.join(_para).strip())
            content = '\n'.join(_joined)
            # Corrige espaços antes de pontuação
            content = re.sub(r'\s+([,.;:!?])', r'\1', content)
        except Exception:
            pass

        # Normaliza a primeira linha com '##' separando título do restante, se estiver tudo junto
        try:
            lines = content.split('\n')
            if lines and lines[0].strip().startswith('##'):
                raw = re.sub(r'^##\s*', '', lines[0].strip())
                split_markers = [' **', ' - ', ' — ', ' – ', '. ']
                split_idx = -1
                for m in split_markers:
                    i = raw.find(m)
                    if i != -1:
                        split_idx = i
                        break
                title = raw[:split_idx].strip() if split_idx != -1 else raw.strip()
                rest = raw[split_idx:].strip() if split_idx != -1 else ''
                new_lines = [f"## {title}"]
                if rest:
                    new_lines.append(rest)
                if len(lines) > 1:
                    new_lines.extend(lines[1:])
                content = '\n'.join(new_lines)
        except Exception:
            pass

        content = re.sub(r'^##\s*(.+)$', r'<br><h3 style="color: #4285f4; margin: 20px 0 10px 0; font-size: 1.3rem; font-weight: 600;">\1</h3>', content, flags=re.MULTILINE)
        content = re.sub(r'\*\*(.+?)\*\*', r'<br><strong style="color: #333; font-size: 1.1rem; display: block; margin: 15px 0 8px 0;">\1</strong>', content)
        # Itens de lista com '* ', '- ' e '1. ' (permitindo espaços iniciais) e evitando bullets vazios
        content = re.sub(r'^\s*\*\s+(\S.+)$', r'<li style="margin: 8px 0; padding-left: 20px; position: relative;">\1</li>', content, flags=re.MULTILINE)
        content = re.sub(r'^\s*-\s+(\S.+)$', r'<li style="margin: 8px 0; padding-left: 20px; position: relative;">\1</li>', content, flags=re.MULTILINE)
        content = re.sub(r'^\d+\.\s+(\S.+)$', r'<li style="margin: 8px 0; padding-left: 20px; position: relative;">\1</li>', content, flags=re.MULTILINE)
        
        lines = content.split('\n')
        formatted_lines = []
        in_list = False
        list_items = []
        
        for line in lines:
            if line.strip().startswith('<li'):
                if not in_list:
                    in_list = True
                    list_items = []
                list_items.append(line)
            else:
                if in_list and list_items:
                    formatted_lines.append('<ul style="margin: 15px 0; padding-left: 20px;">')
                    formatted_lines.extend(list_items)
                    formatted_lines.append('</ul>')
                    in_list = False
                    list_items = []
                formatted_lines.append(line)
        
        if in_list and list_items:
            formatted_lines.append('<ul style="margin: 15px 0; padding-left: 20px;">')
            formatted_lines.extend(list_items)
            formatted_lines.append('</ul>')
        
        content = '\n'.join(formatted_lines)
        # Primeiro transforma blocos de múltiplas quebras de linha em espaçamento maior
        content = re.sub(r'\n{2,}', '<br><br>', content)
        # Depois converte quebras de linha simples em <br> para manter parágrafos
        content = content.replace('\n', '<br>')
        # Negritar sempre os períodos do dia (Manhã/Manha, Tarde, Noite)
        try:
            content = re.sub(r'(?i)\b(manh[ãa]|tarde|noite)\s*:', lambda m: f"<strong>{m.group(0).strip()}</strong>", content)
        except Exception:
            pass
        content = re.sub(r'\*(.+?)\*', r'<em>\1</em>', content)
        content = content.replace('  ', '&nbsp;&nbsp;')
        content = content.lstrip('\n')

        return content
    except Exception as e:
        return content or ""

# ROTAS
@app.route('/')
def index():
    # Página inicial sempre acessível, com ou sem login
    user = User.get_current_user()
    is_logged_in = user is not None
    return render_template('index.html', is_logged_in=is_logged_in, user=user)

@app.route('/login')
def login():
    user = User.get_current_user()
    if user:
        return redirect(url_for('index'))
    return render_template('auth/login.html')

@app.route('/register')
def register():
    user = User.get_current_user()
    if user:
        return redirect(url_for('index'))
    return render_template('auth/register.html')

@app.route('/auth/login', methods=['POST'])
def auth_login():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({"success": False, "error": "Email e senha são obrigatórios"}), 400
        
        result = User.sign_in(email, password)
        
        if result.user:
            return jsonify({"success": True, "redirect": "/"})
        else:
            return jsonify({"success": False, "error": "Email ou senha incorretos"}), 401
            
    except Exception as e:
        print(f"Erro no login: {e}")
        return jsonify({"success": False, "error": "Erro interno do servidor"}), 500

@app.route('/auth/register', methods=['POST'])
def auth_register():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        full_name = data.get('full_name')
        
        if not email or not password or not full_name:
            return jsonify({"success": False, "error": "Todos os campos são obrigatórios"}), 400
        
        if len(password) < 6:
            return jsonify({"success": False, "error": "A senha deve ter pelo menos 6 caracteres"}), 400
        
        result = User.sign_up(email, password, full_name)
        
        if result.user:
            return jsonify({"success": True, "redirect": "/"})
        else:
            return jsonify({"success": False, "error": "Erro ao criar conta"}), 400
            
    except Exception as e:
        print(f"Erro no cadastro: {e}")
        error_msg = str(e)
        if "already registered" in error_msg or "already exists" in error_msg:
            return jsonify({"success": False, "error": "Este email já está cadastrado"}), 400
        return jsonify({"success": False, "error": "Erro interno do servidor"}), 500

@app.route('/auth/logout')
def auth_logout():
    User.sign_out()
    return redirect(url_for('login'))

@app.route('/chat')
def chat_page():
    user = User.get_current_user()
    is_logged_in = user is not None
    return render_template('chat.html', is_logged_in=is_logged_in, user=user)

@app.route('/historico')
@login_required
def historico():
    try:
        user_id = get_current_user_id()
        conversations = Conversation.get_user_conversations(user_id)
        return render_template('historico.html', conversations=conversations)
    except Exception as e:
        print(f"Erro ao carregar histórico: {e}")
        return render_template('historico.html', conversations=[])

@app.route('/conversation/<int:conversation_id>')
@login_required
def view_conversation(conversation_id):
    user_id = get_current_user_id()
    conversation = Conversation.get_conversation_with_messages(conversation_id, user_id)
    
    if not conversation:
        return redirect(url_for('historico'))
    
    # Formata as mensagens
    for message in conversation.get('messages', []):
        if message.get('is_bot'):
            if not ('<div' in message['content'] or '<h3' in message['content'] or '<ul' in message['content']):
                message['content'] = format_message_content(message['content'])
    
    return render_template('chat.html', conversation=conversation)

@app.route('/search', methods=['POST'])
def structured_search():
    try:
        print("[DEBUG] ===== INICIANDO BUSCA ESTRUTURADA =====")
        data = request.get_json()
        print(f"[DEBUG] Dados recebidos: {data}")
        
        user_id = get_current_user_id()
        is_logged_in = user_id is not None
        print(f"[DEBUG] Usuário logado: {is_logged_in}, User ID: {user_id}")
        
        if not data:
            return jsonify({"error": "Dados inválidos recebidos"}), 400
        
        # Extrair dados estruturados
        origin = data.get('origin', '').strip()
        destination = data.get('destination', '').strip()
        checkin = data.get('checkin')
        checkout = data.get('checkout')
        adults = data.get('adults', 2)
        children = data.get('children', 0)
        
        print(f"[DEBUG] Origem: {origin}, Destino: {destination}, Check-in: {checkin}, Check-out: {checkout}")
        
        # Validar dados essenciais
        if not origin or not destination or not checkin:
            return jsonify({"error": "Origem, destino e data de ida são obrigatórios"}), 400
        
        # Calcular duração da viagem
        duration_text = ""
        start_date = None
        end_date = None
        
        try:
            if checkin:
                start_date = datetime.strptime(checkin, "%Y-%m-%d").date()
                
            if checkout:
                end_date = datetime.strptime(checkout, "%Y-%m-%d").date()
                days = (end_date - start_date).days
                if days > 0:
                    duration_text = f" por {days} dia{'s' if days != 1 else ''}"
        except ValueError:
            return jsonify({"error": "Formato de data inválido"}), 400
        
        # Preparar dados para a função get_ai_response
        datas = {
            "data_inicio": checkin,
            "data_fim": checkout
        }
        
        # Construir mensagem natural
        message = f"Quero um roteiro de viagem de {origin} para {destination}{duration_text}"
        
        if checkin:
            formatted_date = start_date.strftime("%d/%m/%Y")
            message += f" saindo no dia {formatted_date}"
        
        if adults > 1 or children > 0:
            message += f" para {adults} adulto{'s' if adults != 1 else ''}"
            if children > 0:
                message += f" e {children} criança{'s' if children != 1 else ''}"
        
        print(f"[DEBUG] Mensagem construída: {message}")
        
        # Criar nova conversa APENAS se usuário estiver logado
        conversation = None
        if is_logged_in:
            conversation = Conversation.create_conversation(
                user_id=user_id,
                title=generate_conversation_title(message),
                origin=origin,
                destination=destination,
                start_date=start_date,
                end_date=end_date
            )
            
            if not conversation:
                return jsonify({"error": "Erro ao criar conversa"}), 500
        
        # Processar com IA
        if not user_id:
            # Criar ID temporário para guest se não existir
            if 'guest_id' not in session:
                session['guest_id'] = str(uuid.uuid4())[:8]
        
        context_key = user_id if user_id else f"guest_{session['guest_id']}"
        if context_key not in chat_context:
            chat_context[context_key] = []
        
        print(f"[DEBUG] Context key: {context_key}")
        chat_context[context_key].append({"role": "user", "content": message})
        
        print("[DEBUG] Chamando get_ai_response...")
        bot_response = get_ai_response(chat_context[context_key], origem=origin, destino=destination, datas=datas)
        print(f"[DEBUG] Bot response recebido. Tamanho: {len(bot_response)} caracteres")
        
        chat_context[context_key].append({"role": "model", "content": bot_response})
        
        # Salvar mensagens APENAS se usuário estiver logado
        if is_logged_in and conversation:
            Message.create_message(conversation['id'], message, is_bot=False)
            formatted_response = format_message_content(bot_response)
            Message.create_message(conversation['id'], formatted_response, is_bot=True)
        else:
            formatted_response = format_message_content(bot_response)
        
        response_data = {
            'success': True,
            'conversation_id': conversation['id'] if conversation else None,
            'title': conversation['title'] if conversation else generate_conversation_title(message),
            'user_message': message,
            'bot_response': formatted_response,
            'is_logged_in': is_logged_in,
            'requires_login': not is_logged_in  # Flag para mostrar aviso de login
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Erro na busca estruturada: {e}")
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500

@app.route('/chat', methods=['POST'])
@login_required
def chat():
    try:
        user_message = request.json.get('message', '').strip()
        user_id = get_current_user_id()
        
        # Lógica similar ao app.py original, mas usando Supabase
        # Por brevidade, versão simplificada
        
        if user_id not in chat_context:
            chat_context[user_id] = []

        chat_context[user_id].append({"role": "user", "content": user_message})
        bot_response = get_ai_response(chat_context[user_id])
        chat_context[user_id].append({"role": "model", "content": bot_response})

        formatted_response = format_message_content(bot_response)
        
        return jsonify({'response': formatted_response})
        
    except Exception as e:
        print(f"Erro no chat: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/new_chat', methods=['POST'])
@login_required
def new_chat():
    try:
        user_id = get_current_user_id()
        
        if user_id in chat_context:
            chat_context[user_id] = []
        
        return jsonify({"success": True, "message": "Nova conversa iniciada"})
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/cambio', methods=['GET'])
def cambio():
    moeda = request.args.get('moeda', 'USD')
    taxa = get_exchange_rate(moeda)
    return jsonify({'moeda': moeda, 'taxa': taxa})

@app.route('/limpar_historico', methods=['POST'])
@login_required
def limpar_historico():
    try:
        user_id = get_current_user_id()
        conversations = Conversation.get_user_conversations(user_id)
        
        for conv in conversations:
            Conversation.delete(conv['id'])
        
        if user_id in chat_context:
            chat_context[user_id] = []
        
        return jsonify({"success": True})
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/excluir_conversa/<int:conversation_id>', methods=['POST'])
@login_required
def excluir_conversa(conversation_id):
    try:
        user_id = get_current_user_id()
        conversation = Conversation.get_conversation_with_messages(conversation_id, user_id)
        
        if not conversation:
            return jsonify({"success": False, "error": "Conversa não encontrada"}), 404
        
        Conversation.delete(conversation_id)
        return jsonify({"success": True})
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/images/<path:filename>')
def serve_image(filename):
    """Serve arquivos da pasta images"""
    return send_from_directory('images', filename)

if __name__ == '__main__':
    app.run(debug=True, port=8000)
