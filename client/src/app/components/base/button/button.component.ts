import { Component, EventEmitter, input, Input, Output } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';


@Component({
  selector: 'app-button',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    MatIconModule,
    MatButtonModule,
    MatFormFieldModule
  
  ],

  templateUrl: './button.component.html',
  styleUrl: './button.component.scss'
})
export class ButtonComponent {
  @Input() type: string;
  @Input() icon: string;
  @Input() label: string;
  @Input() color: string = 'var(--text-primary)';
  @Input() disabled: boolean = true;
  @Input() backgroundColor: string = 'var(--bg-primary)';
  @Input() focusOnTab: boolean  =true;
  @Input() onlyOnMouseClick: boolean  = false;
  @Input() submit: boolean = false;
  @Input() size: string = 'medium';
  @Output() buttonClickedEvent = new EventEmitter<void>();


  onClick(): void {
    if(!this.onlyOnMouseClick){
       this.buttonClickedEvent.emit();}
  }

  onClickMouse(): void {
    if(this.onlyOnMouseClick){
      this.buttonClickedEvent.emit();}
    }
  
}


