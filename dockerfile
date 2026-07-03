FROM node:20-slim

# Install the stress utility
RUN apt-get update && apt-get install -y stress-ng && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy package manifests and install production dependencies
COPY package*.json ./
RUN npm ci --only=production

# Copy application source code
COPY server.js .

# Expose port 8080 to match the application's configuration
EXPOSE 8080

# Switch to the built-in non-root 'node' user for security best practices in Kubernetes
USER node

CMD ["node", "server.js"]