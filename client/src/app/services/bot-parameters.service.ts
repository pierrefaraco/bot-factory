import { Injectable } from "@angular/core";
import { HttpClient, HttpHeaders } from "@angular/common/http";
import { Observable } from "rxjs";
import { API_URL, HTTP_OPTIONS } from "../constants/user-roles.constants";
import { BotParameters } from "@app/models/bot-parameters.model";

@Injectable({
  providedIn: "root",
})
export class BotParametersService {
  private apiUrl = API_URL + "/bot-parameters";

  constructor(private http: HttpClient) { }

  createBotParameters(botParameters: BotParameters): Observable<BotParameters> {
    return this.http.post<BotParameters>(this.apiUrl, botParameters, HTTP_OPTIONS);
  }

  getBotParametersByBotId(botId: number): Observable<BotParameters> {
    return this.http.get<BotParameters>(`${this.apiUrl}/${botId}`);
  }


  updateBotParameters(botParameters: BotParameters): Observable<BotParameters> {
    return this.http.put<BotParameters>(`${this.apiUrl}`, botParameters, HTTP_OPTIONS);
  }

  deleteBotParameters(botId: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${botId}`);
  }

  patchBotParameters(id: number, data: { [key: string]: any }): Observable<BotParameters> {
    return this.http.patch<BotParameters>(`${this.apiUrl}/${id}`,data,HTTP_OPTIONS);
  }

}
