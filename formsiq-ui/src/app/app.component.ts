import { Component, OnInit, PLATFORM_ID, Inject } from '@angular/core';
import { CommonModule, isPlatformBrowser } from '@angular/common';
import { RouterOutlet } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';

import { TranscriptInputComponent } from './components/transcript-input/transcript-input.component';
import { ResultsDisplayComponent } from './components/results-display/results-display.component';
import { SplashScreenComponent } from './components/splash-screen/splash-screen.component';
import { NoteModalComponent } from './components/note-modal/note-modal.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    CommonModule, 
    RouterOutlet, 
    FormsModule, 
    TranscriptInputComponent,
    ResultsDisplayComponent,
    SplashScreenComponent,
    NoteModalComponent
  ],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss'
})
export class AppComponent implements OnInit {
  title = 'FormsIQ';
  extractedData: any = null;
  isLoading: boolean = true;
  private isBrowser: boolean;
  
  showNoteModal = false;
  noteContent = '';
  
  constructor(
    @Inject(PLATFORM_ID) platformId: Object,
    private http: HttpClient
  ) {
    this.isBrowser = isPlatformBrowser(platformId);
  }

  ngOnInit(): void {
    setTimeout(() => {
      this.isLoading = false;
      // Check if running in browser before using browser-specific APIs
      if (this.isBrowser) {
        // Using requestAnimationFrame to wait for the next repaint after isLoading changes
        window.requestAnimationFrame(() => {
          window.scrollTo(0, 0);
        });
      }
    }, 2500);
  }
  
  // Handle the extraction complete event from the transcript-input component
  onExtractionComplete(data: any): void {
    this.extractedData = data;
  }

  openNoteModal(): void {
    this.http.get('assets/note.md', { responseType: 'text' })
      .subscribe(
        data => {
          this.noteContent = data;
          this.showNoteModal = true;
        },
        error => {
          console.error('Error fetching note.md:', error);
          this.noteContent = 'Could not load the note at this time.';
          this.showNoteModal = true;
        }
      );
  }

  closeNoteModal(): void {
    this.showNoteModal = false;
  }
}
