import { TestBed } from '@angular/core/testing';
import { ActivatedRouteSnapshot, Router, RouterStateSnapshot } from '@angular/router';

import { AuthGuard } from './auth.guard';
import { AuthService } from '../services/auth.service';
import { JwtPayload } from '../services/jwt.service';

describe('AuthGuard', () => {
  let guard: AuthGuard;
  let router: jasmine.SpyObj<Router>;
  let currentJwt: JwtPayload | null;
  const route = {} as ActivatedRouteSnapshot;
  const state = { url: '/bots' } as RouterStateSnapshot;

  beforeEach(() => {
    router = jasmine.createSpyObj<Router>('Router', ['navigate']);
    currentJwt = null;
    const authService = { get currentjwtValue() { return currentJwt; } };

    TestBed.configureTestingModule({
      providers: [
        { provide: Router, useValue: router },
        { provide: AuthService, useValue: authService },
      ],
    });
    guard = TestBed.inject(AuthGuard);
  });

  it('lets a logged-in user through', () => {
    currentJwt = { sub: '42' } as JwtPayload;

    expect(guard.canActivate(route, state)).toBeTrue();
    expect(router.navigate).not.toHaveBeenCalled();
  });

  it('sends an anonymous user to /auth, remembering where they were going', () => {
    expect(guard.canActivate(route, state)).toBeFalse();
    expect(router.navigate).toHaveBeenCalledWith(['/auth'], { queryParams: { returnUrl: '/bots' } });
  });
});
