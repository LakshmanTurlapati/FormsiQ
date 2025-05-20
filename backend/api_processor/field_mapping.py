"""
Utility module to define mapping between LLM output field names and PDF form field names.
"""

import logging

logger = logging.getLogger(__name__)

# Mapping between LLM output field names and the actual PDF form field names
LLM_TO_PDF_FIELD_MAP = {
    # Section I: Type of Mortgage and Terms of Loan
    "Mortgage Applied for: VA": "Mortgage Applied For",
    "Mortgage Applied for: FHA": "Mortgage Applied For",
    "Mortgage Applied for: Conventional": "Mortgage Applied For",
    "Mortgage Applied for: USDA": "Mortgage Applied For",
    "Mortgage Applied for: Other Description": "Mortgage Applied For",
    "Mortgage Type: Conventional": "Mortgage Applied For",
    "Mortgage Applied For": "Mortgage Applied For",
    "Agency Case Number": "Agency Case Number",
    "Lender Case Number": "Lender Case Number",
    "Loan Amount": "Loan Amount",
    "Loan Amount Requested": "Loan Amount",
    "Amount": "Loan Amount",
    "Interest Rate": "Interest Rate",
    "Number of Months (Loan Term)": "No. of Months",
    "No. of Months": "No. of Months",
    "Amortization Type: Fixed Rate": "Amortization Type",
    "Amortization Type: GPM": "Amortization Type",
    "Amortization Type: ARM (Specify Type)": "Amortization Type",
    "Amortization Type: Other Description": "Amortization Type",
    "Amortization Type": "Amortization Type",
    
    # Section II: Property Information
    "Subject Property Street Address": "Subject Property Address",
    "Property Street Address (if different from current, or for purchase)": "Subject Property Address",
    "Property Street Address": "Subject Property Address",
    "Property City": "Subject Property Address",
    "Property State": "Subject Property Address",
    "Property Zip Code": "Subject Property Address",
    "Subject Property Address": "Subject Property Address",
    "Number of Units": "No. of Units",
    "No. of Units": "No. of Units",
    "Legal Description of Subject Property": "Subject Property Description",
    "Subject Property Description": "Subject Property Description",
    "Year Built": "Year Built",
    "Purpose of Loan: Purchase": "Purpose of Loan",
    "Purpose of Loan: Refinance": "Purpose of Loan",
    "Loan Purpose: Purchase": "Purpose of Loan",
    "Loan Purpose: Refinance": "Purpose of Loan",
    "Purpose of Loan": "Purpose of Loan",
    "Purpose of Refinance": "Purpose of Refinance",
    "Original Cost": "Original Cost",
    "Cost of Improvements": "Improvements",
    "Estate will be held in: Fee Simple": "Estate will be held in",
    "Estate will be held in: Leasehold": "Estate will be held in",
    "Estate will be held in": "Estate will be held in",
    "Title will be held in what names": "Title will be held in what Name(s)",
    "Title will be held in what Name(s)": "Title will be held in what Name(s)",
    "Manner in which Title will be held": "Manner in which Title will be held",
    
    # Section III: Borrower Information
    "Borrower Name": "Borrower Name",
    "Borrower Full Name": "Borrower Name", 
    "Primary Borrower Name": "Borrower Name",
    "Borrower First Name": "Borrower First Name",
    "Borrower Middle Name": "Borrower Middle Name",
    "Borrower Last Name": "Borrower Last Name",
    "Borrower Suffix (Jr., Sr., etc.)": "Borrower Name",
    "Borrower Suffix": "Borrower Name",
    "Borrower Social Security Number": "Borrower SSN",
    "Social Security Number": "Borrower SSN",
    "Borrower SSN": "Borrower SSN",
    "Borrower Home Phone": "Borrower Home Phone",
    "Primary Phone Number": "Borrower Home Phone",
    "Borrower Date of Birth (MM/DD/YYYY)": "Borrower DOB",
    "Date of Birth": "Borrower DOB",
    "Borrower DOB": "Borrower DOB",
    "Borrower Years of School": "Borrower DOB Yrs School",
    "Marital Status: Married": "Borrower Marital Status",
    "Marital Status: Unmarried": "Borrower Marital Status",
    "Marital Status: Separated": "Borrower Marital Status",
    "Marital Status": "Borrower Marital Status",
    "Borrower Marital Status": "Borrower Marital Status",
    "Borrower Present Street Address": "Borrower Present Address",
    "Current Street Address": "Borrower Present Address",
    "Borrower Present City": "Borrower Present Address",
    "Current City": "Borrower Present Address",
    "Borrower Present State": "Borrower Present Address",
    "Current State": "Borrower Present Address",
    "Borrower Present Zip Code": "Borrower Present Address",
    "Current Zip Code": "Borrower Present Address",
    "Borrower Present Address": "Borrower Present Address",
    "Borrower Own or Rent Present Address": "Borrower Own or Rent",
    "Borrower Own or Rent": "Borrower Own or Rent",
    "Borrower Number of Years at Present Address": "Borrower No of Years",
    "Borrower No of Years": "Borrower No of Years",
    
    # Co-Borrower Information
    "Co-Borrower Name": "Co-Borrower Name",
    "Co-Borrower First Name": "Co-Borrower First Name",
    "Co-Borrower Last Name": "Co-Borrower Last Name",
    "Co-Borrower Social Security Number": "Co-Borrower SSN",
    "Co-Borrower SSN": "Co-Borrower SSN",
    "Co-Borrower Home Phone": "Co-Borrower Home Phone",
    "Co-Borrower Date of Birth": "Co-Borrower DOB",
    "Co-Borrower DOB": "Co-Borrower DOB",
    "Co-Borrower Years of School": "Co-Borrower Yrs School",
    "Co-Borrower Marital Status": "Co-Borrower Marital Status",
    "Co-Borrower Present Address": "Co-Borrower Present Address",
    "Co-Borrower Own or Rent": "Co-Borrower Own or Rent",
    "Co-Borrower Number of Years at Present Address": "Co-Borrower No of Years",
    "Co-Borrower No of Years": "Co-Borrower No of Years",
    
    # Employment Information
    "Borrower Employer Name": "Borrower Name and Address of Employer",
    "Current Employer Name": "Borrower Name and Address of Employer",
    "Borrower Name and Address of Employer": "Borrower Name and Address of Employer",
    "Borrower Self-Employed (Yes/No)": "Borrower Self Employed",
    "Borrower Self Employed": "Borrower Self Employed",
    "Borrower Years on this Job": "Borrower Years on the job",
    "Borrower Years on the job": "Borrower Years on the job",
    "Employment Start Date": "Borrower Years on the job",
    "Borrower Position/Title": "Borrower Position/Title/Type of Business",
    "Borrower Position/Title/Type of Business": "Borrower Position/Title/Type of Business",
    "Job Title/Position": "Borrower Position/Title/Type of Business",
    "Borrower Business Phone": "Borrower Business phone",
    "Borrower Business phone": "Borrower Business phone",
    "Borrower Years employed in this Profession": "Borrower Years employed in this Profession",
    
    # Co-Borrower Employment
    "Co-Borrower Employer Name": "Co-Borrower Name and Address of Employer",
    "Co-Borrower Name and Address of Employer": "Co-Borrower Name and Address of Employer",
    "Co-Borrower Self-Employed": "Co-Borrower Self Employed",
    "Co-Borrower Self Employed": "Co-Borrower Self Employed",
    "Co-Borrower Years on this Job": "Co-Borrower Years on the job",
    "Co-Borrower Years on the job": "Co-Borrower Years on the job",
    "Co-Borrower Position/Title": "Co-Borrower Position/Title/Type of Business",
    "Co-Borrower Position/Title/Type of Business": "Co-Borrower Position/Title/Type of Business",
    "Co-Borrower Business Phone": "Co-Borrower Business phone",
    "Co-Borrower Business phone": "Co-Borrower Business phone",
    "Co-Borrower Years employed in this Profession": "Co-Borrower Years employed in this Profession",
    
    # Income Information
    "Borrower Base Employment Income (Monthly)": "Monthly income Borrower Base",
    "Monthly Income (Base)": "Monthly income Borrower Base",
    "Monthly income Borrower Base": "Monthly income Borrower Base",
    "Borrower Overtime Income (Monthly)": "Monthly income Borrower Overtime",
    "Borrower Bonuses Income (Monthly)": "Monthly income Borrower Bonuses",
    "Monthly income Borrower Bonuses": "Monthly income Borrower Bonuses",
    "Borrower Commissions Income (Monthly)": "Monthly income Borrower Commissions",
    "Borrower Dividends Income (Monthly)": "Monthly income Borrower Dividends",
    "Monthly income Borrower Dividends": "Monthly income Borrower Dividends",
    "Monthly Income (Other, specify source if possible)": "Monthly income Borrower Other",
    "Monthly Income (Other, specify source)": "Monthly income Borrower Other",
    
    # Co-Borrower Income
    "Co-Borrower Base Employment Income (Monthly)": "Monthly income Co-Borrower Base",
    "Monthly income Co-Borrower Base": "Monthly income Co-Borrower Base",
    "Co-Borrower Overtime Income (Monthly)": "Monthly income Co-Borrower Overtime",
    "Co-Borrower Bonuses Income (Monthly)": "Monthly income Co-Borrower Bonuses",
    "Monthly income Co-Borrower Bonuses": "Monthly income Co-Borrower Bonuses",
    "Co-Borrower Commissions Income (Monthly)": "Monthly income Co-Borrower Commissions",
    "Co-Borrower Dividends Income (Monthly)": "Monthly income Co-Borrower Dividends",
    
    # Housing Information
    "Combined Monthly Housing Expense Rent Present": "Combined Monthly Housing Expense Rent Present",
    
    # Dependents Information
    "Dependents not listed by Borrower no": "Dependents not listed by Borrower no",
    "Dependents not listed by Borrower ages": "Dependents not listed by Borrower ages",
    "Dependents not listed by Co-Borrower no": "Dependents not listed by Co-Borrower no",
    "Dependents not listed by Co-Borrower ages": "Dependents not listed by Co-Borrower ages",
    
    # Checkbox and Radio Button Fields
    "Property will be": "Property will be",
    "Borrower US Citizen Y": "Borrower US Citizen Y",
    "Co-Borrower US Citizen Y": "Co-Borrower US Citizen Y",
    "Owner Occupied Y": "Owner Occupied Y",
    "Previous 3 years Owner Y": "Previous 3 years Owner Y",
    "Co-Borrower Previous 3 years Owner Y": "Co-Borrower Previous 3 years Owner Y",
    "Borrower Judgements against": "Borrower Judgements against",
    "Co-Borrower Judgements against": "Co-Borrower Judgements against",
    "Borrower Bankrupt": "Borrower Bankrupt",
    "Co-Borrower Bankrupt y": "Co-Borrower Bankrupt y",
    "Borrower Lawsuit": "Borrower Lawsuit",
    "Co-Borrower Lawsuit y": "Co-Borrower Lawsuit y",
    "Borrower Liability": "Borrower Liability",
    "Co-Borrower Liability y": "Co-Borrower Liability y",
    "Default on Dept": "Default on Dept",
    "Co-Borrower Default on Dept Y": "Co-Borrower Default on Dept Y",
    "Child Support": "Child Support",
    "Co-Borrower Child Support Y": "Co-Borrower Child Support Y",
    "Borrowed down Payment": "Borrowed down Payment",
    "Endorsermor Co-maker of Paymnets": "Endorsermor Co-maker of Paymnets"
}

