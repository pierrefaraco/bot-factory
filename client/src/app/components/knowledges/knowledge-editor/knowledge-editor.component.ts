import { Component, OnDestroy, OnInit } from '@angular/core';
import { Subscription } from 'rxjs';
import { Knowledge } from '@app/models/knowledge.model';
import { CommunicationService } from '@app/services/communication.service';
import { FormBuilder, FormControl, FormGroup, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { FormFieldComponent } from '@app/components/base/form-field/form-field.component';
import { ComboComponent } from '@app/components/base/combo/combo.component';
import { CustomDialogComponent } from '@app/components/base/dialog/custom-dialog/custom-dialog.component';
import { ButtonComponent } from '@app/components/base/button/button.component';
import { KnowledgeService } from '@app/services/knowledge.service';
import { Bot } from '@app/models/bot.model';

@Component({
  selector: 'app-knowledge-editor',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
    FormFieldComponent,
    ComboComponent,
    CustomDialogComponent,
    ButtonComponent,
    ReactiveFormsModule
  ],
  templateUrl: './knowledge-editor.component.html',
  styleUrl: './knowledge-editor.component.css'
})
export class KnowledgeEditorComponent implements OnInit, OnDestroy {

  private subscriptionSelectKnowledge: Subscription;
  private subscriptionSelectBot: Subscription;
  selectedKnowledge: Knowledge;

  knowledgeForm: FormGroup
  knowledgeNameCtrl = new FormControl;
  knowledgeContentCtrl = new FormControl;
  pdfFileCtrl: FormControl
  pdf_file: File | null = null;
  selectedBot: Bot
  constructor(private fb: FormBuilder, private communicationService: CommunicationService, private knowledgeService: KnowledgeService) { }


  ngOnInit(): void {
    // Écouter les changements de bot sélectionné

    this.subscriptionSelectKnowledge = this.communicationService.triggerOnSelectedKnowledge$.subscribe((knowledge) => {
      console.log('KnowledgeEditorComponent - receiveseknowledge', knowledge)
      console.log("KnowledgeEditorComponent DataComponent selected bot: ",  this.selectedBot );
      this.selectedKnowledge = knowledge;
      if (this.selectedBot )
        this.selectedBot = this.communicationService.getSelectedBot()
      this.initFormControls();
    });
    this.subscriptionSelectBot = this.communicationService.triggerOnSelectBot$.subscribe((bot) => {
      console.log("KnowledgeEditorComponent DataComponent selected bot: ", bot);
      if (this.selectedBot && bot && this.selectedBot.id !== bot.id) {
        // Switching to a different bot invalidates the currently displayed
        // knowledge (it belongs to the previous bot's tree) -- clear it so
        // the editor falls back to the "select an item" placeholder instead
        // of showing stale content until the user picks a new node.
        this.selectedKnowledge = null;
      }
      this.selectedBot = bot
    })
    this.knowledgeNameCtrl = new FormControl('', Validators.required);
    this.knowledgeContentCtrl = new FormControl('', Validators.required);
    this.pdfFileCtrl = new FormControl();
    this.initFormControls()
    this.knowledgeForm = this.fb.group({
      knowledge_title: this.knowledgeNameCtrl,
      knowledge_content: this.knowledgeContentCtrl,
      pdf: [null]
    });


    // Signaler que le composant est initialisé
    this.communicationService.onComponentReady('KnowledgeEditorComponent');

  }
  
  ngOnDestroy(): void {
    if (this.subscriptionSelectKnowledge) {
      this.subscriptionSelectKnowledge.unsubscribe();
    }
    if(this.subscriptionSelectKnowledge)
       this.subscriptionSelectKnowledge.unsubscribe()
  }

  private initFormControls(): void {
    console.log("this.editedChapter")

    if (this.selectedKnowledge) {
      console.log("this.isEditMode")
      this.knowledgeNameCtrl.setValue(this.selectedKnowledge.name)
      this.knowledgeContentCtrl.setValue(this.selectedKnowledge.content)
      this.pdfFileCtrl.setValue(this.selectedKnowledge.pdf_file || null);
    }

  }

  private onSubmit() {

    console.log('selectedKnowledge', this.selectedKnowledge)
    if (this.selectedKnowledge) {
      this.selectedKnowledge.name = this.knowledgeNameCtrl.value;
      this.selectedKnowledge.content = this.knowledgeContentCtrl.value;
      this.selectedKnowledge.pdf_file = this.pdfFileCtrl.value || null;

      const formData = new FormData();
      formData.append('data', JSON.stringify(this.selectedKnowledge) as any);
      if (this.pdfFileCtrl && this.pdfFileCtrl.value) {
        formData.append('pdf', this.pdf_file);
      }
      this.knowledgeService.updateKnowledge(this.selectedBot.id, formData).subscribe({
        next: () => {
           this.communicationService.onUpdateKnowledge(this.selectedKnowledge)
        },
        error: () => console.log('Error updating chapter', 'error')
      });
    }
  }

  onPatchKnowledge(param) {
    console.log('knowledgeForm', this.knowledgeForm)
    const value = this.knowledgeForm.value[param]
    console.log('key,value', param, value)

    console.log('onPatchKnowledge - valeur du contrôle:', value);
    // this.bot.bot_name = this.namectrl.value;
    this.onSubmit();
  }

  onFileSelected(event: any) {
    console.log(' onFileSelected:', event);
    const files = event.target.files.FileList || event.target.files;
    console.log('Files array:', files);
    const file = files[0]
    console.log('Selected files:', file);
    if (file) {
      this.pdfFileCtrl.setValue(file.name);

      this.pdf_file = file;
      console.log('File selected:', file);
      this.onPatchKnowledge('pdf')
    }
  }
}
