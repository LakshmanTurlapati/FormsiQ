#!/usr/bin/env python
"""
AI Field Mapper for FormsIQ

This module provides intelligent mapping between extracted field data and PDF form fields.
It uses a combination of techniques:
1. Direct string matching
2. Fuzzy matching based on string similarity
3. Semantic matching based on field meaning

This helps build a robust mapping between the fields identified by the AI in transcripts 
and the actual field names in fillable PDFs.
"""

import os
import sys
import json
import logging
import difflib
import re
from typing import Dict, List, Tuple, Optional, Set, Any
from dataclasses import dataclass

# Import our enhanced PDF handler
from enhanced_pdf_handler import PDFAnalyzer

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Common variations and synonyms for field names
FIELD_SYNONYMS = {
    # Personal information
    'first name': ['given name', 'forename', 'first', 'firstname', 'first_name', 'fname'],
    'middle name': ['middle initial', 'middle', 'mi', 'middlename', 'middle_name', 'mname'],
    'last name': ['surname', 'family name', 'last', 'lastname', 'last_name', 'lname'],
    'suffix': ['name suffix', 'suffix_name', 'namesuffix', 'sfx', 'jr sr ii iii iv'],
    'email': ['email address', 'e-mail', 'electronic mail', 'email_address', 'applicant_email'],
    'phone': ['telephone', 'mobile', 'cell', 'phone number', 'contact number', 'phone_number', 'cellphone', 'primary_phone'],
    'home phone': ['home telephone', 'landline', 'house phone', 'home_phone', 'homephone'],
    'work phone': ['business phone', 'office phone', 'work_phone', 'workphone', 'business_phone', 'employer_phone'],
    'cell phone': ['mobile phone', 'cellular', 'mobile_phone', 'cellphone', 'cell_phone'],
    
    # Address information
    'address': ['street address', 'mailing address', 'residence', 'street', 'address1', 'addr', 'current_address'],
    'street': ['street address', 'address line 1', 'address1', 'addr1', 'street_address', 'current_street'],
    'city': ['town', 'municipality', 'city name', 'cityname', 'current_city'],
    'state': ['province', 'region', 'state name', 'statename', 'current_state'],
    'zip': ['zip code', 'postal code', 'post code', 'zipcode', 'current_zip'],
    'property address': ['subject property', 'property street', 'property location', 'property_addr', 'property_street'],
    'property city': ['subject city', 'property city', 'city of property', 'property_city'],
    'property state': ['subject state', 'property state', 'state of property', 'property_state'],
    'property zip': ['subject zip', 'property zip code', 'property zip', 'zipcode of property', 'property_zip'],
    
    # Personal identification
    'ssn': ['social security', 'social security number', 'tax id', 'tax identification', 'social', 'ssn_number'],
    'dob': ['date of birth', 'birth date', 'birthdate', 'birthday', 'birth_date', 'date_of_birth', 'dateofbirth'],
    'years of school': ['education years', 'school years', 'years of education', 'education_years', 'schooling'],
    'marital status': ['married status', 'single or married', 'marital_status', 'marriage_status'],
    'number of dependents': ['dependents', 'dependent count', 'number_of_dependents', 'num_dependents', 'dependent_count'],
    
    # Employment information
    'employer': ['employer name', 'company', 'business name', 'place of work', 'employer_name', 'company_name'],
    'employer address': ['business address', 'company address', 'work address', 'employer_address', 'company_address'],
    'job title': ['position', 'occupation', 'title', 'role', 'job_title', 'job_position', 'profession'],
    'years at job': ['years employed', 'years with employer', 'time at job', 'employment_duration', 'years_employed', 'years_at_job'],
    'years in profession': ['professional experience', 'years in field', 'experience years', 'profession_years', 'field_experience'],
    'self employed': ['business owner', 'independent', 'own business', 'self_employed', 'selfemployed'],
    
    # Income information
    'monthly income': ['income per month', 'monthly earnings', 'monthly salary', 'monthly_income', 'income_monthly', 'month_income'],
    'annual income': ['yearly income', 'income per year', 'annual earnings', 'yearly salary', 'annual_income', 'income_yearly', 'year_income'],
    'other income': ['additional income', 'extra income', 'secondary income', 'other_income', 'income_other', 'extra_earnings'],
    
    # Loan information
    'loan amount': ['mortgage amount', 'amount of loan', 'borrow amount', 'loan_amount', 'mortgage_amount'],
    'loan purpose': ['purpose of loan', 'reason for loan', 'loan_purpose', 'purpose', 'mortgage_purpose'],
    'loan term': ['mortgage term', 'term of loan', 'loan duration', 'loan_term', 'term_years', 'loan_length'],
    'interest rate': ['rate', 'loan rate', 'mortgage rate', 'interest', 'interest_rate', 'rate_interest'],
    'rate type': ['loan type', 'mortgage type', 'type of rate', 'rate_type', 'interest_type'],
    
    # Property information
    'property type': ['home type', 'residence type', 'dwelling type', 'property_type', 'type_of_property'],
    'number of units': ['unit count', 'units in property', 'number_of_units', 'unit_count', 'units'],
    'property use': ['use of property', 'property purpose', 'home use', 'property_use', 'use_of_home'],
    'year built': ['construction year', 'built in', 'year_built', 'construction_date', 'built_year'],
    
    # Asset information
    'checking account': ['checking balance', 'checking', 'checking_account', 'checking_balance'],
    'savings account': ['savings balance', 'savings', 'savings_account', 'savings_balance'],
    'retirement account': ['401k', 'ira', 'retirement savings', 'retirement_account', 'retirement_balance'],
    
    # Liability information
    'car loan': ['auto loan', 'vehicle loan', 'auto payment', 'car_loan', 'vehicle_payment'],
    'credit card debt': ['credit card balance', 'card debt', 'credit_card_debt', 'cc_debt', 'creditcard_balance'],
    'student loan': ['education loan', 'college debt', 'student_loan', 'education_debt', 'student_debt'],
    
    # Declaration questions
    'bankruptcy': ['filed bankruptcy', 'declared bankruptcy', 'bankruptcy filing', 'bankruptcy_history'],
    'foreclosure': ['home foreclosure', 'foreclosure history', 'foreclosed', 'foreclosure_experience'],
    'lawsuit': ['legal action', 'litigation', 'court case', 'legal_action', 'pending_litigation'],
    'us citizen': ['citizenship', 'american citizen', 'citizen status', 'citizenship_status', 'us_citizenship'],
    'alimony': ['alimony payment', 'spousal support', 'alimony_payment', 'spousal_support'],
    'child support': ['child support payment', 'family support', 'child_support', 'support_payment'],
    'borrowed down payment': ['down payment loan', 'borrowed deposit', 'down_payment_loan', 'borrowed_down_payment'],
    'co signer': ['co-maker', 'endorser', 'co borrower', 'guarantor', 'co_signer', 'co_borrower'],
    'primary residence': ['main home', 'principal dwelling', 'primary_residence', 'main_residence'],
    'prior ownership': ['previous home', 'owned before', 'prior_property', 'previous_ownership', 'home_ownership_history'],
}

