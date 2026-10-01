# frontend/Dockerfile

FROM node:20-alpine3.20 AS builder

WORKDIR /app

# Dependencies
COPY package*.json ./
RUN npm ci

# Source
COPY . .

# Build
RUN npm run build


# Production image
FROM node:20-alpine3.20 AS runner

WORKDIR /app

ENV NODE_ENV=production

# Standalone Next.js runtime
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3000

CMD ["node", "server.js"]