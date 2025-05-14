#!/usr/bin/env python
"""
PDF Field Analyzer for FormsIQ

This script analyzes a PDF form and extracts detailed information about all the fillable fields.
"""
import os
import sys
import json
import logging
from typing import Dict, List, Any, Optional

# Add the backend directory to the Python path if needed
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.append(script_dir)

from enhanced_pdf_handler import PDFAnalyzer

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def analyze_pdf_fields(pdf_path: str, output_path: str = None) -> Dict[str, Any]:
    """
    Analyze a PDF form and extract all field information.
    
    Args:
        pdf_path: Path to the PDF form
        output_path: Optional path to save the results
        
    Returns:
        Dictionary with field information
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    analyzer = PDFAnalyzer(pdf_path)
    
    # Get all field information
    fields_info = analyzer.get_all_fields_info()
    
    # Add metadata about the analysis
    result = {
        "pdf_path": pdf_path,
        "total_fields": len(fields_info),
        "fields": fields_info
    }
    
    # Save results if an output path is provided
    if output_path:
        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2)
    
    return result

def print_field_summary(field_info: Dict[str, Any]) -> None:
    """Print a summary of the field information"""
    print(f"\nPDF Field Analysis Summary")
    print(f"==========================")
    print(f"PDF File: {field_info['pdf_path']}")
    print(f"Total Fields: {field_info['total_fields']}")
    
    # Categorize fields by type
    field_types = {}
    for name, info in field_info['fields'].items():
        field_type = info['type']
        if field_type not in field_types:
            field_types[field_type] = []
        field_types[field_type].append(name)
    
    print("\nField Types:")
    for field_type, fields in field_types.items():
        print(f"  {field_type}: {len(fields)} fields")
    
    # Print sample of each field type
    print("\nSample Fields by Type:")
    for field_type, fields in field_types.items():
        print(f"\n  {field_type.capitalize()} Fields ({min(3, len(fields))} of {len(fields)}):")
        for i, name in enumerate(fields[:3]):
            info = field_info['fields'][name]
            print(f"    {i+1}. {name}")
            print(f"       - Current value: {info['current_value']}")
            if field_type == 'text':
                print(f"       - Multiline: {info.get('multiline', 'N/A')}")
                print(f"       - Max length: {info.get('max_length', 'N/A')}")
                print(f"       - Est. char limit: {info.get('estimated_char_limit', 'N/A')}")
            elif field_type == 'choice':
                print(f"       - Options: {', '.join(info.get('options', []))}")

def main():
    """Command-line interface"""
    if len(sys.argv) < 2:
        import argparse
        parser = argparse.ArgumentParser(
            description="Analyze a PDF form and extract field information",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""Examples:
  python pdf_field_analyzer.py form.pdf
  python pdf_field_analyzer.py form.pdf -o fields.json""")
            
        parser.add_argument('pdf_file', help='Path to the PDF form')
        parser.add_argument('-o', '--output', dest='output_file',
                            help='Output file for field information (JSON)')
                            
        args = parser.parse_args()
        
        try:
            result = analyze_pdf_fields(args.pdf_file, args.output_file)
            print_field_summary(result)
            
            if args.output_file:
                print(f"\nField information saved to: {args.output_file}")
                
        except Exception as e:
            print(f"Error analyzing PDF: {str(e)}")
            return 1
            
        return 0
    else:
        try:
            pdf_file = sys.argv[1]
            output_file = sys.argv[2] if len(sys.argv) > 2 else None
            
            result = analyze_pdf_fields(pdf_file, output_file)
            print_field_summary(result)
            
            if output_file:
                print(f"\nField information saved to: {output_file}")
                
        except Exception as e:
            print(f"Error analyzing PDF: {str(e)}")
            return 1
            
        return 0

if __name__ == "__main__":
    sys.exit(main()) 