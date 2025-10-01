# 🌎 Atlas - Assistente de Viagens

**Projeto de Trabalho de Conclusão de Curso (TCC)**

Atlas é um assistente de viagens inteligente que ajuda os usuários a planejar roteiros, encontrar voos, obter informações sobre hotéis e verificar condições climáticas para seus destinos. Uma inteligência artificial inovadora voltada para o planejamento de viagens de forma interativa e personalizada.

## 🚀 Funcionalidades

- **Planejamento de Roteiros**: Receba sugestões personalizadas de roteiros turísticos
- **Informações de Voos**: Consulte preços e horários de voos entre cidades
- **Sugestões de Hotéis**: Descubra opções de hospedagem no seu destino
- **Previsão do Tempo**: Verifique o clima durante o período da sua viagem
- **Histórico de Buscas**: Acesse suas consultas anteriores
- **Cotação de Moedas**: Acompanhe a cotação atual do dólar e outras moedas

## 🛠️ Tecnologias

- **Backend**: Python, Flask
- **Frontend**: HTML, CSS, JavaScript
- **APIs**:
  - Google Gemini AI: para geração de conteúdo personalizado
  - Amadeus API: para informações de voos e hotéis
  - OpenWeatherMap: para previsão do tempo
  - Banco Central do Brasil: para cotação de moedas

## 📋 Requisitos

- Python 3.8+
- Pip (gerenciador de pacotes Python)
- Chaves de API para:
  - Google Gemini
  - Amadeus
  - OpenWeatherMap

## 🔧 Instalação

1. Clone o repositório:
   ```bash
   git clone --branch atlas_v0 --single-branch https://github.com/ianmello/Atlas.git
   cd Atlas
   ```

2. Instale as dependências:
   ```
   pip install -r requirements.txt
   ```

3. Copie o arquivo de exemplo e configure suas chaves de API:
   ```bash
   cp .env.example .env
   ```
   
   Edite o arquivo `.env` com suas chaves:
   ```env
   SUPABASE_URL=sua_url_aqui
   SUPABASE_ANON_KEY=sua_chave_aqui
   GEMINI_API_KEY=sua_chave_aqui
   AMADEUS_CLIENT_ID=sua_chave_aqui
   AMADEUS_CLIENT_SECRET=sua_chave_aqui
   OPENWEATHER_API_KEY=sua_chave_aqui
   SECRET_KEY=chave_secreta_para_sessoes
   ```

4. Execute o aplicativo:
   ```
   python app.py
   ```

5. Acesse o aplicativo em seu navegador:
   ```
   http://localhost:8000
   ```

## 📱 Como Usar

1. Acesse a página inicial e digite sua consulta na caixa de texto
2. Exemplos de perguntas:
   - "Quero um roteiro de 4 dias em Recife saindo de São Paulo"
   - "Preciso de dicas de pontos turísticos em Curitiba"
   - "Quais são as opções de viagem de Brasília para Salvador em dezembro?"

## 🔜 Próximos Passos

- Integração para visualização de voos e hotéis
- Arquitetura em nuvem para utilização das APIs
- Análise preditiva
- Personalização de preferências do usuário
