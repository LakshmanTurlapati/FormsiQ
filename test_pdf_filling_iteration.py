import os
import sys
import traceback
from pypdf import PdfReader # For checking the PDF

# Remove Django dependency
# import django
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'formsiq_project.settings')
# django.setup()

# Get the absolute path to make sure we access the correct file
current_dir = os.path.dirname(os.path.abspath(__file__))
abs_pdf_template_path = os.path.abspath(os.path.join(current_dir, 'backend', 'media', 'pdf', 'uniform_residential_loan_application.pdf'))
abs_field_mapping_path = os.path.abspath(os.path.join(current_dir, 'backend', 'media', 'pdf', 'field_mapping.json'))

# Make sure the backend directory is in the path
backend_dir = os.path.join(current_dir, 'backend')
if backend_dir not in sys.path:
    sys.path.append(backend_dir)
    
# Also add the current directory to the path
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Import directly the enhanced PDF handler - we need to debug this component
try:
    import enhanced_pdf_handler
    print("Successfully imported enhanced_pdf_handler module")
except ImportError as e:
    print(f"Failed to import enhanced_pdf_handler module: {e}")
    # Try direct import as fallback
    try:
        from backend import enhanced_pdf_handler
        print("Successfully imported enhanced_pdf_handler module from backend")
    except ImportError as e:
        print(f"Failed to import enhanced_pdf_handler from backend: {e}")

try:
    from api_processor.pdf_service import fill_pdf_form, PDFFillError
    from api_processor.field_mapping import LLM_TO_PDF_FIELD_MAP # To map for expected data check
    
    # Override the constants in pdf_service.py with absolute paths to be safe
    import api_processor.pdf_service as pdf_service
    pdf_service.PDF_TEMPLATE_PATH = abs_pdf_template_path
    pdf_service.FIELD_MAPPING_PATH = abs_field_mapping_path
    print("Successfully imported and configured pdf_service module")
except ImportError as e:
    print(f"Failed to import api_processor modules: {e}")
    sys.exit(1)

# Set up enhanced debugging for PDF filling errors
def debug_pdf_filling():
    """Test the PDF filler directly to identify issues"""
    print("\n--- Direct PDF Filler Debug Test ---")
    try:
        # Verify PDF file exists
        if not os.path.exists(abs_pdf_template_path):
            print(f"PDF template does not exist at: {abs_pdf_template_path}")
            return False
        
        print(f"PDF template found at: {abs_pdf_template_path}")
        
        # Try to open and inspect the PDF directly with pypdf first
        try:
            reader = PdfReader(abs_pdf_template_path)
            fields = reader.get_fields()
            print(f"PDF inspection with pypdf shows {len(fields) if fields else 0} fields")
        except Exception as e:
            print(f"Error inspecting PDF with pypdf: {e}")
        
        from enhanced_pdf_handler import PDFFiller, PDFAnalyzer
        print("Successfully imported PDFFiller and PDFAnalyzer classes")
        
        # First test the PDFAnalyzer directly
        try:
            analyzer = PDFAnalyzer(abs_pdf_template_path)
            field_names = analyzer.get_field_names()
            print(f"PDFAnalyzer successfully detected {len(field_names)} form fields")
        except Exception as e:
            print(f"PDFAnalyzer failed: {e}")
            traceback.print_exc()
        
        # Test basic initialization
        try:
            filler = PDFFiller(abs_pdf_template_path)
            print("Successfully created PDFFiller instance")
        except Exception as e:
            print(f"Failed to create PDFFiller instance: {e}")
            traceback.print_exc()
            return False
        
        # Get information about the PDF fields
        try:
            field_names = filler.analyzer.get_field_names()
            print(f"The PDF has {len(field_names)} form fields according to PDFFiller.analyzer")
            print(f"First few field names: {field_names[:5]}")
        except Exception as e:
            print(f"Error getting field names: {e}")
            
        # Test filling just one simple field
        try:
            test_output = os.path.join(current_dir, 'test_output.pdf')
            result = filler.fill_form(
                {"Borrower Name": "Test Name"}, 
                test_output
            )
            print(f"Test filling result: {result}")
            if os.path.exists(test_output):
                print(f"Test output file was created at {test_output}")
            else:
                print(f"Test output file was NOT created at {test_output}")
        except Exception as e:
            print(f"Error during fill_form: {e}")
            traceback.print_exc()
        
        # Try the alternative method too
        try:
            alt_test_output = os.path.join(current_dir, 'test_alt_output.pdf')
            result = filler._fill_form_alternative(
                {"Borrower Name": "Test Name Alternative"}, 
                alt_test_output
            )
            print(f"Alternative filling result: {result}")
            if os.path.exists(alt_test_output):
                print(f"Alternative test output file was created at {alt_test_output}")
            else:
                print(f"Alternative test output file was NOT created at {alt_test_output}")
        except Exception as e:
            print(f"Error during _fill_form_alternative: {e}")
            traceback.print_exc()
            
        return True
    except Exception as e:
        print(f"PDFFiller overall debug test failed: {e}")
        traceback.print_exc()
        return False

