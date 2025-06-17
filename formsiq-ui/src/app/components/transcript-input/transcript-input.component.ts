import { Component, EventEmitter, Output, ElementRef, ViewChild, PLATFORM_ID, Inject } from '@angular/core';
import { CommonModule, isPlatformBrowser } from '@angular/common';
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
  acknowledgedFileName: string | null = null;
  acknowledgedFileSize: string | null = null;
  availableModels: string[] = [];
  selectedModel: string = 'grok'; // Default to Grok (available in production)
  private isBrowser: boolean;
  
  @ViewChild('transcriptFileInput') transcriptFileInput!: ElementRef<HTMLInputElement>;
  
  @Output() extractionComplete = new EventEmitter<any>();

  constructor(private apiService: ApiService, @Inject(PLATFORM_ID) platformId: Object) {
    this.isBrowser = isPlatformBrowser(platformId);
    this.availableModels = this.apiService.getAvailableModels();
    // Set default model to first available model
    if (this.availableModels.length > 0) {
      this.selectedModel = this.availableModels[0];
    }
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      const file = input.files[0];
      this.selectedFile = file;
      this.acknowledgedFileName = file.name;
      this.acknowledgedFileSize = '(' + (file.size / 1024).toFixed(1) + ' KB)';
      this.errorMessage = null;
      
      // If it's a text file, attempt to read its contents into the textarea
      if (this.selectedFile.type === 'text/plain') {
        this.readTextFile(this.selectedFile);
      }
    } else {
      this.clearAcknowledgedFile();
    }
  }

  readTextFile(file: File): void {
    if (!this.isBrowser) return;
    
    const reader = new FileReader();
    reader.onload = (e) => {
      if (e.target && typeof e.target.result === 'string') {
        this.transcriptText = e.target.result;
        // After reading, clear the selectedFile so the textarea becomes editable,
        // but keep acknowledgedFileName
        this.selectedFile = null; 
      }
    };
    
    reader.onerror = () => {
      this.errorMessage = "Error reading the file. Please try again or paste the text manually.";
      this.selectedFile = null;
      // Keep acknowledgedFileName so user knows which file failed
    };
    
    reader.readAsText(file);
  }

  clearAcknowledgedFile(): void {
    this.selectedFile = null;
    this.acknowledgedFileName = null;
    this.acknowledgedFileSize = null;
    this.errorMessage = null;
    // Clear the file input element using ViewChild reference instead of direct DOM access
    if (this.isBrowser && this.transcriptFileInput?.nativeElement) {
      this.transcriptFileInput.nativeElement.value = '';
    }
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
    this.acknowledgedFileName = null;
    this.acknowledgedFileSize = null;
    this.errorMessage = null;
    // Clear the file input element using ViewChild reference
    if (this.isBrowser && this.transcriptFileInput?.nativeElement) {
      this.transcriptFileInput.nativeElement.value = '';
    }
  }
}
