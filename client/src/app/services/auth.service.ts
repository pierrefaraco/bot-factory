// src/app/services/auth.service.ts
import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { BehaviorSubject, Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { User } from '../models/user.model';
import { JwtService, JwtPayload } from './jwt.service'
import { API_URL} from  '../constants/user-roles.constants'
import { formatNumber } from '@angular/common';
import { CommunicationService } from './communication.service';
@Injectable({
  providedIn: 'root'
})
export class AuthService {
  [x: string]: any;
  // Créé avant le constructeur : getJwtInfoFromStorage() peut y appeler
  // logout(), qui le remet à null.
  private currentJwtSubject = new BehaviorSubject<JwtPayload | null>(null);
  public currentJwt: Observable<JwtPayload | null> = this.currentJwtSubject.asObservable();
  public currentUser$: Observable<JwtPayload | null>;
  private isAuthenticatedSubject = new BehaviorSubject<boolean>(false);
  isAuthenticated$ = this.isAuthenticatedSubject.asObservable();

  // Configuration des headers HTTP
  private httpOptions = {
    headers: new HttpHeaders({
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    }),
    withCredentials: true // Important si vous utilisez des cookies
  };

  constructor(private http: HttpClient, private jwtService: JwtService, private communicationService: CommunicationService) {
    this.currentJwtSubject.next(this.getJwtInfoFromStorage());
  }


  getJwtInfoFromStorage(): JwtPayload | null {
    const token: string | null = localStorage.getItem('token');
    let decodedToken = null;
    
    if (token) {
      decodedToken = this.jwtService.decodeToken(token);
      if (decodedToken && !this.jwtService.isTokenExpired(token)) {
      } else {
        // Token expiré ou invalide, déconnexion
        this.logout();
        return null;
      }
    }
    return decodedToken;
  }

  public get_curent_user_id(): number | null{
    let decodedToken  =  this.getJwtInfoFromStorage()
    if (decodedToken) {
      return Number(decodedToken.sub); // ou decodedToken.user_id selon votre structure de token
    }
    return null;
  }
  
  public get currentjwtValue(): JwtPayload | null {
    return this.currentJwtSubject.value;
  }


  login(email: string, password: string): Observable<any> {
    return this.http.post<any>(
      `${API_URL}/auth/login`,
      { email, password },
      this.httpOptions
    ).pipe(
      map(response => {
        if (response?.token) {
          const decodedToken = this.jwtService.decodeToken(response.token);
          if (decodedToken) {
            localStorage.setItem('token', response.token);
            this.currentJwtSubject.next(decodedToken);
            this.isAuthenticatedSubject.next(true);
          }
        }
        return response;
      })
    );
  }

  // Google OAuth login
  loginWithGoogle(credential: string): Observable<any> {
    return this.http.post<any>(
      `${API_URL}/auth/google`,
      { credential },
      this.httpOptions
    ).pipe(
      map(response => {
        if (response?.token) {
          const decodedToken = this.jwtService.decodeToken(response.token);
          if (decodedToken) {
            localStorage.setItem('token', response.token);
            this.currentJwtSubject.next(decodedToken);
            this.isAuthenticatedSubject.next(true);
          }
        }
        return response;
      })
    );
  }


  // Lien de connexion à usage unique (/auth?token=...), créé par un admin
  // (make magic-link) : le serveur échange le jeton contre le JWT habituel.
  loginWithMagicLink(token: string): Observable<any> {
    return this.http.post<any>(
      `${API_URL}/auth/magic-link`,
      { token },
      this.httpOptions
    ).pipe(
      map(response => {
        if (response?.token) {
          const decodedToken = this.jwtService.decodeToken(response.token);
          if (decodedToken) {
            localStorage.setItem('token', response.token);
            this.currentJwtSubject.next(decodedToken);
            this.isAuthenticatedSubject.next(true);
          }
        }
        return response;
      })
    );
  }


  // Compte de démo partagé (boutons "Try the demo" de la landing page).
  isDemoEnabled(): Observable<boolean> {
    return this.http.get<{ enabled: boolean }>(`${API_URL}/auth/demo`).pipe(
      map(response => response.enabled)
    );
  }

  loginDemo(): Observable<any> {
    return this.http.post<any>(`${API_URL}/auth/demo`, {}, this.httpOptions).pipe(
      map(response => {
        if (response?.token) {
          const decodedToken = this.jwtService.decodeToken(response.token);
          if (decodedToken) {
            localStorage.setItem('token', response.token);
            this.currentJwtSubject.next(decodedToken);
            this.isAuthenticatedSubject.next(true);
          }
        }
        return response;
      })
    );
  }


  logout(): void {
    console.log("logout")
    // Lu avant localStorage.clear() : l'appel au backend en a besoin.
    const token = localStorage.getItem('token');

    // La session locale est fermée tout de suite, sans attendre le backend
    // (AuthGuard lit currentjwtValue).
    localStorage.clear();
    this.currentJwtSubject.next(null);
    this.isAuthenticatedSubject.next(false);
    this.communicationService.resetSelectedBot();

    // Révocation côté serveur (le jti du token passe en liste noire), pour
    // qu'une copie du token ne reste pas utilisable jusqu'à son expiration.
    // Le header est posé ici : jwtInterceptor ne trouve plus le token dans
    // localStorage. Inutile pour un token expiré, que le serveur refuse déjà
    // (et dont le 401 déclencherait une redirection vers /auth).
    if (token && !this.jwtService.isTokenExpired(token)) {
      this.http.post(`${API_URL}/auth/logout`, {}, {
        ...this.httpOptions,
        headers: this.httpOptions.headers.set('Authorization', `Bearer ${token}`),
      }).subscribe({
        // La session locale est déjà fermée, quoi qu'il arrive ici.
        error: () => {},
      });
    }
  }

  

  // Nouvelle méthode pour vérifier si l'utilisateur est authentifié
  isAuthenticated(): boolean {
    const token = localStorage.getItem('token');
    if (!token) return false;
    return !this.jwtService.isTokenExpired(token);
  }

  // Nouvelle méthode pour obtenir le rôle de l'utilisateur
  getUserRole(): string | null {
    const jwtInfo = this.currentjwtValue;
    return jwtInfo?.roles || null;
  }

} 