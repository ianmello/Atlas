from flask import Flask, request, jsonify, render_template, session, redirect, url_for
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
from models import db, Conversation, Message, generate_conversation_title

app = Flask(__name__)
app.config["SESSION_PERMANENT"] = True
app.config["SESSION_TYPE"] = "filesystem"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=1)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///atlas.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.secret_key = os.getenv("SECRET_KEY", "chave_secreta_temporaria")

db.init_app(app)
Session(app)

# Criar as tabelas do banco de dados
with app.app_context():
    try:
        print("Criando/verificando banco de dados...")
        db.create_all()
        print("Banco de dados criado/verificado com sucesso!")
    except Exception as e:
        print(f"Erro ao criar banco de dados: {e}")

warnings.filterwarnings("ignore")
load_dotenv()

EXCHANGE_API_URL = "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoMoedaDia(moeda=@moeda,dataCotacao=@dataCotacao)"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
FLIGHT_API_URL = "https://test.api.amadeus.com/v2/shopping/flight-offers"
HOTEL_API_URL = "https://test.api.amadeus.com/v1/reference-data/locations/hotels/by-city"
WEATHER_API_URL = "https://api.openweathermap.org/data/2.5/forecast"
WEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

chat_context = {}

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

# Mapeamento de cidades para códigos IATA
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

# Lista de palavras para descartar após a extração
PALAVRAS_DESCARTAR = [
    "para", "até", "e", "com", "por", "durante", "no", "na", "do", "da", "dos", "das", 
    "de", "em", "ao", "aos", "às", "as", "os", "o", "a", "um", "uma", "uns", "umas"
]

def limpar_nome_cidade(texto):
    palavras = texto.strip().split()
    resultado = []
    for palavra in palavras:
        if palavra.lower() not in PALAVRAS_DESCARTAR:
            resultado.append(palavra)
        else:
            break  # Para na primeira preposição/conector
    return " ".join(resultado)

def get_exchange_rate(currency: str = "USD") -> float:
    try:
        today = datetime.now().strftime("%m-%d-%Y")
        params = {
            "@moeda": f"'{currency}'",
            "@dataCotacao": f"'{today}'",
            "$format": "json"
        }
        response = requests.get(EXCHANGE_API_URL, params=params)
        data = response.json()
        return float(data['value'][0]['cotacaoVenda'])
    except:
        return 5.0

def get_ai_response(messages):
    try:
        last_message = messages[-1]["content"].lower()
        origem = extrair_origem(last_message)
        destino = extrair_destino(last_message)
        datas = extrair_datas(last_message)

        roteiro = ""
        # Sempre gera um roteiro com Gemini primeiro
        headers = {"Content-Type": "application/json"}
        if GEMINI_API_KEY:
            url = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"
            data = {
                "contents": [
                    {"role": m["role"], "parts": [{"text": m["content"]}]} for m in messages
                ]
            }
            response = requests.post(url, headers=headers, data=json.dumps(data))
            if response.status_code == 200:
                resposta = response.json()
                try:
                    roteiro = resposta["candidates"][0]["content"]["parts"][0]["text"]
                except Exception as e:
                    roteiro = "Desculpe, não consegui gerar um roteiro agora."
            else:
                roteiro = "Desculpe, não consegui gerar um roteiro agora."
        else:
            roteiro = "Desculpe, a chave da API Gemini não está configurada."

        # Se tem origem e destino válidos, busca voos e adiciona ao roteiro
        if origem != "Origem não informada" and destino != "Destino não informado":
            origem_iata = buscar_codigo_iata(origem)
            destino_iata = buscar_codigo_iata(destino)
            voos = get_flights(origem_iata, destino_iata, datas.get('data_inicio'))
            if voos and 'data' in voos and voos['data']:
                roteiro += "\n\n---\n\n" + format_flights_response(voos['data'])

        return roteiro

    except Exception as e:
        print(f"[ERROR] Erro ao processar mensagem: {str(e)}")
        return "Desculpe, ocorreu um erro ao processar sua mensagem."

def format_flights_response(flights):
    """Formata a resposta dos voos de forma mais amigável, mostrando conexões"""
    if not flights:
        return "Desculpe, não encontrei voos disponíveis para esta rota."
    
    response = "Encontrei os seguintes voos disponíveis:\n\n"
    
    for i, flight in enumerate(flights, 1):
        response += f"• Voo {i}: {format_price(flight['price'])}\n"
        segments = flight['itineraries'][0]['segments']
        for idx, segment in enumerate(segments):
            departure = datetime.fromisoformat(segment['departure']['at'].replace('Z', '+00:00'))
            arrival = datetime.fromisoformat(segment['arrival']['at'].replace('Z', '+00:00'))
            if idx == 0:
                response += f"  Partida de {segment['departure']['iataCode']}: {departure.strftime('%d/%m/%Y às %H:%M')}\n"
                response += f"  Chegada em {segment['arrival']['iataCode']}: {arrival.strftime('%d/%m/%Y às %H:%M')}\n"
            else:
                response += f"  --- CONEXÃO ---\n"
                response += f"  Partida de {segment['departure']['iataCode']}: {departure.strftime('%d/%m/%Y às %H:%M')}\n"
                response += f"  Chegada em {segment['arrival']['iataCode']}: {arrival.strftime('%d/%m/%Y às %H:%M')}\n"
        response += "\n"
    return response

