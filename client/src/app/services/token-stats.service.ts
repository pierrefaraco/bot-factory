import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  UserTokenStats,
  TokenUsageHistory,
  BotTokenStats,
  TotalTokens,
  AllUsersStats,
  UserTokenStatsLast24h
} from '../models/token-stats.model';
import { API_URL } from '../constants/user-roles.constants';

@Injectable({
  providedIn: 'root'
})
export class TokenStatsService {
  private baseUrl = `${API_URL}/token-stats`;

  constructor(private http: HttpClient) {}

  // ========== Statistiques personnelles ==========

  /**
   * Récupère les statistiques de tokens de l'utilisateur connecté
   */
  getMyStats(): Observable<UserTokenStats> {
    return this.http.get<UserTokenStats>(`${this.baseUrl}/self`);
  }

  /**
   * Récupère uniquement le total de tokens consommés
   */
  getMyTotal(): Observable<TotalTokens> {
    return this.http.get<TotalTokens>(`${this.baseUrl}/total/self`);
  }

  /**
   * Récupère l'historique détaillé des requêtes
   * @param limit Nombre d'enregistrements (1-1000, défaut: 100)
   */
  getMyHistory(limit: number = 100, last24h: boolean = false): Observable<TokenUsageHistory> {
    return this.http.get<TokenUsageHistory>(
      `${this.baseUrl}/history/self?limit=${limit}&last24h=${last24h}`
    );
  }

  /**
   * Récupère le total de tokens consommés dans les dernières 24 heures
   */
  getMyLast24h(): Observable<TotalTokens> {
    return this.http.get<TotalTokens>(`${this.baseUrl}/last-24h/self`);
  }

  /**
   * Récupère les statistiques détaillées des 24 dernières heures
   */
  getMyStatsLast24h(): Observable<UserTokenStatsLast24h> {
    return this.http.get<UserTokenStatsLast24h>(`${this.baseUrl}/stats-24h/self`);
  }

  // ========== Statistiques des guests ==========

  /**
   * Récupère les statistiques d'un utilisateur guest
   * @param guestId ID de l'utilisateur guest
   */
  getGuestStats(guestId: number): Observable<UserTokenStats> {
    return this.http.get<UserTokenStats>(`${this.baseUrl}/guest/${guestId}`);
  }

  /**
   * Total de tokens d'un guest
   * @param guestId ID de l'utilisateur guest
   */
  getGuestTotal(guestId: number): Observable<TotalTokens> {
    return this.http.get<TotalTokens>(`${this.baseUrl}/total/guest/${guestId}`);
  }

  /**
   * Historique d'un guest
   * @param guestId ID de l'utilisateur guest
   * @param limit Nombre d'enregistrements (1-1000, défaut: 100)
   */
  getGuestHistory(guestId: number, limit: number = 100): Observable<TokenUsageHistory> {
    return this.http.get<TokenUsageHistory>(
      `${this.baseUrl}/history/guest/${guestId}?limit=${limit}`
    );
  }

  // ========== Statistiques utilisateur (Admin) ==========

  /**
   * Statistiques d'un utilisateur spécifique (Admin uniquement)
   * @param userId ID de l'utilisateur
   */
  getUserStats(userId: number): Observable<UserTokenStats> {
    return this.http.get<UserTokenStats>(`${this.baseUrl}/user/${userId}`);
  }

  /**
   * Total de tokens d'un utilisateur (Admin uniquement)
   * @param userId ID de l'utilisateur
   */
  getUserTotal(userId: number): Observable<TotalTokens> {
    return this.http.get<TotalTokens>(`${this.baseUrl}/total/user/${userId}`);
  }

  /**
   * Historique d'un utilisateur (Admin uniquement)
   * @param userId ID de l'utilisateur
   * @param limit Nombre d'enregistrements (1-1000, défaut: 100)
   */
  getUserHistory(userId: number, limit: number = 100): Observable<TokenUsageHistory> {
    return this.http.get<TokenUsageHistory>(
      `${this.baseUrl}/history/user/${userId}?limit=${limit}`
    );
  }

  // ========== Statistiques par bot ==========

  /**
   * Statistiques de consommation d'un bot
   * @param botId ID du bot
   */
  getBotStats(botId: number): Observable<BotTokenStats> {
    return this.http.get<BotTokenStats>(`${this.baseUrl}/bot/${botId}`);
  }

  // ========== Statistiques globales (Admin) ==========

  /**
   * Statistiques de tous les utilisateurs (Admin uniquement)
   */
  getAllUsersStats(): Observable<AllUsersStats> {
    return this.http.get<AllUsersStats>(`${this.baseUrl}/all-users`);
  }
}
