import { Component, Inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormControl, FormGroup, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { ComboComponent } from '@app/components/base/combo/combo.component';
import { FormFieldComponent } from '@app/components/base/form-field/form-field.component';
import { CustomDialogComponent } from '@app/components/base/dialog/custom-dialog/custom-dialog.component';
import { Knowledge as Knowledge } from '@app/models/knowledge.model';
import { ButtonComponent } from '@app/components/base/button/button.component';
@Component({
  selector: 'app-knowledges-dialog',
  templateUrl: './data-dialog.component.html',
  styleUrls: ['./data-dialog.component.scss'],
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatDialogModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
    FormFieldComponent,
    ComboComponent,
    CustomDialogComponent,
    ButtonComponent,
    ReactiveFormsModule
  ]
})
export class DataDialogComponent implements OnInit {
  chapterForm: FormGroup
  isInValid = true;
  isEditMode = false;
  editedChapter: Knowledge;
  minlength = 3;
  pdf_file: File | null = null;


  constructor(
    private fb: FormBuilder,
    public dialogRef: MatDialogRef<DataDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: {
      chapter: Knowledge;
      action: 'create' | 'update' | 'view';
    }
  ) {
    this.editedChapter = { ...data.chapter };
    this.isEditMode = data.action !== 'create';
  }

  chapterNameCtrl: FormControl
  chapterContentCtrl: FormControl
  pdfFileCtrl: FormControl
  ngOnInit(): void {
    this.chapterNameCtrl = new FormControl('', [Validators.required, Validators.minLength(3)]);
    this.chapterContentCtrl = new FormControl('', [Validators.required, Validators.minLength(3)])
    this.pdfFileCtrl = new FormControl();
    this.initFormControls()

    this.chapterForm = this.fb.group({
      user_name: this.chapterNameCtrl,
      email: this.chapterContentCtrl,
      pdf: [null]
    });


  }

  private initFormControls(): void {
    console.log("this.editedChapter")
    console.log(this.editedChapter)
    console.log(this.isEditMode)
    if (this.isEditMode && this.editedChapter) {
      console.log("this.isEditMode")
      this.chapterNameCtrl.setValue(this.editedChapter.name)
      this.chapterContentCtrl.setValue(this.editedChapter.content)
      this.pdfFileCtrl.setValue(this.editedChapter.pdf_file || null);
    }

  }

  ;
  toggleEditMode() {
    this.isEditMode = !this.isEditMode;
    if (this.isEditMode) {
      this.editedChapter = { ...this.data.chapter };
      this.chapterNameCtrl.setValue(this.editedChapter.name)
      this.chapterContentCtrl.setValue(this.editedChapter.content)
      this.pdfFileCtrl.setValue(this.editedChapter.pdf_file || null);
    }
  }

  save() {
    this.editedChapter.name = this.chapterNameCtrl.value;
    this.editedChapter.content = this.chapterContentCtrl.value;
    this.editedChapter.pdf_file = this.pdfFileCtrl.value || null;
    const formData = new FormData();
    formData.append('data', JSON.stringify(this.editedChapter) as any);
    if (this.pdfFileCtrl && this.pdfFileCtrl.value) {
      formData.append('pdf', this.pdf_file);


    }
    this.dialogRef.close(formData);
  }



  onSubmitFromChild() {
    console.log('onSubmitFromChild called');
    if (this.chapterForm.valid) {
      this.editedChapter.name = this.chapterNameCtrl.value;
      this.editedChapter.content = this.chapterContentCtrl.value;
      this.editedChapter.pdf_file = this.pdfFileCtrl.value || null;
      const formData = new FormData();
      formData.append('data', JSON.stringify(this.editedChapter) as any);
      if (this.pdfFileCtrl && this.pdfFileCtrl.value) {
        formData.append('pdf', this.pdf_file);
      }

      this.dialogRef.close(formData)
    }

  }


  onFileSelected(event: any) {
    console.log(' onFileSelected:', event);
    const files = event.target.files.FileList || event.target.files;
    console.log('Files array:', files);
    const file = files[0]
    console.log('Selected files:', file);
    if (file) {
      this.pdfFileCtrl.setValue(file.name);
      if (this.isEditMode) {
        this.editedChapter.pdf_file = file.name;
      }

      this.pdf_file = file;
      console.log('File selected:', file);
    }
  }
}



