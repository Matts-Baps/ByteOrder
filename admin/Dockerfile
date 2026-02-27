FROM node:20-slim AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --ignore-scripts
COPY . .
#RUN ARCH=$(node -p process.arch) && \
#    ESBUILD_BINARY_PATH="/app/node_modules/@esbuild/linux-${ARCH}/bin/esbuild" \
RUN npm run build && \
    npm prune --omit=dev

FROM node:20-slim
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/node_modules ./node_modules
COPY server ./server
COPY --from=builder /app/dist ./dist
EXPOSE 3001
CMD ["node", "server/index.js"]
