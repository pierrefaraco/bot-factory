import { Injectable } from "@angular/core";
import { HttpClient, HttpHeaders } from "@angular/common/http";
import { Observable } from "rxjs";
import { Bot } from "../models/bot.model";
import { API_URL, HTTP_OPTIONS } from "../constants/user-roles.constants";
import { ACTIVE_BOT } from "../constants/keys.constants"
import { ComboOptions } from "@app/models/combo-options.model";

@Injectable({
  providedIn: "root",
})
export class BotService {
  private apiUrl = API_URL + "/bot";

  constructor(private http: HttpClient) { }

  createRandomBot(bot: Bot): Observable<Bot> {
    return this.http.post<Bot>(this.apiUrl, bot, HTTP_OPTIONS);
  }

  createBot(): Observable<Bot> {
    return this.http.post<Bot>(this.apiUrl,'', HTTP_OPTIONS);
  }

  getBotById(id: number, view='minimal'): Observable<Bot> {
    return this.http.get<Bot>(`${this.apiUrl}/${id}?view=${view}`);
  }


  getUserBots(): Observable<Bot[]> {
    return this.http.get<Bot[]>(`${this.apiUrl}/self`);
  }

  getAllBots(): Observable<Bot[]> {
    return this.http.get<Bot[]>(`${this.apiUrl}`);
  }

  getOwnedBots(): Observable<Bot[]> {
    return this.http.get<Bot[]>(`${this.apiUrl}/owned`);
  }


  updateBot(bot: Bot): Observable<Bot> {
    return this.http.put<Bot>(`${this.apiUrl}/${bot.id}`, bot, HTTP_OPTIONS);
  }

  deleteBot(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${id}`).pipe();
  }



  get_bot_parameters_description(): Observable<ComboOptions>  {
    return this.http.get<any>(`${this.apiUrl}/parameters-description`);
  }
}
