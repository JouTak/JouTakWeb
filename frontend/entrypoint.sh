#!/bin/sh
set -e

echo "Starting runtime substitution for REACT_APP_API_URL..."

if [ -z "$REACT_APP_API_URL" ]; then
  echo "Error: REACT_APP_API_URL is not set. Exiting."
  exit 1
fi

if ! printf "%s" "$REACT_APP_API_URL" | grep -Eq '^https?://[^[:space:]]+$'; then
  echo "Error: REACT_APP_API_URL must be an absolute http(s) URL."
  exit 1
fi

ESCAPED_API_URL="$(printf "%s" "$REACT_APP_API_URL" | sed 's/[\\|&]/\\&/g')"

find /usr/share/nginx/html -type f -name "*.js" -exec \
  sed -i "s|__REACT_APP_API_URL__|$ESCAPED_API_URL|g" {} \;

if grep -R "__REACT_APP_API_URL__" /usr/share/nginx/html >/dev/null 2>&1; then
  echo "Error: Runtime API URL placeholder substitution is incomplete."
  exit 1
fi

echo "Substitution complete. Starting Nginx..."
exec "$@"
