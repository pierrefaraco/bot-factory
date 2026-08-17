import { HttpInterceptorFn, HttpRequest, HttpHandlerFn, HttpErrorResponse,HttpEvent } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError } from 'rxjs/operators';
import { throwError,Observable } from 'rxjs';
import { AuthService } from '../services/auth.service';
import { JwtService } from '../services/jwt.service';
import { Router } from '@angular/router';
import { ErrorNotificationService } from '../services/error-notification.service';


export function errorInterceptor(req: HttpRequest<unknown>, next: HttpHandlerFn): Observable<HttpEvent<unknown>> {
  const errorNotificationService = inject(ErrorNotificationService);

  // Le 401 des requêtes d'auth (mauvais mot de passe, token Google invalide...)
  // est un vrai échec à afficher à l'utilisateur, pas une session expirée :
  // pas de redirection en jeu ici (jwtInterceptor ne déconnecte/redirige pas
  // pour ces requêtes non plus, cf. plus bas), donc pas de raison de le
  // masquer comme les 401 de session.
  const isAuthRequest = req.url.includes('/auth/login') ||
    req.url.includes('/auth/register') ||
    req.url.includes('/auth/google');

  return next(req).pipe(
    catchError((error: HttpErrorResponse) => {
      console.error('Erreur de la requête:', error);
      // Le 401 hors requêtes d'auth est déjà géré par jwtInterceptor
      // (déconnexion + redirection vers /auth) : un popup d'erreur en plus
      // serait juste du bruit pendant cette redirection.
      if (error.status !== 401 || isAuthRequest) {
        errorNotificationService.showError(error);
      }
      return throwError(() => error);
    })
  );
}

export const jwtInterceptor:HttpInterceptorFn  = (req: HttpRequest<unknown>, next: HttpHandlerFn) => {
  const authService = inject(AuthService);
  const jwtService = inject(JwtService);
  const router = inject(Router);

  console.debug('Intercepting request:', req.url); // Debug log

  const token = jwtService.getJwtToken();

  // Ne pas ajouter le token pour les requêtes d'authentification, et ne pas
  // traiter leur 401 comme une session expirée (déconnexion + redirection) :
  // un mauvais mot de passe sur /auth/login n'est pas une session qui expire,
  // c'est un échec de connexion que l'utilisateur doit voir sur place
  // (cf. errorInterceptor, qui affiche son popup pour ce même cas).
  const isAuthRequest = req.url.includes('/auth/login') ||
    req.url.includes('/auth/register') ||
    req.url.includes('/auth/google') ||
    req.url.includes('api.elevenlabs.io');

  if (token && !isAuthRequest) {
    req = req.clone({
      setHeaders: {
        Authorization: `Bearer ${token}`
      }
    });
    console.debug('Modified headers:', req.headers); // Debug log
  }

  return next(req).pipe(
    catchError((error: HttpErrorResponse) => {
      if (error.status === 401 && !isAuthRequest) {
        console.log('401 error detected, logging out...'); // Debug log
        authService.logout();
        router.navigate(['/auth']);
      }
      return throwError(() => error);
    })
  );
};