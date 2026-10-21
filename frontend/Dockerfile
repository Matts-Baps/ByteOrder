FROM node:24-slim AS builder
# Update npm to get patched bundled deps (tar, minimatch, glob, cross-spawn).
RUN npm install -g npm@latest
WORKDIR /app
COPY package*.json ./
RUN --mount=type=cache,target=/root/.npm,sharing=locked \
    npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
# Upgrade Alpine packages to get patched zlib and libpng.
RUN apk upgrade --no-cache
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
# Switches browser telemetry on at container start when configured (#62).
COPY --chmod=755 docker-entrypoint.d/40-byteorder-browser-telemetry.sh /docker-entrypoint.d/
EXPOSE 80
