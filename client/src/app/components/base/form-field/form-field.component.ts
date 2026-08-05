import { CommonModule } from '@angular/common';
import { Component, Input, Output, EventEmitter, OnInit, OnChanges, SimpleChanges } from '@angular/core';
import { FormControl, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { ButtonComponent } from '../button/button.component';

@Component({
  selector: 'app-form-field',
  standalone: true,
  imports: [
    CommonModule,
    
    FormsModule,
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
    ButtonComponent
  ],
  templateUrl: './form-field.component.html',
  styleUrl: './form-field.component.scss'
})
export class FormFieldComponent implements OnInit {
  

  
  @Input() control: FormControl =  null;
  @Input() name: string;
  @Input() label: string;
  @Input() errorMessage: string;
  @Input() type: string = 'text';
  @Input() disabled: boolean = false;
  @Input() buttonIcon: string = '';
  @Input() buttonLabel: string = '';
  @Input() buttonBackgroundColor = '';
  @Output() my_change = new EventEmitter<void>();
  @Output() buttonClick = new EventEmitter<void>();
  showPassword = true;

  ngOnInit(): void {
    if(this.type === 'password'){
      this.showPassword = false;
    }
    
  }

  onMychange($event):void{
    console.log("onChange", $event);
    this.my_change.emit($event);
     
  }

  clearField(): void {
    this.control?.reset();
  }

  hasError() {
    return this.control?.invalid;
  }

  togglePasswordVisibility():void {
    this.showPassword = !this.showPassword;
  }

  onInputChange(): void {
    console.log("onInputChange")
    this.control?.markAsTouched();
    this.control?.parent.updateValueAndValidity();
  }

  onButtonClick(): void {
    this.buttonClick.emit();
  }
}

