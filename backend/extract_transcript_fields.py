#!/usr/bin/env python
"""
Transcript Field Extractor for FormsIQ

This script analyzes call transcripts and extracts potential field names
and their values using pattern recognition and NLP techniques.
"""

import re
import sys
import json
import logging
from typing import Dict, List, Any, Tuple, Optional

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Common field patterns in transcripts
COMMON_FIELDS = {
    # Basic personal information
    'name': [
        r"(?:my|full|your|applicant'?s?)\s+name\s+is\s+([\w\s.-]+)",
        r"(?:I'm|I am|this is|name:)\s+([\w\s.-]+)",
        r"(?:Full|Complete) name:?\s+([\w\s.-]+)",
    ],
    'first_name': [
        r"(?:my|your|applicant'?s?)\s+first\s+name\s+is\s+([\w\s.-]+)",
        r"(?:first|given)\s+name:?\s+([\w\s.-]+)",
        r"first name is ([A-Z][a-z]+)",
    ],
    'middle_name': [
        r"(?:my|your|applicant'?s?)\s+middle\s+name\s+is\s+([\w\s.-]+)",
        r"(?:middle|second)\s+name:?\s+([\w\s.-]+)",
        r"middle initial:?\s+([A-Z])",
    ],
    'last_name': [
        r"(?:my|your|applicant'?s?)\s+last\s+name\s+is\s+([\w\s.-]+)",
        r"(?:last|family|sur)\s+name:?\s+([\w\s.-]+)",
        r"last name is ([A-Z][a-z]+)",
    ],
    'suffix': [
        r"(?:my|your|name) suffix is\s+(Jr\.|Sr\.|II|III|IV)",
        r"(?:I'm|I am|you are|they are)\s+([A-Za-z]+\.?),? (?:Junior|Senior)",
    ],
    'email': [
        r"(?:my|your|applicant'?s?)\s+email\s+(?:address|is)\s+([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)",
        r"(?:email|e-mail)(?:\s+address)?:?\s+([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)",
        r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)",
    ],
    'phone': [
        r"(?:my|your|applicant'?s?|cell|mobile|phone|contact|telephone)\s+(?:number|is)\s+((?:\+\d{1,2}\s*)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4})",
        r"(?:phone|cell|mobile|telephone)(?:\s+number)?:?\s+((?:\+\d{1,2}\s*)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4})",
        r"(?:at|is|number)\s+(\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4})",
    ],
    'home_phone': [
        r"(?:home|house|landline)\s+(?:phone|telephone)\s+(?:number|is)\s+((?:\+\d{1,2}\s*)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4})",
    ],
    'work_phone': [
        r"(?:work|office|business)\s+(?:phone|telephone)\s+(?:number|is)\s+((?:\+\d{1,2}\s*)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4})",
    ],
    'cell_phone': [
        r"(?:cell|mobile|cellular)\s+(?:phone|telephone)\s+(?:number|is)\s+((?:\+\d{1,2}\s*)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4})",
    ],
    
    # Address information
    'current_address': [
        r"(?:my|your|applicant'?s?|home|current|mailing)\s+address\s+is\s+([\w\s.,#-]+)",
        r"(?:live|living|reside|residing)\s+at\s+([\w\s.,#-]+)",
        r"(?:address|residence):?\s+([\w\s.,#-]+)",
        r"(?:currently|presently)\s+(?:living|residing)\s+at\s+([\w\s.,#-]+)",
    ],
    'current_street': [
        r"(?:my|your|current)\s+street\s+address\s+is\s+([\w\s.,#-]+)",
        r"(?:street|st\.|avenue|ave\.|boulevard|blvd\.|road|rd\.|lane|ln\.|drive|dr\.):?\s+([\w\s.,#-]+)",
    ],
    'current_city': [
        r"(?:my|your|current)\s+city\s+is\s+([A-Za-z\s.-]+)",
        r"(?:in|of|the city of)\s+([A-Za-z\s.-]+)(?:,|\s+[A-Z]{2})",
    ],
    'current_state': [
        r"(?:my|your|current)\s+state\s+is\s+([A-Za-z\s.-]+)",
        r"(?:state|province):?\s+([A-Za-z\s.-]+)",
        r"(?:[A-Za-z\s.-]+),\s+([A-Z]{2})\s+\d{5}",
    ],
    'current_zip': [
        r"(?:my|your|current)\s+zip\s+(?:code)?\s+is\s+(\d{5}(?:-\d{4})?)",
        r"(?:zip|postal)\s+code:?\s+(\d{5}(?:-\d{4})?)",
        r"(?:[A-Za-z\s.-]+),\s+[A-Z]{2}\s+(\d{5}(?:-\d{4})?)",
    ],
    'property_address': [
        r"(?:property|home|house)\s+(?:address|at|located at)\s+([\w\s.,#-]+)",
        r"(?:buying|purchasing|interested in)\s+(?:a|the)\s+(?:property|home|house)\s+(?:at|on|located at)\s+([\w\s.,#-]+)",
        r"(?:property address|home address):?\s+([\w\s.,#-]+)",
        r"(?:new|buying|purchasing|subject)\s+property\s+(?:is|at|on|located at)\s+([\w\s.,#-]+)",
    ],
    'property_city': [
        r"(?:property|home|house)\s+(?:is in|located in|in the city of)\s+([A-Za-z\s.-]+)(?:,|\s+[A-Z]{2})",
    ],
    'property_state': [
        r"(?:property|home|house)\s+(?:is in|located in|in the state of)\s+([A-Za-z\s.-]+)",
        r"(?:property|home|house).*?(?:[A-Za-z\s.-]+),\s+([A-Z]{2})\s+\d{5}",
    ],
    'property_zip': [
        r"(?:property|home|house).*?(?:[A-Za-z\s.-]+),\s+[A-Z]{2}\s+(\d{5}(?:-\d{4})?)",
        r"property.*?zip\s+(?:code)?\s+is\s+(\d{5}(?:-\d{4})?)",
    ],
    
    # Personal identification
    'date_of_birth': [
        r"(?:my|your|applicant'?s?|DOB|D\.O\.B\.|date\s+of\s+birth)\s+(?:is|:)\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"(?:born|birth\s+date)\s+(?:on|:)\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"(?:born|birth\s+date)\s+(?:on|:)\s+([A-Z][a-z]+ \d{1,2}(?:st|nd|rd|th)?,? \d{4})",
        r"(?:born|birth\s+date)\s+(?:on|:)\s+([A-Z][a-z]+ \d{1,2},? \d{4})",
        r"date of birth.*?(?:is|:)\s+(\w+ \d{1,2}(?:st|nd|rd|th)?,? \d{4})",
    ],
    'social_security': [
        r"(?:my|your|applicant'?s?|SSN|social\s+security)\s+(?:number|is)\s+(\d{3}[- ]?\d{2}[- ]?\d{4})",
        r"(?:SSN|social\s+security\s+number):?\s+(\d{3}[- ]?\d{2}[- ]?\d{4})",
        r"SSN:?\s+(\d{3}[- ]?\d{2}[- ]?\d{4})",
        r"last four.*?social security.*?(\d{4})",
    ],
    'years_of_school': [
        r"(?:years|yrs)?\s+of\s+(?:school|education):?\s+(\d{1,2})",
        r"(?:completed|finished|have)\s+(\d{1,2})\s+years of\s+(?:school|education)",
        r"education(?:al)?\s+level:?\s+(\d{1,2})\s+years",
    ],
    'marital_status': [
        r"(?:I'm|I am|applicant is)\s+(single|married|divorced|separated|widowed)",
        r"marital\s+status:?\s+(single|married|divorced|separated|widowed)",
        r"(?:status|am)\s+(single|married|divorced|separated|widowed)",
    ],
    
    # Dependents information
    'number_of_dependents': [
        r"(?:have|has)\s+(\d{1,2})\s+(?:dependent|child|kid)s?",
        r"(\d{1,2})\s+(?:dependent|child|kid)s?",
        r"(?:number of dependents|dependents):?\s+(\d{1,2})",
    ],
    
    # Employment information
    'employer_name': [
        r"(?:my|your|applicant'?s?|current)\s+employer\s+is\s+([\w\s.,&'-]+)",
        r"(?:work|working)\s+(?:for|at)\s+([\w\s.,&'-]+)",
        r"(?:employer|company|organization):?\s+([\w\s.,&'-]+)",
        r"employed (?:by|with|at)\s+([\w\s.,&'-]+)",
    ],
    'employer_address': [
        r"(?:employer|company|work|business)\s+(?:address|located at|location):?\s+([\w\s.,#-]+)",
        r"(?:work|job)\s+(?:is at|at|located at)\s+([\w\s.,#-]+)",
    ],
    'job_title': [
        r"(?:my|your|applicant'?s?)\s+(?:job|position|title|role)\s+is\s+([\w\s.-]+)",
        r"(?:job|position|title|role):?\s+([\w\s.-]+)",
        r"(?:work|am|working)\s+as\s+(?:a|an)\s+([\w\s.-]+)",
    ],
    'years_at_job': [
        r"(?:been|working|employed)(?:\s+there|\s+with them|\s+at this job)?\s+for\s+(\d+\.?\d*)\s+years",
        r"(\d+\.?\d*)\s+years?\s+(?:at|with)\s+(?:this|current|present)\s+(?:job|employer|company)",
        r"(?:years|length)\s+(?:at|with|of)\s+(?:current employment|job|company):?\s+(\d+\.?\d*)",
    ],
    'years_in_profession': [
        r"(?:been|working|employed)\s+in\s+this\s+(?:field|profession|industry)\s+for\s+(\d+\.?\d*)\s+years",
        r"(\d+\.?\d*)\s+years?\s+(?:in|of)\s+(?:this|the|my)\s+(?:field|profession|industry)",
        r"(?:years|experience)\s+in\s+(?:field|profession|industry):?\s+(\d+\.?\d*)",
    ],
    'self_employed': [
        r"(?:I am|I'm|you are|applicant is)\s+(self[- ]employed)",
        r"(?:self[- ]employed):\s*(yes|no|true|false)",
        r"(?:work|working)\s+for\s+(?:myself|themselves|yourself)",
    ],
    'business_phone': [
        r"(?:business|work|office)\s+phone(?:\s+is|\s+number)?:?\s+((?:\+\d{1,2}\s*)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4})",
    ],
    
    # Income information
    'monthly_income': [
        r"(?:my|your|monthly|base)\s+(?:income|salary|earnings)\s+(?:is|of)\s+\$?([\d,.]+)",
        r"(?:make|making|earn|earning)\s+\$?([\d,.]+)\s+(?:per|a|each)?\s+month",
        r"(?:monthly income|monthly salary|monthly earnings):?\s+\$?([\d,.]+)",
        r"(?:base salary|base pay|base income).*\$?([\d,.]+).*(?:month|monthly)",
    ],
    'annual_income': [
        r"(?:my|your|annual|yearly)\s+(?:income|salary|earnings)\s+(?:is|of)\s+\$?([\d,.]+)",
        r"(?:make|making|earn|earning)\s+\$?([\d,.]+)\s+(?:per|a|each)?\s+year",
        r"(?:annual income|annual salary|yearly earnings):?\s+\$?([\d,.]+)",
        r"(?:income|salary|earnings).*\$?([\d,.]+).*(?:year|annual|annually)",
    ],
    'other_income': [
        r"(?:other|additional|extra)\s+(?:income|earnings)\s+(?:of|is)\s+\$?([\d,.]+)",
        r"(?:also|additionally)\s+(?:make|earn)\s+\$?([\d,.]+)",
        r"(?:bonus|commission|overtime|part-time)\s+(?:income|pay|earnings):?\s+\$?([\d,.]+)",
    ],
    
    # Loan information
    'loan_amount': [
        r"(?:loan|mortgage)\s+(?:amount|of)\s+\$?([\d,.]+)",
        r"(?:borrowing|borrow)\s+\$?([\d,.]+)",
        r"(?:loan amount|amount of the loan):?\s+\$?([\d,.]+)",
        r"(?:looking for|need|want)\s+(?:a|an)\s+\$?([\d,.]+)\s+(?:loan|mortgage)",
    ],
    'loan_purpose': [
        r"(?:purpose|reason)(?:\s+of|\s+for)?\s+(?:the|this)?\s+loan(?:\s+is)?:?\s+(purchase|refinance|construction|renovation|investment)",
        r"(?:loan|mortgage)\s+(?:is for|for|to)\s+(purchase|refinance|construction|renovation|investment)",
        r"(?:buying|purchasing|refinancing|constructing|renovating|investing in)\s+(?:a|the)\s+(?:home|house|property)",
    ],
    'loan_term': [
        r"(?:loan|mortgage)\s+(?:term|duration|period|length)\s+(?:of|is)?\s+(\d+)\s+(?:years|yr)",
        r"(\d+)[- ]year(?:\s+fixed)?(?:\s+rate)?(?:\s+mortgage|loan)?",
        r"(?:term|duration|period|length)(?:\s+of|\s+for)?\s+(?:the|this)?\s+loan:?\s+(\d+)\s+(?:years|yr)",
    ],
    'interest_rate': [
        r"(?:interest|rate)(?:\s+is|\s+at|\s+of)?:?\s+(\d+\.?\d*)\s*%",
        r"(\d+\.?\d*)\s*%\s+(?:interest|rate)",
        r"(\d+\.?\d*)\s+percent\s+(?:interest|rate)",
    ],
    'rate_type': [
        r"(?:type of|loan|mortgage)\s+(?:rate|interest):?\s+(fixed|adjustable|variable|ARM)",
        r"(fixed|adjustable|variable|ARM)(?:[- ]rate|\s+interest|\s+type)",
    ],
    
    # Property information
    'property_type': [
        r"(?:type of|property)(?:\s+is|\s+type)?:?\s+(single family|townhouse|condo|condominium|duplex|apartment|multi-family|mobile home)",
        r"(?:buying|purchasing|looking at|interested in)(?:\s+a)?\s+(single family|townhouse|condo|condominium|duplex|apartment|multi-family|mobile home)",
        r"(?:property|home|house|residence)(?:\s+is)?\s+(?:a|an)\s+(single family|townhouse|condo|condominium|duplex|apartment|multi-family|mobile home)",
    ],
    'number_of_units': [
        r"(?:property|building|home)\s+has\s+(\d+)\s+units",
        r"(\d+)(?:[- ]unit|\s+units)",
        r"(?:number of units|units):?\s+(\d+)",
    ],
    'property_use': [
        r"(?:property|home|house|residence)\s+(?:will be|is|as)(?:\s+a|my)?\s+(primary residence|second home|investment|vacation home)",
        r"(?:use|using)(?:\s+the|\s+this)?\s+property\s+(?:as|for)(?:\s+a|my)?\s+(primary residence|second home|investment|vacation home)",
        r"(?:primary residence|second home|investment property|vacation home)",
    ],
    'year_built': [
        r"(?:property|home|house)\s+(?:was)?\s+built\s+in\s+(\d{4})",
        r"(?:built|construction|year built)(?:\s+in|\s+date)?:?\s+(\d{4})",
        r"year (?:built|of construction):?\s+(\d{4})",
    ],
    
    # Asset information
    'checking_account': [
        r"(?:checking|bank)(?:\s+account)?(?:\s+balance|\s+has|\s+with)?:?\s+\$?([\d,.]+)",
        r"(?:have|has)(?:\s+a|\s+about|\s+around)?\s+\$?([\d,.]+)(?:\s+in)?\s+(?:my|the|a)?\s+checking(?:\s+account)?",
    ],
    'savings_account': [
        r"(?:savings|bank)(?:\s+account)?(?:\s+balance|\s+has|\s+with)?:?\s+\$?([\d,.]+)",
        r"(?:have|has)(?:\s+a|\s+about|\s+around)?\s+\$?([\d,.]+)(?:\s+in)?\s+(?:my|the|a)?\s+savings(?:\s+account)?",
    ],
    'retirement_account': [
        r"(?:401k|retirement|ira)(?:\s+account)?(?:\s+balance|\s+has|\s+with)?:?\s+\$?([\d,.]+)",
        r"(?:have|has)(?:\s+a|\s+about|\s+around)?\s+\$?([\d,.]+)(?:\s+in)?\s+(?:my|the|a)?\s+(?:401k|retirement|ira)(?:\s+account)?",
    ],
    
    # Liability information
    'car_loan': [
        r"(?:car|auto|vehicle)(?:\s+loan|\s+payment)?(?:\s+of|\s+is)?:?\s+\$?([\d,.]+)",
        r"(?:pay|paying)\s+\$?([\d,.]+)(?:\s+for|\s+on)(?:\s+my|\s+the)?\s+car(?:\s+loan)?",
        r"(?:car|auto|vehicle)(?:\s+loan)?\s+(?:payment|bill):?\s+\$?([\d,.]+)(?:\s+per|\s+a)?\s+month",
    ],
    'credit_card_debt': [
        r"(?:credit card|card)(?:\s+debt|\s+balance|\s+payment)?(?:\s+of|\s+is)?:?\s+\$?([\d,.]+)",
        r"(?:have|has|owe|owes)\s+\$?([\d,.]+)(?:\s+in)?\s+(?:credit card|card)(?:\s+debt)?",
    ],
    'student_loan': [
        r"(?:student|education|college)(?:\s+loan|\s+debt)?(?:\s+of|\s+is)?:?\s+\$?([\d,.]+)",
        r"(?:pay|paying)\s+\$?([\d,.]+)(?:\s+for|\s+on)(?:\s+my|\s+the)?\s+student(?:\s+loan)?",
        r"(?:have|has|owe|owes)\s+\$?([\d,.]+)(?:\s+in)?\s+student(?:\s+loan|\s+debt)?",
    ],
    
    # Declaration questions
    'bankruptcy': [
        r"(?:filed|declared|had)(?:\s+for)?\s+bankruptcy(?:\s+in the past|\s+within)?\s+((?:yes|no|never|not)(?:\s|,|\.|$))",
        r"bankruptcy:?\s+((?:yes|no|never|not)(?:\s|,|\.|$))",
        r"have you (?:ever)?\s+(?:filed|declared|had)(?:\s+for)?\s+bankruptcy\??\s+((?:yes|no|never|not)(?:\s|,|\.|$))",
    ],
    'foreclosure': [
        r"(?:had|experienced|gone through)(?:\s+a)?\s+foreclosure(?:\s+in the past|\s+within)?\s+((?:yes|no|never|not)(?:\s|,|\.|$))",
        r"foreclosure:?\s+((?:yes|no|never|not)(?:\s|,|\.|$))",
        r"have you (?:ever)?\s+(?:had|experienced|gone through)(?:\s+a)?\s+foreclosure\??\s+((?:yes|no|never|not)(?:\s|,|\.|$))",
    ],
    'lawsuit': [
        r"(?:involved in|party to)(?:\s+a)?\s+lawsuit(?:\s+in the past|\s+currently)?\s+((?:yes|no|never|not)(?:\s|,|\.|$))",
        r"lawsuit:?\s+((?:yes|no|never|not)(?:\s|,|\.|$))",
        r"are you (?:currently)?\s+(?:involved in|party to)(?:\s+a)?\s+lawsuit\??\s+((?:yes|no|never|not)(?:\s|,|\.|$))",
    ],
    'us_citizen': [
        r"(?:US|U.S.|United States)(?:\s+citizen|\s+citizenship)?(?:\s+status)?:?\s+((?:yes|no)(?:\s|,|\.|$))",
        r"(?:am|are|is)(?:\s+a)?\s+(?:US|U.S.|United States)\s+citizen(?:\s+status)?:?\s+((?:yes|no)(?:\s|,|\.|$))",
        r"are you (?:a)?\s+(?:US|U.S.|United States)\s+citizen\??\s+((?:yes|no)(?:\s|,|\.|$))",
    ],
    'alimony_child_support': [
        r"(?:pay|paying)(?:\s+any)?\s+(?:alimony|child support)(?:\s+payments)?:?\s+((?:yes|no|never|not)(?:\s|,|\.|$))",
        r"(?:alimony|child support)(?:\s+payments)?:?\s+((?:yes|no|never|not)(?:\s|,|\.|$))",
        r"are you (?:obligated to)?\s+(?:pay|paying)(?:\s+any)?\s+(?:alimony|child support)(?:\s+payments)?\??\s+((?:yes|no|never|not)(?:\s|,|\.|$))",
    ],
    'borrowed_down_payment': [
        r"(?:down payment|deposit)(?:\s+is)?\s+borrowed:?\s+((?:yes|no|never|not)(?:\s|,|\.|$))",
        r"(?:borrowing|borrowed)(?:\s+the|\s+any)?\s+(?:money for|funds for)?\s+(?:the)?\s+down payment:?\s+((?:yes|no|never|not)(?:\s|,|\.|$))",
        r"is (?:any of)?\s+(?:the)?\s+down payment borrowed\??\s+((?:yes|no|never|not)(?:\s|,|\.|$))",
    ],
    'co_signer': [
        r"(?:co-signer|co-maker|endorser)(?:\s+on a note|\s+on a loan)?:?\s+((?:yes|no|never|not)(?:\s|,|\.|$))",
        r"(?:are you|have you been)(?:\s+a)?\s+(?:co-signer|co-maker|endorser)(?:\s+on a note|\s+on a loan)?:?\s+((?:yes|no|never|not)(?:\s|,|\.|$))",
    ],
    'primary_residence': [
        r"(?:primary residence|main home|primary home)(?:\s+will be|\s+is)?:?\s+((?:yes|no)(?:\s|,|\.|$))",
        r"(?:plan to|going to|will)(?:\s+use|\s+occupy)(?:\s+this)?\s+(?:as)?\s+(?:your)?\s+primary residence:?\s+((?:yes|no)(?:\s|,|\.|$))",
        r"will this (?:property|house|home)\s+be\s+your\s+primary residence\??\s+((?:yes|no)(?:\s|,|\.|$))",
    ],
    'prior_ownership': [
        r"(?:owned|had)(?:\s+a)?\s+(?:home|house|property)(?:\s+before|\s+previously|\s+in the past)?:?\s+((?:yes|no|never|not)(?:\s|,|\.|$))",
        r"(?:first|1st)(?:[- ]time|\s+time)(?:\s+home)?\s+buyer:?\s+((?:yes|no)(?:\s|,|\.|$))",
        r"have you (?:ever)?\s+owned(?:\s+a)?\s+(?:home|house|property)(?:\s+before)?\??\s+((?:yes|no|never|not)(?:\s|,|\.|$))",
    ],
    
    # Mortgage type checkboxes
    'mortgage_type': [
        r"(?:applying for|want|need|looking for)(?:\s+a)?\s+(VA|FHA|conventional|USDA|Rural Housing|USDA\/Rural Housing)(?:\s+loan|\s+mortgage)?",
        r"(?:mortgage|loan)\s+(?:type|is|will be)(?:\s+a)?\s+(VA|FHA|conventional|USDA|Rural Housing|USDA\/Rural Housing)",
        r"(?:type of|kind of)(?:\s+mortgage|loan|financing)(?:\s+is|:)?\s+(VA|FHA|conventional|USDA|Rural Housing|USDA\/Rural Housing)",
    ],
    'mortgage_type_other': [
        r"(?:applying for|want|need|looking for)(?:\s+a)?\s+(?!VA|FHA|conventional|USDA|Rural Housing)(\w+)(?:\s+loan|\s+mortgage)",
        r"(?:mortgage|loan)\s+(?:type|is|will be)(?:\s+a)?\s+(?!VA|FHA|conventional|USDA|Rural Housing)(\w+)",
        r"(?:type of|kind of)(?:\s+mortgage|loan|financing)(?:\s+is|:)?\s+(?!VA|FHA|conventional|USDA|Rural Housing)(\w+)",
    ],
    
    # Amortization type checkboxes
    'amortization_type': [
        r"(?:amortization|payment)\s+(?:type|plan|schedule|is)(?:\s+is)?\s+(fixed rate|adjustable rate|GPM|ARM)",
        r"(?:fixed rate|adjustable rate|GPM|ARM)(?:\s+mortgage|\s+amortization|\s+loan)",
        r"(?:rate|interest|payments)\s+(?:will be|is|are)\s+(fixed|adjustable|graduated|ARM)",
    ],
    'amortization_type_other': [
        r"(?:amortization|payment)\s+(?:type|plan|schedule)(?:\s+is)?\s+(?!fixed rate|adjustable rate|GPM|ARM)(\w+)",
        r"(?!fixed rate|adjustable rate|GPM|ARM)(\w+)(?:\s+amortization|\s+payment schedule)",
    ],
    
    # Loan purpose checkboxes
    'loan_purpose_type': [
        r"(?:loan|mortgage)\s+(?:is for|for|to)\s+(purchase|buying|refinance|refinancing|construction|construction-permanent)",
        r"(?:purpose|reason)(?:\s+of|\s+for)?\s+(?:the|this)?\s+loan(?:\s+is)?:?\s+(purchase|buying|refinance|refinancing|construction|construction-permanent)",
        r"(?:I'm|I am|we are|we're)\s+(purchasing|buying|refinancing|constructing)",
    ],
    'loan_purpose_other': [
        r"(?:loan|mortgage)\s+(?:is for|for|to)\s+(?!purchase|buying|refinance|refinancing|construction|construction-permanent)(\w+)",
        r"(?:purpose|reason)(?:\s+of|\s+for)?\s+(?:the|this)?\s+loan(?:\s+is)?:?\s+(?!purchase|buying|refinance|refinancing|construction|construction-permanent)(\w+)",
    ],
    
    # Property usage checkboxes
    'property_usage': [
        r"(?:property|home|house|residence)\s+(?:will be|is|as)(?:\s+a|my)?\s+(primary residence|second home|secondary residence|investment property)",
        r"(?:use|using)(?:\s+the|\s+this)?\s+property\s+(?:as|for)(?:\s+a|my)?\s+(primary residence|second home|secondary residence|investment property)",
        r"(?:primary residence|second home|secondary residence|investment property)",
        r"(?:will|going to|plan to)\s+(?:live|reside)(?:\s+in|\s+at)\s+(?:the|this)?\s+property(?:\s+as|\s+for)?\s+(?:my|a)?\s+(primary|main|secondary|investment)",
    ],
    
    # Number of months (loan term)
    'number_of_months': [
        r"(?:term|period|duration|length)\s+(?:of|is)\s+(\d+)\s+months",
        r"(\d+)(?:-|\s+)month(?:\s+loan|\s+mortgage|\s+term)?",
        r"(\d+)\s+years",  # Convert to months in processing
    ],
    
    # Property details
    'number_of_units': [
        r"(?:number of units|units)(?:\s+is)?:?\s+(\d+)",
        r"(?:property|building|home)\s+has\s+(\d+)\s+units",
        r"(\d+)(?:-|\s+)unit(?:\s+property|\s+building)?",
    ],
    'year_built': [
        r"(?:property|home|house)\s+(?:was)?\s+built(?:\s+in)?\s+(\d{4})",
        r"(?:year built|built in|construction year|construction date)(?:\s+is)?:?\s+(\d{4})",
        r"built(?:\s+in)?\s+(\d{4})",
    ],
    
    # Estate type checkboxes
    'estate_type': [
        r"(?:estate(?:\s+will be|\s+is)?\s+held|title(?:\s+will be|\s+is)?\s+held)(?:\s+in)?:?\s+(fee simple|leasehold)",
        r"(?:title|ownership)\s+(?:type|is)\s+(fee simple|leasehold)",
    ],
    
    # Down payment source
    'down_payment_source': [
        r"(?:down payment|source of down payment|source of funds)(?:\s+is|:)?\s+(.*?)(?:\.|\n|$)",
        r"(?:paying|pay|making|make)\s+(?:the)?\s+down payment\s+(?:with|using|from)\s+(.*?)(?:\.|\n|$)",
        r"(?:money for|funds for)(?:\s+the)?\s+down payment(?:\s+is|are|:)?\s+(?:from|coming from)?\s+(.*?)(?:\.|\n|$)",
    ],
}

