from flask import Flask, request, jsonify, render_template
import datetime
import requests
import os
from dotenv import load_dotenv
import warnings
import re
from geopy.distance import geodesic

app = Flask(__name__)

warnings.filterwarnings("ignore")
load_dotenv()

EXCHANGE_API_URL = "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoMoedaDia(moeda=@moeda,dataCotacao=@dataCotacao)"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
FLIGHT_API_URL = "https://test.api.amadeus.com/v2/shopping/flight-offers"

chat_context = {}

CITY_COORDINATES = {
    "sao paulo": (-23.5505, -46.6333),
    "campinas": (-22.9099, -47.0626),
    "rio de janeiro": (-22.9068, -43.1729),
    "curitiba": (-25.4284, -49.2733),
    "belo horizonte": (-19.9167, -43.9345)
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
            "Se a pergunta não for sobre isso, recuse educadamente."
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
        return "Erro ao gerar resposta."

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

def format_price(price_data):
    if isinstance(price_data.get("total_brl"), (int, float)):
        return f"R$ {price_data['total_brl']:,.2f}".replace(",", ".")
    return "Preço não disponível"

def extrair_destino(texto: str) -> str:
    try:
        padroes = [
            r'(?:para|em|no|na)\s+([A-Za-zÀ-ÿ\s]+?)(?:\s+com|\s+por|\s+durante|\s*$|,)',
            r'roteiro\s+(?:de|para)\s+[A-Za-zÀ-ÿ\s]+?\s+(?:em|para)\s+([A-Za-zÀ-ÿ\s]+)'
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
        r'saindo de\s+([A-Za-zÀ-ÿ\s]+)',
        r'partindo de\s+([A-Za-zÀ-ÿ\s]+)',
        r'desde\s+([A-Za-zÀ-ÿ\s]+)',
        r'de\s+([A-Za-zÀ-ÿ\s]+)\s+(?:para|até)',
        r'saindo do\s+([A-Za-zÀ-ÿ\s]+)',
     
    ]
    for padrao in padroes:
        match = re.search(padrao, texto, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return "Origem não informada"


@app.route('/')
def index():
    return render_template('chat.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message', '').strip()
    user_id = request.remote_addr

    if user_id not in chat_context:
        chat_context[user_id] = []

    chat_context[user_id].append({"role": "user", "content": user_message})
    resposta = get_ai_response(chat_context[user_id])
    chat_context[user_id].append({"role": "model", "content": resposta})

    destino = extrair_destino(user_message)
    origem = extrair_origem(user_message)

    if origem == "Origem não informada":
        return jsonify({'response': resposta + "\n\n✋ Por favor, informe a cidade de origem para que eu possa sugerir transportes ou voos."})

    if destino.lower() != "destino não informado":
        codigo_destino = buscar_codigo_iata(destino)
        codigo_origem = buscar_codigo_iata(origem)
        data_partida = datetime.datetime.now().strftime("%Y-%m-%d")

        coord_origem = CITY_COORDINATES.get(origem.lower())
        coord_destino = CITY_COORDINATES.get(destino.lower())
        distancia_km = None
        if coord_origem and coord_destino:
            distancia_km = geodesic(coord_origem, coord_destino).km

        if distancia_km and distancia_km < 200:
            resposta += f" A distância entre {origem.title()} e {destino.title()} é de aproximadamente {distancia_km:.1f} km. Não há voos disponíveis, mas você pode ir de carro, ônibus ou trem."
        else:
            voos = get_flights(codigo_origem, codigo_destino, data_partida)
            if voos.get("data"):
                resposta += f"\n\n✈️ Opções de voos de {origem} para {destino}:\n"
                for i, voo in enumerate(voos["data"][:3], 1):
                    segmento = voo["itineraries"][0]["segments"][0]
                    horario = segmento["departure"]["at"][11:16]
                    companhia = segmento["carrierCode"]
                    preco = format_price(voo.get("price", {}))
                    resposta += f"\n• Voo {i}: {companhia}, saída às {horario}, preço: {preco}"
            else:
                resposta += f"\n\n⚠️ Nenhum voo encontrado de {origem} para {destino} no momento."

    return jsonify({'response': resposta})

if __name__ == '__main__':
    app.run(debug=True)
