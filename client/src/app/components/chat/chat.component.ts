import { Component, OnInit, OnChanges, OnDestroy, SimpleChanges, ViewChild, ElementRef, ChangeDetectorRef, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormControl, FormGroup, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { ChatService, ChatServiceUser } from '@services/chat.service'
import { Observable, Subject, Subscription } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { BotService } from '@app/services/bot.service';
import { Bot } from '@app/models/bot.model';
import { FrameComponent } from '@app/components/base/frame/frame.component';
import { FormFieldComponent } from '../base/form-field/form-field.component';
import { ButtonComponent } from '../base/button/button.component';
import { CommunicationService } from '@app/services/communication.service';
import { TextToSpeechService } from '@app/services/text-to-speech.service';
import {SvgAvatarComponent} from '@app/components/bot-list/bot-draw/svg-avatar/svg-avatar.component'
interface ChatMessage {
  content?: string;
  type?: 'user' | 'assistant';
  timestamp?: Date;
  isPlaying?: boolean;
  // true while this exact message is still being received from the
  // backend. The message is pushed into `messages[]` (and its one DOM
  // node created) the moment the response starts, then mutated in place
  // as each network chunk arrives -- never destroyed/recreated -- so
  // there is no ghost-to-permanent DOM swap to cause flicker, z-index
  // resets, scroll jumps, or bubble reshaping at completion (all
  // previously reported and fixed as symptoms of that swap).
  isStreaming?: boolean;
}

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [CommonModule, FormsModule, SvgAvatarComponent, FrameComponent, FormFieldComponent, ButtonComponent, ReactiveFormsModule],
  templateUrl: './chat.component.html',
  styleUrl: './chat.component.scss'
})
export class ChatComponent implements OnInit, OnChanges, OnDestroy, ChatServiceUser {
  @Input() bot: Bot;
  @ViewChild('scrollContainer') private scrollContainer!: ElementRef;
  @ViewChild('inputField') private inputField!: ElementRef;
  chatForm: FormGroup;
  messageToSendCtrl = new FormControl('', [])
  messages: Array<ChatMessage> = [];
  newInputMessage = '';
  private destroy$ = new Subject<void>();
  lastMessage: ChatMessage = {};
  public isLoading: boolean = false;
  currentResponse: string = '';
  response: Observable<string> = new Observable<string>();
  private scrollToBottom = false;
  selected_bot: Bot = {
    id: -1,
  }
  public highlightInput = false;

  // ===== Streaming state =====
  // true tant qu'une réponse assistant est en cours de réception --
  // pilote le curseur clignotant et désactive l'envoi d'un nouveau message.
  public isTyping: boolean = false;
  // Référence vers l'entrée de `messages[]` en cours de réception -- mutée
  // en place (`.content`) à chaque paquet réseau, jamais remplacée.
  private streamingMessage: ChatMessage | null = null;
  private responseSub?: Subscription;
  constructor(private http: HttpClient,
    private chatService: ChatService,
    private cdr: ChangeDetectorRef, private botService: BotService,
    private fb: FormBuilder,
    private communicationService: CommunicationService,
    private textToSpeechService: TextToSpeechService
  ) {



  }


  ngOnInit(): void {
    this.chatForm = this.fb.group({
      message_to_send: this.messageToSendCtrl,
    });

    // Initialiser le bot si fourni via Input
    if (this.bot) {
      this.initBot(this.bot);
    }

    // Bot selection is handled exclusively via the [bot] @Input binding in
    // ngOnChanges (bot-workspace passes it down from the same
    // triggerOnSelectBot$ event, and only ever renders <app-chat> when a
    // bot is actually selected). Subscribing to that same BehaviorSubject
    // here too used to let it replay a *stale* previously-selected bot id
    // to this component on (re)creation -- independent of whatever
    // bot-workspace's own current state actually was -- firing
    // GET /api/rag/trigfirstmessage for a bot nothing in the UI showed as
    // selected.

    // Signaler que le composant est initialisé
    this.communicationService.onComponentReady('ChatComponent');
  }

  ngOnChanges(changes: SimpleChanges): void {
    // Détecter les changements du bot passé via Input
    if (changes['bot'] && changes['bot'].currentValue) {
      this.initBot(changes['bot'].currentValue);
    }
  }

