# Build stage
FROM node:20-alpine AS build

WORKDIR /app

# Build argument to specify which env file to use
# Default to .env.production for production builds
ARG ENV_FILE=.env.production

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source files
COPY . .

# Use the specified env file as .env for Vite to use during build
# Only copy if ENV_FILE is different from .env (e.g., .env.production)
RUN if [ "${ENV_FILE}" != ".env" ]; then cp ${ENV_FILE} .env; fi

# Build the application
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built files from build stage
COPY --from=build /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

