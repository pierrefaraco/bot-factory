import { AfterViewInit, Component, EventEmitter, OnInit, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormControl, FormGroup, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { trigger, state, style, transition, animate } from '@angular/animations';
import { FormFieldComponent } from '../base/form-field/form-field.component';
import { ButtonComponent } from '../base/button/button.component';
import { AuthService } from '@app/services/auth.service';
import { Router } from '@angular/router';
import { User } from '@app/models/user.model';
import { UsersService } from '@app/services/users.service';
declare const google: any;
// Interface pour les données de login
export interface LoginData {
  email: string;
  password: string;
}

// Interface pour les données de signup
export interface SignupData {
  firstName: string;
  lastName: string;
  email: string;
  password: string;
  confirmPassword: string;
}

@Component({
  selector: 'app-auth-form',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    FormFieldComponent,
    ButtonComponent
  ],
  templateUrl: './auth-form.component.html',
  styleUrl: './auth-form.component.scss',
  animations: [
    trigger('slideAnimation', [
      transition('login => signup', [
        animate('300ms cubic-bezier(0.4, 0.0, 0.2, 1)', style({
          transform: 'translateX(-20px)',
          opacity: 0
        })),
        animate('300ms cubic-bezier(0.4, 0.0, 0.2, 1)', style({
          transform: 'translateX(0)',
          opacity: 1
        }))
      ]),
      transition('signup => login', [
        animate('300ms cubic-bezier(0.4, 0.0, 0.2, 1)', style({
          transform: 'translateX(20px)',
          opacity: 0
        })),
        animate('300ms cubic-bezier(0.4, 0.0, 0.2, 1)', style({
          transform: 'translateX(0)',
          opacity: 1
        }))
      ])
    ]),
    trigger('fadeIn', [
      transition(':enter', [
        style({ opacity: 0, transform: 'translateY(10px)' }),
        animate('300ms ease-out', style({ opacity: 1, transform: 'translateY(0)' }))
      ])
    ])
  ]
})
export class AuthFormComponent implements OnInit, AfterViewInit {
  @Output() loginSubmitted = new EventEmitter<LoginData>();
  @Output() signupSubmitted = new EventEmitter<SignupData>();

  isLoginMode = true;
  loginForm!: FormGroup;
  signupForm!: FormGroup;
  loginSubmitting = false;
  signupSubmitting = false;
  private readonly GOOGLE_CLIENT_ID = '913568537440-clfeb4jvitdh7111s1j8cv6u8gb6t3dv.apps.googleusercontent.com'
  constructor(private fb: FormBuilder,
    private authService: AuthService,
    private router: Router,
    private usersService: UsersService) {
    // Diagnostic au démarrage
    console.log('🔍 Configuration Google OAuth:');
    console.log('   Client ID:', this.GOOGLE_CLIENT_ID);
    console.log('   Origin:', window.location.origin);
    console.log('   URL complète:', window.location.href);
  }

  ngOnInit(): void {
    this.initializeForms();
  }

  ngAfterViewInit(): void {
    if (typeof google !== 'undefined') {
      google.accounts.id.initialize({
        client_id: this.GOOGLE_CLIENT_ID,
        callback: (response: any) => this.handleGoogleLogin(response),
        auto_select: false,              // Ne sélectionne pas automatiquement un compte
        cancel_on_tap_outside: true,     // Ferme le popup si on clique à l'extérieur
        ux_mode: 'popup',                // Mode popup (au lieu de 'redirect')
        context: 'signin',               // Contexte: 'signin', 'signup', ou 'use'
      });
    }
  }


