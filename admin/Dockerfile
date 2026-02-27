FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --foreground-scripts
COPY . .
RUN npm run build

FROM node:20-alpine
WORKDIR /app
ENV NODE_ENV=production
COPY package*.json ./
RUN npm ci --omit=dev --foreground-scripts
COPY server ./server
COPY --from=builder /app/dist ./dist
EXPOSE 3001
CMD ["node", "server/index.js"]
