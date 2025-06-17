#!/usr/bin/env python
"""
Field Mapping Generator for FormsIQ

This script creates a comprehensive mapping between transcript fields and PDF form fields.
It uses the PDF field analysis data to create more accurate mappings.
"""
import os
import sys
import json
import argparse
import logging
from typing import Dict, List, Any, Set, Tuple, Optional
import difflib
import re

# Add the backend directory to the Python path if needed
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.append(script_dir)

# Import our custom modules
from enhanced_pdf_handler import PDFAnalyzer
from ai_field_mapper import AIFieldMapper

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Common field name patterns to improve matching
FIELD_PATTERNS = {
    # Personal information
    r"(^|[_\s])first[_\s]?name($|[_\s])": ["name", "borrower name", "first", "given name"],
    r"(^|[_\s])middle[_\s]?name($|[_\s])": ["name", "middle", "middle initial"],
    r"(^|[_\s])last[_\s]?name($|[_\s])": ["name", "surname", "family name", "borrower name"],
    r"(^|[_\s])borrower($|[_\s])": ["borrower", "applicant", "loan applicant"],
    r"(^|[_\s])co[_\s]?borrower($|[_\s])": ["co-borrower", "co borrower", "co-applicant"],
    r"(^|[_\s])ssn($|[_\s])": ["social security", "social security number", "ssn", "tax id"],
    r"(^|[_\s])dob($|[_\s])": ["birth", "date of birth", "birthdate", "born"],
    
    # Contact information
    r"(^|[_\s])email($|[_\s])": ["email", "email address", "e-mail"],
    r"(^|[_\s])phone($|[_\s])": ["phone", "telephone", "cell", "mobile"],
    r"(^|[_\s])address($|[_\s])": ["address", "street", "residence"],
    r"(^|[_\s])city($|[_\s])": ["city", "town", "municipality"],
    r"(^|[_\s])state($|[_\s])": ["state", "province", "region"],
    r"(^|[_\s])zip($|[_\s])": ["zip", "zip code", "postal code", "post code"],
    
    # Employment information
    r"(^|[_\s])employer($|[_\s])": ["employer", "employment", "company", "business"],
    r"(^|[_\s])income($|[_\s])": ["income", "salary", "earnings", "monthly income"],
    r"(^|[_\s])job($|[_\s])": ["job", "position", "occupation", "title"],
    
    # Loan information
    r"(^|[_\s])loan($|[_\s])": ["loan", "mortgage", "financing"],
    r"(^|[_\s])amount($|[_\s])": ["amount", "sum", "total", "value"],
    r"(^|[_\s])interest($|[_\s])": ["interest", "rate", "percentage"],
    r"(^|[_\s])term($|[_\s])": ["term", "duration", "period", "length"],
}

# Common field categories with their synonyms
FIELD_CATEGORIES = {
    'name': [
        'name', 'full name', 'legal name', 'borrower name', 'applicant name',
        'first name', 'middle name', 'last name', 'surname', 'given name'
    ],
    'address': [
        'address', 'street address', 'mailing address', 'property address',
        'home address', 'residence', 'location', 'street', 'domicile'
    ],
    'phone': [
        'phone', 'telephone', 'mobile', 'cell', 'phone number', 
        'contact number', 'business phone', 'home phone', 'work phone'
    ],
    'email': [
        'email', 'e-mail', 'email address', 'electronic mail'
    ],
    'ssn': [
        'ssn', 'social security', 'social security number', 'tax id', 
        'tax identification', 'tax number'
    ],
    'dob': [
        'dob', 'date of birth', 'birth date', 'birthdate', 'birthday'
    ],
    'employment': [
        'employer', 'employment', 'job', 'work', 'company', 'business',
        'position', 'title', 'occupation', 'profession'
    ],
    'income': [
        'income', 'salary', 'earnings', 'wages', 'compensation', 'revenue',
        'monthly income', 'annual income', 'gross income', 'net income'
    ],
    'loan': [
        'loan', 'mortgage', 'financing', 'borrowing', 'debt',
        'loan amount', 'mortgage amount', 'financing amount'
    ],
    'property': [
        'property', 'home', 'house', 'real estate', 'residential property',
        'dwelling', 'residence', 'building', 'structure'
    ]
}

