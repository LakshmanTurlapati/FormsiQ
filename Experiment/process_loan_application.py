import os
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, TextStringObject, BooleanObject

# Define the input PDF path and output directory
PDF_PATH = "Experiment/uniform_residential_loan_application.pdf"
OUTPUT_DIR = "Experiment/output/"
EXTRACTED_FIELDS_PATH = "Experiment/pdf_fields_extracted_pypdf.txt"
FILLED_PDF_PATH = os.path.join(OUTPUT_DIR, "filled_loan_application_pypdf.pdf")

# Revised USER_DATA_STRING with keys closer to typical PDF field names
# This will need to be EXACTLY matched to names from pdf_fields_extracted_pypdf.txt later
USER_DATA_STRING = """Borrower Name	Brenda Carol Parker	100%
Borrower SSN	987-65-6789	80%
Borrower DOB	1988-06-15	100%
Borrower Present Address	123 Elm Street, Apartment 4B, Pleasantville, TX, 75002	100%
Borrower Home Phone	214-555-1212	100%
Borrower Email Address	brenda.c.parker@exampleemail.com	100%
Borrower Marital Status	Unmarried	95% 
Borrower Name and Address of Employer	Innovatech Solutions LLC	100%
Borrower Position/Title/Type of Business	Senior Software Engineer	100%
Borrower Employment Start Date	five years and two months ago	70%
Monthly income Borrower Base a	$9,500	100%
Monthly income Borrower Other a21	$10	80%
Describe other income 1	savings interest	80%
Amount	$280,000	100%
Purpose of Loan	Purchase	100%
Subject Property Address	456 Oak Lane, Pleasantville, TX, 75002	100%
Borrower Suffix	Not Found	90%
""" 
# Removed fields that were too vague (city, state, zip as separate items for now, handled by combined address)
# And combined first/middle/last name into "Borrower Name"

def parse_user_data(data_string):
    parsed_data = []
    for line in data_string.strip().splitlines():
        parts = line.split('\t')
        if len(parts) == 3:
            field_name, value, confidence_str = parts
            parsed_data.append({
                "field_name": field_name.strip(),
                "value": value.strip(),
                "confidence": int(confidence_str.replace('%', '').strip())
            })
        else:
            print(f"Warning: Skipping malformed line in user data: {line}")
    return parsed_data

def get_pdf_fields_pypdf(pdf_path, output_txt_path):
    try:
        reader = PdfReader(pdf_path)
        fields = reader.get_fields() # This gets a dictionary of field objects
        if not fields:
            print(f"Warning: No fields found in {pdf_path} using pypdf.get_fields().")
            with open(output_txt_path, 'w') as f:
                f.write("No fields found by pypdf.get_fields().\n")
            return None

        with open(output_txt_path, 'w') as f:
            f.write(f"Extracted {len(fields)} fields using pypdf.get_fields():\n\n")
            for field_name, field_obj in fields.items(): # field_obj is a dictionary-like object
                f.write(f"Field Name (Key from get_fields()): {field_name}\n")
                partial_name = field_obj.get('/T', 'N/A') # Partial field name
                field_type = field_obj.get('/FT', 'N/A') # Field Type
                value = field_obj.get('/V', 'N/A')       # Current Value
                default_value = field_obj.get('/DV', 'N/A') # Default Value
                
                f.write(f"  Partial Name (/T): {partial_name}\n")
                f.write(f"  Field Type (/FT): {field_type}\n")
                f.write(f"  Value (/V): {value}\n")
                f.write(f"  Default Value (/DV): {default_value}\n")

                # For buttons (checkboxes, radio buttons), export values/states are key
                if field_type == '/Btn':
                    # The _States_ key often directly lists the ON and OFF state names
                    states_tuple = field_obj.get('/_States_') 
                    if states_tuple:
                        f.write(f"  Explicit States (/_States_): {list(states_tuple)}\n")

                    # Appearance states can also give clues about "on"/"off" values
                    ap_dict = field_obj.get('/AP')
                    if ap_dict and ap_dict.get('/N'): # Normal appearance
                        f.write(f"  Appearance States (/AP/N keys): {list(ap_dict['/N'].keys())}\n")
                    
                    # Kids are individual radio buttons in a group
                    kids = field_obj.get('/Kids')
                    if kids:
                        f.write(f"  Kids ({len(kids)}):\n")
                        for kid_idx, kid_ref in enumerate(kids):
                            kid_obj = kid_ref.get_object()
                            kid_partial_name = kid_obj.get('/T', f'Kid_{kid_idx}_Name_Unknown')
                            kid_ap_states = kid_obj.get('/APN', {}).keys() # Possible appearance states for this kid
                            kid_as = kid_obj.get('/AS', 'N/A') # Current appearance state
                            # Export value is often one of the /AP/N keys
                            # Example: if /AP/N has a key like '/Yes', that's the export value
                            export_value = "Unknown"
                            if kid_obj.get('/AP') and kid_obj['/AP'].get('/N'):
                                # The keys of AP/N are the export values for different states
                                possible_exports = list(kid_obj['/AP']['/N'].keys())
                                # Often, one is '/Off' and the other is the 'on' state like '/Yes' or a specific name
                                on_values = [k for k in possible_exports if k != '/Off']
                                if on_values:
                                    export_value = on_values[0] # Take the first non-'Off' state as representative "on" value
                            
                            f.write(f"    - Kid {kid_idx}: PartialName={kid_partial_name}, ExportValue(guess)={export_value}, CurrentState(/AS)={kid_as}\n")
                f.write(f"  Full Object (raw): {str(field_obj)}\n\n")
        print(f"Successfully extracted {len(fields)} fields to {output_txt_path} using pypdf.")
        return fields
    except Exception as e:
        print(f"Error extracting PDF fields with pypdf: {e}")
        return None

