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
from geopy.geocoders import Nominatim
from flask_session import Session
import uuid
from datetime import timedelta, datetime, date
from functools import wraps
import time

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
    # 🇧🇷 Brasil
    "brasil": "BSB",
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
    "foz do iguacu": "IGU",
    "foz do iguaçu": "IGU",
    "maceio": "MCZ",
    "maceió": "MCZ",
    "vitoria": "VIX",
    "vitória": "VIX",
    "aracaju": "AJU",
    "belem": "BEL",
    "belém": "BEL",
    "joao pessoa": "JPA",
    "joão pessoa": "JPA",
    "campo grande": "CGR",
    "cuiaba": "CGB",
    "cuiabá": "CGB",
    "londrina": "LDB",
    "ribeirao preto": "RAO",
    "ribeirão preto": "RAO",
    "palmas": "PMW",
    "porto seguro": "BPS",
    "ilhéus": "IOS",

    # 🇦🇷 Argentina
    "argentina": "EZE",
    "buenos aires": "EZE",
    "cordoba": "COR",
    "rosario": "ROS",

    # 🇺🇾 Uruguai
    "uruguai": "MVD",
    "montevideo": "MVD",
    "punta del este": "PDP",

    # 🇨🇱 Chile
    "chile": "SCL",
    "santiago": "SCL",
    "valparaiso": "VAP",

    # 🇵🇪 Peru
    "peru": "LIM",
    "lima": "LIM",
    "cusco": "CUZ",

    # 🇪🇨 Equador
    "equador": "UIO",
    "quito": "UIO",
    "guayaquil": "GYE",

    # 🇨🇴 Colômbia
    "colombia": "BOG",
    "colômbia": "BOG",
    "bogota": "BOG",
    "bogotá": "BOG",
    "medellin": "MDE",
    "cartagena": "CTG",

    # 🇻🇪 Venezuela
    "venezuela": "CCS",
    "caracas": "CCS",

    # 🇵🇾 Paraguai
    "paraguai": "ASU",
    "assuncao": "ASU",
    "assunção": "ASU",

    # 🇧🇴 Bolívia
    "bolivia": "LPB",
    "bolívia": "LPB",
    "la paz": "LPB",
    "santa cruz de la sierra": "VVI",

    # 🇲🇽 México
    "mexico": "MEX",
    "méxico": "MEX",
    "cidade do mexico": "MEX",
    "cancun": "CUN",
    "cancún": "CUN",
    "guadalajara": "GDL",
    "monterrey": "MTY",

    # 🇨🇦 Canadá
    "canada": "YYZ",
    "canadá": "YYZ",
    "toronto": "YYZ",
    "vancouver": "YVR",
    "montreal": "YUL",
    "ottawa": "YOW",
    "calgary": "YYC",

    # 🇺🇸 Estados Unidos
    "estados unidos": "JFK",
    "eua": "JFK",
    "nova iorque": "JFK",
    "new york": "JFK",
    "miami": "MIA",
    "orlando": "MCO",
    "los angeles": "LAX",
    "san francisco": "SFO",
    "chicago": "ORD",
    "washington": "IAD",
    "boston": "BOS",
    "atlanta": "ATL",
    "las vegas": "LAS",
    "houston": "IAH",
    "dallas": "DFW",
    "seattle": "SEA",
    "denver": "DEN",
    "philadelphia": "PHL",

    # 🇬🇧 Reino Unido
    "reino unido": "LHR",
    "inglaterra": "LHR",
    "londres": "LHR",
    "london": "LHR",
    "manchester": "MAN",
    "edinburgh": "EDI",
    "liverpool": "LPL",

    # 🇮🇪 Irlanda
    "irlanda": "DUB",
    "dublin": "DUB",

    # 🇫🇷 França
    "franca": "CDG",
    "frança": "CDG",
    "paris": "CDG",
    "marselha": "MRS",
    "nice": "NCE",
    "lyon": "LYS",

    # 🇪🇸 Espanha
    "espanha": "MAD",
    "madrid": "MAD",
    "barcelona": "BCN",
    "valencia": "VLC",
    "sevilla": "SVQ",
    "malaga": "AGP",

    # 🇵🇹 Portugal
    "portugal": "LIS",
    "lisboa": "LIS",
    "porto": "OPO",
    "faro": "FAO",

    # 🇮🇹 Itália
    "italia": "FCO",
    "itália": "FCO",
    "roma": "FCO",
    "veneza": "VCE",
    "milao": "MXP",
    "milão": "MXP",
    "florenca": "FLR",
    "florença": "FLR",
    "napoles": "NAP",
    "nápoles": "NAP",

    # 🇩🇪 Alemanha
    "alemanha": "FRA",
    "berlim": "BER",
    "frankfurt": "FRA",
    "munique": "MUC",
    "hamburgo": "HAM",
    "colonia": "CGN",
    "colônia": "CGN",

    # 🇨🇭 Suíça
    "suica": "ZRH",
    "suíça": "ZRH",
    "zurique": "ZRH",
    "geneva": "GVA",
    "genebra": "GVA",

    # 🇧🇪 Bélgica
    "belgica": "BRU",
    "bélgica": "BRU",
    "bruxelas": "BRU",

    # 🇳🇱 Países Baixos
    "paises baixos": "AMS",
    "holanda": "AMS",
    "amsterda": "AMS",
    "amsterdã": "AMS",

    # 🇦🇹 Áustria
    "austria": "VIE",
    "áustria": "VIE",
    "viena": "VIE",

    # 🇩🇰 Dinamarca
    "dinamarca": "CPH",
    "copenhague": "CPH",

    # 🇸🇪 Suécia
    "suecia": "ARN",
    "suécia": "ARN",
    "estocolmo": "ARN",

    # 🇳🇴 Noruega
    "noruega": "OSL",
    "oslo": "OSL",

    # 🇫🇮 Finlândia
    "finlandia": "HEL",
    "finlândia": "HEL",
    "helsinque": "HEL",

    # 🇨🇿 República Tcheca
    "republica tcheca": "PRG",
    "república tcheca": "PRG",
    "praga": "PRG",

    # 🇭🇺 Hungria
    "hungria": "BUD",
    "budapeste": "BUD",

    # 🇵🇱 Polônia
    "polonia": "WAW",
    "polônia": "WAW",
    "varsovia": "WAW",
    "varsóvia": "WAW",
    "cracovia": "KRK",

    # 🇷🇺 Rússia
    "russia": "SVO",
    "rússia": "SVO",
    "moscou": "SVO",
    "são petersburgo": "LED",

    # 🇬🇷 Grécia
    "grecia": "ATH",
    "grécia": "ATH",
    "atenas": "ATH",
    "santorini": "JTR",
    "mykonos": "JMK",

    # 🇹🇷 Turquia
    "turquia": "IST",
    "istambul": "IST",
    "istanbul": "IST",
    "ancara": "ESB",

    # 🇮🇱 Israel
    "israel": "TLV",
    "tel aviv": "TLV",
    "jerusalem": "TLV",

    # 🇯🇵 Japão
    "japao": "HND",
    "japão": "HND",
    "tokyo": "HND",
    "tóquio": "HND",
    "osaka": "KIX",
    "kyoto": "ITM",

    # 🇨🇳 China
    "china": "PEK",
    "pequim": "PEK",
    "xangai": "PVG",
    "hong kong": "HKG",

    # 🇰🇷 Coreia do Sul
    "coreia do sul": "ICN",
    "seul": "ICN",

    # 🇮🇳 Índia
    "india": "DEL",
    "índia": "DEL",
    "nova deli": "DEL",
    "mumbai": "BOM",

    # 🇹🇭 Tailândia
    "tailandia": "BKK",
    "tailândia": "BKK",
    "bangkok": "BKK",
    "phuket": "HKT",

    # 🇲🇾 Malásia
    "malasia": "KUL",
    "malásia": "KUL",
    "kuala lumpur": "KUL",

    # 🇸🇬 Singapura
    "singapura": "SIN",

    # 🇮🇩 Indonésia
    "indonesia": "CGK",
    "indonésia": "CGK",
    "jacarta": "CGK",
    "bali": "DPS",

    # 🇦🇪 Emirados Árabes
    "emirados arabes unidos": "DXB",
    "emirados árabes unidos": "DXB",
    "dubai": "DXB",
    "abu dhabi": "AUH",

    # 🇶🇦 Catar
    "qatar": "DOH",
    "catara": "DOH",
    "doha": "DOH",

    # 🇸🇦 Arábia Saudita
    "arabia saudita": "RUH",
    "arábia saudita": "RUH",
    "riade": "RUH",
    "jeddah": "JED",

    # 🇪🇬 Egito
    "egito": "CAI",
    "cairo": "CAI",
    "hurghada": "HRG",

    # 🇿🇦 África do Sul
    "africa do sul": "JNB",
    "áfrica do sul": "JNB",
    "johanesburgo": "JNB",
    "cidade do cabo": "CPT",

    # 🇲🇦 Marrocos
    "marrocos": "CMN",
    "casablanca": "CMN",
    "marrakech": "RAK",

    # 🇰🇪 Quênia
    "quenia": "NBO",
    "quênia": "NBO",
    "nairobi": "NBO",

    # 🇳🇬 Nigéria
    "nigeria": "LOS",
    "nigéria": "LOS",
    "lagos": "LOS",

    # 🇦🇺 Austrália
    "australia": "SYD",
    "austrália": "SYD",
    "sydney": "SYD",
    "melbourne": "MEL",
    "brisbane": "BNE",
    "perth": "PER",

    # 🇳🇿 Nova Zelândia
    "nova zelandia": "AKL",
    "nova zelândia": "AKL",
    "auckland": "AKL",
    "wellington": "WLG",
    "christchurch": "CHC",

    # 🌴 Ilhas e destinos turísticos
    "maldivas": "MLE",
    "seychelles": "SEZ",
    "ilhas mauricio": "MRU",
    "ilhas mauritio": "MRU",
    "hawai": "HNL",
    "havaí": "HNL",
    "taiti": "PPT",
    "fiji": "NAN",
    "bahamas": "NAS",
    "barbados": "BGI",
    "aruba": "AUA",
    "cabo verde": "RAI",
}

