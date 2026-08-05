// chapter.service.ts
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { API_URL, HTTP_OPTIONS} from  '../constants/user-roles.constants'
@Injectable({
  providedIn: 'root'
})
export class KnowledgeService {
  private apiUrl = API_URL + '/knowledge';

  constructor(private http: HttpClient) {}

  getKnowledges(bot_id): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/${bot_id}`);
  }

  getKnowledge(bot_id,chapter_id: number): Observable<any> {
    return this.http.get(`${this.apiUrl}/${bot_id}/${chapter_id}`);
  }

  loadTemplate(bot_id): Observable<any> {
    return this.http.get(`${this.apiUrl}/load_template/${bot_id}/french_template`);
  }

  createKnowledge(bot_id,formData: any): Observable<any> {
    return this.http.post(`${this.apiUrl}/save/${bot_id}`, formData);
  }

  createEmptyKnowledge(bot_id,knowledge_dad_id: any): Observable<any> {
    return this.http.post(`${this.apiUrl}/save/${bot_id}/${knowledge_dad_id}`,{});
  }


  updateKnowledge(bot_id,formData: any): Observable<any> {
    return this.http.put(`${this.apiUrl}/save/${bot_id}`,  formData);
  }

  deleteKnowledge(chapter_id: number): Observable<any> {
    return this.http.delete(`${this.apiUrl}/${chapter_id}`);
  }

  deleteAllKnowledges(): Observable<any> {
    return this.http.delete(`${this.apiUrl}/all`);
  }

  saveKnowledges(bot_id,chapters: any[]): Observable<any> {
    return this.http.post(`${this.apiUrl}/save_chapters/${bot_id}`, { importedChapters: chapters });
  }

  transmitToAlfred(bot_id): Observable<any> {
    return this.http.post(`${API_URL}/rag/transmit_to_alfred/${bot_id}`,HTTP_OPTIONS);
  }
}