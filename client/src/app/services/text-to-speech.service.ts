import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';
import { catchError, map } from 'rxjs/operators';

export interface Voice {
  voice_id: string;
  name: string;
  category: string;
  description?: string;
}

export interface VoiceSettings {
  stability: number;
  similarity_boost: number;
  style?: number;
  use_speaker_boost?: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class TextToSpeechService {
  private readonly apiKey = 'sk_e284b13042f4dc52272958d6c3ca025905053aaf2dc3bc87';
  private readonly baseUrl = 'https://api.elevenlabs.io/v1';

  constructor(private http: HttpClient) {}

  private getHeaders(): HttpHeaders {
    return new HttpHeaders({
      'xi-api-key': this.apiKey,
      'Content-Type': 'application/json'
    });
  }

  getVoices(): Observable<Voice[]> {
    return this.http.get<{ voices: Voice[] }>(`${this.baseUrl}/voices`, {
      headers: this.getHeaders()
    }).pipe(
      map(response => response.voices),
      catchError(error => {
        console.error('Error fetching voices:', error);
        throw error;
      })
    );
  }

  generateSpeech(
    text: string, 
    voiceId: string = 'pNInz6obpgDQGcFmaJgB', // Default voice ID
    voiceSettings: VoiceSettings = { stability: 0.5, similarity_boost: 0.5 }
  ): Observable<Blob> {
    const body = {
      text,
      voice_settings: voiceSettings
    };

    return this.http.post(`${this.baseUrl}/text-to-speech/${voiceId}`, body, {
      headers: this.getHeaders(),
      responseType: 'blob'
    }).pipe(
      catchError(error => {
        console.error('Error generating speech:', error);
        throw error;
      })
    );
  }

  playAudio(audioBlob: Blob): void {
    const audioUrl = URL.createObjectURL(audioBlob);
    const audio = new Audio(audioUrl);
    
    audio.onended = () => {
      URL.revokeObjectURL(audioUrl);
    };
    
    audio.play().catch(error => {
      console.error('Error playing audio:', error);
      URL.revokeObjectURL(audioUrl);
    });
  }

  downloadAudio(audioBlob: Blob, filename: string = 'speech.mp3'): void {
    const url = URL.createObjectURL(audioBlob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  textToSpeechAndPlay(
    text: string, 
    voiceId?: string, 
    voiceSettings?: VoiceSettings
  ): Observable<void> {
    return new Observable<void>(observer => {
      this.generateSpeech(text, voiceId, voiceSettings).subscribe({
        next: (audioBlob) => {
          this.playAudio(audioBlob);
          observer.next();
          observer.complete();
        },
        error: (error) => observer.error(error)
      });
    });
  }
}