#!/usr/bin/env python
"""
Gemma-3 PDF Field Extractor

This script uses Gemma-3 to extract field data from text transcripts in the expected format
for the PDF field processor. It sends the transcript to Gemma-3 and formats the response
according to the field structure in the uniform_residential_loan_application.pdf form.
"""

import os
import sys
import json
import argparse
import requests
from pathlib import Path
from typing import List, Dict, Any
import re

# Add api_processor directory to the Python path
current_dir = Path(__file__).resolve().parent
api_processor_dir = current_dir / 'api_processor'
if str(api_processor_dir) not in sys.path:
    sys.path.append(str(api_processor_dir))

# Import the pdf_field_processor module
from api_processor.pdf_field_processor import PDFFieldProcessor

# Set up paths
PDF_TEMPLATE_PATH = os.path.join(current_dir, 'media', 'pdf', 'uniform_residential_loan_application.pdf')
AI_FIELD_GUIDE_PATH = os.path.join(current_dir, 'media', 'pdf', 'ai_parser_field_guide.md')
OUTPUT_DIR = os.path.join(current_dir, 'media', 'pdf', 'output')
FILLED_PDF_PATH = os.path.join(OUTPUT_DIR, 'filled_loan_application.pdf')

# Replace with your actual API endpoint for Gemma-3
GEMMA_API_ENDPOINT = "http://localhost:8000/api/generate"  # Change this to your actual endpoint


def parse_command_line():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Extract field data from text using Gemma-3')
    parser.add_argument('--input', '-i', type=str, required=True, help='Path to the input transcript file')
    parser.add_argument('--output', '-o', type=str, default=FILLED_PDF_PATH, help='Path for the filled PDF output')
    parser.add_argument('--json-output', '-j', type=str, help='Path to save the extracted JSON data')
    return parser.parse_args()


def read_field_guide():
    """Read the AI field guide to understand the field structure"""
    with open(AI_FIELD_GUIDE_PATH, 'r') as f:
        return f.read()


