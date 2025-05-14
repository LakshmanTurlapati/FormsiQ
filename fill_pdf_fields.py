import os
import fitz  # PyMuPDF
import json
from datetime import datetime
import re

def parse_variables(variables_text):
    """Parse the variables from the given text format"""
    variables = {}
    lines = variables_text.strip().split('\n')
    
    for line in lines:
        parts = line.split('\t')
        if len(parts) >= 3:
            field_name = parts[0].strip()
            value = parts[1].strip()
            confidence = parts[2].strip().replace('%', '')
            
            # Convert confidence to float
            try:
                confidence = float(confidence)
            except ValueError:
                confidence = 0
                
            variables[field_name] = {
                'value': value,
                'confidence': confidence
            }
    
    return variables

def map_variable_to_pdf_field(var_name, pdf_fields):
    """Map a variable name to a PDF field name using fuzzy matching logic"""
    # Basic mapping for common fields
    mapping = {
        "Borrower First Name": ["first_name", "firstname", "fname", "borrower_first_name", "borrower_firstname"],
        "Borrower Middle Name": ["middle_name", "middlename", "mname", "borrower_middle_name", "borrower_middlename"],
        "Borrower Last Name": ["last_name", "lastname", "lname", "borrower_last_name", "borrower_lastname", "surname"],
        "Borrower Suffix": ["suffix", "borrower_suffix", "name_suffix"],
        "Social Security Number": ["ssn", "social_security", "social_security_number", "borrower_ssn"],
        "Date of Birth": ["dob", "birth_date", "birthdate", "date_of_birth", "borrower_dob"],
        "Current Street Address": ["street", "address", "street_address", "current_address", "borrower_address"],
        "Current City": ["city", "current_city", "borrower_city"],
        "Current State": ["state", "current_state", "borrower_state"],
        "Current Zip Code": ["zip", "zipcode", "zip_code", "current_zip", "borrower_zip"],
        "Primary Phone Number": ["phone", "phone_number", "telephone", "borrower_phone"],
        "Email Address": ["email", "email_address", "borrower_email"],
        "Marital Status": ["marital", "marital_status", "borrower_marital_status"],
        "Current Employer Name": ["employer", "employer_name", "current_employer", "borrower_employer"],
        "Job Title/Position": ["job_title", "position", "title", "occupation", "borrower_job_title"],
        "Employment Start Date": ["employment_date", "start_date", "employment_start_date"],
        "Monthly Income (Base)": ["income", "base_income", "monthly_income", "borrower_income"],
        "Monthly Income (Other, specify source if possible)": ["other_income", "additional_income"],
        "Loan Amount Requested": ["loan_amount", "requested_amount", "amount"],
        "Loan Purpose": ["purpose", "loan_purpose"],
        "Property Street Address": ["property_address", "property_street", "property_street_address"],
        "Property City": ["property_city"],
        "Property State": ["property_state"],
        "Property Zip Code": ["property_zip", "property_zip_code"]
    }
    
    # Clean up var_name and remove common prefixes/suffixes for matching
    clean_var_name = var_name.lower().replace('(', '').replace(')', '').replace(',', '')
    
    # Check if the var_name is in our mapping
    if var_name in mapping:
        # For each potential field name in our mapping
        for field_pattern in mapping[var_name]:
            # Look for exact matches in PDF fields
            for pdf_field in pdf_fields:
                pdf_field_lower = pdf_field.lower()
                if field_pattern in pdf_field_lower or any(p in pdf_field_lower for p in mapping[var_name]):
                    return pdf_field
    
    # If no match found through mapping, try direct fuzzy matching
    var_words = set(clean_var_name.split())
    best_match = None
    best_score = 0
    
    for pdf_field in pdf_fields:
        pdf_field_lower = pdf_field.lower()
        pdf_words = set(pdf_field_lower.replace('_', ' ').split())
        
        # Calculate word overlap score
        intersection = len(var_words.intersection(pdf_words))
        if intersection > best_score:
            best_score = intersection
            best_match = pdf_field
    
    # Return the best match if it has at least some overlap
    if best_score > 0:
        return best_match
    
    return None

def format_value(var_name, value):
    """Format the value based on the variable name"""
    # Format date of birth if in YYYY-MM-DD format
    if "Date of Birth" in var_name or "birth" in var_name.lower():
        if re.match(r'\d{4}-\d{2}-\d{2}', value):
            try:
                date_obj = datetime.strptime(value, '%Y-%m-%d')
                return date_obj.strftime('%m/%d/%Y')
            except ValueError:
                pass
    
    # Format SSN if in XXX-XX-XXXX format
    if "Social Security" in var_name or "ssn" in var_name.lower():
        if re.match(r'\d{3}-\d{2}-\d{4}', value):
            return value.replace('-', '')
    
    # Format income values
    if "Income" in var_name:
        # Remove $ and commas
        value = value.replace('$', '').replace(',', '')
        # Extract the numeric part
        match = re.search(r'(\d+(\.\d+)?)', value)
        if match:
            return match.group(1)
    
    # Handle employment date that's described in words
    if "Employment Start Date" in var_name:
        if "years" in value.lower() and "months" in value.lower():
            # Try to convert relative time description to an actual date
            try:
                # Extract years and months
                years_match = re.search(r'(\d+)\s+years?', value.lower())
                months_match = re.search(r'(\d+)\s+months?', value.lower())
                
                years = int(years_match.group(1)) if years_match else 0
                months = int(months_match.group(1)) if months_match else 0
                
                # Calculate date based on current date
                current_date = datetime.now()
                start_date = current_date.replace(
                    year=current_date.year - years,
                    month=max(1, current_date.month - months)
                )
                
                return start_date.strftime('%m/%d/%Y')
            except (ValueError, AttributeError):
                pass
    
    # Return the original value if no special formatting is needed
    return value

