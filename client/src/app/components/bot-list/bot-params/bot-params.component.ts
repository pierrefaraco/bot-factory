// bot-dialog.component.ts (version responsive avec nouvelles importations)
import { Component, Inject, CUSTOM_ELEMENTS_SCHEMA, OnInit, HostListener, AfterViewInit, OnChanges, SimpleChanges, Input, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormControl, Validators, FormGroup, FormBuilder } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatSelectModule } from '@angular/material/select';
import { MatTabsModule } from '@angular/material/tabs';

import { Bot } from '../../../models/bot.model';
import { BotDrawComponent } from '../bot-draw/bot-draw.component';
import { SvgAvatarComponent } from '../bot-draw/svg-avatar/svg-avatar.component';
import { Avatar } from '@app/models/avatar.model';
import { BotParameters } from '@app/models/bot-parameters.model';
import { BotService } from '@app/services/bot.service';
import { BotParametersService } from '@app/services/bot-parameters.service';
import { KnowledgesComponent } from '@app/components/knowledges/knowledges.component';
import { ComboOptions, CustomOption, transformToCustomOptions } from '@app/models/combo-options.model';

import { FormFieldComponent } from '@app/components/base/form-field/form-field.component'
import { ComboComponent } from '@app/components/base/combo/combo.component'
import { CustomDialogComponent } from '@app/components/base/dialog/custom-dialog/custom-dialog.component';
import { MatDialog, MatDialogRef } from '@angular/material/dialog';
import { CommunicationService } from '@app/services/communication.service';
import { debounceTime, distinctUntilChanged, Subscription } from 'rxjs';
import { ButtonComponent } from '@app/components/base/button/button.component';

@Component({
  selector: 'app-bot-params',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule, // Ajout de ReactiveFormsModule

    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    BotDrawComponent,
    SvgAvatarComponent,
    MatSelectModule,
    MatAutocompleteModule,
    MatTabsModule,
    KnowledgesComponent,
    MatIconModule,
    FormFieldComponent,
    ComboComponent,
    CustomDialogComponent,
    ButtonComponent
  ],
  templateUrl: './bot-params.component.html',
  styleUrl: './bot-params.component.scss',
  schemas: [CUSTOM_ELEMENTS_SCHEMA]
})
export class BotParamsComponent implements OnInit, OnDestroy, OnChanges {
  @Input() bot: Bot
  @Input() isEditing = false
  @Input() screenWidth = window.innerWidth;

  selectedTabIndex = 0;
  private subscriptionCreateBot: Subscription;
  private subscriptionSelectBot: Subscription;
  botForm: FormGroup
  namectrl = new FormControl('', Validators.required)
  botinfewwordsctrl = new FormControl('', Validators.required)

  // Contrôles pour les champs autocomplete
  botTypeCtrl = new FormControl('', Validators.required);
  interlocutorTypeCtrl = new FormControl('', Validators.required);
  interlocutorIdentityCtrl = new FormControl('', Validators.required);
  behaviourWhenIgnoreCtrl = new FormControl('', Validators.required);
  answerStyleCtrl = new FormControl('', Validators.required);
  behaviourWithLanguageCtrl = new FormControl('', Validators.required);
  answerLengthCtrl = new FormControl('', Validators.required);
  contextTypeCtrl = new FormControl('', Validators.required);
  usedSourcesCtrl = new FormControl('', Validators.required);
  goalCtrl = new FormControl('', Validators.required);
  personalityTrait1Ctrl = new FormControl('', Validators.required);
  personalityTrait2Ctrl = new FormControl('', Validators.required);
  personalityTrait3Ctrl = new FormControl('', Validators.required);
  localisationCtrl = new FormControl('', Validators.required);
  // Champs optionnels (pas de Validators.required : les bots existants n'ont pas encore ces valeurs)
  answerFormatCtrl = new FormControl('');
  voiceOutputCtrl = new FormControl(false);
  personaDescriptionCtrl = new FormControl('');
  isInValid = true;
 
  success: boolean = false;
  error: string = "";

  loadOptions = false
  subcategories = []
  width: number = 0;
  options_combo: ComboOptions | undefined;
  personalityTraits: CustomOption[] = []

  constructor(
    private fb: FormBuilder,
    private botService: BotService,
    private botParametersService: BotParametersService,
    private dialog: MatDialog,
    private communicationService: CommunicationService
  ) {




  }

