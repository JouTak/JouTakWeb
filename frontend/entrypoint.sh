#!/bin/sh
set -e

echo "Starting runtime substitution for REACT_APP_API_URL..."

if [ -z "$REACT_APP_API_URL" ]; then
  echo "Error: REACT_APP_API_URL is not set. Exiting."
  exit 1
fi

find /usr/share/nginx/html -type f -name "*.js" -exec sed -i "s|__REACT_APP_API_URL__|$REACT_APP_API_URL|g" {} \;

echo "Substitution complete. Starting Nginx..."
exec "$@"