  initBot(bot: Bot) {
    if (bot.id != this.selected_bot.id) {
      this.messages = []
      this.selected_bot = bot
      this.highlightInputField();
      this.chatService.getMessageHistory(this.selected_bot.id).subscribe({
        next: (response) => {
          console.log('Status:', response);
          if (response.status == 200) {
            this.messages = response.body.map((message) => ({
              content: message.content,
              type: message.role === 'user' ? 'user' : 'assistant',
              timestamp: message.time
            }));
            this.cdr.detectChanges();
            // Multiple scroll attempts to ensure it works after animations complete (0.4s slideInUp animation)
            this.scrollToBottomOfChat();
            setTimeout(() => this.scrollToBottomOfChat(), 100);
            setTimeout(() => this.scrollToBottomOfChat(), 300);
            setTimeout(() => this.scrollToBottomOfChat(), 500);
          }
          if (response.status == 204) {
            this.beginAssistantStream(this.chatService.concatenateFirstMessageStream(this.selected_bot.id, this));
          }
        },
        error: (error) => {
          console.error('Error loading message history:', error);
          if (error.status === 403) {
            this.addMessage({
              type: 'assistant',
              content: 'Access denied. You do not have the required permissions to access this conversation history.',
              timestamp: new Date()
            });
          } else {
            this.addMessage({
              type: 'assistant',
              content: `Une erreur est survenue lors du chargement de l'historique (Code: ${error.status || 'inconnu'}).`,
              timestamp: new Date()
            });
          }
          this.cdr.detectChanges();
        }
      });
    }
  }

  private highlightInputField(): void {
    this.highlightInput = true;
    setTimeout(() => {
      this.highlightInput = false;
      this.cdr.detectChanges();
    }, 2000);
  }

  ngAfterViewChecked() {
    if (this.scrollToBottom) {
      this.scrollToBottomOfChat();
      this.scrollToBottom = false;
    }
  }

  scrollToBottomOfChat(): void {
    try {
      if (this.scrollContainer && this.scrollContainer.nativeElement) {
        const element = this.scrollContainer.nativeElement;
        // `.messages-container` a `scroll-behavior: smooth` en CSS, qui
        // s'applique aussi à une simple affectation de `scrollTop` (pas
        // seulement à scrollIntoView/scrollTo sans option `behavior`) --
        // contrairement à ce que dit le commentaire d'origine ("scroll
        // immédiatement"), ce n'était donc PAS instantané. Appelé à chaque
        // caractère révélé par le typewriter (toutes les ~20ms), ça
        // empilait des animations de scroll smooth qui s'interrompaient
        // les unes les autres -- effet d'ascenseur qui rebondit, surtout
        // visible au moment où la bulle de streaming est remplacée par le
        // message permanent (vraie variation de hauteur au même instant).
        // Piège : `behavior: 'auto'` ne veut PAS dire "instantané", ça
        // signifie "se conformer au `scroll-behavior` CSS" (donc smooth
        // ici, aucun changement par rapport à avant) -- seul `'instant'`
        // force réellement un saut immédiat en ignorant le CSS.
        element.scrollTo({ top: element.scrollHeight, behavior: 'instant' as ScrollBehavior });
      }
    } catch (err) {
      console.error('Error scrolling to bottom:', err);
    }
  }

  addMessage(message: ChatMessage) {
    this.messages.push({
      ...message,
      timestamp: message.timestamp || new Date()
    });
    this.scrollToBottom = true;
  }

  onSubmit() {
    // [disabled]="isLoading || isTyping" on the input already prevents this
    // in the UI, but the form's (ngSubmit) can still fire on Enter in some
    // edge cases -- guard here too rather than relying on the template alone.
    if (this.isLoading || this.isTyping) return;
    this.newInputMessage = this.messageToSendCtrl.value.trim()
    if (!this.newInputMessage.trim()) return;

    // Ajouter le message de l'utilisateur
    this.addMessage({
      type: 'user',
      content: this.newInputMessage.trim(),
      timestamp: new Date()
    });

    this.isLoading = true;
    const userMessage = this.newInputMessage.trim();
    this.newInputMessage = '';
    this.currentResponse = '';
    this.messageToSendCtrl.reset();
    this.beginAssistantStream(this.chatService.concatenateChatStream([userMessage], this.selected_bot.id, this));
  }

  // Appelé par ChatService à chaque paquet réseau reçu. La valeur elle-même
  // est captée par la souscription faite dans beginAssistantStream() (seul
  // moyen d'obtenir le texte accumulé sans relire chatService.get_response(),
  // qui vide son buffer et n'est prévu que pour un appel unique en fin de
  // flux) -- ce hook ne fait donc rien de plus ici, gardé pour satisfaire
  // l'interface ChatServiceUser.
  update() {}

  complete(): void {
    // Le réseau a fini : chatService.get_response() donne le texte
    // définitif, utilisé pour être sûr d'avoir exactement le texte final
    // même si un `next()` a été manqué -- en pratique déjà à jour, le
    // dernier `next()` (avant le [DONE] réseau) contient déjà tout.
    if (this.streamingMessage) {
      this.streamingMessage.content = this.chatService.get_response();
    }
    this.finishStreaming();
  }

