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
import { SvgAvatarComponent } from "@app/components/bot-list/bot-draw/svg-avatar/svg-avatar.component";

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
    CustomDialogComponent,
    SvgAvatarComponent,
  ],
  templateUrl: "./bot-assignment-dialog.component.html",
  styleUrl: "./bot-assignment-dialog.component.scss"
})
export class BotAssignmentDialogComponent implements OnInit {

  assignedBotsCtrl: FormControl;
  assignmentForm: FormGroup;
  availableBots: Bot[] = [];
  filteredBots: Bot[] = [];

  loading = true;
  searchTerm = '';
  focusedIndex = 0;

  /** Threshold above which the search box is shown. */
  readonly searchThreshold = 6;

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
    this.loading = true;
    this.botService.getOwnedBots().subscribe({
      next: (bots) => {
        this.availableBots = bots;
        this.filteredBots = bots;
        this.loading = false;
      },
      error: (error) => {
        console.error('Error loading bots:', error);
        this.loading = false;
      }
    });
  }

  getBotName(bot: Bot): string {
    return bot.bot_parameters?.bot_name || `Bot ${bot.id}`;
  }

  isSelected(bot: Bot): boolean {
    return (this.assignedBotsCtrl.value || []).includes(bot.id);
  }

  // No availability flag exists on Bot yet; kept as a hook for the disabled
  // state so the UI is ready as soon as the backend exposes one.
  isBotUnavailable(bot: Bot): boolean {
    return false;
  }

  toggleBot(bot: Bot): void {
    if (this.isBotUnavailable(bot)) {
      return;
    }
    const current: number[] = this.assignedBotsCtrl.value || [];
    const next = this.isSelected(bot)
      ? current.filter(id => id !== bot.id)
      : [...current, bot.id];
    this.assignedBotsCtrl.setValue(next);
    this.assignedBotsCtrl.markAsTouched();
  }

  onSearchChange(term: string): void {
    this.searchTerm = term;
    const normalized = term.trim().toLowerCase();
    this.filteredBots = normalized
      ? this.availableBots.filter(bot => this.getBotName(bot).toLowerCase().includes(normalized))
      : this.availableBots;
    this.focusedIndex = 0;
  }

  onRowKeydown(event: KeyboardEvent, index: number, bot: Bot): void {
    switch (event.key) {
      case 'ArrowDown':
        event.preventDefault();
        this.focusRow(Math.min(index + 1, this.filteredBots.length - 1));
        break;
      case 'ArrowUp':
        event.preventDefault();
        this.focusRow(Math.max(index - 1, 0));
        break;
      case 'Enter':
      case ' ':
        event.preventDefault();
        this.toggleBot(bot);
        break;
    }
  }

  private focusRow(index: number): void {
    this.focusedIndex = index;
    const row = document.getElementById(`bot-option-${this.filteredBots[index]?.id}`);
    row?.focus();
  }

  trackByBotId(_index: number, bot: Bot): number {
    return bot.id;
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
