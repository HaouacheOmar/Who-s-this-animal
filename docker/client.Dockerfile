FROM node:23-alpine
WORKDIR /app
COPY client/package.json client/package-lock.json ./
RUN npm ci
COPY client .
EXPOSE 5173
CMD ["npm", "run", "dev"]