def buscar_codigo_iata(nome_destino: str) -> str:
    """Retorna o código IATA para a cidade especificada"""
    try:
        nome_normalizado = nome_destino.lower().strip()
        
        # Verifica na lista de códigos conhecidos
        if nome_normalizado in CITY_IATA_CODES:
            return CITY_IATA_CODES[nome_normalizado]
        
        # Tenta encontrar uma correspondência parcial
        for cidade, codigo in CITY_IATA_CODES.items():
            if nome_normalizado in cidade or cidade in nome_normalizado:
                return codigo
            
        # Fallback para a API da Amadeus
        auth_url = "https://test.api.amadeus.com/v1/security/oauth2/token"
        auth_data = {
            "grant_type": "client_credentials",
            "client_id": os.getenv("AMADEUS_CLIENT_ID"),
            "client_secret": os.getenv("AMADEUS_CLIENT_SECRET")
        }
        auth_response = requests.post(auth_url, data=auth_data, verify=False)
        token = auth_response.json().get("access_token")

        params = {
            "keyword": nome_destino,
            "subType": "CITY",
            "max": 1
        }
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get("https://test.api.amadeus.com/v1/reference-data/locations", headers=headers, params=params, verify=False)

        results = response.json().get("data", [])
        if results and "iataCode" in results[0]:
            codigo_iata = results[0]["iataCode"]
            print(f"API Amadeus encontrou código IATA para {nome_destino}: {codigo_iata}")
            return codigo_iata
        
        # Se não encontrou na API, tenta fazer uma busca mais genérica
        # Muitas vezes a API requer nomes específicos em inglês
        params["keyword"] = nome_destino.split()[0]  # Usa apenas a primeira palavra
        response = requests.get("https://test.api.amadeus.com/v1/reference-data/locations", headers=headers, params=params, verify=False)
        
        results = response.json().get("data", [])
        if results and "iataCode" in results[0]:
            codigo_iata = results[0]["iataCode"]
            print(f"API Amadeus encontrou código IATA usando busca parcial para {nome_destino}: {codigo_iata}")
            return codigo_iata
            
        # Último recurso: retorna um código padrão para cidades grandes internacionais
        cidades_grandes = {
            "franca": "CDG",  # Paris, França
            "frança": "CDG",
            "estados unidos": "JFK",  # Nova York, EUA
            "eua": "JFK",
            "irlanda": "DUB",
            "dublin": "DUB",
            "italia": "FCO",  # Roma, Itália
            "itália": "FCO",
            "japao": "HND",  # Tóquio, Japão
            "japão": "HND",
            "espanha": "MAD",  # Madrid, Espanha
            "alemanha": "FRA",  # Frankfurt, Alemanha
            "portugal": "LIS",  # Lisboa, Portugal
            "canada": "YYZ",  # Toronto, Canadá
            "canadá": "YYZ",
            "china": "PEK",  # Pequim, China
            "australia": "SYD",  # Sydney, Austrália
            "austrália": "SYD"
        }
        
        for pais, codigo in cidades_grandes.items():
            if pais in nome_normalizado:
                return codigo
                
        # Se nada encontrado, retorna as três primeiras letras da cidade
        return nome_destino[:3].upper()
    except Exception as e:
        print(f"Erro ao buscar código IATA: {e}")
        return nome_destino[:3].upper()

def get_flights(origin: str, destination: str, date: str):
    """Busca voos entre origem e destino na data especificada"""
    try:
        print(f"[DEBUG] get_flights chamada com: origem={origin}, destino={destination}, data={date}")
        
        # Verifica se as credenciais da API estão configuradas
        client_id = os.getenv("AMADEUS_CLIENT_ID")
        client_secret = os.getenv("AMADEUS_CLIENT_SECRET")
        
        if not client_id or not client_secret:
            print("[ERROR] Credenciais da API Amadeus não configuradas")
            return {"data": [], "error": "Credenciais da API não configuradas"}
        
        # Verifica se os códigos são válidos
        if not origin or not destination:
            print(f"[ERROR] Códigos IATA inválidos ou vazios: origem={origin}, destino={destination}")
            return {"data": [], "error": "Códigos IATA inválidos"}
            
        # Garante que os códigos estão no formato correto (3 letras maiúsculas)
        origin = origin.strip().upper()
        destination = destination.strip().upper()
        
        if len(origin) != 3 or len(destination) != 3:
            print(f"[ERROR] Códigos IATA com tamanho incorreto: origem={origin} ({len(origin)}), destino={destination} ({len(destination)})")
            return {"data": [], "error": "Formato de código IATA inválido"}
            
        # Verifica se a data está no formato correto
        try:
            parsed_date = datetime.strptime(date, "%Y-%m-%d")
            # Verifica se a data não é no passado
            if parsed_date.date() < datetime.now().date():
                print(f"[ERROR] Data no passado: {date}")
                data_atual = datetime.now() + timedelta(days=7)
                date = data_atual.strftime("%Y-%m-%d")
                print(f"[DEBUG] Ajustando para data futura: {date}")
        except ValueError:
            print(f"[ERROR] Formato de data inválido: {date}")
            data_atual = datetime.now() + timedelta(days=7)
            date = data_atual.strftime("%Y-%m-%d")
            print(f"[DEBUG] Usando data padrão: {date}")
        
        print(f"[DEBUG] Buscando voos: {origin} -> {destination}, data: {date}")
        
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
            print(f"[ERROR] Erro na autenticação com a API Amadeus: {str(e)}")
            return {"data": [], "error": "Erro de autenticação na API"}
            
        if auth_response.status_code != 200:
            print(f"[ERROR] Erro na autenticação com a API Amadeus: {auth_response.text}")
            return {"data": [], "error": "Erro de autenticação na API"}
            
        token = auth_response.json().get("access_token")
        if not token:
            print("[ERROR] Token de acesso não encontrado na resposta de autenticação")
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
            print(f"[ERROR] Erro na requisição de voos: {str(e)}")
            return {"data": [], "error": "Erro na busca de voos"}
        
        print(f"[DEBUG] Resposta da API de voos: {response.status_code}")
        print(f"[DEBUG] Conteúdo da resposta: {response.text[:500]}...")
        
        if response.status_code != 200:
            print(f"[ERROR] Erro na API de voos: {response.status_code} - {response.text}")
            return {"data": [], "error": "Erro na API de voos"}
            
        result = response.json()
        
        if "data" not in result or not result["data"]:
            print(f"[DEBUG] Resposta da API sem dados de voos: {result}")
            # Tentativa alternativa: inverter origem e destino para testar
            params["originLocationCode"], params["destinationLocationCode"] = params["destinationLocationCode"], params["originLocationCode"]
            print(f"[DEBUG] Tentando busca invertida: {params['originLocationCode']} -> {params['destinationLocationCode']}")
            
            try:
                alt_response = requests.get(FLIGHT_API_URL, headers=headers, params=params, verify=False, timeout=15)
                if alt_response.status_code == 200:
                    alt_result = alt_response.json()
                    if "data" in alt_result and alt_result["data"]:
                        print("[DEBUG] Busca invertida encontrou voos!")
                        return alt_result
            except requests.exceptions.RequestException as e:
                print(f"[ERROR] Erro na busca invertida: {str(e)}")
        
        # Formata os preços antes de retornar
        if "data" in result:
            for voo in result["data"]:
                if "price" in voo:
                    voo["price"]["formatted"] = format_price(voo["price"])
        
        return result
    except Exception as e:
        print(f"[ERROR] Erro ao buscar voos: {str(e)}")
        return {"data": [], "error": str(e)}

