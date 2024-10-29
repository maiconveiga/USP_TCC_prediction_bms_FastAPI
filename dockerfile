# Use a imagem Python
FROM python:3.9

# Defina o diretório de trabalho
WORKDIR /app

# Copie os arquivos necessários para o container
COPY . /app

# Instale as dependências
RUN pip install --no-cache-dir -r requirements.txt

# Exponha a porta que o Uvicorn usará
EXPOSE 8000

# Comando para rodar a aplicação
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