# Add common field name prefixes/suffixes to recognize in PDF form fields
FORM_FIELD_PATTERNS = {
    'borrower': ['borrower', 'applicant', 'primary', 'primary borrower', 'primary applicant', 'b1'],
    'co-borrower': ['co-borrower', 'co borrower', 'coborrower', 'co-applicant', 'coapplicant', 'secondary', 'b2'],
    'property': ['property', 'subject', 'subject property', 'real estate'],
    'employment': ['employment', 'employer', 'job', 'occupation', 'work'],
    'income': ['income', 'earnings', 'salary', 'compensation', 'wages'],
    'asset': ['asset', 'assets', 'account', 'accounts', 'holdings'],
    'liability': ['liability', 'liabilities', 'debt', 'debts', 'obligation'],
    'declaration': ['declaration', 'question', 'info', 'information'],
}

# Add checkbox field synonyms
CHECKBOX_FIELD_SYNONYMS = {
    # Mortgage types
    'va': ['va loan', 'veterans affairs', 'veterans administration', 'va mortgage', 'veteran'],
    'fha': ['fha loan', 'federal housing administration', 'fha mortgage'],
    'conventional': ['conventional loan', 'conventional mortgage', 'standard mortgage', 'regular mortgage'],
    'usda': ['usda loan', 'rural housing', 'rural development', 'rural housing service', 'usda/rural'],
    
    # Amortization types
    'fixed rate': ['fixed', 'fixed interest', 'fixed interest rate', 'fixed payment', 'fixed mortgage'],
    'gpm': ['graduated payment', 'graduated payment mortgage', 'graduated', 'graduated mortgage'],
    'arm': ['adjustable rate', 'adjustable', 'adjustable rate mortgage', 'variable rate', 'variable'],
    
    # Loan purpose
    'purchase': ['buy', 'buying', 'purchasing', 'acquisition', 'home purchase'],
    'refinance': ['refi', 'refinancing', 'mortgage refinance', 'loan refinance'],
    'construction': ['building', 'new construction', 'constructing', 'build'],
    'construction-permanent': ['construction to permanent', 'construction perm', 'c-p loan', 'c to p'],
    
    # Property usage
    'primary residence': ['main home', 'principal dwelling', 'primary home', 'main residence'],
    'secondary residence': ['second home', 'vacation home', 'second property'],
    'investment': ['investment property', 'rental', 'rental property', 'investment home'],
    
    # Property type
    'fee simple': ['fee ownership', 'freehold', 'complete ownership', 'outright ownership'],
    'leasehold': ['lease', 'leased land', 'ground lease', 'leased property'],
}