PALAVRAS_DESCARTAR = [
    "para", "até", "e", "com", "por", "durante", "no", "na", "do", "da", "dos", "das", 
    "de", "em", "ao", "aos", "às", "as", "os", "o", "a", "um", "uma", "uns", "umas"
]

# Decorator para autenticação
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        print(f"[DEBUG] @login_required checking authentication for {f.__name__}")
        try:
            user = User.get_current_user()
            print(f"[DEBUG] User authenticated: {user is not None}")
            if user:
                print(f"[DEBUG] User ID: {user.id if hasattr(user, 'id') else 'N/A'}")

            if not user:
                print(f"[DEBUG] No user found, redirecting to login")
                if request.is_json:
                    return jsonify({"error": "Autenticação necessária"}), 401
                return redirect(url_for('login'))

            print(f"[DEBUG] Calling function {f.__name__}")
            return f(*args, **kwargs)
        except Exception as e:
            print(f"[ERROR] Error in login_required: {e}")
            import traceback
            print(f"[ERROR] Traceback: {traceback.format_exc()}")
            return redirect(url_for('login'))
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
                    "maxOutputTokens": 8192,  # Aumentado significativamente para roteiros completos
                }
            }
            
            print(f"[DEBUG] Enviando requisição para Gemini API...")
            try:
                response = requests.post(url, headers=headers, data=json.dumps(data), timeout=30)
                print(f"[DEBUG] Resposta da API Gemini: {response.status_code}")
                
                if response.status_code == 200:
                    resposta = response.json()
                    try:
                        # Verificar se há candidatos
                        if not resposta.get("candidates") or len(resposta["candidates"]) == 0:
                            print(f"[ERROR] Nenhum candidato retornado pela API")
                            print(f"[DEBUG] Resposta completa: {resposta}")
                            roteiro = "Desculpe, não consegui gerar um roteiro completo. Por favor, tente novamente."
                        else:
                            candidate = resposta["candidates"][0]

                            # Verificar finish reason
                            finish_reason = candidate.get("finishReason", "UNKNOWN")
                            print(f"[DEBUG] Finish reason: {finish_reason}")

                            if finish_reason == "MAX_TOKENS":
                                print(f"[WARN] Resposta truncada por MAX_TOKENS")

                            # Tentar extrair o conteúdo
                            content = candidate.get("content", {})
                            parts = content.get("parts", [])

                            if parts and len(parts) > 0 and "text" in parts[0]:
                                roteiro = parts[0]["text"]
                                print(f"[DEBUG] Resposta do Gemini recebida. Tamanho: {len(roteiro)} caracteres")

                                if finish_reason == "MAX_TOKENS":
                                    roteiro += "\n\n*Nota: O roteiro pode estar incompleto devido ao limite de tokens. Para roteiros mais longos, considere solicitar informações mais específicas.*"
                                    print(f"[WARN] Roteiro pode estar incompleto")

                                print(f"[DEBUG] Primeiros 200 caracteres: {roteiro[:200]}...")
                            else:
                                print(f"[ERROR] Estrutura de resposta inválida - 'parts' não encontrado ou vazio")
                                print(f"[DEBUG] Content: {content}")
                                print(f"[DEBUG] Resposta completa: {resposta}")
                                roteiro = "Desculpe, não consegui gerar um roteiro completo. A resposta da IA foi incompleta. Por favor, tente novamente com uma solicitação mais específica."

                    except KeyError as e:
                        print(f"[ERROR] Campo faltando na resposta do Gemini: {e}")
                        print(f"[DEBUG] Resposta completa: {resposta}")
                        roteiro = "Desculpe, ocorreu um erro ao processar a resposta da IA. Por favor, tente novamente."
                    except Exception as e:
                        print(f"[ERROR] Erro inesperado ao processar resposta do Gemini: {e}")
                        print(f"[DEBUG] Resposta completa: {resposta}")
                        import traceback
                        print(f"[ERROR] Traceback: {traceback.format_exc()}")
                        roteiro = "Desculpe, não consegui gerar um roteiro agora. Por favor, tente novamente."
                else:
                    print(f"[ERROR] Erro na API Gemini: {response.status_code} - {response.text}")
                    roteiro = "Desculpe, a API de geração de roteiros está temporariamente indisponível. Por favor, tente novamente em alguns instantes."
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
                
                # NOVA LÓGICA: Extrair cidade principal do roteiro gerado
                cidade_principal, codigo_iata_roteiro = extract_main_city_from_itinerary(roteiro, destino, origem)
                
                # Se encontrou uma cidade específica no roteiro, usa ela; senão usa o destino original
                if codigo_iata_roteiro:
                    destino_iata = codigo_iata_roteiro
                    destino_para_busca = cidade_principal
                    print(f"[DEBUG] Usando cidade do roteiro: {cidade_principal} -> {destino_iata}")
                else:
                    destino_iata = buscar_codigo_iata(destino)
                    destino_para_busca = destino
                    print(f"[DEBUG] Usando destino original: {destino} -> {destino_iata}")
                
                print(f"[DEBUG] Códigos IATA finais: {origem_iata} -> {destino_iata}")
                
                if origem_iata and destino_iata:
                    # Buscar hotéis primeiro
                    print(f"[DEBUG] Buscando hotéis para {destino_iata}")
                    try:
                        print(f"[DEBUG] Buscando hotéis para {destino_para_busca}")
                        hoteis = buscar_hoteis(destino_iata)
                        
                        if hoteis and 'data' in hoteis and hoteis['data']:
                            try:
                                hoteis_html = format_hotels_response(hoteis['data'])
                                # Adiciona hotéis ao roteiro
                                if roteiro.strip():
                                    roteiro += "\n\n---\n\n" + hoteis_html
                                else:
                                    roteiro = hoteis_html
                                print(f"[DEBUG] Hotéis adicionados ao roteiro")
                            except Exception as hotel_error:
                                print(f"[ERROR] Erro ao formatar hotéis: {hotel_error}")
                                roteiro += "\n\n---\n\n⚠️ Encontrei hotéis disponíveis, mas houve um erro ao exibir as informações detalhadas."
                        elif hoteis and 'error' in hoteis:
                            print(f"[WARN] Erro na busca de hotéis: {hoteis['error']}")
                            roteiro += "\n\n---\n\n⚠️ Não foi possível buscar informações de hotéis no momento."
                        else:
                            print(f"[DEBUG] Nenhum hotel encontrado")
                            roteiro += "\n\n---\n\n🏨 Não encontrei hotéis disponíveis para este destino."
                    except Exception as hotel_error:
                        print(f"[ERROR] Erro ao buscar hotéis: {hotel_error}")
                        roteiro += "\n\n---\n\n⚠️ Houve um erro ao buscar informações de hotéis."
                    
                    # Buscar voos
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

