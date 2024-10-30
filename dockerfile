# Use uma imagem base Python
FROM python:3.10


# Defina o diretório de trabalho
WORKDIR /app

# Copie o projeto para o contêiner
COPY . .

# Instale as dependências
RUN pip install --no-cache-dir -r requirements.txt

# Comando para iniciar a aplicação FastAPI
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
