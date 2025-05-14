#!/usr/bin/env python
"""
Script to fill PDF forms using PyPDF2 instead of PyPDF.
"""
import os
import sys
import PyPDF2

# PDF paths
PDF_TEMPLATE = os.path.join('media', 'pdf', 'uniform_residential_loan_application.pdf')
PDF_OUTPUT = os.path.join('media', 'pdf', 'filled_pypdf2.pdf')

# Sample data to fill
SAMPLE_DATA = {
    'Borrower Name': 'John Smith',
    'Borrower SSN': '123-45-6789',
    'Borrower Home Phone': '(555) 123-4567',
    'Text1': 'johnsmith@example.com',  # Email field
    'Loan Amount': '$350,000'
}

def fill_pdf_with_pypdf2():
    """Fill PDF using PyPDF2"""
    print(f"Reading PDF template: {PDF_TEMPLATE}")
    
    try:
        # Read the PDF
        with open(PDF_TEMPLATE, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            writer = PyPDF2.PdfWriter()
            
            # Add all pages from template
            for page in reader.pages:
                writer.add_page(page)
            
            # Check if the PDF has form fields
            if reader.get_fields():
                print(f"PDF has {len(reader.get_fields())} form fields")
                
                # Update fields with values
                for field_name, field_value in SAMPLE_DATA.items():
                    print(f"Attempting to fill field: {field_name} = {field_value}")
                    
                    try:
                        writer.update_page_form_field_values(
                            writer.pages[0],  # Update first page
                            {field_name: field_value}
                        )
                    except Exception as field_err:
                        print(f"  Error updating field {field_name}: {str(field_err)}")
                
                # Write the PDF
                print(f"Writing filled PDF to: {PDF_OUTPUT}")
                with open(PDF_OUTPUT, 'wb') as output_file:
                    writer.write(output_file)
                
                print("PDF filling completed successfully")
                return True
            else:
                print("No form fields found in the PDF")
                return False
            
    except Exception as e:
        print(f"Error filling PDF: {str(e)}", file=sys.stderr)
        return False

def alternative_fill_method():
    """Try an alternative method with PyPDF2"""
    print("\nTrying alternative PyPDF2 method...")
    alternative_output = os.path.join('media', 'pdf', 'filled_pypdf2_alt.pdf')
    
    try:
        # Read the PDF
        with open(PDF_TEMPLATE, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            writer = PyPDF2.PdfWriter()
            
            # Add all pages from template
            for page in reader.pages:
                writer.add_page(page)
            
            # Get the form fields
            fields = reader.get_fields()
            if not fields:
                print("No form fields found in PDF")
                return False
            
            # Try to fill all fields at once
            form_data = {}
            for field_name, field_value in SAMPLE_DATA.items():
                if field_name in fields:
                    form_data[field_name] = field_value
            
            if form_data:
                print(f"Filling {len(form_data)} fields at once")
                writer.update_page_form_field_values(writer.pages[0], form_data)
                
            # Write the filled PDF
            with open(alternative_output, 'wb') as output_file:
                writer.write(output_file)
                
            print(f"Alternative method completed, output at: {alternative_output}")
            return True
            
    except Exception as e:
        print(f"Alternative method failed: {str(e)}", file=sys.stderr)
        return False

def check_filled_pdf(pdf_path):
    """Check if fields were filled in the PDF"""
    print(f"\nChecking filled PDF: {pdf_path}")
    
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            fields = reader.get_fields()
            
            if not fields:
                print("No form fields found in the filled PDF")
                return
            
            print(f"PDF has {len(fields)} form fields")
            
            # Check our sample fields
            for field_name, expected_value in SAMPLE_DATA.items():
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
    
    except Exception as e:
        print(f"Error checking PDF: {str(e)}")

if __name__ == "__main__":
    success = fill_pdf_with_pypdf2()
    
    # If the first method succeeds, check the filled PDF
    if success:
        check_filled_pdf(PDF_OUTPUT)
    
    # Try the alternative method
    alt_success = alternative_fill_method()
    if alt_success:
        check_filled_pdf(os.path.join('media', 'pdf', 'filled_pypdf2_alt.pdf'))
        
    sys.exit(0 if success or alt_success else 1) 