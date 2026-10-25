# frontend/Dockerfile

# ── Build stage ──────────────────────────────────────────────────────────────
FROM node:20-slim AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# VITE_BACKEND_URL is baked into the Vite output at build time.
# Pass it as a build ARG from docker-compose or the CI environment.
ARG VITE_BACKEND_URL=http://localhost:8000
ENV VITE_BACKEND_URL=$VITE_BACKEND_URL

RUN npm run build

# ── Serve stage ───────────────────────────────────────────────────────────────
FROM nginx:alpine AS serve

# Rewrite all paths to index.html so React Router works correctly.
COPY nginx.conf /etc/nginx/conf.d/default.conf

COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
