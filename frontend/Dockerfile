FROM node:20-slim AS builder
# Update npm to get patched bundled deps (tar, minimatch, glob, cross-spawn).
RUN npm install -g npm@latest
WORKDIR /app
COPY package*.json ./
RUN --mount=type=cache,target=/root/.npm,sharing=locked \
    npm ci
COPY . .
ARG VITE_OTEL_ENDPOINT=""
ENV VITE_OTEL_ENDPOINT=$VITE_OTEL_ENDPOINT
RUN npm run build

FROM nginx:alpine
# Upgrade Alpine packages to get patched zlib and libpng.
RUN apk upgrade --no-cache
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
