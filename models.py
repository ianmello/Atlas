from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.String(100), nullable=False)
    origin = db.Column(db.String(100))
    destination = db.Column(db.String(100))
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    messages = db.relationship('Message', backref='conversation', lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'timestamp': self.timestamp.strftime("%d/%m/%Y às %H:%M") if self.timestamp else None,
            'origin': self.origin,
            'destination': self.destination,
            'start_date': self.start_date.strftime("%d/%m/%Y") if self.start_date else None,
            'end_date': self.end_date.strftime("%d/%m/%Y") if self.end_date else None,
            'messages': [message.to_dict() for message in self.messages]
        }

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_bot = db.Column(db.Boolean, default=False)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'content': self.content,
            'timestamp': self.timestamp.strftime("%H:%M"),
            'is_bot': self.is_bot
        }

def generate_conversation_title(message):
    """Gera um título apropriado baseado na mensagem do usuário"""
    message = message.lower()
    
    # Palavras-chave para identificar o tipo de consulta
    keywords = {
        'roteiro': ['roteiro', 'guia', 'itinerário', 'programação'],
        'pontos turísticos': ['pontos turísticos', 'o que visitar', 'lugares para conhecer', 'atrações'],
        'restaurantes': ['restaurantes', 'onde comer', 'gastronomia', 'comida'],
        'hotéis': ['hotéis', 'onde ficar', 'hospedagem', 'acomodação'],
        'transporte': ['voos', 'passagens', 'como chegar', 'transporte']
    }
    
    # Identificar o tipo de consulta
    query_type = None
    for key, words in keywords.items():
        if any(word in message for word in words):
            query_type = key
            break
    
    # Se não encontrou um tipo específico, usa "Viagem"
    if not query_type:
        query_type = "Viagem"
    
    # Identificar destino
    destinations = ['frança', 'eua', 'estados unidos', 'paris', 'nova york', 'rio de janeiro', 'são paulo']
    destination = None
    for dest in destinations:
        if dest in message:
            destination = dest.title()
            break
    
    # Se não encontrou destino específico, usa parte da mensagem
    if not destination:
        # Pega as primeiras 3-4 palavras após palavras-chave comuns
        common_prefixes = ['para', 'em', 'sobre', 'na', 'no']
        for prefix in common_prefixes:
            if prefix + ' ' in message:
                destination = message.split(prefix + ' ')[1].split()[0:3]
                destination = ' '.join(destination).title()
                break
    
    if not destination:
        destination = "Destino não especificado"
    
    # Montar o título
    title = f"{query_type} - {destination}"
    
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