def buscar_hoteis(codigo_cidade):
    """Busca hotéis usando a API Amadeus"""
    try:
        # Autenticação
        auth_data = {
            "grant_type": "client_credentials",
            "client_id": os.getenv("AMADEUS_CLIENT_ID"),
            "client_secret": os.getenv("AMADEUS_CLIENT_SECRET")
        }
        
        auth_response = requests.post("https://test.api.amadeus.com/v1/security/oauth2/token", data=auth_data, verify=False, timeout=10)
        if auth_response.status_code != 200:
            return {"data": [], "error": "Erro na autenticação"}
        
        token = auth_response.json().get("access_token")
        if not token:
            return {"data": [], "error": "Token de acesso não encontrado"}

        # Busca de hotéis
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }
        
        # Buscar hotéis por código da cidade
        hotel_params = {
            "cityCode": codigo_cidade,
            "radius": 20,
            "radiusUnit": "KM",
            "hotelSource": "ALL"
        }
        
        hotel_response = requests.get(
            "https://test.api.amadeus.com/v1/reference-data/locations/hotels/by-city",
            headers=headers,
            params=hotel_params,
            verify=False,
            timeout=15
        )
        
        if hotel_response.status_code != 200:
            return {"data": [], "error": "Erro na busca de hotéis"}
        
        hotel_data = hotel_response.json()
        hoteis = hotel_data.get("data", [])
        
        if not hoteis:
            return {"data": [], "error": "Nenhum hotel encontrado"}
        
        # Limitar a 5 hotéis
        hoteis = hoteis[:5]
        
        # Buscar preços dos hotéis
        from datetime import datetime, timedelta
        
        # Data de check-in: 7 dias a partir de hoje
        checkin_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        # Data de check-out: 10 dias a partir de hoje (3 noites)
        checkout_date = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d")
        
        hoteis_com_preco = []
        
        for hotel in hoteis:
            hotel_id = hotel.get("hotelId")
            if not hotel_id:
                continue
            
            # Buscar preços do hotel
            offer_params = {
                "hotelIds": hotel_id,
                "adults": 1,
                "checkInDate": checkin_date,
                "checkOutDate": checkout_date,
                "roomQuantity": 1,
                "currency": "USD"
            }
            
            try:
                offer_response = requests.get(
                    "https://test.api.amadeus.com/v3/shopping/hotel-offers",
                    headers=headers,
                    params=offer_params,
                    verify=False,
                    timeout=10
                )
                
                if offer_response.status_code == 200:
                    offer_data = offer_response.json()
                    offers = offer_data.get("data", [])
                    
                    if offers and len(offers) > 0:
                        # Pegar a primeira oferta
                        offer = offers[0]
                        hotel_info = offer.get("hotel", {})
                        room_offers = offer.get("offers", [])
                        

        
                        
                        if room_offers:
                            price_info = room_offers[0].get("price", {})
                            total_price = price_info.get("total")
                            
                            if total_price:
                                # Converter para BRL
                                try:
                                    cotacao_dolar = get_exchange_rate("USD")
                                    if cotacao_dolar <= 0:
                                        cotacao_dolar = 5.0
                                    
                                    preco_usd = float(total_price)
                                    preco_brl = preco_usd * cotacao_dolar
                                    preco_formatado = f"R$ {preco_brl:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                                    
                                    # Como a API Hotel List não retorna classificação por estrelas na resposta,
                                    # vamos atribuir classificações baseadas no preço dos hotéis
                                    preco_numerico = float(total_price)
                                    
                                    if preco_numerico > 700:
                                        rating = 5
                                    elif preco_numerico > 500:
                                        rating = 4
                                    elif preco_numerico > 300:
                                        rating = 3
                                    else:
                                        # Para hotéis com preços baixos, atribuir baseado na posição (primeiros são melhores)
                                        rating = max(3, 5 - len(hoteis_com_preco))
                                    
                                    print(f"Hotel: {hotel_info.get('name', hotel.get('name', 'Sem nome'))} - Rating: {rating} estrelas")
                                    
                                    hotel_completo = {
                                        "hotelId": hotel_id,
                                        "name": hotel_info.get("name", hotel.get("name", "Hotel sem nome")),
                                        "rating": rating,
                                        "price": preco_formatado,
                                        "address": hotel_info.get("address", {}),
                                        "contact": hotel_info.get("contact", {}),
                                        "amenities": hotel_info.get("amenities", [])
                                    }
                                    hoteis_com_preco.append(hotel_completo)
                                except Exception as e:
                                    print(f"[ERROR] Erro ao converter preço: {e}")
                                    continue
            except Exception as e:
                print(f"[ERROR] Erro ao buscar preços do hotel {hotel_id}: {e}")
                continue
        
        return {"data": hoteis_com_preco, "error": None}
        
    except Exception as e:
        print(f"[ERROR] Erro geral na busca de hotéis: {e}")
        return {"data": [], "error": str(e)}

