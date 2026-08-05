import { Component, CUSTOM_ELEMENTS_SCHEMA, Inject, OnChanges, OnInit, SimpleChanges } from '@angular/core';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule, FormControl } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { UsersService } from '@app/services/users.service';
import { User } from '@app/models/user.model';
import { FormFieldComponent } from '@app/components/base/form-field/form-field.component';
import { ButtonComponent } from '@app/components/base/button/button.component';
import { CustomDialogComponent } from '@app/components/base/dialog/custom-dialog/custom-dialog.component';
import {  MatDialogRef } from '@angular/material/dialog';

@Component({
  selector: 'app-dialog-account',
  templateUrl: './dialog-account.component.html',
  styleUrls: ['./dialog-account.component.scss'],
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, FormFieldComponent, ButtonComponent, CustomDialogComponent],
})
export class DialogAccountComponent implements OnInit {
  profileForm: FormGroup;
  loading = false;
  error = '';
  success = false;
  currentUser: User | null = null;
  profileError = '';
  profileSuccess = false;
  user_name_ctrl: FormControl= new FormControl('', Validators.required);
  email_ctrl: FormControl = new FormControl('', [Validators.required, Validators.email])
  constructor(
    private fb: FormBuilder,
    private usersService: UsersService,
    public dialogRef: MatDialogRef<DialogAccountComponent>,
  ) {
    
   

  }


  ngOnInit(): void {
    this.profileForm = this.fb.group({
      user_name: this.user_name_ctrl,
      email: this.email_ctrl
    });
    this.loadUserProfile();
  }



  loadUserProfile(): void {
    console.log(this.loadUserProfile)
    this.usersService.getCurrentUser().subscribe({
      next: (user) => {
        this.currentUser = user;
        this.user_name_ctrl.setValue(user.name);
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

  get usernameControl() { return this.profileForm.get('user_name'); }
  get emailControl() { return this.profileForm.get('email'); }
  
} 