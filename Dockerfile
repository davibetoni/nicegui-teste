# Use uma imagem base Python oficial leve
FROM python:3.10-slim-buster

# Define o diretório de trabalho dentro do contêiner
WORKDIR /app

# Copia os arquivos de requisitos para o contêiner
# Isso otimiza o cache do Docker: se os requisitos não mudarem, ele não reinstala
COPY requirements.txt .

# Instala as dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o restante do código do seu projeto para o contêiner
COPY . .

# Expõe a porta que o NiceGUI usará
EXPOSE 8080

# Define o comando padrão para rodar o aplicativo NiceGUI
CMD ["python", "app.py"]