def get_checkbox_on_value(field_obj):
    """
    Tries to determine the 'ON' state value for a checkbox.
    Checks /_States_ first, then /AP/N keys.
    Returns the 'ON' state string (e.g., '/Yes') or None if not determinable.
    """
    if not field_obj or field_obj.get('/FT') != '/Btn' or field_obj.get('/Kids'):
        return None # Not a standalone checkbox

    # 1. Check for /_States_ array (most direct)
    # Example: {'/T': 'checkbox1', '/FT': '/Btn', '/_States_': ['/Yes', '/Off']}
    states_tuple = field_obj.get('/_States_')
    if states_tuple and isinstance(states_tuple, tuple) and len(states_tuple) > 0:
        # Typically, one is '/Off', the other is the 'ON' state.
        # Or, if only one state, that's the 'ON' state for some types of buttons.
        for state in states_tuple:
            if state != '/Off':
                return str(state) # Return the first non-'/Off' state
        if '/Off' not in states_tuple: # If no /Off, the first one might be the ON state
             return str(states_tuple[0])


    # 2. Check /AP /N dictionary (Appearance States / Normal)
    # Example: {'/AP': {'/N': {'/Yes': stream_obj, '/Off': stream_obj}}}
    ap_dict = field_obj.get('/AP')
    if ap_dict:
        normal_states_dict = ap_dict.get('/N')
        if normal_states_dict and hasattr(normal_states_dict, 'keys'):
            # PyPDF2 makes these keys NameObject, convert to string
            possible_on_states = [str(k) for k in normal_states_dict.keys() if str(k) != '/Off']
            if possible_on_states:
                return possible_on_states[0] # Return the first non-'/Off' state found

    # Fallback for common checkboxes if no explicit states found but it's a /Btn
    # This is a guess; many simple checkboxes use /Yes by convention.
    # The current value /V might also indicate the ON state if it's already checked in the template.
    current_val = field_obj.get('/V')
    if current_val and isinstance(current_val, NameObject) and str(current_val) != '/Off':
        return str(current_val)
        
    return "/Yes" # Default guess if no other info found (common but not guaranteed)

def list_checkbox_fields(pdf_fields_dict):
    """
    Identifies and prints details of standalone checkboxes from the extracted PDF fields,
    including a more robustly determined 'ON' state.
    """
    if not pdf_fields_dict:
        print("Cannot list checkboxes, PDF fields dictionary is empty.")
        return

    print("\n--- Identified Standalone Checkboxes (with detected 'ON' values) ---")
    found_checkboxes = False
    for field_name, field_obj in pdf_fields_dict.items():
        field_type = field_obj.get('/FT')
        if field_type == '/Btn': # It's a button
            kids = field_obj.get('/Kids')
            if not kids: # It's a standalone button (likely a checkbox)
                found_checkboxes = True
                partial_name = field_obj.get('/T', 'N/A')
                current_value_obj = field_obj.get('/V')
                current_value_str = str(current_value_obj) if current_value_obj else 'N/A'
                
                on_state_value = get_checkbox_on_value(field_obj)
                
                print(f"  Checkbox PDF Name (Key): {field_name}")
                print(f"    Descriptive Name (/T): {partial_name}")
                print(f"    Current Value in PDF (/V): {current_value_str}")
                print(f"    Detected 'ON' State Value: {on_state_value if on_state_value else 'Could not determine'}")
    
    if not found_checkboxes:
        print("No standalone checkboxes found.")
    print("--------------------------------------------------------------------\n")

