// src/app/services/jwt.service.ts
import { Injectable } from '@angular/core';
import { jwtDecode } from 'jwt-decode'; 

export interface JwtPayload {
  iat: number;
  jti: string;
  type: string;
  sub: string;
  nbf: number;
  exp: number;
  roles: string;
  mail: string
}

@Injectable({
  providedIn: 'root'
})
export class JwtService {
  
  constructor( ) { }

  getJwtToken(): string | null {
    const token:  string | null = localStorage.getItem('token')
    return token
  }

  _decodeToken(): JwtPayload | null {
    try {
      const token =  this.getJwtToken()
      if(token){
        return this.decodeToken(token)
      }
      else {
        return null
      }
    }
    catch{
      return null
    }
  }

  decodeToken(token:string): JwtPayload | null {
    try {
      if(token){
        return jwtDecode<JwtPayload>(token);
      }
      else {
        return null
      }
    }
    catch{
      return null
    }
  }

  getTokenExpirationDate(token:string): Date | null {
    const decoded = this.decodeToken(token);
    
    if (!decoded || !decoded.exp) {
      return null;
    }

    const date = new Date(0);
    date.setUTCSeconds(decoded.exp);
    return date;
  }

  isTokenExpired(token: string): boolean {
    const date = this.getTokenExpirationDate(token);
    
    if (!date) {
      return true;
    }
    
    return !(date.valueOf() > new Date().valueOf());
  }

  hasRole(token: string, role: string): boolean {
    const decoded = this.decodeToken(token);
    return decoded?.type?.includes(role) || false;
  }

  getUserEmail(token: string): string | null {
    const decoded = this.decodeToken(token);
    return decoded?.sub || null;
  }

  getUserId(token: string): string | null {
    const decoded = this.decodeToken(token);
    return decoded?.sub || null;
  }

  getUserRoles(token: string): string | null {
    const decoded = this.decodeToken(token);
    return decoded?.sub || null;
  }
}