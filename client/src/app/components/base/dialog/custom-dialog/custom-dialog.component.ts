import { CommonModule } from '@angular/common';
import { Component, CUSTOM_ELEMENTS_SCHEMA, EventEmitter, HostBinding, Input, Output } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogContent, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { ButtonComponent } from '../../button/button.component';

@Component({
  selector: 'app-custom-dialog',
  standalone: true,
  imports: [
    MatDialogModule,
    MatDialogContent,
    MatButtonModule,
    CommonModule,
    ButtonComponent
  ],
  templateUrl: './custom-dialog.component.html',
  styleUrl: './custom-dialog.component.scss',
  schemas: [CUSTOM_ELEMENTS_SCHEMA],
})
export class CustomDialogComponent {
  @Input() title: string = "";
  @Input() action: string = "";
  @Input() isInValid: boolean = false;
  @Input() fullHeight: boolean = false;
  @Input() dialogRef: MatDialogRef<any>;
  @Output() submit = new EventEmitter();
  @Output() isFormInvalidChange = new EventEmitter();

  @HostBinding('class.full-height') get isFullHeight() {
    return this.fullHeight;
  }

  constructor() {

  }

  onSubmit() {
    this.submit.emit();
  }

  onCancel() {
    this.dialogRef.close();
  }

  isFormInvalid(): boolean {
    const isInValid = true; 
    this.isFormInvalidChange.emit();
    return this.isInValid;
  }


}


