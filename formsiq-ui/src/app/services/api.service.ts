import { Injectable } from '@angular/core';
import { HttpClient, HttpContext } from '@angular/common/http';
import { Observable } from 'rxjs';
import { timeout } from 'rxjs/operators';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private baseUrl = 'http://localhost:8000/api';
  private defaultTimeout = 120000; // 120 seconds (2 minutes) timeout

  constructor(private http: HttpClient) { }

  /**
   * Extract fields from a transcript by calling the backend API
   * @param transcript The call transcript to process
   * @param model The AI model to use for extraction (gemma or grok)
   * @returns Observable with the structured field data and confidence scores
   */
  extractFields(transcript: string, model: string = 'gemma'): Observable<any> {
    return this.http.post(`${this.baseUrl}/extract-fields`, { transcript, model })
      .pipe(timeout(this.defaultTimeout));
  }

  /**
   * Generate a filled PDF from the extracted field data
   * @param fieldsData The extracted fields data to fill in the PDF form
   * @returns Observable with the PDF file as a Blob
   */
  fillPdf(fieldsData: any): Observable<Blob> {
    return this.http.post(`${this.baseUrl}/fill-pdf`, fieldsData, {
      responseType: 'blob'
    }).pipe(timeout(this.defaultTimeout));
  }

  /**
   * Get information about the PDF form fields (for debugging)
   * @returns Observable with information about the PDF fields
   */
  getPdfFields(): Observable<any> {
    return this.http.get(`${this.baseUrl}/pdf-fields`)
      .pipe(timeout(30000)); // 30 seconds timeout for this simpler request
  }
}
