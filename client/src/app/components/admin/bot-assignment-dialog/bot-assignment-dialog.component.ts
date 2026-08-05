import { Component, Inject, OnInit } from "@angular/core";
import { CommonModule } from '@angular/common';
import { FormBuilder, FormControl, FormGroup, Validators } from "@angular/forms";
import {
  MatDialogModule,
  MatDialogRef,
  MAT_DIALOG_DATA,
} from "@angular/material/dialog";

import { MatProgressSpinnerModule } from "@angular/material/progress-spinner";
import { User } from "../../../models/user.model";
import { Bot } from "../../../models/bot.model";
import { BotService } from "../../../services/bot.service";
import { ReactiveFormsModule } from '@angular/forms'
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { CustomDialogComponent } from "@app/components/base/dialog/custom-dialog/custom-dialog.component";
import { ComboComponent } from "@app/components/base/combo/combo.component";
import { MultiSelectComponent } from "@app/components/base/multi-select/multi-select.component";

@Component({
  selector: "app-bot-assignment-dialog",
  standalone: true,
  imports: [
    CommonModule,
    MatProgressSpinnerModule,
    MatDialogModule,
    FormsModule,
    ReactiveFormsModule,
    MatButtonModule,
    ComboComponent,
    MultiSelectComponent,
    CustomDialogComponent,
  ],
  templateUrl: "./bot-assignment-dialog.component.html",
  styleUrl: "./bot-assignment-dialog.component.scss"
})
export class BotAssignmentDialogComponent implements OnInit {

  assignedBotsCtrl: FormControl;
  assignmentForm: FormGroup;
  availableBots: Bot[] = [];
  botOptions: any[] = [];

  constructor(
    private fb: FormBuilder,
    private botService: BotService,
    public dialogRef: MatDialogRef<BotAssignmentDialogComponent>,
    @Inject(MAT_DIALOG_DATA)
    public data: {
      jwt
      user: User;
    }
  ) {}




  ngOnInit(): void {
    const assignedBotIds: number[] = [];
    this.data.user.assigned_bots.forEach(assignedBot => {assignedBotIds.push(assignedBot.bot_id)})

    this.assignedBotsCtrl = new FormControl(assignedBotIds || []);
    
    this.assignmentForm = this.fb.group({
      assigned_bot_ids: this.assignedBotsCtrl
    });

    this.loadAvailableBots();
  }

  private loadAvailableBots(): void {
    this.botService.getOwnedBots().subscribe({
      next: (bots) => {
        this.availableBots = bots;
        this.botOptions = bots.map(bot => ({ 
          value: bot.id, 
          label: `Bot #${bot.id}` 
        }));
      },
      error: (error) => {
        console.error('Error loading bots:', error);
      }
    });
  }

  onSubmitFromChild() {
    if (this.assignmentForm.valid) {
      const assignedBotIds = this.assignedBotsCtrl.value || [];
      this.dialogRef.close({ assigned_bot_ids: assignedBotIds });
    }
  }

  onCancel() {
    this.dialogRef.close();
  }
}