  private initializeForms(): void {
    // Formulaire de connexion
    this.loginForm = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required, Validators.minLength(3)]]
    });

    // Formulaire d'inscription
    this.signupForm = this.fb.group({
      name: ['', [Validators.required, Validators.minLength(2)]],
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required, Validators.minLength(6)]],
      confirmPassword: ['', [Validators.required]]
    }, { validators: this.passwordMatchValidator });
  }

  // Validateur personnalisé pour vérifier que les mots de passe correspondent
  private passwordMatchValidator(group: FormGroup): { [key: string]: boolean } | null {
    const password = group.get('password');
    const confirmPassword = group.get('confirmPassword');

    if (!password || !confirmPassword) {
      return null;
    }

    return password.value === confirmPassword.value ? null : { passwordMismatch: true };
  }

  // Basculer entre les modes login et signup
  toggleMode(): void {
    this.isLoginMode = !this.isLoginMode;
    // Réinitialiser les formulaires lors du changement de mode
    this.loginForm.reset();
    this.signupForm.reset();
  }


  go_to_app(): void {
    this.router.navigate(["/workspace"]);
  }

  // Soumettre le formulaire de connexion
  onLoginSubmit(): void {
    if (this.loginForm.valid && !this.loginSubmitting) {
      this.loginSubmitting = true;
      this.authService.login(this.loginEmail.value, this.loginPassword.value)
        .subscribe({
          next: () => {
            this.go_to_app()
            this.loginSubmitting = false;
          },
          error: error => {
            console.log(error.error?.message || 'Identifiants invalides');
            this.loginSubmitting = false;
          }
        });
    } else {
      // Marquer tous les champs comme touchés pour afficher les erreurs
      Object.keys(this.loginForm.controls).forEach(key => {
        this.loginForm.get(key)?.markAsTouched();
      });
    }
  }
  loginWithGoogle(): void {
    console.log('🔑 Tentative de connexion Google...');
    console.log('   Origin actuel:', window.location.origin);
    console.log('   Client ID:', this.GOOGLE_CLIENT_ID);

    if (typeof google !== 'undefined') {
      // Ouvre le popup d'authentification Google
      google.accounts.id.prompt((notification: any) => {
        console.log('📋 Notification du prompt:', notification);

        // Gestion des notifications du prompt
        if (notification.isNotDisplayed()) {
          console.warn('⚠️ Le prompt n\'a pas été affiché:', notification.getNotDisplayedReason());
          // Raisons possibles: 'suppressed_by_user', 'unregistered_origin', 'invalid_client', etc.
        } else if (notification.isSkippedMoment()) {
          console.warn('⚠️ Le prompt a été ignoré:', notification.getSkippedReason());
          // Raisons possibles: 'user_cancel', 'tap_outside', 'issuing_failed', etc.
        } else if (notification.isDismissedMoment()) {
          console.log('ℹ️ Le prompt a été fermé:', notification.getDismissedReason());
          // Raisons possibles: 'credential_returned', 'cancel', 'flow_restarted', etc.
        }
      });
    } else {
      console.error('❌ Google SDK non chargé');
      alert('Google Sign-In is not available. Please refresh the page.');
    }
  }

  handleGoogleLogin(response: any): void {
    console.log('✅ Réponse Google reçue:', response);
    this.loginSubmitting = true;

    this.authService.loginWithGoogle(response.credential)
      .subscribe({
        next: (result) => {
          console.log('✅ Connexion réussie:', result);
             this.go_to_app()
          this.loginSubmitting = false;
        },
        error: error => {
          console.error('❌ Erreur de connexion:', error);
          const errorMessage = error.error?.message || 'Échec de la connexion avec Google';
          alert(errorMessage);
          this.loginSubmitting = false;
        }
      });
  }




  // Soumettre le formulaire d'inscription
  onSignupSubmit(): void {
    if (this.signupForm.valid && !this.signupSubmitting) {
      this.signupSubmitting = true;
      let user = {

        email: this.signupForm.value.email,
        password: this.signupForm.value.password,
        name: this.signupForm.value.name,

      };
      if (user) {
        console.log(user)
        this.usersService.registerUser(user)
          .subscribe({
            next: () => {
              this.signupSubmitting = false;
              this.router.navigate(['/auth'], {

                queryParams: { registered: true }
              });
              this.toggleMode()

            },
            error: (error) => {
              this.signupSubmitting = false;
            }
          });
      }

    }
  }

  // Getters pour faciliter l'accès aux contrôles du formulaire de connexion
  get loginEmail(): FormControl {
    return this.loginForm.get('email') as FormControl;
  }

  get loginPassword(): FormControl {
    return this.loginForm.get('password') as FormControl;
  }

  // Getters pour faciliter l'accès aux contrôles du formulaire d'inscription
  get signupFirstName(): FormControl {
    return this.signupForm.get('firstName') as FormControl;
  }

  get signupLastName(): FormControl {
    return this.signupForm.get('lastName') as FormControl;
  }

  get signupEmail(): FormControl {
    return this.signupForm.get('email') as FormControl;
  }

  get signupPassword(): FormControl {
    return this.signupForm.get('password') as FormControl;
  }

  get signupName(): FormControl {
    return this.signupForm.get('name') as FormControl;
  }


  get signupConfirmPassword(): FormControl {
    return this.signupForm.get('confirmPassword') as FormControl;
  }

  // Vérifier si les mots de passe correspondent dans le formulaire d'inscription
  get passwordsMatch(): boolean {
    const password = this.signupForm.get('password')?.value;
    const confirmPassword = this.signupForm.get('confirmPassword')?.value;
    return password === confirmPassword;
  }

  // Messages d'erreur personnalisés
  getErrorMessage(controlName: string, formType: 'login' | 'signup'): string {
    const control = formType === 'login'
      ? this.loginForm.get(controlName)
      : this.signupForm.get(controlName);

    if (!control || !control.touched || !control.errors) {
      return '';
    }

    if (control.errors['required']) {
      return 'This field is required';
    }

    if (control.errors['email']) {
      return 'Invalid email';
    }

    if (control.errors['minlength']) {
      const minLength = control.errors['minlength'].requiredLength;
      return `Minimum ${minLength} characters required`;
    }

    if (controlName === 'confirmPassword' && this.signupForm.errors?.['passwordMismatch']) {
      return 'Passwords do not match';
    }

    return '';
  }
}
