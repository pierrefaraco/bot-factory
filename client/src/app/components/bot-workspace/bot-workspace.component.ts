import { Component, OnInit, OnDestroy, ViewChild, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router, ActivatedRoute } from '@angular/router';
import { Subscription } from 'rxjs';

// Composants
import { BotListComponent } from '../bot-list/bot-list.component';
import { ChatComponent } from '../chat/chat.component';
import { KnowledgesComponent } from '../knowledges/knowledges.component';
import { BotParamsComponent } from '../bot-list/bot-params/bot-params.component';
import { SvgAvatarComponent } from '../bot-list/bot-draw/svg-avatar/svg-avatar.component';
import { BotDrawComponent } from '../bot-list/bot-draw/bot-draw.component';
// Services
import { BotService } from '../../services/bot.service';
import { CommunicationService } from '../../services/communication.service';
import { AuthService } from '../../services/auth.service';
import { Bot } from '../../models/bot.model';
import { Avatar } from '@app/models/avatar.model';
import { ButtonComponent } from '../base/button/button.component';
import { KnowledgeEditorComponent } from '../knowledges/knowledge-editor/knowledge-editor.component';
import { USER_ROLES } from '../../constants/user-roles.constants';

@Component({
  selector: 'app-bot-workspace',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    BotListComponent,
    ChatComponent,
    KnowledgesComponent,
    KnowledgeEditorComponent,
    BotParamsComponent,
    SvgAvatarComponent,
    BotDrawComponent,
    ButtonComponent,

  ],
  templateUrl: './bot-workspace.component.html',
  styleUrls: ['./bot-workspace.component.scss']
})
export class BotWorkspaceComponent implements OnInit, OnDestroy {
  activeTab: 'overview' | 'chat' | 'knowledge' | 'settings' | 'draw' = 'overview';
  selectedBot: Bot | null = null;
  bots: Bot[] = [];
  loading = true;
  showBotList = true;
  botListLayout: 'horizontal' | 'vertical' = 'vertical';
  private subscriptionSubmitPatchBot: Subscription;
  private subscriptionSelectBot: Subscription;
  @ViewChild(BotListComponent) botListComponent!: BotListComponent;
  @ViewChild(ChatComponent) chatComponent!: ChatComponent;

  constructor(
    private communicationService: CommunicationService,
    private router: Router,
    private route: ActivatedRoute,
    private botService: BotService,
    private authService: AuthService
  ) {
    this.updateLayoutBasedOnScreenSize();
  }

  @HostListener('window:resize')
  onResize(): void {
    this.updateLayoutBasedOnScreenSize();
  }

  private updateLayoutBasedOnScreenSize(): void {
    const screenWidth = window.innerWidth;
    this.botListLayout = screenWidth < 1024 ? 'horizontal' : 'vertical';
  }

  ngOnInit(): void {
    // Écouter les changements de bot sélectionné

    this.subscriptionSelectBot = this.communicationService.triggerOnSelectBot$.subscribe((bot) => {
      console.log('BotWorkspaceComponent', bot)
      this.selectedBot = bot;
    });

    this.subscriptionSubmitPatchBot = this.communicationService.triggerSubmitPatchBot$.subscribe((result) => {
      console.log("BotWorkspaceComponent: patchBot bot triggered!", result.data);
      // Mettre à jour tous les paramètres reçus dans result.data
      if (this.selectedBot && this.selectedBot.bot_parameters) {
        Object.keys(result.data).forEach(key => {
          this.selectedBot.bot_parameters[key] = result.data[key];
        });
      }
    });
    // Charger le bot actif
    // this.botService.getActiveBot().subscribe({
    //   next: (bot) => {
    //     this.selectedBot = bot;
    //      console.info('Following Bot has been selected',bot );
    //     this.loading = false;
    //   },
    //   error: (error) => {
    //     console.error('Error loading active bot:', error);
    //     this.loading = false;
    //   }
    // });

    // Récupérer l'onglet depuis les query params
    const validTabs: typeof this.activeTab[] = ['overview', 'chat', 'knowledge', 'settings', 'draw'];
    this.route.queryParams.subscribe(params => {
      // Une valeur non reconnue (lien externe/marque-page obsolète, faute de
      // frappe) laissait `activeTab` sur cette valeur : aucun onglet ne
      // matchait plus dans le template, page vide sans repli ni message.
      // 'settings'/'knowledge'/'draw' restent dans validTabs pour tout le
      // monde (ce ne sont pas des valeurs invalides), mais un Guest y
      // arrivant par un lien direct ne doit ni les voir ni pouvoir
      // déclencher les appels (GET /api/knowledge, GET
      // /api/bot/parameters-description, PATCH /api/avatar) qu'il n'a pas
      // le droit d'appeler (403 côté serveur) -- repli sur l'onglet par
      // défaut.
      const restrictedForGuest = ['settings', 'knowledge', 'draw'];
      if (this.isGuest && restrictedForGuest.includes(params['tab'])) {
        return;
      }
      if (validTabs.includes(params['tab'])) {
        this.activeTab = params['tab'];
      }
    });

    // Signaler que le composant est initialisé
    this.communicationService.onComponentReady('BotWorkspaceComponent');
  }