def extract_fields_with_gemma(transcript_text: str, field_guide: str) -> List[Dict[str, Any]]:
    """
    Extract field data from text using Gemma-3
    
    Args:
        transcript_text: The input transcript text
        field_guide: The field guide content
        
    Returns:
        List of dictionaries with field_name, value, and confidence
    """
    # Prepare the prompt
    prompt = f"""
You are a specialized PDF form field extractor. Your task is to extract field data from the provided transcript 
and return it in a structured JSON format that can be used to fill out a Uniform Residential Loan Application form.

Use ONLY the field names that are mentioned in the field guide. The format should be a list of dictionaries, each 
containing 'field_name', 'value', and 'confidence' (0-100).

For checkbox fields, use "Yes" or "No" as the value.
For radio button groups, use the format "Group Name: Option" with "Yes" as the value.

Here's a section of the field guide for reference:
{field_guide[:2000]}  # Only include the beginning to keep the prompt short

Now, extract the fields from the following transcript:

{transcript_text}

Output ONLY a valid JSON array with the extracted fields in the format:
[
  {{"field_name": "Field Name", "value": "Field Value", "confidence": confidence_score}},
  ...
]
"""

    try:
        # Call Gemma-3 API
        response = requests.post(
            GEMMA_API_ENDPOINT,
            json={
                "prompt": prompt,
                "max_tokens": 2048,
                "temperature": 0.1
            },
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            # Extract JSON from the response
            # This assumes the model outputs a JSON array directly
            # You might need to adjust this based on your API's response format
            extracted_text = result.get('text', '')
            
            # Try to find JSON array in the text
            start_idx = extracted_text.find('[')
            end_idx = extracted_text.rfind(']') + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = extracted_text[start_idx:end_idx]
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    print(f"Error parsing JSON from API response: {json_str}")
                    return []
            else:
                print(f"No JSON array found in API response: {extracted_text}")
                return []
        else:
            print(f"API request failed with status code: {response.status_code}")
            print(f"Response: {response.text}")
            return []
    
    except Exception as e:
        print(f"Error calling Gemma-3 API: {str(e)}")
        return []


def simulate_extraction(transcript_text: str) -> List[Dict[str, Any]]:
    """
    Simulate field extraction for testing when API is not available
    
    Args:
        transcript_text: The input transcript text
        
    Returns:
        List of dictionaries with field_name, value, and confidence
    """
    # This is a simulation that extracts fields from the transcript text
    fields = []
    
    # Extract name
    if "my name is" in transcript_text.lower():
        for line in transcript_text.split("\n"):
            if "my name is" in line.lower():
                name_match = re.search(r"my name is ([^.,!?]+)", line, re.IGNORECASE)
                if name_match:
                    full_name = name_match.group(1).strip()
                    
                    # Try to split into first, middle, last
                    name_parts = full_name.split()
                    if len(name_parts) >= 3:
                        fields.append({"field_name": "Borrower First Name", "value": name_parts[0], "confidence": 100})
                        fields.append({"field_name": "Borrower Middle Name", "value": name_parts[1], "confidence": 100})
                        fields.append({"field_name": "Borrower Last Name", "value": ' '.join(name_parts[2:]), "confidence": 100})
                    elif len(name_parts) == 2:
                        fields.append({"field_name": "Borrower First Name", "value": name_parts[0], "confidence": 100})
                        fields.append({"field_name": "Borrower Last Name", "value": name_parts[1], "confidence": 100})
                    else:
                        fields.append({"field_name": "Borrower Name", "value": full_name, "confidence": 100})
                    
                    fields.append({"field_name": "Borrower Suffix", "value": "Not Found", "confidence": 90})
                    break
    
    # Extract SSN
    ssn_pattern = r"\b\d{3}[-]?\d{2}[-]?\d{4}\b"
    ssn_matches = re.findall(ssn_pattern, transcript_text)
    if ssn_matches:
        fields.append({"field_name": "Borrower SSN", "value": ssn_matches[0], "confidence": 80})
        fields.append({"field_name": "Social Security Number", "value": ssn_matches[0], "confidence": 80})
    
    # Extract DOB
    dob_patterns = [
        r"\b(\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})\b",  # MM/DD/YYYY or DD/MM/YYYY
        r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})(?:rd|th|st|nd)?,?\s+(\d{4})\b",  # Month DD, YYYY
        r"\b(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})\b"  # YYYY-MM-DD
    ]
    
    for pattern in dob_patterns:
        dob_matches = re.findall(pattern, transcript_text, re.IGNORECASE)
        if dob_matches:
            # Format as YYYY-MM-DD
            if re.match(r"\b\d{4}[/\-]\d{1,2}[/\-]\d{1,2}\b", dob_matches[0][0] + "-" + dob_matches[0][1] + "-" + dob_matches[0][2]):
                dob = f"{dob_matches[0][0]}-{dob_matches[0][1].zfill(2)}-{dob_matches[0][2].zfill(2)}"
            else:
                dob = f"{dob_matches[0][2]}-{dob_matches[0][0].zfill(2)}-{dob_matches[0][1].zfill(2)}"
            fields.append({"field_name": "Borrower DOB", "value": dob, "confidence": 100})
            fields.append({"field_name": "Date of Birth", "value": dob, "confidence": 100})
            break
    
    # Extract address
    address_patterns = [
        r"\b(\d+\s+[A-Za-z]+\s+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Circle|Cir|Court|Ct|Place|Pl|Terrace|Ter|Way|Parkway|Pkwy)(?:\s*[A-Za-z0-9,]+)(?:\s*,\s*)?(?:Apt|Apartment|Unit|#)?\s*(?:[A-Za-z0-9]+)?(?:\s*,\s*)?(?:[A-Za-z]+\s*,\s*[A-Za-z]{2}\s*,?\s*\d{5}(?:-\d{4})?)?)",
        r"\b(\d+\s+[A-Za-z]+\s+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Circle|Cir|Court|Ct|Place|Pl|Terrace|Ter|Way|Parkway|Pkwy)(?:\s*[A-Za-z0-9,]+)?)",
        r"\b(I live at\s+(?:\d+\s+[A-Za-z]+\s+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Circle|Cir|Court|Ct|Place|Pl|Terrace|Ter|Way|Parkway|Pkwy)(?:\s*[A-Za-z0-9,]+)(?:\s*,\s*)?(?:Apt|Apartment|Unit|#)?\s*(?:[A-Za-z0-9]+)?(?:\s*,\s*)?(?:[A-Za-z]+\s*,\s*[A-Za-z]{2}\s*,?\s*\d{5}(?:-\d{4})?)?))"
    ]
    
    full_address = None
    for pattern in address_patterns:
        address_matches = re.findall(pattern, transcript_text, re.IGNORECASE)
        if address_matches:
            full_address = address_matches[0]
            break
            
    # If address found, split it into parts
    if full_address:
        # Try to extract the parts
        street_match = re.search(r"\b(\d+\s+[A-Za-z]+\s+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Circle|Cir|Court|Ct|Place|Pl|Terrace|Ter|Way|Parkway|Pkwy)(?:\s*[A-Za-z0-9]+)?)", full_address, re.IGNORECASE)
        if street_match:
            street = street_match.group(1)
            fields.append({"field_name": "Borrower Present Address", "value": full_address, "confidence": 100})
            fields.append({"field_name": "Current Street Address", "value": street, "confidence": 100})
        
        # City
        city_match = re.search(r"([A-Za-z\s]+)(?:\s*,\s*[A-Za-z]{2}\s*,?\s*\d{5}(?:-\d{4})?)?$", full_address, re.IGNORECASE)
        if city_match:
            city = city_match.group(1).strip()
            fields.append({"field_name": "Current City", "value": city, "confidence": 100})
        
        # State
        state_match = re.search(r"([A-Za-z]{2})\s*,?\s*\d{5}(?:-\d{4})?$", full_address, re.IGNORECASE)
        if state_match:
            state = state_match.group(1).strip()
            fields.append({"field_name": "Current State", "value": state, "confidence": 100})
        
        # Zip
        zip_match = re.search(r"(\d{5}(?:-\d{4})?)$", full_address, re.IGNORECASE)
        if zip_match:
            zip_code = zip_match.group(1).strip()
            fields.append({"field_name": "Current Zip Code", "value": zip_code, "confidence": 100})
    
    # Extract phone number
    phone_pattern = r"\b(?:\+?1[-\s]?)?(?:\(?\d{3}\)?[-\s]?)?\d{3}[-\s]?\d{4}\b"
    phone_matches = re.findall(phone_pattern, transcript_text)
    if phone_matches:
        fields.append({"field_name": "Borrower Home Phone", "value": phone_matches[0], "confidence": 100})
        fields.append({"field_name": "Primary Phone Number", "value": phone_matches[0], "confidence": 100})
    
    # Extract email
    email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    email_matches = re.findall(email_pattern, transcript_text)
    if email_matches:
        fields.append({"field_name": "Text1", "value": email_matches[0], "confidence": 100})
        fields.append({"field_name": "Email Address", "value": email_matches[0], "confidence": 100})
    
    # Extract marital status
    marital_status_patterns = [
        r"(?:I am|I'm)\s+(single|married|unmarried|separated)",
        r"marital status.*?(single|married|unmarried|separated)",
        r"(single|married|unmarried|separated).*?marital status"
    ]
    
    marital_status = None
    for pattern in marital_status_patterns:
        marital_matches = re.findall(pattern, transcript_text, re.IGNORECASE)
        if marital_matches:
            marital_status = marital_matches[0].strip().lower()
            break
            
    if marital_status:
        fields.append({"field_name": "Borrower Marital Status", "value": marital_status.capitalize(), "confidence": 95})
        fields.append({"field_name": "Marital Status", "value": marital_status.capitalize(), "confidence": 95})
        
        # Add checkbox format for marital status
        if marital_status.lower() == "married":
            fields.append({"field_name": "Borrower Marital Status: Married", "value": "Yes", "confidence": 95})
        elif marital_status.lower() in ["single", "unmarried"]:
            fields.append({"field_name": "Borrower Marital Status: Unmarried", "value": "Yes", "confidence": 95})
        elif marital_status.lower() == "separated":
            fields.append({"field_name": "Borrower Marital Status: Separated", "value": "Yes", "confidence": 95})
    
    # Extract employer information
    employer_patterns = [
        r"(?:I work|I am employed|I'm employed).*?(?:at|for|with)\s+([^.,;]+)",
        r"(?:employer|company|firm).*?(?:is|called|named)\s+([^.,;]+)",
        r"(?:I am a|I'm a).*?(?:at|for|with)\s+([^.,;]+)"
    ]
    
    employer = None
    for pattern in employer_patterns:
        employer_matches = re.findall(pattern, transcript_text, re.IGNORECASE)
        if employer_matches:
            employer = employer_matches[0].strip()
            break
    
    if employer:
        fields.append({"field_name": "Borrower Name and Address of Employer", "value": employer, "confidence": 100})
        fields.append({"field_name": "Current Employer Name", "value": employer, "confidence": 100})
    
    # Extract job title
    job_patterns = [
        r"(?:position|title|role|job).*?(?:is|as)\s+([^.,;]+)",
        r"(?:I am a|I'm a)\s+([^.,;]+?)\s+(?:at|for|with)"
    ]
    
    job_title = None
    for pattern in job_patterns:
        job_matches = re.findall(pattern, transcript_text, re.IGNORECASE)
        if job_matches:
            job_title = job_matches[0].strip()
            break
    
    if job_title:
        fields.append({"field_name": "Borrower Position/Title/Type of Business", "value": job_title, "confidence": 100})
        fields.append({"field_name": "Job Title/Position", "value": job_title, "confidence": 100})
    
    # Extract years of employment
    years_patterns = [
        r"(?:been there|been working|employed).*?(?:for|since)\s+(\d+)\s+(?:years|year)",
        r"(\d+)\s+(?:years|year).*?(?:with current employer|at this job|in this role|at this company)"
    ]
    
    years_employment = None
    for pattern in years_patterns:
        years_matches = re.findall(pattern, transcript_text, re.IGNORECASE)
        if years_matches:
            years_employment = years_matches[0].strip()
            break
    
    if years_employment:
        fields.append({"field_name": "Borrower Years on the job", "value": years_employment, "confidence": 75})
        fields.append({"field_name": "Employment Start Date", "value": f"{years_employment} years", "confidence": 75})
    
    # Extract income
    income_patterns = [
        r"(?:income|salary|make|earn|earning).*?(?:is|about|approximately|around)?\s+\$?(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)\s*(?:thousand|k|K|,000)?(?:per|a|each)?\s*(?:year|yearly|annually|month|monthly)?",
        r"\$?(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)\s*(?:thousand|k|K|,000)?(?:per|a|each)?\s*(?:year|yearly|annually|month|monthly)?.*?(?:income|salary|make|earn)"
    ]
    
    income = None
    for pattern in income_patterns:
        income_matches = re.findall(pattern, transcript_text, re.IGNORECASE)
        if income_matches:
            income = income_matches[0].strip().replace(",", "")
            # Check if it's followed by "thousand" or "k"
            if "thousand" in transcript_text.lower() or "k" in transcript_text.lower():
                income = str(float(income) * 1000)
            break
    
    if income:
        # Check if it's annual or monthly
        if "year" in transcript_text.lower() or "annual" in transcript_text.lower():
            # Convert to monthly
            monthly_income = str(float(income) / 12)
            fields.append({"field_name": "Monthly income Borrower Base a", "value": monthly_income, "confidence": 100})
            fields.append({"field_name": "Monthly Income (Base)", "value": f"${monthly_income}", "confidence": 100})
        else:
            fields.append({"field_name": "Monthly income Borrower Base a", "value": income, "confidence": 100})
            fields.append({"field_name": "Monthly Income (Base)", "value": f"${income}", "confidence": 100})
    
    # Extract additional income
    additional_income_patterns = [
        r"(?:other income|additional income|extra income|also make).*?(?:is|about|approximately|around)?\s+\$?(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)\s*(?:thousand|k|K)?(?:per|a|each)?\s*(?:year|yearly|annually|month|monthly)?",
        r"\$?(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)\s*(?:thousand|k|K)?(?:per|a|each)?\s*(?:year|yearly|annually|month|monthly)?.*?(?:other income|additional income|extra income)"
    ]
    
    additional_income = None
    additional_income_source = None
    
    for pattern in additional_income_patterns:
        additional_income_matches = re.findall(pattern, transcript_text, re.IGNORECASE)
        if additional_income_matches:
            additional_income = additional_income_matches[0].strip().replace(",", "")
            # Extract the source of additional income
            source_match = re.search(r"(?:from|through|via|by)\s+([^.,;]+)", transcript_text, re.IGNORECASE)
            if source_match:
                additional_income_source = source_match.group(1).strip()
            break
    
    if additional_income:
        if additional_income_source:
            fields.append({"field_name": "Monthly income Borrower Other a21", "value": additional_income, "confidence": 80})
            fields.append({"field_name": "Monthly Income (Other, specify source if possible)", "value": f"${additional_income} ({additional_income_source})", "confidence": 80})
        else:
            fields.append({"field_name": "Monthly income Borrower Other a21", "value": additional_income, "confidence": 80})
            fields.append({"field_name": "Monthly Income (Other, specify source if possible)", "value": f"${additional_income}", "confidence": 80})
    
    # Extract loan amount
    loan_patterns = [
        r"(?:loan|mortgage|borrow|finance).*?(?:for|amount|of|looking for)\s+\$?(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)\s*(?:thousand|k|K)?",
        r"\$?(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)\s*(?:thousand|k|K)?.*?(?:loan|mortgage|borrow|financing)"
    ]
    
    loan_amount = None
    for pattern in loan_patterns:
        loan_matches = re.findall(pattern, transcript_text, re.IGNORECASE)
        if loan_matches:
            loan_amount = loan_matches[0].strip().replace(",", "")
            # Check if it's followed by "thousand" or "k"
            if "thousand" in transcript_text.lower() or "k" in transcript_text.lower():
                loan_amount = str(float(loan_amount) * 1000)
            break
    
    if loan_amount:
        fields.append({"field_name": "Loan Amount", "value": loan_amount, "confidence": 100})
        fields.append({"field_name": "Amount", "value": loan_amount, "confidence": 100})
        fields.append({"field_name": "Loan Amount Requested", "value": f"${loan_amount}", "confidence": 100})
    
    # Extract loan purpose
    purpose_patterns = [
        r"(?:purpose|reason|want|looking).*?(?:loan|mortgage|financing|borrow|refinance).*?(?:is|for|to)\s+([^.,;]+)",
        r"(?:buying|purchasing|refinancing|building|constructing)\s+([^.,;]+)"
    ]
    
    loan_purpose = None
    for pattern in purpose_patterns:
        purpose_matches = re.findall(pattern, transcript_text, re.IGNORECASE)
        if purpose_matches:
            loan_purpose = purpose_matches[0].strip()
            break
    
    if loan_purpose:
        # Normalize the purpose
        if "buy" in loan_purpose.lower() or "purchas" in loan_purpose.lower():
            normalized_purpose = "Purchase"
        elif "refinanc" in loan_purpose.lower():
            normalized_purpose = "Refinance"
        elif "build" in loan_purpose.lower() or "construct" in loan_purpose.lower():
            normalized_purpose = "Construction"
        else:
            normalized_purpose = "Other"
            
        fields.append({"field_name": "Purpose of Loan", "value": normalized_purpose, "confidence": 100})
        fields.append({"field_name": "Loan Purpose", "value": normalized_purpose, "confidence": 100})
        
        # Add checkbox format for purpose
        fields.append({"field_name": f"Purpose of Loan: {normalized_purpose}", "value": "Yes", "confidence": 100})
    
    # Extract property address (if different from current)
    property_patterns = [
        r"(?:property|house|home).*?(?:is located at|address is|located at)\s+([^.]+)",
        r"(?:purchasing|buying|refinancing).*?(?:at|on|located at)\s+([^.]+)"
    ]
    
    property_address = None
    for pattern in property_patterns:
        property_matches = re.findall(pattern, transcript_text, re.IGNORECASE)
        if property_matches:
            property_address = property_matches[0].strip()
            break
    
    if property_address and property_address != full_address:
        fields.append({"field_name": "Subject Property Address", "value": property_address, "confidence": 100})
        
        # Try to extract property address parts
        prop_street_match = re.search(r"\b(\d+\s+[A-Za-z]+\s+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Circle|Cir|Court|Ct|Place|Pl|Terrace|Ter|Way|Parkway|Pkwy)(?:\s*[A-Za-z0-9]+)?)", property_address, re.IGNORECASE)
        if prop_street_match:
            prop_street = prop_street_match.group(1)
            fields.append({"field_name": "Property Street Address (if different from current, or for purchase)", "value": prop_street, "confidence": 100})
        
        # Property City
        prop_city_match = re.search(r"([A-Za-z\s]+)(?:\s*,\s*[A-Za-z]{2}\s*,?\s*\d{5}(?:-\d{4})?)?$", property_address, re.IGNORECASE)
        if prop_city_match:
            prop_city = prop_city_match.group(1).strip()
            fields.append({"field_name": "Property City (if different from current, or for purchase)", "value": prop_city, "confidence": 100})
        
        # Property State
        prop_state_match = re.search(r"([A-Za-z]{2})\s*,?\s*\d{5}(?:-\d{4})?$", property_address, re.IGNORECASE)
        if prop_state_match:
            prop_state = prop_state_match.group(1).strip()
            fields.append({"field_name": "Property State (if different from current, or for purchase)", "value": prop_state, "confidence": 100})
        
        # Property Zip
        prop_zip_match = re.search(r"(\d{5}(?:-\d{4})?)$", property_address, re.IGNORECASE)
        if prop_zip_match:
            prop_zip = prop_zip_match.group(1).strip()
            fields.append({"field_name": "Property Zip Code (if different from current, or for purchase)", "value": prop_zip, "confidence": 100})
            
    # Extract self-employment status
    self_employed_patterns = [
        r"(?:self[- ]employed|own my own business|freelancer|independent contractor|business owner)",
        r"(?:not self[- ]employed|work for someone else|employed by)"
    ]
    
    is_self_employed = False
    for pattern in self_employed_patterns:
        if re.search(pattern, transcript_text, re.IGNORECASE):
            is_self_employed = "self" in pattern.lower()
            break
    
    if is_self_employed is not None:
        fields.append({"field_name": "Borrower Self Employed", "value": "Yes" if is_self_employed else "No", "confidence": 90})
    
    # Add default for checkbox fields we didn't find
    # This ensures the UI shows them, even if not checked
    if not any(field["field_name"] == "Borrower Self Employed" for field in fields):
        fields.append({"field_name": "Borrower Self Employed", "value": "No", "confidence": 90})
    
    return fields


