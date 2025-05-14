import os
from fillpdf import fillpdfs

# Define the input PDF path and output directory
PDF_PATH = "Experiment/uniform_residential_loan_application.pdf"
OUTPUT_DIR = "Experiment/output/"
EXTRACTED_FIELDS_PATH = "Experiment/pdf_fields_extracted.txt"
FILLED_PDF_PATH = os.path.join(OUTPUT_DIR, "filled_loan_application.pdf")

# The data provided by the user
USER_DATA_STRING = """Borrower Name\tBrenda Carol Parker\t100%
Borrower SSN\t987-65-6789\t80%
Borrower DOB\t1988-06-15\t100%
Borrower Present Address\t123 Elm Street, Apartment 4B, Pleasantville, TX, 75002\t100%
Borrower Home Phone\t214-555-1212\t100%
Borrower Marital Status\tUnmarried\t95%
Borrower Name and Address of Employer\tInnovatech Solutions LLC\t100%
Borrower Position/Title/Type of Business\tSenior Software Engineer\t100%
Monthly income Borrower Base a\t$9,500\t100%
Monthly income Borrower Other a21\t$10\t80%
Describe other income 1\tsavings interest\t80%
Amount\t$280,000\t100%
Purpose of Loan\tPurchase\t100%
Subject Property Address\t456 Oak Lane, Pleasantville, TX, 75002\t100%
"""

def parse_user_data(data_string):
    """Parses the user-provided string into a list of dictionaries."""
    parsed_data = []
    lines = data_string.strip().splitlines()
    for line in lines:
        parts = line.split('\t')
        if len(parts) == 3:
            field_name = parts[0].strip()
            value = parts[1].strip()
            try:
                confidence = int(parts[2].strip().replace('%', ''))
                parsed_data.append({
                    "field_name": field_name,
                    "value": value,
                    "confidence": confidence
                })
            except ValueError:
                print(f"Warning: Could not parse confidence for line: {line}")
        else:
            print(f"Warning: Skipping malformed line: {line}")
    return parsed_data

def get_pdf_fields_and_save(pdf_path, output_txt_path):
    """Extracts fillable fields from the PDF and saves them to a text file."""
    try:
        fields = fillpdfs.get_form_fields(pdf_path)
        with open(output_txt_path, 'w') as f:
            for field_name, field_value in fields.items():
                f.write(f"{field_name}: {field_value}\\n")
        print(f"Successfully extracted {len(fields)} fields to {output_txt_path}")
        return fields
    except Exception as e:
        print(f"Error extracting PDF fields: {e}")
        print("Please ensure 'pdftk' or 'poppler-utils' (for pdftotext) is installed and in your PATH.")
        return None

def map_user_data_to_pdf_fields(user_data, pdf_fields_dict):
    """
    Attempts to map user data to actual PDF field names.
    This is a simple mapping strategy and might need refinement based on actual field names.
    It prioritizes exact matches and then tries common variations.
    """
    data_to_fill = {}
    pdf_field_names_lower = {name.lower().replace(" ", "").replace("_", "").replace("-", ""): name for name in pdf_fields_dict.keys()}

    for item in user_data:
        if item['confidence'] >= 80:
            # Normalize user field name for matching
            user_field_normalized = item['field_name'].lower().replace(" ", "").replace("_", "").replace("-", "")
            
            # Attempt to find a match in PDF fields
            matched_pdf_field = None
            if user_field_normalized in pdf_field_names_lower:
                matched_pdf_field = pdf_field_names_lower[user_field_normalized]
            else:
                # Try to find partial matches or known common variations
                # Example: "BorrowerFirstName" vs "FirstNameBorrower1"
                # This part would likely need significant expansion for robust mapping
                if "borrowerfirstname" in user_field_normalized:
                    # Look for fields like 'topmostSubform[0].Page1[0].Borrower1Information[0].FirstName[0]' etc.
                    # This requires knowing the structure or having a more sophisticated fuzzy matching.
                    # For now, we'll rely on the direct mapping being mostly correct
                    # or the user providing exact field names if simple mapping fails.
                    pass # Placeholder for more advanced matching

            if matched_pdf_field:
                data_to_fill[matched_pdf_field] = item['value']
                print(f"Mapped user field '{item['field_name']}' to PDF field '{matched_pdf_field}' with value '{item['value']}'")
            elif item['field_name'] in pdf_fields_dict: # Direct match if no normalization was needed
                data_to_fill[item['field_name']] = item['value']
                print(f"Directly mapped user field '{item['field_name']}' to PDF field '{item['field_name']}' with value '{item['value']}'")
            else:
                # A common pattern for fillable PDFs is to have complex names.
                # The `fillpdf` library often returns names like:
                # 'topmostSubform[0].Page1[0].Borrower1Information[0].FirstName[0]'
                # 'topmostSubform[0].Page1[0].SocialSecurityNumber[0].SSN1[0]'
                # We need a strategy to map "Borrower First Name" to something like the above.
                # This is non-trivial without knowing the exact PDF structure or using fuzzy matching.
                # The current `pdf_fields_dict` from `get_form_fields` should contain these exact names.
                # We will rely on the user's provided field names being close enough for now,
                # or they might need to inspect `pdf_fields_extracted.txt` and adjust.
                print(f"Warning: User field '{item['field_name']}' (normalized: '{user_field_normalized}') with confidence {item['confidence']}% could not be directly mapped to a known PDF field. It will be skipped.")
                print(f"         Available PDF fields (normalized keys): {list(pdf_field_names_lower.keys())[:20]}...") # Print a sample

    # Handle specific known complex fields based on typical loan applications if direct mapping fails
    # This is highly PDF-specific and would need to be adjusted per PDF.
    # Example:
    # if 'Borrower First Name' in [item['field_name'] for item in user_data if item['confidence'] > 80] and \
    #    'topmostSubform[0].Page1[0].Borrower1Information[0].FirstName[0]' in pdf_fields_dict:
    #        data_to_fill['topmostSubform[0].Page1[0].Borrower1Information[0].FirstName[0]'] = next(i['value'] for i in user_data if i['field_name'] == 'Borrower First Name')

    return data_to_fill

