FROM node:20-slim AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --ignore-scripts
RUN node -e " \
  const fs = require('fs'); \
  const arch = process.arch === 'arm64' ? 'linux-arm64' : 'linux-x64'; \
  fs.copyFileSync('node_modules/@esbuild/' + arch + '/bin/esbuild', 'node_modules/esbuild/bin/esbuild'); \
  fs.chmodSync('node_modules/esbuild/bin/esbuild', 0o755);"
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
