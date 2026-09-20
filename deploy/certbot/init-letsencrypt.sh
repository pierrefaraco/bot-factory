#!/usr/bin/env bash
# One-time bootstrap for HTTPS in production: obtains the first Let's
# Encrypt certificate for $DOMAIN and gets the "reverse-proxy" service
# serving it. Run once from the repo root on the production host -- see
# deploy/README.md for the full walkthrough. Safe to re-run (certbot skips
# domains that already have a certificate that isn't close to expiring,
# unless --force-renewal below is removed).
set -euo pipefail

cd "$(dirname "$0")/../.."  # repo root

if [ -f .env ]; then
  set -a; . ./.env; set +a
fi

: "${DOMAIN:?Set DOMAIN in .env first (the FQDN pointing at this server)}"
: "${LETSENCRYPT_EMAIL:?Set LETSENCRYPT_EMAIL in .env first (contact email for certificate renewal/abuse notices)}"

COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml"
CERT_DIR="/etc/letsencrypt/live/$DOMAIN"

STAGING_ARG=""
if [ "${LETSENCRYPT_STAGING:-0}" = "1" ]; then
  STAGING_ARG="--staging"
  echo "### Using Let's Encrypt STAGING environment (untrusted test certs, no rate limits)."
fi

echo "### Creating a dummy self-signed certificate for $DOMAIN so nginx can start ..."
$COMPOSE run --rm --entrypoint sh certbot -c "
  mkdir -p '$CERT_DIR' &&
  openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
    -keyout '$CERT_DIR/privkey.pem' \
    -out '$CERT_DIR/fullchain.pem' \
    -subj '/CN=localhost'
"

echo "### Starting reverse-proxy with the dummy certificate ..."
$COMPOSE up -d reverse-proxy

# "up -d" returns as soon as the container process starts, not once nginx has
# actually loaded the certificate -- deleting the dummy cert before that
# happens crashes nginx (it re-reads the cert on every restart) and leaves it
# permanently unable to start, since it now has no certificate at all. Wait
# for the nginx master process to actually be running first.
echo "### Waiting for reverse-proxy to finish starting ..."
for i in $(seq 1 30); do
  if $COMPOSE exec -T reverse-proxy pgrep -x nginx >/dev/null 2>&1; then
    break
  fi
  if [ "$i" = 30 ]; then
    echo "### reverse-proxy did not start in time -- check 'docker compose logs reverse-proxy'." >&2
    exit 1
  fi
  sleep 1
done

echo "### Deleting dummy certificate ..."
$COMPOSE run --rm --entrypoint sh certbot -c "
  rm -rf '/etc/letsencrypt/live/$DOMAIN' \
         '/etc/letsencrypt/archive/$DOMAIN' \
         '/etc/letsencrypt/renewal/$DOMAIN.conf'
"

echo "### Requesting the real Let's Encrypt certificate for $DOMAIN ..."
$COMPOSE run --rm --entrypoint certbot certbot certonly \
  --webroot -w /var/www/certbot \
  $STAGING_ARG \
  --email "$LETSENCRYPT_EMAIL" \
  -d "$DOMAIN" \
  --rsa-key-size 2048 \
  --agree-tos \
  --no-eff-email \
  --force-renewal

echo "### Reloading reverse-proxy with the real certificate ..."
$COMPOSE exec reverse-proxy nginx -s reload

echo "### Done. HTTPS should now be live at https://$DOMAIN"
