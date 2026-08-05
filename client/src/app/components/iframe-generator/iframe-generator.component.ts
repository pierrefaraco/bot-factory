import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { BotService } from '@app/services/bot.service';
import { Bot } from '@app/models/bot.model';

interface IframeConfig {
  botId: string;
  width: number;
  height: number;
  position: 'floating' | 'centered' | 'fullwidth';
  theme: 'light' | 'dark';
  primaryColor: string;
  secondaryColor: string;
  textColor: string;
  backgroundColor: string;
  borderRadius: number;
  showHeader: boolean;
  showAvatar: boolean;
  placeholderText: string;
  welcomeMessage: string;
  fontSize: number;
}

@Component({
  selector: 'app-iframe-generator',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './iframe-generator.component.html',
  styleUrls: ['./iframe-generator.component.scss']
})
export class IframeGeneratorComponent implements OnInit {
  activeTab: string = 'configure';
  bots: Bot[] = [];
  loadingBots: boolean = true;
  generatedCode: string = '';

  config: IframeConfig = {
    botId: '',
    width: 400,
    height: 600,
    position: 'floating',
    theme: 'light',
    primaryColor: '#667eea',
    secondaryColor: '#764ba2',
    textColor: '#333333',
    backgroundColor: '#ffffff',
    borderRadius: 15,
    showHeader: true,
    showAvatar: true,
    placeholderText: 'Écrivez votre message...',
    welcomeMessage: 'Bonjour ! Comment puis-je vous aider ?',
    fontSize: 14
  };

  // Sample messages for preview
  previewMessages = [
    { type: 'assistant', content: 'Bonjour ! Comment puis-je vous aider ?', time: '10:30' },
    { type: 'user', content: 'Bonjour, j\'ai une question', time: '10:31' }
  ];

  constructor(private botService: BotService) {}

  ngOnInit(): void {
    this.loadBots();
    this.generateCode();
  }

  loadBots(): void {
    this.loadingBots = true;
    this.botService.getUserBots().subscribe({
      next: (bots) => {
        this.bots = bots;
        if (bots.length > 0 && !this.config.botId) {
          this.config.botId = bots[0].id?.toString() || '';
        }
        this.loadingBots = false;
        this.generateCode();
      },
      error: (error) => {
        console.error('Error loading bots:', error);
        this.loadingBots = false;
      }
    });
  }

  setActiveTab(tab: string): void {
    this.activeTab = tab;
    if (tab === 'code') {
      this.generateCode();
    }
  }

  onConfigChange(): void {
    this.generateCode();
  }

  getSelectedBot(): Bot | undefined {
    return this.bots.find(bot => bot.id?.toString() === this.config.botId);
  }

  generateCode(): void {
    const baseUrl = window.location.origin;
    const iframeUrl = `${baseUrl}/chat?botId=${this.config.botId}&embedded=true`;

    const styleParams = [
      `theme=${this.config.theme}`,
      `primaryColor=${encodeURIComponent(this.config.primaryColor)}`,
      `secondaryColor=${encodeURIComponent(this.config.secondaryColor)}`,
      `textColor=${encodeURIComponent(this.config.textColor)}`,
      `backgroundColor=${encodeURIComponent(this.config.backgroundColor)}`,
      `borderRadius=${this.config.borderRadius}`,
      `fontSize=${this.config.fontSize}`,
      `showHeader=${this.config.showHeader}`,
      `showAvatar=${this.config.showAvatar}`,
      `placeholderText=${encodeURIComponent(this.config.placeholderText)}`,
      `welcomeMessage=${encodeURIComponent(this.config.welcomeMessage)}`
    ].join('&');

    const fullUrl = `${iframeUrl}&${styleParams}`;

    let containerStyle = '';
    if (this.config.position === 'floating') {
      containerStyle = `
  position: fixed;
  bottom: 20px;
  right: 20px;
  z-index: 9999;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
  border-radius: ${this.config.borderRadius}px;`;
    } else if (this.config.position === 'centered') {
      containerStyle = `
  margin: 0 auto;
  max-width: ${this.config.width}px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
  border-radius: ${this.config.borderRadius}px;`;
    } else {
      containerStyle = `
  width: 100%;
  max-width: 100%;`;
    }

    this.generatedCode = `<!-- AlfredReact Chat Widget -->
<div id="alfredreact-chat-container" style="${containerStyle}">
  <iframe
    src="${fullUrl}"
    width="${this.config.position === 'fullwidth' ? '100%' : this.config.width + 'px'}"
    height="${this.config.height}px"
    frameborder="0"
    allow="microphone"
    style="border-radius: ${this.config.borderRadius}px; display: block;">
  </iframe>
</div>`;
  }

  copyCode(): void {
    navigator.clipboard.writeText(this.generatedCode).then(() => {
      alert('Code copié dans le presse-papiers !');
    }).catch(err => {
      console.error('Error copying code:', err);
      alert('Erreur lors de la copie du code');
    });
  }

  getPreviewStyles() {
    return {
      'width': this.config.position === 'fullwidth' ? '100%' : this.config.width + 'px',
      'height': this.config.height + 'px',
      'border-radius': this.config.borderRadius + 'px',
      'background-color': this.config.backgroundColor,
      'color': this.config.textColor,
      'font-size': this.config.fontSize + 'px'
    };
  }

  getHeaderStyles() {
    return {
      'background': `linear-gradient(135deg, ${this.config.primaryColor}, ${this.config.secondaryColor})`
    };
  }

  getUserMessageStyles() {
    return {
      'background': `linear-gradient(135deg, ${this.config.primaryColor}, ${this.config.secondaryColor})`,
      'color': '#ffffff'
    };
  }

  getSendButtonStyles() {
    return {
      'background': `linear-gradient(135deg, ${this.config.primaryColor}, ${this.config.secondaryColor})`
    };
  }
}