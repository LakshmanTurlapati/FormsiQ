#!/usr/bin/env python
"""
AI Field Format Guide

This script helps generate a format guide for the AI parsing component based on the 
PDF field structure in the uniform_residential_loan_application.pdf form.

The guide includes:
1. A list of all fields in the PDF form with their types and descriptive names
2. Guidelines for how the AI parser should format its output
3. Examples of correctly formatted output data
"""

import os
import sys
import json
from pathlib import Path
import argparse

# Add api_processor directory to the Python path
current_dir = Path(__file__).resolve().parent
api_processor_dir = current_dir / 'api_processor'
if str(api_processor_dir) not in sys.path:
    sys.path.append(str(api_processor_dir))

# Import modules
from api_processor.pdf_field_processor import PDFFieldProcessor
from api_processor.field_mapping import LLM_TO_PDF_FIELD_MAP

# PDF template path
PDF_TEMPLATE_PATH = os.path.join(current_dir, 'media', 'pdf', 'uniform_residential_loan_application.pdf')
# Output file paths
OUTPUT_DIR = os.path.join(current_dir, 'media', 'pdf')
FIELD_GUIDE_PATH = os.path.join(OUTPUT_DIR, 'ai_parser_field_guide.md')
FIELD_SCHEMA_PATH = os.path.join(OUTPUT_DIR, 'ai_parser_field_schema.json')


def parse_command_line():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Generate AI Field Format Guide')
    parser.add_argument('--output', '-o', type=str, default=FIELD_GUIDE_PATH, help='Path for the output guide file')
    parser.add_argument('--schema', '-s', type=str, default=FIELD_SCHEMA_PATH, help='Path for the output schema file')
    parser.add_argument('--template', '-t', type=str, default=PDF_TEMPLATE_PATH, help='Path to the PDF template')
    return parser.parse_args()


