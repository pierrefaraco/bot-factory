import { Injectable } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { MatDialog } from '@angular/material/dialog';
import { ErrorDialogComponent, ErrorDialogData } from '../components/base/error-dialog/error-dialog.component';

@Injectable({
  providedIn: 'root'
})
export class ErrorNotificationService {

  constructor(private dialog: MatDialog) { }

  showError(error: HttpErrorResponse): void {
    // Un seul popup d'erreur à la fois : une rafale d'appels en échec (ex.
    // plusieurs requêtes en parallèle qui échouent toutes) ne doit pas
    // empiler les dialogs les uns sur les autres.
    if (this.dialog.openDialogs.some(ref => ref.componentInstance instanceof ErrorDialogComponent)) {
      return;
    }

    const data: ErrorDialogData = {
      title: 'Something went wrong',
      message: this.extractMessage(error),
      status: error.status || undefined
    };

    this.dialog.open(ErrorDialogComponent, {
      data,
      autoFocus: false,
    });
  }

  private extractMessage(error: HttpErrorResponse): string {
    // Format standard de l'API : {"error": "..."}.
    const body = error.error;
    if (body && typeof body === 'object') {
      if (typeof body.error === 'string' && body.error) {
        return body.error;
      }
    }

    if (typeof body === 'string' && body) {
      return body;
    }

    if (error.status === 0) {
      return 'Unable to reach the server. Please check your connection and try again.';
    }

    return error.message || 'An unexpected error occurred. Please try again.';
  }
}
