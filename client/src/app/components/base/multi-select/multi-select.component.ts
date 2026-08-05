import { Component, Input, forwardRef } from '@angular/core';
import { ControlValueAccessor, NG_VALUE_ACCESSOR, FormControl } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule } from '@angular/forms';
import { MatCheckboxModule, MatCheckboxChange } from '@angular/material/checkbox';
import { MatFormFieldModule } from '@angular/material/form-field';

export interface MultiSelectOption {
  value: any;
  label: string;
  disabled?: boolean;
}

@Component({
  selector: 'app-multi-select',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatCheckboxModule,
    MatFormFieldModule
  ],
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => MultiSelectComponent),
      multi: true
    }
  ],
  templateUrl: './multi-select.component.html',
  styleUrl: './multi-select.component.scss'
})
export class MultiSelectComponent implements ControlValueAccessor {
  @Input() options: MultiSelectOption[] = [];
  @Input() label: string = '';
  @Input() placeholder: string = 'Select options...';

  selectedValues: any[] = [];
  disabled = false;

  private onChange = (value: any[]) => {};
  private onTouched = () => {};

  public triggerTouched(): void {
    this.onTouched();
  }

  writeValue(value: any[]): void {
    this.selectedValues = value || [];
  }

  registerOnChange(fn: (value: any[]) => void): void {
    this.onChange = fn;
  }

  registerOnTouched(fn: () => void): void {
    this.onTouched = fn;
  }

  setDisabledState(isDisabled: boolean): void {
    this.disabled = isDisabled;
  }

  isSelected(value: any): boolean {
    return this.selectedValues.includes(value);
  }

  toggleOption(value: any): void {
    if (this.disabled) return;

    const index = this.selectedValues.indexOf(value);
    if (index > -1) {
      this.selectedValues.splice(index, 1);
    } else {
      this.selectedValues.push(value);
    }

    this.onChange([...this.selectedValues]);
    this.onTouched();
  }

  onCheckboxChange(event: MatCheckboxChange, value: any): void {
    if (this.disabled) return;
    
    const isChecked = event.checked;
    const index = this.selectedValues.indexOf(value);
    
    console.log('Checkbox change:', { value, isChecked, currentSelection: this.selectedValues });
    
    if (isChecked && index === -1) {
      this.selectedValues.push(value);
    } else if (!isChecked && index > -1) {
      this.selectedValues.splice(index, 1);
    }
    
    console.log('New selection:', this.selectedValues);
    this.onChange([...this.selectedValues]);
    this.onTouched();
  }

  getSelectedLabels(): string {
    if (this.selectedValues.length === 0) {
      return this.placeholder;
    }
    
    const selectedOptions = this.options.filter(option => 
      this.selectedValues.includes(option.value)
    );
    
    return selectedOptions.map(option => option.label).join(', ');
  }
}