def format_hotels_response(hotels):
    """Formata a resposta dos hotéis em cards HTML com nomes e ratings em estrelas"""
    try:
        if not isinstance(hotels, (list, tuple)):
            return "Erro ao processar dados dos hotéis. Por favor, tente novamente."
        
        if not hotels:
            return "Desculpe, não encontrei hotéis disponíveis para este destino."
        
        response = '<div class="hotels-section">'
        response += '<h3 style="color: #ff6b35; margin-bottom: 15px; font-size: 1.2rem; font-weight: 600;">🏨 Hotéis Disponíveis</h3>'
        response += '<div class="hotels-grid">'
        
        for i, hotel in enumerate(hotels, 1):
            try:
                if not isinstance(hotel, dict):
                    continue
                
                nome = hotel.get("name", "Hotel sem nome")
                rating = hotel.get("rating", 0)
                preco = hotel.get("price", "Preço não disponível")
                
                # Gerar estrelas baseado no rating
                estrelas = ""
                if rating and isinstance(rating, (int, float)) and rating > 0:
                    rating_int = int(rating)
                    for j in range(5):
                        if j < rating_int:
                            estrelas += "⭐"
                        else:
                            estrelas += "☆"
                    estrelas += f" ({rating})"
                else:
                    estrelas = "Sem classificação"
                
                # Endereço
                address = hotel.get("address", {})
                endereco = ""
                if isinstance(address, dict):
                    city = address.get("cityName", "")
                    country = address.get("countryCode", "")
                    if city or country:
                        endereco = f"{city}, {country}".strip(", ")
                
                response += f'''
                <div class="hotel-card" style="
                    background: linear-gradient(135deg, #fff 0%, #f8f9fa 100%);
                    border: 1px solid #e9ecef;
                    border-radius: 12px;
                    padding: 16px;
                    margin-bottom: 12px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                    transition: all 0.3s ease;
                    cursor: pointer;
                ">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                        <div style="flex: 1;">
                            <h4 style="margin: 0 0 4px 0; color: #2c3e50; font-size: 1.1rem; font-weight: 600;">
                                🏨 {nome}
                            </h4>
                            <div style="color: #f39c12; font-size: 0.9rem; margin-bottom: 4px;">
                                {estrelas}
                            </div>
                            {f'<div style="color: #6c757d; font-size: 0.85rem; margin-bottom: 8px;">{endereco}</div>' if endereco else ''}
                        </div>
                        <div style="text-align: right;">
                            <div style="background: #ff6b35; color: white; padding: 6px 12px; border-radius: 20px; font-weight: 600; font-size: 0.9rem;">
                                {preco}
                            </div>
                            <div style="color: #6c757d; font-size: 0.75rem; margin-top: 2px;">
                                3 noites
                            </div>
                        </div>
                    </div>
                </div>
                '''
                
            except Exception as e:
                print(f"[ERROR] Erro ao formatar hotel {i}: {e}")
                continue
        
        response += '</div></div>'
        return response
        
    except Exception as e:
        print(f"[ERROR] Erro ao formatar resposta dos hotéis: {e}")
        return "Erro ao exibir hotéis. Por favor, tente novamente."

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

