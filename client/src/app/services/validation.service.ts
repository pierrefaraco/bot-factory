import { Injectable } from '@angular/core';
import { FormControl, FormGroup, Validators } from '@angular/forms';

@Injectable({
  providedIn: 'root'
})
export class ValidationService {
  
  createFormControls(bot, bot_parameters) {
    return {
      namectrl: new FormControl(bot.bot_name, [Validators.required]),
      welcomemsgctrl: new FormControl(bot.hello_msg, [Validators.required]),
      botTypeCtrl: new FormControl(bot_parameters.bot_type, [Validators.required]),
      interlocutorTypeCtrl: new FormControl(bot_parameters.interlocutor_type, [Validators.required]),
      behaviourCtrl: new FormControl(bot_parameters.behaviour, [Validators.required]),
      behaviourWhenFinishSpeakCtrl: new FormControl(bot_parameters.behaviour_when_finish_speak, [Validators.required]),
      behaviourWhenIgnoreCtrl: new FormControl(bot_parameters.behaviour_when_ignore, [Validators.required]),
      // Ajouter les autres contrôles...
    };
  }

  createFormGroup(controls) {
    return new FormGroup(controls);
  }

  hasError(control: FormControl): boolean {
    return control.invalid && (control.dirty || control.touched);
  }
}