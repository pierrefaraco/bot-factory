#!/bin/sh
# Runs as an nginx:alpine docker-entrypoint.d hook (see the base image's
# /docker-entrypoint.sh, which execs every executable *.sh file here before
# starting nginx -- same mechanism as the image's own
# 20-envsubst-on-templates.sh). Regenerates assets/env.js from the
# GOOGLE_CLIENT_ID env var (see docker-compose.yml / repo-root .env) so it
# can be changed per environment without rebuilding the image. Leaves the
# built-in dev default in place (client/src/assets/env.js) if the var isn't
# set. Must NOT exec nginx itself -- that's the base entrypoint's job, once
# every hook here has run.
set -e

if [ -n "$GOOGLE_CLIENT_ID" ]; then
  cat > /usr/share/nginx/html/assets/env.js <<EOF
window.__env = {
  GOOGLE_CLIENT_ID: '${GOOGLE_CLIENT_ID}'
};
EOF
fi
