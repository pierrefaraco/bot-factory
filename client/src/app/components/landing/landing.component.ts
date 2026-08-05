import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { ButtonComponent } from '../base/button/button.component';

@Component({
  selector: 'app-landing',
  standalone: true,
  imports: [CommonModule, ButtonComponent],
  templateUrl: './landing.component.html',
  styleUrl: './landing.component.scss'
})
export class LandingComponent {
  mobileMenuOpen = false;

  features = [
    {
      icon: 'smart_toy',
      title: 'Create Custom Bots',
      description: 'Design and personalize your AI bots with unique avatars, personalities, and capabilities.'
    },
    {
      icon: 'chat',
      title: 'Real-time Chat',
      description: 'Engage in natural conversations with your bots powered by advanced AI technology.'
    },
    {
      icon: 'storage',
      title: 'Knowledge Management',
      description: 'Upload and manage data sources to enhance your bots\' knowledge base.'
    },
    {
      icon: 'palette',
      title: 'Visual Customization',
      description: 'Customize every aspect of your bot\'s appearance with our intuitive avatar builder.'
    },
    {
      icon: 'insights',
      title: 'Analytics & Stats',
      description: 'Track token usage, conversation metrics, and performance insights.'
    },
    {
      icon: 'groups',
      title: 'Multi-Bot Management',
      description: 'Create and manage multiple bots for different purposes and contexts.'
    }
  ];

  steps = [
    {
      number: '1',
      icon: 'person_add',
      title: 'Sign Up',
      description: 'Create your account in seconds and get started immediately.'
    },
    {
      number: '2',
      icon: 'build',
      title: 'Customize Your Bot',
      description: 'Use our visual builder to design your bot\'s appearance and personality.'
    },
    {
      number: '3',
      icon: 'rocket_launch',
      title: 'Start Chatting',
      description: 'Begin conversations with your AI companion and explore its capabilities.'
    }
  ];

  stats = [
    { value: '10K+', label: 'Active Users' },
    { value: '50K+', label: 'Bots Created' },
    { value: '1M+', label: 'Conversations' },
    { value: '99.9%', label: 'Uptime' }
  ];

  constructor(private router: Router) {}


  navigateToAuth() {
    this.router.navigate(['/auth']);
  }

  scrollToSection(sectionId: string) {
    const element = document.getElementById(sectionId);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    this.mobileMenuOpen = false;
  }

  toggleMobileMenu() {
    this.mobileMenuOpen = !this.mobileMenuOpen;
  }

  closeMobileMenu() {
    this.mobileMenuOpen = false;
  }
}
