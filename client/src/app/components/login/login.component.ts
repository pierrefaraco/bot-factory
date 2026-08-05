// src/app/components/login/login.component.ts
import { Component, OnInit, AfterViewInit } from '@angular/core';
import { RouterModule } from '@angular/router';
import { FormControl, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, AbstractControl } from '@angular/forms';
import { Router, ActivatedRoute } from '@angular/router';
import { first } from 'rxjs/operators';
import { AuthService } from '../../services/auth.service';
import { FormFieldComponent } from '../base/form-field/form-field.component';
import { ButtonComponent } from '../base/button/button.component';
import { MatDialog } from '@angular/material/dialog';
import { UsersService } from '@app/services/users.service';
import { UserDialogComponent } from '../admin/user-dialog/user-dialog.component';
import { User } from '@app/models/user.model';
import { firstValueFrom } from 'rxjs/internal/firstValueFrom';
declare const google: any;


@Component({
  selector: 'app-login',
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.css'],
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule, RouterModule, FormFieldComponent, ButtonComponent]  // Ajoutez ce fichier si vous avez des styles spécifiques
})
export class LoginComponent implements OnInit, AfterViewInit {
  loginForm!: FormGroup;
  loading = false;
  submitted = false;
  error = '';
  returnUrl: string = '/';
  emailCtrl = new FormControl('', [Validators.required, Validators.email])
  passwordCtrl = new FormControl('', [Validators.required, Validators.minLength(3)])
  private readonly GOOGLE_CLIENT_ID = '913568537440-clfeb4jvitdh7111s1j8cv6u8gb6t3dv.apps.googleusercontent.com'
  constructor(
    private formBuilder: FormBuilder,
    private route: ActivatedRoute,
    private router: Router,
    private authService: AuthService,
    private dialog: MatDialog,
    private usersService: UsersService
  ) {
    if (this.authService.isAuthenticated()) {
      this.router.navigate(['/workspace']);
    }
  }

  ngOnInit(): void {
    this.loginForm = this.formBuilder.group({
      email: this.emailCtrl,
      password: this.passwordCtrl
    });

    // obtenir l'url de retour des paramètres de route ou utiliser '/' par défaut
    this.returnUrl = this.route.snapshot.queryParams['returnUrl'] || '/';
  }

  ngAfterViewInit(): void {
    // Initialize Google Sign-In
    if (typeof google !== 'undefined') {
      google.accounts.id.initialize({
        client_id: this.GOOGLE_CLIENT_ID,
        callback: (response: any) => this.handleGoogleLogin(response),
        auto_select: false,
        cancel_on_tap_outside: true,
        context: 'signin', // ou 'signup', 'use'
        ux_mode: 'popup' // ou 'redirect'
      });

      google.accounts.id.renderButton(
        document.getElementById('google-button-container'),
        {
          theme: 'outline',
          size: 'large',
          width: 300,
          text: 'signin_with',
          shape: 'rectangular'
        }
      );
    }

  }



  get email(): AbstractControl {
    return this.loginForm.get('email')!;
  }

  get password(): AbstractControl {
    return this.loginForm.get('password')!;
  }

  onSubmit(): void {
    console.log('onSubmit')
    this.submitted = true;
    if (this.loginForm.invalid) {
      return;
    }

    this.loading = true;
    this.authService.login(this.email.value, this.password.value)
      .pipe(first())
      .subscribe({
        next: () => {
          this.router.navigate(["/workspace"]);
          this.loading = false;
        },
        error: error => {
          this.error = error.error?.message || 'Identifiants invalides';
          this.loading = false;
        }
      });
  }

  handleGoogleLogin(response: any): void {
    this.loading = true;
    this.error = '';
    console.log('response :', response)
    this.authService.loginWithGoogle(response.credential)
      .pipe(first())
      .subscribe({
        next: () => {
          this.router.navigate(["/workspace"]);
          // this.router.navigate([this.returnUrl]);
          this.loading = false;
        },
        error: error => {
          this.error = error.error?.message || 'Échec de la connexion avec Google';
          this.loading = false;
        }
      });
  }


  on_open_create_modal() {
    const dialogRef = this.dialog.open(UserDialogComponent, {
      data: { isEditing: false, user: this.createEmptyUser() },

    });

    dialogRef.afterClosed().subscribe(user => {
      console.log(user)
      if (user) {
        console.log(user)
        this.usersService.registerUser(user)
          .subscribe({
            next: () => {
              this.router.navigate(['/login'], {
                queryParams: { registered: true }
              });
            },
            error: (error) => {
              this.error = error.error?.message || 'Une erreur est survenue lors de l\'inscription';
              this.loading = false;
            }
          });
      }
    });
  }

  createEmptyUser(): User {
    return {
      id: -1,
      email: '',
      password: '',
      name: '',
      roles: '',
      parent_id: -1,
      is_active: false,
      selected_bot_id: -1
    };
  }
}