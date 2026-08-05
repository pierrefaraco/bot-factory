// match-password.directive.ts
import { Directive, Input } from '@angular/core';
import { Validator, AbstractControl, ValidationErrors, NG_VALIDATORS } from '@angular/forms';

@Directive({
  selector: '[appMatchPassword]',
  providers: [
    { provide: NG_VALIDATORS, useExisting: MatchPasswordDirective, multi: true }
  ]
})
export class MatchPasswordDirective implements Validator {
  @Input('appMatchPassword') matchPassword: string;

  validate(control: AbstractControl): ValidationErrors | null {
    if (!control.parent || !control.parent.value) {
      return null;
    }

    const passwordControl = control.parent.get(this.matchPassword);
    if (!passwordControl) {
      return null;
    }

    if (passwordControl.value !== control.value) {
      return { passwordMismatch: true };
    }

    return null;
  }
}