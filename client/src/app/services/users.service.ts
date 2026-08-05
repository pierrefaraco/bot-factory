import { HttpHeaders } from '@angular/common/http';
import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { User } from '@app/models/user.model';
import { Observable } from 'rxjs';

import { API_URL,HTTP_OPTIONS } from '@app/constants/user-roles.constants';
import { Bot } from '@app/models/bot.model';

interface ProfileUpdateData {
  user_name: string;
  email: string;
  current_password: string;
  new_password?: string;
}

@Injectable({
  providedIn: 'root'
})
export class UsersService {

  constructor(private http: HttpClient) { }


  getCurrentUser(): Observable<User> {
    return this.http.get<User>(`${API_URL}/users/self`);
  }

  registerUser(user: any): Observable<any> {
    return this.http.post<any>(
      `${API_URL}/users`,
      user,
      HTTP_OPTIONS
    );
  }

  registerGuest(user: User): Observable<any> {
    return this.http.post(`${API_URL}/users/guest`, user, HTTP_OPTIONS);
  }

  getAllGuests(): Observable<User[]> {
    return this.http.get<User[]>(`${API_URL}/users/guests`);
  }

  getUsers(): Observable<User[]> {
    return this.http.get<User[]>(`${API_URL}/users`);
  }

  activateGuest(guestId: number): Observable<User[]> {
    return this.http.put<User[]>(`${API_URL}/users/${guestId}/activate/guest`, HTTP_OPTIONS);
  }

  deactivateGuest(guestId: number): Observable<User[]> {
    return this.http.put<User[]>(`${API_URL}/users/${guestId}/deactivate/guest`, HTTP_OPTIONS);
  }
  
  patchSelectBotID(selected_bot_id: number): Observable<any> {
    let value_to_patch = {selected_bot_id:selected_bot_id }
    return this.http.patch(`${API_URL}/users/self`,value_to_patch, HTTP_OPTIONS);
  }

  assignBotsToGuest(user_id: number, bot_ids: number[]): Observable<any> {
    let value_to_patch = {assigned_bot_ids: bot_ids};
    return this.http.patch(`${API_URL}/users/guest/${user_id}`, value_to_patch, HTTP_OPTIONS);
  }

  getSelectedBot(): Observable<any> {
    return this.http.get<Bot>(`${API_URL}/users/selected_bot/self`, HTTP_OPTIONS);
  }

  updateUser(user: User): Observable<any> {


    return this.http.put(
      `${API_URL}/users/${user.id}`,
      user,
     HTTP_OPTIONS
    );
  }

  updateGuest(userId: number, user: any): Observable<any> {
 

    return this.http.put(
      `${API_URL}/users/guest/${userId}`,
      user,
     HTTP_OPTIONS
    );
  }


  deleteGuest(userId: number): Observable<any> {

    return this.http.delete(
      `${API_URL}/users/guest/${userId}`,
      HTTP_OPTIONS
    );
  }


  updateProfile(data: ProfileUpdateData): Observable<User> {
    return this.http.put<User>(`${API_URL}/users/self`, data);
  }

  updateGuestPassword(userId: number, passwordData: { old_password: string; new_password: string;  }): Observable<any> {
    console.log("updateGuestPassword",passwordData)
    return this.http.put(
      `${API_URL}/users/password/guest/${userId}`,
      passwordData,
      HTTP_OPTIONS
    );
  }

  updateProfilePassword(passwordData: { old_password: string; new_password: string; }): Observable<any> {
      console.log("updateProfilePassword",passwordData.old_password,passwordData.new_password)
    return this.http.put(
      `${API_URL}/users/password/self`,
      passwordData,
      HTTP_OPTIONS
    );

  }
}
