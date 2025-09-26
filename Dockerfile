# Usa uma imagem oficial do Node.js
FROM node:18-slim

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Copia o package.json e o package-lock.json (se existir)
COPY package*.json ./

# Instala as dependências
RUN npm install

# Copia o restante dos arquivos da aplicação
COPY . .

# Comando para iniciar a aplicação
# Usa a variável de ambiente PORT, padrão para 8080 se não definida (necessário para alguns hosts como Google Cloud Run)
ENV PORT 8080
CMD [ "npm", "start" ]
