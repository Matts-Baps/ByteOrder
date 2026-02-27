FROM node:20-slim AS builder
WORKDIR /app
COPY package*.json ./
RUN --mount=type=cache,target=/root/.npm,sharing=locked \
    npm ci --ignore-scripts
COPY . .
RUN ARCH=$(node -p process.arch) && \
    mkdir -p node_modules/esbuild/bin && \
    cp node_modules/@esbuild/linux-${ARCH}/bin/esbuild node_modules/esbuild/bin/esbuild && \
    npm run build && \
    npm prune --omit=dev

FROM node:20-slim
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/node_modules ./node_modules
COPY server ./server
COPY --from=builder /app/dist ./dist
EXPOSE 3001
CMD ["node", "server/index.js"]