# Map transcript field categories to PDF field patterns
# These are common patterns in PDF field names for each category
CATEGORY_TO_PDF_PATTERNS = {
    'name': [
        r'(?:borrower|co-borrower|applicant).*name',
        r'name.*(?:borrower|co-borrower|applicant)',
        r'(?:first|last|middle|full).*name',
        r'name'
    ],
    'address': [
        r'(?:property|subject).*address',
        r'(?:present|current|mailing).*address',
        r'address',
        r'(?:street|city|state|zip)'
    ],
    'phone': [
        r'(?:phone|telephone|cell|mobile)',
        r'contact.*number',
        r'number.*contact'
    ],
    'email': [
        r'email',
        r'e-?mail',
        r'electronic.*mail'
    ],
    'ssn': [
        r'(?:ssn|social|security|tax)',
        r'(?:borrower|co-borrower).*ssn'
    ],
    'dob': [
        r'(?:dob|birth|birthdate)',
        r'date.*birth'
    ],
    'employment': [
        r'(?:employer|employment|job|company)',
        r'(?:position|title|occupation)',
        r'(?:business|work)'
    ],
    'income': [
        r'(?:income|salary|earnings|revenue)',
        r'(?:monthly|annual).*income',
        r'base.*income'
    ],
    'loan': [
        r'(?:loan|mortgage).*(?:amount|term|purpose)',
        r'(?:amount|purpose).*(?:loan|mortgage)'
    ],
    'property': [
        r'(?:property|subject|home|house)',
        r'(?:type|purpose).*property'
    ]
}

def normalize_field_name(field_name: str) -> str:
    """
    Normalize a field name for better matching:
    - Convert to lowercase
    - Replace special characters with spaces
    - Remove common prefixes/suffixes
    - Trim whitespace
    
    Args:
        field_name: The field name to normalize
        
    Returns:
        Normalized field name
    """
    # Convert to lowercase
    name = field_name.lower()
    
    # Replace special characters with spaces
    name = re.sub(r'[^a-z0-9]', ' ', name)
    
    # Remove common prefixes
    prefixes = ['form_', 'field_', 'txt_', 'chk_', 'opt_', 'input_']
    for prefix in prefixes:
        if name.startswith(prefix):
            name = name[len(prefix):]
            
    # Remove common suffixes
    suffixes = ['_field', '_input', '_box', '_text', '_value']
    for suffix in suffixes:
        if name.endswith(suffix):
            name = name[:-len(suffix)]
            
    # Compress multiple spaces into one
    name = re.sub(r'\s+', ' ', name)
    
    return name.strip()


def get_field_patterns(field_name: str) -> Set[str]:
    """
    Get potential pattern matches for a field name
    
    Args:
        field_name: The field name to match
        
    Returns:
        Set of related terms for the field
    """
    related_terms = set()
    normalized = normalize_field_name(field_name)
    
    # Add the normalized field name itself
    related_terms.add(normalized)
    
    # Add words in the field name
    for word in normalized.split():
        if len(word) > 2:  # Skip very short words
            related_terms.add(word)
    
    # Check for pattern matches
    for pattern, terms in FIELD_PATTERNS.items():
        if re.search(pattern, normalized):
            related_terms.update(terms)
    
    return related_terms


