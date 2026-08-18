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
  private currentJwtSubject: BehaviorSubject<JwtPayload | null>;
  public currentJwt: Observable<JwtPayload | null>;
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
    let jwt = this.getJwtInfoFromStorage()
    this.currentJwtSubject = new BehaviorSubject<JwtPayload | null>(jwt);
    this.currentJwt = this.currentJwtSubject.asObservable();
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


  logout() {
    // Optionnel: Appel au backend pour invalider le token
    console.log("logout")
    localStorage.clear();
    this.isAuthenticatedSubject.next(false);
    this.communicationService.resetSelectedBot();
    return this.http.post(`${API_URL}/auth/logout`, {}, this.httpOptions)
      .pipe(
        map(() => {
          this.currentJwtSubject.next(null);
        })
      );
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