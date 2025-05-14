#!/usr/bin/env python
"""
Script to check if fields were filled in a PDF.
"""
import os
import sys
from pypdf import PdfReader

# PDF paths
ORIGINAL_PDF = os.path.join('media', 'pdf', 'uniform_residential_loan_application.pdf')
FILLED_PDF = os.path.join('media', 'pdf', 'filled_alternative.pdf')

# Sample data we tried to fill
EXPECTED_DATA = {
    'Borrower Name': 'John Smith',
    'Borrower SSN': '123-45-6789',
    'Borrower Home Phone': '(555) 123-4567',
    'Text1': 'johnsmith@example.com',  # Email field
    'Loan Amount': '$350,000'
}

def check_pdf_fields(pdf_path, expected_data=None):
    """Check and print information about PDF fields"""
    print(f"Checking PDF: {pdf_path}")
    
    try:
        reader = PdfReader(pdf_path)
        print(f"Number of pages: {len(reader.pages)}")
        
        # Try to get fields
        fields = reader.get_fields()
        if fields:
            print(f"Number of fields: {len(fields)}")
            
            # If we have expected data, check those fields specifically
            if expected_data:
                print("\nChecking expected fields:")
                for field_name, expected_value in expected_data.items():
                    if field_name in fields:
                        actual_value = fields[field_name].get('/V', 'None')
                        print(f"  {field_name}:")
                        print(f"    - Expected: {expected_value}")
                        print(f"    - Actual: {actual_value}")
                        if str(actual_value) == str(expected_value):
                            print(f"    - ✓ MATCH")
                        else:
                            print(f"    - ✗ NO MATCH")
                    else:
                        print(f"  {field_name}: Field not found in PDF")
            
            # Print sample of other fields
            print("\nSample of other fields:")
            count = 0
            for name, field in fields.items():
                if expected_data and name in expected_data:
                    continue  # Skip fields we already checked
                    
                value = field.get('/V', 'None')
                if value != 'None':  # Only show fields with values
                    print(f"  {name}: {value}")
                    count += 1
                    if count >= 10:
                        break
                        
            if count == 0:
                print("  No other fields have values")
        else:
            print("No form fields found in the PDF.")
            
    except Exception as e:
        print(f"Error analyzing PDF: {str(e)}", file=sys.stderr)
        return False
        
    return True

if __name__ == "__main__":
    # First check the original PDF
    print("=== ORIGINAL PDF ===")
    check_pdf_fields(ORIGINAL_PDF)
    
    # Then check the filled PDF
    print("\n=== FILLED PDF ===")
    check_pdf_fields(FILLED_PDF, EXPECTED_DATA)
    
    sys.exit(0) 