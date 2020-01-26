FROM node:11

COPY package.json ./

RUN npm install

COPY server.js ./
COPY views/ ./views/

CMD ["node", "server.js"]