# Map known radio button field values to their exact PDF field values
RADIO_BUTTON_MAPS = {
    "Mortgage Applied For": {
        "Conventional": "Conventional",
        "FHA": "FHA",
        "VA": "VA",
        "USDA/Rural Housing Service": "USDA/Rural Housing Service",
        "Other": "Other"
    },
    "Purpose of Loan": {
        "Purchase": "Purchase",
        "Refinance": "Refinance",
        "Construction": "Construction", 
        "Construction-Permanent": "Construction-Permanent",
        "Other": "Other"
    },
    "Property will be": {
        "Primary Residence": "Primary Residence",
        "Secondary Residence": "Secondary Residence",
        "Investment": "Investment"
    },
    "Amortization Type": {
        "Fixed Rate": "Fixed Rate",
        "ARM": "ARM",
        "GPM": "GPM",
        "Other": "Other"
    },
    "Borrower Marital Status": {
        "Married": "Married",
        "Unmarried": "Unmarried",
        "Separated": "Separated"
    },
    "Co-Borrower Marital Status": {
        "Married": "Married",
        "Unmarried": "Unmarried",
        "Separated": "Separated"
    },
    "Borrower Own or Rent": {
        "Own": "Own",
        "Rent": "Rent"
    },
    "Co-Borrower Own or Rent": {
        "Own": "Own",
        "Rent": "Rent"
    },
    "Estate will be held in": {
        "Fee Simple": "Fee Simple",
        "Leasehold": "Leasehold"
    }
}

