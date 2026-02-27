FROM node:20-slim AS builder
WORKDIR /app
COPY package*.json ./
RUN --mount=type=cache,target=/root/.npm,sharing=locked \
    npm ci --ignore-scripts
COPY . .
RUN ARCH=$(node -p process.arch) && \
    mkdir -p node_modules/esbuild/bin && \
    cp node_modules/@esbuild/linux-${ARCH}/bin/esbuild node_modules/esbuild/bin/esbuild && \
    npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
