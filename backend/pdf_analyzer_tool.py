#!/usr/bin/env python
"""
PDF Analyzer Tool for FormsIQ

This command-line tool provides a comprehensive interface to:
1. Analyze and extract information from fillable PDF forms
2. Test PDF field mapping
3. Fill PDF forms with test or real data
4. Generate and manage field mappings

Usage examples:
    python pdf_analyzer_tool.py analyze path/to/form.pdf
    python pdf_analyzer_tool.py map path/to/form.pdf path/to/fields.json
    python pdf_analyzer_tool.py fill path/to/form.pdf path/to/data.json
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional

# Import our enhanced PDF handlers
from enhanced_pdf_handler import PDFAnalyzer, PDFFiller
from ai_field_mapper import AIFieldMapper

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def analyze_pdf(args):
    """
    Analyze a PDF form and extract field information
    """
    pdf_path = args.pdf_file
    output_file = args.output_file
    include_areas = args.areas
    
    try:
        analyzer = PDFAnalyzer(pdf_path)
        field_count = len(analyzer.get_field_names())
        
        print(f"\n=== PDF Form Analysis ===")
        print(f"PDF file: {pdf_path}")
        print(f"Total fields: {field_count}")
        
        # Get field categories
        categories = analyzer.categorize_fields()
        print("\nField types:")
        for category, fields in categories.items():
            if fields:
                print(f"  {category}: {len(fields)} fields")
                
        # Export field information
        if not output_file:
            output_file = os.path.splitext(pdf_path)[0] + "_fields_info.json"
            
        fields_info = analyzer.get_all_fields_info()
        
        # Add field areas if requested
        if include_areas:
            print("\nAttempting to extract field coordinates (experimental)...")
            pdf_filler = PDFFiller(pdf_path)
            areas = pdf_filler.get_form_areas()
            
            if areas:
                print(f"Found coordinates for {len(areas)} fields")
                for field_name, field_info in fields_info.items():
                    if field_name in areas:
                        field_info['area'] = areas[field_name]
            else:
                print("Could not extract field coordinates")
                
        # Save to file
        with open(output_file, 'w') as f:
            json.dump(fields_info, f, indent=2)
            
        print(f"\nField information exported to: {output_file}")
        
        # Print sample fields
        sample_count = min(5, field_count)
        if sample_count > 0:
            print(f"\nSample of {sample_count} fields:")
            for i, field_name in enumerate(list(fields_info.keys())[:sample_count]):
                field = fields_info[field_name]
                print(f"  {i+1}. {field_name} ({field['type']}/{field['subtype']})")
                if field['options']:
                    print(f"     Options: {', '.join(field['options'])}")
                if field['required']:
                    print(f"     Required: Yes")
                if field['max_length']:
                    print(f"     Max length: {field['max_length']}")
                    
        return 0
        
    except Exception as e:
        print(f"\nError analyzing PDF: {str(e)}")
        return 1


def map_fields(args):
    """
    Generate and test field mapping between extracted fields and PDF form fields
    """
    pdf_path = args.pdf_file
    fields_json = args.fields_json
    output_file = args.output_file
    threshold = args.threshold
    
    try:
        # Load fields data from JSON
        with open(fields_json, 'r') as f:
            fields_data = json.load(f)
            
        # Extract field names from the data
        if isinstance(fields_data, list):
            # Assume it's a list of field objects
            field_names = [item['field_name'] for item in fields_data if 'field_name' in item]
        elif isinstance(fields_data, dict) and 'fields' in fields_data:
            # Assume it's an object with a 'fields' property
            field_names = [item['field_name'] for item in fields_data['fields'] if 'field_name' in item]
        else:
            # Assume it's a dictionary with field names as keys
            field_names = list(fields_data.keys())
            
        if not field_names:
            print(f"No valid field names found in {fields_json}")
            return 1
            
        print(f"\n=== Field Mapping Analysis ===")
        print(f"PDF file: {pdf_path}")
        print(f"Fields file: {fields_json}")
        print(f"Found {len(field_names)} fields to map")
        
        # Create mapper and generate mapping
        mapper = AIFieldMapper(pdf_path, min_score=threshold)
        mapping = mapper.generate_mapping(field_names)
        
        # Generate and save report
        report = mapper.get_mapping_report()
        
        print(f"\nMapping results:")
        print(f"  Total PDF fields: {report['total_pdf_fields']}")
        print(f"  Fields mapped: {report['total_mapped']}")
        print(f"  Coverage: {report['coverage_percentage']}%")
        
        # Save mapping if requested
        if output_file:
            mapper.save_mapping(output_file)
            print(f"\nMapping saved to: {output_file}")
            
        # Print a sample of the mappings
        sample_count = min(10, len(mapping))
        if sample_count > 0:
            print(f"\nSample of {sample_count} mappings:")
            for i, (source, target) in enumerate(list(mapping.items())[:sample_count]):
                print(f"  {i+1}. {source} -> {target}")
                
        return 0
        
    except Exception as e:
        print(f"\nError generating field mapping: {str(e)}")
        return 1


def fill_pdf(args):
    """
    Fill a PDF form with provided data
    """
    pdf_path = args.pdf_file
    data_json = args.data_json
    mapping_json = args.mapping_json
    output_file = args.output_file
    
    try:
        # Load data from JSON
        with open(data_json, 'r') as f:
            data = json.load(f)
            
        # Load field mapping if provided
        field_mapping = None
        if mapping_json and os.path.exists(mapping_json):
            with open(mapping_json, 'r') as f:
                field_mapping = json.load(f)
                print(f"Loaded mapping with {len(field_mapping)} entries from {mapping_json}")
        
        # Make sure data is in the right format
        if not isinstance(data, list):
            if isinstance(data, dict) and 'fields' in data:
                data = data['fields']
            else:
                # Convert from dictionary format to list format
                data = [{"field_name": k, "field_value": v, "confidence_score": 1.0} 
                       for k, v in data.items()]
                
        # Fill the PDF
        print(f"\n=== Filling PDF Form ===")
        print(f"PDF template: {pdf_path}")
        print(f"Data source: {data_json}")
        print(f"Processing {len(data)} data fields")
        
        filler = PDFFiller(pdf_path)
        filled_pdf_path = filler.fill_form(
            data=data,
            field_mapping=field_mapping,
            validation=True
        )
        
        # Copy to the desired output location if specified
        if output_file:
            # Make sure the directory exists
            output_dir = os.path.dirname(output_file)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
                
            with open(filled_pdf_path, 'rb') as src, open(output_file, 'wb') as dst:
                dst.write(src.read())
            filled_pdf_path = output_file
            
        print(f"\nFilled PDF saved to: {filled_pdf_path}")
        return 0
        
    except Exception as e:
        print(f"\nError filling PDF: {str(e)}")
        return 1


def generate_sample_data(args):
    """
    Generate sample data for testing PDF filling
    """
    pdf_path = args.pdf_file
    output_file = args.output_file
    count = args.count
    
    try:
        analyzer = PDFAnalyzer(pdf_path)
        fields_info = analyzer.get_all_fields_info()
        
        # Generate sample data
        sample_data = []
        
        # Use the first 'count' fields or all if count is larger
        field_count = min(count, len(fields_info))
        field_names = list(fields_info.keys())[:field_count]
        
        for field_name in field_names:
            field_info = fields_info[field_name]
            field_type = field_info['type']
            
            # Generate a sample value based on field type
            sample_value = None
            
            if field_type == 'text':
                if 'name' in field_name.lower():
                    sample_value = "John Doe"
                elif 'email' in field_name.lower():
                    sample_value = "john.doe@example.com"
                elif 'phone' in field_name.lower():
                    sample_value = "(555) 123-4567"
                elif 'date' in field_name.lower():
                    sample_value = datetime.now().strftime("%Y-%m-%d")
                elif 'address' in field_name.lower():
                    sample_value = "123 Main Street"
                elif 'city' in field_name.lower():
                    sample_value = "New York"
                elif 'state' in field_name.lower():
                    sample_value = "NY"
                elif 'zip' in field_name.lower():
                    sample_value = "10001"
                elif 'social' in field_name.lower() or 'ssn' in field_name.lower():
                    sample_value = "123-45-6789"
                else:
                    sample_value = f"Sample value for {field_name}"
                    
            elif field_type == 'button':
                if field_info['subtype'] == 'checkbox':
                    sample_value = True
                elif field_info['subtype'] == 'radio':
                    sample_value = True
                    
            elif field_type == 'choice':
                if field_info['options']:
                    sample_value = field_info['options'][0]
                    
            # Add to sample data if we have a value
            if sample_value is not None:
                sample_data.append({
                    "field_name": field_name,
                    "field_value": sample_value,
                    "confidence_score": 0.95
                })
                
        # Save sample data
        if not output_file:
            output_file = os.path.splitext(pdf_path)[0] + "_sample_data.json"
            
        with open(output_file, 'w') as f:
            json.dump(sample_data, f, indent=2)
            
        print(f"\n=== Sample Data Generation ===")
        print(f"PDF file: {pdf_path}")
        print(f"Generated sample data for {len(sample_data)} fields")
        print(f"Sample data saved to: {output_file}")
        
        return 0
        
    except Exception as e:
        print(f"\nError generating sample data: {str(e)}")
        return 1


def main():
    """Main entry point for the PDF analyzer tool"""
    parser = argparse.ArgumentParser(
        description="PDF Analyzer Tool for FormsIQ",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python pdf_analyzer_tool.py analyze form.pdf
  python pdf_analyzer_tool.py map form.pdf fields.json
  python pdf_analyzer_tool.py fill form.pdf data.json --mapping mapping.json
  python pdf_analyzer_tool.py sample form.pdf --count 10""")
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze a PDF form')
    analyze_parser.add_argument('pdf_file', help='Path to the PDF form')
    analyze_parser.add_argument('-o', '--output', dest='output_file', help='Output file for field information')
    analyze_parser.add_argument('--areas', action='store_true', help='Try to extract field areas (experimental)')
    
    # Map command
    map_parser = subparsers.add_parser('map', help='Generate field mapping')
    map_parser.add_argument('pdf_file', help='Path to the PDF form')
    map_parser.add_argument('fields_json', help='Path to JSON file with field names')
    map_parser.add_argument('-o', '--output', dest='output_file', help='Output file for field mapping')
    map_parser.add_argument('-t', '--threshold', type=float, default=0.6, help='Threshold for fuzzy matching (0-1)')
    
    # Fill command
    fill_parser = subparsers.add_parser('fill', help='Fill a PDF form with data')
    fill_parser.add_argument('pdf_file', help='Path to the PDF form')
    fill_parser.add_argument('data_json', help='Path to JSON file with data to fill')
    fill_parser.add_argument('-m', '--mapping', dest='mapping_json', help='Path to field mapping JSON file')
    fill_parser.add_argument('-o', '--output', dest='output_file', help='Output file for filled PDF')
    
    # Sample command
    sample_parser = subparsers.add_parser('sample', help='Generate sample data for testing')
    sample_parser.add_argument('pdf_file', help='Path to the PDF form')
    sample_parser.add_argument('-o', '--output', dest='output_file', help='Output file for sample data')
    sample_parser.add_argument('-c', '--count', type=int, default=20, help='Number of fields to include in sample data')
    
    args = parser.parse_args()
    
    # Run the appropriate command
    if args.command == 'analyze':
        return analyze_pdf(args)
    elif args.command == 'map':
        return map_fields(args)
    elif args.command == 'fill':
        return fill_pdf(args)
    elif args.command == 'sample':
        return generate_sample_data(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main()) 