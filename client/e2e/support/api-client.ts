import { APIRequestContext } from '@playwright/test';

/** Posts to /api/auth/login and returns the raw JWT string, the same way
 * AuthService.login() consumes it client-side. */
export async function login(
  api: APIRequestContext,
  email: string,
  password: string
): Promise<string> {
  const res = await api.post('/api/auth/login', { data: { email, password } });
  if (!res.ok()) {
    throw new Error(`Login failed for ${email}: ${res.status()} ${await res.text()}`);
  }
  const body = await res.json();
  return body.token as string;
}

export function authHeaders(token: string): Record<string, string> {
  return { Authorization: `Bearer ${token}` };
}

/** Throws with the response body on non-2xx, so setup/teardown fail loudly
 * instead of leaving half-created fixtures behind. */
export async function expectOk(res: {
  ok(): boolean;
  status(): number;
  text(): Promise<string>;
}, context: string): Promise<void> {
  if (!res.ok()) {
    throw new Error(`${context}: ${res.status()} ${await res.text()}`);
  }
}
