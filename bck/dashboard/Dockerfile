# syntax=docker/dockerfile:1.7

# Stage 1: build the Vite/React SPA
FROM node:20-alpine AS build

WORKDIR /app

# Enable pnpm via corepack (no global install needed)
RUN corepack enable

# Install deps first for better layer caching
COPY package.json ./
COPY pnpm-lock.yaml* ./
RUN pnpm install --no-frozen-lockfile

# Build the static bundle into /app/dist
COPY tsconfig*.json vite.config.ts index.html eslint.config.js ./
COPY public ./public
COPY src ./src
RUN pnpm build

# Stage 2: serve via nginx
FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -q -O /dev/null http://127.0.0.1/ || exit 1
