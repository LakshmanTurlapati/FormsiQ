import { Component, Input, OnChanges, SimpleChanges, PLATFORM_ID, Inject } from '@angular/core';
import { CommonModule, isPlatformBrowser } from '@angular/common';
import { 
  ApiService, 
  PDFResult, 
  CheckboxField, 
  RadioGroup, 
  MappedPdfField, 
  FIELD_NOT_MAPPED_VALUE 
} from '../../services/api.service';

@Component({
  selector: 'app-results-display',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './results-display.component.html',
  styleUrl: './results-display.component.scss'
})
export class ResultsDisplayComponent implements OnChanges {
  @Input() extractedData: any = null; 
  
  isProcessingFields: boolean = false; 
  pdfGenerationInProgress: boolean = false; 
  
  pdfResult: PDFResult | null = null; 
  uiMessage: string | null = null; 
  private isBrowser: boolean;
  
  // Properties to bind to the template tabs. These will hold all fields from the PDF.
  textFieldsForDisplay: MappedPdfField[] = [];
  checkboxFieldsForDisplay: CheckboxField[] = [];
  radioGroupsForDisplay: RadioGroup[] = [];

  // Properties for filtered fields (showing only mapped fields)
  filteredTextFields: MappedPdfField[] = [];
  filteredCheckboxFields: CheckboxField[] = [];
  filteredRadioGroups: RadioGroup[] = [];
  showAllFields: boolean = false;

  activeTab: string = 'text';
  
  // Expose constant to the template
  readonly FIELD_NOT_MAPPED_VALUE = FIELD_NOT_MAPPED_VALUE;

  constructor(private apiService: ApiService, @Inject(PLATFORM_ID) platformId: Object) { 
    this.isBrowser = isPlatformBrowser(platformId);
  }
  
  ngOnChanges(changes: SimpleChanges): void {
    if (changes['extractedData'] && changes['extractedData'].currentValue) {
      console.log('ResultsDisplayComponent: Received new extractedData from parent:', this.extractedData);
      const rawFields = this.extractedData?.fields || [];
      if (rawFields.length > 0) {
        this.fetchAndProcessFieldsForDisplay(rawFields);
      } else {
        this.resetState('No fields found in the extracted data from AI. PDF placeholders will be shown.');
        // Even with no AI data, we might want to fetch all PDF placeholders if backend supports it
        // For now, this relies on rawFields having something to trigger the call.
        // Consider a separate mechanism to load all placeholders if rawFields is empty.
        console.error('ResultsDisplayComponent: No fields found in the received extractedData');
      }
    }
  }

  resetState(message?: string | null) {
    this.pdfResult = null;
    this.textFieldsForDisplay = [];
    this.checkboxFieldsForDisplay = [];
    this.radioGroupsForDisplay = [];
    this.filteredTextFields = [];
    this.filteredCheckboxFields = [];
    this.filteredRadioGroups = [];
    this.isProcessingFields = false;
    this.pdfGenerationInProgress = false;
    this.uiMessage = message || null;
    this.showAllFields = false;
  }

  fetchAndProcessFieldsForDisplay(fieldsToProcess: any[]): void {
    this.isProcessingFields = true;
    this.uiMessage = 'Processing extracted fields and loading all PDF placeholders...';
    console.log('ResultsDisplayComponent: Calling fillPdf service with perform_fill: false', fieldsToProcess);
    
    // Create a map of field names to confidence scores from the AI output
    const confidenceMap = new Map<string, number>();
    fieldsToProcess.forEach((field: any) => {
      if (field.field_name && field.confidence_score !== undefined) {
        confidenceMap.set(field.field_name, field.confidence_score);
      }
    });
    
    this.apiService.fillPdf({ fields: fieldsToProcess, perform_fill: false }).subscribe({
      next: (response) => {
        console.log('ResultsDisplayComponent: Response from fillPdf (perform_fill: false):', response);
        this.isProcessingFields = false;
        this.pdfResult = response; 

        // Get the mapped fields and add confidence scores
        this.textFieldsForDisplay = response.all_mapped_fields || [];
        
        // Add confidence scores to the mapped fields
        this.textFieldsForDisplay.forEach(field => {
          // If the field has a value (not unmapped) and we have a confidence score for it
          if (field.value !== FIELD_NOT_MAPPED_VALUE) {
            // Try to find a confidence score by field name
            const confidence = confidenceMap.get(field.name);
            if (confidence !== undefined) {
              field.confidence_score = confidence;
            }
          }
        });
        
        this.checkboxFieldsForDisplay = response.checkbox_fields || [];
        this.radioGroupsForDisplay = response.radio_groups || [];
        
        // Filter fields to only show mapped ones initially
        this.filterMappedFields();
        
        console.log(`ResultsDisplayComponent: Populated textFields: ${this.textFieldsForDisplay.length}, checkboxes: ${this.checkboxFieldsForDisplay.length}, radioGroups: ${this.radioGroupsForDisplay.length}`);

        // Refined UI Message Logic
        if (response.pdf_generation_status === 'failed') {
          this.uiMessage = response.message || 'Error processing fields and loading PDF placeholders.';
        } else if (fieldsToProcess.length === 0) {
          // No AI input was provided
          if (this.textFieldsForDisplay.length > 0 || this.checkboxFieldsForDisplay.length > 0 || this.radioGroupsForDisplay.length > 0) {
            this.uiMessage = 'No AI data submitted. Displaying all available PDF placeholders.';
          } else {
            this.uiMessage = 'No AI data submitted and no PDF placeholders could be loaded.';
          }
        } else {
          // AI input was provided
          if (response.mapped_field_count && response.mapped_field_count > 0) {
            this.uiMessage = `Successfully processed AI data: ${response.mapped_field_count} field(s) were mapped to the PDF. All PDF placeholders shown below.`;
          } else {
            this.uiMessage = 'AI data processed, but no fields successfully mapped to the PDF. All PDF placeholders shown below (values from AI will indicate \"Not Found\").';
          }
        }
      },
      error: (error) => {
        console.error('ResultsDisplayComponent: Error from fillPdf (perform_fill: false):', error);
        this.isProcessingFields = false;
        const errorMessage = error.error?.message || error.message || 'An unknown error occurred while processing fields.';
        this.resetState(errorMessage);
      }
    });
  }
  
