#!/usr/bin/env python
"""
Simple PDF filling script using PyPDF directly with minimal dependencies.
"""
import os
import sys
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, TextStringObject, BooleanObject

# PDF paths
PDF_TEMPLATE = os.path.join('media', 'pdf', 'uniform_residential_loan_application.pdf')
PDF_OUTPUT = os.path.join('media', 'pdf', 'filled_output.pdf')

# Sample data to fill
SAMPLE_DATA = {
    'Borrower Name': 'John Smith',
    'Borrower SSN': '123-45-6789',
    'Borrower Home Phone': '(555) 123-4567',
    'Text1': 'johnsmith@example.com',  # Email field
    'Loan Amount': '$350,000'
}

def fill_pdf_simple_approach():
    """Fill PDF with a simpler, more direct approach"""
    print(f"Reading PDF template: {PDF_TEMPLATE}")
    
    try:
        # Read the PDF
        with open(PDF_TEMPLATE, 'rb') as file:
            reader = PdfReader(file)
            writer = PdfWriter()
            
            # Add all pages from template
            for page in reader.pages:
                writer.add_page(page)
            
            # Get the AcroForm
            if '/AcroForm' in reader.root:
                writer._root_object.update({
                    NameObject('/AcroForm'): reader.root['/AcroForm']
                })
            
            # Update fields with values
            for field_name, field_value in SAMPLE_DATA.items():
                print(f"Attempting to fill field: {field_name} = {field_value}")
                
                try:
                    # Update fields on each page (to ensure we find all instances)
                    for page_num, page in enumerate(writer.pages):
                        update_dict = {field_name: field_value}
                        writer.update_page_form_field_values(page, update_dict, False)
                        
                except Exception as page_err:
                    print(f"  Error updating field on page {page_num}: {str(page_err)}")
            
            # Write the PDF
            print(f"Writing filled PDF to: {PDF_OUTPUT}")
            with open(PDF_OUTPUT, 'wb') as output_file:
                writer.write(output_file)
            
            print("PDF filling completed successfully")
            return True
            
    except Exception as e:
        print(f"Error filling PDF: {str(e)}", file=sys.stderr)
        
        # Provide diagnostics on what went wrong
        if "has no attribute 'root'" in str(e):
            print("\nDiagnostics: The PDF might not have the proper structure for form filling.")
            print("This often happens with PDFs that were not properly created as fillable forms.")
        elif "No /AcroForm dictionary in PDF" in str(e):
            print("\nDiagnostics: The PDF does not have proper AcroForm dictionary.")
            print("This PDF likely has issues with its form structure.")
        
        return False

def alternative_fill_method():
    """Try an alternative method using direct field access"""
    print("\nTrying alternative filling method...")
    
    try:
        # Read the PDF
        with open(PDF_TEMPLATE, 'rb') as file:
            reader = PdfReader(file)
            writer = PdfWriter()
            
            # Add all pages from template
            for page in reader.pages:
                writer.add_page(page)
            
            # Get the form fields
            fields = reader.get_fields()
            if not fields:
                print("No form fields found in PDF")
                return False
                
            # Directly modify the fields in the PDF
            for field_name, field_value in SAMPLE_DATA.items():
                if field_name in fields:
                    print(f"Setting field {field_name} = {field_value}")
                    field_obj = fields[field_name]
                    
                    # Get the appropriate object type based on field type
                    if field_obj.get('/FT') == '/Tx':  # Text field
                        field_obj[NameObject('/V')] = TextStringObject(field_value)
                    elif field_obj.get('/FT') == '/Btn':  # Button/checkbox
                        # For checkbox, true = 'Yes' and false = 'Off'
                        if isinstance(field_value, bool):
                            field_obj[NameObject('/V')] = NameObject('/Yes' if field_value else '/Off')
                        else:
                            field_obj[NameObject('/V')] = NameObject(field_value)
                
            # Write the filled PDF
            alternative_output = os.path.join('media', 'pdf', 'filled_alternative.pdf')
            with open(alternative_output, 'wb') as output_file:
                writer.write(output_file)
                
            print(f"Alternative method completed, output at: {alternative_output}")
            return True
            
    except Exception as e:
        print(f"Alternative method failed: {str(e)}", file=sys.stderr)
        return False

if __name__ == "__main__":
    success = fill_pdf_simple_approach()
    
    # If the first method fails, try the alternative
    if not success:
        success = alternative_fill_method()
        
    sys.exit(0 if success else 1) 