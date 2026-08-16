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
      title: 'Chat with Alfred',
      content: 'To talk with Alfred, go to the Chat section. You can ask questions and get natural, instant answers.<br><br>Use the prompt suggestions to start a conversation.',
      icon: 'forum'
    },
    {
      title: 'Data management',
      content: 'The Data section lets you view and manage the data available in the system.<br><br>Import, export and analyze your data in a few clicks.',
      icon: 'storage'
    },
    {
      title: 'Administration',
      content: 'Administrators can manage users and their permissions in the Admin section.<br><br>Manage permissions and monitor system activity in real time.',
      icon: 'admin_panel_settings'
    },
    {
      title: 'User profile',
      content: 'You can edit your personal information in the Profile section, available from the user menu.<br><br>Customize your experience and manage your preferences.',
      icon: 'account_circle'
    }
  ];
}
