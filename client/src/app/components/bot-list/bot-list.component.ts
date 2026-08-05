import { Component, OnDestroy, OnInit, Optional, ViewChild, Input, AfterViewInit } from "@angular/core";
import { CommonModule } from "@angular/common";
import { FormsModule } from "@angular/forms";
import { MatDialog, MatDialogModule } from "@angular/material/dialog";
import { MatButtonModule } from "@angular/material/button";
import { MatIconModule } from "@angular/material/icon";
import { BotService } from "../../services/bot.service";
import { AuthService } from "../../services/auth.service";
import { Bot } from "../../models/bot.model";
import { AvatarService } from "@app/services/avatar.service";
import { Avatar } from "@app/models/avatar.model";
import { SvgAvatarComponent } from "./bot-draw/svg-avatar/svg-avatar.component";
import { BotParameters } from "@app/models/bot-parameters.model";
import { BotParametersService } from "@app/services/bot-parameters.service";
import { ButtonComponent } from "../base/button/button.component";
import { ArrayComponent } from "../base/array/array.component";
import { LineComponent } from "../base/array/line/line.component";
import { ColumnComponent } from "../base/array/column/column.component";
import { CustomDropDownMenuComponent } from "../base/custom-dropdown-menu/custom-dropdown-menu.component";
import { CommunicationService } from "@app/services/communication.service";
import { Subscription } from "rxjs";
import { MatListModule } from '@angular/material/list';
import { BotDrawComponent } from "./bot-draw/bot-draw.component";
import { UsersService } from "@app/services/users.service";
import { USER_ROLES } from "@app/constants/user-roles.constants";

@Component({
  selector: "app-bot-list",
  standalone: true,
  templateUrl: "./bot-list.component.html",
  styleUrls: ["./bot-list.component.scss"],
  inputs: ['layout'],
  imports: [
    CommonModule,
    FormsModule,
    MatDialogModule,
    MatButtonModule,
    MatIconModule,
    SvgAvatarComponent,
    ButtonComponent,
    ArrayComponent,
    LineComponent,
    ColumnComponent,
    CustomDropDownMenuComponent,
    MatListModule
  ],
})
export class BotListComponent implements OnInit, OnDestroy {
  @Input() layout: 'horizontal' | 'vertical' = 'horizontal';
  private subscriptionSubmitEditBot: Subscription;
  private subscriptionSubmitPatchBot: Subscription;
  private subscriptionAllComponentsReady: Subscription;
  private subscriptionSubmitPatchAvatar: Subscription;
  private subscriptionCreateBot: Subscription;
  botDropdownVisible = true
  actionItemList = [

    {
      label: "Draw bot",
      color: "var(--text-accent)",
      icon: "border_color",
      action: (bot) => { this.openDrawDialog(bot) }
    },
    {
      divider: true,
      color: "var(--text-primary)",
    }, {
      label: "Delete",
      color: "var(--text-danger)",
      icon: "delete",
      action: (bot) => { this.deleteBot(bot?.id!) }
    }]
  bots: Bot[] = [];
  selected_bot: Bot | null = null;
  currentPage = 1;
  pageSize = 4;
  totalPages = 1;
  screenWidth: number;
  isDropdownOpen = false;
  user_id: number = -1;
  constructor(
    private botService: BotService,
    private botParametersService: BotParametersService,
    private avatarService: AvatarService,
    private communicationService: CommunicationService,
    private dialog: MatDialog,
    private userService: UsersService,
    private authService: AuthService,
  ) {
    console.log("BotListComponent constructor");
    this.screenWidth = window.innerWidth;
    // Écouter l'événement workspaceReady pour charger les bots après l'initialisation du workspace





  }