  generateAndDownloadPdf(): void {
    if (!this.extractedData || !this.extractedData.fields || this.extractedData.fields.length === 0) {
      this.uiMessage = 'Cannot generate PDF: No extracted fields available from AI.';
      return;
    }
    this.pdfGenerationInProgress = true;
    this.uiMessage = 'Generating and downloading PDF...';
    
    // Create a map of field names to confidence scores from the AI output
    const confidenceMap = new Map<string, number>();
    this.extractedData.fields.forEach((field: any) => {
      if (field.field_name && field.confidence_score !== undefined) {
        confidenceMap.set(field.field_name, field.confidence_score);
      }
    });
    
    // Call fillPdf with perform_fill: true to generate the actual PDF file
    this.apiService.fillPdf({
      fields: this.extractedData.fields,
      perform_fill: true
    }).subscribe({
      next: (result) => {
        this.pdfGenerationInProgress = false;
        this.pdfResult = result;
        
        if (result.pdf_generation_status === 'success' && result.pdf_url) {
          this.uiMessage = 'PDF generated successfully!';
          
          // Construct full URL by combining baseUrl with pdf_url
          // The baseUrl should be the same as the one used in the api service
          const baseUrl = 'http://localhost:8000';
          const fullPdfUrl = baseUrl + result.pdf_url;
          
          // Only attempt to open URL in browser environment
          if (this.isBrowser) {
            window.open(fullPdfUrl, '_blank');
          }
        } else {
          this.uiMessage = `PDF generation failed: ${result.message || 'Unknown error'}`;
        }
        
        // Re-populate display arrays as the backend might have more complete data after a fill attempt
        this.textFieldsForDisplay = result.all_mapped_fields || [];
        
        // Add confidence scores to the mapped fields
        this.textFieldsForDisplay.forEach(field => {
          // If the field has a value (not unmapped) and we have a confidence score for it
          if (field.value !== FIELD_NOT_MAPPED_VALUE) {
            // Try to find a confidence score by field name
            const confidence = confidenceMap.get(field.name);
            if (confidence !== undefined) {
              field.confidence_score = confidence;
            }
          }
        });
        
        this.checkboxFieldsForDisplay = result.checkbox_fields || [];
        this.radioGroupsForDisplay = result.radio_groups || [];
        
        // Refilter fields based on the updated data
        this.filterMappedFields();
      },
      error: (error) => {
        console.error('Error generating PDF:', error);
        this.pdfGenerationInProgress = false;
        this.uiMessage = `Error generating PDF: ${error.message || 'Unknown error'}`;
      }
    });
  }

  selectTab(tabName: string): void {
    this.activeTab = tabName;
  }

  isFieldValueNotFound(value: any): boolean {
    if (value === this.FIELD_NOT_MAPPED_VALUE) {
      return true;
    }
    // Optionally, keep previous checks if you want to visually distinguish
    // between explicitly unmapped and truly empty/null from a (hypothetical) direct PDF field read
    if (value === null || value === undefined || value === '') {
      return true; // Consider if this should also be styled as "Not Found" or just empty
    }
    if (typeof value === 'string' && value.toLowerCase().includes('not found')) {
      // This case might be redundant if AI output is cleaned before sending to backend,
      // or if backend normalizes "not found" strings to FIELD_NOT_MAPPED_VALUE
      return true;
    }
    return false;
  }
  
  toggleShowAllFields(): void {
    this.showAllFields = !this.showAllFields;
    this.filterMappedFields();
  }
  
  filterMappedFields(): void {
    if (this.showAllFields) {
      // Show all fields
      this.filteredTextFields = [...this.textFieldsForDisplay];
      this.filteredCheckboxFields = [...this.checkboxFieldsForDisplay];
      this.filteredRadioGroups = [...this.radioGroupsForDisplay];
    } else {
      // Filter to show only mapped fields
      this.filteredTextFields = this.textFieldsForDisplay.filter(field => 
        !this.isFieldValueNotFound(field.value)
      );
      
      // Show only checked checkboxes
      this.filteredCheckboxFields = this.checkboxFieldsForDisplay.filter(checkbox => 
        checkbox.checked
      );
      
      // Show only radio groups with a selection
      this.filteredRadioGroups = this.radioGroupsForDisplay.filter(radioGroup => 
        radioGroup.selected_value !== null
      );
    }
  }
}
