import { trigger, transition, style, animate } from '@angular/animations';

// Même entrée que la carte de auth-form.component.ts (`fadeIn`), extraite
// ici pour être réutilisée par les dialogues/tableaux sans dupliquer la
// définition dans chaque composant.
export const fadeInAnimation = trigger('fadeIn', [
  transition(':enter', [
    style({ opacity: 0, transform: 'translateY(10px)' }),
    animate('300ms ease-out', style({ opacity: 1, transform: 'translateY(0)' }))
  ])
]);