def fill_pdf_form(pdf_path, variables, confidence_threshold=80, output_path=None):
    """Fill a PDF form with the provided variables above the confidence threshold"""
    # Open the PDF
    doc = fitz.open(pdf_path)
    
    # Get all form fields
    pdf_fields = {}
    for page_num in range(len(doc)):
        page = doc[page_num]
        widgets = page.widgets()
        for widget in widgets:
            field_name = widget.field_name
            field_type = widget.field_type
            pdf_fields[field_name] = {"widget": widget, "page": page, "type": field_type}
    
    # Map variables to PDF fields and fill them
    filled_fields = []
    unmapped_variables = []
    
    for var_name, var_info in variables.items():
        # Skip if confidence is below threshold
        if var_info['confidence'] < confidence_threshold:
            continue
        
        # Skip if value is "Not Found"
        if var_info['value'] == "Not Found":
            continue
            
        # Find matching PDF field
        pdf_field_name = map_variable_to_pdf_field(var_name, pdf_fields.keys())
        
        if pdf_field_name:
            # Format the value appropriately
            formatted_value = format_value(var_name, var_info['value'])
            
            # Get the field info
            field_info = pdf_fields[pdf_field_name]
            widget = field_info["widget"]
            page = field_info["page"]
            
            # Fill the field
            widget.field_value = formatted_value
            widget.update()
            
            filled_fields.append({
                "variable": var_name,
                "pdf_field": pdf_field_name,
                "value": formatted_value,
                "confidence": var_info['confidence']
            })
        else:
            unmapped_variables.append({
                "variable": var_name,
                "value": var_info['value'],
                "confidence": var_info['confidence']
            })
    
    # Save the filled PDF
    if output_path:
        doc.save(output_path)
        print(f"Filled PDF saved to: {output_path}")
    else:
        output_dir = os.path.dirname(pdf_path)
        output_file = os.path.join(output_dir, "filled_" + os.path.basename(pdf_path))
        doc.save(output_file)
        print(f"Filled PDF saved to: {output_file}")
    
    doc.close()
    
    return {
        "filled_fields": filled_fields,
        "unmapped_variables": unmapped_variables
    }

if __name__ == "__main__":
    # Define paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_path = os.path.join(script_dir, "Experiment", "uniform_residential_loan_application.pdf")
    
    # Create output directory if it doesn't exist
    output_dir = os.path.join(script_dir, "Experiment", "output")
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = os.path.join(output_dir, "filled_uniform_residential_loan_application.pdf")
    
    # Sample variables text
    variables_text = """Borrower First Name	Brenda	100%
Borrower Middle Name	Carol	100%
Borrower Last Name	Parker	100%
Borrower Suffix	Not Found	90%
Social Security Number	987-65-6789	80%
Date of Birth	1988-06-15	100%
Current Street Address	123 Elm Street, Apartment 4B	100%
Current City	Pleasantville	100%
Current State	TX	100%
Current Zip Code	75002	100%
Primary Phone Number	214-555-1212	100%
Email Address	brenda.c.parker@exampleemail.com	100%
Marital Status	Unmarried	95%
Current Employer Name	Innovatech Solutions LLC	100%
Job Title/Position	Senior Software Engineer	100%
Employment Start Date	five years and two months ago	70%
Monthly Income (Base)	$9,500	100%
Monthly Income (Other, specify source if possible)	$10 (savings interest)	80%
Loan Amount Requested	$280,000	100%
Loan Purpose	Purchase	100%
Property Street Address (if different from current, or for purchase)	456 Oak Lane	100%
Property City (if different from current, or for purchase)	Pleasantville	100%
Property State (if different from current, or for purchase)	TX	100%
Property Zip Code (if different from current, or for purchase)	75002	100%"""
    
    # Parse variables
    variables = parse_variables(variables_text)
    
    # Set confidence threshold (80%)
    confidence_threshold = 80
    
    # Fill the PDF
    result = fill_pdf_form(pdf_path, variables, confidence_threshold, output_path)
    
    # Print summary
    print(f"\nFilled {len(result['filled_fields'])} fields:")
    for field in result['filled_fields']:
        print(f"  - {field['variable']} -> {field['pdf_field']} = {field['value']} (Confidence: {field['confidence']}%)")
    
    if result['unmapped_variables']:
        print(f"\nCould not map {len(result['unmapped_variables'])} variables:")
        for var in result['unmapped_variables']:
            print(f"  - {var['variable']} = {var['value']} (Confidence: {var['confidence']}%)")
    
    # Save the results to a report file
    report_path = os.path.join(output_dir, "fill_report.json")
    with open(report_path, "w") as f:
        json.dump(result, f, indent=2)
    
    print(f"\nDetailed report saved to: {report_path}") 