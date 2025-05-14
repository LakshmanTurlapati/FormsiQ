"""
Service to interact with Grok 3 Mini API for field extraction from transcripts.
"""
import json
import logging
import re
import requests
import os
from dotenv import load_dotenv
from django.conf import settings
from openai import OpenAI

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Grok API endpoint and key from .env
GROK_API_URL = os.getenv("GROK_API_URL", "https://api.x.ai/v1/chat/completions")
GROK_API_KEY = os.getenv("GROK_API_KEY")

logger.info(f"Loaded Grok API key: {'PRESENT' if GROK_API_KEY else 'MISSING'}")
logger.info(f"Loaded Grok API URL: {GROK_API_URL}")

# Define custom exception
class GrokExtractionError(Exception):
    """Exception raised for errors in the Grok extraction process."""
    pass

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
25. **Mortgage Type** (e.g., VA, FHA, Conventional, USDA)
26. **Amortization Type** (e.g., Fixed Rate, ARM, GPM)
27. **Property Usage** (e.g., Primary Residence, Second Home, Investment)

IMPORTANT: During your reasoning process, you MUST analyze and extract all available fields from the transcript, then generate a valid JSON object containing these fields in the following format:

```json
{
  "fields": [
    {
      "field_name": "Borrower First Name",
      "field_value": "John",
      "confidence_score": 0.95
    },
    ...
  ]
}
```

For each field:
* Provide the extracted "field_value".
* Provide a "confidence_score" between 0.0 (no confidence/not found) and 1.0 (very high confidence). If a field is not mentioned or clearly identifiable in the transcript, use a low confidence score (e.g., 0.0 or 0.1) and the field_value can be null, an empty string, or "Not Found".

Pay special attention to checkboxes like Mortgage Type, Amortization Type, and Property Usage. If you find these values in the transcript, be sure to extract them with the appropriate confidence score.

