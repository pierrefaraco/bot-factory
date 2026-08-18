import { Injectable } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';
import { SuccessToastComponent, SuccessToastData } from '../components/base/success-toast/success-toast.component';

const TOAST_DURATION_MS = 4500;

@Injectable({
  providedIn: 'root'
})
export class SuccessNotificationService {

  constructor(private snackBar: MatSnackBar) { }

  showSuccess(message: string): void {
    this.snackBar.openFromComponent<SuccessToastComponent, SuccessToastData>(SuccessToastComponent, {
      data: { message },
      duration: TOAST_DURATION_MS,
      horizontalPosition: 'end',
      verticalPosition: 'bottom',
      panelClass: ['success-toast-panel'],
    });
  }
}
