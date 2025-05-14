#!/usr/bin/env python
"""
Test Transcript Field Extraction and Mapping for FormsIQ

This script tests the extraction of fields from a transcript file and maps them
to fields in a PDF form to validate the extraction and mapping process.
"""

import os
import sys
import json
import logging
from typing import Dict, List, Any, Tuple, Optional

# Add the backend directory to the Python path if needed
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.append(script_dir)

# Import our custom modules
from extract_transcript_fields import analyze_transcript, extract_to_flat_list
from ai_field_mapper import AIFieldMapper
from enhanced_pdf_handler import PDFAnalyzer, PDFFiller

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_extraction_and_mapping(transcript_path: str, pdf_path: str, output_path: Optional[str] = None) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Test the extraction of fields from a transcript and mapping to PDF form fields
    
    Args:
        transcript_path: Path to the transcript file
        pdf_path: Path to the PDF form
        output_path: Optional path to save the results
        
    Returns:
        Tuple of (extracted_fields, field_mapping)
    """
    # Extract fields from transcript
    logger.info(f"Extracting fields from transcript: {transcript_path}")
    with open(transcript_path, 'r') as f:
        transcript = f.read()
    
    extracted_fields = extract_to_flat_list(transcript)
    
    # Analyze PDF form fields
    logger.info(f"Analyzing PDF form fields: {pdf_path}")
    pdf_analyzer = PDFAnalyzer(pdf_path)
    pdf_fields = pdf_analyzer.get_field_names()
    
    # Create values dictionary for checkbox processing
    extracted_values = {field['field_name']: field['field_value'] for field in extracted_fields}
    
    # Map extracted fields to PDF fields
    logger.info("Mapping extracted fields to PDF form fields")
    mapper = AIFieldMapper(pdf_path, min_score=0.5)  # Lower threshold for testing
    field_mapping = mapper.generate_mapping(
        [f['field_name'] for f in extracted_fields],
        extracted_values=extracted_values
    )
    
    # Create a friendly report
    report = {
        "extracted_fields": extracted_fields,
        "pdf_fields": pdf_fields,
        "field_mapping": field_mapping,
        "checkbox_fields": [k for k in field_mapping if k.startswith("checkbox:")],
        "mapping_stats": {
            "total_extracted": len(extracted_fields),
            "total_pdf_fields": len(pdf_fields),
            "successfully_mapped": len([k for k in field_mapping if not k.startswith("checkbox:")]),
            "checkbox_fields_mapped": len([k for k in field_mapping if k.startswith("checkbox:")]),
            "mapping_rate": round(len([k for k in field_mapping if not k.startswith("checkbox:")]) / len(extracted_fields) * 100, 2) if extracted_fields else 0,
            "pdf_coverage": round((len([k for k in field_mapping if not k.startswith("checkbox:")]) + 
                                  len([k for k in field_mapping if k.startswith("checkbox:")])) / len(pdf_fields) * 100, 2) if pdf_fields else 0
        },
        "unmapped_extracted_fields": [f['field_name'] for f in extracted_fields if f['field_name'] not in field_mapping],
        "unmapped_pdf_fields": [f for f in pdf_fields if f not in field_mapping.values() and 
                               not any(k.startswith(f"checkbox:{f}") for k in field_mapping)]
    }
    
    # Save results if output path provided
    if output_path:
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        logger.info(f"Results saved to: {output_path}")
    
    # Print summary
    print("\n=== Extraction and Mapping Results ===")
    print(f"Total fields extracted from transcript: {len(extracted_fields)}")
    print(f"Total fields in PDF form: {len(pdf_fields)}")
    print(f"Successfully mapped text fields: {report['mapping_stats']['successfully_mapped']}")
    print(f"Successfully mapped checkbox fields: {report['mapping_stats']['checkbox_fields_mapped']}")
    print(f"Mapping rate: {report['mapping_stats']['mapping_rate']}%")
    print(f"PDF coverage: {report['mapping_stats']['pdf_coverage']}%")
    
    print("\n=== Some Example Text Field Mappings ===")
    for i, (src, tgt) in enumerate([(k, v) for k, v in field_mapping.items() if not k.startswith("checkbox:")]):
        if i < 5:  # Show first 5 mappings
            print(f"  {src} -> {tgt}")
    
    print("\n=== Some Example Checkbox Mappings ===")
    for i, (src, tgt) in enumerate([(k, v) for k, v in field_mapping.items() if k.startswith("checkbox:")]):
        if i < 5:  # Show first 5 mappings
            # Remove checkbox: prefix for display
            clean_src = src.replace("checkbox:", "")
            print(f"  {clean_src} -> {tgt}")
    
    return extracted_fields, field_mapping

def fill_test_pdf(transcript_path: str, pdf_path: str, output_pdf_path: str) -> str:
    """
    Extract fields from a transcript, map them to a PDF, and fill the PDF
    
    Args:
        transcript_path: Path to the transcript file
        pdf_path: Path to the PDF form
        output_pdf_path: Path to save the filled PDF
        
    Returns:
        Path to the filled PDF
    """
    # Extract and map fields
    extracted_fields, field_mapping = test_extraction_and_mapping(transcript_path, pdf_path)
    
    # Prepare data for filling
    fill_data = {}
    
    # Process regular text fields
    for field in extracted_fields:
        field_name = field['field_name']
        if field_name in field_mapping:
            pdf_field = field_mapping[field_name]
            fill_data[pdf_field] = field['field_value']
    
    # Process checkbox fields
    for key, value in field_mapping.items():
        if key.startswith("checkbox:"):
            checkbox_field = key.replace("checkbox:", "")
            fill_data[checkbox_field] = value
    
    # Fill the PDF
    logger.info(f"Filling PDF form: {pdf_path}")
    pdf_filler = PDFFiller(pdf_path)
    filled_pdf_path = pdf_filler.fill_form(fill_data, output_pdf_path)
    
    logger.info(f"Filled PDF saved to: {filled_pdf_path}")
    return filled_pdf_path

def main():
    """Command-line interface for testing transcript extraction and mapping"""
    if len(sys.argv) < 3:
        print("Usage:")
        print("  To test extraction and mapping:")
        print("    python test_transcript_extraction.py extract <transcript_file> <pdf_file> [output_json]")
        print()
        print("  To fill a PDF form based on a transcript:")
        print("    python test_transcript_extraction.py fill <transcript_file> <pdf_file> <output_pdf>")
        sys.exit(1)
    
    action = sys.argv[1]
    
    if action == "extract":
        if len(sys.argv) < 4:
            print("Missing required arguments for 'extract'")
            print("Usage: python test_transcript_extraction.py extract <transcript_file> <pdf_file> [output_json]")
            sys.exit(1)
            
        transcript_path = sys.argv[2]
        pdf_path = sys.argv[3]
        output_path = sys.argv[4] if len(sys.argv) > 4 else None
        
        test_extraction_and_mapping(transcript_path, pdf_path, output_path)
        
    elif action == "fill":
        if len(sys.argv) < 5:
            print("Missing required arguments for 'fill'")
            print("Usage: python test_transcript_extraction.py fill <transcript_file> <pdf_file> <output_pdf>")
            sys.exit(1)
            
        transcript_path = sys.argv[2]
        pdf_path = sys.argv[3]
        output_pdf_path = sys.argv[4]
        
        fill_test_pdf(transcript_path, pdf_path, output_pdf_path)
        
    else:
        print(f"Unknown action: {action}")
        print("Available actions: extract, fill")
        sys.exit(1)

if __name__ == "__main__":
    main() 