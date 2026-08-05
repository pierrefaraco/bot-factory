import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subject, takeUntil } from 'rxjs';
import { TokenStatsService } from '../../services/token-stats.service';
import {
  UserTokenStats,
  TokenUsageRecord,
  UserTokenStatsLast24h
} from '../../models/token-stats.model';
import { ButtonComponent } from '../base/button/button.component';

@Component({
  selector: 'app-token-stats',
  standalone: true,
  imports: [CommonModule, FormsModule, ButtonComponent],
  templateUrl: './token-stats.component.html',
  styleUrl: './token-stats.component.scss'
})
export class TokenStatsComponent implements OnInit, OnDestroy {
  // État du composant
  stats: UserTokenStats | null = null;
  history: TokenUsageRecord[] = [];
  loading = false;
  loadingHistory = false;
  error: string | null = null;
  historyLimit = 25;

  // Paramètre pour basculer entre tout le temps et 24h
  showLast24h = true;
  statsLast24h: UserTokenStatsLast24h | null = null;

  // Subject pour le nettoyage des abonnements
  private destroy$ = new Subject<void>();

  constructor(private tokenStatsService: TokenStatsService) {}

  ngOnInit(): void {
    this.toggleTimePeriod()
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  /**
   * Charge les statistiques de l'utilisateur
   */
  loadStats(): void {
    this.loading = true;
    this.error = null;

    this.tokenStatsService
      .getMyStats()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (data) => {
          this.stats = data;
          this.loading = false;
             this.loadHistory();
        },
        error: (err) => {
          console.error('Erreur lors du chargement des statistiques:', err);
          this.error = this.getErrorMessage(err);
          this.loading = false;
        }
      });
  }

  /**
   * Charge l'historique des requêtes
   */
  loadHistory(): void {
    this.loadingHistory = true;

    this.tokenStatsService
      .getMyHistory(this.historyLimit, this.showLast24h)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (data) => {
          this.history = data.history;
          this.loadingHistory = false;
         
        },
        error: (err) => {
          console.error('Erreur lors du chargement de l\'historique:', err);
          this.loadingHistory = false;
        }
      });
  }

  /**
   * Charge les statistiques des 24 dernières heures
   */
  loadStatsLast24h(): void {
    this.tokenStatsService
      .getMyStatsLast24h()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (data) => {
          this.stats = data;
          this.loading = false;
          this.loadHistory();
        },
        error: (err) => {
          console.error('Erreur lors du chargement des statistiques:', err);
          this.error = this.getErrorMessage(err);
          this.loading = false;
        }
      });
  }

  /**
   * Bascule entre l'affichage des stats 24h et tout le temps
   */
  toggleTimePeriod(): void {
    console.log('Toggling time period');
    this.showLast24h = !this.showLast24h;
    if (this.showLast24h) {
      this.loadStatsLast24h();
    } else {
      this.loadStats();
    }
  }

  /**
   * Retourne le total de tokens à afficher selon la période sélectionnée
   */
  getDisplayedTotal(): number {
    return this.stats?.total_tokens || 0;
  }

  /**
   * Retourne les stats à afficher selon la période sélectionnée
   */
  getDisplayedStats(): UserTokenStats | UserTokenStatsLast24h | null {
    return this.stats;
  }

  /**
   * Rafraîchit toutes les données
   */
  refreshStats(): void {
     this.toggleTimePeriod()
  }

  /**
   * Formate un nombre avec des espaces pour les milliers
   */
  formatNumber(num: number): string {
    return num.toLocaleString('fr-FR');
  }

  /**
   * Calcule la moyenne de tokens par requête
   */
  getAverageTokensPerRequest(): string {
    if (!this.stats || this.stats.total_requests === 0) {
      return '0';
    }
    const average = Math.round(this.stats.total_tokens / this.stats.total_requests);
    return this.formatNumber(average);
  }

  /**
   * Calcule le pourcentage de tokens de prompt
   */
  getPromptPercentage(): string {
    if (!this.stats || this.stats.total_tokens === 0) {
      return '0';
    }
    const percentage = (this.stats.total_prompt_tokens / this.stats.total_tokens) * 100;
    return percentage.toFixed(1);
  }

  /**
   * Calcule le pourcentage de tokens de complétion
   */
  getCompletionPercentage(): string {
    if (!this.stats || this.stats.total_tokens === 0) {
      return '0';
    }
    const percentage = (this.stats.total_completion_tokens / this.stats.total_tokens) * 100;
    return percentage.toFixed(1);
  }

  /**
   * Formate un timestamp au format français
   * Convertit "28/11/2025 14:30:00" en format lisible
   */
  formatTimestamp(timestamp: string): string {
    try {
      // Format d'entrée: "DD/MM/YYYY HH:MM:SS"
      const [datePart, timePart] = timestamp.split(' ');
      const [day, month, year] = datePart.split('/');
      const [hours, minutes] = timePart.split(':');

      const date = new Date(
        parseInt(year),
        parseInt(month) - 1,
        parseInt(day),
        parseInt(hours),
        parseInt(minutes)
      );

      // Vérifier si la date est valide
      if (isNaN(date.getTime())) {
        return timestamp; // Retourner le timestamp original si invalide
      }

      // Formater la date
      const now = new Date();
      const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
      const dateToCheck = new Date(date.getFullYear(), date.getMonth(), date.getDate());

      // Si c'est aujourd'hui, afficher seulement l'heure
      if (dateToCheck.getTime() === today.getTime()) {
        return `Aujourd'hui ${hours}:${minutes}`;
      }

      // Si c'est hier
      const yesterday = new Date(today);
      yesterday.setDate(yesterday.getDate() - 1);
      if (dateToCheck.getTime() === yesterday.getTime()) {
        return `Hier ${hours}:${minutes}`;
      }

      // Sinon afficher la date complète
      return `${day}/${month}/${year} ${hours}:${minutes}`;
    } catch (e) {
      console.error('Erreur lors du formatage du timestamp:', e);
      return timestamp;
    }
  }

  /**
   * Extrait un message d'erreur lisible
   */
  private getErrorMessage(error: any): string {
    if (error.status === 401) {
      return 'Vous devez être connecté pour voir vos statistiques';
    } else if (error.status === 403) {
      return 'Vous n\'avez pas les permissions nécessaires';
    } else if (error.status === 404) {
      return 'Aucune statistique trouvée';
    } else if (error.status === 0) {
      return 'Impossible de contacter le serveur';
    } else if (error.error?.error) {
      return error.error.error;
    } else {
      return 'Une erreur est survenue lors du chargement des statistiques';
    }
  }
}
