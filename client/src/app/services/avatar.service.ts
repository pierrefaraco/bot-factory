import { Injectable } from "@angular/core";
import { HttpClient, HttpHeaders } from "@angular/common/http";
import { Observable } from "rxjs";
import { Bot } from "../models/bot.model";
import { API_URL, HTTP_OPTIONS } from "../constants/user-roles.constants";
import { Avatar } from "@app/models/avatar.model";

@Injectable({
  providedIn: "root",
})
export class AvatarService {
    private apiUrl = API_URL + "/avatar";

    constructor(private http: HttpClient) {}


  createAvatar(avatar: Avatar): Observable<Avatar> {
    return this.http.post<Avatar>(this.apiUrl, avatar, HTTP_OPTIONS);
  }


  createRandomAvatar(bot_id: number): Observable<Avatar> {
    return this.http.post<Avatar>(`${this.apiUrl}/random`, {bot_id:bot_id}, HTTP_OPTIONS);
  }


  patchAvatar(data): Observable<any> {
    return this.http.patch<Avatar>(this.apiUrl, data, HTTP_OPTIONS);
  }

   updateAvatar(avatar: Avatar): Observable<Avatar> {
    return this.http.put<Avatar>(this.apiUrl, avatar, HTTP_OPTIONS);
  }


  getAvatarByBotID(bot_id: number): Observable<Avatar> {

    return this.http.get<Avatar>(`${this.apiUrl}/${bot_id}`);
  }

  deleteAvatarByBotID(bot_id: number): Observable<Avatar> {
    return this.http.delete<Avatar>(`${this.apiUrl}/${bot_id}`);
  }
}

