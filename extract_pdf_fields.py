import os
import fitz  # PyMuPDF
import json

def extract_fillable_fields(pdf_path):
    """Extract all fillable fields from a PDF file"""
    doc = fitz.open(pdf_path)
    fields = {}
    
    # Get all form fields
    for page_num in range(len(doc)):
        page = doc[page_num]
        widgets = page.widgets()
        for widget in widgets:
            field_name = widget.field_name
            field_type = widget.field_type
            field_value = widget.field_value
            
            # Store field info
            fields[field_name] = {
                "type": field_type,
                "value": field_value,
                "page": page_num
            }
    
    return fields

if __name__ == "__main__":
    # Define paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_path = os.path.join(script_dir, "Experiment", "uniform_residential_loan_application.pdf")
    output_txt = os.path.join(script_dir, "pdf_fields.txt")
    
    # Extract fields
    print(f"Extracting fields from: {pdf_path}")
    fields = extract_fillable_fields(pdf_path)
    
    # Write to text file
    with open(output_txt, "w") as f:
        for field_name, field_info in fields.items():
            f.write(f"Field Name: {field_name}\n")
            f.write(f"Field Type: {field_info['type']}\n")
            f.write(f"Current Value: {field_info['value']}\n")
            f.write(f"Page: {field_info['page']}\n")
            f.write("-" * 50 + "\n")
    
    print(f"Extracted {len(fields)} fields to {output_txt}")
    
    # Also save as JSON for easier processing
    json_output = os.path.join(script_dir, "pdf_fields.json")
    with open(json_output, "w") as f:
        json.dump(fields, f, indent=2)
    
    print(f"JSON data saved to {json_output}") 