import { Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class ThemeService {
  private readonly THEME_KEY = 'app-theme';
  private theme: string;

  constructor() {
    // Récupérer le thème sauvegardé ou utiliser le thème par défaut
    this.theme = localStorage.getItem(this.THEME_KEY) || 'dark-theme';
    // Appliquer le thème au démarrage
    this.applyTheme(this.theme);
  }

  get isDarkMode() {
    return this.theme === 'dark-theme';
  }

  private applyTheme(theme: string) {
    // Retirer l'ancien thème
    document.documentElement.classList.remove('light-theme', 'dark-theme');
    // Appliquer le nouveau thème
    document.documentElement.classList.add(theme);
    // Sauvegarder le thème
    localStorage.setItem(this.THEME_KEY, theme);
    this.theme = theme;
  }

  toggleTheme() {
    const newTheme = this.theme === 'light-theme' ? 'dark-theme' : 'light-theme';
    this.applyTheme(newTheme);
  }
}