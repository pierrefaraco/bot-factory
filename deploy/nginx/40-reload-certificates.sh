#!/bin/sh
# Picks up certificates renewed by the "certbot" service (see
# docker-compose.prod.yml and deploy/README.md): nginx only reads its
# certificate files at startup and on reload, so without this it would keep
# serving the one it started with until it expires.
#
# Mounted into /docker-entrypoint.d/, whose scripts the nginx:alpine
# entrypoint runs (after rendering the templates) just before starting
# nginx. It starts a background loop and returns immediately, so nginx
# starts as usual. `nginx -s reload` is graceful: new workers load the
# certificate from disk, old ones finish their open connections (including
# streamed chat answers) before exiting. Certbot renews 30 days before
# expiry, so reloading every few hours is more than enough.

set -eu

interval="${CERT_RELOAD_INTERVAL:-6h}"

echo "$0: reloading nginx every $interval to pick up renewed certificates"

# No `set -e` in the loop: a failed sleep or reload must not end it.
(
  set +e
  while :; do
    sleep "$interval"
    echo "$0: reloading nginx to pick up renewed certificates"
    nginx -s reload || echo "$0: nginx reload failed" >&2
  done
) </dev/null &
