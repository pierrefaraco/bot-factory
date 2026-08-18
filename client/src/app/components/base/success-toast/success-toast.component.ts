import { CommonModule } from '@angular/common';
import { Component, Inject } from '@angular/core';
import { MAT_SNACK_BAR_DATA, MatSnackBarRef } from '@angular/material/snack-bar';

export interface SuccessToastData {
  message: string;
}

@Component({
  selector: 'app-success-toast',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './success-toast.component.html',
  styleUrl: './success-toast.component.scss',
})
export class SuccessToastComponent {
  constructor(
    @Inject(MAT_SNACK_BAR_DATA) public data: SuccessToastData,
    private snackBarRef: MatSnackBarRef<SuccessToastComponent>
  ) {}

  close(): void {
    this.snackBarRef.dismiss();
  }
}
