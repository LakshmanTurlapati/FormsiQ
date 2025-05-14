import os
import sys
import fitz  # PyMuPDF
import json
from datetime import datetime
import re
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PDFFormProcessor:
    """Class to extract and fill PDF form fields"""
    
    def __init__(self, pdf_path, output_dir=None):
        """Initialize with the path to the PDF file"""
        self.pdf_path = pdf_path
        self.output_dir = output_dir or os.path.dirname(pdf_path)
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Initialize document
        try:
            self.doc = fitz.open(pdf_path)
            logger.info(f"Successfully opened PDF: {pdf_path}")
        except Exception as e:
            logger.error(f"Error opening PDF: {e}")
            raise
    
    def extract_fields(self, save_to_file=True):
        """Extract all fillable fields from the PDF"""
        fields = {}
        
        # Get all form fields
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            widgets = page.widgets()
            for widget in widgets:
                field_name = widget.field_name
                field_type = widget.field_type
                field_value = widget.field_value
                field_type_name = self._get_field_type_name(field_type)
                field_options = []
                
                # Get options for choice fields (combo and list boxes)
                if field_type in [3, 4]:  # 3 for combo box, 4 for list box
                    try:
                        field_options = widget.choice_values
                    except:
                        field_options = []
                
                fields[field_name] = {
                    "type": field_type,
                    "type_name": field_type_name,
                    "value": field_value,
                    "page": page_num,
                    "options": field_options,
                    "rect": [round(c, 2) for c in widget.rect]
                }
        
        # Save to file if requested
        if save_to_file:
            # Save as JSON
            json_output = os.path.join(self.output_dir, "pdf_fields.json")
            with open(json_output, "w") as f:
                json.dump(fields, f, indent=2)
            logger.info(f"Extracted {len(fields)} fields to JSON: {json_output}")
            
            # Save as text
            txt_output = os.path.join(self.output_dir, "pdf_fields.txt")
            with open(txt_output, "w") as f:
                for field_name, field_info in fields.items():
                    f.write(f"Field Name: {field_name}\n")
                    f.write(f"Field Type: {field_info['type_name']}\n")
                    f.write(f"Current Value: {field_info['value']}\n")
                    f.write(f"Page: {field_info['page']}\n")
                    if field_info['options']:
                        f.write(f"Options: {', '.join(field_info['options'])}\n")
                    f.write(f"Rectangle: {field_info['rect']}\n")
                    f.write("-" * 50 + "\n")
            logger.info(f"Extracted {len(fields)} fields to text: {txt_output}")
        
        return fields
    
    def _get_field_type_name(self, field_type):
        """Convert field type number to string name"""
        type_names = {
            0: "Text",          # Text field
            1: "Checkbox",      # Checkbox
            2: "Button",        # Button
            3: "Combobox",      # Combo box
            4: "Listbox",       # List box
            5: "RadioButton",   # Radio button
            6: "Signature"      # Signature
        }
        return type_names.get(field_type, f"Unknown ({field_type})")
    
    def parse_variables(self, variables_text):
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
    
    def map_variable_to_field(self, var_name, fields):
        """Map a variable name to a PDF field name"""
        # Basic pattern matching
        patterns = {
            "First Name": ["first", "firstname", "first_name", "fname"],
            "Middle Name": ["middle", "middlename", "middle_name", "mname"],
            "Last Name": ["last", "lastname", "last_name", "lname", "surname"],
            "Name": ["name", "full_name", "fullname"],
            "Suffix": ["suffix", "name_suffix"],
            "SSN": ["ssn", "social", "socialsecurity", "social_security"],
            "DOB": ["dob", "birth", "birthdate", "birth_date", "date_of_birth"],
            "Address": ["address", "street", "street_address", "addr"],
            "City": ["city", "town"],
            "State": ["state", "province"],
            "Zip": ["zip", "zipcode", "zip_code", "postal", "postal_code"],
            "Phone": ["phone", "telephone", "cell", "mobile"],
            "Email": ["email", "e-mail", "emailaddress", "email_address"],
            "Marital Status": ["marital", "marital_status"],
            "Employer": ["employer", "company", "business"],
            "Job Title": ["title", "job", "position", "occupation"],
            "Income": ["income", "salary", "wage", "earnings", "pay"],
            "Loan": ["loan", "mortgage", "debt"],
            "Gender": ["gender", "sex"]
        }
        
        # Clean up variable name for matching
        var_clean = var_name.lower()
        
        # Try direct matches first
        for field_name in fields.keys():
            field_clean = field_name.lower()
            
            # Exact match
            if var_clean == field_clean:
                return field_name
            
            # Field contains variable name exactly
            if var_clean in field_clean:
                return field_name
            
            # Variable contains field name exactly
            if field_clean in var_clean:
                return field_name
        
        # Try pattern matching
        for pattern_key, pattern_values in patterns.items():
            if any(pattern in var_clean for pattern in pattern_values):
                for field_name in fields.keys():
                    field_clean = field_name.lower()
                    if any(pattern in field_clean for pattern in pattern_values):
                        return field_name
        
        # No match found
        return None
    
    def format_value(self, var_name, value, field_type=None):
        """Format the value based on variable name and field type"""
        # Format date of birth if in YYYY-MM-DD format
        if "date" in var_name.lower() or "dob" in var_name.lower() or "birth" in var_name.lower():
            if re.match(r'\d{4}-\d{2}-\d{2}', value):
                try:
                    date_obj = datetime.strptime(value, '%Y-%m-%d')
                    return date_obj.strftime('%m/%d/%Y')
                except ValueError:
                    pass
        
        # Format SSN if in XXX-XX-XXXX format
        if "ssn" in var_name.lower() or "social" in var_name.lower():
            if re.match(r'\d{3}-\d{2}-\d{4}', value):
                return value.replace('-', '')
        
        # Format income values
        if "income" in var_name.lower() or "salary" in var_name.lower():
            # Remove $ and commas
            value = value.replace('$', '').replace(',', '')
            # Extract the numeric part
            match = re.search(r'(\d+(\.\d+)?)', value)
            if match:
                return match.group(1)
        
        # Handle employment date that's described in words
        if "employment" in var_name.lower() and "date" in var_name.lower() and any(x in value.lower() for x in ["year", "month"]):
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
                    month=max(1, current_date.month - months) if months < current_date.month else 12 - (months - current_date.month),
                    day=min(current_date.day, 28)  # Avoid month boundary issues
                )
                
                return start_date.strftime('%m/%d/%Y')
            except (ValueError, AttributeError):
                pass
        
        # For checkbox/radio button fields, try to map values to appropriate states
        if field_type in [1, 5]:  # 1 for checkbox, 5 for radio button
            if value.lower() in ["yes", "true", "on", "checked"]:
                return True
            elif value.lower() in ["no", "false", "off", "unchecked"]:
                return False
        
        # Return the original value if no special formatting is needed
        return value
    
    def fill_form(self, variables, confidence_threshold=80, output_filename=None):
        """Fill the PDF form with the provided variables above the confidence threshold"""
        # Extract the fields if not already done
        fields = self.extract_fields(save_to_file=False)
        
        # Keep track of filled fields and unmapped variables
        filled_fields = []
        unmapped_variables = []
        
        # Map variables to fields and fill them
        for var_name, var_info in variables.items():
            # Skip if confidence is below threshold
            if var_info['confidence'] < confidence_threshold:
                logger.info(f"Skipping {var_name} due to low confidence: {var_info['confidence']}%")
                continue
            
            # Skip if value is "Not Found"
            if var_info['value'] == "Not Found":
                logger.info(f"Skipping {var_name} with value 'Not Found'")
                continue
                
            # Find matching PDF field
            pdf_field_name = self.map_variable_to_field(var_name, fields)
            
            if pdf_field_name:
                field_info = fields[pdf_field_name]
                field_type = field_info["type"]
                
                # Format the value appropriately
                formatted_value = self.format_value(var_name, var_info['value'], field_type)
                
                # Find the widget on the correct page
                page_num = field_info["page"]
                page = self.doc[page_num]
                
                for widget in page.widgets():
                    if widget.field_name == pdf_field_name:
                        try:
                            widget.field_value = formatted_value
                            widget.update()
                            
                            filled_fields.append({
                                "variable": var_name,
                                "pdf_field": pdf_field_name,
                                "value": formatted_value,
                                "confidence": var_info['confidence'],
                                "page": page_num
                            })
                            logger.info(f"Filled field '{pdf_field_name}' with value '{formatted_value}' (from variable '{var_name}')")
                            break
                        except Exception as e:
                            logger.error(f"Error filling field '{pdf_field_name}': {e}")
            else:
                unmapped_variables.append({
                    "variable": var_name,
                    "value": var_info['value'],
                    "confidence": var_info['confidence']
                })
                logger.warning(f"Could not map variable '{var_name}' to any PDF field")
        
        # Save the filled PDF
        if output_filename:
            output_path = os.path.join(self.output_dir, output_filename)
        else:
            base_name = os.path.basename(self.pdf_path)
            output_path = os.path.join(self.output_dir, f"filled_{base_name}")
        
        self.doc.save(output_path)
        logger.info(f"Saved filled PDF to: {output_path}")
        
        # Save a report
        report = {
            "filled_fields": filled_fields,
            "unmapped_variables": unmapped_variables,
            "total_variables": len(variables),
            "matched_variables": len(filled_fields),
            "unmatched_variables": len(unmapped_variables),
            "confidence_threshold": confidence_threshold
        }
        
        report_path = os.path.join(self.output_dir, "fill_report.json")
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        logger.info(f"Saved report to: {report_path}")
        
        # Print summary
        print(f"\nFilled {len(filled_fields)} out of {len(variables)} variables with confidence >= {confidence_threshold}%")
        print(f"  - {len(unmapped_variables)} variables could not be mapped to PDF fields")
        
        summary_txt_path = os.path.join(self.output_dir, "summary.txt")
        with open(summary_txt_path, "w") as f:
            f.write(f"PDF Form Processing Summary\n")
            f.write(f"=========================\n\n")
            f.write(f"Input PDF: {self.pdf_path}\n")
            f.write(f"Output PDF: {output_path}\n\n")
            f.write(f"Fields in PDF: {len(fields)}\n")
            f.write(f"Variables provided: {len(variables)}\n")
            f.write(f"Confidence threshold: {confidence_threshold}%\n\n")
            f.write(f"Results:\n")
            f.write(f"- Fields filled: {len(filled_fields)}\n")
            f.write(f"- Variables not mapped: {len(unmapped_variables)}\n\n")
            
            f.write(f"Field Mappings:\n")
            for field in filled_fields:
                f.write(f"- '{field['variable']}' -> '{field['pdf_field']}' = '{field['value']}' ({field['confidence']}%)\n")
            
            if unmapped_variables:
                f.write(f"\nUnmapped Variables:\n")
                for var in unmapped_variables:
                    f.write(f"- '{var['variable']}' = '{var['value']}' ({var['confidence']}%)\n")
        
        return report

def main():
    """Main function to run the script"""
    # Make sure we have PyMuPDF installed
    try:
        import fitz
    except ImportError:
        print("PyMuPDF is not installed. Please install it with 'pip install pymupdf'")
        sys.exit(1)
    
    # Get the PDF path
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        pdf_path = "Experiment/uniform_residential_loan_application.pdf"
    
    # Create output directory if needed
    output_dir = os.path.join(os.path.dirname(pdf_path), "output")
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize processor
    processor = PDFFormProcessor(pdf_path, output_dir)
    
    # Extract fields first
    fields = processor.extract_fields()
    print(f"Extracted {len(fields)} fields from {pdf_path}")
    
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
    variables = processor.parse_variables(variables_text)
    
    # Fill the form
    processor.fill_form(variables, confidence_threshold=80, output_filename="filled_uniform_residential_loan_application.pdf")

if __name__ == "__main__":
    main() 