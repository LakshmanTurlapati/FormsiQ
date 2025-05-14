#!/usr/bin/env python
"""
Test script to verify the Django API endpoints with a sample transcript.
"""
import requests
import json
import os
import sys
import time

# API endpoint
API_URL = "http://localhost:8000/api"

# Sample transcript for testing
SAMPLE_TRANSCRIPT = """
Hello, my name is John Smith and I'd like to apply for a mortgage loan. I was born on May 15, 1980.
My Social Security Number is 123-45-6789. I currently live at 123 Main Street, Apartment 4B, 
in San Francisco, California, zip code 94107.

I've been working at Tech Innovations Inc. as a Senior Software Engineer for about 4 years now. 
My monthly income is around $12,500 before taxes.

I'm looking to purchase a property at 456 Park Avenue in San Francisco, CA, 94108. 
The purchase price is $850,000 and I'm planning to make a down payment of $170,000, 
so I'll need a loan for $680,000.

You can reach me at (415) 555-7890 or email me at john.smith@example.com.
I'm married, and my wife Sarah might be a co-borrower on this loan.
"""

def test_extraction_endpoint():
    """Test the field extraction endpoint."""
    print("Testing the /extract-fields endpoint with sample transcript...")
    
    try:
        response = requests.post(
            f"{API_URL}/extract-fields",
            json={"transcript": SAMPLE_TRANSCRIPT},
            timeout=60
        )
        
        response.raise_for_status()
        result = response.json()
        
        print("\nExtraction successful! API Response:")
        print("-" * 60)
        
        # Print fields in a readable format
        if 'fields' in result:
            for field in result['fields']:
                field_name = field['field_name']
                field_value = field['field_value']
                confidence = field['confidence_score']
                print(f"{field_name}: {field_value} (Confidence: {confidence:.2f})")
        else:
            print(json.dumps(result, indent=2))
            
        print("-" * 60)
        
        return result
        
    except requests.RequestException as e:
        print(f"\nError testing extraction endpoint: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                print(f"Response: {e.response.json()}")
            except:
                print(f"Response text: {e.response.text}")
        print("\nMake sure the Django server is running on http://localhost:8000")
        return None

def test_pdf_generation(extraction_result):
    """Test the PDF generation endpoint with the extracted fields."""
    if not extraction_result or 'fields' not in extraction_result:
        print("Skipping PDF generation test due to failed extraction.")
        return False
        
    print("\nTesting the /fill-pdf endpoint with extracted fields...")
    
    try:
        response = requests.post(
            f"{API_URL}/fill-pdf",
            json=extraction_result,
            timeout=60,
            stream=True  # Handle file download
        )
        
        response.raise_for_status()
        
        # Save the PDF file
        output_file = "test_filled_form.pdf"
        with open(output_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                
        file_size = os.path.getsize(output_file)
        if file_size > 0:
            print(f"\nPDF generation successful! Saved to: {os.path.abspath(output_file)}")
            print(f"File size: {file_size / 1024:.2f} KB")
            return True
        else:
            print("\nError: Generated PDF is empty.")
            return False
            
    except requests.RequestException as e:
        print(f"\nError testing PDF generation endpoint: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                print(f"Response: {e.response.json()}")
            except:
                print(f"Response text: {e.response.text}")
        return False

if __name__ == "__main__":
    print("Starting API test sequence...")
    
    extraction_result = test_extraction_endpoint()
    if extraction_result:
        time.sleep(1)  # Small delay between requests
        test_pdf_generation(extraction_result)
    
    print("\nTest sequence completed.") 