  ngOnInit(): void {
    console.log("BotListComponent ngOnInit");

    // Écouter l'événement allComponentsReady pour charger les bots après l'initialisation de tous les composants
    this.subscriptionAllComponentsReady = this.communicationService.triggerAllComponentsReady$.subscribe(() => {
      console.log("BotListComponent: all components ready - loading bots");
      this.loadBots();
    });


    this.subscriptionCreateBot = this.communicationService.triggerCreateBot$.subscribe(() => {
      this.createBot_random()
    });

    this.subscriptionSubmitEditBot = this.communicationService.triggerSubmitEditBot$.subscribe((result) => {
      console.log("BotListComponent: edit bot triggered");
      this.editBot(result.bot, result.avatar, result.bot_parameters);
    });

    this.subscriptionSubmitPatchBot = this.communicationService.triggerSubmitPatchBot$.subscribe((result) => {
      console.log("BotListComponent: patchBot bot triggered!");
      this.patch_bot(result.bot_id, result.data);
    });

    this.subscriptionSubmitPatchAvatar = this.communicationService.triggerSubmitPatchAvatar$.subscribe((data) => {
      console.log("BotListComponent: patchAvatar avatar triggered!");
      if (this.selected_bot?.avatar) {
        this.patchAvatarCache(this.selected_bot.avatar.id, data);
      }
    });
    this.communicationService.onComponentReady('BotListComponent');
    this.user_id = this.authService.get_curent_user_id();
  }



  ngOnDestroy() {
    this.subscriptionSubmitEditBot.unsubscribe();
    this.subscriptionSubmitPatchBot.unsubscribe();
    this.subscriptionAllComponentsReady.unsubscribe();
    this.subscriptionSubmitPatchAvatar.unsubscribe();
    this.subscriptionCreateBot.unsubscribe();
  }

  get botsList() {
    return this.bots;
  }

  loadBots(): void {
    this.botService.getUserBots().subscribe((bots) => {
      console.log("bot loaded: " + bots.length)
      this.bots = bots;
      if (this.bots.length > 0) {
        this.userService.getSelectedBot().subscribe({
          next: (result) => {
            console.log("Select loaded bot ", result.selected_bot_id)
            if (!result.selected_bot_id && this.bots.length > 0)
              this.onSelectBot(this.bots[0].id, false);
            if (result.selected_bot_id)
              this.onSelectBot(result.selected_bot_id, false);
          },
          error: (error) => {
            console.error('Error loading selected bot id:', error);
          },
          complete: () => {
            console.info('Selected bot id loading completed', this.selected_bot);
          }
        });
      }
      else {
        console.info('Bots list is empty');
      }
    });
  }

  /**
   * Méthode publique pour rafraîchir la liste des bots
   * Peut être appelée par le composant parent via ViewChild
   */
  refresh(): void {
    console.log("BotListComponent: refresh triggered from parent");
    this.loadBots();
  }

  trunk(txt: string, limite = 200): string {
    return txt.length > limite ? txt.substring(0, limite) + '...' : txt;
  }

  getEmptyBot(): Bot {
    return {
      id: -1,
    };
  }





  getBasicAvatar(): Avatar {

    let new_avatar: Avatar = {
      id: -1,
      bot_id: -1,
      body: 0,
      hat: 0,
      eyes: 0,
      mouth: 0,
      body_color: 0,
      hat_color: 0,
      eyes_color: 0,
      mouth_color: 0
    };
    return new_avatar;
  }

  onCreateBotClick(): void {
    console.log('onCreateBotClick')
    this.communicationService.onCreateBot()
  }


  onSelectBot(selected_bot_id: number, must_patch_selected_bot = true): void {
    console.log("onSelectBot id: ", selected_bot_id)

    this.botService.getBotById(selected_bot_id, 'full').subscribe({
      next: (_bot) => {
        this.selected_bot = _bot;
        this.communicationService.onSelectBot(this.selected_bot)
        if (must_patch_selected_bot) {
          this.userService.patchSelectBotID(this.selected_bot.id).subscribe({
            next: (response) => {
              console.log("User updated successfully with selected_bot_id:", response);


            }
          });
        }
      }
    });

  }



  editBot(bot: Bot, avatar: Avatar, botParameters: BotParameters): void {
    this.updateBot(bot);
    this.updateAvatar(avatar);
    this.updateBotPArameters(botParameters);
  }

  createBot_random(): void {
    this.botService.createBot().subscribe((newBot) => {
      this.bots.push(newBot);

      this.onSelectBot(newBot.id);
    });

  }