def extract_main_city_from_itinerary(roteiro_text, destino_original, origem=None):
    """
    Extrai a cidade principal mencionada no roteiro gerado pela IA
    para usar na busca de voos e hotéis ao invés do destino original genérico
    """
    try:
        print(f"[DEBUG] Extraindo cidade principal do roteiro para destino original: {destino_original}")
        print(f"[DEBUG] Origem a ser excluída: {origem}")
        
        # Usar principalmente o array CITY_IATA_CODES existente
        cidades_conhecidas = CITY_IATA_CODES.copy()
        
        # Complementar com cidades adicionais que não estão no CITY_IATA_CODES
        cidades_adicionais = {
            # Variações em inglês que podem não estar no array principal
            "rome": "FCO", "milan": "MXP", "venice": "VCE", "florence": "FLR",
            "berlin": "BER", "munich": "MUC", "hamburg": "HAM",
            "vienna": "VIE", "prague": "PRG", "lisbon": "LIS",
            "zurich": "ZRH", "geneva": "GVA",
            "london": "LHR", "edinburgh": "EDI",
            "marseille": "MRS", "lyon": "LYS",
            "seville": "SVQ", "valencia": "VLC",
            "naples": "NAP", "bologna": "BLQ",
            "stockholm": "ARN", "copenhagen": "CPH", "oslo": "OSL",
            "helsinki": "HEL", "budapest": "BUD", "warsaw": "WAW",
            "krakow": "KRK", "athens": "ATH", "istanbul": "IST",
            "tel aviv": "TLV", "jerusalem": "TLV",
            "beijing": "PEK", "shanghai": "PVG", "seoul": "ICN",
            "new delhi": "DEL", "mumbai": "BOM", "bangkok": "BKK",
            "kuala lumpur": "KUL", "singapore": "SIN", "jakarta": "CGK",
            "dubai": "DXB", "abu dhabi": "AUH", "doha": "DOH",
            "riyadh": "RUH", "cairo": "CAI", "johannesburg": "JNB",
            "cape town": "CPT", "casablanca": "CMN", "marrakech": "RAK",
            "nairobi": "NBO", "lagos": "LOS", "sydney": "SYD",
            "melbourne": "MEL", "brisbane": "BNE", "perth": "PER",
            "auckland": "AKL", "wellington": "WLG", "christchurch": "CHC"
        }
        
        # Adicionar cidades que não estão no array principal
        for cidade, codigo in cidades_adicionais.items():
            if cidade not in cidades_conhecidas:
                cidades_conhecidas[cidade] = codigo
        
        # Criar lista de cidades a excluir (origem e variações)
        cidades_excluir = set()
        if origem:
            origem_lower = origem.lower().strip()
            cidades_excluir.add(origem_lower)
            
            # Adicionar variações da origem que podem estar no dicionário
            for cidade_conhecida in cidades_conhecidas.keys():
                if origem_lower in cidade_conhecida or cidade_conhecida in origem_lower:
                    cidades_excluir.add(cidade_conhecida)
            
            print(f"[DEBUG] Cidades a excluir: {cidades_excluir}")
        
        # Padrões para encontrar cidades no texto
        patterns = [
            # Padrões diretos de menção de cidade
            r'\b(?:em|para|de|visit|explore|conhecer|ir para|vá para|dirija-se)\s+([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú][a-zà-ú]+)?)\b',
            # Cidades no início de frases
            r'^([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú][a-zà-ú]+)?)\s+(?:é|tem|possui|oferece|conta)',
            # Padrões com "cidade de"
            r'cidade de ([A-ZÀ-Ú][a-zà-ú]+)',
            # Menções diretas de cidades conhecidas
            r'\b(' + '|'.join(cidades_conhecidas.keys()) + r')\b'
        ]
        
        cidades_encontradas = {}
        
        # Buscar por todas as cidades mencionadas
        for pattern in patterns:
            matches = re.finditer(pattern, roteiro_text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                cidade = match.group(1).lower().strip()
                
                # Verificar se a cidade está no dicionário e não é uma cidade a excluir
                if cidade in cidades_conhecidas and cidade not in cidades_excluir:
                    if cidade not in cidades_encontradas:
                        cidades_encontradas[cidade] = 0
                    cidades_encontradas[cidade] += 1
                    print(f"[DEBUG] Cidade encontrada: {cidade} (menções: {cidades_encontradas[cidade]})")
                elif cidade in cidades_excluir:
                    print(f"[DEBUG] Cidade excluída (origem): {cidade}")
        
        # Se encontrou cidades, retorna a mais mencionada
        if cidades_encontradas:
            cidade_principal = max(cidades_encontradas, key=cidades_encontradas.get)
            codigo_iata = cidades_conhecidas[cidade_principal]
            print(f"[DEBUG] Cidade principal identificada: {cidade_principal} -> {codigo_iata}")
            return cidade_principal, codigo_iata
        
        # Se não encontrou nenhuma cidade específica, retorna o destino original
        print(f"[DEBUG] Nenhuma cidade específica encontrada, usando destino original: {destino_original}")
        return destino_original, None
        
    except Exception as e:
        print(f"[ERROR] Erro ao extrair cidade principal: {e}")
        return destino_original, None

def extract_points_of_interest(text, destination):
    """
    Extrai pontos de interesse mencionados no roteiro gerado pela IA
    """
    try:
        print(f"[DEBUG] Extraindo pontos de interesse para {destination}")
        print(f"[DEBUG] Texto para análise (primeiros 500 chars): {text[:500]}")

        # Padrões mais abrangentes para capturar nomes de lugares
        patterns = [
            # Nomes com palavras-chave de tipos de lugares (PT e EN)
            r'\b([A-ZÀ-Ú][A-Za-zÀ-ú\'\-]+(?:\s+[A-Za-zÀ-ú\'\-]+)*)\s*(?:Museum|Museu|Torre|Tower|Catedral|Cathedral|Igreja|Church|Praça|Square|Parque|Park|Palácio|Palace|Teatro|Theatre|Theater|Centro|Center|Centre|Praia|Beach|Monumento|Monument|Memorial|Castelo|Castle|Forte|Fort|Jardim|Garden|Mercado|Market|Bairro|District|Avenue|Avenida|Basílica|Basilica|Galeria|Gallery|Aquário|Aquarium|Estádio|Stadium|Arena|Observatório|Observatory)\b',

            # Padrão para lugares entre asteriscos (markdown bold)
            r'\*\*([A-ZÀ-Ú][A-Za-zÀ-ú\'\-\s]{3,50}(?:Museum|Museu|Torre|Tower|Catedral|Cathedral|Igreja|Church|Praça|Square|Parque|Park|Palácio|Palace|Teatro|Theatre|Theater|Centro|Center|Centre|Praia|Beach|Monumento|Monument|Memorial|Castelo|Castle|Forte|Fort|Jardim|Garden|Mercado|Market|Basílica|Basilica|Galeria|Gallery))\*\*',

            # Padrão para lugares famosos conhecidos (sem palavras-chave)
            r'\b(Torre Eiffel|Louvre|Notre[- ]Dame|Arc de Triomphe|Arco do Triunfo|Sacré[- ]Cœur|Versailles|Montmartre|Champs[- ]Élysées|Musée d\'Orsay|Centre Pompidou|Panteão|Panthéon|Sorbonne|Opéra Garnier|Ópera Garnier|Coliseu|Colosseum|Vaticano|Vatican|Fontana di Trevi|Piazza Navona|Piazza di Spagna|Fórum Romano|Roman Forum|Sagrada Família|Park Güell|Parque Güell|La Rambla|Camp Nou|Big Ben|Tower Bridge|British Museum|Buckingham Palace|Westminster|London Eye|Statue of Liberty|Estátua da Liberdade|Times Square|Central Park|Empire State|Brooklyn Bridge|Christ the Redeemer|Cristo Redentor|Copacabana|Ipanema|Pão de Açúcar|Maracanã|Alhambra|Prado Museum|Reina Sofia|Plaza Mayor|Parque del Retiro|Retiro Park)\b',

            # Padrão para verbos de ação seguidos de lugar
            r'(?:visitar|conhecer|visite|explore|ver|vá para|ir para|dirija-se|caminhe até|passe por|não perca)\s+(?:o|a|os|as)?\s*([A-ZÀ-Ú][A-Za-zÀ-ú\'\-\s]{4,50})',

            # Linhas que começam com bullet points e têm lugares
            r'[•\-\*]\s+([A-ZÀ-Ú][A-Za-zÀ-ú\'\-]+(?:\s+[A-Za-zÀ-ú\'\-]+){1,5})\s*(?:\(|:|\-|–)',
        ]

        points = set()

        for pattern in patterns:
            matches = re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE)
            for match in matches:
                point = match.group(1).strip()

                # Limpar o ponto extraído
                point = re.sub(r'\s+', ' ', point)  # Normalizar espaços
                point = point.strip('.,;:!?')  # Remover pontuação no final

                # Filtros de qualidade
                if len(point) < 4:  # Muito curto
                    continue
                if len(point) > 60:  # Muito longo
                    continue
                if point.lower() == destination.lower():  # É o próprio destino
                    continue
                if point.lower() in ['manhã', 'tarde', 'noite', 'dia', 'hora', 'horas', 'minutos']:
                    continue

                # Validar que tem pelo menos uma letra maiúscula (nome próprio)
                if not any(c.isupper() for c in point):
                    continue

                points.add(point)
                print(f"[DEBUG] POI encontrado: '{point}'")

        points_list = list(points)[:10]  # Limitar a 10 pontos
        print(f"[DEBUG] Total de {len(points_list)} pontos de interesse extraídos")
        return points_list

    except Exception as e:
        print(f"[ERROR] Erro ao extrair pontos de interesse: {e}")
        import traceback
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        return []

