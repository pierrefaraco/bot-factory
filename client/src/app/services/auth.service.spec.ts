import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

import { AuthService } from './auth.service';
import { API_URL } from '../constants/user-roles.constants';
import { fakeJwt } from '../testing/fake-jwt';

describe('AuthService', () => {
  let httpTesting: HttpTestingController;

  // AuthService reads localStorage in its constructor: set it up first.
  function createService(): AuthService {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    httpTesting = TestBed.inject(HttpTestingController);
    return TestBed.inject(AuthService);
  }

  beforeEach(() => {
    localStorage.clear();
    spyOn(console, 'log');
  });

  afterEach(() => {
    httpTesting.verify();
    localStorage.clear();
  });

  it('starts logged out without a token', () => {
    const service = createService();

    expect(service.currentjwtValue).toBeNull();
    expect(service.isAuthenticated()).toBeFalse();
  });

  it('restores the session from a valid token in localStorage', () => {
    localStorage.setItem('token', fakeJwt({ sub: '42' }));

    const service = createService();

    expect(service.currentjwtValue?.sub).toBe('42');
    expect(service.get_curent_user_id()).toBe(42);
    expect(service.isAuthenticated()).toBeTrue();
  });

  it('drops an expired token found in localStorage, without calling the server', () => {
    localStorage.setItem('token', fakeJwt({}, -1));

    const service = createService();

    expect(service.currentjwtValue).toBeNull();
    expect(localStorage.getItem('token')).toBeNull();
    httpTesting.expectNone(`${API_URL}/auth/logout`);
  });

  it('stores the token and publishes the user on a successful login', () => {
    const service = createService();
    const token = fakeJwt({ sub: '42', roles: 'admin' });
    let authenticated = false;
    service.isAuthenticated$.subscribe((value) => (authenticated = value));

    service.login('me@example.com', 'secret').subscribe();
    const req = httpTesting.expectOne(`${API_URL}/auth/login`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ email: 'me@example.com', password: 'secret' });
    req.flush({ token });

    expect(localStorage.getItem('token')).toBe(token);
    expect(service.currentjwtValue?.sub).toBe('42');
    expect(service.getUserRole()).toBe('admin');
    expect(authenticated).toBeTrue();
  });

  it('stores nothing when the login response has no token', () => {
    const service = createService();

    service.login('me@example.com', 'secret').subscribe();
    httpTesting.expectOne(`${API_URL}/auth/login`).flush({});

    expect(localStorage.getItem('token')).toBeNull();
    expect(service.currentjwtValue).toBeNull();
  });

  describe('logout', () => {
    it('closes the session locally right away', () => {
      localStorage.setItem('token', fakeJwt());
      const service = createService();

      service.logout();

      expect(localStorage.getItem('token')).toBeNull();
      expect(service.currentjwtValue).toBeNull();
      expect(service.isAuthenticated()).toBeFalse();
      httpTesting.expectOne(`${API_URL}/auth/logout`).flush({});
    });

    it('asks the server to revoke the token, authenticated with that token', () => {
      const token = fakeJwt();
      localStorage.setItem('token', token);
      const service = createService();

      service.logout();

      const req = httpTesting.expectOne(`${API_URL}/auth/logout`);
      expect(req.request.method).toBe('POST');
      expect(req.request.headers.get('Authorization')).toBe(`Bearer ${token}`);
      req.flush({});
    });

    it('does not call the server when there is no valid token to revoke', () => {
      const service = createService();

      service.logout();

      httpTesting.expectNone(`${API_URL}/auth/logout`);
      expect(service.currentjwtValue).toBeNull();
    });

    it('stays logged out locally even if the server call fails', () => {
      localStorage.setItem('token', fakeJwt());
      const service = createService();

      service.logout();
      httpTesting.expectOne(`${API_URL}/auth/logout`).flush({}, { status: 500, statusText: 'Server Error' });

      expect(service.currentjwtValue).toBeNull();
    });
  });
});
