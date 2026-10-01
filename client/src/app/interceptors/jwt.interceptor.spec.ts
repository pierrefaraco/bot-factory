import { TestBed } from '@angular/core/testing';
import { HttpClient, HttpErrorResponse, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { Router } from '@angular/router';

import { errorInterceptor, jwtInterceptor } from './jwt.interceptor';
import { AuthService } from '../services/auth.service';
import { ErrorNotificationService } from '../services/error-notification.service';

describe('jwtInterceptor and errorInterceptor', () => {
  let http: HttpClient;
  let httpTesting: HttpTestingController;
  let authService: jasmine.SpyObj<AuthService>;
  let router: jasmine.SpyObj<Router>;
  let errorNotification: jasmine.SpyObj<ErrorNotificationService>;

  beforeEach(() => {
    localStorage.clear();
    authService = jasmine.createSpyObj<AuthService>('AuthService', ['logout']);
    router = jasmine.createSpyObj<Router>('Router', ['navigate']);
    errorNotification = jasmine.createSpyObj<ErrorNotificationService>('ErrorNotificationService', ['showError']);
    spyOn(console, 'error');

    TestBed.configureTestingModule({
      providers: [
        // Same order as app.config.ts.
        provideHttpClient(withInterceptors([errorInterceptor, jwtInterceptor])),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: authService },
        { provide: Router, useValue: router },
        { provide: ErrorNotificationService, useValue: errorNotification },
      ],
    });
    http = TestBed.inject(HttpClient);
    httpTesting = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpTesting.verify();
    localStorage.clear();
  });

  function failWith(url: string, status: number): void {
    http.get(url).subscribe({ error: () => {} });
    httpTesting.expectOne(url).flush({ error: 'failed' }, { status, statusText: 'Error' });
  }

  describe('Authorization header', () => {
    it('adds the Bearer token from localStorage', () => {
      localStorage.setItem('token', 'my-token');

      http.get('/api/bot').subscribe();

      const req = httpTesting.expectOne('/api/bot');
      expect(req.request.headers.get('Authorization')).toBe('Bearer my-token');
      req.flush([]);
    });

    it('sends no Authorization header without a token', () => {
      http.get('/api/bot').subscribe();

      const req = httpTesting.expectOne('/api/bot');
      expect(req.request.headers.has('Authorization')).toBeFalse();
      req.flush([]);
    });

    for (const url of ['/api/auth/login', '/api/auth/register', '/api/auth/google', 'https://api.elevenlabs.io/v1/tts']) {
      it(`does not send the token to ${url}`, () => {
        localStorage.setItem('token', 'my-token');

        http.get(url).subscribe();

        const req = httpTesting.expectOne(url);
        expect(req.request.headers.has('Authorization')).toBeFalse();
        req.flush({});
      });
    }

    it('still sends the token to /users/password/ (a protected route)', () => {
      localStorage.setItem('token', 'my-token');

      http.get('/api/users/password/42').subscribe();

      const req = httpTesting.expectOne('/api/users/password/42');
      expect(req.request.headers.get('Authorization')).toBe('Bearer my-token');
      req.flush({});
    });
  });

  describe('401 responses', () => {
    it('log out and redirect to /auth when the session expired', () => {
      failWith('/api/bot', 401);

      expect(authService.logout).toHaveBeenCalled();
      expect(router.navigate).toHaveBeenCalledWith(['/auth']);
      // The redirection is enough: no error popup on top of it.
      expect(errorNotification.showError).not.toHaveBeenCalled();
    });

    it('on a wrong password at login, show the error without logging out', () => {
      failWith('/api/auth/login', 401);

      expect(authService.logout).not.toHaveBeenCalled();
      expect(router.navigate).not.toHaveBeenCalled();
      expect(errorNotification.showError).toHaveBeenCalled();
    });

    it('on a wrong old password when changing it, show the error without logging out', () => {
      failWith('/api/users/password/42', 401);

      expect(authService.logout).not.toHaveBeenCalled();
      expect(errorNotification.showError).toHaveBeenCalled();
    });
  });

  it('shows an error popup for any other failure, and still propagates the error', () => {
    let received: HttpErrorResponse | undefined;
    http.get('/api/bot').subscribe({ error: (e) => (received = e) });
    httpTesting.expectOne('/api/bot').flush({}, { status: 500, statusText: 'Server Error' });

    expect(errorNotification.showError).toHaveBeenCalled();
    expect(authService.logout).not.toHaveBeenCalled();
    expect(received?.status).toBe(500);
  });
});
