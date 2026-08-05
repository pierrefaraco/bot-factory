import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

interface HelpSection {
  titre: string;
  contenu: string;
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
      titre: 'Chat avec Alfred',
      contenu: 'Pour discuter avec Alfred, rendez-vous dans la section Chat. Vous pouvez lui poser des questions et il vous répondra de manière naturelle et instantanée.<br><br>Utilisez les suggestions de prompts pour démarrer une conversation.',
      icon: 'fas fa-comments'
    },
    {
      titre: 'Gestion des données',
      contenu: 'La section Data vous permet de visualiser et gérer les données disponibles dans le système.<br><br>Importez, exportez et analysez vos données en quelques clics.',
      icon: 'fas fa-database'
    },
    {
      titre: 'Administration',
      contenu: 'Les administrateurs peuvent gérer les utilisateurs et leurs droits dans la section Admin.<br><br>Gérez les permissions et surveillez l\'activité du système en temps réel.',
      icon: 'fas fa-user-shield'
    },
    {
      titre: 'Profil utilisateur',
      contenu: 'Vous pouvez modifier vos informations personnelles dans la section Profile, accessible depuis le menu utilisateur.<br><br>Personnalisez votre expérience et gérez vos préférences.',
      icon: 'fas fa-user-circle'
    }
  ];
}