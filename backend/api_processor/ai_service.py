"""
Service to interact with LM Studio API for field extraction from transcripts.
"""
import json
import logging
import re
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# LM Studio endpoint - this would typically come from settings
LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"

# System prompt for the AI model
SYSTEM_PROMPT = """
Extract mortgage application fields from transcript:

RULES:
1. Use ONLY the EXACT field names listed below
2. Only extract mentioned fields
3. Format: dates (MM/DD/YYYY), phone (xxx-xxx-xxxx), SSN (xxx-xx-xxxx)
4. For checkbox fields: "Yes" or "No" only
5. For radio button fields: Use EXACT values specified in parentheses

FIELDS TO EXTRACT:

## TEXT FIELDS
- Borrower Name
- Borrower SSN
- Borrower DOB
- Borrower Home Phone
- Borrower Present Address
- Borrower Position/Title/Type of Business
- Borrower Name and Address of Employer
- Borrower Years on the job
- Amount
- Interest Rate
- Subject Property Address
- Subject Property Description
- Year Built

## CHECKBOX FIELDS (answer with "Yes" or "No" only)
- First Time Homebuyer
- Property will be Primary Residence
- Property will be Second Home
- Property will be Investment
- Mortgage is Conventional
- Borrower Self Employed
- Borrower has Dependents
- Borrower is US Citizen
- Co-Borrower is US Citizen
- Borrower Intends to Occupy Property
- This is Construction Loan
- This is Refinance
- Co-Borrower will be using income

## RADIO BUTTON FIELDS (use EXACT values in parentheses)
- Purpose of Loan (Purchase, Refinance, Construction, Construction-Permanent, Other)
- Property Usage (Primary Residence, Secondary Residence, Investment Property)
- Mortgage Type (Conventional, FHA, VA, USDA/Rural Housing Service, Other)
- Marital Status (Married, Unmarried, Separated)
- Borrower Own/Rent (Own, Rent)

FORMAT:
{
  "fields": [
    {"n": 1, "name": "Borrower Name", "value": "John Smith", "conf": 95},
    {"n": 2, "name": "Amount", "value": "350000", "conf": 90},
    {"n": 3, "name": "First Time Homebuyer", "value": "Yes", "conf": 85},
    {"n": 4, "name": "Purpose of Loan", "value": "Purchase", "conf": 98}
  ]
}

Remember: Use ONLY the exact field names listed, and the exact values for radio buttons.
"""


class AIExtractionError(Exception):
    """Exception raised for errors in the AI extraction process."""
    pass


def extract_json_from_llm_response(text):
    """
    Extract JSON from an LLM response that might contain markdown code blocks or other text.
    
    Args:
        text (str): The raw response from the LLM
        
    Returns:
        str: The extracted JSON string
    """
    # Check if the response is already a valid JSON
    try:
        json.loads(text)
        return text
    except json.JSONDecodeError:
        pass
        
    # Try to extract JSON from a markdown code block
    json_block_pattern = r"```(?:json)?\s*([\s\S]*?)```"
    match = re.search(json_block_pattern, text)
    if match:
        extracted_json = match.group(1).strip()
        try:
            # Validate that this is valid JSON
            json.loads(extracted_json)
            return extracted_json
        except json.JSONDecodeError:
            pass
            
    # If we can't find a code block, look for a JSON-like structure
    # This is a more aggressive approach and might cause issues
    json_pattern = r"({[\s\S]*})"
    match = re.search(json_pattern, text)
    if match:
        potential_json = match.group(1).strip()
        try:
            # Validate that this is valid JSON
            json.loads(potential_json)
            return potential_json
        except json.JSONDecodeError:
            pass
            
    # If we can't extract JSON, raise an exception
    logger.error(f"Could not extract valid JSON from LLM response: {text}")
    raise json.JSONDecodeError("Could not extract valid JSON from LLM response", text, 0)


def extract_fields_from_transcript(transcript):
    """
    Extract fields from a transcript using the LM Studio API.
    
    Args:
        transcript (str): The call transcript to analyze
        
    Returns:
        dict: The structured field data extracted from the transcript
        
    Raises:
        AIExtractionError: If there's an error in the extraction process
    """
    try:
        # Prepare the payload for LM Studio
        payload = {
            "model": "gemma-3-12b",  # This should match the model loaded in LM Studio
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": transcript}
            ],
            "temperature": 0.1,  # Low temperature for factual extraction
            "max_tokens": 4000,  # Increased from 2000 to 4000 to allow for longer responses
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        # Call LM Studio API
        response = requests.post(
            LM_STUDIO_URL, 
            headers=headers, 
            json=payload,
            timeout=180  # Increased timeout to 3 minutes (180 seconds)
        )
        
        # Check if request was successful
        response.raise_for_status()
        
        # Parse response JSON
        response_json = response.json()
        
        # Extract the content from the response
        # The structure follows OpenAI's API format
        if 'choices' not in response_json or not response_json['choices']:
            raise AIExtractionError("Invalid response format from LM Studio API")
            
        extracted_text = response_json['choices'][0]['message']['content']
        
        # Parse the JSON content returned by the LLM
        try:
            # Try to extract JSON from the response text which might contain markdown code blocks
            extracted_json_str = extract_json_from_llm_response(extracted_text)
            extracted_data = json.loads(extracted_json_str)
            
            # Basic validation of the expected structure
            if not isinstance(extracted_data, dict) or 'fields' not in extracted_data:
                raise AIExtractionError("AI response doesn't have the expected 'fields' key")
                
            # Convert the compact numbered format to the expected structure
            reformatted_fields = []
            for field in extracted_data['fields']:
                # Handle compact numbering format conversion
                if 'n' in field and 'name' in field and 'value' in field and 'conf' in field:
                    reformatted_fields.append({
                        'field_name': field['name'],
                        'field_value': field['value'],
                        'confidence_score': field['conf'] / 100.0  # Convert 0-100 to 0-1
                    })
                # Handle legacy format
                elif 'field_name' in field and ('field_value' in field or 'value' in field) and ('confidence_score' in field or 'confidence' in field):
                    value = field.get('field_value', field.get('value', ''))
                    confidence = field.get('confidence_score', field.get('confidence', 0))
                    reformatted_fields.append({
                        'field_name': field['field_name'],
                        'field_value': value,
                        'confidence_score': confidence if confidence <= 1 else confidence / 100.0
                    })
            
            return {'fields': reformatted_fields}
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {extracted_text}")
            raise AIExtractionError(f"Failed to parse AI response as JSON: {str(e)}")
            
    except requests.RequestException as e:
        logger.error(f"Error calling LM Studio API: {str(e)}")
        raise AIExtractionError(f"Error calling LM Studio API: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in field extraction: {str(e)}")
        raise AIExtractionError(f"Unexpected error in field extraction: {str(e)}") 