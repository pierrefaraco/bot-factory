import { HttpInterceptorFn, HttpRequest, HttpHandlerFn, HttpErrorResponse,HttpEvent } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError } from 'rxjs/operators';
import { throwError,Observable } from 'rxjs';
import { AuthService } from '../services/auth.service';
import { JwtService } from '../services/jwt.service';
import { Router } from '@angular/router';


export function errorInterceptor(req: HttpRequest<unknown>, next: HttpHandlerFn): Observable<HttpEvent<unknown>> {
  return next(req).pipe(
    
    catchError((error: HttpErrorResponse) => {
      console.error('Erreur de la requête:', error);
      return throwError(error);
    })
  );
}

export const jwtInterceptor:HttpInterceptorFn  = (req: HttpRequest<unknown>, next: HttpHandlerFn) => {
  const authService = inject(AuthService);
  const jwtService = inject(JwtService);
  const router = inject(Router);

  console.debug('Intercepting request:', req.url); // Debug log

  const token = jwtService.getJwtToken();

  if (token) {
    // Ne pas ajouter le token pour les requêtes d'authentification
    const isAuthRequest = req.url.includes('/auth/login') || 
    req.url === '/auth/register' ||  req.url.includes('api.elevenlabs.io');

    if (!isAuthRequest) {
      req = req.clone({
        setHeaders: {
          Authorization: `Bearer ${token}`
        }
      });
      console.debug('Modified headers:', req.headers); // Debug log
    }
  }

  return next(req).pipe(
    catchError((error: HttpErrorResponse) => {
      if (error.status === 401) {
        console.log('401 error detected, logging out...'); // Debug log
        authService.logout();
        router.navigate(['/login']);
      }
      return throwError(() => error);
    })
  );
};