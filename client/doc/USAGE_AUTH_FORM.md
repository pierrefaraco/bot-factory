# Guide d'utilisation du composant AuthForm

## Vue d'ensemble

Le composant `auth-form` est un composant Angular standalone moderne qui fournit une interface élégante et animée pour l'authentification des utilisateurs avec deux modes : **Login** et **Signup**.

## Caractéristiques principales

- ✨ Design moderne inspiré des tendances actuelles
- 🎨 Cohérent avec la palette de couleurs de l'application (Indigo #6366f1)
- 🔄 Animations fluides lors du passage entre Login et Signup
- 📱 Responsive et adaptatif
- ♿ Accessible avec support du clavier
- 🎭 Support complet des thèmes dark/light
- ✅ Validation de formulaire avec messages d'erreur personnalisés
- 🔐 Validation de correspondance des mots de passe

## Import du composant

```typescript
import { AuthFormComponent, LoginData, SignupData } from './components/auth-form/auth-form.component';
```

## Utilisation basique

### Dans votre composant parent

```typescript
import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { AuthFormComponent, LoginData, SignupData } from './components/auth-form/auth-form.component';
import { AuthService } from './services/auth.service';

@Component({
  selector: 'app-auth-page',
  standalone: true,
  imports: [AuthFormComponent],
  template: `
    <app-auth-form
      (loginSubmitted)="onLogin($event)"
      (signupSubmitted)="onSignup($event)">
    </app-auth-form>
  `
})
export class AuthPageComponent {
  constructor(
    private authService: AuthService,
    private router: Router
  ) {}

  onLogin(loginData: LoginData): void {
    console.log('Login data:', loginData);

    this.authService.login(loginData.email, loginData.password)
      .subscribe({
        next: (response) => {
          console.log('Login successful:', response);
          this.router.navigate(['/workspace']);
        },
        error: (error) => {
          console.error('Login error:', error);
          // Gérer l'erreur (afficher un message, etc.)
        }
      });
  }

  onSignup(signupData: SignupData): void {
    console.log('Signup data:', signupData);

    this.authService.register(
      signupData.email,
      signupData.password,
      signupData.firstName,
      signupData.lastName
    ).subscribe({
      next: (response) => {
        console.log('Signup successful:', response);
        // Rediriger vers la page de login ou directement vers le workspace
        this.router.navigate(['/workspace']);
      },
      error: (error) => {
        console.error('Signup error:', error);
        // Gérer l'erreur (afficher un message, etc.)
      }
    });
  }
}
```

## Interfaces de données

### LoginData

```typescript
interface LoginData {
  email: string;
  password: string;
}
```

### SignupData

```typescript
interface SignupData {
  firstName: string;
  lastName: string;
  email: string;
  password: string;
  confirmPassword: string;
}
```

## Événements

### @Output loginSubmitted

Émis lorsque l'utilisateur soumet le formulaire de connexion.

**Type:** `EventEmitter<LoginData>`

**Exemple:**
```typescript
onLogin(data: LoginData) {
  console.log('Email:', data.email);
  console.log('Password:', data.password);
}
```

### @Output signupSubmitted

Émis lorsque l'utilisateur soumet le formulaire d'inscription.

**Type:** `EventEmitter<SignupData>`

**Exemple:**
```typescript
onSignup(data: SignupData) {
  console.log('First Name:', data.firstName);
  console.log('Last Name:', data.lastName);
  console.log('Email:', data.email);
  console.log('Password:', data.password);
  console.log('Confirm Password:', data.confirmPassword);
}
```

## Validation des formulaires

### Formulaire de connexion

- **Email:** Requis, format email valide
- **Mot de passe:** Requis, minimum 6 caractères

### Formulaire d'inscription

- **Prénom:** Requis, minimum 2 caractères
- **Nom:** Requis, minimum 2 caractères
- **Email:** Requis, format email valide
- **Mot de passe:** Requis, minimum 6 caractères
- **Confirmation mot de passe:** Requis, doit correspondre au mot de passe

## Ajout à vos routes

```typescript
// app.routes.ts
import { Routes } from '@angular/router';
import { AuthPageComponent } from './components/auth-page/auth-page.component';

export const routes: Routes = [
  {
    path: 'auth',
    component: AuthPageComponent
  },
  // ... autres routes
];
```

## Personnalisation

### Thèmes

Le composant utilise automatiquement les variables CSS définies dans vos fichiers de thème:

- `--btn-primary-bg`
- `--btn-primary-text`
- `--text-primary`
- `--text-secondary`
- `--input-bg`
- `--input-border`
- `--input-focus-border`
- Etc.

### Bouton de connexion sociale (optionnel)

Le composant inclut un bouton "Continuer avec Google" que vous pouvez personnaliser ou étendre pour d'autres providers :

