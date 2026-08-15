import { Injectable } from '@angular/core';
import { Router, CanActivate, ActivatedRouteSnapshot, RouterStateSnapshot } from '@angular/router';
import { AuthService } from '../services/auth.service';

@Injectable({
  providedIn: 'root'
})
export class AuthGuard implements CanActivate {
  
  constructor(
    private router: Router,
    private authService: AuthService
  ) {}

  canActivate(
    route: ActivatedRouteSnapshot,
    state: RouterStateSnapshot
  ): boolean {
    const currentUser = this.authService.currentjwtValue;
    if (currentUser) {
      return true;
    }

    this.router.navigate(['/auth'], { queryParams: { returnUrl: state.url } });
    return false;
  }
}