  ngOnInit(): void {
    // Initialiser avec le bot si fourni via Input
    if (this.bot && this.isEditing) {
      this.editBot();
    }

    this.subscriptionCreateBot = this.communicationService.triggerCreateBot$.subscribe(() => {
      this.createBot()
    });

    this.subscriptionSelectBot = this.communicationService.triggerOnSelectBot$.subscribe((bot) => {
      this.bot = bot
      this.editBot()
    });

    // Signaler que le composant est initialisé
    this.communicationService.onComponentReady('BotParamsComponent');
  }

  ngOnChanges(changes: SimpleChanges): void {
    // Détecter les changements du bot passé via Input
    if (changes['bot'] && changes['bot'].currentValue && this.isEditing) {
      this.bot = changes['bot'].currentValue;
      this.editBot();
    }
  }


  ngOnDestroy(): void {
    this.subscriptionCreateBot.unsubscribe();
    this.subscriptionSelectBot.unsubscribe();
  }



  editBot(): void {
    this.botService.get_bot_parameters_description().subscribe(
      (data) => {
        this.options_combo = data;
        this.personalityTraits = transformToCustomOptions(this.options_combo)
  
         console.log('this.bot.bot_parameters loaded:')
         console.log(this.bot.bot_parameters)
         this.initFormControls()
            // this.bot.bot_parameters.bot_type = data
        
      });


  }
  onEditBotClick() {

    this.onSubmitFromChild(true)
  }

  createBot(): void {
    console.log('BotCreateComponent initialized')
    // Ajuster le dialogue en fonction de la taille d'écran
    this.botService.get_bot_parameters_description().subscribe(
      (data) => {

        this.options_combo = data;

        this.personalityTraits = transformToCustomOptions(this.options_combo)

        console.log('this.isEditing' + this.isEditing)

        if (this.options_combo)
          this.bot = {
            id: -1,
          }
        this.bot.bot_parameters = {
          bot_type: "A Butler",
          bot_name: "Alfred",
          answer_length: this.options_combo.answer_length[0].label,
          answer_style: this.options_combo.answer_style[0].label,
          behaviour_when_ignore: this.options_combo.behaviour_when_ignore[0].label,
          behaviour_with_language: this.options_combo.behaviour_with_language[0].label,
          context_type: this.options_combo.context_type[2].label,
          goal: this.options_combo.goal[0].label,
          interlocutor_type: "A guest",
          interlocutor_identity: this.options_combo.interlocutor_identity[0].label,
          main_personality_trait_1: this.options_combo.quality.intellectual[5],
          main_personality_trait_2: this.options_combo.quality.moral[1],
          main_personality_trait_3: this.options_combo.quality.professional[4],
          used_sources: this.options_combo.used_sources[0].label,
          localisation: 'Paris, France', // Valeur par défaut si non spécifiée
          answer_format: '',
          voice_output: false,
          persona_description: ''
        };
        this.initFormControls()
        this.onSubmitFromChild(false)
      })
  }




  private initFormControls(): void {
    if (!this.options_combo) return;
    console.log('initFormControls 0')
    // Initialiser les valeurs si on édite un bot existant
    if (this.bot.bot_parameters) {
      console.log('initFormControls 1',this.bot.bot_parameters)
      this.namectrl.setValue(this.bot.bot_parameters.bot_name)
      this.botTypeCtrl.setValue(this.bot.bot_parameters.bot_type || '');
      this.interlocutorTypeCtrl.setValue(this.bot.bot_parameters.interlocutor_type || '');
      this.interlocutorIdentityCtrl.setValue(this.bot.bot_parameters.interlocutor_identity || '');
      this.behaviourWhenIgnoreCtrl.setValue(this.bot.bot_parameters.behaviour_when_ignore || '');
      this.behaviourWithLanguageCtrl.setValue(this.bot.bot_parameters.behaviour_with_language || '');
      this.localisationCtrl.setValue(this.bot.bot_parameters.localisation); // Valeur par défaut si non spécifiée
      this.answerStyleCtrl.setValue(this.bot.bot_parameters.answer_style || '');
      this.answerLengthCtrl.setValue(this.bot.bot_parameters.answer_length || '');
      this.contextTypeCtrl.setValue(this.bot.bot_parameters.context_type || '');
      this.usedSourcesCtrl.setValue(this.bot.bot_parameters.used_sources || '');
      this.goalCtrl.setValue(this.bot.bot_parameters.goal || '');
      this.personalityTrait1Ctrl.setValue(this.bot.bot_parameters.main_personality_trait_1 || '');
      this.personalityTrait2Ctrl.setValue(this.bot.bot_parameters.main_personality_trait_2 || '');
      this.personalityTrait3Ctrl.setValue(this.bot.bot_parameters.main_personality_trait_3 || '');
      this.answerFormatCtrl.setValue(this.bot.bot_parameters.answer_format || '');
      this.voiceOutputCtrl.setValue(this.bot.bot_parameters.voice_output || false);
      this.personaDescriptionCtrl.setValue(this.bot.bot_parameters.persona_description || '');
    }

    this.botForm = this.fb.group({

      bot_name: this.namectrl,
      bot_type: this.botTypeCtrl,
      interlocutor_type: this.interlocutorTypeCtrl,
      interlocutor_identity: this.interlocutorIdentityCtrl,
      behaviour_when_ignore: this.behaviourWhenIgnoreCtrl,
      behaviour_with_language: this.behaviourWithLanguageCtrl,
      localisation: this.localisationCtrl,
      answer_style: this.answerStyleCtrl,
      answer_length: this.answerLengthCtrl,
      context_type: this.contextTypeCtrl,
      used_sources: this.usedSourcesCtrl,
      goal: this.goalCtrl,
      main_personality_trait_1: this.personalityTrait1Ctrl,
      main_personality_trait_2: this.personalityTrait2Ctrl,
      main_personality_trait_3: this.personalityTrait3Ctrl,
      answer_format: this.answerFormatCtrl,
      voice_output: this.voiceOutputCtrl,
      persona_description: this.personaDescriptionCtrl,
    });
    this.markAllControlsAsTouched()

  }