# Map checkbox field values to their appropriate state
CHECKBOX_FIELD_MAPS = {
    "Borrower US Citizen Y": {
        "Yes": "Yes",
        "No": "Off"
    },
    "Co-Borrower US Citizen Y": {
        "Yes": "Yes",
        "No": "Off"
    },
    "Owner Occupied Y": {
        "Yes": "Yes",
        "No": "Off"
    },
    "Previous 3 years Owner Y": {
        "Yes": "Yes",
        "No": "Off"
    },
    "Co-Borrower Previous 3 years Owner Y": {
        "Yes": "Yes",
        "No": "Off"
    },
    "Borrower Judgements against": {
        "Yes": "Yes",
        "No": "No"
    },
    "Co-Borrower Judgements against": {
        "Yes": "Yes",
        "No": "No"
    },
    "Borrower Bankrupt": {
        "Yes": "Yes",
        "No": "No"
    },
    "Co-Borrower Bankrupt y": {
        "Yes": "Yes",
        "No": "No"
    },
    "Borrower Self Employed": {
        "Yes": "Yes",
        "No": "No" 
    },
    "Co-Borrower Self Employed": {
        "Yes": "Yes",
        "No": "No"
    }
}

def get_pdf_field_name(llm_field_name):
    """
    Get the corresponding PDF field name for an LLM field name.
    
    Args:
        llm_field_name (str): Field name as output by the LLM
        
    Returns:
        str or None: The corresponding PDF field name, or None if not found
    """
    return LLM_TO_PDF_FIELD_MAP.get(llm_field_name, None)