def map_user_data_to_pdf_fields_pypdf(user_data_list, pdf_fields_dict):
    data_to_fill = {} 
    normalized_pdf_name_to_original_key = {}

    for pdf_key, field_obj in pdf_fields_dict.items():
        normalized_key = pdf_key.lower().replace(" ", "").replace("_", "").replace("-", "").replace(":", "")
        normalized_pdf_name_to_original_key[normalized_key] = pdf_key
        partial_name = field_obj.get('/T')
        if partial_name and isinstance(partial_name, (str, TextStringObject)):
            normalized_partial_name = str(partial_name).lower().replace(" ", "").replace("_", "").replace("-", "").replace(":", "")
            if normalized_partial_name not in normalized_pdf_name_to_original_key:
                 normalized_pdf_name_to_original_key[normalized_partial_name] = pdf_key

    print(f"DEBUG (pypdf map): Sample of normalized PDF keys for matching: {list(normalized_pdf_name_to_original_key.keys())[:10]}")

    # First pass: Fill text fields and map radio groups based on user data
    for item in user_data_list:
        if item['confidence'] < 80:
            print(f"DEBUG (pypdf map): Skipping user field '{item['field_name']}' due to low confidence ({item['confidence']}%).")
            continue

        user_field_normalized = item['field_name'].lower().replace(" ", "").replace("_", "").replace("-", "").replace(":", "")
        pdf_target_field_key = normalized_pdf_name_to_original_key.get(user_field_normalized)
        
        if not pdf_target_field_key:
            # This field from USER_DATA_STRING doesn't directly map to a PDF key by name
            # It might be used for intelligent checkbox ticking later, or it's unmapped
            print(f"DEBUG (pypdf map): User field '{item['field_name']}' (normalized: '{user_field_normalized}') not directly mapped to a PDF key for text/radio. May be used for checkboxes or unmapped.")
            continue

        field_obj = pdf_fields_dict[pdf_target_field_key]
        field_type = field_obj.get('/FT')
        user_value = item['value']
        
        print(f"DEBUG (pypdf map): Processing user field '{item['field_name']}' (value: '{user_value}') mapped to PDF key '{pdf_target_field_key}' (Type: {field_type})")

        if field_type == '/Tx': # Text field
            data_to_fill[pdf_target_field_key] = user_value
            print(f"  Action: Set Text for '{pdf_target_field_key}' to '{user_value}'")
        
        elif field_type == '/Btn': # Button (Radio group at this stage)
            kids = field_obj.get('/Kids')
            if kids: # Radio group
                print(f"  Action: Radio group '{pdf_target_field_key}'. User wants to select option representing '{user_value}'.")
                found_option = False
                for kid_ref in kids:
                    kid_obj = kid_ref.get_object()
                    kid_ap_n_states = kid_obj.get('/AP', {}).get('/N', {})
                    kid_on_state = None
                    for state_key in kid_ap_n_states.keys():
                        if state_key != '/Off': 
                            kid_on_state = state_key
                            break
                    
                    if kid_on_state and str(kid_on_state).strip('/').lower() == user_value.lower():
                        data_to_fill[pdf_target_field_key] = NameObject(kid_on_state)
                        print(f"    Set radio group '{pdf_target_field_key}' to '{kid_on_state}' (matches user value '{user_value}')")
                        found_option = True
                        break
                    elif kid_obj.get('/T') and user_value.lower() in str(kid_obj.get('/T')).lower(): 
                         if kid_on_state:
                            data_to_fill[pdf_target_field_key] = NameObject(kid_on_state)
                            print(f"    Set radio group '{pdf_target_field_key}' to '{kid_on_state}' (kid name '{kid_obj.get('/T')}' matches user value '{user_value}')")
                            found_option = True
                            break
                if not found_option:
                    print(f"    WARNING: Could not find a matching radio option for '{user_value}' in group '{pdf_target_field_key}'. Field may not be set correctly.")
                    data_to_fill[pdf_target_field_key] = user_value # Fallback attempt
            # Standalone checkboxes are handled in the next pass
        
        elif field_type == '/Ch': # Choice field (dropdown)
            data_to_fill[pdf_target_field_key] = user_value
            print(f"  Action: Set Choice/Dropdown '{pdf_target_field_key}' to '{user_value}'")
        
        else:
            print(f"  WARNING: PDF field '{pdf_target_field_key}' has unhandled type '{field_type}'. Attempting to set as text: '{user_value}'")
            data_to_fill[pdf_target_field_key] = user_value

    # Second pass: "Intelligently" tick checkboxes
    print("\n--- Attempting to intelligently tick checkboxes ---")
    for pdf_key, field_obj in pdf_fields_dict.items():
        if field_obj.get('/FT') == '/Btn' and not field_obj.get('/Kids'): # Standalone checkbox
            checkbox_desc_name = str(field_obj.get('/T', pdf_key)) # Use /T if available, else the main key
            normalized_checkbox_desc_name = checkbox_desc_name.lower().replace(" ", "").replace("_", "").replace("-", "").replace(":", "")
            
            # Try to find a matching entry in USER_DATA_STRING for this checkbox's descriptive name
            matched_user_item = None
            for item in user_data_list:
                user_field_normalized = item['field_name'].lower().replace(" ", "").replace("_", "").replace("-", "").replace(":", "")
                if user_field_normalized == normalized_checkbox_desc_name:
                    matched_user_item = item
                    break
            
            if matched_user_item:
                user_value_for_checkbox = matched_user_item['value']
                print(f"  Evaluating checkbox '{checkbox_desc_name}' based on user data: '{matched_user_item['field_name']}: {user_value_for_checkbox}'")
                
                # Check if user value suggests an affirmative
                if user_value_for_checkbox.lower() in ['true', 'yes', 'on', 'checked']:
                    on_state = get_checkbox_on_value(field_obj)
                    if on_state:
                        data_to_fill[pdf_key] = NameObject(on_state)
                        print(f"    Action: Set checkbox '{checkbox_desc_name}' (PDF key: {pdf_key}) to ON state '{on_state}'")
                    else:
                        print(f"    WARNING: Could not determine 'ON' state for checkbox '{checkbox_desc_name}'. Cannot tick.")
                elif user_value_for_checkbox.lower() in ['false', 'no', 'off', 'unchecked']:
                    # Explicitly set to Off if "false", "no", or "off" is provided
                    # Most PDFs default to Off, but this makes it explicit
                    data_to_fill[pdf_key] = NameObject("/Off") # Common 'off' state
                    print(f"    Action: Set checkbox '{checkbox_desc_name}' (PDF key: {pdf_key}) to OFF state '/Off'")
                else:
                    print(f"    Info: User value '{user_value_for_checkbox}' for checkbox '{checkbox_desc_name}' is not a standard affirmative/negative. No action taken by default for this checkbox.")
            # else:
                # print(f"  No direct user data entry found for checkbox: {checkbox_desc_name}")

    return data_to_fill

