# Stage 1: Build the Vite production bundle
FROM node:22-alpine AS builder

WORKDIR /app

# Build-time configuration
ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_USE_MOCKS=false

# Install npm dependencies using package lock
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# Copy frontend source code
COPY frontend/ ./

# Run production build (outputs to /app/dist)
RUN npm run build

# Stage 2: Serve with Nginx
FROM nginx:alpine

# Replace default configuration with custom SPA configuration on port 8080
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

# Copy production bundle into Nginx html directory
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
