import { ApplicationConfig, provideZoneChangeDetection } from '@angular/core';
import { provideRouter, withComponentInputBinding, withPreloading, PreloadAllModules } from '@angular/router';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { alfred_routes } from './app.routes';
import { jwtInterceptor,errorInterceptor } from './interceptors/jwt.interceptor';
import { successNotificationInterceptor } from './interceptors/success-notification.interceptor';
import { provideAnimations } from '@angular/platform-browser/animations';

export const appConfig: ApplicationConfig = {
  providers: [
    provideHttpClient(withInterceptors([errorInterceptor,jwtInterceptor,successNotificationInterceptor])),
    provideZoneChangeDetection({ eventCoalescing: true }), 
    provideRouter(
      alfred_routes, 
      withComponentInputBinding(),
      withPreloading(PreloadAllModules)
    ), 
    provideAnimations()
  ]
};