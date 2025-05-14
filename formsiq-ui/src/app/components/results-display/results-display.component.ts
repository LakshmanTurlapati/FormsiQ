import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../services/api.service';

@Component({
  selector: 'app-results-display',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './results-display.component.html',
  styleUrl: './results-display.component.scss'
})
export class ResultsDisplayComponent {
  @Input() extractedData: any = null;
  
  isGeneratingPdf: boolean = false;
  pdfError: string | null = null;
  
  constructor(private apiService: ApiService) { }
  
  // Get CSS class based on confidence score
  getConfidenceClass(score: number): string {
    if (score >= 0.8) return 'high-confidence';
    if (score >= 0.5) return 'medium-confidence';
    return 'low-confidence';
  }
  
  // Generate PDF from the extracted fields
  generatePdf(): void {
    this.isGeneratingPdf = true;
    this.pdfError = null;
    
    this.apiService.fillPdf(this.extractedData).subscribe({
      next: (blob) => {
        this.isGeneratingPdf = false;
        // Create a URL for the blob
        const url = window.URL.createObjectURL(blob);
        
        // Create a link element and trigger download
        const a = document.createElement('a');
        a.href = url;
        a.download = 'filled_loan_application.pdf';
        document.body.appendChild(a);
        a.click();
        
        // Cleanup
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      },
      error: (error) => {
        this.isGeneratingPdf = false;
        this.pdfError = 'Error generating PDF. Please try again.';
        console.error('Error generating PDF:', error);
      }
    });
  }
}