def buscar_hoteis(cidade_codigo: str):
    try:
        if not cidade_codigo or len(cidade_codigo.strip()) != 3:
            print(f"Código IATA inválido para buscar hotéis: {cidade_codigo}")
            return []
            
        auth_url = "https://test.api.amadeus.com/v1/security/oauth2/token"
        auth_data = {
            "grant_type": "client_credentials",
            "client_id": os.getenv("AMADEUS_CLIENT_ID"),
            "client_secret": os.getenv("AMADEUS_CLIENT_SECRET")
        }
        auth_response = requests.post(auth_url, data=auth_data, verify=False)
        if auth_response.status_code != 200:
            print(f"Erro na autenticação para busca de hotéis: {auth_response.text}")
            return []
            
        token = auth_response.json().get("access_token")
        if not token:
            print("Token de acesso não encontrado para busca de hotéis")
            return []

        # Primeiro busca os hotéis disponíveis
        params = {
            "cityCode": cidade_codigo.upper().strip(),
            "radius": 5,
            "radiusUnit": "KM",
            "ratings": "3,4,5",
            "hotelSource": "ALL"
        }
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(HOTEL_API_URL, headers=headers, params=params, verify=False)
        
        if response.status_code != 200:
            print(f"Erro na API de hotéis: {response.status_code} - {response.text}")
            return []
            
        hoteis = response.json().get("data", [])[:5]  # Obtém até 5 hotéis
        print(f"Encontrados {len(hoteis)} hotéis para {cidade_codigo}")
        
        # Busca os preços dos hotéis
        # Define o período para busca de preços (7 dias a partir de hoje)
        hoje = datetime.now()
        data_checkin = (hoje + timedelta(days=7)).strftime("%Y-%m-%d")
        data_checkout = (hoje + timedelta(days=10)).strftime("%Y-%m-%d")
        
        # Para cada hotel, tenta obter informações de preços
        for hotel in hoteis:
            try:
                hotel_id = hotel.get("hotelId")
                if not hotel_id:
                    hotel["preco"] = "Preço não disponível"
                    continue
                
                # URL para buscar ofertas de hotéis
                hotel_offers_url = f"https://test.api.amadeus.com/v3/shopping/hotel-offers"
                params = {
                    "hotelIds": hotel_id,
                    "adults": 2,
                    "checkInDate": data_checkin,
                    "checkOutDate": data_checkout,
                    "roomQuantity": 1,
                    "currency": "USD"
                }
                
                offers_response = requests.get(hotel_offers_url, headers=headers, params=params, verify=False)
                
                if offers_response.status_code == 200:
                    ofertas = offers_response.json().get("data", [])
                    if ofertas and "offers" in ofertas[0] and ofertas[0]["offers"]:
                        preco_total = ofertas[0]["offers"][0].get("price", {}).get("total")
                        if preco_total:
                            # Converte para reais
                            preco_brl = float(preco_total) * get_exchange_rate("USD")
                            hotel["preco"] = f"R$ {preco_brl:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                        else:
                            hotel["preco"] = "Preço não disponível"
                    else:
                        hotel["preco"] = "Sem ofertas disponíveis"
                else:
                    hotel["preco"] = "Preço não disponível"
                    
            except Exception as e:
                print(f"Erro ao buscar preço para hotel {hotel.get('name')}: {e}")
                hotel["preco"] = "Preço não disponível"
        
        return hoteis
    except Exception as e:
        print(f"Erro ao buscar hotéis: {e}")
        return []

def obter_previsao_tempo(cidade: str, data_inicio=None, data_fim=None):
    try:
        coords = CITY_COORDINATES.get(cidade.lower())
        if not coords:
            return None
        
        lat, lon = coords
        params = {
            "lat": lat,
            "lon": lon,
            "appid": WEATHER_API_KEY,
            "units": "metric",
            "lang": "pt_br"
        }
        
        response = requests.get(WEATHER_API_URL, params=params)
        data = response.json()
        
        # Filtra apenas os dias relevantes se datas fornecidas
        if data_inicio and data_fim:
            data_inicio = datetime.strptime(data_inicio, "%Y-%m-%d")
            data_fim = datetime.strptime(data_fim, "%Y-%m-%d")
            previsao_filtrada = []
            
            for p in data.get("list", []):
                data_previsao = datetime.fromtimestamp(p.get("dt"))
                if data_inicio <= data_previsao <= data_fim and data_previsao.hour == 12:  # previsão do meio-dia
                    previsao_filtrada.append({
                        "data": data_previsao.strftime("%d/%m"),
                        "temperatura": round(p.get("main", {}).get("temp")),
                        "descricao": p.get("weather", [{}])[0].get("description", "")
                    })
            
            return previsao_filtrada
        
        return None
    except Exception as e:
        print(f"Erro ao obter previsão do tempo: {e}")
        return None

def format_price(price_data):
    """Formata o preço do voo em reais com base no valor em dólares"""
    try:
        # Verifica se há dados de preço válidos
        if not price_data or not isinstance(price_data, dict):
            return "Preço não disponível"
            
        # Extrai o valor total do preço
        total = price_data.get("total")
        if not total:
            return "Preço não disponível"
            
        # Converte para float se for string
        if isinstance(total, str):
            try:
                total = float(total)
            except ValueError:
                return "Preço não disponível"
        
        # Converte para real usando a taxa de câmbio atual
        cotacao_dolar = get_exchange_rate("USD")
        preco_brl = float(total) * cotacao_dolar
        
        # Formata o preço em reais
        valor_formatado = f"R$ {preco_brl:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        print(f"Preço formatado: {valor_formatado} (Original: {total} USD, Cotação: {cotacao_dolar})")
        return valor_formatado
    except Exception as e:
        print(f"Erro ao formatar preço: {e}")
        return "Preço não disponível"

