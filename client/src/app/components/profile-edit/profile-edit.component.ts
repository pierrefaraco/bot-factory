import { Component, OnChanges, OnInit, SimpleChanges } from '@angular/core';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule, FormControl } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { UsersService } from '../../services/users.service';
import { User } from '../../models/user.model';
import { finalize } from 'rxjs/operators';
import { FormFieldComponent } from '../base/form-field/form-field.component';
import { ButtonComponent } from '../base/button/button.component';
import { CustomDialogComponent } from '../base/dialog/custom-dialog/custom-dialog.component';
import { MatDialogRef } from '@angular/material/dialog';

@Component({
  selector: 'app-profile-edit',
  templateUrl: './profile-edit.component.html',
  styleUrls: ['./profile-edit.component.scss'],
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, FormFieldComponent, ButtonComponent, CustomDialogComponent]
})
export class ProfileEditComponent implements OnInit {
  profileForm: FormGroup;
  passwordForm: FormGroup;
  loading = false;
  passwordLoading = false;
  error = '';
  success = false;
  currentUser: User | null = null;
  profileError = '';
  passwordError = '';
  profileSuccess = false;
  passwordSuccess = false;
  user_name_ctrl: FormControl;
  email_ctrl: FormControl
  current_password_ctrl: FormControl
  new_password_ctrl: FormControl
  new_password_confirmed_ctrl: FormControl
  constructor(
    private fb: FormBuilder,
    private usersService: UsersService,
    public dialogRef: MatDialogRef<ProfileEditComponent>,
  ) {
    this.user_name_ctrl = new FormControl('', Validators.required),
      this.email_ctrl = new FormControl('', [Validators.required, Validators.email])


    this.profileForm = this.fb.group({
      user_name: this.user_name_ctrl,
      email: this.email_ctrl
    });


    this.current_password_ctrl = new FormControl('', Validators.required),
    this.new_password_ctrl = new FormControl('', Validators.minLength(8)),
    this.new_password_confirmed_ctrl = new FormControl('', Validators.minLength(8)),

    this.passwordForm = this.fb.group({
        current_password: this.current_password_ctrl,
        new_password: this.new_password_ctrl,
        new_password_confirmed: this.new_password_confirmed_ctrl
    }, { validator: this.passwordMatchValidator });
  }

  ngOnChanges(changes: SimpleChanges): void {
    this.profileForm.markAllAsTouched()
    console.log(changes)
    console.log("ngOnChanges")
  }

  ngOnInit(): void {
    this.loadUserProfile();
  }



  loadUserProfile(): void {
    this.usersService.getCurrentUser().subscribe({
      next: (user) => {
        this.currentUser = user;
        this.user_name_ctrl.setValue(user.user_name);
        this.email_ctrl.setValue(user.email)

      },
      error: (error) => {
        this.error = error.error?.message || error.message || 'An error occurred';
      }
    });
  }

  onProfileSubmit() {
    if (this.profileForm.valid) {
      this.loading = true;
      this.profileError = '';

      this.usersService.updateProfile(this.profileForm.value).subscribe(
        () => {
          this.profileSuccess = true;
          this.loading = false;
        },
        error => {
          this.profileError = error.error?.message || error.message || 'An error occurred';
          this.loading = false;
        }
      );
    }
  }

  onPasswordSubmit() {
    console.log("onPasswordSubmit")
    if (this.passwordForm.valid) {
      this.passwordLoading = true;
      this.passwordError = '';

      this.usersService.updateProfilePassword({
        old_password: this.passwordForm.value.current_password,
        new_password: this.passwordForm.value.new_password,
      }).subscribe(
        () => {
          this.passwordSuccess = true;
          this.passwordLoading = false;
          this.passwordForm.reset();
        },
        error => {
          this.passwordError = error.error?.message || error.message || 'An error occurred';
          this.passwordLoading = false;
        }
      );
    }
    else{

    }
  }

  passwordMatchValidator(g: FormGroup) {
    return g.get('new_password')?.value === g.get('new_password_confirmed')?.value
      ? null
      : { mismatch: true };
  }

  get usernameControl() { return this.profileForm.get('user_name'); }
  get emailControl() { return this.profileForm.get('email'); }
  get currentPasswordControl() { return this.passwordForm.get('current_password'); }
  get newPasswordControl() { return this.passwordForm.get('new_password'); }
  get confirmPasswordControl() { return this.passwordForm.get('new_password_confirmed'); }
} 