import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { HttpClientModule } from '@angular/common/http';

import { TranscriptInputComponent } from './components/transcript-input/transcript-input.component';
import { ResultsDisplayComponent } from './components/results-display/results-display.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    CommonModule, 
    RouterOutlet, 
    FormsModule, 
    HttpClientModule,
    TranscriptInputComponent,
    ResultsDisplayComponent
  ],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss'
})
export class AppComponent {
  title = 'FormsIQ';
  extractedData: any = null;
  
  // Handle the extraction complete event from the transcript-input component
  onExtractionComplete(data: any): void {
    this.extractedData = data;
  }
}
