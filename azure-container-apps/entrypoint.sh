#!/bin/sh
# Entrypoint script for frontend container
# Replaces BACKEND_URL_PLACEHOLDER with actual backend URL from environment variable

# Check if BACKEND_URL is set
if [ -z "$BACKEND_URL" ]; then
    echo "ERROR: BACKEND_URL environment variable is not set"
    echo "Set it to your backend Container App URL, e.g., https://wci-backend.azurecontainerapps.io"
    exit 1
fi

# Replace placeholder in nginx config with actual backend URL
sed -i "s|BACKEND_URL_PLACEHOLDER|${BACKEND_URL}|g" /etc/nginx/conf.d/default.conf

echo "Configured backend URL: $BACKEND_URL"

# Start nginx
exec nginx -g 'daemon off;'
