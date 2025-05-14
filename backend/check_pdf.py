#!/usr/bin/env python
"""
Simple script to check PDF fields and their properties.
"""
import os
import sys
from pypdf import PdfReader

PDF_PATH = os.path.join('media', 'pdf', 'uniform_residential_loan_application.pdf')

def check_pdf_fields():
    """Check and print information about PDF fields"""
    print(f"Checking PDF: {PDF_PATH}")
    
    try:
        reader = PdfReader(PDF_PATH)
        print(f"Number of pages: {len(reader.pages)}")
        
        # Try to get fields
        fields = reader.get_fields()
        if fields:
            print(f"Number of fields: {len(fields)}")
            print("\nSample of field names:")
            for i, name in enumerate(list(fields.keys())[:10]):
                print(f"  {i+1}. {name}")
                field = fields[name]
                # Print some details about the field
                field_type = field.get('/FT', 'Unknown')
                value = field.get('/V', 'None')
                print(f"     - Type: {field_type}, Current value: {value}")
        else:
            print("No form fields found in the PDF.")
            
    except Exception as e:
        print(f"Error analyzing PDF: {str(e)}", file=sys.stderr)
        return False
        
    return True

if __name__ == "__main__":
    success = check_pdf_fields()
    sys.exit(0 if success else 1) 