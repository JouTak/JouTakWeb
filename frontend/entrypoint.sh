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
API_ORIGIN="$(printf "%s" "$REACT_APP_API_URL" | sed -E 's#^(https?://[^/]+).*#\1#')"
ESCAPED_API_ORIGIN="$(printf "%s" "$API_ORIGIN" | sed 's/[\\|&]/\\&/g')"
OTEL_TRACES_URL="${OTEL_EXPORTER_OTLP_TRACES_ENDPOINT:-}"
OTEL_SERVICE_NAME_VALUE="${OTEL_SERVICE_NAME:-}"

if [ -n "$OTEL_TRACES_URL" ] && ! printf "%s" "$OTEL_TRACES_URL" | grep -Eq '^https?://[^[:space:]]+$'; then
  echo "Error: OTEL_EXPORTER_OTLP_TRACES_ENDPOINT must be an absolute http(s) URL."
  exit 1
fi

if [ -n "$OTEL_TRACES_URL" ]; then
  ESCAPED_OTEL_TRACES_URL="$(printf "%s" "$OTEL_TRACES_URL" | sed 's/[\\|&]/\\&/g')"
  OTEL_ORIGIN="$(printf "%s" "$OTEL_TRACES_URL" | sed -E 's#^(https?://[^/]+).*#\1#')"
else
  ESCAPED_OTEL_TRACES_URL=""
  OTEL_ORIGIN=""
fi

ESCAPED_OTEL_ORIGIN="$(printf "%s" "$OTEL_ORIGIN" | sed 's/[\\|&]/\\&/g')"
ESCAPED_OTEL_SERVICE_NAME="$(printf "%s" "$OTEL_SERVICE_NAME_VALUE" | sed 's/[\\|&]/\\&/g')"

# All runtime placeholders share the `__JOUTAK_RUNTIME_*__` prefix. The
# prefix is namespaced enough that the substitution cannot collide with
# user-authored string literals. Keep this invariant: never introduce a
# placeholder without the prefix.
find /usr/share/nginx/html -type f -name "*.js" -exec \
  sed -i "s|__JOUTAK_RUNTIME_API_URL__|$ESCAPED_API_URL|g" {} \;

find /usr/share/nginx/html -type f -name "*.js" -exec \
  sed -i "s|__JOUTAK_RUNTIME_OTEL_EXPORTER_OTLP_TRACES_ENDPOINT__|$ESCAPED_OTEL_TRACES_URL|g" {} \;

find /usr/share/nginx/html -type f -name "*.js" -exec \
  sed -i "s|__JOUTAK_RUNTIME_OTEL_SERVICE_NAME__|$ESCAPED_OTEL_SERVICE_NAME|g" {} \;

sed -i "s|__JOUTAK_RUNTIME_CSP_API_ORIGIN__|$ESCAPED_API_ORIGIN|g" \
  /etc/nginx/conf.d/default.conf
sed -i "s|__JOUTAK_RUNTIME_CSP_OTEL_ORIGIN__|$ESCAPED_OTEL_ORIGIN|g" \
  /etc/nginx/conf.d/default.conf

# Any remaining `__JOUTAK_RUNTIME_*__` placeholder signals a bug: either
# we forgot to substitute it above, or someone hand-wrote the reserved
# prefix somewhere in the build output. Either way, refuse to start.
if grep -R "__JOUTAK_RUNTIME_[A-Z0-9_]*__" /usr/share/nginx/html >/dev/null 2>&1; then
  echo "Error: Unresolved __JOUTAK_RUNTIME_*__ placeholder left in the static bundle."
  grep -R "__JOUTAK_RUNTIME_[A-Z0-9_]*__" /usr/share/nginx/html | head -n 20 || true
  exit 1
fi

if grep -R "__JOUTAK_RUNTIME_[A-Z0-9_]*__" /etc/nginx/conf.d >/dev/null 2>&1; then
  echo "Error: Unresolved __JOUTAK_RUNTIME_*__ placeholder left in the nginx config."
  exit 1
fi

echo "Substitution complete. Starting Nginx..."
exec "$@"
