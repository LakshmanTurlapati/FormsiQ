#!/usr/bin/env python
"""
Simple test script to verify PDF filling with specific fields.
"""
import os
import sys
import tempfile
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the project root to the Python path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'formsiq_project.settings')

import django
django.setup()

from django.conf import settings
from pypdf import PdfReader, PdfWriter

# Import the functions to test
from api_processor.field_mapping import get_pdf_field_name
from api_processor.pdf_service import fill_pdf_form

# Define a minimal set of fields we know should exist in the PDF
TEST_FIELDS = [
    {
        "field_name": "Borrower First Name",
        "field_value": "John",
        "confidence_score": 0.95
    },
    {
        "field_name": "Borrower Last Name",
        "field_value": "Smith",
        "confidence_score": 0.95
    },
    {
        "field_name": "Borrower Social Security Number",
        "field_value": "123-45-6789",
        "confidence_score": 0.90
    },
    {
        "field_name": "Primary Phone Number",
        "field_value": "(555) 123-4567",
        "confidence_score": 0.90
    },
    {
        "field_name": "Email Address",
        "field_value": "johnsmith@example.com",
        "confidence_score": 0.90
    },
    {
        "field_name": "Loan Amount Requested",
        "field_value": "$350,000",
        "confidence_score": 0.95
    }
]

def test_pdf_field_mapping():
    """Test that our fields are properly mapped"""
    logger.info("Testing field mapping...")
    
    success = True
    for field in TEST_FIELDS:
        llm_field_name = field["field_name"]
        pdf_field_name = get_pdf_field_name(llm_field_name)
        
        if pdf_field_name:
            logger.info(f"✓ Field mapped: {llm_field_name} -> {pdf_field_name}")
        else:
            logger.error(f"✗ Field mapping failed: {llm_field_name}")
            success = False
    
    return success

def inspect_pdf_fields(pdf_path):
    """Print out filled field values in a PDF"""
    try:
        reader = PdfReader(pdf_path)
        fields = reader.get_fields()
        
        logger.info(f"PDF has {len(fields)} form fields")
        
        # Check specifically for our test fields
        for field in TEST_FIELDS:
            llm_field_name = field["field_name"]
            expected_value = field["field_value"]
            pdf_field_name = get_pdf_field_name(llm_field_name)
            
            if pdf_field_name and pdf_field_name in fields:
                actual_value = fields[pdf_field_name].get('/V', None)
                if actual_value is not None:
                    logger.info(f"Field '{pdf_field_name}' has value: {actual_value}")
                    if str(actual_value) == str(expected_value):
                        logger.info(f"✓ Value matches expected: {expected_value}")
                    else:
                        logger.warning(f"✗ Value '{actual_value}' doesn't match expected: {expected_value}")
                else:
                    logger.warning(f"Field '{pdf_field_name}' does not have a value set")
            else:
                logger.warning(f"Field '{pdf_field_name}' not found in PDF")
        
    except Exception as e:
        logger.error(f"Error inspecting PDF: {str(e)}")
        return False
    
    return True

def main():
    """Run the test"""
    logger.info("Starting PDF filling test")
    
    # First test the field mapping
    if not test_pdf_field_mapping():
        logger.error("Field mapping test failed")
        return False
    
    # Test the PDF filling
    try:
        filled_pdf_path = fill_pdf_form(TEST_FIELDS)
        
        if filled_pdf_path and os.path.exists(filled_pdf_path):
            logger.info(f"PDF generated successfully: {filled_pdf_path}")
            
            # Copy to a more accessible location
            output_path = os.path.join(os.path.dirname(__file__), "filled_test.pdf")
            with open(filled_pdf_path, 'rb') as src, open(output_path, 'wb') as dst:
                dst.write(src.read())
            
            logger.info(f"Copied PDF to {output_path} for inspection")
            
            # Inspect the PDF to see if fields were actually filled
            inspect_pdf_fields(output_path)
            
            return True
        else:
            logger.error("PDF filling failed")
            return False
            
    except Exception as e:
        logger.error(f"Error in test: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    print(f"\nTest {'PASSED' if success else 'FAILED'}")
    sys.exit(0 if success else 1) 