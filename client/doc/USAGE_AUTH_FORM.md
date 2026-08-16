# AuthForm Component Usage Guide

## Overview

The `auth-form` component is a modern standalone Angular component that provides an elegant and animated UI for user authentication with two modes: Login and Signup.

## Key features

- ✨ Modern design inspired by current trends
- 🎨 Consistent with the app color palette (Indigo #6366f1)
- 🔄 Smooth animations when switching between Login and Signup
- 📱 Responsive and adaptive
- ♿ Accessible with keyboard support
- 🎭 Full dark/light theme support
- ✅ Form validation with custom error messages
- 🔐 Password match validation

## Importing the component

```typescript
import { AuthFormComponent, LoginData, SignupData } from './components/auth-form/auth-form.component';
```

## Basic usage

### In your parent component

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
          // Handle error (display message, etc.)
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
        // Redirect to login page or directly to workspace
        this.router.navigate(['/workspace']);
      },
      error: (error) => {
        console.error('Signup error:', error);
        // Handle error (display message, etc.)
      }
    });
  }
}
```

## Data interfaces

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

## Events

### @Output loginSubmitted

Emitted when the user submits the login form.

**Type:** `EventEmitter<LoginData>`

**Example:**
```typescript
onLogin(data: LoginData) {
  console.log('Email:', data.email);
  console.log('Password:', data.password);
}
```

### @Output signupSubmitted

Emitted when the user submits the signup form.

**Type:** `EventEmitter<SignupData>`

**Example:**
```typescript
onSignup(data: SignupData) {
  console.log('First Name:', data.firstName);
  console.log('Last Name:', data.lastName);
  console.log('Email:', data.email);
  console.log('Password:', data.password);
  console.log('Confirm Password:', data.confirmPassword);
}
```

## Form validation

### Login form

- **Email:** Required, valid email format
- **Password:** Required, minimum 6 characters

### Signup form

- **First name:** Required, minimum 2 characters
- **Last name:** Required, minimum 2 characters
- **Email:** Required, valid email format
- **Password:** Required, minimum 6 characters
- **Confirm password:** Required, must match the password

## Adding to your routes

```typescript
// app.routes.ts
import { Routes } from '@angular/router';
import { AuthPageComponent } from './components/auth-page/auth-page.component';

export const routes: Routes = [
  {
    path: 'auth',
    component: AuthPageComponent
  },
  // ... other routes
];
```

## Customization

### Themes

The component automatically uses the CSS variables defined in your theme files:

- `--btn-primary-bg`
- `--btn-primary-text`
- `--text-primary`
- `--text-secondary`
- `--input-bg`
- `--input-border`
- `--input-focus-border`
- Etc.

### Social sign-in button (optional)

The component includes a "Continue with Google" button you can customize or extend for other providers:

```typescript
// In your parent component, add handlers for social authentication
```

## Full example with error handling

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
      <!-- Global error message -->
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
          this.errorMessage = error.error?.message || 'Invalid credentials';
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
        this.errorMessage = error.error?.message || 'Error during signup';
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

## Integration with existing AuthService

The component is compatible with your current `AuthService`. Just ensure the service exposes these methods:

```typescript
// auth.service.ts
export class AuthService {
  login(email: string, password: string): Observable<any> {
    // Your implementation
  }

  register(email: string, password: string, firstName: string, lastName: string): Observable<any> {
    // Your implementation
  }
}
```

## Accessibility

The component is built with accessibility in mind:

- Full keyboard support
- Visible focus for keyboard navigation
- Field-level error messages
- Proper labels for all fields
- Color contrast following WCAG guidelines

## Browser support

The component works on modern browsers:

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Opera (latest)

## Important notes

1. Animations use the Angular Animations API; ensure `@angular/animations` is present in your dependencies
2. The component relies on existing base components (`FormFieldComponent` and `ButtonComponent`)
3. The design adapts automatically to your app's dark/light themes
4. Forms are reset automatically when switching modes

## Troubleshooting

### Animations not working

Ensure `provideAnimations()` is included in your application configuration:

```typescript
// app.config.ts
import { provideAnimations } from '@angular/platform-browser/animations';

export const appConfig: ApplicationConfig = {
  providers: [
    provideAnimations(),
    // ... other providers
  ]
};
```

### Styles not applying correctly

Verify your theme CSS variables are defined in `src/styles/dark-theme.scss` and `src/styles/light-theme.scss`.

### Problem with FormFieldComponent

If you encounter issues with `FormFieldComponent`, ensure it accepts the following inputs:
- `[control]` - FormControl
- `name` - string
- `label` - string
- `type` - string
- `[errorMessage]` - string