def geocode_location(location, city=None):
    """
    Obtém coordenadas (lat, lng) de um local usando geocoding
    SEMPRE usa a cidade como contexto para garantir precisão
    """
    try:
        geolocator = Nominatim(user_agent="atlas_travel_app", timeout=15)

        # SEMPRE incluir cidade para contexto preciso
        if city:
            # Primeira tentativa: local completo com cidade
            query = f"{location}, {city}"
            print(f"[DEBUG] Geocodificando: '{query}'")

            time.sleep(1)  # Rate limiting mais conservador para Nominatim
            location_data = geolocator.geocode(query, exactly_one=True, addressdetails=True)

            if location_data:
                print(f"[DEBUG] ✓ Encontrado: {location_data.address} @ ({location_data.latitude}, {location_data.longitude})")
                return {
                    "name": location,
                    "lat": location_data.latitude,
                    "lng": location_data.longitude,
                    "display_name": location_data.address
                }

            # Segunda tentativa: buscar apenas o local e filtrar por cidade
            print(f"[DEBUG] Tentativa 2: Buscando '{location}' e filtrando por proximidade")
            time.sleep(1)
            results = geolocator.geocode(location, exactly_one=False, addressdetails=True, limit=5)

            if results:
                # Pegar o resultado que menciona a cidade no endereço
                for result in results:
                    address = result.address.lower() if hasattr(result, 'address') else ''
                    if city.lower() in address:
                        print(f"[DEBUG] ✓ Encontrado por filtro: {result.address}")
                        return {
                            "name": location,
                            "lat": result.latitude,
                            "lng": result.longitude,
                            "display_name": result.address
                        }

        else:
            # Sem cidade de contexto - geocode direto
            print(f"[DEBUG] Geocodificando sem contexto: '{location}'")
            time.sleep(1)
            location_data = geolocator.geocode(location, timeout=10)

            if location_data:
                return {
                    "name": location,
                    "lat": location_data.latitude,
                    "lng": location_data.longitude,
                    "display_name": location_data.address
                }

        print(f"[WARN] Não foi possível geocodificar: {location}")
        return None

    except Exception as e:
        print(f"[ERROR] Erro ao geocodificar '{location}': {e}")
        return None

