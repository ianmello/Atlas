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
            'timestamp': self.timestamp.strftime("%d/%m/%Y %H:%M:%S") if self.timestamp else None,
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