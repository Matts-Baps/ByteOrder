FROM node:20-slim AS builder
# Update npm to get patched bundled deps (tar, minimatch, glob, cross-spawn).
RUN npm install -g npm@latest
WORKDIR /app
COPY package*.json ./
RUN --mount=type=cache,target=/root/.npm,sharing=locked \
    npm ci
COPY . .
RUN npm run build && \
    npm prune --omit=dev

FROM node:20-slim
# Update npm to get patched bundled deps in the runtime image too.
RUN npm install -g npm@latest
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/node_modules ./node_modules
COPY server ./server
COPY --from=builder /app/dist ./dist
USER node
EXPOSE 3001
CMD ["node", "server/index.js"]
