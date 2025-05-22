from flask import Flask, request, jsonify, render_template, session
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
from datetime import timedelta

app = Flask(__name__)
app.config["SESSION_PERMANENT"] = True
app.config["SESSION_TYPE"] = "filesystem"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=1)
app.secret_key = os.getenv("SECRET_KEY", "chave_secreta_temporaria")
Session(app)

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
    "bogotá": "BOG"
}

def get_exchange_rate(currency: str = "USD") -> float:
    try:
        today = datetime.datetime.now().strftime("%m-%d-%Y")
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
    headers = {"Content-Type": "application/json"}
    system_prompt = {
        "role": "system",
        "content": (
            "Você é um assistente especializado em criação de roteiros de viagens personalizados. "
            "Responda apenas perguntas relacionadas a roteiros, locais turísticos, atividades, transporte e dicas de viagem. "
            "Se a pergunta não for sobre isso, recuse educadamente. "
            "Quando sugerir pontos turísticos, seja detalhado incluindo os melhores horários para visita, custos aproximados "
            "e dicas úteis como o que vestir ou levar. Personalize suas respostas de acordo com a duração da viagem e preferências "
            "do usuário. Inclua sugestões de restaurantes locais com pratos típicos que valem a pena experimentar."
        )
    }
    full_messages = [system_prompt] + [{"role": "user", "content": m["content"]} for m in messages if m["role"] == "user"]
    data = {"contents": [{"parts": [{"text": m["content"]} for m in full_messages]}]}

    try:
        response = requests.post(
            f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
            headers=headers,
            json=data
        )
        response.raise_for_status()
        result = response.json()
        return result['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        print(f"Erro na API Gemini: {e}")
        return "Erro ao gerar resposta. Por favor, tente novamente mais tarde."

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
        # Verifica se os códigos são válidos
        if not origin or not destination:
            print(f"Códigos IATA inválidos ou vazios: origem={origin}, destino={destination}")
            return {"data": []}
            
        # Garante que os códigos estão no formato correto (3 letras maiúsculas)
        origin = origin.strip().upper()
        destination = destination.strip().upper()
        
        if len(origin) != 3 or len(destination) != 3:
            print(f"Códigos IATA com tamanho incorreto: origem={origin} ({len(origin)}), destino={destination} ({len(destination)})")
            return {"data": []}
            
        # Verifica se a data está no formato correto
        try:
            datetime.datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            print(f"Formato de data inválido: {date}")
            data_atual = datetime.datetime.now() + timedelta(days=7)
            date = data_atual.strftime("%Y-%m-%d")
        
        print(f"Buscando voos: {origin} -> {destination}, data: {date}")
        
        auth_url = "https://test.api.amadeus.com/v1/security/oauth2/token"
        auth_data = {
            "grant_type": "client_credentials",
            "client_id": os.getenv("AMADEUS_CLIENT_ID"),
            "client_secret": os.getenv("AMADEUS_CLIENT_SECRET")
        }
        auth_response = requests.post(auth_url, data=auth_data, verify=False)
        if auth_response.status_code != 200:
            print(f"Erro na autenticação com a API Amadeus: {auth_response.text}")
            return {"data": []}
            
        token = auth_response.json().get("access_token")
        if not token:
            print("Token de acesso não encontrado na resposta de autenticação")
            return {"data": []}

        params = {
            "originLocationCode": origin,
            "destinationLocationCode": destination,
            "departureDate": date,
            "adults": 1,
            "max": 5,
            "currencyCode": "USD"  # Garante que os preços estejam em USD
        }
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(FLIGHT_API_URL, headers=headers, params=params, verify=False)
        
        if response.status_code != 200:
            print(f"Erro na API de voos: {response.status_code} - {response.text}")
            return {"data": []}
            
        result = response.json()
        
        if "data" not in result or not result["data"]:
            print(f"Resposta da API sem dados de voos: {result}")
            # Tentativa alternativa: inverter origem e destino para testar
            params["originLocationCode"], params["destinationLocationCode"] = params["destinationLocationCode"], params["originLocationCode"]
            print(f"Tentando busca invertida: {params['originLocationCode']} -> {params['destinationLocationCode']}")
            
            alt_response = requests.get(FLIGHT_API_URL, headers=headers, params=params, verify=False)
            if alt_response.status_code == 200:
                alt_result = alt_response.json()
                if "data" in alt_result and alt_result["data"]:
                    print("Busca invertida encontrou voos!")
                    return alt_result
        
        return result
    except Exception as e:
        print(f"Erro ao buscar voos: {e}")
        return {"data": []}
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
        hoje = datetime.datetime.now()
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
            data_inicio = datetime.datetime.strptime(data_inicio, "%Y-%m-%d")
            data_fim = datetime.datetime.strptime(data_fim, "%Y-%m-%d")
            previsao_filtrada = []
            
            for p in data.get("list", []):
                data_previsao = datetime.datetime.fromtimestamp(p.get("dt"))
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
        padroes = [
            r'(?:para|em|no|na)\s+([A-Za-zÀ-ÿ\s]+?)(?:\s+com|\s+por|\s+durante|\s*$|,)',
            r'roteiro\s+(?:de|para)\s+[A-Za-zÀ-ÿ\s]+?\s+(?:em|para)\s+([A-Za-zÀ-ÿ\s]+)',
            r'conhecer\s+([A-Za-zÀ-ÿ\s]+?)(?:\s+e|\s+com|\s+por|\s+durante|\s*$|,)',
            r'visitar\s+([A-Za-zÀ-ÿ\s]+?)(?:\s+e|\s+com|\s+por|\s+durante|\s*$|,)'
        ]
        for padrao in padroes:
            match = re.search(padrao, texto, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return "Destino não informado"
    except:
        return "Destino não informado"

# Lista de palavras para descartar após a extração
PALAVRAS_DESCARTAR = [
    "para", "até", "e", "com", "por", "durante", "no", "na", "do", "da", "dos", "das", "de", "em", "ao", "aos", "às", "as", "os", "o", "a", "um", "uma", "uns", "umas"
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

def extrair_origem(texto: str) -> str:
    padroes = [
        r'saindo de\s+([A-Za-zÀ-ÿ\s]+?)(?:\s+e|\s+com|\s+por|\s+durante|\s*$|,)',
        r'partindo de\s+([A-Za-zÀ-ÿ\s]+?)(?:\s+e|\s+com|\s+por|\s+durante|\s*$|,)',
        r'desde\s+([A-Za-zÀ-ÿ\s]+?)(?:\s+e|\s+com|\s+por|\s+durante|\s*$|,)',
        r'de\s+([A-Za-zÀ-ÿ\s]+)\s+(?:para|até)',
        r'saindo do\s+([A-Za-zÀ-ÿ\s]+?)(?:\s+e|\s+com|\s+por|\s+durante|\s*$|,)',
    ]
    for padrao in padroes:
        match = re.search(padrao, texto, re.IGNORECASE)
        if match:
            cidade = limpar_nome_cidade(match.group(1))
            return cidade
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
            
            ano_atual = datetime.datetime.now().year
            resultado["data_inicio"] = f"{ano_atual}-{mes}-{dia}"
        
        # Processar data de fim
        match_fim = re.search(padrao_data, data_fim_texto, re.IGNORECASE)
        if match_fim:
            dia = match_fim.group(1).zfill(2)
            if match_fim.group(2):  # Formato "15 de janeiro"
                mes = meses.get(match_fim.group(2).lower(), '01')
            else:  # Formato "15/01"
                mes = match_fim.group(3).zfill(2)
            
            ano_atual = datetime.datetime.now().year
            resultado["data_fim"] = f"{ano_atual}-{mes}-{dia}"
    
    # Se não encontrou período específico, tenta extrair a duração
    if not resultado["data_inicio"]:
        padrao_duracao = r'(\d+)\s+dias?'
        match_duracao = re.search(padrao_duracao, texto, re.IGNORECASE)
        
        if match_duracao:
            dias = int(match_duracao.group(1))
            hoje = datetime.datetime.now()
            data_inicio = hoje + timedelta(days=7)  # Assume viagem uma semana à frente
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
        dados_busca["timestamp"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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

@app.route('/')
def index():
    # Cria ou recupera ID de sessão
    if not session.get("id"):
        session["id"] = str(uuid.uuid4())
    # Limpa dados de conversa anterior
    session["nova_conversa"] = True
    return render_template('chat.html')

@app.route('/historico')
def historico():
    # Carrega o histórico da sessão atual
    sessao_id = session.get("id")
    if not sessao_id:
        return render_template('historico.html', historico=[])
    
    historico_buscas = carregar_historico(sessao_id)
    return render_template('historico.html', historico=historico_buscas)

@app.route('/carregar_conversa/<conversa_id>', methods=['GET'])
def carregar_conversa(conversa_id):
    """Carrega uma conversa específica e inicia uma nova sessão com seus dados"""
    sessao_id = session.get("id")
    if not sessao_id:
        return jsonify({"status": "error", "message": "Sessão inválida"})
    
    conversa = carregar_conversa_por_id(sessao_id, conversa_id)
    if not conversa:
        return jsonify({"status": "error", "message": "Conversa não encontrada"})
    
    # Inicia uma nova conversa com os dados da conversa carregada
    session["destino"] = conversa.get("destino")
    session["origem"] = conversa.get("origem")
    if conversa.get("datas"):
        session["data_inicio"] = conversa["datas"].get("data_inicio")
        session["data_fim"] = conversa["datas"].get("data_fim")
    
    # Limpa o contexto atual do usuário
    if sessao_id in chat_context:
        chat_context[sessao_id] = []
    
    session["nova_conversa"] = True
    
    return jsonify({
        "status": "success", 
        "message": "Conversa carregada com sucesso",
        "conversa": conversa
    })

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message', '').strip()
    user_id = session.get("id", request.remote_addr)
    
    # Verifica se é uma nova conversa ou continuação
    é_nova_conversa = session.get("nova_conversa", True)
    session["nova_conversa"] = False  # Próximas mensagens não serão novas
    
    if user_id not in chat_context:
        chat_context[user_id] = []

    chat_context[user_id].append({"role": "user", "content": user_message})
    resposta = get_ai_response(chat_context[user_id])
    chat_context[user_id].append({"role": "model", "content": resposta})

    # Extrai informações da mensagem atual
    destino_atual = extrair_destino(user_message)
    origem_atual = extrair_origem(user_message)
    datas = extrair_datas(user_message)
    
    # Armazena informações na sessão se forem encontradas
    if destino_atual != "Destino não informado":
        session["destino"] = destino_atual
    
    if origem_atual != "Origem não informada":
        session["origem"] = origem_atual
    
    if datas.get("data_inicio"):
        session["data_inicio"] = datas.get("data_inicio")
    
    if datas.get("data_fim"):
        session["data_fim"] = datas.get("data_fim")
    
    # Usa informações da sessão se não forem encontradas na mensagem atual
    destino = destino_atual
    if destino == "Destino não informado" and session.get("destino"):
        destino = session.get("destino")
    
    origem = origem_atual
    if origem == "Origem não informada" and session.get("origem"):
        origem = session.get("origem")
    
    # Atualiza datas com informações da sessão se necessário
    data_inicio = datas.get("data_inicio") or session.get("data_inicio")
    data_fim = datas.get("data_fim") or session.get("data_fim")
    datas_completas = {"data_inicio": data_inicio, "data_fim": data_fim}

    dados_busca = {
        "mensagem": user_message,
        "destino": destino,
        "origem": origem,
        "datas": datas_completas
    }

    # Salva no histórico apenas se for uma nova conversa
    salvar_historico(user_id, dados_busca, é_nova_conversa)

    # Verifica se tem origem (atual ou da sessão)
    if origem == "Origem não informada":
        return jsonify({'response': resposta + "\n\n✋ Por favor, informe a cidade de origem para que eu possa sugerir transportes ou voos."})

    info_adicional = ""

    if destino != "Destino não informado":
        # Obtém códigos IATA para origem e destino
        codigo_origem = buscar_codigo_iata(origem)
        codigo_destino = buscar_codigo_iata(destino)
        
        # Registra os códigos para depuração
        print(f"Origem: {origem} -> {codigo_origem}")
        print(f"Destino: {destino} -> {codigo_destino}")
        
        # Define a data de partida
        data_partida = data_inicio if data_inicio else (datetime.datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        
        # Busca previsão do tempo
        previsao = obter_previsao_tempo(destino, data_inicio, data_fim)
        if previsao:
            info_adicional += f"\n\n🌤️ Previsão do tempo para {destino.title()}:\n"
            for p in previsao:
                info_adicional += f"• {p['data']}: {p['temperatura']}°C, {p['descricao']}\n"

        # Busca hotéis
        hoteis = buscar_hoteis(codigo_destino)
        if hoteis:
            info_adicional += f"\n\n🏨 Opções de hotéis em {destino.title()}:\n"
            for i, hotel in enumerate(hoteis, 1):
                nome = hotel.get("name", "Hotel sem nome")
                categoria = "⭐" * int(hotel.get("rating", 3))
                preco = hotel.get("preco", "Preço não disponível")
                info_adicional += f"• {nome} {categoria} - {preco}\n"

        # Calcula distância usando a API e sugere transporte
        distancia_info = calcular_distancia(origem, destino)
        if distancia_info is not None:
            distancia_km = distancia_info["distancia_km"]
            distancia_formatada = f"{distancia_km:.1f}".replace(".", ",")
            tipo_rota = distancia_info["tipo_rota"]

            if tipo_rota == "curta":
                info_adicional += (
                    f"\n\n🚗 A distância entre {origem.title()} e {destino.title()} é de aproximadamente {distancia_formatada} km."
                    f"\nRecomendamos transporte terrestre (carro, ônibus ou aplicativo de transporte)."
                    f"\n✈️ Não há voos comerciais regulares para esta distância."
                )
            elif tipo_rota == "media":
                info_adicional += (
                    f"\n\n🚗 A distância entre {origem.title()} e {destino.title()} é de aproximadamente {distancia_formatada} km."
                    f"\nO transporte terrestre (carro ou ônibus) costuma ser mais prático."
                )
                voos = get_flights(codigo_origem, codigo_destino, data_partida)
                if voos.get("data"):
                    info_adicional += (
                        f"\n✈️ Existem voos disponíveis, mas normalmente não compensa para esta distância."
                    )
            else:  # tipo_rota == "longa"
                voos = get_flights(codigo_origem, codigo_destino, data_partida)
                if voos.get("data"):
                    info_adicional += (
                        f"\n\n✈️ A distância entre {origem.title()} e {destino.title()} é de {distancia_formatada} km."
                        f"\nVeja as melhores opções de voos:"
                    )
                    for i, voo in enumerate(voos["data"][:3], 1):
                        try:
                            segmento = voo["itineraries"][0]["segments"][0]
                            horario_partida = segmento["departure"]["at"][11:16]
                            horario_chegada = segmento["arrival"]["at"][11:16]
                            companhia = segmento["carrierCode"]
                            duracao = segmento.get("duration", "").replace("PT", "").replace("H", "h ").replace("M", "m")
                            preco = format_price(voo.get("price", {}))
                            info_adicional += (
                                f"\n• Voo {i}: {companhia}, {horario_partida}-{horario_chegada}, duração {duracao}, preço: {preco}"
                            )
                        except Exception as e:
                            print(f"Erro ao processar voo {i}: {e}")
                            continue
                else:
                    info_adicional += (
                        f"\n\n⚠️ Nenhum voo encontrado de {origem.title()} para {destino.title()} na data {data_partida}."
                        f"\nConsidere opções terrestres, como ônibus ou carro."
                    )
    resposta_final = resposta + info_adicional
    return jsonify({'response': resposta_final})
    
@app.route('/new_chat', methods=['POST'])
def new_chat():
    """Inicia uma nova conversa, limpando o contexto anterior."""
    user_id = session.get("id", request.remote_addr)
    
    # Limpa o contexto atual do usuário
    if user_id in chat_context:
        chat_context[user_id] = []
    
    # Limpa dados da sessão relacionados à viagem
    session.pop("destino", None)
    session.pop("origem", None)
    session.pop("data_inicio", None)
    session.pop("data_fim", None)
    
    # Marca que a próxima mensagem será de uma nova conversa
    session["nova_conversa"] = True
    
    return jsonify({"status": "success", "message": "Nova conversa iniciada"})

@app.route('/api/cambio', methods=['GET'])
def cambio():
    moeda = request.args.get('moeda', 'USD')
    taxa = get_exchange_rate(moeda)
    return jsonify({'moeda': moeda, 'taxa': taxa})

if __name__ == '__main__':
    # Cria pasta para armazenar histórico de buscas
    os.makedirs("historico", exist_ok=True)
    app.run(debug=True)