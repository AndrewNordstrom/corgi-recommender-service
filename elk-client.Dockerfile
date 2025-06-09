# Multi-stage build for ELK Client
# Stage 1: Builder
FROM node:18-alpine AS builder

# Install build dependencies
RUN apk add --no-cache python3 make g++

# Set working directory
WORKDIR /app

# Copy package files
COPY frontend/package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy source code
COPY frontend/ .

# Build the application
RUN npm run build

# Stage 2: Production
FROM node:18-alpine

# Install production dependencies
RUN apk add --no-cache curl

# Create non-root user
RUN addgroup -g 1001 -S elk && \
    adduser -S elk -u 1001

# Set working directory
WORKDIR /app

# Copy built application from builder
COPY --from=builder --chown=elk:elk /app/.output ./.output
COPY --from=builder --chown=elk:elk /app/package.json ./package.json

# Install serve for static hosting
RUN npm install -g serve

# Switch to non-root user
USER elk

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:3000 || exit 1

# Serve the built application
CMD ["npx", "serve", ".output/public", "-l", "3000"] 