def generate_field_guide(processor, output_path, schema_path):
    """
    Generate a comprehensive field guide for the AI parser based on PDF form fields
    
    Args:
        processor: PDFFieldProcessor instance
        output_path: Path to write the field guide
        schema_path: Path to write the field schema
    """
    fields_info = processor.extract_fields_info()
    
    # Organize fields by type
    field_types = {
        'text': [],
        'checkbox': [],
        'radio': {},
        'dropdown': []
    }
    
    # Keep track of inferred LLM field names based on field mapping (reverse mapping)
    pdf_to_llm_field_map = {}
    for llm_field, pdf_field in LLM_TO_PDF_FIELD_MAP.items():
        if pdf_field not in pdf_to_llm_field_map:
            pdf_to_llm_field_map[pdf_field] = llm_field
    
    # Process all radio button groups first to organize them
    radio_groups = {}
    for pdf_key, field_info in fields_info.items():
        if field_info['field_type'] == '/Btn' and 'kids' in field_info and field_info['kids']:
            # It's a radio button group
            group_name = field_info.get('name', pdf_key)
            radio_groups[pdf_key] = {
                'name': group_name,
                'options': []
            }
            
            # Handle kids whether it's a list or dictionary
            if isinstance(field_info['kids'], dict):
                # Dictionary format
                for kid_ref, kid_info in field_info['kids'].items():
                    option_name = kid_info.get('name', kid_ref)
                    option_state = kid_info.get('on_state', '/Yes')
                    
                    radio_groups[pdf_key]['options'].append({
                        'name': option_name,
                        'value': option_state,
                        'pdf_key': kid_ref
                    })
            else:
                # List format
                for kid_idx, kid_info in enumerate(field_info['kids']):
                    option_name = kid_info.get('name', f'Option_{kid_idx}')
                    option_state = kid_info.get('on_state', '/Yes')
                    
                    radio_groups[pdf_key]['options'].append({
                        'name': option_name,
                        'value': option_state,
                        'pdf_key': f'{pdf_key}_option_{kid_idx}'
                    })
    
    # Now process all fields and organize them
    for pdf_key, field_info in fields_info.items():
        field_type = field_info['field_type']
        field_name = field_info.get('name', pdf_key)
        
        # Map to LLM field name if available
        llm_field_name = pdf_to_llm_field_map.get(pdf_key, field_name)
        
        if field_type == '/Tx':  # Text field
            field_types['text'].append({
                'pdf_key': pdf_key,
                'name': field_name,
                'llm_name': llm_field_name
            })
        elif field_type == '/Btn' and ('kids' not in field_info or not field_info['kids']):  # Checkbox
            on_value = field_info.get('on_state', '/Yes')
            field_types['checkbox'].append({
                'pdf_key': pdf_key,
                'name': field_name,
                'llm_name': llm_field_name,
                'on_value': on_value
            })
        elif field_type == '/Ch':  # Choice/dropdown
            options = field_info.get('options', [])
            field_types['dropdown'].append({
                'pdf_key': pdf_key,
                'name': field_name,
                'llm_name': llm_field_name,
                'options': options
            })
    
    # Map radio groups to field_types
    for group_key, group_info in radio_groups.items():
        group_name = group_info['name']
        field_types['radio'][group_key] = {
            'name': group_name,
            'options': group_info['options']
        }
    
    # Generate JSON schema for the expected field format
    schema = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "field_name": {
                    "type": "string",
                    "description": "The name of the field (must match exactly one of the field names listed in the guide)"
                },
                "value": {
                    "oneOf": [
                        {"type": "string"},
                        {"type": "number"},
                        {"type": "boolean"}
                    ],
                    "description": "The field value. For checkboxes use 'Yes'/'No', for radio buttons use the syntax 'Group Name: Option'"
                },
                "confidence": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 100,
                    "description": "A confidence score from 0-100 indicating how confident the AI is in this extraction"
                }
            },
            "required": ["field_name", "value", "confidence"]
        }
    }

    # Write the schema
    with open(schema_path, 'w') as f:
        json.dump(schema, f, indent=2)
    
    # Generate the field guide markdown
    with open(output_path, 'w') as f:
        f.write("# AI Parser Field Guide for Uniform Residential Loan Application\n\n")
        f.write("This guide lists all fields in the PDF form and how to format the extraction output.\n\n")
        
        f.write("## Output Format\n\n")
        f.write("The AI parser should output a JSON array of objects with the following structure:\n\n")
        f.write("```json\n")
        f.write("[\n")
        f.write("  {\n")
        f.write("    \"field_name\": \"Field Name\",\n")
        f.write("    \"value\": \"Field Value\",\n")
        f.write("    \"confidence\": 90\n")
        f.write("  },\n")
        f.write("  ...\n")
        f.write("]\n")
        f.write("```\n\n")
        
        f.write("## Field Value Formats\n\n")
        f.write("- **Text Fields**: Plain text values\n")
        f.write("- **Checkbox Fields**: Use `Yes` or `No` as the value\n")
        f.write("- **Radio Buttons**: Use the format `Group Name: Option Name` as the field name with `Yes` as the value\n")
        f.write("- **Dropdown Fields**: Use the exact option text from the available options\n\n")
        
        # Text Fields
        f.write("## Text Fields\n\n")
        f.write("| Field Name | PDF Field Key |\n")
        f.write("|------------|-------------|\n")
        for field in field_types['text']:
            f.write(f"| {field['llm_name']} | {field['pdf_key']} |\n")
        f.write("\n")
        
        # Checkbox Fields
        f.write("## Checkbox Fields\n\n")
        f.write("| Field Name | PDF Field Key | Expected 'Yes' Value |\n")
        f.write("|------------|-------------|-------------------|\n")
        for field in field_types['checkbox']:
            f.write(f"| {field['llm_name']} | {field['pdf_key']} | Yes |\n")
        f.write("\n")
        
        # Radio Button Groups
        f.write("## Radio Button Groups\n\n")
        for group_key, group_info in field_types['radio'].items():
            f.write(f"### Group: {group_info['name']}\n\n")
            f.write("| Option Format | PDF Key | Value When Selected |\n")
            f.write("|---------------|---------|--------------------|\n")
            for option in group_info['options']:
                formatted_option = f"{group_info['name']}: {option['name']}"
                f.write(f"| {formatted_option} | {group_key} | Yes |\n")
            f.write("\n")
        
        # Dropdown Fields
        if field_types['dropdown']:
            f.write("## Dropdown Fields\n\n")
            for field in field_types['dropdown']:
                f.write(f"### {field['llm_name']} (PDF Key: {field['pdf_key']})\n\n")
                f.write("Available options:\n\n")
                for option in field['options']:
                    f.write(f"- {option}\n")
                f.write("\n")
        
        # Examples
        f.write("## Examples\n\n")
        f.write("### Text Field Example\n")
        f.write("```json\n")
        f.write("{\n")
        f.write("  \"field_name\": \"Borrower Name\",\n")
        f.write("  \"value\": \"John Smith\",\n")
        f.write("  \"confidence\": 95\n")
        f.write("}\n")
        f.write("```\n\n")
        
        f.write("### Checkbox Example\n")
        f.write("```json\n")
        f.write("{\n")
        f.write("  \"field_name\": \"Borrower Self Employed\",\n")
        f.write("  \"value\": \"Yes\",\n")
        f.write("  \"confidence\": 90\n")
        f.write("}\n")
        f.write("```\n\n")
        
        f.write("### Radio Button Example\n")
        f.write("```json\n")
        f.write("{\n")
        f.write("  \"field_name\": \"Purpose of Loan: Purchase\",\n")
        f.write("  \"value\": \"Yes\",\n")
        f.write("  \"confidence\": 95\n")
        f.write("}\n")
        f.write("```\n\n")
        
        if field_types['dropdown']:
            f.write("### Dropdown Example\n")
            f.write("```json\n")
            f.write("{\n")
            f.write("  \"field_name\": \"Dropdown Field Name\",\n")
            f.write("  \"value\": \"Option Value\",\n")
            f.write("  \"confidence\": 85\n")
            f.write("}\n")
            f.write("```\n\n")
        
        f.write("## Complete Field List\n\n")
        f.write("Here is a complete list of all fields in the PDF form:\n\n")
        f.write("```\n")
        for pdf_key, field_info in fields_info.items():
            field_type = field_info['field_type']
            field_name = field_info.get('name', pdf_key)
            f.write(f"{pdf_key} ({field_type}): {field_name}\n")
        f.write("```\n")


def main():
    """Main function"""
    args = parse_command_line()
    
    # Initialize the PDF processor
    try:
        processor = PDFFieldProcessor(args.template)
    except FileNotFoundError:
        print(f"Error: PDF template not found at {args.template}")
        return 1
    except Exception as e:
        print(f"Error initializing PDF processor: {e}")
        return 1
    
    # Generate the field guide
    generate_field_guide(processor, args.output, args.schema)
    
    print("AI Field Format Guide generation completed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main()) 