  ngOnDestroy(): void {
    if (this.subscriptionSelectBot) {
      this.subscriptionSelectBot.unsubscribe();
    }
  }

  setActiveTab(tab: 'overview' | 'chat' | 'knowledge' | 'settings' | 'draw'): void {
    this.activeTab = tab;
    // Mettre à jour l'URL sans recharger la page
    this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { tab },
      queryParamsHandling: 'merge'
    });

    // Scroller vers le bas du chat quand on ouvre l'onglet Discussion
    if (tab === 'chat' && this.chatComponent) {
      setTimeout(() => {
        this.chatComponent.scrollToBottomOfChat();
      }, 100);
    }
  }

  resetChat(){
    this.chatComponent.resetChat()
  }

  toggleBotList(): void {
    this.showBotList = !this.showBotList;
  }

  onCreateBot(): void {
    this.communicationService.onCreateBot();
  }

  deleteBot(bot_id: number): void {
    console.log('delete bot')
    // Convertir la méthode synchrone en Observable
    if (confirm("Are you sure you want to delete this bot?")) {

      this.botService.deleteBot(bot_id).subscribe(() => {
        this.selectedBot = null;
        this.botListComponent.refresh();
      });

    }
  }

  get hasSelectedBot(): boolean {
    return this.selectedBot !== null && this.selectedBot.id !== -1;
  }

  // GET /api/knowledge/<id>, GET /api/bot/parameters-description, PATCH
  // /api/avatar, POST /api/bot and DELETE /api/bot/<id> are all
  // role_required([ADMIN_ROLE, USER_ROLE]) server-side -- GUEST is
  // deliberately excluded (bot configuration/knowledge/avatar editing and
  // bot creation/deletion aren't Guest capabilities, only chatting with an
  // assigned bot is). The Settings/Knowledge/Avatar tabs, their child
  // components (<app-bot-params>, <app-knowledges>, <app-bot-draw>), both
  // "Create a new bot" buttons and the "Delete selected bot" menu used to
  // be rendered unconditionally regardless of role, so a Guest could fire
  // requests guaranteed to 403 just by selecting a bot or clicking around.
  get isGuest(): boolean {
    return this.authService.getUserRole() === USER_ROLES.GUEST;
  }

  // DELETE /api/bot/<id> is ownership-scoped server-side (_can_modify_bot,
  // rest_bot.py): a User can only delete a bot they created themselves,
  // Admin bypasses unconditionally. "My Bots" now also lists bots merely
  // *assigned* to a User (bot_svc.get_owned_and_assigned_bots), so
  // selecting one of those and hitting "Delete selected bot" would
  // otherwise be a guaranteed 403.
  get canDeleteSelectedBot(): boolean {
    if (this.isAdmin) return true;
    return this.selectedBot?.user_account_id === this.authService.get_curent_user_id();
  }

  get isAdmin(): boolean {
    return this.authService.getUserRole() === USER_ROLES.ADMIN;
  }

  get botName(): string {
    return this.selectedBot?.bot_parameters?.bot_name || 'No bot selected';
  }

  get totalBots(): number {
    return this.bots.length;
  }

  get hasAvatar(): boolean {
    return this.selectedBot !== null && this.selectedBot.avatar !== null;
  }

  avatar(): Avatar {
    return this.selectedBot.avatar
  }
}