def calculate_similarity(source: str, target: str) -> float:
    """
    Calculate similarity between two field names using various methods
    
    Args:
        source: Source field name
        target: Target field name
        
    Returns:
        Similarity score (0-1)
    """
    source_norm = normalize_field_name(source)
    target_norm = normalize_field_name(target)
    
    # Direct match
    if source_norm == target_norm:
        return 1.0
    
    # Sequence similarity
    seq_ratio = difflib.SequenceMatcher(None, source_norm, target_norm).ratio()
    
    # Word overlap
    source_words = set(source_norm.split())
    target_words = set(target_norm.split())
    word_overlap = len(source_words.intersection(target_words)) / max(len(source_words), len(target_words)) if source_words and target_words else 0
    
    # Pattern match
    source_patterns = get_field_patterns(source)
    target_patterns = get_field_patterns(target)
    pattern_overlap = len(source_patterns.intersection(target_patterns)) / max(len(source_patterns), len(target_patterns)) if source_patterns and target_patterns else 0
    
    # Combine scores giving more weight to direct pattern matching
    combined_score = (seq_ratio * 0.3) + (word_overlap * 0.3) + (pattern_overlap * 0.4)
    
    return min(combined_score, 1.0)  # Cap at 1.0


def categorize_transcript_field(field_name: str) -> str:
    """
    Categorize a transcript field name into one of the defined categories.
    
    Args:
        field_name: The field name from the transcript
        
    Returns:
        The category name or 'other' if no matching category
    """
    # Normalize the field name
    norm_field = field_name.lower().strip()
    
    # Check against each category's synonyms
    for category, synonyms in FIELD_CATEGORIES.items():
        for synonym in synonyms:
            if synonym in norm_field or norm_field in synonym:
                return category
    
    return 'other'

def categorize_pdf_field(field_name: str) -> str:
    """
    Categorize a PDF field name into one of the defined categories.
    
    Args:
        field_name: The field name from the PDF
        
    Returns:
        The category name or 'other' if no matching category
    """
    # Normalize the field name
    norm_field = field_name.lower().strip()
    
    # Check against each category's patterns
    for category, patterns in CATEGORY_TO_PDF_PATTERNS.items():
        for pattern in patterns:
            if any(word in norm_field for word in pattern.split('|')):
                return category
    
    return 'other'

def generate_field_mapping(pdf_path: str, transcript_fields: List[str], min_score: float = 0.6) -> Dict[str, Dict]:
    """
    Generate a detailed mapping between transcript fields and PDF form fields
    
    Args:
        pdf_path: Path to the PDF form
        transcript_fields: List of field names from transcript analysis
        min_score: Minimum similarity score to consider a match
        
    Returns:
        Dictionary with mapping details
    """
    # Get the PDF field info
    analyzer = PDFAnalyzer(pdf_path)
    pdf_fields = analyzer.get_field_names()
    pdf_field_info = analyzer.get_all_fields_info()
    
    # Categorize transcript fields
    transcript_categories = {}
    for field in transcript_fields:
        category = categorize_transcript_field(field)
        if category not in transcript_categories:
            transcript_categories[category] = []
        transcript_categories[category].append(field)
    
    # Categorize PDF fields
    pdf_categories = {}
    for field in pdf_fields:
        category = categorize_pdf_field(field)
        if category not in pdf_categories:
            pdf_categories[category] = []
        pdf_categories[category].append(field)
    
    # Generate the mapping
    mapping = {}
    mapping_details = {
        'pdf_path': pdf_path,
        'total_transcript_fields': len(transcript_fields),
        'total_pdf_fields': len(pdf_fields),
        'transcript_categories': transcript_categories,
        'pdf_categories': pdf_categories,
        'mappings': {}
    }
    
    # Use the AI Field Mapper for the actual mapping
    field_mapper = AIFieldMapper(pdf_path, min_score=min_score)
    mapping = field_mapper.generate_mapping(transcript_fields)
    
    # Add detailed mapping information
    for transcript_field, pdf_field in mapping.items():
        t_category = categorize_transcript_field(transcript_field)
        p_category = categorize_pdf_field(pdf_field)
        similarity = difflib.SequenceMatcher(None, transcript_field.lower(), pdf_field.lower()).ratio()
        
        mapping_details['mappings'][transcript_field] = {
            'transcript_field': transcript_field,
            'pdf_field': pdf_field,
            'transcript_category': t_category,
            'pdf_category': p_category,
            'similarity_score': similarity,
            'pdf_field_info': pdf_field_info.get(pdf_field, {})
        }
    
    # Calculate coverage statistics
    covered_fields = len(mapping)
    coverage_percent = round((covered_fields / len(transcript_fields) * 100), 2) if transcript_fields else 0
    
    mapping_details['coverage_statistics'] = {
        'mapped_fields': covered_fields,
        'unmapped_fields': len(transcript_fields) - covered_fields,
        'coverage_percent': coverage_percent,
        'unmapped_transcript_fields': [f for f in transcript_fields if f not in mapping]
    }
    
    return {
        'mapping': mapping,
        'details': mapping_details
    }

