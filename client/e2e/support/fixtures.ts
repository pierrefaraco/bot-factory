import * as fs from 'fs';
import * as path from 'path';

export interface E2EFixtures {
  adminEmail: string;
  adminPassword: string;
  userEmail: string;
  userId: number;
  guestEmail: string;
  guestId: number;
  botId: number;
  botId2: number;
  adminBotId: number;
}

/** Reads the ids/emails global-setup.ts created, so specs never hardcode
 * fixture data that only exists for the duration of a single run. */
export function loadFixtures(): E2EFixtures {
  const p = path.join(__dirname, '..', '.auth', 'fixtures.json');
  return JSON.parse(fs.readFileSync(p, 'utf-8'));
}