def fill_pdf_form(pdf_path, data_dict, output_path):
    """Fills the PDF form with the provided data and saves it."""
    try:
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Fill the PDF
        # The `flatten=True` option makes the fields non-editable after filling.
        # Depending on `fillpdf` version and backend, this might behave differently or require poppler.
        fillpdfs.write_fillable_pdf(pdf_path, output_path, data_dict, flatten=False) # Changed flatten to False for wider compatibility initially
        print(f"Successfully filled PDF and saved to {output_path}")
        print("If fields are still editable, you might try with flatten=True, which may require poppler-utils.")
    except Exception as e:
        print(f"Error filling PDF: {e}")
        print("Please ensure 'pdftk' or 'poppler-utils' is installed and in your PATH.")

if __name__ == "__main__":
    print("Starting PDF processing script...")

    # Ensure the PDF path is correct relative to the script's execution directory
    # If this script is in Experiment/, and PDF is in Experiment/, then PDF_PATH is fine.
    # If running from project root, Experiment/ needs to be prepended.
    # For simplicity, assuming this script is run from the project root or paths are adjusted.
    
    # Correct paths assuming script is in Experiment/ and run from project root
    # If script is run from Experiment/, paths should be relative to Experiment/
    # For consistency with your request, I'm using paths relative to project root
    # and assuming the script `process_loan_application.py` is IN `Experiment/`
    
    # Make sure the output directory exists
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"Created output directory: {OUTPUT_DIR}")

    # Step 1: Extract and save PDF fields
    print(f"Attempting to extract fields from: {PDF_PATH}")
    pdf_actual_fields = get_pdf_fields_and_save(PDF_PATH, EXTRACTED_FIELDS_PATH)

    if pdf_actual_fields:
        # Step 2: Parse user data
        user_provided_data = parse_user_data(USER_DATA_STRING)
        print(f"Parsed {len(user_provided_data)} items from user data string.")

        # Step 3: Map user data to PDF fields (with >80% confidence)
        data_to_fill_pdf = map_user_data_to_pdf_fields(user_provided_data, pdf_actual_fields)
        
        if not data_to_fill_pdf:
            print("No data fields were mapped for filling. Check field names and confidence levels.")
            print("The extracted PDF field names are in:", EXTRACTED_FIELDS_PATH)
            print("Please compare them with your input data's 'field_name'.")
        else:
            print(f"Attempting to fill PDF with {len(data_to_fill_pdf)} mapped fields.")
            # Step 4: Fill the PDF
            fill_pdf_form(PDF_PATH, data_to_fill_pdf, FILLED_PDF_PATH)
    else:
        print("Could not extract PDF fields. Aborting fill process.")
        print(f"Please check if '{PDF_PATH}' is a valid fillable PDF and if 'pdftk' or 'poppler-utils' is installed.")

    print("PDF processing script finished.") 