def load_transcript_fields(file_path: str) -> List[str]:
    """
    Load transcript fields from a JSON file
    
    Args:
        file_path: Path to the JSON file with extracted fields
        
    Returns:
        List of transcript field names
    """
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    # Handle different formats
    if isinstance(data, list):
        # Simple list of field names
        return data
    elif isinstance(data, dict):
        # Check for different structures
        if 'extracted_fields' in data:
            return [field.get('field_name') for field in data['extracted_fields'] 
                   if 'field_name' in field]
        elif 'potential_field_names' in data:
            return data['potential_field_names']
        else:
            # Try to extract field names from any fields with field_name key
            field_names = []
            for key, value in data.items():
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict) and 'field_name' in item:
                            field_names.append(item['field_name'])
            return field_names
    
    # If we couldn't parse the file, return an empty list
    logger.warning(f"Could not extract field names from {file_path}")
    return []

def main():
    """CLI entry point"""
    if len(sys.argv) < 3:
        print("Usage: python field_mapping_generator.py <pdf_file> <transcript_fields_json> [output_json] [min_score]")
        print("  <pdf_file>: Path to the PDF form")
        print("  <transcript_fields_json>: JSON file with extracted transcript fields")
        print("  [output_json]: Output file for the mapping (default: mapping.json)")
        print("  [min_score]: Minimum similarity score (0.0-1.0, default: 0.6)")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    transcript_fields_path = sys.argv[2]
    output_path = sys.argv[3] if len(sys.argv) > 3 else 'mapping.json'
    min_score = float(sys.argv[4]) if len(sys.argv) > 4 else 0.6
    
    try:
        # Load transcript fields
        print(f"Loading transcript fields from {transcript_fields_path}...")
        transcript_fields = load_transcript_fields(transcript_fields_path)
        
        if not transcript_fields:
            print("Error: No transcript fields found in the input file.")
            sys.exit(1)
        
        print(f"Generating mapping for {len(transcript_fields)} transcript fields...")
        
        # Generate the mapping
        result = generate_field_mapping(pdf_path, transcript_fields, min_score)
        
        # Save the mapping
        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2)
        
        # Print coverage statistics
        coverage = result['details']['coverage_statistics']
        
        print("\n=== Field Mapping Results ===")
        print(f"PDF Form: {pdf_path}")
        print(f"Transcript Fields: {len(transcript_fields)}")
        print(f"Mapped Fields: {coverage['mapped_fields']} ({coverage['coverage_percent']}%)")
        print(f"Unmapped Fields: {coverage['unmapped_fields']}")
        
        # Print sample mappings
        print("\nSample Mappings:")
        sample_count = min(5, len(result['mapping']))
        for i, (t_field, p_field) in enumerate(list(result['mapping'].items())[:sample_count]):
            print(f"  {t_field} → {p_field}")
        
        if len(result['mapping']) > sample_count:
            print(f"  ... and {len(result['mapping']) - sample_count} more")
        
        print(f"\nMapping saved to: {output_path}")
        
    except Exception as e:
        print(f"Error generating field mapping: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 