import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

interface HelpSection {
  title: string;
  content: string;
  icon: string;
}

@Component({
  selector: 'app-help',
  templateUrl: './help.component.html',
  styleUrls: ['./help.component.scss'],
  standalone: true,
  imports: [CommonModule]
})
export class HelpComponent {
  sections: HelpSection[] = [
    {
      title: 'Bot Craft',
      content: 'Bot Craft is your workspace: pick a bot from the list on the left, or create a new one, then chat with it from the Overview tab.<br><br>Guests only see Overview — Settings, Knowledge and Avatar belong to the bot\'s owner.',
      icon: 'smart_toy'
    },
    {
      title: 'Settings',
      content: 'Configure the selected bot\'s personality, communication style and capabilities from the Settings tab.',
      icon: 'tune'
    },
    {
      title: 'Knowledge',
      content: 'Build the bot\'s knowledge base from the Knowledge tab: organize a tree of chapters on the left, and edit each item\'s content on the right so the bot can answer from it.',
      icon: 'auto_stories'
    },
    {
      title: 'Avatar',
      content: 'Customize the bot\'s look from the Avatar tab — body, eyes, hat, mouth and colors.',
      icon: 'brush'
    },
    {
      title: 'Administration',
      content: 'Available to Admins, and to Users managing their own guests.<br><br>The Guest tab lists your guests — assign bots, edit details, change password, activate/deactivate or delete a guest from its action menu (⋮), and see its token usage over the last 24 hours and 30 days. The Users tab (Admin only) covers every account platform-wide.',
      icon: 'admin_panel_settings'
    },
    {
      title: 'Token usage',
      content: 'Track your own token consumption from the Token stats page, available from the user menu — totals, last-24h usage, and a breakdown between prompt and completion tokens.',
      icon: 'insights'
    },
    {
      title: 'Account',
      content: 'From the user menu (top right), edit your account details, change your password, switch between light and dark theme, or sign out.',
      icon: 'account_circle'
    }
  ];
}
