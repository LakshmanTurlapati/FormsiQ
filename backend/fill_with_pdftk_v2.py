#!/usr/bin/env python
"""
Script to fill PDF forms using the pdftk command line tool with a different FDF approach.
"""
import os
import sys
import subprocess
import tempfile
import re

# PDF paths
PDF_TEMPLATE = os.path.join('media', 'pdf', 'uniform_residential_loan_application.pdf')
PDF_OUTPUT = os.path.join('media', 'pdf', 'filled_pdftk_v2.pdf')

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

def generate_fdf_from_pdf():
    """Generate an FDF file from the PDF using pdftk"""
    print("Generating FDF template from PDF...")
    
    # Create a temporary file for the FDF
    with tempfile.NamedTemporaryFile(suffix='.fdf', delete=False) as temp_file:
        fdf_template_path = temp_file.name
    
    # Run pdftk to generate an FDF template
    command = [
        'pdftk',
        PDF_TEMPLATE,
        'generate_fdf',
        'output',
        fdf_template_path
    ]
    
    if run_pdftk_command(command) is not None:
        print(f"FDF template generated: {fdf_template_path}")
        return fdf_template_path
    else:
        print("Failed to generate FDF template")
        return None

def modify_fdf_with_data(fdf_template_path):
    """Modify the FDF template with our data"""
    print("Modifying FDF with our data...")
    
    # Read the FDF template - use binary mode to avoid encoding issues
    with open(fdf_template_path, 'rb') as f:
        fdf_content = f.read()
    
    # Create a new FDF file with our data
    with tempfile.NamedTemporaryFile(suffix='.fdf', delete=False) as temp_file:
        filled_fdf_path = temp_file.name
    
    # For each field in our data, update the FDF content
    for field_name, field_value in SAMPLE_DATA.items():
        # Convert to bytes for binary replacement
        field_name_bytes = field_name.encode('utf-8')
        field_value_bytes = field_value.encode('utf-8')
        
        # Create pattern and replacement in bytes
        field_pattern = re.compile(b'/T\\s*\\(\\s*' + re.escape(field_name_bytes) + b'\\s*\\)\\s*/V\\s*\\([^)]*\\)')
        replacement = b'/T (' + field_name_bytes + b') /V (' + field_value_bytes + b')'
        
        # Replace the field value
        fdf_content = field_pattern.sub(replacement, fdf_content)
        
        print(f"Updated field in FDF: {field_name} = {field_value}")
    
    # Write the modified FDF
    with open(filled_fdf_path, 'wb') as f:
        f.write(fdf_content)
    
    print(f"Modified FDF created: {filled_fdf_path}")
    return filled_fdf_path

def create_fdf_directly():
    """Create an FDF file directly with our data"""
    print("Creating FDF file directly...")
    
    # Create a temporary file for the FDF
    with tempfile.NamedTemporaryFile(suffix='.fdf', delete=False) as temp_file:
        fdf_path = temp_file.name
    
    # Basic FDF structure
    fdf_header = b"""%FDF-1.2
%\xe2\xe3\xcf\xd3
1 0 obj
<</FDF<</Fields[
"""
    
    # Add our fields
    fields = []
    for field_name, field_value in SAMPLE_DATA.items():
        fields.append(f"<</T({field_name})/V({field_value})>>".encode('utf-8'))
    
    # Complete the FDF structure
    fdf_footer = b"""
]/ID[<f5fe04b2f5c0364f8870a843fa7127a6><f5fe04b2f5c0364f8870a843fa7127a6>]
>>/Type/Catalog>>
endobj
trailer
<</Root 1 0 R>>
%%EOF
"""
    
    # Write the FDF file
    with open(fdf_path, 'wb') as f:
        f.write(fdf_header)
        f.write(b"\n".join(fields))
        f.write(fdf_footer)
    
    print(f"FDF file created: {fdf_path}")
    return fdf_path

def fill_pdf_with_pdftk():
    """Fill the PDF form using pdftk"""
    print(f"Filling PDF form: {PDF_TEMPLATE}")
    
    # Skip the FDF template generation and go straight to direct creation
    print("Using direct FDF creation method...")
    fdf_path = create_fdf_directly()
    
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
        
        # Clean up the FDF file
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