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
import { Bot } from '../../models/bot.model';
import { Avatar } from '@app/models/avatar.model';
import { ButtonComponent } from '../base/button/button.component';
import { KnowledgeEditorComponent } from '../knowledges/knowledge-editor/knowledge-editor.component';

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
    private botService: BotService
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
    this.route.queryParams.subscribe(params => {
      if (params['tab']) {
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

  get botName(): string {
    return this.selectedBot?.bot_parameters?.bot_name || 'Aucun bot sélectionné';
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
