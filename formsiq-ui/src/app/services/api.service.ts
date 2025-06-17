import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { timeout } from 'rxjs/operators';
import { environment } from '../../environments/environment';

// Field value can be string, number, boolean, or the special unmapped marker
export type FieldValue = string | number | boolean | null | undefined;
export const FIELD_NOT_MAPPED_VALUE = "__FIELD_NOT_MAPPED__";

export interface MappedPdfField {
  name: string; // Usually the /T value (descriptive name)
  key: string;  // The internal PDF field key
  value: FieldValue | typeof FIELD_NOT_MAPPED_VALUE; // The value from AI, or the marker
  field_type: string; // e.g., /Tx, /Btn
  confidence_score?: number; // Confidence score from AI (0-1 range)
}

export interface CheckboxField {
  name: string;
  key: string;
  checked: boolean; // Reflects if AI data intended to check it
  on_value_in_pdf: string; // The PDF's defined 'ON' value (e.g., /Yes)
}

export interface RadioOption {
  name: string; // Descriptive name of the option (kid /T)
  value: string; // Export value of the option (e.g., /VA, /FixedRate)
}

export interface RadioGroup {
  name: string; // Descriptive name of the radio group (/T of parent field)
  key: string; // PDF key of the radio group parent field
  options: RadioOption[];
  selected_value: string | null; // The export value of the AI-selected option, or null if none/unmapped
}

export interface PDFResult {
  success?: boolean; 
  pdf_generation_status: 'success' | 'failed' | 'deferred' | 'pending';
  message: string;
  pdf_url: string | null; 
  filled_pdf_path_ref?: string | null; 
  mapped_field_count?: number; 
  all_mapped_fields: MappedPdfField[]; // Changed from any[]
  checkbox_fields: CheckboxField[]; // Represents all checkboxes
  radio_groups: RadioGroup[];       // Represents all radio groups
}

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private baseUrl = environment.apiUrl;
  private defaultTimeout = 120000; // 120 seconds (2 minutes) timeout

  constructor(private http: HttpClient) { }

  /**
   * Get available AI models for the current environment
   * @returns Array of available model names
   */
  getAvailableModels(): string[] {
    return environment.availableModels || ['grok'];
  }

  /**
   * Extract fields from a transcript by calling the backend API
   * @param transcript The call transcript to process
   * @param model The AI model to use for extraction (gemma or grok)
   * @returns Observable with the structured field data and confidence scores
   */
  extractFields(transcript: string, model: string = 'gemma'): Observable<any> {
    return this.http.post(`${this.baseUrl}/extract-fields/`, { transcript, model })
      .pipe(timeout(this.defaultTimeout));
  }

  /**
   * Generate a filled PDF from the extracted field data, or just process for display.
   * @param fieldsData The extracted fields data.
   * @param performFill Whether to actually generate the PDF file (true) or just get mapped data (false).
   * @returns Observable with the PDF processing results.
   */
  fillPdf(fieldsData: { fields: any[], perform_fill?: boolean }): Observable<PDFResult> {
    const payload = {
      fields: fieldsData.fields,
      perform_fill: fieldsData.perform_fill === undefined ? true : fieldsData.perform_fill
    };
    return this.http.post<PDFResult>(`${this.baseUrl}/fill-pdf/`, payload)
      .pipe(timeout(this.defaultTimeout));
  }

  /**
   * Get information about the PDF form fields (for debugging)
   * @returns Observable with information about the PDF fields
   */
  getPdfFields(): Observable<any> {
    return this.http.get(`${this.baseUrl}/pdf-fields/`)
      .pipe(timeout(30000)); // 30 seconds timeout for this simpler request
  }
}