@dataclass
class FieldMatch:
    """Class representing a potential match between fields"""
    source_field: str  # Field name from extracted data
    target_field: str  # Field name in PDF
    score: float       # Match score (0-1)
    match_type: str    # Type of match (exact, fuzzy, semantic)


class AIFieldMapper:
    """
    Class to intelligently map between extracted field names from AI 
    and actual field names in the PDF form.
    """
    
    def __init__(self, pdf_path: str, min_score: float = 0.6):
        """
        Initialize the mapper with the PDF path
        
        Args:
            pdf_path: Path to the PDF form
            min_score: Minimum score for considering a match (0-1)
        """
        self.pdf_analyzer = PDFAnalyzer(pdf_path)
        self.pdf_fields = self.pdf_analyzer.get_field_names()
        self.min_score = min_score
        self.field_mapping = {}  # Will be populated when generate_mapping is called
        self.checkbox_fields = {}  # Will hold checkbox fields and their mapping
        
        # Identify likely checkbox fields
        self._identify_checkbox_fields()
        
    def _identify_checkbox_fields(self):
        """Identify fields that are likely checkboxes based on naming patterns"""
        checkbox_patterns = [
            r'check', r'chk', r'checkbox', r'cb_', r'_cb',
            r'va', r'fha', r'conventional', r'usda',
            r'fixed', r'gpm', r'arm',
            r'purchase', r'refinance', r'construction', 
            r'primary', r'secondary', r'investment',
            r'fee_simple', r'leasehold'
        ]
        
        for field in self.pdf_fields:
            normalized = self._normalize_field_name(field).lower()
            if any(re.search(pattern, normalized) for pattern in checkbox_patterns):
                self.checkbox_fields[field] = self._determine_checkbox_type(field)
    
    def _determine_checkbox_type(self, field_name: str) -> str:
        """Determine the type of checkbox field"""
        normalized = self._normalize_field_name(field_name).lower()
        
        for category, terms in {
            'mortgage_type': ['va', 'fha', 'conventional', 'usda', 'rural'],
            'amortization_type': ['fixed', 'gpm', 'arm', 'adjustable'],
            'loan_purpose': ['purchase', 'refinance', 'construction', 'permanent'],
            'property_usage': ['primary', 'secondary', 'investment'],
            'estate_type': ['fee', 'simple', 'leasehold']
        }.items():
            if any(term in normalized for term in terms):
                return category
                
        return 'other'
    
    def _normalize_field_name(self, field_name: str) -> str:
        """Normalize a field name by lowercasing and removing common prefixes/suffixes"""
        field = field_name.lower().strip()
        
        # Remove common prefixes
        prefixes = ['form_', 'field_', 'txt_', 'chk_', 'opt_', 'input_']
        for prefix in prefixes:
            if field.startswith(prefix):
                field = field[len(prefix):]
                
        # Remove common suffixes
        suffixes = ['_field', '_input', '_box', '_text', '_value']
        for suffix in suffixes:
            if field.endswith(suffix):
                field = field[:-len(suffix)]
                
        return field.strip()
    
    def _get_exact_matches(self, 
                         extracted_fields: List[str]) -> Dict[str, FieldMatch]:
        """Find exact matches between extracted fields and PDF fields"""
        matches = {}
        
        # Create normalized versions of PDF fields
        normalized_pdf_fields = {
            self._normalize_field_name(f): f for f in self.pdf_fields
        }
        
        # Check for exact matches
        for ext_field in extracted_fields:
            norm_ext = self._normalize_field_name(ext_field)
            
            if norm_ext in normalized_pdf_fields:
                pdf_field = normalized_pdf_fields[norm_ext]
                matches[ext_field] = FieldMatch(
                    source_field=ext_field,
                    target_field=pdf_field,
                    score=1.0,
                    match_type="exact"
                )
                
        return matches
    
    def _get_fuzzy_matches(self, 
                        extracted_fields: List[str], 
                        excluded_targets: Set[str]) -> Dict[str, FieldMatch]:
        """Find fuzzy matches based on string similarity"""
        matches = {}
        available_pdf_fields = [f for f in self.pdf_fields if f not in excluded_targets]
        
        for ext_field in extracted_fields:
            norm_ext = self._normalize_field_name(ext_field)
            
            # Get the closest match
            closest_matches = difflib.get_close_matches(
                norm_ext, 
                [self._normalize_field_name(f) for f in available_pdf_fields],
                n=1,
                cutoff=self.min_score
            )
            
            if closest_matches:
                closest_norm = closest_matches[0]
                
                # Find the original field name
                for pdf_field in available_pdf_fields:
                    if self._normalize_field_name(pdf_field) == closest_norm:
                        # Compute similarity score
                        score = difflib.SequenceMatcher(None, norm_ext, closest_norm).ratio()
                        
                        matches[ext_field] = FieldMatch(
                            source_field=ext_field,
                            target_field=pdf_field,
                            score=score,
                            match_type="fuzzy"
                        )
                        break
                        
        return matches
    
    def _get_semantic_matches(self, 
                           extracted_fields: List[str], 
                           excluded_targets: Set[str]) -> Dict[str, FieldMatch]:
        """Find semantic matches based on field meaning and common synonyms"""
        matches = {}
        available_pdf_fields = [f for f in self.pdf_fields if f not in excluded_targets]
        
        # Build synonym dictionary for PDF fields
        pdf_field_synonyms = {}
        for pdf_field in available_pdf_fields:
            norm_field = self._normalize_field_name(pdf_field)
            pdf_field_synonyms[pdf_field] = [norm_field]
            
            # Add common synonyms
            for concept, variations in FIELD_SYNONYMS.items():
                if concept in norm_field or any(var in norm_field for var in variations):
                    pdf_field_synonyms[pdf_field].extend(variations)
                    pdf_field_synonyms[pdf_field].append(concept)
        
        # Add form field patterns recognition
        pdf_field_categories = {}
        for pdf_field in available_pdf_fields:
            norm_field = self._normalize_field_name(pdf_field)
            # Categorize fields based on patterns
            for category, patterns in FORM_FIELD_PATTERNS.items():
                if any(pattern in norm_field for pattern in patterns):
                    if pdf_field not in pdf_field_categories:
                        pdf_field_categories[pdf_field] = []
                    pdf_field_categories[pdf_field].append(category)
        
        # Check for semantic matches
        for ext_field in extracted_fields:
            norm_ext = self._normalize_field_name(ext_field)
            best_match = None
            best_score = 0
            
            # First try direct semantic matching with synonyms
            for pdf_field, synonyms in pdf_field_synonyms.items():
                for synonym in synonyms:
                    if (synonym in norm_ext or norm_ext in synonym or 
                        difflib.SequenceMatcher(None, norm_ext, synonym).ratio() > 0.7):
                        # Calculate a score based on the similarity
                        score = difflib.SequenceMatcher(None, norm_ext, synonym).ratio()
                        if score > best_score and score >= self.min_score:
                            best_score = score
                            best_match = pdf_field
                        
            # If no good match yet, try category-based matching
            if not best_match or best_score < 0.8:
                # Try to identify the field category
                field_category = None
                for category, patterns in FORM_FIELD_PATTERNS.items():
                    if any(pattern in norm_ext for pattern in patterns):
                        field_category = category
                        break
                        
                if field_category:
                    # Look for PDF fields in the same category
                    for pdf_field, categories in pdf_field_categories.items():
                        if field_category in categories:
                            # For fields in the same category, do another matching pass
                            for concept, variations in FIELD_SYNONYMS.items():
                                if concept in norm_ext or any(var in norm_ext for var in variations):
                                    # Get the normalized PDF field name for comparison
                                    norm_pdf = self._normalize_field_name(pdf_field)
                                    
                                    # Check if this concept appears in the PDF field
                                    if (concept in norm_pdf or 
                                        any(var in norm_pdf for var in variations)):
                                        
                                        # Calculate a score that factors in the category match
                                        base_score = difflib.SequenceMatcher(None, norm_ext, norm_pdf).ratio()
                                        category_bonus = 0.2  # Bonus for matching category
                                        total_score = min(1.0, base_score + category_bonus)
                                        
                                        if total_score > best_score and total_score >= self.min_score:
                                            best_score = total_score
                                            best_match = pdf_field
            
            if best_match:
                matches[ext_field] = FieldMatch(
                    source_field=ext_field,
                    target_field=best_match,
                    score=best_score,
                    match_type="semantic"
                )
                
        return matches
    
    def map_checkbox_fields(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map extracted field values to checkbox fields in the PDF
        
        Args:
            extracted_data: Dictionary of extracted field values
            
        Returns:
            Dictionary of checkbox field mappings to boolean values
        """
        checkbox_mappings = {}
        
        # Process fields that might contain checkbox values
        checkbox_field_types = [
            'mortgage_type', 'mortgage_type_other',
            'amortization_type', 'amortization_type_other',
            'loan_purpose_type', 'loan_purpose_other',
            'property_usage', 'estate_type'
        ]
        
        for field in checkbox_field_types:
            if field in extracted_data:
                checkbox_values = process_checkbox_value(field, extracted_data[field])
                
                # Map processed checkbox values to PDF fields
                for value_key, checked in checkbox_values.items():
                    # Find matching PDF fields for this checkbox value
                    for pdf_field in self.checkbox_fields:
                        pdf_field_normalized = self._normalize_field_name(pdf_field).lower()
                        
                        # Check if value matches this field
                        if value_key in pdf_field_normalized:
                            checkbox_mappings[pdf_field] = checked
                            
                        # Handle special field for explanations
                        if value_key == 'other_explanation' and 'explain' in pdf_field_normalized:
                            checkbox_mappings[pdf_field] = checkbox_values['other_explanation']
        
        return checkbox_mappings

    def generate_mapping(self, 
                      extracted_fields: List[str], 
                      extracted_values: Optional[Dict[str, str]] = None,
                      custom_mappings: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Generate a mapping from extracted fields to PDF fields
        
        Args:
            extracted_fields: List of field names from extracted data
            extracted_values: Optional dictionary of field values
            custom_mappings: Optional dictionary of custom mappings to override automatic ones
            
        Returns:
            Dictionary mapping extracted field names to PDF field names
        """
        # Start with any provided custom mappings
        final_mapping = {}
        if custom_mappings:
            final_mapping = custom_mappings.copy()
            
        # Fields that haven't been mapped yet
        unmapped_fields = [f for f in extracted_fields if f not in final_mapping]
        
        # Already targeted PDF fields (to avoid duplicates)
        used_targets = set(final_mapping.values())
        
        # Step 1: Find exact matches
        exact_matches = self._get_exact_matches(unmapped_fields)
        for ext_field, match in exact_matches.items():
            final_mapping[ext_field] = match.target_field
            used_targets.add(match.target_field)
            unmapped_fields.remove(ext_field)
        
        # Step 2: Find fuzzy matches for remaining fields
        if unmapped_fields:
            fuzzy_matches = self._get_fuzzy_matches(unmapped_fields, used_targets)
            for ext_field, match in fuzzy_matches.items():
                final_mapping[ext_field] = match.target_field
                used_targets.add(match.target_field)
                unmapped_fields.remove(ext_field)
        
        # Step 3: Find semantic matches for remaining fields
        if unmapped_fields:
            semantic_matches = self._get_semantic_matches(unmapped_fields, used_targets)
            for ext_field, match in semantic_matches.items():
                final_mapping[ext_field] = match.target_field
                used_targets.add(match.target_field)
                unmapped_fields.remove(ext_field)
        
        # Step 4: Process checkbox fields if we have values
        if extracted_values:
            checkbox_mappings = self.map_checkbox_fields(extracted_values)
            # Add checkbox mappings to the final result
            for checkbox_field, value in checkbox_mappings.items():
                # Only add if not already mapped
                if checkbox_field not in used_targets:
                    # For checkboxes, we'll use field:value mapping rather than field:field
                    final_mapping[f"checkbox:{checkbox_field}"] = value
        
        self.field_mapping = final_mapping
        return final_mapping
    
    def save_mapping(self, output_path: str) -> str:
        """Save the generated mapping to a JSON file"""
        with open(output_path, 'w') as f:
            json.dump(self.field_mapping, f, indent=2)
        return output_path
    
    def load_mapping(self, mapping_path: str) -> Dict[str, str]:
        """Load a mapping from a JSON file"""
        with open(mapping_path, 'r') as f:
            self.field_mapping = json.load(f)
        return self.field_mapping
    
    def get_mapping_report(self) -> Dict[str, Any]:
        """Get a report of the mapping results"""
        if not self.field_mapping:
            return {"error": "No mapping has been generated yet"}
            
        report = {
            "total_mapped": len(self.field_mapping),
            "total_pdf_fields": len(self.pdf_fields),
            "coverage_percentage": round(len(self.field_mapping) / len(self.pdf_fields) * 100, 2),
            "mapped_fields": self.field_mapping,
            "unmapped_pdf_fields": [f for f in self.pdf_fields if f not in self.field_mapping.values()]
        }
        
        return report


def test_mapping(pdf_path: str, extracted_fields: List[str], output_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Test the field mapping on a specific PDF with sample extracted fields
    
    Args:
        pdf_path: Path to the PDF form
        extracted_fields: List of field names from extracted data
        output_path: Optional path to save the mapping
        
    Returns:
        Report of the mapping results
    """
    mapper = AIFieldMapper(pdf_path)
    mapping = mapper.generate_mapping(extracted_fields)
    
    if output_path:
        mapper.save_mapping(output_path)
        
    return mapper.get_mapping_report()


def process_checkbox_value(field_name: str, field_value: str) -> Dict[str, bool]:
    """
    Process checkbox values to determine which boxes should be checked
    
    Args:
        field_name: The name of the field containing checkbox values
        field_value: The value extracted for this field
        
    Returns:
        Dictionary mapping checkbox field names to boolean values
    """
    result = {}
    normalized_value = field_value.lower().strip()
    
    # Process mortgage type checkboxes
    if field_name == 'mortgage_type':
        if any(match in normalized_value for match in ['va', 'veteran']):
            result['va'] = True
        elif any(match in normalized_value for match in ['fha']):
            result['fha'] = True
        elif any(match in normalized_value for match in ['conventional', 'standard', 'regular']):
            result['conventional'] = True
        elif any(match in normalized_value for match in ['usda', 'rural']):
            result['usda/rural'] = True
        elif normalized_value:
            result['other'] = True
            result['other_explanation'] = field_value
    
    # Process amortization type checkboxes
    elif field_name == 'amortization_type':
        if any(match in normalized_value for match in ['fixed']):
            result['fixed_rate'] = True
        elif any(match in normalized_value for match in ['gpm', 'graduated']):
            result['gpm'] = True
        elif any(match in normalized_value for match in ['arm', 'adjustable', 'variable']):
            result['arm'] = True
            # Try to extract ARM type if specified
            arm_type_match = re.search(r'(\d+/\d+|\d+)', normalized_value)
            if arm_type_match:
                result['arm_type'] = arm_type_match.group(1)
        elif normalized_value:
            result['other'] = True
            result['other_explanation'] = field_value
    
    # Process loan purpose checkboxes
    elif field_name == 'loan_purpose_type':
        if any(match in normalized_value for match in ['purchase', 'buy', 'buying']):
            result['purchase'] = True
        elif any(match in normalized_value for match in ['refinance', 'refi']):
            result['refinance'] = True
        elif any(match in normalized_value for match in ['construction']) and any(match in normalized_value for match in ['permanent']):
            result['construction-permanent'] = True
        elif any(match in normalized_value for match in ['construction', 'build']):
            result['construction'] = True
        elif normalized_value:
            result['other'] = True
            result['other_explanation'] = field_value
    
    # Process property usage checkboxes
    elif field_name == 'property_usage':
        if any(match in normalized_value for match in ['primary', 'main', 'principal']):
            result['primary_residence'] = True
        elif any(match in normalized_value for match in ['secondary', 'second', 'vacation']):
            result['secondary_residence'] = True
        elif any(match in normalized_value for match in ['investment', 'rental']):
            result['investment'] = True
    
    # Process estate type checkboxes
    elif field_name == 'estate_type':
        if any(match in normalized_value for match in ['fee simple', 'freehold', 'complete']):
            result['fee_simple'] = True
        elif any(match in normalized_value for match in ['leasehold', 'lease']):
            result['leasehold'] = True
            # Try to extract expiration date if mentioned
            date_match = re.search(r'(?:expiration|expires|until|through)\s+(\d{1,2}/\d{1,2}/\d{2,4}|\d{4})', normalized_value)
            if date_match:
                result['leasehold_expiration'] = date_match.group(1)
    
    return result


def main():
    """Command-line interface for AI Field Mapper"""
    if len(sys.argv) < 3:
        print("Usage: python ai_field_mapper.py <pdf_file> <fields_json> [output_json]")
        print("  <pdf_file>: Path to the PDF form")
        print("  <fields_json>: Path to JSON file with extracted field names")
        print("  [output_json]: Optional path to save the mapping")
        sys.exit(1)
        
    pdf_path = sys.argv[1]
    fields_json_path = sys.argv[2]
    output_path = sys.argv[3] if len(sys.argv) > 3 else None
    
    try:
        # Load extracted fields from JSON
        with open(fields_json_path, 'r') as f:
            extracted_data = json.load(f)
        
        # Extract field names
        if isinstance(extracted_data, list):
            # Assume it's a list of field objects
            extracted_fields = [item.get('field_name') for item in extracted_data 
                               if 'field_name' in item]
        elif isinstance(extracted_data, dict) and 'fields' in extracted_data:
            # Assume it's an object with a 'fields' property
            extracted_fields = [item.get('field_name') for item in extracted_data['fields'] 
                               if 'field_name' in item]
        else:
            # Assume it's a dictionary with field names as keys
            extracted_fields = list(extracted_data.keys())
        
        report = test_mapping(pdf_path, extracted_fields, output_path)
        
        # Print report
        print(f"Mapping report:")
        print(f"  Total PDF fields: {report['total_pdf_fields']}")
        print(f"  Fields mapped: {report['total_mapped']}")
        print(f"  Coverage: {report['coverage_percentage']}%")
        
        if output_path:
            print(f"Mapping saved to: {output_path}")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main() 