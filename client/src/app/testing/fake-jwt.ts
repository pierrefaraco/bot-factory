import { JwtPayload } from '../services/jwt.service';

function base64Url(value: object): string {
  return btoa(JSON.stringify(value)).replace(/=+$/, '').replace(/\+/g, '-').replace(/\//g, '_');
}

/**
 * Builds a structurally valid, unsigned JWT for unit tests. The client only
 * decodes tokens (jwt-decode never checks the signature), so this is enough
 * to exercise everything but the server.
 * `expiresInSeconds` may be negative to get an already expired token.
 */
export function fakeJwt(overrides: Partial<JwtPayload> = {}, expiresInSeconds = 3600): string {
  const now = Math.floor(Date.now() / 1000);
  const payload: JwtPayload = {
    iat: now,
    nbf: now,
    exp: now + expiresInSeconds,
    jti: 'test-jti',
    type: 'access',
    sub: '42',
    roles: 'user',
    mail: 'user@example.com',
    ...overrides,
  };
  return `${base64Url({ alg: 'HS256', typ: 'JWT' })}.${base64Url(payload)}.signature`;
}
