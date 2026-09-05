FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy application source
COPY . .

# Build Angular application
RUN npm run build -- --configuration=production

# Production stage - Nginx
FROM nginx:alpine

# Template is rendered with envsubst on container start (see docker-entrypoint.d),
# substituting ${API_HOST} so the backend target can be switched without a rebuild.
ENV NGINX_ENVSUBST_TEMPLATE_DIR=/etc/nginx/templates
ENV NGINX_ENVSUBST_OUTPUT_DIR=/etc/nginx
ENV API_HOST=api

COPY nginx.conf.template /etc/nginx/templates/nginx.conf.template

# Copy built application from builder stage
COPY --from=builder /app/dist/alfred_react/browser /usr/share/nginx/html

# Run as the existing non-root "nginx" user (already created in the base
# image for worker processes). Binding to a port <1024 requires root, so
# the server listens on 8080 instead (see nginx.conf.template) -- the
# host-side mapping in docker-compose.yml stays on port 4200.
RUN chown -R nginx:nginx /usr/share/nginx/html /var/cache/nginx /var/log/nginx /etc/nginx && \
    touch /var/run/nginx.pid && \
    chown nginx:nginx /var/run/nginx.pid

USER nginx

# Expose port
EXPOSE 8080

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]