# --- Adapted from check_filled_pdf.py ---
def check_form_fields(pdf_path, expected_data_llm_keys):
    """Check and print information about PDF fields, comparing against LLM keys."""
    print(f"--- Checking Filled PDF: {pdf_path} ---")
    results = {'passed': 0, 'failed': 0, 'not_found': 0, 'details': []}
    
    # Convert LLM expected keys to PDF expected keys
    expected_data_pdf_keys = {}
    for llm_key, expected_val in expected_data_llm_keys.items():
        pdf_key = LLM_TO_PDF_FIELD_MAP.get(llm_key)
        if pdf_key:
            # Handle "Group: Value" convention for expected value if applicable
            if ": " in llm_key:
                parts = llm_key.split(": ", 1)
                if len(parts) == 2:
                     # If original value was confirming the choice (e.g. Yes, True)
                    if expected_val in [True, 'True', 'true', 'Yes', 'yes', 'On', 'on']:
                        expected_data_pdf_keys[pdf_key] = parts[1].strip() # The option becomes the expected value
                    else: # if the value is 'No', 'False', etc. it means this option should NOT be selected.
                          # This check is tricky, as absence of selection is the norm.
                          # For now, we only check for positive selections.
                          pass 
            elif expected_val is True: # For boolean true, expect "Yes"
                 expected_data_pdf_keys[pdf_key] = "Yes"
            elif expected_val is False: # For boolean false, expect "Off" or None (field not set)
                                        # pypdf often returns None for unchecked boxes, or their 'Off' state export value.
                                        # For simplicity in this test, we'll expect it not to be the 'Yes' or 'On' state.
                                        # A more robust check would get the field's off appearance name.
                expected_data_pdf_keys[pdf_key] = None # Or 'Off', depends on PDF
            else:
                expected_data_pdf_keys[pdf_key] = expected_val
        else:
            print(f"Warning: LLM key '{llm_key}' not in LLM_TO_PDF_FIELD_MAP. Cannot check.")

    try:
        reader = PdfReader(pdf_path)
        fields = reader.get_fields()
        
        if not fields:
            print("No form fields found in the PDF.")
            results['details'].append("No form fields found in the PDF.")
            return results

        print(f"Found {len(fields)} fields in the PDF.")

        for pdf_field_name, expected_value in expected_data_pdf_keys.items():
            detail = {"field": pdf_field_name, "expected": str(expected_value), "actual": "Not Found"}
            if pdf_field_name in fields:
                actual_value_obj = fields[pdf_field_name]
                actual_value = actual_value_obj.get('/V') # Direct value
                
                # For checkboxes/radio buttons, /V might be a NameObject (e.g., /Yes, /Off, /Option1)
                # We need to convert it to a string for comparison.
                if actual_value is not None and not isinstance(actual_value, (str, int, float)):
                    actual_value = str(actual_value) # Convert NameObject like /Yes to "Yes" (strips leading /)
                
                detail["actual"] = str(actual_value)

                # Normalize common checkbox/radio button values for comparison
                normalized_actual = actual_value
                normalized_expected = expected_value
                
                if isinstance(actual_value, str) and actual_value.startswith("/"):
                    normalized_actual = actual_value[1:] # Strip leading / for comparison (e.g. /Yes -> Yes)

                if str(normalized_actual) == str(normalized_expected):
                    print(f"  ✓ {pdf_field_name}: Expected '{expected_value}', Got '{actual_value}' -> MATCH")
                    results['passed'] += 1
                    detail["status"] = "PASS"
                elif expected_value is None and actual_value is None: # Handled by above
                    print(f"  ✓ {pdf_field_name}: Expected not set (None), Got not set (None) -> MATCH (for false booleans)")
                    results['passed'] +=1
                    detail["status"] = "PASS (unset as expected)"
                else:
                    print(f"  ✗ {pdf_field_name}: Expected '{expected_value}', Got '{actual_value}' -> MISMATCH")
                    results['failed'] += 1
                    detail["status"] = "FAIL"
            else:
                print(f"  ✗ {pdf_field_name}: Expected field not found in PDF.")
                results['not_found'] += 1
                detail["status"] = "NOT_FOUND"
            results['details'].append(detail)
            
    except Exception as e:
        print(f"Error analyzing PDF: {str(e)}", file=sys.stderr)
        results['details'].append(f"Error analyzing PDF: {str(e)}")
    
    print(f"--- Check Summary: Passed: {results['passed']}, Failed: {results['failed']}, Not Found: {results['not_found']} ---")
    return results

