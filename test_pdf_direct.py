#!/usr/bin/env python
"""
Test PDF filling directly with fields in the Gemma response format
"""

import os
import sys
import json
from pathlib import Path

# Set up proper path for imports
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.append(str(current_dir))

# Import from backend
sys.path.append(str(current_dir / 'backend'))
from api_processor.pdf_field_processor import PDFFieldProcessor

def test_pdf_filling_direct():
    """
    Test filling the PDF with fields from the Gemma API response
    """
    # Sample Gemma response with fields
    gemma_response = {
      "fields": [
        {"n": 1, "name": "Borrower First Name", "value": "Brenda", "conf": 100},
        {"n": 2, "name": "Borrower Middle Name", "value": "Carol", "conf": 95},
        {"n": 3, "name": "Borrower Last Name", "value": "Parker", "conf": 100},
        {"n": 4, "name": "Social Security Number", "value": "987-65-6789", "conf": 90},
        {"n": 5, "name": "Date of Birth", "value": "June 15th, 1988", "conf": 100},
        {"n": 6, "name": "Current Street Address", "value": "123 Elm Street", "conf": 95},
        {"n": 7, "name": "Current City", "value": "Pleasantville", "conf": 95},
        {"n": 8, "name": "Current Zip Code", "value": "75002", "conf": 95},
        {"n": 9, "name": "Phone Number", "value": "214-555-1212", "conf": 95},
        {"n": 10, "name": "Email Address", "value": "brenda.c.parker@exampleemail.com", "conf": 95},
        {"n": 11, "name": "Marital Status", "value": "Unmarried", "conf": 95},
        {"n": 12, "name": "Loan Amount", "value": "280000", "conf": 90},
        {"n": 13, "name": "Purpose of Loan", "value": "Purchase", "conf": 95},
        {"n": 14, "name": "Property Street Address", "value": "456 Oak Lane", "conf": 95},
        {"n": 15, "name": "Property City", "value": "Pleasantville", "conf": 95},
        {"n": 17, "name": "Property Zip Code", "value": "75002", "conf": 95},
        {"n": 18, "name": "Interest Rate", "value": "reasonable", "conf": 60},
        {"n": 19, "name": "Loan Term (Years)", "value": "30", "conf": 85},
        {"n": 20, "name": "Borrower Employer Name", "value": "Innovatech Solutions LLC", "conf": 95},
        {"n": 21, "name": "Job Title", "value": "Senior Software Engineer", "conf": 95},
        {"n": 22, "name": "Employment Start Date", "value": "five years and two months", "conf": 80},
        {"n": 23, "name": "Monthly Income (Base)", "value": "9500", "conf": 95},
        {"n": 24, "name": "Other Income Sources", "value": "small annual bonus", "conf": 75},
        {"n": 25, "name": "Mortgage Type", "value": "Conventional", "conf": 80},
        {"n": 26, "name": "Property Usage", "value": "Primary Residence", "conf": 95},
        {"n": 27, "name": "Borrower Self Employed", "value": "No", "conf": 85},
        {"n": 28, "name": "Borrower Own or Rent", "value": "Rent", "conf": 90},
        {"n": 29, "name": "Down Payment Amount", "value": "50000", "conf": 85}
      ]
    }
    
    # Extract fields from response
    fields = gemma_response.get('fields', [])
    
    print(f"Testing PDF filling with {len(fields)} fields from Gemma response")
    
    # Initialize the PDFFieldProcessor
    pdf_template_path = os.path.join(current_dir, 'backend', 'media', 'pdf', 'uniform_residential_loan_application.pdf')
    output_dir = os.path.join(current_dir, 'backend', 'media', 'pdf', 'output')
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, 'test_gemma_fill.pdf')
    
    try:
        # Create PDFFieldProcessor instance
        processor = PDFFieldProcessor(pdf_template_path)
        
        # Now map and fill
        data_to_fill = processor.map_user_data_to_pdf_fields(fields)
        
        print(f"\nMapped {len(data_to_fill)} PDF fields to fill:")
        for field_name, value in data_to_fill.items():
            print(f"  {field_name}: {value}")
        
        # Fill the PDF
        filled_pdf_path = processor.fill_pdf_form(data_to_fill, output_path)
        
        print(f"\nPDF filled successfully: {filled_pdf_path}")
        
        return True
    except Exception as e:
        print(f"Error filling PDF: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_pdf_filling_direct() 