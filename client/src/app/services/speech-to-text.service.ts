import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, from, throwError } from 'rxjs';
import { catchError, map } from 'rxjs/operators';

@Injectable({
  providedIn: 'root'
})
export class SpeechToTextService {
  private readonly apiKey = 'sk_45fcdf8d9b9891e8e7f6363d6dc1a9d2be4a7800f4ec7907';
  private readonly baseUrl = 'https://api.elevenlabs.io/v1';

  constructor(private http: HttpClient) {}

  transcribeAudio(audioFile: File): Observable<string> {
    const formData = new FormData();
    formData.append('audio', audioFile);

    const headers = new HttpHeaders({
      'xi-api-key': this.apiKey
    });

    return this.http.post<{ text: string }>(`${this.baseUrl}/speech-to-text`, formData, {
      headers
    }).pipe(
      map(response => response.text),
      catchError(error => {
        console.error('Error transcribing audio:', error);
        return throwError(() => error);
      })
    );
  }

  transcribeAudioBlob(audioBlob: Blob): Observable<string> {
    const audioFile = new File([audioBlob], 'audio.wav', { type: 'audio/wav' });
    return this.transcribeAudio(audioFile);
  }

  startRecording(): Promise<MediaRecorder> {
    return navigator.mediaDevices.getUserMedia({ audio: true })
      .then(stream => {
        const mediaRecorder = new MediaRecorder(stream);
        return mediaRecorder;
      })
      .catch(error => {
        console.error('Error accessing microphone:', error);
        throw error;
      });
  }

  recordAudio(durationMs: number = 5000): Observable<Blob> {
    return from(
      this.startRecording().then(mediaRecorder => {
        return new Promise<Blob>((resolve, reject) => {
          const chunks: Blob[] = [];

          mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
              chunks.push(event.data);
            }
          };

          mediaRecorder.onstop = () => {
            const audioBlob = new Blob(chunks, { type: 'audio/wav' });
            resolve(audioBlob);
          };

          mediaRecorder.onerror = (event) => {
            reject(event);
          };

          mediaRecorder.start();
          
          setTimeout(() => {
            if (mediaRecorder.state === 'recording') {
              mediaRecorder.stop();
              mediaRecorder.stream.getTracks().forEach(track => track.stop());
            }
          }, durationMs);
        });
      })
    );
  }

  recordAndTranscribe(durationMs: number = 5000): Observable<string> {
    return new Observable<string>(observer => {
      this.recordAudio(durationMs).subscribe({
        next: (audioBlob) => {
          this.transcribeAudioBlob(audioBlob).subscribe({
            next: (text) => {
              observer.next(text);
              observer.complete();
            },
            error: (error) => observer.error(error)
          });
        },
        error: (error) => observer.error(error)
      });
    });
  }
}