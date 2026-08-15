import { Component, OnInit, OnChanges, SimpleChanges, ViewChild, ElementRef, ChangeDetectorRef, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormControl, FormGroup, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { ChatService, ChatServiceUser } from '@services/chat.service'
import { Observable, Subject,  Subscription } from 'rxjs';
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
}

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [CommonModule, FormsModule, SvgAvatarComponent, FrameComponent, FormFieldComponent, ButtonComponent, ReactiveFormsModule],
  templateUrl: './chat.component.html',
  styleUrl: './chat.component.scss'
})
export class ChatComponent implements OnInit, OnChanges, ChatServiceUser {
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
  private subscriptionSelectBot: Subscription;
  selected_bot: Bot = {
    id: -1,
  }
  public highlightInput = false;
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

    this.subscriptionSelectBot = this.communicationService.triggerOnSelectBot$.subscribe((bot) => {
      this.initBot(bot);
    });

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
            this.response = this.chatService.concatenateFirstMessageStream( this.selected_bot.id, this)
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
        // Scroll immédiatement au maximum
        element.scrollTop = element.scrollHeight;
        console.log('Scrolled to bottom:', element.scrollTop, 'of', element.scrollHeight);
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
    // this.response = this.chatService.chat(userMessage)
    this.messageToSendCtrl.reset();
    this.response = this.chatService.concatenateChatStream([userMessage], this.selected_bot.id, this)
  }

  update() {
    this.cdr.detectChanges();
    this.scrollToBottomOfChat();

  }

  complete(): void {
    console.log("finalize")
    this.isLoading = false;
    // Ajouter le message de l'assistant une fois terminé
    if (this.currentResponse || true) {
      console.log("addMessage")
      this.addMessage({
        type: 'assistant',
        content: this.chatService.get_response(),
        timestamp: new Date()
      });

      this.response = new Observable<string>();
    }
    this.cdr.detectChanges();
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
        this.response = this.chatService.concatenateFirstMessageStream( this.selected_bot.id, this)
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
