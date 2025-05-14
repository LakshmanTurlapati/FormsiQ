#!/usr/bin/env python
"""
Direct test for the PDFFiller component to identify issues.
This script does not rely on Django or other FormsIQ components.
"""

import os
import sys
import traceback
from pypdf import PdfReader, PdfWriter

# Get the absolute path to make sure we access the correct file
current_dir = os.path.dirname(os.path.abspath(__file__))
pdf_template_path = os.path.abspath(os.path.join(current_dir, 'backend', 'media', 'pdf', 'uniform_residential_loan_application.pdf'))
output_path = os.path.abspath(os.path.join(current_dir, 'test_direct_output.pdf'))

# Make sure the backend directory is in the path
backend_dir = os.path.join(current_dir, 'backend')
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

print(f"Using PDF template at: {pdf_template_path}")
print(f"Output will be saved to: {output_path}")

# Function to test PDF using pypdf directly
def test_with_pypdf():
    print("\n=== Testing with pypdf directly ===")
    try:
        # Verify the PDF can be opened
        reader = PdfReader(pdf_template_path)
        print(f"Successfully opened PDF with {len(reader.pages)} pages")
        
        # Check for fillable fields
        fields = reader.get_fields()
        if fields:
            print(f"Found {len(fields)} fillable fields")
            print(f"Sample field names: {list(fields.keys())[:5]}")
        else:
            print("No fillable fields found in the PDF")
            
        # Try a very basic fill and save operation
        writer = PdfWriter()
        
        # Add all pages from the original PDF
        for page in reader.pages:
            writer.add_page(page)
            
        # Try to set a field
        writer.update_page_form_field_values(
            writer.pages[0], 
            {"Borrower Name": "Test Name"}
        )
        
        # Write the result
        with open(output_path, "wb") as output_file:
            writer.write(output_file)
            
        print(f"PDF filled with pypdf and saved to {output_path}")
        if os.path.exists(output_path):
            print("Output file was successfully created")
        else:
            print("Failed to create output file")
            
        return True
    except Exception as e:
        print(f"Error in pypdf test: {e}")
        traceback.print_exc()
        return False
        
# Function to test the enhanced_pdf_handler
def test_with_enhanced_handler():
    print("\n=== Testing with enhanced_pdf_handler ===")
    try:
        # Import the enhanced_pdf_handler module
        import enhanced_pdf_handler
        print("Successfully imported enhanced_pdf_handler module")
        
        # Test PDFAnalyzer
        print("\n--- Testing PDFAnalyzer ---")
        analyzer = enhanced_pdf_handler.PDFAnalyzer(pdf_template_path)
        field_names = analyzer.get_field_names()
        print(f"PDFAnalyzer successfully found {len(field_names)} fields")
        print(f"Sample field names: {field_names[:5]}")
        
        # Test categorizing fields
        categories = analyzer.categorize_fields()
        for category, fields in categories.items():
            if fields:
                print(f"  {category}: {len(fields)} fields")
                
        # Get detailed field info for analysis
        all_fields_info = analyzer.get_all_fields_info()
        print(f"Got detailed info for {len(all_fields_info)} fields")
        
        # Test PDFFiller initialization
        print("\n--- Testing PDFFiller Initialization ---")
        filler = enhanced_pdf_handler.PDFFiller(pdf_template_path)
        print("Successfully initialized PDFFiller")
        
        # Test filling with one field
        print("\n--- Testing Basic Fill Operation ---")
        test_data = {"Borrower Name": "Test Name"}
        enhanced_output = os.path.join(current_dir, 'enhanced_output.pdf')
        
        try:
            result = filler.fill_form(test_data, enhanced_output)
            print(f"fill_form result: {result}")
            if os.path.exists(enhanced_output):
                print(f"Successfully created output file at {enhanced_output}")
            else:
                print(f"Failed to create output file at {enhanced_output}")
        except Exception as e:
            print(f"Error during fill_form: {e}")
            traceback.print_exc()
            
            # Try the alternative method
            print("\n--- Testing Alternative Fill Method ---")
            alt_output = os.path.join(current_dir, 'alt_output.pdf')
            try:
                result = filler._fill_form_alternative(test_data, alt_output)
                print(f"_fill_form_alternative result: {result}")
                if os.path.exists(alt_output):
                    print(f"Successfully created alternative output file at {alt_output}")
                else:
                    print(f"Failed to create alternative output file at {alt_output}")
            except Exception as e:
                print(f"Error during _fill_form_alternative: {e}")
                traceback.print_exc()
        
        return True
    except Exception as e:
        print(f"Error in enhanced_pdf_handler test: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # First check if PDF exists
    if not os.path.exists(pdf_template_path):
        print(f"ERROR: PDF template not found at {pdf_template_path}")
        sys.exit(1)
        
    # Run the tests
    pypdf_result = test_with_pypdf()
    enhanced_result = test_with_enhanced_handler()
    
    # Summary
    print("\n=== Test Summary ===")
    print(f"pypdf test: {'PASSED' if pypdf_result else 'FAILED'}")
    print(f"enhanced_pdf_handler test: {'PASSED' if enhanced_result else 'FAILED'}")
    
    if not pypdf_result and not enhanced_result:
        print("\nBoth tests failed. This suggests issues with the PDF file itself.")
    elif pypdf_result and not enhanced_result:
        print("\nThe PDF can be processed with pypdf but not with enhanced_pdf_handler.")
        print("This suggests issues with the enhanced_pdf_handler implementation.")
    elif not pypdf_result and enhanced_result:
        print("\nUnexpected result: enhanced_pdf_handler works but pypdf doesn't.")
    else:
        print("\nBoth libraries can process the PDF correctly.") 