def get_map_data(destination, points_of_interest):
    """
    Gera dados do mapa para exibição no frontend
    """
    try:
        print(f"[DEBUG] Gerando dados do mapa para {destination}")

        # Geocodificar destino principal
        destination_coords = geocode_location(destination)
        if not destination_coords:
            print(f"[WARN] Não foi possível geocodificar o destino: {destination}")
            return None

        map_data = {
            "center": {
                "lat": destination_coords["lat"],
                "lng": destination_coords["lng"]
            },
            "destination": destination,
            "markers": [
                {
                    "name": destination,
                    "lat": destination_coords["lat"],
                    "lng": destination_coords["lng"],
                    "type": "destination",
                    "description": f"Destino principal: {destination}"
                }
            ]
        }

        # Geocodificar pontos de interesse
        for i, poi in enumerate(points_of_interest[:8]):  # Limitar a 8 para não sobrecarregar
            poi_coords = geocode_location(poi, destination)
            if poi_coords:
                map_data["markers"].append({
                    "name": poi,
                    "lat": poi_coords["lat"],
                    "lng": poi_coords["lng"],
                    "type": "poi",
                    "description": poi_coords.get("display_name", poi)
                })
                print(f"[DEBUG] POI geocodificado: {poi}")

        print(f"[DEBUG] Mapa gerado com {len(map_data['markers'])} marcadores")
        return map_data

    except Exception as e:
        print(f"[ERROR] Erro ao gerar dados do mapa: {e}")
        import traceback
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        return None

def clean_double_formatting(content):
    """Remove formatação dupla de mensagens que foram formatadas múltiplas vezes"""
    if not content or not isinstance(content, str):
        return content or ""
    
    # Remove múltiplos <br> consecutivos
    content = re.sub(r'(<br>){3,}', '<br><br>', content)
    
    # Remove espaços desnecessários entre tags
    content = re.sub(r'<br>\s*<br>\s*<br>', '<br><br>', content)
    
    # Corrige parágrafos que foram unidos incorretamente
    # Procura por padrões como "palavra<br><strong>Palavra" e adiciona quebra
    content = re.sub(r'([a-záàâãéêíóôõúç])<br>(<strong>|<h3>)', r'\1<br><br>\2', content, flags=re.IGNORECASE)
    
    # Corrige listas que perderam formatação
    content = re.sub(r'<br>(\*\s+)', r'<br><br>\1', content)
    
    # Adiciona quebras antes de títulos que estão grudados
    content = re.sub(r'([.!?])\s*(<h3>)', r'\1<br><br>\2', content)
    
    # Adiciona quebras antes de listas que estão grudadas
    content = re.sub(r'([.!?])\s*(<li>)', r'\1<br><br>\2', content)
    
    # Adiciona quebras antes de parágrafos em negrito que estão grudados
    content = re.sub(r'([.!?])\s*(<strong>)', r'\1<br><br>\2', content)
    
    # Separa seções que estão muito próximas
    content = re.sub(r'(<\/h3>)([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ])', r'\1<br><br>\2', content)
    content = re.sub(r'(<\/strong>)([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ])', r'\1<br><br>\2', content)
    content = re.sub(r'(<\/ul>)([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ])', r'\1<br><br>\2', content)
    
    return content

