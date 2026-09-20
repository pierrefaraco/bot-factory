# HTTPS in production

`docker-compose.prod.yml` adds a public, TLS-terminating nginx reverse proxy
in front of the `web` service, with certificates obtained and renewed
automatically by [Certbot](https://certbot.eff.org/) (Let's Encrypt). The
base `docker-compose.yml` stays dev-friendly and unchanged; this is an
additive overlay, only used in production.

```
Internet --80/443--> reverse-proxy (nginx, TLS) --8080--> web (nginx, SPA + /api/ proxy) --444--> api
```

`db`, `chromadb`, `api` and `web` all publish their ports on `127.0.0.1`
only (see `docker-compose.yml`) -- `reverse-proxy` is the only service
reachable from outside the host, on 80 and 443.

## One-time setup

1. **DNS**: point an A (and/or AAAA) record for your domain at this
   server's public IP. Certbot's HTTP-01 challenge needs this to already
   resolve correctly -- it will fail otherwise.

2. **Firewall**: make sure only 80 and 443 are open to the internet on this
   host (e.g. `ufw allow 80,443/tcp`). The loopback-only bindings above are
   a second layer of defense, not a substitute for this.

3. **`.env`**: set, at the repo root:
   ```bash
   DOMAIN=bots.example.com
   LETSENCRYPT_EMAIL=you@example.com
   ```
   (see `.env.example` for the full list, including `LETSENCRYPT_STAGING=1`
   to test against Let's Encrypt's staging CA first and avoid tripping its
   production rate limits while you get the setup right).

   Also check `WEB_PORT`: it must stay a normal value like `8080` (the
   default). `reverse-proxy` is the one that owns 80/443 -- if `WEB_PORT`
   is set to `80` or `443`, `web`'s own `127.0.0.1:<WEB_PORT>:8080` binding
   fights `reverse-proxy` for that port and one of the two containers will
   fail to start ("address already in use").

4. **Google OAuth**: if `GOOGLE_CLIENT_ID` is set (see root `.env.example`),
   add `https://<DOMAIN>` to that OAuth client's "Authorized JavaScript
   origins" in the [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
   -- Google Identity Services rejects the popup otherwise.

5. **Build, start, and get the first certificate** (builds the images,
   starts every service except `reverse-proxy` -- which has no certificate
   yet -- then bootstraps it: a temporary self-signed cert so nginx can
   start, the real Let's Encrypt cert via the webroot challenge, and a
   reload; see `deploy/certbot/init-letsencrypt.sh` for the details):
   ```bash
   make prod-deploy
   ```

`https://<DOMAIN>` should now be live. Renewal is automatic from here on:
the `certbot` service checks twice a day and only actually renews when a
certificate is close to expiry.

## Day-to-day

```bash
# Bring the whole prod stack up (after the one-time setup above)
make prod-up

# Logs
make prod-logs

# Stop everything
make prod-down
```

## Troubleshooting

- **`init-letsencrypt.sh` fails at the "Requesting the real certificate"
  step**: almost always DNS not resolving yet, or the firewall blocking
  port 80 from Let's Encrypt's validation servers. Check both before
  re-running.
- **Rate limited**: Let's Encrypt allows a limited number of certificates
  per domain per week. Set `LETSENCRYPT_STAGING=1` in `.env` while
  iterating on the setup, then unset it and re-run
  `init-letsencrypt.sh` once for the real, trusted certificate.
- **Renewal isn't happening**: check `docker compose ... logs certbot`; the
  loop calls `certbot renew` every 12h, which is a no-op unless the
  certificate is within 30 days of expiring.
- **`docker ps` shows `80/tcp` (or `443/tcp`) on `botfactory-web` and
  `botfactory-certbot`, with no arrow / host address**: harmless. That's
  Docker's `EXPOSE`, inherited from those images' own base images
  (`nginx:alpine`, `certbot/certbot`) -- pure metadata, nothing is actually
  listening on it inside those containers, and nothing is published to the
  host. Only a mapping shown as `host:port->container_port` (with an
  arrow) is a real, host-reachable port -- that's what would conflict.
