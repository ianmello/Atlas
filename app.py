from flask import Flask, request, jsonify, render_template
import datetime
import requests
import os
from dotenv import load_dotenv
import warnings
import datetime

app = Flask(__name__)

# Configurações (mantenha as mesmas do seu código)
warnings.filterwarnings("ignore")
load_dotenv()

# ... (Cole TODAS as suas funções existentes aqui: get_exchange_rate, get_flights, etc)

EXCHANGE_API_URL = "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoMoedaDia(moeda=@moeda,dataCotacao=@dataCotacao)"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"  # Corrigido typo "completions"

FLIGHT_API_URL = "https://test.api.amadeus.com/v2/shopping/flight-offers"

def get_exchange_rate(currency: str = "USD") -> float:
    """Obtém a cotação atual da moeda para BRL"""
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
    except Exception as e:
        print(f"Erro ao obter câmbio: {e}")
        return 5.0  # Fallback para dólar a R$5.00

def get_ai_response(prompt):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://meu-planejador.com",
        "X-Title": "Planejador de Viagens AI"
    }
    data = {
        "model": "mistralai/mistral-7b-instruct",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }
    try:
        response = requests.post(OPENROUTER_URL, headers=headers, json=data)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Erro no OpenRouter: {e}")
        return None

def get_flights(origin: str, destination: str, date: str):
    try:
        # Autenticação (mantida igual)
        auth_url = "https://test.api.amadeus.com/v1/security/oauth2/token"
        auth_data = {
            "grant_type": "client_credentials",
            "client_id": os.getenv("AMADEUS_CLIENT_ID"),
            "client_secret": os.getenv("AMADEUS_CLIENT_SECRET")
        }
        auth_response = requests.post(auth_url, data=auth_data, verify=False)
        auth_response.raise_for_status()
        token = auth_response.json().get("access_token")

        # Busca de voos (mantida igual)
        params = {
            "originLocationCode": origin.upper(),
            "destinationLocationCode": destination.upper(),
            "departureDate": date,
            "adults": 1,
            "max": 5
        }
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(FLIGHT_API_URL, headers=headers, params=params, verify=False)
        response.raise_for_status()
        
        flights_data = response.json()
        
        # Nova lógica de extração e conversão de preços
        for flight in flights_data.get("data", []):
            try:
                # Extrai o preço total e moeda de forma mais robusta
                price_info = flight.get("price", {})
                total_price = str(price_info.get("grandTotal", price_info.get("total", "0")))
                currency = price_info.get("currency", "USD")
                
                # Remove caracteres não numéricos
                total_price = ''.join(c for c in total_price if c.isdigit() or c == '.')
                
                # Conversão para BRL
                if currency and currency != "BRL":
                    exchange_rate = get_exchange_rate(currency)
                    flight["price"] = {
                        "total_brl": round(float(total_price) * exchange_rate, 2),
                        "original_value": total_price,
                        "original_currency": currency,
                        "currency": "BRL"
                    }
                else:
                    flight["price"] = {
                        "total_brl": round(float(total_price), 2),
                        "currency": "BRL"
                    }
                    
            except Exception as e:
                print(f"Erro ao processar preço do voo: {e}")
                flight["price"] = {
                    "total_brl": "Preço não disponível",
                    "currency": "BRL"
                }
        
        return flights_data
    
    except Exception as e:
        print(f"Erro na API de voos: {e}")
        return {"data": []}

def generate_travel_plan(destination: str, days: int, interests: list):
    prompt = f"""
    Você é um assistente de viagens brasileiro. Crie um roteiro em PORTUGUÊS para {destination} com {days} dias, focado em: {', '.join(interests)}.
    
    Formato:
    ✈️ Roteiro para {destination}
    ---
    Dia 1: [Tema]
    ☀️ Manhã: [Atividade 1 + detalhes]
    🍽️ Almoço: [Sugestão]
    🌆 Tarde: [Atividade 2]
    🌃 Noite: [Atividade noturna + dica]
    ---
    Inclua dicas práticas como "melhor horário para visitar" e "o que levar".
    """
    response = get_ai_response(prompt)
    return response["choices"][0]["message"]["content"] if response else "Erro ao gerar roteiro"

def format_price(price_data):
    """Formata o preço de forma consistente"""
    if isinstance(price_data.get("total_brl"), (int, float)):
        return f"R$ {price_data['total_brl']:,.2f}".replace(",", ".")
    return "Preço não disponível"


