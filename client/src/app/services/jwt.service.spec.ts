import { TestBed } from '@angular/core/testing';

import { JwtService } from './jwt.service';
import { fakeJwt } from '../testing/fake-jwt';

describe('JwtService', () => {
  let service: JwtService;

  beforeEach(() => {
    localStorage.clear();
    service = TestBed.inject(JwtService);
  });

  afterEach(() => localStorage.clear());

  it('reads the token from localStorage', () => {
    expect(service.getJwtToken()).toBeNull();

    localStorage.setItem('token', 'abc');

    expect(service.getJwtToken()).toBe('abc');
  });

  it('decodes the payload of a token', () => {
    const payload = service.decodeToken(fakeJwt({ sub: '7', roles: 'admin' }));

    expect(payload?.sub).toBe('7');
    expect(payload?.roles).toBe('admin');
  });

  it('returns null for a malformed or empty token instead of throwing', () => {
    expect(service.decodeToken('not-a-jwt')).toBeNull();
    expect(service.decodeToken('')).toBeNull();
  });

  it('gives the expiration date from the exp claim', () => {
    const token = fakeJwt({ exp: 2_000_000_000 });

    expect(service.getTokenExpirationDate(token)).toEqual(new Date(2_000_000_000 * 1000));
  });

  it('tells a valid token from an expired one', () => {
    expect(service.isTokenExpired(fakeJwt({}, 3600))).toBeFalse();
    expect(service.isTokenExpired(fakeJwt({}, -1))).toBeTrue();
  });

  it('treats an undecodable token as expired', () => {
    expect(service.isTokenExpired('not-a-jwt')).toBeTrue();
  });
});