def extrair_destino(texto: str) -> str:
    try:
        print(f"[DEBUG] Extraindo destino do texto: {texto}")
        padroes = [
            # Padrão para "para [destino]"
            r'(?:roteiro|viagem|viajar|ir)\s+para\s+([A-Za-zÀ-ÿ\s]+?)(?:\s+saindo|\s+partindo|\s+no dia|\s+em|\s+com|\s+por|\s+durante|\s*$|,)',
            # Padrão para "em [destino]"
            r'(?:roteiro|viagem|viajar)\s+(?:em|no|na|para)\s+([A-Za-zÀ-ÿ\s]+?)(?:\s+saindo|\s+partindo|\s+no dia|\s+em|\s+com|\s+por|\s+durante|\s*$|,)',
            # Padrão para "conhecer [destino]"
            r'conhecer\s+([A-Za-zÀ-ÿ\s]+?)(?:\s+saindo|\s+partindo|\s+no dia|\s+em|\s+com|\s+por|\s+durante|\s*$|,)',
            # Padrão para "visitar [destino]"
            r'visitar\s+([A-Za-zÀ-ÿ\s]+?)(?:\s+saindo|\s+partindo|\s+no dia|\s+em|\s+com|\s+por|\s+durante|\s*$|,)',
            # Padrão para "para [destino] saindo de [origem]"
            r'para\s+([A-Za-zÀ-ÿ\s]+?)\s+saindo\s+de',
            # Padrão para "de [origem] para [destino]"
            r'de\s+[A-Za-zÀ-ÿ\s]+?\s+para\s+([A-Za-zÀ-ÿ\s]+?)(?:\s+no dia|\s+em|\s+com|\s+por|\s+durante|\s*$|,)'
        ]
        
        # Lista de palavras que não podem ser destinos
        palavras_invalidas = ['casal', 'familia', 'amigos', 'sozinho', 'grupo', 'dias', 'semanas', 'meses', 'voos', 'roteiro', 'viagem']
        
        for padrao in padroes:
            match = re.search(padrao, texto, re.IGNORECASE)
            if match:
                destino = match.group(1).strip()
                # Verifica se o destino encontrado não é uma palavra inválida
                if destino.lower() not in palavras_invalidas:
                    print(f"[DEBUG] Destino encontrado com padrão '{padrao}': {destino}")
                    return destino
                else:
                    print(f"[DEBUG] Destino encontrado '{destino}' é uma palavra inválida, continuando busca...")
                    continue
                    
        # Se não encontrou com os padrões principais, tenta encontrar qualquer menção a país/cidade conhecida
        paises_cidades = [
            'estados unidos', 'frança', 'italia', 'espanha', 'portugal', 'alemanha', 
            'japão', 'china', 'brasil', 'argentina', 'chile', 'peru', 'mexico',
            'são paulo', 'rio de janeiro', 'paris', 'londres', 'tokyo', 'nova york',
            'miami', 'orlando', 'lisboa', 'madrid', 'barcelona', 'roma', 'los angeles',
            'massachussets', 'campinas', 'sorocaba'
        ]
        
        for local in paises_cidades:
            if local in texto.lower():
                print(f"[DEBUG] Destino encontrado por menção direta: {local}")
                return local.title()
                
        print("[DEBUG] Nenhum destino válido encontrado")
        return "Destino não informado"
    except Exception as e:
        print(f"[ERROR] Erro ao extrair destino: {str(e)}")
        return "Destino não informado"

def extrair_origem(texto: str) -> str:
    try:
        print(f"[DEBUG] Extraindo origem do texto: {texto}")
        padroes = [
            r'saindo de\s+([A-Za-zÀ-ÿ\s]+?)(?:\s+para|\s+no dia|\s+em|\s+e|\s+com|\s+por|\s+durante|\s*$|,)',
            r'partindo de\s+([A-Za-zÀ-ÿ\s]+?)(?:\s+para|\s+no dia|\s+em|\s+e|\s+com|\s+por|\s+durante|\s*$|,)',
            r'desde\s+([A-Za-zÀ-ÿ\s]+?)(?:\s+para|\s+no dia|\s+em|\s+e|\s+com|\s+por|\s+durante|\s*$|,)',
            r'de\s+([A-Za-zÀ-ÿ\s]+?)\s+(?:para|até|no dia)',
            # Padrão para "de [origem] para [destino]"
            r'de\s+([A-Za-zÀ-ÿ\s]+?)\s+para\s+[A-Za-zÀ-ÿ\s]+'
        ]
        
        # Lista de palavras que não podem ser origens
        palavras_invalidas = ['casal', 'familia', 'amigos', 'sozinho', 'grupo', 'dias', 'semanas', 'meses', 'voos', 'roteiro', 'viagem']
        
        for padrao in padroes:
            match = re.search(padrao, texto, re.IGNORECASE)
            if match:
                origem = limpar_nome_cidade(match.group(1))
                # Verifica se a origem encontrada não é uma palavra inválida
                if origem.lower() not in palavras_invalidas:
                    print(f"[DEBUG] Origem encontrada com padrão '{padrao}': {origem}")
                    return origem
                else:
                    print(f"[DEBUG] Origem encontrada '{origem}' é uma palavra inválida, continuando busca...")
                    continue
        
        # Se não encontrou com os padrões principais, tenta encontrar qualquer menção a cidade brasileira conhecida
        cidades_br = [
            'são paulo', 'rio de janeiro', 'brasília', 'curitiba', 'florianópolis',
            'salvador', 'recife', 'fortaleza', 'manaus', 'belém', 'porto alegre',
            'belo horizonte', 'vitória', 'natal', 'joão pessoa', 'campinas', 'sorocaba'
        ]
        
        for cidade in cidades_br:
            if cidade in texto.lower():
                print(f"[DEBUG] Origem encontrada por menção direta: {cidade}")
                return cidade.title()
                
        print("[DEBUG] Nenhuma origem válida encontrada")
        return "Origem não informada"
    except Exception as e:
        print(f"[ERROR] Erro ao extrair origem: {str(e)}")
        return "Origem não informada"