Make sure to include the JSON output in your reasoning process, as it's critical for proper extraction.
"""


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
    logger.error(f"Could not extract valid JSON from Grok response: {text}")
    raise json.JSONDecodeError("Could not extract valid JSON from Grok response", text, 0)


def fix_incomplete_json(text):
    """
    Attempts to fix incomplete JSON by closing any unclosed brackets, quotes, etc.
    
    Args:
        text (str): The potentially incomplete JSON string
        
    Returns:
        str: A fixed JSON string that should be parseable
    """
    logger.info(f"Attempting to fix JSON: {text[:100]}...")
    
    # First try to extract JSON from a code block if it exists
    json_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if json_block_match:
        extracted_json = json_block_match.group(1).strip()
        logger.info(f"Extracted JSON from code block: {extracted_json[:100]}...")
        text = extracted_json
    
    # Find field objects in the text using regex patterns
    field_objects = []
    
    # Pattern to match field objects that span multiple lines
    field_pattern = re.compile(r'{\s*"field_name"\s*:\s*"([^"]+)",\s*"field_value"\s*:\s*(?:"([^"]*)"|(null)),\s*"confidence_score"\s*:\s*([\d.]+)\s*}', re.DOTALL)
    
    # Find all complete field objects
    for match in field_pattern.finditer(text):
        field_name, field_value_str, field_value_null, confidence_score = match.groups()
        field_value = field_value_null if field_value_null else field_value_str
        field_value = None if field_value == "null" else field_value
        
        try:
            confidence = float(confidence_score)
            field_objects.append({
                "field_name": field_name,
                "field_value": field_value,
                "confidence_score": confidence
            })
        except (ValueError, TypeError):
            # If confidence_score can't be converted to float, use default
            field_objects.append({
                "field_name": field_name,
                "field_value": field_value,
                "confidence_score": 0.5
            })
    
    # If we found field objects, construct a valid JSON with them
    if field_objects:
        logger.info(f"Extracted {len(field_objects)} field objects directly")
        return json.dumps({"fields": field_objects})
    
    # If no field objects found, look for name-value pairs in a simpler pattern
    simple_field_pattern = re.compile(r'(?:"|\*)([^:"]*?)(?:"|:)?\s*(?:\*|\(|:)?\s*(?:"?)([^",\n\)]+)(?:"|\)|,)?', re.MULTILINE)
    field_pairs = {}
    
    for match in simple_field_pattern.finditer(text):
        field_name, field_value = match.groups()
        field_name = field_name.strip().lower().replace(' ', '_')
        field_value = field_value.strip()
        
        # Skip if either name or value is empty or if field_name contains common words that aren't fields
        if not field_name or not field_value or field_name in ['the', 'and', 'this', 'that', 'with', 'from', 'for']:
            continue
            
        # Normalize common field names
        if 'first' in field_name and 'name' in field_name:
            field_name = 'borrower_first_name'
        elif 'last' in field_name and 'name' in field_name:
            field_name = 'borrower_last_name'
        elif 'address' in field_name:
            field_name = 'property_address'
        elif 'loan' in field_name and 'amount' in field_name:
            field_name = 'loan_amount'
        elif 'type' in field_name and ('mortgage' in field_name or 'loan' in field_name):
            field_name = 'mortgage_type'
        elif 'purpose' in field_name:
            field_name = 'loan_purpose'
        
        field_pairs[field_name] = field_value
    
    # Convert field_pairs to our standard format
    if field_pairs:
        logger.info(f"Extracted {len(field_pairs)} field pairs using simple pattern")
        simple_fields = []
        for name, value in field_pairs.items():
            simple_fields.append({
                "field_name": name,
                "field_value": value,
                "confidence_score": 0.5
            })
        return json.dumps({"fields": simple_fields})
    
    logger.warning("Could not extract any fields from the text")
    return text  # Return original if we couldn't extract anything


def extract_fields_with_grok(transcript):
    """
    Extract fields from a transcript using the Grok 3 Mini API.
    
    Args:
        transcript (str): The call transcript to analyze
        
    Returns:
        dict: The structured field data extracted from the transcript
    """
    # Check if API key is present
    if not GROK_API_KEY:
        logger.error("No Grok API key found in environment variables")
        return grok_field_extraction_wrapper(transcript)
    
    try:
        logger.info("Initializing Grok API client with OpenAI library")
        
        # Initialize OpenAI client with xAI base URL and API key
        client = OpenAI(
            api_key=GROK_API_KEY,
            base_url="https://api.x.ai/v1",
        )
        
        logger.info("Sending request to Grok API for chat completion")
        
        # Make the API call using the client
        completion = client.chat.completions.create(
            model="grok-3-mini",  # Using grok-3-mini model
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": transcript}
            ],
            temperature=0.1,
            max_tokens=4000,  # Increased for more complete reasoning
        )
        
        logger.info("Grok API response received successfully")
        logger.info(f"Model used: {completion.model}")
        
        # Try to get content from different possible sources
        content = None
        source = None
        
        # Check regular content first
        if hasattr(completion.choices[0].message, 'content') and completion.choices[0].message.content:
            content = completion.choices[0].message.content
            source = "content"
        
        # If not, check reasoning_content
        elif hasattr(completion.choices[0].message, 'reasoning_content') and completion.choices[0].message.reasoning_content:
            content = completion.choices[0].message.reasoning_content
            source = "reasoning_content"
        
        if not content:
            logger.error("No content or reasoning_content found in Grok response")
            logger.info(f"Response object: {completion}")
            return grok_field_extraction_wrapper(transcript)
        
        logger.info(f"Using {source}, content length: {len(content)}")
        logger.info(f"Raw content from Grok: {content[:200]}...")
        
        # Process the response to extract the fields
        try:
            # First try to extract JSON from markdown code blocks if present
            json_block_pattern = r"```(?:json)?\s*([\s\S]*?)```"
            match = re.search(json_block_pattern, content)
            if match:
                logger.info("Found JSON code block in content")
                extracted_json = match.group(1).strip()
                try:
                    parsed_data = json.loads(extracted_json)
                    logger.info("Successfully parsed JSON from code block")
                    
                    # Check if we have the expected structure
                    if isinstance(parsed_data, dict) and 'fields' in parsed_data:
                        logger.info(f"Found {len(parsed_data['fields'])} fields in JSON code block")
                        
                        # Process fields to ensure proper structure
                        for field in parsed_data['fields']:
                            # Ensure field values are strings
                            if field.get('field_value') is None:
                                field['field_value'] = ""
                            else:
                                field['field_value'] = str(field['field_value'])
                                
                            # Ensure confidence_score is a float between 0 and 1
                            try:
                                field['confidence_score'] = float(field['confidence_score'])
                                if field['confidence_score'] < 0:
                                    field['confidence_score'] = 0.0
                                elif field['confidence_score'] > 1:
                                    field['confidence_score'] = 1.0
                            except (ValueError, TypeError):
                                field['confidence_score'] = 0.5
                        
                        return parsed_data
                except json.JSONDecodeError:
                    logger.warning("JSON in code block is not valid, will try other methods")
            
            # Try fixing and parsing the entire content
            fixed_json = fix_incomplete_json(content)
            
            try:
                parsed_data = json.loads(fixed_json)
                logger.info("Successfully parsed JSON from Grok API response")
                
                # If parsed_data is an array, wrap it in a fields object
                if isinstance(parsed_data, list):
                    parsed_data = {"fields": parsed_data}
                
                # Check if we have the expected structure
                if isinstance(parsed_data, dict) and 'fields' in parsed_data:
                    logger.info(f"Found {len(parsed_data['fields'])} fields in response")
                    
                    # Process fields to ensure proper structure
                    for field in parsed_data['fields']:
                        # Ensure field values are strings
                        if field.get('field_value') is None:
                            field['field_value'] = ""
                        else:
                            field['field_value'] = str(field['field_value'])
                            
                        # Ensure confidence_score is a float between 0 and 1
                        try:
                            field['confidence_score'] = float(field['confidence_score'])
                            if field['confidence_score'] < 0:
                                field['confidence_score'] = 0.0
                            elif field['confidence_score'] > 1:
                                field['confidence_score'] = 1.0
                        except (ValueError, TypeError):
                            field['confidence_score'] = 0.5
                    
                    return parsed_data
                
                logger.warning("Parsed data doesn't have expected structure")
                
            except json.JSONDecodeError as json_err:
                logger.warning(f"JSON parsing failed: {json_err}")
            
            # Use the fallback extraction for all cases where JSON parsing fails
            logger.warning("Using fallback field extraction")
            return grok_field_extraction_wrapper(transcript)
            
        except Exception as processing_err:
            logger.error(f"Error processing Grok response: {str(processing_err)}")
            return grok_field_extraction_wrapper(transcript)
    
    except Exception as api_err:
        logger.error(f"Error calling Grok API: {str(api_err)}")
        logger.error(f"Error type: {type(api_err).__name__}")
        return grok_field_extraction_wrapper(transcript)


def grok_field_extraction_wrapper(transcript):
    """
    Fallback function that returns a minimal response with default fields
    when the main extraction method fails.
    
    Args:
        transcript (str): The call transcript to analyze
        
    Returns:
        dict: A minimal structured field data with some default values
    """
    logger.warning("Using fallback field extraction wrapper")
    
    # Define all the field names from the system prompt
    field_names = [
        "Borrower First Name",
        "Borrower Middle Name",
        "Borrower Last Name",
        "Borrower Suffix",
        "Social Security Number",
        "Date of Birth",
        "Current Street Address",
        "Current City",
        "Current State",
        "Current Zip Code",
        "Primary Phone Number",
        "Email Address",
        "Marital Status",
        "Current Employer Name",
        "Job Title/Position",
        "Employment Start Date",
        "Monthly Income (Base)",
        "Monthly Income (Other, specify source if possible)",
        "Loan Amount Requested",
        "Loan Purpose",
        "Property Street Address (if different from current, or for purchase)",
        "Property City (if different from current, or for purchase)",
        "Property State (if different from current, or for purchase)",
        "Property Zip Code (if different from current, or for purchase)",
        "Mortgage Type",
        "Amortization Type",
        "Property Usage",
    ]
    
    # Try to extract some basic information from the transcript
    fields = []
    
    # Basic field extraction patterns
    name_pattern = re.search(r'(?:name|caller|I am)[^a-zA-Z]*([\w\s]+)', transcript, re.IGNORECASE)
    if name_pattern:
        name_parts = name_pattern.group(1).strip().split()
        if len(name_parts) > 0:
            fields.append({
                "field_name": "Borrower First Name",
                "field_value": name_parts[0],
                "confidence_score": 0.5
            })
            if len(name_parts) > 1:
                if len(name_parts) > 2:
                    fields.append({
                        "field_name": "Borrower Middle Name",
                        "field_value": name_parts[1],
                        "confidence_score": 0.5
                    })
                fields.append({
                    "field_name": "Borrower Last Name",
                    "field_value": name_parts[-1],
                    "confidence_score": 0.5
                })
    
    # Look for address
    address_pattern = re.search(r'(?:address|live at|located at|property at)[^a-zA-Z]*([\w\s\.,]+)', transcript, re.IGNORECASE)
    if address_pattern:
        address = address_pattern.group(1).strip()
        if "purchase" in transcript.lower():
            fields.append({
                "field_name": "Property Street Address (if different from current, or for purchase)",
                "field_value": address,
                "confidence_score": 0.5
            })
        else:
            fields.append({
                "field_name": "Current Street Address",
                "field_value": address,
                "confidence_score": 0.5
            })
    
    # Look for loan amount
    amount_pattern = re.search(r'(?:loan|amount|borrow|financing)[^a-zA-Z]*(?:[$])?(\d[\d,]+(?:\.\d+)?)', transcript, re.IGNORECASE)
    if amount_pattern:
        fields.append({
            "field_name": "Loan Amount Requested",
            "field_value": amount_pattern.group(1).strip().replace(',', ''),
            "confidence_score": 0.5
        })
    
    # Look for mortgage type
    if re.search(r'\bconventional\b', transcript, re.IGNORECASE):
        fields.append({
            "field_name": "Mortgage Type",
            "field_value": "Conventional",
            "confidence_score": 0.5
        })
    elif re.search(r'\bFHA\b', transcript):
        fields.append({
            "field_name": "Mortgage Type",
            "field_value": "FHA",
            "confidence_score": 0.5
        })
    elif re.search(r'\bVA\b', transcript):
        fields.append({
            "field_name": "Mortgage Type", 
            "field_value": "VA",
            "confidence_score": 0.5
        })
    
    # Look for loan purpose
    if re.search(r'\b(?:purchase|buying|buy)\b', transcript, re.IGNORECASE):
        fields.append({
            "field_name": "Loan Purpose",
            "field_value": "Purchase",
            "confidence_score": 0.5
        })
    elif re.search(r'\b(?:refinance|refi)\b', transcript, re.IGNORECASE):
        fields.append({
            "field_name": "Loan Purpose",
            "field_value": "Refinance",
            "confidence_score": 0.5
        })
    
    # Look for property usage
    if re.search(r'\b(?:primary|live|residence)\b', transcript, re.IGNORECASE):
        fields.append({
            "field_name": "Property Usage",
            "field_value": "Primary Residence",
            "confidence_score": 0.5
        })
    elif re.search(r'\b(?:invest|rental|investment)\b', transcript, re.IGNORECASE):
        fields.append({
            "field_name": "Property Usage",
            "field_value": "Investment",
            "confidence_score": 0.5
        })
    elif re.search(r'\b(?:second|vacation)\b', transcript, re.IGNORECASE):
        fields.append({
            "field_name": "Property Usage",
            "field_value": "Second Home",
            "confidence_score": 0.5
        })
    
    # Add any missing fields with empty values
    existing_field_names = [field["field_name"] for field in fields]
    
    for field_name in field_names:
        if field_name not in existing_field_names:
            fields.append({
                "field_name": field_name,
                "field_value": "",
                "confidence_score": 0.0
            })
    
    fallback_response = {"fields": fields}
    
    logger.warning(f"Returning fallback response with {len(fields)} fields")
    return fallback_response 