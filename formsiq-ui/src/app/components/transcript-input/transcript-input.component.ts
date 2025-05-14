import { Component, EventEmitter, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';

@Component({
  selector: 'app-transcript-input',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './transcript-input.component.html',
  styleUrl: './transcript-input.component.scss'
})
export class TranscriptInputComponent {
  transcriptText: string = '';
  isLoading: boolean = false;
  errorMessage: string | null = null;
  selectedFile: File | null = null;
  selectedModel: string = 'gemma'; // Default to Gemma 3

  @Output() extractionComplete = new EventEmitter<any>();

  constructor(private apiService: ApiService) { }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.selectedFile = input.files[0];
      this.errorMessage = null;
      
      // If it's a text file, attempt to read its contents into the textarea
      if (this.selectedFile.type === 'text/plain') {
        this.readTextFile(this.selectedFile);
      }
    }
  }

  readTextFile(file: File): void {
    const reader = new FileReader();
    reader.onload = (e) => {
      if (e.target && typeof e.target.result === 'string') {
        this.transcriptText = e.target.result;
        // After reading, clear the selectedFile so the textarea becomes editable
        this.selectedFile = null;
      }
    };
    
    reader.onerror = () => {
      this.errorMessage = "Error reading the file. Please try again or paste the text manually.";
      this.selectedFile = null;
    };
    
    reader.readAsText(file);
  }

  clearSelectedFile(): void {
    this.selectedFile = null;
    this.errorMessage = null;
  }

  onSubmit(): void {
    // Don't process if no transcript is available
    if (!this.transcriptText.trim() && !this.selectedFile) {
      this.errorMessage = 'Please enter a transcript or upload a file before submitting.';
      return;
    }

    this.isLoading = true;
    this.errorMessage = null;

    // If we have a file selected and it's not a text file, we need to handle it
    if (this.selectedFile && this.selectedFile.type !== 'text/plain') {
      this.errorMessage = "Only text (.txt) files can be processed directly. For other formats, please copy and paste the content.";
      this.isLoading = false;
      return;
    }

    // Call the API with the selected model
    this.apiService.extractFields(this.transcriptText, this.selectedModel).subscribe({
      next: (response) => {
        this.isLoading = false;
        // Emit the extracted fields to the parent component
        this.extractionComplete.emit(response);
      },
      error: (error) => {
        this.isLoading = false;
        this.errorMessage = error.error?.details || 'Error processing transcript. Please try again.';
        console.error('Error extracting fields:', error);
      }
    });
  }

  clearTranscript(): void {
    this.transcriptText = '';
    this.selectedFile = null;
    this.errorMessage = null;
  }
}
