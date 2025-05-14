"""
Utility module to define mapping between LLM output field names and PDF form field names.
"""

# Mapping between LLM output field names and the actual PDF form field names
LLM_TO_PDF_FIELD_MAP = {
    # Section I: Type of Mortgage and Terms of Loan
    "Mortgage Applied for: VA": "Mortgage Applied For",
    "Mortgage Applied for: FHA": "Mortgage Applied For",
    "Mortgage Applied for: Conventional": "Mortgage Applied For",
    "Mortgage Applied for: USDA": "Mortgage Applied For",
    "Mortgage Applied for: Other Description": "Mortgage Applied For",
    "Mortgage Type: Conventional": "Mortgage Applied For",
    "Agency Case Number": "Agency Case Number",
    "Lender Case Number": "Lender Case Number",
    "Loan Amount": "Loan Amount",
    "Loan Amount Requested": "Loan Amount",
    "Interest Rate": "Interest Rate",
    "Number of Months (Loan Term)": "Interest Rate",
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
    "Number of Units": "Type of Property",
    "Legal Description of Subject Property": "Subject Property Description",
    "Year Built": "Year Built",
    "Purpose of Loan: Purchase": "Purpose of Loan",
    "Purpose of Loan: Refinance": "Purpose of Loan",
    "Loan Purpose: Purchase": "Purpose of Loan",
    "Purpose of Loan: Construction": "Purpose of Loan",
    "Purpose of Loan: Construction-Permanent": "Purpose of Loan",
    "Purpose of Loan: Other Description": "Purpose of Loan",
    "Loan Purpose": "Purpose of Loan",
    "Purpose of Loan": "Purpose of Loan",
    "Property will be: Primary Residence": "Property will be",
    "Property Usage: Primary Residence": "Property will be",
    "Property will be: Secondary Residence": "Property will be",
    "Property will be: Investment": "Property will be",
    "Property will be": "Property will be",
    "Source of Down Payment/Settlement Charges": "other assets itemized",
    
    # Section III: Borrower Information
    "Borrower First Name": "Borrower Name",
    "Borrower Middle Name": "Borrower Name",
    "Borrower Last Name": "Borrower Name",
    "Borrower Suffix (Jr., Sr., etc.)": "Borrower Name",
    "Borrower Suffix": "Borrower Name",
    "Borrower Name": "Borrower Name",
    "Borrower Social Security Number": "Borrower SSN",
    "Social Security Number": "Borrower SSN",
    "Borrower Home Phone": "Borrower Home Phone",
    "Primary Phone Number": "Borrower Home Phone",
    "Borrower Date of Birth (MM/DD/YYYY)": "Borrower DOB",
    "Date of Birth": "Borrower DOB",
    "Borrower Years of School": "Borrower DOB Yrs School",
    "Marital Status: Married": "Borrower Marital Status",
    "Marital Status: Unmarried": "Borrower Marital Status",
    "Marital Status: Separated": "Borrower Marital Status",
    "Marital Status": "Borrower Marital Status",
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
    "Borrower Number of Years at Present Address": "Borrower No of Years",
    
    # Email Information
    "Email Address": "Text1",
    
    # CoBorrower Information
    "Co-Borrower First Name": "Co-Borrower Name",
    "Co-Borrower Last Name": "Co-Borrower Name",
    "Co-Borrower Social Security Number": "Co-Borrower SSN",
    "Co-Borrower Name": "Co-Borrower Name",
    
    # Employment Information
    "Borrower Employer Name": "Borrower Name and Address of Employer",
    "Current Employer Name": "Borrower Name and Address of Employer",
    "Borrower Self-Employed (Yes/No)": "Borrower Self Employed",
    "Borrower Years on this Job": "Borrower Years on the job",
    "Employment Start Date": "Borrower Years on the job",
    "Borrower Position/Title": "Borrower Position/Title/Type of Business",
    "Job Title/Position": "Borrower Position/Title/Type of Business",
    "Borrower Business Phone": "Borrower Business phone",
    
    # Income Information
    "Borrower Base Employment Income (Monthly)": "Monthly income Borrower Base a",
    "Monthly Income (Base)": "Monthly income Borrower Base a",
    "Borrower Overtime Income (Monthly)": "Monthly income Borrower Bonuses 1",
    "Borrower Bonuses Income (Monthly)": "Monthly income Borrower Bonuses a1",
    "Borrower Commissions Income (Monthly)": "Monthly income Borrower Commissions a5",
    "Monthly Income (Other, specify source if possible)": "Monthly income Borrower Other a21",
    "Monthly Income (Other, specify source)": "Monthly income Borrower Other a21",
    
    # Transaction Details
    "Purchase Price": "Purchase Price",
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