def extrair_datas(texto: str):
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
    
    # Padrão para datas como "15 de janeiro" ou "15/01" ou "15-01"
    padrao_data = r'(\d{1,2})(?:\s+de\s+([a-zç]+)|[/-](\d{1,2}))'
    
    resultado = {"data_inicio": None, "data_fim": None}
    
    # Busca por datas específicas
    padrao_periodo = r'(?:de|entre)\s+(\d{1,2}(?:\s+de\s+[a-zç]+|\d{1,2}[/-]\d{1,2}))\s+(?:a|até|e)\s+(\d{1,2}(?:\s+de\s+[a-zç]+|\d{1,2}[/-]\d{1,2}))'
    
    match_periodo = re.search(padrao_periodo, texto, re.IGNORECASE)
    if match_periodo:
        data_inicio_texto = match_periodo.group(1)
        data_fim_texto = match_periodo.group(2)
        
        # Processar data de início
        match_inicio = re.search(padrao_data, data_inicio_texto, re.IGNORECASE)
        if match_inicio:
            dia = match_inicio.group(1).zfill(2)
            if match_inicio.group(2):  # Formato "15 de janeiro"
                mes = meses.get(match_inicio.group(2).lower(), '01')
            else:  # Formato "15/01"
                mes = match_inicio.group(3).zfill(2)
            
            ano_atual = datetime.now().year
            resultado["data_inicio"] = f"{ano_atual}-{mes}-{dia}"
        
        # Processar data de fim
        match_fim = re.search(padrao_data, data_fim_texto, re.IGNORECASE)
        if match_fim:
            dia = match_fim.group(1).zfill(2)
            if match_fim.group(2):  # Formato "15 de janeiro"
                mes = meses.get(match_fim.group(2).lower(), '01')
            else:  # Formato "15/01"
                mes = match_fim.group(3).zfill(2)
            
            ano_atual = datetime.now().year
            resultado["data_fim"] = f"{ano_atual}-{mes}-{dia}"
    
    # Se não encontrou período específico, tenta extrair a duração
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

