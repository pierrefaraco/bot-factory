import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, Inject } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { CustomDialogComponent } from '../dialog/custom-dialog/custom-dialog.component';

export interface ConfirmDialogData {
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  /** Frames the confirm button as destructive (delete/deactivate). */
  danger?: boolean;
}

/**
 * Generic confirmation modal, built on <app-custom-dialog> (same card/
 * button styling as every other dialog in the app). Usage:
 *
 *   const ref = this.dialog.open(ConfirmDialogComponent, {
 *     data: { title: 'Delete user', message: 'This cannot be undone.', danger: true }
 *   });
 *   ref.afterClosed().subscribe(confirmed => { if (confirmed) { ... } });
 */
@Component({
  selector: 'app-confirm-dialog',
  standalone: true,
  imports: [CommonModule, CustomDialogComponent],
  templateUrl: './confirm-dialog.component.html',
  styleUrl: './confirm-dialog.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ConfirmDialogComponent {
  constructor(
    public dialogRef: MatDialogRef<ConfirmDialogComponent, boolean>,
    @Inject(MAT_DIALOG_DATA) public data: ConfirmDialogData
  ) {}

  onConfirm(): void {
    this.dialogRef.close(true);
  }
}
