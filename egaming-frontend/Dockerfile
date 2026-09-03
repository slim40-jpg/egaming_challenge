# frontend/Dockerfile

# Pin a current, patched Node.js Alpine base image to reduce known OS vulnerabilities.
FROM node:20-alpine3.20 AS builder

WORKDIR /app

# Copy package files first for better layer caching.
COPY package*.json ./

# Install all dependencies needed for the build, but keep the runtime image lean.
RUN npm ci

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Production image
FROM node:20-alpine3.20 AS runner

WORKDIR /app

ENV NODE_ENV=production

# Copy built application
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/node_modules ./node_modules

# Expose port
EXPOSE 3000

# Run the application
CMD ["npm", "run" , "start"]