def clean_text(text: str) -> str:
    """Clean and normalize text for better pattern matching"""
    # Remove extra whitespaces
    text = re.sub(r'\s+', ' ', text)
    # Convert common spoken forms to standard format
    text = re.sub(r'(?i)my name is', 'My name is', text)
    text = re.sub(r'(?i)my email is', 'My email is', text)
    text = re.sub(r'(?i)my phone (?:number )?is', 'My phone is', text)
    return text.strip()

def extract_field_value_pairs(transcript: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Extract field name and value pairs from a transcript
    
    Args:
        transcript: The text of the call transcript
        
    Returns:
        Dictionary with field types as keys and lists of extracted values as values
    """
    # Clean the text
    clean_transcript = clean_text(transcript)
    
    # Storage for extracted fields
    extracted_fields = {}
    
    # Process each field type
    for field_type, patterns in COMMON_FIELDS.items():
        field_matches = []
        
        for pattern in patterns:
            matches = re.finditer(pattern, clean_transcript, re.IGNORECASE)
            
            for match in matches:
                # Extract the value and surrounding context
                value = match.group(1).strip()
                
                # Get some context (10 words before and after)
                start_pos = max(0, match.start() - 50)
                end_pos = min(len(clean_transcript), match.end() + 50)
                context = clean_transcript[start_pos:end_pos]
                
                # Add to our matches
                field_matches.append({
                    'field_name': field_type,
                    'field_value': value,
                    'context': context,
                    'confidence_score': 0.7,  # Basic confidence score
                    'pattern_used': pattern
                })
        
        if field_matches:
            extracted_fields[field_type] = field_matches
    
    return extracted_fields

def extract_to_flat_list(transcript: str) -> List[Dict[str, Any]]:
    """
    Extract field value pairs as a flat list (format needed by FormsIQ)
    
    Args:
        transcript: The text of the call transcript
        
    Returns:
        List of dictionaries with field_name, field_value, and confidence_score
    """
    extracted_dict = extract_field_value_pairs(transcript)
    flat_list = []
    
    for field_type, matches in extracted_dict.items():
        # Take the first match with highest confidence for each field type
        if matches:
            best_match = max(matches, key=lambda x: x['confidence_score'])
            flat_list.append({
                'field_name': field_type,
                'field_value': best_match['field_value'],
                'confidence_score': best_match['confidence_score']
            })
    
    return flat_list

def find_potential_field_names(transcript: str) -> List[str]:
    """
    Extract potential field names from a transcript based on patterns
    
    Args:
        transcript: The text of the call transcript
        
    Returns:
        List of potential field names
    """
    clean_transcript = clean_text(transcript)
    potential_fields = set()
    
    # Common patterns for field name introductions
    patterns = [
        r"(?:what(?:'s| is) your|could (?:I|you) get your|(?:I need|we need) your|please provide your|enter your|fill in your|give me your)\s+([a-z][a-z\s]+?)\??(?:\s|$|\.|\?)",
        r"(?:your|the|applicant(?:'s)?)\s+([a-z][a-z\s]+?)\s+(?:is|will be|should be|was|has been|:)",
        r"(?:do you have|have you|are you|were you)\s+([a-z][a-z\s]+?)\??(?:\s|$|\.|\?)",
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, clean_transcript, re.IGNORECASE)
        for match in matches:
            field_name = match.group(1).strip().lower()
            
            # Filter out common non-field phrases
            stopwords = ['information', 'response', 'answer', 'reply', 'question', 'name', 'email', 'phone']
            if field_name not in stopwords and len(field_name) > 3:
                potential_fields.add(field_name)
    
    return list(potential_fields)

def analyze_transcript(transcript_path: str, output_path: Optional[str] = None) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Analyze a transcript file and extract field values and potential field names
    
    Args:
        transcript_path: Path to the transcript file
        output_path: Optional path to save the results
        
    Returns:
        Tuple of (extracted_fields, potential_field_names)
    """
    # Read the transcript
    with open(transcript_path, 'r') as f:
        transcript = f.read()
    
    # Extract fields and potential field names
    extracted_fields = extract_to_flat_list(transcript)
    potential_names = find_potential_field_names(transcript)
    
    # Save results if output path provided
    if output_path:
        with open(output_path, 'w') as f:
            json.dump({
                'extracted_fields': extracted_fields,
                'potential_field_names': potential_names
            }, f, indent=2)
    
    return extracted_fields, potential_names

def main():
    """CLI entry point"""
    if len(sys.argv) < 2:
        print("Usage: python extract_transcript_fields.py <transcript_file> [output_file]")
        sys.exit(1)
    
    transcript_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        extracted_fields, potential_names = analyze_transcript(transcript_path, output_path)
        
        print(f"\nExtracted {len(extracted_fields)} fields from transcript:")
        for field in extracted_fields:
            print(f"  {field['field_name']}: {field['field_value']} (confidence: {field['confidence_score']})")
        
        print(f"\nIdentified {len(potential_names)} potential field names:")
        for name in potential_names:
            print(f"  {name}")
            
        if output_path:
            print(f"\nResults saved to: {output_path}")
    
    except Exception as e:
        print(f"Error analyzing transcript: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 