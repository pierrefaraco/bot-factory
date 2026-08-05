import { Component, OnInit, OnChanges, OnDestroy, SimpleChanges, Inject, ViewChild, Input } from '@angular/core';
import { MatDialog, MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatInputModule } from '@angular/material/input';
import { FormsModule } from '@angular/forms';
import { ColorComponent } from './color/color.component';
import { SvgAvatarComponent } from './svg-avatar/svg-avatar.component';
import { AVATAR_COLORS } from '../../../constants/color.constants'
import { Avatar } from '../../../models/avatar.model'
import { CustomDialogComponent } from '@app/components/base/dialog/custom-dialog/custom-dialog.component';
import { CommunicationService } from '@app/services/communication.service';
import { Subscription } from 'rxjs';
import { Bot } from '@app/models/bot.model';
import { AvatarService } from '@app/services/avatar.service';
interface ColorHistory {
  primary: string;
  timestamp: Date;
}

@Component({
  standalone: true,
  selector: 'app-bot-draw',
  templateUrl: './bot-draw.component.html',
  styleUrl: './bot-draw.component.scss',
  imports: [
    MatInputModule,
    FormsModule,
    MatDialogModule,
    ColorComponent,
    SvgAvatarComponent,
    CustomDialogComponent
  ],
})
export class BotDrawComponent implements OnInit, OnChanges, OnDestroy {
  @Input() bot: Bot;
  @Input() isEditing: boolean = false;
  private subscriptionSelectBot: Subscription;
  avatar: Avatar;
  colors = AVATAR_COLORS;
  botHat: string = "hat";
  botMouth: string = "mouth";
  botBody: string = "body";
  botEyes: string = "eyes";
  bodyColor: string = AVATAR_COLORS[1];
  eyesColor: string = AVATAR_COLORS[0];
  mouthColor: string = AVATAR_COLORS[3];
  hatColor: string = AVATAR_COLORS[4];

  imgBot: string = "assets/img/bot/bot.png";
  imgHat: string = "assets/img/bot/hat.png";
  imgEyes: string = "assets/img/bot/eyes.png";
  imgMouth: string = "assets/img/bot/mouth.png";

  @ViewChild('draw_avatar') svgAvatarComponent!: SvgAvatarComponent;

  get svgStyle(): string {
    return `
      --body-color: ${this.bodyColor};
      --eyes-color: ${this.eyesColor};
      --hat-color: ${this.hatColor};
      --mouth-color: ${this.mouthColor};
    `;
  }

  constructor(
    private communicationService: CommunicationService,
    private avatarService: AvatarService
  ) { }

  ngOnInit(): void {
    // Initialiser l'avatar si le bot est déjà fourni via Input
    if (this.bot?.avatar) {
      this.avatar = this.bot.avatar;
    }

    this.subscriptionSelectBot = this.communicationService.triggerOnSelectBot$.subscribe((bot) => {
      if (bot?.avatar) {
        this.avatar = bot.avatar;
      }
    });
    // Signaler que le composant est initialisé
    this.communicationService.onComponentReady('BotDrawComponent');
  }

  ngOnChanges(changes: SimpleChanges): void {
    // Détecter les changements du bot passé via Input
    if (changes['bot'] && changes['bot'].currentValue?.avatar) {
      this.avatar = changes['bot'].currentValue.avatar;
    }
  }

  ngOnDestroy(): void {
    if (this.subscriptionSelectBot) {
      this.subscriptionSelectBot.unsubscribe();
    }
  }

  updateAvatar(): void {
    this.avatarService.updateAvatar(this.avatar).subscribe((_avatar) => {
      console.log('Avatarupdated with succès:', _avatar);
    });
  }

  patchAvatar(data: Partial<Avatar>): void {
    data.id = this.avatar.id; // Assurer que l'ID est inclus
    console.log('BotDrawComponent: patchAvatar triggered', data);
    this.avatarService.patchAvatar(data).subscribe((_avatar) => {
      // Mettre à jour le cache local immédiatement
      this.avatar = { ...this.avatar, ...data };
      // Notifier via le CommunicationService pour synchroniser avec les autres composants
      this.communicationService.onPatchAvatar(data);
    }
    );
  }

  nextBot(): void {
    this.patchAvatar({ body: this.avatar.body + 1 });
  }

  previousBot(): void {
    this.patchAvatar({ body: this.avatar.body - 1 });
  }

  nextHat(): void {
    this.patchAvatar({ hat: this.avatar.hat + 1 });
  }

  previousHat(): void {
    this.patchAvatar({ hat: this.avatar.hat - 1 });
  }

  nextMouth(): void {
    this.patchAvatar({ mouth: this.avatar.mouth + 1 });
  }

  previousMouth(): void {
    this.patchAvatar({ mouth: this.avatar.mouth - 1 });
  }

  nextEyes(): void {
    this.patchAvatar({ eyes: this.avatar.eyes + 1 });
  }

  previousEyes(): void {
    this.patchAvatar({ eyes: this.avatar.eyes - 1 });
  }

  setBodyColor(indice: number): void {
    this.patchAvatar({ body_color: indice });
  }

  setHatColor(indice: number): void {
    this.patchAvatar({ hat_color: indice });
  }

  setEyesColor(indice: number): void {
    this.patchAvatar({ eyes_color: indice });
  }

  setMouthColor(indice: number): void {
    this.patchAvatar({ mouth_color: indice });
  }

  Color($event: any): void {
    this.hatColor = $event.target.value;
  }

  onSubmit(): void {
    // TODO: Implement submit logic
  }

  onCancel(): void {
    // TODO: Implement cancel logic
  }
}