# --- End of adapted check_filled_pdf.py logic ---

# Parse the multi-line string data into extracted_fields format
raw_data = """
Borrower First Name: Varun (100%)
Borrower Middle Name: Kumar (80%)
Borrower Last Name: Metha (100%)
Borrower Suffix: Not Found (0%)
Social Security Number: 123-00-1234 (100%)
Date of Birth: 1990-10-27 (100%)
Current Street Address: 987 Willow Creek Circle, Apt 12D (100%)
Current City: Plano (100%)
Current State: TX (100%)
Current Zip Code: 75093 (100%)
Primary Phone Number: 469-555-0011 (100%)
Email Address: v.k.metha@fastmail.net (100%)
Marital Status: Unmarried (100%)
Current Employer Name: CyberSystems Inc (100%)
Job Title/Position: Data Scientist (100%)
Employment Start Date: Not Found (0%)
Monthly Income (Base): 10500 (100%)
Monthly Income (Other, specify source): 200 (Dividends from stocks) (90%)
Loan Amount Requested: 220000 (90%)
Loan Purpose: Purchase (100%)
Property Street Address: 1210 Innovation Drive, Apartment 305 (100%)
Property City: Richardson (100%)
Property State: TX (100%)
Property Zip Code: 75081 (100%)
Mortgage Type: Conventional (100%)
Amortization Type: Fixed Rate (90%)
Property Usage: Primary Residence (100%)
"""

extracted_fields = []
expected_values_for_check = {} # For check_form_fields

