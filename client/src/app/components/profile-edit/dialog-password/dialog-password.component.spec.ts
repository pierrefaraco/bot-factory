import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { MatDialogRef } from '@angular/material/dialog';
import { provideNoopAnimations } from '@angular/platform-browser/animations';

import { DialogPasswordComponent } from './dialog-password.component';

describe('DialogPasswordComponent', () => {
  let component: DialogPasswordComponent;
  let fixture: ComponentFixture<DialogPasswordComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DialogPasswordComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideNoopAnimations(),
        { provide: MatDialogRef, useValue: { close: () => {} } }
      ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(DialogPasswordComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
