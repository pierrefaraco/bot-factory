// chat.service.ts
import { Injectable, ChangeDetectorRef } from '@angular/core';
import { HttpClient, HttpResponse } from '@angular/common/http';
import { Observable, concatMap } from 'rxjs';
import { EventSourcePolyfill } from 'event-source-polyfill'
import { JwtService } from './jwt.service';
import { inject } from '@angular/core';
import { API_URL, HTTP_OPTIONS } from '@app/constants/user-roles.constants';
import { Message } from '@app/models/message.model';
export interface ChatServiceUser {
  update(): void;
  complete(): void;
}

@Injectable({
  providedIn: 'root'
})
export class ChatService {
  constructor(private http: HttpClient) { }
  private apiUrl = API_URL + '/rag'
  private response: string = ''
  private jwtService = inject(JwtService)

  get_response(): string {
    const _response = this.response + '';
    console.log('chat ' + _response)
    this.response = ''
    return _response
  }
  getMessageHistory(botId): Observable<HttpResponse<Message[]>> {
    return this.http.get<Message[]>(`${API_URL}/rag/${botId}`, { ...HTTP_OPTIONS, observe: 'response' });
  }


  deleteMessageHistory(botId): Observable<HttpResponse<any>> {
    return this.http.delete<any>(`${API_URL}/rag/${botId}`, { ...HTTP_OPTIONS, observe: 'response' });
  }


  chat(question: string): Observable<any> {
    console.log('chat')
    return this.http.get(`${this.apiUrl}${question}`)
  }
  
  trigfirstmessage(bot_id: number): Observable<any> {
    console.log('trigfirstmessage')

    return new Observable(observer => {
      const options = {
        headers: {
          Authorization: `Bearer ${this.jwtService.getJwtToken()}`
        }
      }
      const eventSource = new EventSourcePolyfill(`${this.apiUrl}/trigfirstmessage?bot_id=${bot_id}`, options);

      eventSource.onmessage = (event) => {
        try {
          if (event.data === '[DONE]') {
            eventSource.close();
            observer.complete();
            return;
          }
          const data = JSON.parse(event.data);
          observer.next(data.answer);
        } catch (error) {
          observer.error(error);
        }
      };

      eventSource.onerror = (error: any) => {
        console.log('eventSource.onerror', error)
        eventSource.close();
        // Enrichir l'erreur avec le statut HTTP si disponible
        const enrichedError = {
          ...error,
          status: error.status || (error.target && error.target.status) || 0,
          message: error.message || 'Connection error'
        };
        observer.error(enrichedError);
      };

      // Nettoyage quand l'observable est unsubscribed
      return () => {
        eventSource.close();
      };
    });

  }


  chatStream(question: string, bot_id: number): Observable<any> {
    console.log('chatStream')

    return new Observable(observer => {
      const options = {
        headers: {
          Authorization: `Bearer ${this.jwtService.getJwtToken()}`
        }
      }
      const eventSource = new EventSourcePolyfill(`${this.apiUrl}/streamchat?question=${question}&bot_id=${bot_id}`, options);

      eventSource.onmessage = (event) => {
        try {
          if (event.data === '[DONE]') {
            eventSource.close();
            observer.complete();
            return;
          }
          const data = JSON.parse(event.data);
          observer.next(data.answer);
        } catch (error) {
          observer.error(error);
        }
      };

      eventSource.onerror = (error: any) => {
        console.log('eventSource.onerror', error)
        eventSource.close();
        // Enrichir l'erreur avec le statut HTTP si disponible
        const enrichedError = {
          ...error,
          status: error.status || (error.target && error.target.status) || 0,
          message: error.message || 'Connection error'
        };
        observer.error(enrichedError);
      };

      // Nettoyage quand l'observable est unsubscribed
      return () => {
        eventSource.close();
      };
    });
  }

  concatenateChatStream(questions: string[], bot_id: number, chatServiceUser: ChatServiceUser): Observable<string> {
    console.log("concatenateChatStream" + questions)
    return new Observable(observer => {
      this.response = '';

      const subscription = this.chatStream(questions.join(' '), bot_id)
        .pipe(
          concatMap(response => {
            this.response += response;
            return [this.response];
          })
        )
        .subscribe({
          next: (value) => { observer.next(value), chatServiceUser.update() },
          error: (err) => { console.log(err); this.response = "error " + err.status; chatServiceUser.complete() },
          complete: () => { observer.complete(), chatServiceUser.complete() }
        });

      return () => {
        subscription.unsubscribe();
      };
    });
  }

  concatenateFirstMessageStream(bot_id: number, chatServiceUser: ChatServiceUser): Observable<string> {
    return new Observable(observer => {
      this.response = '';

      const subscription = this.trigfirstmessage(bot_id)
        .pipe(
          concatMap(response => {
            this.response += response;
            return [this.response];
          })
        )
        .subscribe({
          next: (value) => { observer.next(value), chatServiceUser.update() },
          error: (err) => { console.log(err); this.response = "error " + err.status; chatServiceUser.complete() },
          complete: () => { observer.complete(), chatServiceUser.complete() }
        });

      return () => {
        subscription.unsubscribe();
      };
    });
  }
}

