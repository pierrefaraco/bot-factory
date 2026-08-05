import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AbstractControl, FormBuilder, FormControl, FormGroup, Validators } from '@angular/forms';
import { MatDialogModule, MatDialogRef, } from '@angular/material/dialog';
import { MatProgressSpinnerModule } from "@angular/material/progress-spinner";
import { CUSTOM_ELEMENTS_SCHEMA, NgModule } from '@angular/core';
import { FormsModule, ValidatorFn } from '@angular/forms';
import { ReactiveFormsModule } from '@angular/forms'
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { FormFieldComponent } from '@app/components/base/form-field/form-field.component';
import { ComboComponent } from '@app/components/base/combo/combo.component';
import { CustomDialogComponent } from '@app/components/base/dialog/custom-dialog/custom-dialog.component';



export function emailValidator(): ValidatorFn {
  return (control: AbstractControl<string>): { [key: string]: any } | null => {
    const forbidden = !control.value.endsWith('gmail.com');
    return forbidden ? { 'forbiddenEmail': { value: control.value } } : null;
  };
}

@Component({
  selector: 'app-password-dialog',
  standalone: true,
  imports: [
    CommonModule,
    MatProgressSpinnerModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    FormsModule,
    ReactiveFormsModule,
    MatButtonModule,
    FormFieldComponent,
    ComboComponent,
    CustomDialogComponent,

  ],

  templateUrl: './password-dialog.component.html',
  styleUrl: './password-dialog.component.scss',
  schemas: [CUSTOM_ELEMENTS_SCHEMA]
})
export class PasswordDialogComponent {
  match: string;
  isInValid: boolean = true
  loading = false;
  error = '';
  success = false;
  currentPasswordCtrl: FormControl;
  passwordCtrl: FormControl;
  confirmPasswordCtrl: FormControl;
  passwordForm: FormGroup;
  constructor(
    private fb: FormBuilder,
    public dialogRef: MatDialogRef<PasswordDialogComponent>,
  ) {
    this.currentPasswordCtrl = new FormControl('', [Validators.required]);
    this.passwordCtrl = new FormControl('', [Validators.required, Validators.minLength(8)]);
    this.confirmPasswordCtrl = new FormControl('', [Validators.required, this.confirmPasswordValidator.bind(this)]);

    this.passwordForm = this.fb.group({
      old_password: this.currentPasswordCtrl,
      password: this.passwordCtrl,
      confirm_password: this.confirmPasswordCtrl
    });
  }




  confirmPasswordValidator(control: FormControl): { [key: string]: boolean } | null {
    if (!control.parent) {
      return null;
    }

    const password = control.parent.get('password')?.value;
    const confirmPassword = control.value;
    return password === confirmPassword ? null : { passwordMismatch: true };
  }



  onSubmitFromChild() {
    if (this.passwordForm.valid) {
      console.log(this.currentPasswordCtrl.value)
      console.log(this.passwordCtrl.value)
      this.dialogRef.close({ old_password: this.currentPasswordCtrl.value, new_password: this.passwordCtrl.value });
    }
  }
}