def obter_coordenadas(cidade: str):
    """Obtém as coordenadas de uma cidade usando múltiplas abordagens para contornar falhas de DNS/conexão"""
    import time
    import socket
    
    try:
        print(f"Buscando coordenadas para: {cidade}")
        
        # Verifica cache primeiro (sem valores predefinidos)
        if cidade.lower() in CITY_COORDINATES:
            print(f"Coordenadas encontradas no cache para {cidade}")
            return CITY_COORDINATES[cidade.lower()]
        
        # Lista de serviços de geocodificação alternativos (sem necessidade de chave de API)
        geocoding_services = [
            {
                "nome": "OpenStreetMap via HTTPS",
                "url": "https://nominatim.openstreetmap.org/search",
                "params": {
                    "q": cidade + ", Brasil",
                    "format": "json",
                    "limit": 1
                },
                "headers": {"User-Agent": "Atlas-TravelPlanner/1.0"}
            },
            {
                "nome": "OpenStreetMap via HTTP",
                "url": "http://nominatim.openstreetmap.org/search",
                "params": {
                    "q": cidade + ", Brasil",
                    "format": "json",
                    "limit": 1
                },
                "headers": {"User-Agent": "Atlas-TravelPlanner/1.0"}
            },
            {
                "nome": "OpenStreetMap mirror",
                "url": "https://nominatim.openstreetmap.de/search",
                "params": {
                    "q": cidade + ", Brasil",
                    "format": "json",
                    "limit": 1
                },
                "headers": {"User-Agent": "Atlas-TravelPlanner/1.0"}
            },
            {
                "nome": "PhotonAPI (baseado no OpenStreetMap)",
                "url": "https://photon.komoot.io/api",
                "params": {
                    "q": cidade + ", Brasil",
                    "limit": 1
                },
                "headers": {"User-Agent": "Atlas-TravelPlanner/1.0"},
                "parser": lambda data: (float(data["features"][0]["geometry"]["coordinates"][1]), 
                                        float(data["features"][0]["geometry"]["coordinates"][0])) 
                           if data.get("features") and len(data["features"]) > 0 else None
            },
            {
                "nome": "OpenStreetMap via IP",
                "url": "http://212.0.151.52/search", # IP de um dos servidores Nominatim
                "params": {
                    "q": cidade + ", Brasil",
                    "format": "json",
                    "limit": 1
                },
                "headers": {"User-Agent": "Atlas-TravelPlanner/1.0"}
            },
            {
                "nome": "LocationIQ (gratuito para baixo volume)",
                "url": "https://eu1.locationiq.com/v1/search.php",
                "params": {
                    "q": cidade + ", Brasil",
                    "format": "json",
                    "limit": 1,
                    "key": "pk.33d6c19fd4e2f1d3829a5e5950695505" # Chave pública de exemplo
                },
                "headers": {"User-Agent": "Atlas-TravelPlanner/1.0"}
            }
        ]
        
        # Tenta resolver o DNS manualmente para verificar se esse é o problema
        try:
            ip_nominatim = socket.gethostbyname("nominatim.openstreetmap.org")
            print(f"Resolvido nominatim.openstreetmap.org para IP: {ip_nominatim}")
            
            # Adiciona o serviço com IP resolvido manualmente
            geocoding_services.append({
                "nome": "OpenStreetMap via IP resolvido",
                "url": f"http://{ip_nominatim}/search",
                "params": {
                    "q": cidade + ", Brasil",
                    "format": "json",
                    "limit": 1
                },
                "headers": {"User-Agent": "Atlas-TravelPlanner/1.0"}
            })
        except socket.gaierror:
            print("Não foi possível resolver o DNS para nominatim.openstreetmap.org")
        
        # Tenta cada serviço de geocodificação
        for service in geocoding_services:
            try:
                print(f"Tentando serviço: {service['nome']}")
                response = requests.get(
                    service["url"], 
                    params=service["params"], 
                    headers=service["headers"], 
                    timeout=5
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Extrai as coordenadas usando o parser personalizado ou o padrão
                    if "parser" in service:
                        coords = service["parser"](data)
                    else:
                        if data and len(data) > 0:
                            coords = (float(data[0]["lat"]), float(data[0]["lon"]))
                        else:
                            coords = None
                    
                    if coords:
                        print(f"Coordenadas encontradas via {service['nome']}: {coords}")
                        CITY_COORDINATES[cidade.lower()] = coords
                        return coords
                        
                    print(f"Sem resultados via {service['nome']}")
                else:
                    print(f"Erro ao consultar {service['nome']}: {response.status_code}")
                    
            except Exception as e:
                print(f"Falha no serviço {service['nome']}: {e}")
            
            # Respeita limites de taxa (evita ser bloqueado)
            time.sleep(1)
        
        # Se todas as tentativas falharem, tenta resolver via geocodificação simples
        # baseada na busca mais genérica (só cidade ou cidade+estado)
        variantes_consulta = [
            cidade,
            cidade + ", Brasil",
            cidade.title(),
            cidade.split(',')[0] if ',' in cidade else cidade
        ]
        
        for variante in variantes_consulta:
            for service in geocoding_services[:3]:  # Tenta apenas os 3 primeiros serviços
                try:
                    service["params"]["q"] = variante
                    response = requests.get(
                        service["url"], 
                        params=service["params"], 
                        headers=service["headers"], 
                        timeout=5
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        if "parser" in service:
                            coords = service["parser"](data)
                        else:
                            if data and len(data) > 0:
                                coords = (float(data[0]["lat"]), float(data[0]["lon"]))
                            else:
                                coords = None
                        
                        if coords:
                            print(f"Coordenadas encontradas via {service['nome']} com consulta alternativa: {coords}")
                            CITY_COORDINATES[cidade.lower()] = coords
                            return coords
                            
                except Exception as e:
                    print(f"Falha na consulta alternativa: {e}")
                
                time.sleep(1)
        
        # Implementa um sistema de proxy web simples como último recurso
        try:
            # Tenta usar um serviço de proxy CORS como fallback
            proxy_url = "https://corsproxy.io/?"
            target = "https://nominatim.openstreetmap.org/search"
            params = {
                "q": cidade + ", Brasil",
                "format": "json",
                "limit": 1
            }
            
            # Constrói a URL com os parâmetros codificados
            import urllib.parse
            params_encoded = urllib.parse.urlencode(params)
            full_url = f"{proxy_url}{urllib.parse.quote(target + '?' + params_encoded)}"
            
            headers = {"User-Agent": "Atlas-TravelPlanner/1.0"}
            response = requests.get(full_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    coords = (float(data[0]["lat"]), float(data[0]["lon"]))
                    print(f"Coordenadas encontradas via proxy CORS: {coords}")
                    CITY_COORDINATES[cidade.lower()] = coords
                    return coords
        except Exception as e:
            print(f"Falha na tentativa com proxy: {e}")
        
        # Se todas as tentativas falharem, retorna None
        print(f"Não foi possível obter coordenadas para {cidade} após todas as tentativas")
        return None
        
    except Exception as e:
        print(f"Erro inesperado ao obter coordenadas: {e}")
        return None

def calcular_distancia(origem: str, destino: str):
    """Calcula a distância entre duas cidades em km e retorna informações resumidas"""
    try:
        coord_origem = obter_coordenadas(origem)
        coord_destino = obter_coordenadas(destino)
        if not coord_origem or not coord_destino:
            return None
        distancia = geodesic(coord_origem, coord_destino).km
        tipo_rota = "curta" if distancia < 100 else "media" if distancia < 300 else "longa"
        return {
            "distancia_km": distancia,
            "tipo_rota": tipo_rota
        }
    except Exception as e:
        print(f"Erro ao calcular distância: {e}")
        return None

def salvar_historico(sessao_id, dados_busca, é_nova_conversa=False):
    """
    Salva uma entrada no histórico.
    Parâmetro é_nova_conversa indica se esta é a primeira mensagem de uma conversa.
    Apenas perguntas iniciais de cada conversa serão salvas no histórico.
    """
    try:
        # Se não for uma nova conversa, não salva no histórico
        if not é_nova_conversa:
            return True
            
        caminho_arquivo = f"historico/{sessao_id}.json"
        os.makedirs(os.path.dirname(caminho_arquivo), exist_ok=True)
        
        # Lê o histórico existente ou cria um novo
        if os.path.exists(caminho_arquivo):
            with open(caminho_arquivo, 'r', encoding='utf-8') as arquivo:
                historico = json.load(arquivo)
        else:
            historico = []
        
        # Adiciona a nova busca com timestamp e ID único
        dados_busca["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        dados_busca["id"] = str(uuid.uuid4())
        historico.append(dados_busca)
        
        # Salva o histórico atualizado
        with open(caminho_arquivo, 'w', encoding='utf-8') as arquivo:
            json.dump(historico, arquivo, ensure_ascii=False, indent=2)
            
        return True
    except Exception as e:
        print(f"Erro ao salvar histórico: {e}")
        return False

def carregar_historico(sessao_id):
    """Carrega todas as entradas do histórico para o usuário"""
    try:
        caminho_arquivo = f"historico/{sessao_id}.json"
        if os.path.exists(caminho_arquivo):
            with open(caminho_arquivo, 'r', encoding='utf-8') as arquivo:
                return json.load(arquivo)
        return []
    except Exception as e:
        print(f"Erro ao carregar histórico: {e}")
        return []

def carregar_conversa_por_id(sessao_id, conversa_id):
    """Carrega uma conversa específica pelo ID"""
    try:
        historico = carregar_historico(sessao_id)
        for conversa in historico:
            if conversa.get("id") == conversa_id:
                return conversa
        return None
    except Exception as e:
        print(f"Erro ao carregar conversa: {e}")
        return None

def format_message_content(content):
    """Formata o conteúdo da mensagem para HTML"""
    content = content.replace('\n', '<br>')
    content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', content)
    content = re.sub(r'\*(.*?)\*', r'<em>\1</em>', content)
    content = content.replace('  ', '&nbsp;&nbsp;')
    return content

@app.route('/')
def index():
    # Cria ou recupera ID de sessão
    if not session.get("id"):
        session["id"] = str(uuid.uuid4())
    # Limpa dados de conversa anterior
    session["nova_conversa"] = True
    return render_template('index.html')

@app.route('/chat')
def chat_page():
    # Cria ou recupera ID de sessão
    if not session.get("id"):
        session["id"] = str(uuid.uuid4())
    return render_template('chat.html')

@app.route('/historico')
def historico():
    try:
        user_id = session.get("id")
        print(f"Acessando histórico para usuário: {user_id}")
        
        if not user_id:
            print("Usuário não autenticado, redirecionando para index")
            return redirect(url_for('index'))
        
        conversations = Conversation.query.filter_by(user_id=user_id).order_by(Conversation.timestamp.desc()).all()
        print(f"Encontradas {len(conversations)} conversas")
        
        for conv in conversations:
            print(f"Conversa {conv.id}: {conv.title} ({len(conv.messages)} mensagens)")
        
        return render_template('historico.html', conversations=conversations)
    except Exception as e:
        print(f"Erro ao carregar histórico: {e}")
        return render_template('historico.html', conversations=[])

@app.route('/conversation/<int:conversation_id>')
def view_conversation(conversation_id):
    user_id = session.get("id")
    if not user_id:
        return redirect(url_for('index'))
    
    conversation = Conversation.query.get_or_404(conversation_id)
    if conversation.user_id != user_id:
        return redirect(url_for('historico'))
    
    # Atualiza a sessão com os dados desta conversa
    session["conversation_id"] = conversation.id
    session["origem"] = conversation.origin
    session["destino"] = conversation.destination
    session["data_inicio"] = conversation.start_date
    session["data_fim"] = conversation.end_date
    
    return render_template('chat.html', conversation=conversation)

@app.route('/search', methods=['POST'])
def structured_search():
    """Processa busca estruturada do painel principal"""
    try:
        data = request.get_json()
        user_id = session.get("id")
        
        if not user_id:
            user_id = str(uuid.uuid4())
            session["id"] = user_id
        
        # Extrair dados estruturados
        destination = data.get('destination', '').strip()
        checkin = data.get('checkin')
        checkout = data.get('checkout')
        adults = data.get('adults', 2)
        children = data.get('children', 0)
        include_flights = data.get('includeFlights', True)
        include_hotels = data.get('includeHotels', False)
        include_weather = data.get('includeWeather', True)
        
        # Validar dados essenciais
        if not destination:
            return jsonify({"error": "Destino é obrigatório"}), 400
        
        if not checkin:
            return jsonify({"error": "Data de ida é obrigatória"}), 400
        
        # Calcular duração da viagem
        duration_text = ""
        start_date = None
        end_date = None
        
        if checkin:
            start_date = datetime.strptime(checkin, "%Y-%m-%d").date()
            
        if checkout:
            end_date = datetime.strptime(checkout, "%Y-%m-%d").date()
            days = (end_date - start_date).days
            if days > 0:
                duration_text = f" por {days} dia{'s' if days != 1 else ''}"
        
        # Construir mensagem natural
        message = f"Quero um roteiro de viagem para {destination}{duration_text}"
        
        if checkin:
            formatted_date = start_date.strftime("%d/%m/%Y")
            message += f" saindo no dia {formatted_date}"
        
        if adults > 1 or children > 0:
            message += f" para {adults} adulto{'s' if adults != 1 else ''}"
            if children > 0:
                message += f" e {children} criança{'s' if children != 1 else ''}"
        
        # Adicionar preferências
        preferences = []
        if include_flights:
            preferences.append("incluir informações de voos")
        if include_hotels:
            preferences.append("sugestões de hospedagem")
        if include_weather:
            preferences.append("previsão do tempo")
        
        if preferences:
            message += ". Por favor, " + ", ".join(preferences)
        
        # Criar nova conversa
        conversation = Conversation(
            title=generate_conversation_title(message),
            user_id=user_id,
            destination=destination,
            start_date=start_date,
            end_date=end_date
        )
        
        db.session.add(conversation)
        db.session.commit()
        session["conversation_id"] = conversation.id
        
        # Processar com IA
        if user_id not in chat_context:
            chat_context[user_id] = []
        
        chat_context[user_id].append({"role": "user", "content": message})
        bot_response = get_ai_response(chat_context[user_id])
        chat_context[user_id].append({"role": "model", "content": bot_response})
        
        # Salvar mensagens
        user_msg = Message(
            content=message,
            is_bot=False,
            conversation_id=conversation.id
        )
        
        formatted_response = format_message_content(bot_response)
        bot_msg = Message(
            content=formatted_response,
            is_bot=True,
            conversation_id=conversation.id
        )
        
        db.session.add(user_msg)
        db.session.add(bot_msg)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'conversation_id': conversation.id,
            'title': conversation.title,
            'user_message': message,
            'bot_response': formatted_response
        })
        
    except Exception as e:
        print(f"Erro na busca estruturada: {e}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/chat', methods=['POST'])
def chat():
    try:
        user_message = request.json.get('message', '').strip()
        user_id = session.get("id")
        
        print(f"Processando mensagem do usuário {user_id}")
        
        if not user_id:
            print("ID de sessão não encontrado, gerando novo ID")
            user_id = str(uuid.uuid4())
            session["id"] = user_id
        
        # Verifica se é uma nova conversa
        conversation_id = session.get("conversation_id")
        print(f"ID da conversa atual: {conversation_id}")
        
        # Força nova conversa se vier da página inicial ou se a flag estiver ativa
        initial_message = request.json.get('initial_message', False)
        is_new_conversation = initial_message or session.get("nova_conversa", False)
        
        if is_new_conversation:
            print("Iniciando nova conversa")
            # Limpa o contexto anterior
            if user_id in chat_context:
                chat_context[user_id] = []
                
            # Extrai origem e destino da mensagem
            destino = extrair_destino(user_message)
            origem = extrair_origem(user_message)
            datas = extrair_datas(user_message)
            
            print(f"Origem: {origem}")
            print(f"Destino: {destino}")
            print(f"Datas: {datas}")
            
            # Converte strings de data para objetos date
            start_date = datas.get("data_inicio")
            end_date = datas.get("data_fim")
            
            if start_date:
                start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            if end_date:
                end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
                
            # Cria uma nova conversa
            conversation = Conversation(
                title=generate_conversation_title(user_message),
                user_id=user_id,
                origin=origem if origem != "Origem não informada" else None,
                destination=destino if destino != "Destino não informado" else None,
                start_date=start_date,
                end_date=end_date
            )
            
            try:
                print("Salvando nova conversa no banco de dados")
                db.session.add(conversation)
                db.session.commit()
                session["conversation_id"] = conversation.id
                print(f"Nova conversa criada com ID: {conversation.id}")
                
                # Limpa a flag de nova conversa
                session.pop("nova_conversa", None)
            except Exception as e:
                print(f"Erro ao salvar conversa: {e}")
                db.session.rollback()
                raise
        else:
            print(f"Continuando conversa existente: {conversation_id}")
            conversation = Conversation.query.get(conversation_id)
            if not conversation:
                print("Conversa não encontrada no banco de dados")
                return jsonify({"error": "Conversa não encontrada"}), 404

        # Adiciona a mensagem do usuário
        user_msg = Message(
            content=user_message,
            is_bot=False,
            conversation_id=conversation.id
        )
        
        try:
            print("Salvando mensagem do usuário")
            db.session.add(user_msg)
            db.session.commit()
        except Exception as e:
            print(f"Erro ao salvar mensagem do usuário: {e}")
            db.session.rollback()
            raise
        
        # Processa a resposta do chatbot
        if user_id not in chat_context:
            chat_context[user_id] = []

        chat_context[user_id].append({"role": "user", "content": user_message})
        bot_response = get_ai_response(chat_context[user_id])
        chat_context[user_id].append({"role": "model", "content": bot_response})

        # Formata e adiciona a resposta do bot
        formatted_response = format_message_content(bot_response)
        bot_msg = Message(
            content=formatted_response,
            is_bot=True,
            conversation_id=conversation.id
        )
        
        try:
            print("Salvando resposta do bot")
            db.session.add(bot_msg)
            db.session.commit()
            print("Mensagens salvas com sucesso")
        except Exception as e:
            print(f"Erro ao salvar resposta do bot: {e}")
            db.session.rollback()
            raise

        return jsonify({'response': formatted_response, 'title': conversation.title})
        
    except Exception as e:
        print(f"Erro geral na rota de chat: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/new_chat', methods=['POST'])
def new_chat():
    """Inicia uma nova conversa, limpando o contexto anterior."""
    try:
        user_id = session.get("id")
        print(f"Iniciando nova conversa para usuário {user_id}")
        
        if not user_id:
            print("ID de sessão não encontrado, gerando novo ID")
            user_id = str(uuid.uuid4())
            session["id"] = user_id
        
        # Limpa o contexto atual do usuário
        if user_id in chat_context:
            print("Limpando contexto do chat")
            chat_context[user_id] = []
        
        # Limpa dados da sessão relacionados à viagem
        print("Limpando dados da sessão")
        session.pop("conversation_id", None)
        session.pop("destino", None)
        session.pop("origem", None)
        session.pop("data_inicio", None)
        session.pop("data_fim", None)
        session.pop("nova_conversa", None)
        
        # Força uma nova conversa na próxima mensagem
        session["nova_conversa"] = True
        
        print("Nova conversa iniciada com sucesso")
        return jsonify({"success": True, "message": "Nova conversa iniciada"})
        
    except Exception as e:
        print(f"Erro ao iniciar nova conversa: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/cambio', methods=['GET'])
def cambio():
    moeda = request.args.get('moeda', 'USD')
    taxa = get_exchange_rate(moeda)
    return jsonify({'moeda': moeda, 'taxa': taxa})

@app.route('/limpar_historico', methods=['POST'])
def limpar_historico():
    try:
        user_id = session.get("id")
        if not user_id:
            return jsonify({"success": False, "error": "Usuário não autenticado"}), 401
        
        print(f"Limpando histórico para usuário: {user_id}")
        
        # Busca todas as conversas do usuário
        conversations = Conversation.query.filter_by(user_id=user_id).all()
        
        # Deleta cada conversa (as mensagens serão deletadas automaticamente devido ao cascade)
        for conv in conversations:
            db.session.delete(conv)
        
        # Limpa o contexto do chat
        if user_id in chat_context:
            chat_context[user_id] = []
        
        # Limpa dados da sessão relacionados à conversa atual
        session.pop("conversation_id", None)
        session.pop("destino", None)
        session.pop("origem", None)
        session.pop("data_inicio", None)
        session.pop("data_fim", None)
        
        # Commit das alterações
        db.session.commit()
        print(f"Histórico limpo com sucesso para usuário: {user_id}")
        
        return jsonify({"success": True})
        
    except Exception as e:
        print(f"Erro ao limpar histórico: {e}")
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/excluir_conversa/<int:conversation_id>', methods=['POST'])
def excluir_conversa(conversation_id):
    try:
        user_id = session.get("id")
        if not user_id:
            return jsonify({"success": False, "error": "Usuário não autenticado"}), 401
        
        print(f"Excluindo conversa {conversation_id} do usuário {user_id}")
        
        # Busca a conversa
        conversation = Conversation.query.get_or_404(conversation_id)
        
        # Verifica se a conversa pertence ao usuário
        if conversation.user_id != user_id:
            return jsonify({"success": False, "error": "Conversa não pertence ao usuário"}), 403
        
        # Se a conversa atual está sendo excluída, limpa a sessão
        if session.get("conversation_id") == conversation_id:
            session.pop("conversation_id", None)
            session.pop("destino", None)
            session.pop("origem", None)
            session.pop("data_inicio", None)
            session.pop("data_fim", None)
            
            # Limpa o contexto do chat se necessário
            if user_id in chat_context:
                chat_context[user_id] = []
        
        # Deleta a conversa (as mensagens serão deletadas automaticamente devido ao cascade)
        db.session.delete(conversation)
        db.session.commit()
        
        print(f"Conversa {conversation_id} excluída com sucesso")
        return jsonify({"success": True})
        
    except Exception as e:
        print(f"Erro ao excluir conversa: {e}")
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    # Cria pasta para armazenar histórico de buscas
    os.makedirs("historico", exist_ok=True)
    app.run(debug=True, port=8000)