```typescript
// Dans votre composant parent, vous pouvez ajouter des gestionnaires pour l'authentification sociale
```

## Exemple complet avec gestion d'erreurs

```typescript
import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { AuthFormComponent, LoginData, SignupData } from './components/auth-form/auth-form.component';
import { AuthService } from './services/auth.service';

@Component({
  selector: 'app-auth-page',
  standalone: true,
  imports: [CommonModule, AuthFormComponent],
  template: `
    <div class="auth-page-wrapper">
      <!-- Message d'erreur global -->
      <div *ngIf="errorMessage" class="error-banner">
        {{ errorMessage }}
      </div>

      <app-auth-form
        (loginSubmitted)="onLogin($event)"
        (signupSubmitted)="onSignup($event)">
      </app-auth-form>
    </div>
  `,
  styles: [`
    .auth-page-wrapper {
      position: relative;
    }

    .error-banner {
      position: fixed;
      top: 1rem;
      left: 50%;
      transform: translateX(-50%);
      padding: 1rem 1.5rem;
      background: var(--error-color);
      color: white;
      border-radius: 0.5rem;
      box-shadow: var(--shadow-lg);
      z-index: 1000;
      animation: slideDown 0.3s ease-out;
    }

    @keyframes slideDown {
      from {
        opacity: 0;
        transform: translateX(-50%) translateY(-20px);
      }
      to {
        opacity: 1;
        transform: translateX(-50%) translateY(0);
      }
    }
  `]
})
export class AuthPageComponent {
  errorMessage = '';

  constructor(
    private authService: AuthService,
    private router: Router
  ) {}

  onLogin(loginData: LoginData): void {
    this.errorMessage = '';

    this.authService.login(loginData.email, loginData.password)
      .subscribe({
        next: () => {
          this.router.navigate(['/workspace']);
        },
        error: (error) => {
          this.errorMessage = error.error?.message || 'Identifiants invalides';
          this.clearErrorAfterDelay();
        }
      });
  }

  onSignup(signupData: SignupData): void {
    this.errorMessage = '';

    this.authService.register(
      signupData.email,
      signupData.password,
      signupData.firstName,
      signupData.lastName
    ).subscribe({
      next: () => {
        this.router.navigate(['/workspace']);
      },
      error: (error) => {
        this.errorMessage = error.error?.message || 'Erreur lors de l\'inscription';
        this.clearErrorAfterDelay();
      }
    });
  }

  private clearErrorAfterDelay(): void {
    setTimeout(() => {
      this.errorMessage = '';
    }, 5000);
  }
}
```

## Intégration avec le AuthService existant

Le composant est compatible avec votre `AuthService` actuel. Assurez-vous simplement que votre service a les méthodes suivantes :

```typescript
// auth.service.ts
export class AuthService {
  login(email: string, password: string): Observable<any> {
    // Votre implémentation
  }

  register(email: string, password: string, firstName: string, lastName: string): Observable<any> {
    // Votre implémentation
  }
}
```

## Accessibilité

Le composant est conçu avec l'accessibilité à l'esprit :

- Support complet du clavier
- Focus visible pour la navigation au clavier
- Messages d'erreur associés aux champs de formulaire
- Labels appropriés pour tous les champs
- Contraste de couleurs conforme aux normes WCAG

## Support des navigateurs

Le composant fonctionne sur tous les navigateurs modernes :

- Chrome/Edge (dernières versions)
- Firefox (dernières versions)
- Safari (dernières versions)
- Opera (dernières versions)

## Notes importantes

1. Les animations utilisent l'API Angular Animations, assurez-vous d'avoir `@angular/animations` dans vos dépendances
2. Le composant utilise les composants de base existants (`FormFieldComponent` et `ButtonComponent`)
3. Le design s'adapte automatiquement aux thèmes dark/light de votre application
4. Les formulaires sont réinitialisés automatiquement lors du changement de mode

## Dépannage

### Les animations ne fonctionnent pas

Assurez-vous que `provideAnimations()` est bien présent dans votre configuration d'application :

```typescript
// app.config.ts
import { provideAnimations } from '@angular/platform-browser/animations';

export const appConfig: ApplicationConfig = {
  providers: [
    provideAnimations(),
    // ... autres providers
  ]
};
```

### Les styles ne s'appliquent pas correctement

Vérifiez que vos variables CSS de thème sont bien définies dans `src/styles/dark-theme.scss` et `src/styles/light-theme.scss`.

### Problème avec FormFieldComponent

Si vous rencontrez des problèmes avec le `FormFieldComponent`, vérifiez que le composant accepte bien les inputs suivants :
- `[control]` - FormControl
- `name` - string
- `label` - string
- `type` - string
- `[errorMessage]` - string
