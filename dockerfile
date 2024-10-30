# Use a imagem Python
FROM python:3.9

# Defina o diretório de trabalho
WORKDIR /app

# Copie todos os arquivos para o container
COPY . .

# Instale as dependências
RUN pip install --no-cache-dir -r requirements.txt

# Comando para rodar a aplicação
CMD ["./start.sh"]
