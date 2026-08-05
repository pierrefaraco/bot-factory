// Exemple d'utilisation du composant AuthForm
// Fichier: src/app/components/auth-page-example.component.ts

import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { AuthFormComponent, LoginData, SignupData } from './auth-form/auth-form.component';
import { AuthService } from '../services/auth.service';

/**
 * Exemple de composant conteneur pour le formulaire d'authentification
 *
 * Usage dans les routes:
 * {
 *   path: 'auth',
 *   component: AuthPageExampleComponent
 * }
 */
@Component({
  selector: 'app-auth-page-example',
  standalone: true,
  imports: [CommonModule, AuthFormComponent],
  template: `
    <div class="auth-page-wrapper">
      <!-- Message d'erreur global (optionnel) -->
      <div *ngIf="errorMessage" class="error-banner" [@fadeIn]>
        <span class="error-icon">⚠</span>
        <span>{{ errorMessage }}</span>
        <button class="close-button" (click)="errorMessage = ''" aria-label="Fermer">×</button>
      </div>

      <!-- Message de succès (optionnel) -->
      <div *ngIf="successMessage" class="success-banner" [@fadeIn]>
        <span class="success-icon">✓</span>
        <span>{{ successMessage }}</span>
      </div>

      <!-- Composant d'authentification -->
      <app-auth-form
        (loginSubmitted)="onLogin($event)"
        (signupSubmitted)="onSignup($event)">
      </app-auth-form>
    </div>
  `,
  styles: [`
    .auth-page-wrapper {
      position: relative;
      width: 100%;
      height: 100vh;
    }

    .error-banner,
    .success-banner {
      position: fixed;
      top: 2rem;
      left: 50%;
      transform: translateX(-50%);
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 1rem 1.5rem;
      border-radius: 0.75rem;
      box-shadow: var(--shadow-lg);
      z-index: 1000;
      min-width: 320px;
      max-width: 500px;
      animation: slideDown 0.3s ease-out;
    }

    .error-banner {
      background: var(--error-color);
      color: white;
    }

    .success-banner {
      background: var(--success-color);
      color: white;
    }

    .error-icon,
    .success-icon {
      font-size: 1.25rem;
      font-weight: bold;
      flex-shrink: 0;
    }

    .close-button {
      margin-left: auto;
      background: none;
      border: none;
      color: white;
      font-size: 1.5rem;
      line-height: 1;
      cursor: pointer;
      padding: 0;
      width: 24px;
      height: 24px;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 0.25rem;
      transition: all var(--transition-fast);

      &:hover {
        background: rgba(255, 255, 255, 0.2);
      }

      &:focus {
        outline: 2px solid white;
        outline-offset: 2px;
      }
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

    @media (max-width: 640px) {
      .error-banner,
      .success-banner {
        top: 1rem;
        left: 1rem;
        right: 1rem;
        transform: none;
        min-width: auto;
      }

      @keyframes slideDown {
        from {
          opacity: 0;
          transform: translateY(-20px);
        }
        to {
          opacity: 1;
          transform: translateY(0);
        }
      }
    }
  `]
})
export class AuthPageExampleComponent {
  errorMessage = '';
  successMessage = '';

  constructor(
    private authService: AuthService,
    private router: Router
  ) {}

  /**
   * Gère la soumission du formulaire de connexion
   * @param loginData - Données de connexion (email, password)
   */
  onLogin(loginData: LoginData): void {
    // Réinitialiser les messages
    this.errorMessage = '';
    this.successMessage = '';

    console.log('Login attempt with:', { email: loginData.email });

    // Appel au service d'authentification
    this.authService.login(loginData.email, loginData.password)
      .subscribe({
        next: (response) => {
          console.log('Login successful:', response);
          this.successMessage = 'Connexion réussie ! Redirection...';

          // Redirection après un court délai
          setTimeout(() => {
            this.router.navigate(['/workspace']);
          }, 1000);
        },
        error: (error) => {
          console.error('Login error:', error);
          this.errorMessage = error.error?.message || 'Identifiants invalides. Veuillez réessayer.';
          this.clearErrorAfterDelay();
        }
      });
  }

  /**
   * Gère la soumission du formulaire d'inscription
   * @param signupData - Données d'inscription (firstName, lastName, email, password, confirmPassword)
   */
  onSignup(signupData: SignupData): void {
    // Réinitialiser les messages
    this.errorMessage = '';
    this.successMessage = '';

    console.log('Signup attempt with:', {
      firstName: signupData.firstName,
      lastName: signupData.lastName,
      email: signupData.email
    });

    // Appel au service d'inscription
    // Note: Adaptez cette méthode selon votre AuthService
    this.authService.register(
      signupData.email,
      signupData.password,
      signupData.firstName,
      signupData.lastName
    ).subscribe({
      next: (response) => {
        console.log('Signup successful:', response);
        this.successMessage = 'Inscription réussie ! Redirection...';

        // Redirection après un court délai
        setTimeout(() => {
          // Vous pouvez rediriger vers /login ou directement vers /workspace
          this.router.navigate(['/workspace']);
        }, 1000);
      },
      error: (error) => {
        console.error('Signup error:', error);

        // Gestion des différents types d'erreurs
        if (error.status === 409) {
          this.errorMessage = 'Cet email est déjà utilisé.';
        } else if (error.status === 400) {
          this.errorMessage = error.error?.message || 'Données invalides. Veuillez vérifier vos informations.';
        } else {
          this.errorMessage = 'Une erreur est survenue lors de l\'inscription. Veuillez réessayer.';
        }

        this.clearErrorAfterDelay();
      }
    });
  }

  /**
   * Efface le message d'erreur après un délai
   */
  private clearErrorAfterDelay(): void {
    setTimeout(() => {
      this.errorMessage = '';
    }, 5000);
  }
}

// ============================================================================
// ALTERNATIVE: Version simplifiée sans gestion d'erreurs visuelles
// ============================================================================

/**
 * Version simplifiée du composant conteneur
 * Utilise uniquement la console pour les logs et erreurs
 */
/*
@Component({
  selector: 'app-auth-page-simple',
  standalone: true,
  imports: [AuthFormComponent],
  template: `
    <app-auth-form
      (loginSubmitted)="onLogin($event)"
      (signupSubmitted)="onSignup($event)">
    </app-auth-form>
  `
})
export class AuthPageSimpleComponent {
  constructor(
    private authService: AuthService,
    private router: Router
  ) {}

  onLogin(loginData: LoginData): void {
    this.authService.login(loginData.email, loginData.password)
      .subscribe({
        next: () => this.router.navigate(['/workspace']),
        error: (error) => console.error('Login error:', error)
      });
  }

  onSignup(signupData: SignupData): void {
    this.authService.register(
      signupData.email,
      signupData.password,
      signupData.firstName,
      signupData.lastName
    ).subscribe({
      next: () => this.router.navigate(['/workspace']),
      error: (error) => console.error('Signup error:', error)
    });
  }
}
*/
