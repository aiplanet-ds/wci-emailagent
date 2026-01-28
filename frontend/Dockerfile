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

# Use the specified env file: copy it to .env and remove .env.production
# so Vite doesn't override with production values during build
RUN if [ "${ENV_FILE}" != ".env" ]; then cp ${ENV_FILE} .env; fi && \
    if [ "${ENV_FILE}" != ".env.production" ]; then rm -f .env.production; fi

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

