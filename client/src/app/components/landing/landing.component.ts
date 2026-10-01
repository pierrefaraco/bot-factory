import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { ButtonComponent } from '../base/button/button.component';
import { AuthService } from '@app/services/auth.service';

@Component({
  selector: 'app-landing',
  standalone: true,
  imports: [CommonModule, ButtonComponent],
  templateUrl: './landing.component.html',
  styleUrl: './landing.component.scss'
})
export class LandingComponent implements OnInit {
  mobileMenuOpen = false;
  demoEnabled = false;
  demoLoading = false;

  readonly githubUrl = 'https://github.com/pierrefaraco/bot-factory';
  readonly linkedinUrl = 'https://www.linkedin.com/in/pierre-faraco-03088149/';
  readonly contactEmail = 'pierre.faraco@gmail.com';

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

  // "Meet My Digital Twin": a new bot is created with Pierre's persona
  // (BotParametersService.RANDOM_BOT_PROFILES) and his career knowledge
  // (server/src/resources/templates/start.txt).
  meetMe = [
    {
      icon: 'record_voice_over',
      title: 'Interview Me',
      description: 'Ask about my background, my current job or the projects I\'ve built, the way a recruiter or a technical interviewer would.'
    },
    {
      icon: 'tune',
      title: 'Change My Parameters',
      description: 'Change my personality, tone, answer length or who I think I\'m talking to, and see how my answers change.'
    },
    {
      icon: 'auto_stories',
      title: 'Edit My Knowledge',
      description: 'Browse, edit or extend the chapters I answer from, or upload a PDF: I only answer from what\'s in there.'
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
      icon: 'smart_toy',
      title: 'Create a Bot',
      description: 'Click "Create a new bot": it starts as my digital twin, with my career as its knowledge base.'
    },
    {
      number: '3',
      icon: 'record_voice_over',
      title: 'Interview or Reshape Me',
      description: 'Interview me in the chat, or change my parameters, avatar and knowledge to make the bot your own.'
    }
  ];

  engineering = [
    {
      icon: 'account_tree',
      title: 'Layered FastAPI Backend',
      description: 'Routers, services and repositories kept separate, wired together through FastAPI dependency injection.'
    },
    {
      icon: 'schema',
      title: 'Versioned Database Schema',
      description: 'SQLAlchemy models on MySQL with Alembic migrations, so every schema change is tracked and reproducible.'
    },
    {
      icon: 'security',
      title: 'Auth & Usage Limits',
      description: 'JWT and Google OAuth authentication, per-user data scoping and a configurable 24h token quota.'
    },
    {
      icon: 'hub',
      title: 'RAG Pipeline',
      description: 'Document ingestion into ChromaDB and retrieval-augmented answers through LangChain and Mistral AI.'
    },
    {
      icon: 'inventory_2',
      title: 'Containerized Deployment',
      description: 'The whole stack runs in Docker Compose, with separate dev and production configurations.'
    },
    {
      icon: 'lock',
      title: 'Nginx & Automated HTTPS',
      description: 'Nginx reverse proxy in front of the API, with Let\'s Encrypt certificates renewed automatically by Certbot.'
    }
  ];

  techStack = [
    { icon: 'bolt', name: 'Python + FastAPI' },
    { icon: 'storage', name: 'MySQL + SQLAlchemy' },
    { icon: 'history', name: 'Alembic Migrations' },
    { icon: 'hub', name: 'ChromaDB (RAG)' },
    { icon: 'psychology', name: 'LangChain + Mistral AI' },
    { icon: 'inventory_2', name: 'Docker Compose' },
    { icon: 'dns', name: 'Nginx' },
    { icon: 'lock', name: 'Let\'s Encrypt' },
    { icon: 'verified', name: 'pytest' },
    { icon: 'web', name: 'Angular' }
  ];

  constructor(private router: Router, private authService: AuthService) {}

  ngOnInit(): void {
    // Démo non configurée ou serveur injoignable : les boutons "Try the
    // demo" retombent sur la page de connexion, comme avant.
    this.authService.isDemoEnabled().subscribe({
      next: enabled => this.demoEnabled = enabled,
      error: () => this.demoEnabled = false,
    });
  }

  // Boutons "Try the demo" : connexion directe au compte de démo partagé.
  tryDemo() {
    if (this.authService.isAuthenticated()) {
      // Déjà connecté : on ne remplace pas sa session par celle de la démo.
      this.router.navigate(['/workspace']);
      return;
    }
    if (!this.demoEnabled) {
      this.navigateToAuth();
      return;
    }
    if (this.demoLoading) {
      return;
    }
    this.demoLoading = true;
    this.authService.loginDemo().subscribe({
      next: () => {
        this.demoLoading = false;
        this.router.navigate(['/workspace']);
      },
      error: () => {
        this.demoLoading = false;
        this.navigateToAuth();
      }
    });
  }


  navigateToAuth() {
    this.router.navigate(['/auth']);
  }

  // Liens "Create your own account" : formulaire d'inscription directement.
  navigateToSignup() {
    this.router.navigate(['/auth'], { queryParams: { mode: 'signup' } });
  }

  navigateToPolicies() {
    this.router.navigate(['/policies']);
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
