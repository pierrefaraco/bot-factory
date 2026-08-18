import { HttpInterceptorFn, HttpRequest, HttpHandlerFn, HttpEvent, HttpEventType, HttpResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { Observable } from 'rxjs';
import { tap } from 'rxjs/operators';
import { SuccessNotificationService } from '../services/success-notification.service';

// Header purement frontend : un appelant peut le poser pour couper le toast
// sur une requête précise (ex. sauvegarde silencieuse en arrière-plan). Il
// n'a aucun sens côté backend et est retiré du clone avant l'envoi.
export const SKIP_SUCCESS_NOTIFICATION_HEADER = 'X-Skip-Success-Notification';

// Endpoints dont le succès n'est pas un "enregistrement" au sens où
// l'utilisateur l'entend (échange de chat, synthèse vocale...) : un toast
// serait juste du bruit ici plutôt qu'une confirmation utile.
const EXCLUDED_URL_SEGMENTS = ['/rag/', '/text-to-speech/', '/auth/register'];

// Association segment d'URL -> message affiché, vérifiée dans l'ordre : les
// segments les plus spécifiques ('/bot-parameters') doivent précéder les
// plus génériques ('/bot') pour ne pas être masqués par eux.
const URL_MESSAGE_MAP: ReadonlyArray<readonly [string, string]> = [
  ['/auth/login', 'Connexion réussie.'],
  ['/bot-parameters', 'Paramètres du bot enregistrés.'],
  ['/bot-assignment', 'Attribution du bot mise à jour.'],
  ['/knowledge', 'Base de connaissances mise à jour.'],
  ['/avatar', 'Avatar mis à jour.'],
  ['/users-admin', 'Utilisateur mis à jour.'],
  ['/deactivate', 'Compte désactivé.'],
  ['/activate', 'Compte activé.'],
  ['/users', 'Utilisateur mis à jour.'],
  ['/bot', 'Bot enregistré.'],
];

export function resolveSuccessMessage(url: string): string | null {
  const path = url.split('?')[0];

  if (EXCLUDED_URL_SEGMENTS.some(segment => path.includes(segment))) {
    return null;
  }

  const match = URL_MESSAGE_MAP.find(([segment]) => path.includes(segment));
  return match ? match[1] : 'Vos modifications ont été enregistrées.';
}

export const successNotificationInterceptor: HttpInterceptorFn = (
  req: HttpRequest<unknown>,
  next: HttpHandlerFn
): Observable<HttpEvent<unknown>> => {
  const successNotificationService = inject(SuccessNotificationService);

  const skipRequested = req.headers.has(SKIP_SUCCESS_NOTIFICATION_HEADER);
  if (skipRequested) {
    req = req.clone({ headers: req.headers.delete(SKIP_SUCCESS_NOTIFICATION_HEADER) });
  }

  const isTargetMethod = req.method === 'POST' || req.method === 'PUT' || req.method === 'PATCH';
  if (!isTargetMethod || skipRequested) {
    return next(req);
  }

  return next(req).pipe(
    tap((event: HttpEvent<unknown>) => {
      if (event.type !== HttpEventType.Response) {
        return;
      }

      const response = event as HttpResponse<unknown>;
      if (response.status < 200 || response.status >= 300) {
        return;
      }

      const message = resolveSuccessMessage(req.url);
      if (message) {
        successNotificationService.showSuccess(message);
      }
    })
  );
};