@app.route('/')
def index():
    return render_template('chat.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message', '')
    
    if any(palavra in user_message.lower() for palavra in ['roteiro', 'viagem', 'dias', 'planejar', 'semanas']):
        destino = extrair_destino(user_message)
        dias = extrair_dias(user_message)
        interesses = extrair_interesses(user_message)
        
        # Gera o roteiro
        resposta = f"✈️ Roteiro para {destino} ({dias} dias) - Foco em: {', '.join(interesses)}\n\n"
        resposta += generate_travel_plan(destino, dias, interesses)
        
        # Adiciona informações de voos (exemplo com GRU como origem)
        resposta += "\n\n✈️ Opções de Voos (Exemplo GRU -> {}):\n".format(destino[:3].upper())
        flights = get_flights("GRU", destino[:3].upper(), datetime.datetime.now().strftime("%Y-%m-%d"))
        
        if flights and "data" in flights and flights["data"]:
            for i, flight in enumerate(flights["data"][:3], 1):  # Mostra até 3 voos
                price_info = flight.get("price", {})
                resposta += f"\nVoo {i}:"
                resposta += f"\n• Companhia: {flight['itineraries'][0]['segments'][0]['carrierCode']}"
                resposta += f"\n• Partida: {flight['itineraries'][0]['segments'][0]['departure']['at'][11:16]}"
                resposta += f"\n• Preço: {format_price(price_info)}"
                if "original_value" in price_info:
                    resposta += f" (Original: {price_info['original_value']} {price_info.get('original_currency', '')})"
        else:
            resposta += "\nNenhum voo encontrado para esta rota no momento."
            
    else:
        resposta = """Por favor, me diga sobre a viagem que quer planejar. Exemplos:
        - "Quero um roteiro de 5 dias em Paris com museus e restaurantes"
        - "Planeje 3 dias em São Paulo para compras e gastronomia"
        - "2 dias em Roma com foco em história\""""
    
    return jsonify({'response': resposta})

import re

def extrair_dias(texto: str) -> int:
    """Extrai o número de dias do texto do usuário"""
    try:
        # Padrões para encontrar dias (ex: "3 dias", "por 5 dias", "durante 2 dias")
        padroes = [
            r'(\d+)\s*dias?',
            r'por\s*(\d+)\s*dias?',
            r'durante\s*(\d+)\s*dias?',
            r'para\s*(\d+)\s*dias?'
        ]
        
        for padrao in padroes:
            match = re.search(padrao, texto, re.IGNORECASE)
            if match:
                return int(match.group(1))
                
        # Se não encontrar, retorna padrão 3 dias
        return 3
    except:
        return 3  # Fallback

def extrair_interesses(texto: str) -> list:
    """Extrai interesses/tópicos do texto do usuário"""
    try:
        # Palavras-chave que indicam interesses
        palavras_chave = {
            'museus': ['museu', 'museus', 'galeria', 'galerias'],
            'praias': ['praia', 'praias', 'mar', 'litoral'],
            'compras': ['compras', 'shopping', 'lojas'],
            'gastronomia': ['comida', 'restaurante', 'gastronomia', 'culinária'],
            'história': ['história', 'histórico', 'monumento', 'monumentos'],
            'natureza': ['natureza', 'parque', 'parques', 'trilha']
        }
        
        interesses = []
        texto = texto.lower()
        
        for interesse, palavras in palavras_chave.items():
            if any(palavra in texto for palavra in palavras):
                interesses.append(interesse)
        
        return interesses if interesses else ["pontos turísticos"]
    except:
        return ["pontos turísticos"]  # Fallback

def extrair_destino(texto: str) -> str:
    """Extrai o destino do texto do usuário"""
    try:
        # Padrões para encontrar o destino
        padroes = [
            r'(?:em|para|no|na|em)\s+([A-Za-zÀ-ÿ\s]+?)(?:\s+com|\s+por|\s+durante|\s*$|,)',
            r'roteiro\s+(?:de|para)\s+[A-Za-zÀ-ÿ\s]+?\s+(?:em|para)\s+([A-Za-zÀ-ÿ\s]+)'
        ]
        
        for padrao in padroes:
            match = re.search(padrao, texto, re.IGNORECASE)
            if match:
                return match.group(1).strip()
                
        return "Rio de Janeiro"  # Default
    except:
        return "Rio de Janeiro"  # Fallback
if __name__ == '__main__':
    app.run(debug=True)