def get_radio_button_value(field_name, value):
    """
    Get the proper value for a radio button field based on the extracted value.
    More flexible matching.
    
    Args:
        field_name (str): The PDF field name
        value (str): The extracted value from LLM
        
    Returns:
        str or None: The proper value for the radio button, or None if not found
    """
    if field_name in RADIO_BUTTON_MAPS:
        button_map = RADIO_BUTTON_MAPS[field_name] # e.g., {"Primary Residence": "/Choice1", "Investment": "/Choice2"}
        val_str_lower = str(value).strip().lower()

        # 1. Try exact match on original value (case-sensitive) against keys
        if str(value) in button_map:
            return button_map[str(value)]

        # 2. Try case-insensitive exact match on value against keys
        for option_key, pdf_val in button_map.items():
            if option_key.lower() == val_str_lower:
                return pdf_val
        
        # 3. Try if the input value CONTAINS a known option key (case-insensitive)
        #    Sort keys by length descending to match longer keys first (e.g., "Co-Borrower" before "Borrower")
        sorted_options_by_len_desc = sorted(button_map.keys(), key=len, reverse=True)
        for option_key in sorted_options_by_len_desc:
            if option_key.lower() in val_str_lower:
                # Ensure it's a reasonably whole-word match if possible, or a significant substring
                # This is a simple heuristic; more advanced NLP could be used if needed.
                # For now, direct substring match after sorting by length is a good improvement.
                return button_map[option_key] 
            
    return None # No match found

def get_checkbox_value(field_name, value):
    """
    Get the proper semantic value ("Yes" or "Off"/"No") for a checkbox field 
    based on the extracted value. More flexible matching.
    
    Args:
        field_name (str): The PDF field name (used to look up specific "Yes"/"No" mappings if they differ from "Yes"/"Off")
        value (str): The extracted value from LLM
        
    Returns:
        str: "Yes" for affirmative, or the field-specific negative value ("No" or "Off")
    """
    value_str = str(value).strip().lower()

    # Define more comprehensive lists of affirmative and negative keywords/phrases
    # Order matters slightly: check for negatives that might contain affirmatives first (e.g. "not applicable" contains "applicable")
    negative_indicators = [
        "no", "false", "off", "n", "0", "unchecked", "not selected", "none", "n/a", 
        "not applicable", "not confirmed", "not completed", "inactive", "disagree", "denied",
        "is not", "are not", "has not", "does not", "was not", "were not" # word boundaries might be better but simple "in" for now
    ]
    affirmative_indicators = [
        "yes", "true", "on", "y", "1", "checked", "selected", "agree", "confirmed", "completed", "active",
        "is ", "are ", "has ", "does ", "was ", "were " # Trailing space to catch "is a citizen", "is applicable"
    ] # The "is ", "are " need to be used carefully if negative_indicators like "is not" are also present.

    # Determine specific "Yes" and "No" values for this field, defaulting to "Yes" and "Off"
    specific_yes_val = "Yes"
    specific_no_val = "Off"
    if field_name in CHECKBOX_FIELD_MAPS:
        checkbox_map_for_field = CHECKBOX_FIELD_MAPS[field_name]
        specific_yes_val = checkbox_map_for_field.get("Yes", "Yes")
        specific_no_val = checkbox_map_for_field.get("No", "Off")

    # Check for negative indicators first
    for neg_phrase in negative_indicators:
        if neg_phrase in value_str:
            # If "is not" is found, but "is" (affirmative) was also part of a longer phrase,
            # we need to ensure the negative takes precedence. The order of checking helps.
            return specific_no_val

    # Check for affirmative indicators
    for aff_phrase in affirmative_indicators:
        if aff_phrase in value_str:
            # Special handling for phrases like "is " to avoid false positives if "is not" was missed.
            # However, the negative check above should catch "is not".
            return specific_yes_val
            
    # Fallback: if after keyword search, no clear indicator, default to the negative value.
    # This is safer than assuming affirmative if unsure.
    return specific_no_val 