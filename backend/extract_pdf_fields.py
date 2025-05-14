#!/usr/bin/env python
"""
Utility script to extract form field names from a fillable PDF.
This helps in creating the mapping between LLM field names and actual PDF form field names.
"""
import os
import sys
import json
from pypdf import PdfReader

def extract_pdf_fields(pdf_path):
    """Extract field names and types from a fillable PDF."""
    if not os.path.exists(pdf_path):
        print(f"Error: PDF file not found: {pdf_path}")
        sys.exit(1)
        
    try:
        reader = PdfReader(pdf_path)
        fields = reader.get_fields()
        
        if not fields:
            print("No fillable fields found in the PDF.")
            sys.exit(0)
            
        print(f"Found {len(fields)} fillable fields in {pdf_path}\n")
        
        # Print fields in a readable format
        print("Field Name | Field Type | Field Value")
        print("-" * 60)
        
        for name, field in fields.items():
            field_type = field.get('/FT', 'Unknown').replace('/', '')
            field_value = field.get('/V', '')
            print(f"{name} | {field_type} | {field_value}")
            
        # Export fields to a JSON file for easier reference
        output_file = os.path.splitext(pdf_path)[0] + "_fields.json"
        
        # Convert the fields dict to a serializable format
        serializable_fields = {}
        for name, field in fields.items():
            field_dict = {
                "type": str(field.get('/FT', 'Unknown')).replace('/', ''),
                "value": str(field.get('/V', '')),
                "flags": str(field.get('/Ff', '')),
                "options": [str(opt) for opt in field.get('/Opt', [])] if '/Opt' in field else []
            }
            serializable_fields[name] = field_dict
            
        with open(output_file, 'w') as f:
            json.dump(serializable_fields, f, indent=2)
            
        print(f"\nExported field information to {output_file}")
        
    except Exception as e:
        print(f"Error extracting fields: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python extract_pdf_fields.py path/to/form.pdf")
        sys.exit(1)
        
    pdf_path = sys.argv[1]
    extract_pdf_fields(pdf_path) 