  onPatchBot(param){
    const value = this.botForm.value[param]
    console.log(this.botForm)
    console.log('key,value', param ,value)
    
    console.log('onPatchBotName - valeur du contrôle:', value);
    // this.bot.bot_name = this.namectrl.value;
    this.communicationService.submitPatchBot({ bot_id: this.bot.id, data:{ [param]: value}});
  }

  onSubmitFromChild(edit: boolean) {
    console.log('onSubmitFromChild')
    if (this.botForm.valid) {
      this.bot = {
        id: this.bot.id,
      }


      this.bot.bot_parameters = {
        bot_id: this.bot.bot_parameters.id,
        bot_name: this.bot.bot_parameters.bot_name,
        bot_type: this.botTypeCtrl.value,
        answer_length: this.answerLengthCtrl.value,
        answer_style: this.answerStyleCtrl.value,
        behaviour_when_ignore: this.behaviourWhenIgnoreCtrl.value,
        behaviour_with_language: this.behaviourWithLanguageCtrl.value,
        context_type: this.contextTypeCtrl.value,
        goal: this.goalCtrl.value,
        interlocutor_type: this.interlocutorTypeCtrl.value,
        interlocutor_identity: this.interlocutorIdentityCtrl.value,
        main_personality_trait_1: this.personalityTrait1Ctrl.value,
        main_personality_trait_2: this.personalityTrait2Ctrl.value,
        main_personality_trait_3: this.personalityTrait3Ctrl.value,
        used_sources: this.usedSourcesCtrl.value,
        localisation: this.localisationCtrl.value,
        answer_format: this.answerFormatCtrl.value,
        voice_output: this.voiceOutputCtrl.value,
        persona_description: this.personaDescriptionCtrl.value
      };

   
      } else {
        // Afficher un message d'erreur ou mettre en évidence les champs invalides
        console.error('Formulaire invalide. Veuillez corriger les erreurs.');
        console.log(this.botForm)
        // Marquer tous les contrôles comme touchés pour afficher les erreurs
        this.markAllControlsAsTouched();
      }
    }


  // Marquer tous les contrôles comme touchés pour afficher les erreurs
  private markAllControlsAsTouched(): void {
    this.namectrl.markAsTouched();
    this.botTypeCtrl.markAsTouched();
    this.interlocutorTypeCtrl.markAsTouched();
    this.interlocutorIdentityCtrl.markAsTouched();
    this.behaviourWhenIgnoreCtrl.markAsTouched();
    this.behaviourWithLanguageCtrl.markAsTouched();
    this.localisationCtrl.markAsTouched();
    this.answerStyleCtrl.markAsTouched();
    this.answerLengthCtrl.markAsTouched();
    this.contextTypeCtrl.markAsTouched();
    this.usedSourcesCtrl.markAsTouched();
    this.goalCtrl.markAsTouched();
    this.personalityTrait1Ctrl.markAsTouched();
    this.personalityTrait2Ctrl.markAsTouched();
    this.personalityTrait3Ctrl.markAsTouched();
  }

  displayFn(option: string): string {
    return option ? option : '';
  }

  test_if_error(formCtrl: FormControl): boolean {
    if (formCtrl.invalid) {
      return true
    }
    return false
  }
}


