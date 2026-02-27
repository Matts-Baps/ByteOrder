FROM node:20-slim AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --ignore-scripts
RUN node -e " \
  const fs = require('fs'), p = require('path'); \
  const dirs = ['node_modules/@esbuild', 'node_modules/esbuild/node_modules/@esbuild']; \
  let src = null; \
  for (const d of dirs) { \
    if (!fs.existsSync(d)) continue; \
    for (const sub of fs.readdirSync(d)) { \
      const c = p.join(d, sub, 'bin', 'esbuild'); \
      if (fs.existsSync(c)) { src = c; break; } \
    } \
    if (src) break; \
  } \
  if (!src) throw new Error('esbuild binary not found'); \
  fs.mkdirSync('node_modules/esbuild/bin', { recursive: true }); \
  fs.copyFileSync(src, 'node_modules/esbuild/bin/esbuild'); \
  fs.chmodSync('node_modules/esbuild/bin/esbuild', 0o755);"
COPY . .
RUN npm run build && npm prune --omit=dev

FROM node:20-slim
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/node_modules ./node_modules
COPY server ./server
COPY --from=builder /app/dist ./dist
EXPOSE 3001
CMD ["node", "server/index.js"]
