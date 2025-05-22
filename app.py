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
    try:
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
        if results:
            return results[0].get("iataCode", nome_destino[:3].upper())
        else:
            return nome_destino[:3].upper()
    except Exception as e:
        print(f"Erro ao buscar código IATA: {e}")
        return nome_destino[:3].upper()

def get_flights(origin: str, destination: str, date: str):
    try:
        auth_url = "https://test.api.amadeus.com/v1/security/oauth2/token"
        auth_data = {
            "grant_type": "client_credentials",
            "client_id": os.getenv("AMADEUS_CLIENT_ID"),
            "client_secret": os.getenv("AMADEUS_CLIENT_SECRET")
        }
        auth_response = requests.post(auth_url, data=auth_data, verify=False)
        token = auth_response.json().get("access_token")

        params = {
            "originLocationCode": origin.upper(),
            "destinationLocationCode": destination.upper(),
            "departureDate": date,
            "adults": 1,
            "max": 5
        }
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(FLIGHT_API_URL, headers=headers, params=params, verify=False)
        return response.json()
    except:
        return {"data": []}

def buscar_hoteis(cidade_codigo: str):
    try:
        auth_url = "https://test.api.amadeus.com/v1/security/oauth2/token"
        auth_data = {
            "grant_type": "client_credentials",
            "client_id": os.getenv("AMADEUS_CLIENT_ID"),
            "client_secret": os.getenv("AMADEUS_CLIENT_SECRET")
        }
        auth_response = requests.post(auth_url, data=auth_data, verify=False)
        token = auth_response.json().get("access_token")

        params = {
            "cityCode": cidade_codigo.upper(),
            "radius": 5,
            "radiusUnit": "KM",
            "ratings": "3,4,5",
            "hotelSource": "ALL"
        }
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(HOTEL_API_URL, headers=headers, params=params, verify=False)
        return response.json().get("data", [])[:3]  # Retorna apenas 3 hotéis
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
    if isinstance(price_data.get("total"), (int, float)):
        cotacao_dolar = get_exchange_rate("USD")
        preco_brl = float(price_data.get("total")) * cotacao_dolar
        return f"R$ {preco_brl:,.2f}".replace(",", ".")
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
            return match.group(1).strip()
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

def salvar_historico(sessao_id, dados_busca):
    try:
        caminho_arquivo = f"historico/{sessao_id}.json"
        os.makedirs(os.path.dirname(caminho_arquivo), exist_ok=True)
        
        # Lê o histórico existente ou cria um novo
        if os.path.exists(caminho_arquivo):
            with open(caminho_arquivo, 'r', encoding='utf-8') as arquivo:
                historico = json.load(arquivo)
        else:
            historico = []
        
        # Adiciona a nova busca com timestamp
        dados_busca["timestamp"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        historico.append(dados_busca)
        
        # Salva o histórico atualizado
        with open(caminho_arquivo, 'w', encoding='utf-8') as arquivo:
            json.dump(historico, arquivo, ensure_ascii=False, indent=2)
            
        return True
    except Exception as e:
        print(f"Erro ao salvar histórico: {e}")
        return False

def carregar_historico(sessao_id):
    try:
        caminho_arquivo = f"historico/{sessao_id}.json"
        if os.path.exists(caminho_arquivo):
            with open(caminho_arquivo, 'r', encoding='utf-8') as arquivo:
                return json.load(arquivo)
        return []
    except Exception as e:
        print(f"Erro ao carregar histórico: {e}")
        return []

@app.route('/')
def index():
    # Cria ou recupera ID de sessão
    if not session.get("id"):
        session["id"] = str(uuid.uuid4())
    return render_template('index.html')

@app.route('/historico')
def historico():
    # Carrega o histórico da sessão atual
    sessao_id = session.get("id")
    if not sessao_id:
        return render_template('historico.html', historico=[])
    
    historico_buscas = carregar_historico(sessao_id)
    return render_template('historico.html', historico=historico_buscas)

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message', '').strip()
    user_id = session.get("id", request.remote_addr)

    if user_id not in chat_context:
        chat_context[user_id] = []

    chat_context[user_id].append({"role": "user", "content": user_message})
    resposta = get_ai_response(chat_context[user_id])
    chat_context[user_id].append({"role": "model", "content": resposta})

    destino = extrair_destino(user_message)
    origem = extrair_origem(user_message)
    datas = extrair_datas(user_message)

    dados_busca = {
        "mensagem": user_message,
        "destino": destino,
        "origem": origem,
        "datas": datas
    }

    # Salva no histórico
    salvar_historico(user_id, dados_busca)

    if origem == "Origem não informada":
        return jsonify({'response': resposta + "\n\n✋ Por favor, informe a cidade de origem para que eu possa sugerir transportes ou voos."})

    info_adicional = ""

    if destino.lower() != "destino não informado":
        codigo_destino = buscar_codigo_iata(destino)
        codigo_origem = buscar_codigo_iata(origem)
        
        # Define a data de partida (usando data extraída ou data atual + 7 dias)
        data_partida = datas.get("data_inicio") if datas.get("data_inicio") else (datetime.datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        
        # Busca previsão do tempo
        previsao = obter_previsao_tempo(destino, datas.get("data_inicio"), datas.get("data_fim"))
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
                info_adicional += f"• {nome} {categoria}\n"

        # Verifica distância e sugere transporte
        coord_origem = CITY_COORDINATES.get(origem.lower())
        coord_destino = CITY_COORDINATES.get(destino.lower())
        distancia_km = None
        if coord_origem and coord_destino:
            distancia_km = geodesic(coord_origem, coord_destino).km

        if distancia_km and distancia_km < 200:
            info_adicional += f"\n\n🚗 A distância entre {origem.title()} e {destino.title()} é de aproximadamente {distancia_km:.1f} km. Recomendamos transporte terrestre:"
            info_adicional += f"\n• Carro: aproximadamente {(distancia_km/80):.1f} horas de viagem"
            info_adicional += f"\n• Ônibus: diversas opções de viação disponíveis"
        else:
            voos = get_flights(codigo_origem, codigo_destino, data_partida)
            if voos.get("data"):
                info_adicional += f"\n\n✈️ Opções de voos de {origem.title()} para {destino.title()} em {data_partida}:\n"
                for i, voo in enumerate(voos["data"][:3], 1):
                    segmento = voo["itineraries"][0]["segments"][0]
                    horario_partida = segmento["departure"]["at"][11:16]
                    horario_chegada = segmento["arrival"]["at"][11:16]
                    companhia = segmento["carrierCode"]
                    duracao = segmento.get("duration", "").replace("PT", "").replace("H", "h ").replace("M", "m")
                    preco = format_price(voo.get("price", {}))
                    info_adicional += f"\n• Voo {i}: {companhia}, {horario_partida}-{horario_chegada}, duração {duracao}, preço: {preco}"
            else:
                info_adicional += f"\n\n⚠️ Nenhum voo encontrado de {origem.title()} para {destino.title()} na data {data_partida}."

    resposta_final = resposta + info_adicional
    return jsonify({'response': resposta_final})

@app.route('/new_chat', methods=['POST'])
def new_chat():
    """Inicia uma nova conversa, limpando o contexto anterior."""
    user_id = session.get("id", request.remote_addr)
    
    # Limpa o contexto atual do usuário
    if user_id in chat_context:
        chat_context[user_id] = []
    
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