  patch_bot(bot_id, data): void {
    console.log("patch_bot bot_id", bot_id)
    console.log("patch_bot data", data)
    this.botParametersService.patchBotParameters(bot_id, data).subscribe((botParameters) => {
      this.selected_bot.id = botParameters.bot_id
    });
  }

  patchAvatarCache(avatar_id: number, data: Partial<Avatar>): void {
    console.log("patchAvatar avatar_id", avatar_id);
    console.log("patchAvatar data", data);
    for (let bot of this.bots) {
      if (bot.avatar.id === avatar_id) {
        bot.avatar = { ...bot.avatar, ...data };
        this.selected_bot.avatar = { ...this.selected_bot.avatar, ...data };
        ;
      }
    }
  }
  updateBot(bot: Bot): void {
    this.botService.updateBot(bot).subscribe((bot) => {
      this.loadBots();
    });
  }



  createBotParameters(botParameters: BotParameters): void {
    console.log('Bot parameters: ', botParameters);
    this.botParametersService.createBotParameters(botParameters).subscribe((new_botParameters) => {
      console.log('Bot parameters created: ', new_botParameters);
    });
  }

  updateBotPArameters(botParameters: BotParameters): void {
    console.log('Bot parameters: ', botParameters);
    if (botParameters.bot_id)
      this.botParametersService.updateBotParameters(botParameters).subscribe((data) => {
      })

  }


  updateAvatar(avatar: Avatar): void {
    this.avatarService.updateAvatar(avatar).subscribe((updated_avatar) => {
      console.log('Avatar updated: ', updated_avatar);
      this.totalPages = Math.ceil(this.bots.length / this.pageSize);
      this.loadBots()
    });
  }


  deleteBot(bot_id: number): void {
    // Convertir la méthode synchrone en Observable
    if (confirm("Are you sure you want to delete this bot?")) {

      this.botService.deleteBot(bot_id).subscribe(() => {
        this.bots = this.bots.filter((bot) => bot.id !== bot_id);
        this.totalPages = Math.ceil(this.bots.length / this.pageSize);
        this.selected_bot = null;
        if (this.bots.length > 0)
          this.selected_bot = this.bots[0];
      });

    }
  }


  // Méthode pour ajuster la taille de l'avatar en fonction de la taille d'écran
  getAvatarSize(): number {
    return this.screenWidth < 576 ? 64 : 96;
  }

  getTrunkLength(): number {
    return this.screenWidth < 576 ? 64 : 256;
  }


  openDrawDialog(bot: Bot): void {
    const dialogWidth = this.screenWidth < 576 ? '100vw' : '1024px';
    const dialogHeight = this.screenWidth < 576 ? '100vh' : '512px';
    let avatar_copy: Avatar = {
      body: bot.avatar.body,
      body_color: bot.avatar.body_color,
      eyes: bot.avatar.eyes,
      eyes_color: bot.avatar.eyes_color,
      hat: bot.avatar.hat,
      hat_color: bot.avatar.hat_color,
      mouth: bot.avatar.mouth,
      mouth_color: bot.avatar.mouth_color
    }
    const drawDialogRef = this.dialog.open(BotDrawComponent, {
      // width: dialogWidth,
      // height: dialogHeight,

      data: { avatar: avatar_copy }
    });

    drawDialogRef.afterClosed().subscribe(data => {
      if (data) {
        bot.avatar.body = data.avatar.body
        bot.avatar.body_color = data.avatar.body_color
        bot.avatar.eyes = data.avatar.eyes
        bot.avatar.eyes_color = data.avatar.eyes_color
        bot.avatar.hat = data.avatar.hat
        bot.avatar.hat_color = data.avatar.hat_color
        bot.avatar.mouth = data.avatar.mouth
        bot.avatar.mouth_color = data.avatar.mouth_color
        this.updateAvatar(bot.avatar);
      }
    });
  }

  get isAdmin() {
    return this.authService.currentjwtValue?.roles === USER_ROLES.ADMIN;
  }

  get isUser() {
    return this.authService.currentjwtValue?.roles === USER_ROLES.USER;
  }


  get isGuest() {
    return this.authService.currentjwtValue?.roles === USER_ROLES.GUEST;
  }

}