def fill_pdf_with_extracted_data(extracted_fields: List[Dict[str, Any]], output_path: str):
    """
    Fill the PDF with the extracted field data
    
    Args:
        extracted_fields: List of dictionaries with field_name, value, and confidence
        output_path: Path to save the filled PDF
    
    Returns:
        str: Path to the filled PDF
    """
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Initialize PDF processor
    processor = PDFFieldProcessor(PDF_TEMPLATE_PATH)
    
    # Map extracted fields to PDF fields
    data_to_fill = processor.map_user_data_to_pdf_fields(extracted_fields)
    
    # Fill the PDF
    filled_pdf_path = processor.fill_pdf_form(data_to_fill, output_path)
    return filled_pdf_path


def main():
    """Main function"""
    args = parse_command_line()
    
    # Read input transcript
    try:
        with open(args.input, 'r') as f:
            transcript_text = f.read()
    except FileNotFoundError:
        print(f"Error: Input file not found at {args.input}")
        return 1
    
    # Read the field guide
    field_guide = read_field_guide()
    
    # Extract fields from transcript
    try:
        extracted_fields = extract_fields_with_gemma(transcript_text, field_guide)
        
        # If the API call failed or returned no results, fall back to simulation
        if not extracted_fields:
            print("No fields extracted from API. Falling back to simulation mode.")
            extracted_fields = simulate_extraction(transcript_text)
    except Exception as e:
        print(f"Error extracting fields: {str(e)}")
        print("Falling back to simulation mode.")
        extracted_fields = simulate_extraction(transcript_text)
    
    # Save the extracted fields to JSON if requested
    if args.json_output:
        try:
            with open(args.json_output, 'w') as f:
                json.dump(extracted_fields, f, indent=2)
            print(f"Saved extracted fields to {args.json_output}")
        except Exception as e:
            print(f"Error saving extracted fields to JSON: {str(e)}")
    
    # Fill the PDF with the extracted fields
    if extracted_fields:
        print(f"Extracted {len(extracted_fields)} fields from transcript")
        for field in extracted_fields:
            print(f"  {field['field_name']}: {field['value']} (confidence: {field['confidence']}%)")
        
        filled_pdf_path = fill_pdf_with_extracted_data(extracted_fields, args.output)
        print(f"Successfully filled PDF and saved to {filled_pdf_path}")
    else:
        print("No fields were extracted from the transcript")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 