for line in raw_data.strip().split('\n'):
    parts = line.split(':', 1)
    if len(parts) != 2:
        continue
    
    field_name_raw = parts[0].strip()
    value_and_confidence = parts[1].strip()
    
    # Extract value and confidence (e.g., "Varun (100%)")
    conf_start = value_and_confidence.rfind('(')
    conf_end = value_and_confidence.rfind('%)')
    
    field_value_str = ""
    confidence = 0.0

    if conf_start != -1 and conf_end != -1 and conf_start < conf_end:
        field_value_str = value_and_confidence[:conf_start].strip()
        try:
            confidence = float(value_and_confidence[conf_start+1:conf_end]) / 100.0
        except ValueError:
            # Handle cases where confidence might not be a number, or "Not Found" is the value
            field_value_str = value_and_confidence # Keep the whole string if parsing confidence fails
            confidence = 0.0 # Default confidence
    else:
        field_value_str = value_and_confidence # No confidence found, assume whole string is value
        confidence = 1.0 # Default if no confidence specified

    if field_value_str.lower() == 'not found':
        field_value = None # Or some other placeholder if your logic expects it for "Not Found"
        confidence = 0.0
    else:
        field_value = field_value_str

    # Special handling for choice-like fields based on common patterns in your data
    # This aligns with how pdf_service.py tries to interpret them
    llm_field_for_map_and_service = field_name_raw # Default
    
    # For fields that imply a selection (e.g., "Loan Purpose: Purchase")
    # the LLM output name is "Loan Purpose", value is "Purchase"
    # but your sample format is "Loan Purpose: Purchase (100%)"
    # We need to reconstruct the effective "LLM field name" that matches LLM_TO_PDF_FIELD_MAP keys
    # and what pdf_service expects.
    
    # If field_value contains the actual choice (e.g. 'Purchase' for 'Loan Purpose')
    # And field_name_raw is the generic category (e.g. 'Loan Purpose')
    # Then the key for LLM_TO_PDF_FIELD_MAP might be "Loan Purpose: Purchase"
    
    # Examples from your data:
    # Marital Status: Unmarried (100%) -> field_name_raw = "Marital Status", field_value = "Unmarried"
    #   LLM_TO_PDF_FIELD_MAP key could be "Marital Status: Unmarried"
    # Mortgage Type: Conventional (100%) -> field_name_raw = "Mortgage Type", field_value = "Conventional"
    #   LLM_TO_PDF_FIELD_MAP key could be "Mortgage Type: Conventional"

    # Let's form the key for mapping and for `pdf_service` based on this:
    # This is an assumption on how the LLM output is structured vs. `LLM_TO_PDF_FIELD_MAP` keys
    if field_name_raw in ["Marital Status", "Loan Purpose", "Mortgage Type", "Amortization Type", "Property Usage"]:
        # For these, the map key is like "Category: Value"
        llm_field_for_map_and_service = f"{field_name_raw}: {field_value}"
        # The 'field_value' for extracted_fields should indicate confirmation if the field is a choice.
        # The pdf_service now expects the 'value' part (e.g. "VA") to be passed if 'field_value' is 'Yes'/'True'.
        # So, for these, we set field_value to 'Yes' to indicate the choice is made.
        actual_value_for_service = "Yes" # This signals to pdf_service that this choice is selected
    else:
        actual_value_for_service = field_value

    if confidence > 0 and field_value is not None: # Only add if confidence is positive and value exists
        extracted_fields.append({
            'field_name': llm_field_for_map_and_service, # This must match keys in LLM_TO_PDF_FIELD_MAP or direct handling
            'field_value': actual_value_for_service, 
            'confidence_score': confidence
        })
        # For checking, use the llm_field_for_map_and_service as key, and its intended selected value
        expected_values_for_check[llm_field_for_map_and_service] = actual_value_for_service


print("--- Parsed Extracted Fields for PDF Filling ---")
for f in extracted_fields:
    print(f)

print("\n--- Expected LLM Key-Value Pairs for PDF Check ---")
for k, v in expected_values_for_check.items():
    print(f"LLM Key: '{k}', Expected Service Value: '{v}'")


print("\n--- Attempting to Fill PDF ---")
try:
    # Use the hard-coded paths
    filled_pdf_path = fill_pdf_form(extracted_fields)
    print(f"PDF filling function completed. Output PDF at: {filled_pdf_path}")
    
    # Now check the filled PDF
    if filled_pdf_path and os.path.exists(filled_pdf_path):
        check_form_fields(filled_pdf_path, expected_values_for_check)
    elif filled_pdf_path:
        print(f"Error: Filled PDF path returned ({filled_pdf_path}), but file does not exist.")
    else:
        print("Error: PDF filling function did not return a path.")

except PDFFillError as e:
    print(f"PDFFillError occurred: {e}")
except Exception as e:
    print(f"An unexpected error occurred during the test: {e}", file=sys.stderr)
    traceback.print_exc()

# To exit shell if run via "<"
# quit() 

# Call our debug function at the end
print("\n=== RUNNING DIRECT PDFFILLER DEBUG TEST ===")
debug_success = debug_pdf_filling()
print(f"Debug test {'passed' if debug_success else 'failed'}")

print("\n=== MAIN TEST COMPLETE ===") 