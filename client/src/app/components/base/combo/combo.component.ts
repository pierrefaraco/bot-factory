import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { FormControl, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { CustomOption } from '@app/models/combo-options.model';
import { map, Observable, startWith } from 'rxjs';
import { ButtonComponent } from '../button/button.component';
@Component({
  selector: 'app-combo',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule, // Ajout de ReactiveFormsModule
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
    MatSelectModule,
    ButtonComponent,
    MatAutocompleteModule
  ],
  templateUrl: './combo.component.html',
  styleUrl: './combo.component.scss'
})
export class ComboComponent implements OnInit {

  @Input() control: FormControl;
  @Input() name: string;
  @Input() label: string;
  @Input() options: CustomOption[] = [];
  @Input() errorMessage: string;
  @Input() autoComplete: boolean = false;
  @Output() my_change = new EventEmitter<void>();
  filteredOptions: Observable<CustomOption[]>;


  ngOnInit(): void {
    if (this.autoComplete) {
      this.setupFilteredObservables()
      this.record()
    }
  }
  clearField(): void {
    this.control.reset();
    setTimeout(() => {
      const botTypeInput = document.querySelector(`input[name="${this.name}"]`) as HTMLInputElement;
      if (botTypeInput) {
        botTypeInput.focus();
      }
    }, 0);
  }

  hasError() {
    // console.log("this.control.invalid: " +this.control.invalid)
    // console.log("this.name: " +this.name)
    return !this.control.valid;
  }

  private setupFilteredObservables(): void {
    this.filteredOptions = this.setupFilter(
      this.control,
      this.options
    );
  }

  private setupFilter(control: FormControl, options: CustomOption[]): Observable<CustomOption[]> {
    return control.valueChanges.pipe(
      startWith(''),
      map(value => this._filter(value || '', this.options))
    );
  }

  private _filter(value: string, options: CustomOption[]): CustomOption[] {
    const filterValue = value.toLowerCase();
    return options?.filter(option => {  return option.label.toLowerCase().includes(filterValue); });
  }

  private record() {
    this.control.valueChanges.subscribe(value => {
     
      if (value && this.isValidOption(value)) {
      } else {
        this.control.setErrors({ 'invalid': true });
      }
    });
  }

  // Vérifier si une valeur est une option valide
  private isValidOption(value:string): boolean {
    let result =this.options?.map(_option=>{return _option.label}).includes(value);
    return result
  }


  onMychange($event):void{
    console.log("onChange conbo", $event);
    this.my_change.emit($event);
     
  }

}