def format_message_content(content):
    # Copia a função completa do app.py original
    try:
        if not content or not isinstance(content, str):
            return content or ""
        
        # Verifica se já contém tags HTML (já foi formatado)
        html_tags = ['<div', '<html', '<body', '<h3', '<ul', '<br>', '<strong>', '<em>', '<li>', '&nbsp;']
        if any(tag in content for tag in html_tags):
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

        content = re.sub(r'^##\s*(.+)$', r'<br><h3>\1</h3>', content, flags=re.MULTILINE)
        content = re.sub(r'\*\*(.+?)\*\*', r'<br><strong>\1</strong>', content)
        # Itens de lista com '* ', '- ' e '1. ' (permitindo espaços iniciais) e evitando bullets vazios
        content = re.sub(r'^\s*\*\s+(\S.+)$', r'<li>\1</li>', content, flags=re.MULTILINE)
        content = re.sub(r'^\s*-\s+(\S.+)$', r'<li>\1</li>', content, flags=re.MULTILINE)
        content = re.sub(r'^\d+\.\s+(\S.+)$', r'<li>\1</li>', content, flags=re.MULTILINE)
        
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
                    formatted_lines.append('<ul>')
                    formatted_lines.extend(list_items)
                    formatted_lines.append('</ul>')
                    in_list = False
                    list_items = []
                formatted_lines.append(line)

        if in_list and list_items:
            formatted_lines.append('<ul>')
            formatted_lines.extend(list_items)
            formatted_lines.append('</ul>')

        content = '\n'.join(formatted_lines)
        # Primeiro transforma blocos de múltiplas quebras de linha em espaçamento menor
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
        print("[DEBUG] ===== INICIANDO CARREGAMENTO DO HISTÓRICO =====")
        user_id = get_current_user_id()
        print(f"[DEBUG] User ID: {user_id}")

        if not user_id:
            print("[ERROR] User ID não encontrado")
            return redirect(url_for('login'))

        print("[DEBUG] Buscando conversas do usuário...")
        conversations = Conversation.get_user_conversations(user_id)
        print(f"[DEBUG] Conversas encontradas: {len(conversations) if conversations else 0}")

        # Adiciona informações de timestamp para cada conversa
        for conv in conversations:
            if 'created_at' in conv and conv['created_at']:
                from datetime import datetime
                if isinstance(conv['created_at'], str):
                    try:
                        conv['timestamp'] = datetime.fromisoformat(conv['created_at'].replace('Z', '+00:00'))
                    except:
                        conv['timestamp'] = datetime.now()
                else:
                    conv['timestamp'] = conv['created_at']
            else:
                from datetime import datetime
                conv['timestamp'] = datetime.now()

        print("[DEBUG] Renderizando template historico.html")
        return render_template('historico.html', conversations=conversations)
    except Exception as e:
        print(f"[ERROR] Erro ao carregar histórico: {e}")
        import traceback
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        return render_template('historico.html', conversations=[])

@app.route('/conversation/<int:conversation_id>')
@login_required
def view_conversation(conversation_id):
    user_id = get_current_user_id()
    user = User.get_current_user()
    conversation = Conversation.get_conversation_with_messages(conversation_id, user_id)

    if not conversation:
        return redirect(url_for('historico'))

    # Formata as mensagens
    for message in conversation.get('messages', []):
        if message.get('is_bot'):
            # Verifica se a mensagem já foi formatada (contém tags HTML)
            content = message['content']
            has_html_tags = any(tag in content for tag in ['<div', '<html', '<body', '<h3', '<ul', '<br>', '<strong>', '<em>', '<li>', '&nbsp;'])
            
            if has_html_tags:
                # Se já tem HTML, limpa formatação dupla
                message['content'] = clean_double_formatting(content)
            else:
                # Se não tem HTML, aplica formatação
                message['content'] = format_message_content(message['content'])

    return render_template('chat.html', conversation=conversation, is_logged_in=True, user=user)

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
        
        # Gerar dados do mapa em background (não bloqueia resposta)
        map_data = None
        try:
            # Extrair cidade principal do roteiro para usar na geocodificação
            cidade_principal_mapa, codigo_iata_mapa = extract_main_city_from_itinerary(bot_response, destination, origin)
            destino_para_mapa = cidade_principal_mapa if cidade_principal_mapa else destination
            
            print(f"[DEBUG] Tentando gerar mapa para: {destino_para_mapa} (extraído do roteiro)")
            points = extract_points_of_interest(bot_response, destino_para_mapa)
            if points:
                print(f"[DEBUG] Pontos extraídos do roteiro: {points}")
                map_data = get_map_data(destino_para_mapa, points)
                if map_data:
                    print(f"[DEBUG] Mapa gerado com sucesso!")
        except Exception as map_error:
            print(f"[WARN] Erro ao gerar mapa (não crítico): {map_error}")

        response_data = {
            'success': True,
            'conversation_id': conversation['id'] if conversation else None,
            'title': conversation['title'] if conversation else generate_conversation_title(message),
            'user_message': message,
            'bot_response': formatted_response,
            'is_logged_in': is_logged_in,
            'requires_login': not is_logged_in,  # Flag para mostrar aviso de login
            'map_data': map_data  # Dados do mapa (pode ser None)
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

@app.route('/api/map_data', methods=['POST'])
def api_map_data():
    """API para gerar dados do mapa com base em um destino e pontos de interesse"""
    try:
        data = request.get_json()
        destination = data.get('destination', '').strip()
        bot_response = data.get('bot_response', '')

        if not destination:
            return jsonify({"success": False, "error": "Destino não informado"}), 400

        # Extrair cidade principal do roteiro para usar na geocodificação
        destino_para_mapa = destination
        if bot_response:
            try:
                cidade_principal_mapa, codigo_iata_mapa = extract_main_city_from_itinerary(bot_response, destination)
                if cidade_principal_mapa:
                    destino_para_mapa = cidade_principal_mapa
                    print(f"[DEBUG] Cidade específica extraída do roteiro: {cidade_principal_mapa}")
            except Exception as e:
                print(f"[WARN] Erro ao extrair cidade do roteiro: {e}")
        
        print(f"[DEBUG] Gerando mapa para: {destino_para_mapa}")

        # Extrair pontos de interesse do roteiro (se fornecido)
        points_of_interest = []
        if bot_response:
            points_of_interest = extract_points_of_interest(bot_response, destino_para_mapa)
            print(f"[DEBUG] Pontos extraídos: {points_of_interest}")

        # Gerar dados do mapa
        map_data = get_map_data(destino_para_mapa, points_of_interest)

        if not map_data:
            return jsonify({
                "success": False,
                "error": "Não foi possível gerar o mapa para este destino"
            }), 404

        return jsonify({
            "success": True,
            "map_data": map_data
        })

    except Exception as e:
        print(f"[ERROR] Erro na API de mapa: {e}")
        import traceback
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/images/<path:filename>')
def serve_image(filename):
    """Serve arquivos da pasta images"""
    return send_from_directory('images', filename)

if __name__ == '__main__':
    app.run(debug=True, port=8000)