def fill_pdf_form_pypdf(input_pdf_path, output_pdf_path, data_to_fill_dict):
    try:
        reader = PdfReader(input_pdf_path)
        writer = PdfWriter()
        
        # Revert to writer.append(reader) to preserve document-level structures like AcroForm
        writer.append(reader)

        print(f"DEBUG (pypdf fill): Data dictionary for filling: {data_to_fill_dict}")
        
        # Update form field values on the writer's pages
        # pypdf's update_page_form_field_values works on a page object from the writer
        for page_num in range(len(writer.pages)):
            # Important: Need to ensure field_values are passed correctly.
            # Some values (like for checkboxes) need to be NameObject, not just strings.
            # The data_to_fill_dict should already have NameObjects where appropriate.
            writer.update_page_form_field_values(
                writer.pages[page_num], 
                fields=data_to_fill_dict,
                auto_regenerate=False # Recommended
            )
            # Forcing appearance generation might be needed for some viewers if auto_regenerate=False isn't enough
            # This is an advanced topic. For now, rely on update_page_form_field_values.

        if os.path.exists(output_pdf_path):
            os.remove(output_pdf_path)
            print(f"DEBUG (pypdf fill): Removed existing output file: {output_pdf_path}")

        with open(output_pdf_path, "wb") as output_stream:
            writer.write(output_stream)
        print(f"Successfully filled PDF using pypdf and saved to {output_pdf_path}")

    except Exception as e:
        print(f"Error filling PDF with pypdf: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("Starting PDF processing script using pypdf...")

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"Created output directory: {OUTPUT_DIR}")

    print(f"Attempting to extract fields from: {PDF_PATH} using pypdf")
    pdf_fields = get_pdf_fields_pypdf(PDF_PATH, EXTRACTED_FIELDS_PATH)

    if pdf_fields:
        print(f"\nSuccessfully read {len(pdf_fields)} fields from {PDF_PATH}")
        
        # List checkboxes
        list_checkbox_fields(pdf_fields)

        user_data = parse_user_data(USER_DATA_STRING)
        print(f"Parsed {len(user_data)} items from user data string.")
        
        data_to_fill = map_user_data_to_pdf_fields_pypdf(user_data, pdf_fields)
        
        if not data_to_fill:
            print("No data to fill after mapping (pypdf). Exiting.")
        else:
            print(f"Attempting to fill PDF with {len(data_to_fill)} mapped fields using pypdf.")
            fill_pdf_form_pypdf(PDF_PATH, FILLED_PDF_PATH, data_to_fill)
    else:
        print(f"Could not extract fields from {PDF_PATH}. Aborting fill process.")

    print("PDF processing script (pypdf) finished.") 