import { Component, OnInit } from '@angular/core';
import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, AbstractControl } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../services/auth.service';
import { first } from 'rxjs/operators';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { UsersService } from '../../services/users.service';
@Component({
  selector: 'app-register',
  templateUrl: './register.component.html',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule, RouterModule]
})
export class RegisterComponent implements OnInit {
  registerForm!: FormGroup;
  loading = false;
  submitted = false;
  error = '';
  showPassword = false;
  showConfirmPassword = false;

  constructor(
    private formBuilder: FormBuilder,
    private router: Router,
    private authService: AuthService,
    private usersService: UsersService
  ) {
    if (this.authService.currentjwtValue) {
      this.router.navigate(['/']);
    }
  }

  ngOnInit() {
    this.registerForm = this.formBuilder.group({
      user_name: ['', Validators.required],
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required, Validators.minLength(6)]],
      confirm_password: ['', Validators.required]
    }, {
      validator: this.passwordMatchValidator
    });
  }

  // Validateur personnalisé pour vérifier que les mots de passe correspondent
  passwordMatchValidator(g: FormGroup) {
    const password = g.get('password')?.value;
    const confirmPassword = g.get('confirm_password')?.value;
    
    return password === confirmPassword ? null : { 'mismatch': true };
  }

  // Bascule la visibilité du mot de passe
  togglePasswordVisibility() {
    this.showPassword = !this.showPassword;
  }

  // Bascule la visibilité de la confirmation du mot de passe
  toggleConfirmPasswordVisibility() {
    this.showConfirmPassword = !this.showConfirmPassword;
  }

  get username(): AbstractControl {
    return this.registerForm.get('user_name')!;
  }

  get email(): AbstractControl {
    return this.registerForm.get('email')!;
  }

  get password(): AbstractControl {
    return this.registerForm.get('password')!;
  }

  get confirmPassword(): AbstractControl {
    return this.registerForm.get('confirm_password')!;
  }

  onSubmit() {
    this.submitted = true;

    if (this.registerForm.invalid) {
      return;
    }

    this.loading = true;
    console.log(this.registerForm.value)
    this.usersService.registerUser(this.registerForm.value)
      .pipe(first())
      .subscribe({
        next: () => {
          this.router.navigate(['/login'], {
            queryParams: { registered: true }
          });
        },
        error: error => {
          this.error = error.error?.message || 'Une erreur est survenue lors de l\'inscription';
          this.loading = false;
        }
      });
  }
}