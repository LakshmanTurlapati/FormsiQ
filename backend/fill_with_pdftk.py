#!/usr/bin/env python
"""
Script to fill PDF forms using the pdftk command line tool.
"""
import os
import sys
import subprocess
import tempfile
import json

# PDF paths
PDF_TEMPLATE = os.path.join('media', 'pdf', 'uniform_residential_loan_application.pdf')
PDF_OUTPUT = os.path.join('media', 'pdf', 'filled_pdftk.pdf')

# Sample data to fill
SAMPLE_DATA = {
    'Borrower Name': 'John Smith',
    'Borrower SSN': '123-45-6789',
    'Borrower Home Phone': '(555) 123-4567',
    'Text1': 'johnsmith@example.com',  # Email field
    'Loan Amount': '$350,000'
}

def run_pdftk_command(command):
    """Run a pdftk command and return the output"""
    try:
        result = subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"pdftk command failed: {e.stderr}", file=sys.stderr)
        return None

def dump_data_fields():
    """Dump the data fields from the PDF to understand its structure"""
    print("Dumping PDF form field data...")
    
    # Create a temporary file for the output
    with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp_file:
        dump_path = temp_file.name
    
    # Run pdftk to dump the data fields
    command = [
        'pdftk',
        PDF_TEMPLATE,
        'dump_data_fields',
        'output',
        dump_path
    ]
    
    if run_pdftk_command(command) is not None:
        # Read and parse the dump file
        with open(dump_path, 'r') as f:
            dump_data = f.read()
            
        print("PDF form fields:")
        field_count = 0
        current_field = {}
        
        for line in dump_data.split('\n'):
            line = line.strip()
            if line.startswith('---'):
                # New field separator
                if current_field and 'FieldName' in current_field:
                    field_count += 1
                    if field_count <= 10:  # Show only first 10 fields
                        print(f"  {field_count}. {current_field['FieldName']} ({current_field.get('FieldType', 'Unknown')})")
                current_field = {}
            elif ':' in line:
                key, value = line.split(':', 1)
                current_field[key.strip()] = value.strip()
        
        print(f"Total fields found: {field_count}")
        return dump_path
    else:
        print("Failed to dump PDF fields")
        return None

def create_fdf_file():
    """Create an FDF (Form Data Format) file for pdftk"""
    print("Creating FDF data file...")
    
    # Create a temporary file for the FDF data
    with tempfile.NamedTemporaryFile(suffix='.fdf', delete=False) as temp_file:
        fdf_path = temp_file.name
    
    # FDF header
    fdf_content = [
        "%FDF-1.2",
        "1 0 obj<</FDF<</Fields["
    ]
    
    # Add field data
    for field_name, field_value in SAMPLE_DATA.items():
        # Format: /FieldName (FieldValue)
        fdf_content.append(f"<</T({field_name})/V({field_value})>>");
    
    # FDF footer
    fdf_content.extend([
        "]>>/Type/Catalog>>",
        "endobj",
        "trailer",
        "<</Root 1 0 R>>",
        "%%EOF"
    ])
    
    # Write the FDF file
    with open(fdf_path, 'w') as f:
        f.write('\n'.join(fdf_content))
    
    print(f"FDF file created at: {fdf_path}")
    return fdf_path

def fill_pdf_with_pdftk():
    """Fill the PDF form using pdftk"""
    print(f"Filling PDF form: {PDF_TEMPLATE}")
    
    # First dump the fields to understand the PDF structure
    dump_path = dump_data_fields()
    if not dump_path:
        return False
    
    # Create the FDF data file
    fdf_path = create_fdf_file()
    if not fdf_path:
        return False
    
    # Fill the form using pdftk
    command = [
        'pdftk',
        PDF_TEMPLATE,
        'fill_form',
        fdf_path,
        'output',
        PDF_OUTPUT
    ]
    
    if run_pdftk_command(command) is not None:
        print(f"PDF filled successfully: {PDF_OUTPUT}")
        
        # Clean up temporary files
        os.unlink(dump_path)
        os.unlink(fdf_path)
        
        return True
    else:
        print("Failed to fill PDF form")
        return False

def check_filled_pdf():
    """Check if the PDF was filled correctly"""
    print(f"\nChecking filled PDF: {PDF_OUTPUT}")
    
    # Create a temporary file for the output
    with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp_file:
        dump_path = temp_file.name
    
    # Run pdftk to dump the data fields from the filled PDF
    command = [
        'pdftk',
        PDF_OUTPUT,
        'dump_data_fields',
        'output',
        dump_path
    ]
    
    if run_pdftk_command(command) is not None:
        # Read and parse the dump file
        with open(dump_path, 'r') as f:
            dump_data = f.read()
            
        # Check our sample fields
        print("Checking filled fields:")
        field_values = {}
        current_field = {}
        
        for line in dump_data.split('\n'):
            line = line.strip()
            if line.startswith('---'):
                # New field separator
                if current_field and 'FieldName' in current_field and 'FieldValue' in current_field:
                    field_values[current_field['FieldName']] = current_field['FieldValue']
                current_field = {}
            elif ':' in line:
                key, value = line.split(':', 1)
                current_field[key.strip()] = value.strip()
        
        # Check our expected fields
        for field_name, expected_value in SAMPLE_DATA.items():
            if field_name in field_values:
                actual_value = field_values[field_name]
                print(f"  {field_name}:")
                print(f"    - Expected: {expected_value}")
                print(f"    - Actual: {actual_value}")
                if actual_value == expected_value:
                    print(f"    - ✓ MATCH")
                else:
                    print(f"    - ✗ NO MATCH")
            else:
                print(f"  {field_name}: Field not found in filled PDF")
        
        # Clean up
        os.unlink(dump_path)
        
    else:
        print("Failed to check filled PDF")

if __name__ == "__main__":
    success = fill_pdf_with_pdftk()
    
    if success:
        check_filled_pdf()
    
    sys.exit(0 if success else 1) 