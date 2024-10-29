# Use Python 3.9 para garantir compatibilidade
FROM python:3.9-slim

# Define o diretório de trabalho no contêiner
WORKDIR /app

# Copia os arquivos do projeto
COPY . /app

# Instala as dependências
RUN pip install --no-cache-dir -r requirements.txt

# Expõe a porta usada pelo FastAPI
EXPOSE 8000

# Comando para iniciar a aplicação
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
