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
You are an expert data extraction AI. Your task is to analyze a provided call transcript related to a mortgage application (1003 Form) and extract specific fields.

The fields to extract are:
1.  **Borrower First Name**
2.  **Borrower Middle Name**
3.  **Borrower Last Name**
4.  **Borrower Suffix**
5.  **Social Security Number**
6.  **Date of Birth** (YYYY-MM-DD format if possible, otherwise as stated)
7.  **Current Street Address**
8.  **Current City**
9.  **Current State** (2-letter abbreviation if possible)
10. **Current Zip Code**
11. **Primary Phone Number**
12. **Email Address**
13. **Marital Status** (e.g., Married, Unmarried, Separated)
14. **Current Employer Name**
15. **Job Title/Position**
16. **Employment Start Date**
17. **Monthly Income (Base)**
18. **Monthly Income (Other, specify source if possible)**
19. **Loan Amount Requested**
20. **Loan Purpose** (e.g., Purchase, Refinance)
21. **Property Street Address (if different from current, or for purchase)**
22. **Property City (if different from current, or for purchase)**
23. **Property State (if different from current, or for purchase)**
24. **Property Zip Code (if different from current, or for purchase)**

For each field you identify:
* Provide the extracted "field_value".
* Provide a "confidence_score" between 0.0 (no confidence/not found) and 1.0 (very high confidence). If a field is not mentioned or clearly identifiable in the transcript, use a low confidence score (e.g., 0.0 or 0.1) and the field_value can be null, an empty string, or "Not Found".

**VERY IMPORTANT: Respond ONLY with a valid JSON object.** The JSON object should have a single key "fields", which is an array of objects. Each object in the array must have three keys: "field_name" (exactly as listed above), "field_value", and "confidence_score".

Example of the expected JSON structure for a single field:
{
  "field_name": "Borrower First Name",
  "field_value": "John",
  "confidence_score": 0.95
}

Do not include any explanations, apologies, or introductory/closing text outside of the JSON object itself.
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
            "max_tokens": 2000,  # Adjust as needed for expected JSON output size
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        # Call LM Studio API
        response = requests.post(
            LM_STUDIO_URL, 
            headers=headers, 
            json=payload,
            timeout=120  # Increased timeout to 120 seconds (2 minutes)
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
                
            # Validate each field has the required structure
            for field in extracted_data['fields']:
                if not all(key in field for key in ('field_name', 'field_value', 'confidence_score')):
                    raise AIExtractionError("Field is missing required keys")
                    
                # Ensure confidence_score is a float between 0 and 1
                if not isinstance(field['confidence_score'], (int, float)) or not 0 <= field['confidence_score'] <= 1:
                    field['confidence_score'] = float(field['confidence_score']) if isinstance(field['confidence_score'], (str, int)) else 0.0
                    if not 0 <= field['confidence_score'] <= 1:
                        field['confidence_score'] = max(0.0, min(1.0, field['confidence_score']))
            
            return extracted_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {extracted_text}")
            raise AIExtractionError(f"Failed to parse AI response as JSON: {str(e)}")
            
    except requests.RequestException as e:
        logger.error(f"Error calling LM Studio API: {str(e)}")
        raise AIExtractionError(f"Error calling LM Studio API: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in field extraction: {str(e)}")
        raise AIExtractionError(f"Unexpected error in field extraction: {str(e)}") 