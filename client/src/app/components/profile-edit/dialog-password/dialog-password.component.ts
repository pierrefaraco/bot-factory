import { Component,  SimpleChanges } from '@angular/core';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule, FormControl } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { UsersService } from '@app/services/users.service';
import { User } from '@app/models/user.model';
import { FormFieldComponent } from '@app/components/base/form-field/form-field.component';
import { ButtonComponent } from '@app/components/base/button/button.component';
import { CustomDialogComponent } from '@app/components/base/dialog/custom-dialog/custom-dialog.component';
import { MatDialogRef } from '@angular/material/dialog';

@Component({
  selector: 'app-dialog-password',
  templateUrl: './dialog-password.component.html',
  styleUrls: ['./dialog-password.component.scss'],
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, FormFieldComponent, ButtonComponent, CustomDialogComponent]
})
export class DialogPasswordComponent  {
  passwordForm: FormGroup;
  loading = false;
  passwordLoading = false;
  error = '';
  success = false;
  currentUser: User | null = null;
  passwordError = '';
  passwordSuccess = false;
  current_password_ctrl: FormControl
  new_password_ctrl: FormControl
  new_password_confirmed_ctrl: FormControl
  constructor(
    private fb: FormBuilder,
    private usersService: UsersService,
    public dialogRef: MatDialogRef<DialogPasswordComponent>,
  ) {


    this.current_password_ctrl = new FormControl('', Validators.required),
    this.new_password_ctrl = new FormControl('', Validators.minLength(8)),
    this.new_password_confirmed_ctrl = new FormControl('', Validators.minLength(8)),

    this.passwordForm = this.fb.group({
        current_password: this.current_password_ctrl,
        new_password: this.new_password_ctrl,
        new_password_confirmed: this.new_password_confirmed_ctrl
    }, { validator: this.passwordMatchValidator });
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


  get currentPasswordControl() { return this.passwordForm.get('current_password'); }
  get newPasswordControl() { return this.passwordForm.get('new_password'); }
  get confirmPasswordControl() { return this.passwordForm.get('new_password_confirmed'); }
} 
