import { Component, Inject, OnInit } from "@angular/core";
import { CommonModule } from '@angular/common';
import { FormBuilder, FormControl, FormGroup, Validators } from "@angular/forms";
import {
  MatDialogModule,
  MatDialogRef,
  MAT_DIALOG_DATA,
} from "@angular/material/dialog";

import { MatProgressSpinnerModule } from "@angular/material/progress-spinner";
import { User } from "../../../models/user.model";
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { CUSTOM_ELEMENTS_SCHEMA, NgModule } from '@angular/core';
import { ReactiveFormsModule } from '@angular/forms'
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { CustomDialogComponent } from "@app/components/base/dialog/custom-dialog/custom-dialog.component";
import { FormFieldComponent } from "@app/components/base/form-field/form-field.component";
import { ComboComponent } from "@app/components/base/combo/combo.component";
import { MultiSelectComponent } from "@app/components/base/multi-select/multi-select.component";
import { Bot } from "@app/models/bot.model";
import { BotService } from "@app/services/bot.service";

@Component({
  selector: "app-user-dialog",
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
    MultiSelectComponent,
    CustomDialogComponent,
  ],
  templateUrl: "./user-dialog.component.html",
  styleUrl: "./user-dialog.component.scss",
  schemas: [CUSTOM_ELEMENTS_SCHEMA]
})
export class UserDialogComponent implements OnInit {


  error = "";
  success = false;
  isEdit = false

  userNameCtrl: FormControl;
  emailCtrl: FormControl;
  passwordCtrl: FormControl;
  confirmPasswordCtrl: FormControl;
  selectedBotCtrl: FormControl;
  assignedBotsCtrl: FormControl;
  userForm: FormGroup;
  availableBots: Bot[] = [];
  botOptions: any[] = []; 
  constructor(
    private fb: FormBuilder,
    private botService: BotService,
    public dialogRef: MatDialogRef<UserDialogComponent>,
    @Inject(MAT_DIALOG_DATA)
    public data: {
      isEditing: boolean;
      user?: User;
    }
  ) {
    // Initialiser isEditing avant la création du formulaire
    this.isEdit = data.isEditing


  }
  ngOnInit(): void {
    this.userNameCtrl = new FormControl('', [Validators.required, Validators.minLength(3)]);
    this.emailCtrl = new FormControl('', [Validators.required, Validators.email]);
    this.selectedBotCtrl = new FormControl('');

    this.passwordCtrl = new FormControl('', this.isEdit ? [] : [Validators.required, Validators.minLength(8)])
    this.confirmPasswordCtrl = new FormControl('', this.isEdit ? [] : [Validators.required, this.confirmPasswordValidator.bind(this)])
    
    this.userForm = this.fb.group({
      name: this.userNameCtrl,
      email: this.emailCtrl,
      password: this.passwordCtrl,
      confirm_password: this.confirmPasswordCtrl,
      selected_bot_id: this.selectedBotCtrl,
    });
    
    this.initFormControls()
    this.loadAvailableBots();

  

  }

  private loadAvailableBots(): void {
    this.botService.getOwnedBots().subscribe({
      next: (bots) => {
        this.availableBots = bots;
        this.botOptions = bots.map(bot => ({ 
          value: bot.id, 
          label: `Bot #${bot.id}` 
        }));
        console.log('Bot options loaded:', this.botOptions);
      },
      error: (error) => {
        console.error('Error loading bots:', error);
      }
    });
  }

  private initFormControls(): void {
    console.log('initFormControls')
    console.log(this.isEdit)
    console.log(this.data.user)


    if (this.isEdit && this.data.user) {


      console.log('initFormControls 2')
      this.userNameCtrl.setValue(this.data.user.name)
      this.emailCtrl.setValue(this.data.user.email)
      this.selectedBotCtrl.setValue(this.data.user.selected_bot_id || -1)
    } else {
      this.selectedBotCtrl.setValue(-1)
    }

  }

  confirmPasswordValidator(control: FormControl): { [key: string]: boolean } | null {
    console.log("confirmPasswordValidator")
    if (!control.parent) {
      return null;
    }
    
    const password = control.parent.get('password')?.value;
    const confirmPassword = control.value;
    console.log(password + " / " + confirmPassword)
    
    return password === confirmPassword ? null : { passwordMismatch: true };
  }






  onSubmitFromChild() {
    if (this.userForm.valid) {
      if (this.isEdit){
        let user = {
          email: this.emailCtrl.value,
          name: this.userNameCtrl.value,
        };
        this.dialogRef.close( user );
        
    } else {
        let user = {
          email: this.emailCtrl.value,
          name: this.userNameCtrl.value,
          password: this.passwordCtrl.value,
        };
         this.dialogRef.close( user );
      }
      
  }
}

  onCancel() {
    this.dialogRef.close();
  }
}