  /**
   * Démarre la consommation d'un flux de réponse assistant : la valeur
   * accumulée arrive via l'Observable retourné par ChatService (souscrite
   * ici, pas via `| async` dans le template -- ChatService construit un
   * Observable froid, une resouscription depuis le template ouvrirait une
   * 2e connexion SSE en doublon). Chaque paquet reçu est affiché
   * immédiatement (pas de lissage/délai artificiel) : la réponse s'affiche
   * au même rythme qu'elle est streamée par le backend.
   */
  private beginAssistantStream(response$: Observable<string>): void {
    this.response = response$;

    // Une nouvelle réponse ne peut normalement pas démarrer tant que
    // isLoading/isTyping bloque l'envoi (cf. [disabled]="isLoading ||
    // isTyping" dans le template) -- filet de sécurité si ce flux est
    // malgré tout déclenché pendant qu'un précédent tourne encore (ex.
    // changement de bot en cours de réponse) : on termine l'ancien avant
    // de démarrer le nouveau plutôt que de laisser deux souscriptions
    // actives en parallèle.
    if (this.isTyping) {
      this.finishStreaming();
    }
    this.responseSub?.unsubscribe();

    this.isTyping = true;

    // Le message est créé une seule fois, ici, puis muté en place
    // (streamingMessage.content) à chaque paquet réseau -- jamais
    // détruit/recréé, donc son animation d'entrée ne joue qu'une fois (au
    // début) et sa bulle ne "saute" jamais entre deux formes différentes.
    this.streamingMessage = { type: 'assistant', content: '', isStreaming: true, timestamp: new Date() };
    this.messages.push(this.streamingMessage);
    this.scrollToBottom = true;

    this.responseSub = response$.pipe(takeUntil(this.destroy$)).subscribe({
      next: (value) => {
        if (this.streamingMessage) {
          this.streamingMessage.content = value;
        }
        this.cdr.detectChanges();
        this.scrollToBottomOfChat();
      },
      error: (err) => {
        console.error('Error in assistant response stream:', err);
        this.finishStreaming();
      }
      // La complétion "réseau terminé" arrive via ChatServiceUser.complete()
      // (appelé directement par ChatService), pas via le complete() de cet
      // Observable -- même mécanisme que l'existant.
    });
  }

  private finishStreaming(): void {
    this.responseSub?.unsubscribe();
    this.isTyping = false;
    this.isLoading = false;

    if (this.streamingMessage) {
      if (this.streamingMessage.content) {
        this.streamingMessage.isStreaming = false;
        this.streamingMessage.timestamp = new Date();
      } else {
        // Rien reçu (ex. erreur réseau avant le premier chunk) : retirer la
        // bulle vide plutôt que de laisser un message assistant sans texte.
        const idx = this.messages.indexOf(this.streamingMessage);
        if (idx !== -1) {
          this.messages.splice(idx, 1);
        }
      }
    }
    this.streamingMessage = null;

    this.cdr.detectChanges();
    this.scrollToBottomOfChat();
  }

  resetChat() {
    this.messages = [];
    // this.lastMessage = null;
    this.response = null;
    if (this.chatForm) {
      this.chatForm.reset();
    }
    this.chatService.deleteMessageHistory(this.selected_bot.id).subscribe({
      next: (response) => {
        console.log('Message history deleted:', response);
        this.beginAssistantStream(this.chatService.concatenateFirstMessageStream(this.selected_bot.id, this));
        this.scrollToBottom = true;
        this.cdr.detectChanges();
      },
      error: (error) => {
        console.error('Error deleting message history:', error);
        if (error.status === 403) {
          this.addMessage({
            type: 'assistant',
            content: 'Access denied. You do not have the required permissions to delete this conversation history.',
            timestamp: new Date()
          });
        } else {
          this.addMessage({
            type: 'assistant',
            content: `Une erreur est survenue lors de la suppression de l'historique (Code: ${error.status || 'inconnu'}).`,
            timestamp: new Date()
          });
        }
        this.cdr.detectChanges();
      }
    });
  }

  playMessage(message: ChatMessage) {
    if (!message.content) return;
    
    message.isPlaying = true;
    this.textToSpeechService.textToSpeechAndPlay(message.content).subscribe({
      next: () => {
        message.isPlaying = false;
        this.cdr.detectChanges();
      },
      error: (error) => {
        console.error('Error playing audio:', error);
        message.isPlaying = false;
        this.cdr.detectChanges();
      }
    });
  }

  ngOnDestroy() {
    this.destroy$.next();
    this.destroy$.complete();
  }
}
