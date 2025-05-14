"""
Service to fill PDF forms with extracted data.
"""
import os
import logging
import tempfile
import sys
from pathlib import Path
from django.conf import settings

# Add the backend directory to the Python path so we can import the enhanced modules
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.append(str(backend_dir))

# Import our enhanced PDF handling modules
from enhanced_pdf_handler import PDFAnalyzer, PDFFiller
from ai_field_mapper import AIFieldMapper

# Import the legacy field mapping for backward compatibility
from .field_mapping import get_pdf_field_name as legacy_get_pdf_field_name, LLM_TO_PDF_FIELD_MAP

logger = logging.getLogger(__name__)

# Path to the PDF template
PDF_TEMPLATE_PATH = os.path.join(settings.BASE_DIR, 'media', 'pdf', 'uniform_residential_loan_application.pdf')
# Path to save the field mapping if it needs to be generated
FIELD_MAPPING_PATH = os.path.join(settings.BASE_DIR, 'media', 'pdf', 'field_mapping.json')

MINIMUM_ACCEPTABLE_MAPPING_ENTRIES = 50 # Heuristic: if JSON map has fewer entries, it's likely stale/incomplete


class PDFFillError(Exception):
    """Exception raised for errors in the PDF filling process."""
    pass


def get_pdf_fields_info():
    """
    Get information about all fillable fields in the PDF template.
    This is useful for debugging and identifying field names.
    
    Returns:
        dict: A dictionary of PDF field names and their attributes
    """
    try:
        analyzer = PDFAnalyzer(PDF_TEMPLATE_PATH)
        return analyzer.get_all_fields_info()
    except Exception as e:
        logger.error(f"Error getting PDF fields: {str(e)}")
        raise PDFFillError(f"Error getting PDF fields: {str(e)}")


def get_pdf_field_categories():
    """
    Categorize the PDF fields by type (text, checkbox, etc.)
    
    Returns:
        dict: A dictionary with categories as keys and lists of field names as values
    """
    try:
        analyzer = PDFAnalyzer(PDF_TEMPLATE_PATH)
        return analyzer.categorize_fields()
    except Exception as e:
        logger.error(f"Error categorizing PDF fields: {str(e)}")
        raise PDFFillError(f"Error categorizing PDF fields: {str(e)}")


def map_fields(extracted_fields):
    """
    Map the extracted field names to PDF field names.
    Prioritizes a comprehensive mapping from field_mapping.py if the stored JSON seems incomplete,
    and ensures the .py version takes precedence for shared keys.
    
    Args:
        extracted_fields (list): List of field objects with field_name
        
    Returns:
        dict: Mapping from extracted field names to PDF field names
    """
    final_authoritative_map = {}
    mapper = AIFieldMapper(PDF_TEMPLATE_PATH) # Assuming AIFieldMapper might still be useful for its methods

    try:
        # Start with a copy of the code-defined map as the base, ensuring it's the primary source
        final_authoritative_map = LLM_TO_PDF_FIELD_MAP.copy()
        logger.info(f"Initialized mapping with LLM_TO_PDF_FIELD_MAP from .py file ({len(final_authoritative_map)} entries).")

        if os.path.exists(FIELD_MAPPING_PATH):
            try:
                json_loaded_map = mapper.load_mapping(FIELD_MAPPING_PATH)
                logger.info(f"Loaded existing field mapping from JSON with {len(json_loaded_map)} entries.")
                
                # Update the authoritative map with any entries from JSON that are NOT in the .py map.
                # The .py map's values for shared keys are preserved.
                original_keys = set(final_authoritative_map.keys())
                for key, value in json_loaded_map.items():
                    if key not in original_keys:
                        final_authoritative_map[key] = value
                
                logger.info(f"Merged map. JSON entries for non-conflicting keys were added. .py map entries take precedence for conflicts.")

            except Exception as e_load:
                logger.warning(f"Could not load existing JSON mapping: {str(e_load)}. Proceeding with .py map only.")
        else:
            logger.info("No existing JSON field mapping file found. Using .py map as is.")

        # Always try to save the final, authoritative map back to JSON.
        # This keeps the JSON cache consistent with the .py file as the master + any non-conflicting JSON additions.
        try:
            mapper.save_mapping(final_authoritative_map, FIELD_MAPPING_PATH)
            logger.info(f"Saved current authoritative field mapping ({len(final_authoritative_map)} entries) to {FIELD_MAPPING_PATH}")
        except Exception as e_save:
            logger.error(f"Could not save authoritative field mapping to JSON: {str(e_save)}")

        if not final_authoritative_map:
             logger.error("Field mapping is empty after all attempts.")
             return {}

        logger.info(f"Final field mapping has {len(final_authoritative_map)} entries.")
        return final_authoritative_map
        
    except Exception as e:
        logger.error(f"Error in map_fields: {str(e)}. Returning empty map.", exc_info=True)
        # Fallback to raw LLM_TO_PDF_FIELD_MAP if any severe error occurs during JSON processing
        if LLM_TO_PDF_FIELD_MAP:
            logger.warning("map_fields encountered a severe error, falling back to returning raw LLM_TO_PDF_FIELD_MAP.")
            return LLM_TO_PDF_FIELD_MAP.copy()
        return {}


def fill_pdf_form(extracted_fields):
    """
    Fill the PDF form with extracted data.
    
    Args:
        extracted_fields (list): List of dictionaries with field_name, field_value, and confidence_score
        
    Returns:
        str: Path to the filled PDF file
        
    Raises:
        PDFFillError: If there's an error in the PDF filling process
    """
    try:
        field_mapping = map_fields(extracted_fields) # Now uses a more robust mapping
        
        if not field_mapping:
            logger.error("Field mapping failed to produce a usable mapping.")
            # No longer falling back to legacy_get_pdf_field_name here as map_fields should be comprehensive
            raise PDFFillError("Failed to map extracted fields to PDF fields (map_fields returned empty).")

        # --- Logic for concatenating multipart fields ---
        # Example: Borrower Name (First, Middle, Last), Address (Street, City, State, Zip)
        # This needs to be done carefully based on PDF field structure and LLM output structure.
        
        processed_for_concatenation = {}
        single_fields = []

        # Define multipart fields and their PDF target + order
        # This structure assumes specific LLM field names for parts.
        multipart_field_config = {
            "Borrower Name": { # Target PDF Field from LLM_TO_PDF_FIELD_MAP
                "parts": ["Borrower First Name", "Borrower Middle Name", "Borrower Last Name", "Borrower Suffix"],
                "separator": " "
            },
            "Co-Borrower Name": {
                 "parts": ["Co-Borrower First Name", "Co-Borrower Middle Name", "Co-Borrower Last Name", "Co-Borrower Suffix"],
                 "separator": " "
            },
            "Borrower Present Address": { # Target PDF Field
                "parts": ["Current Street Address", "Current City", "Current State", "Current Zip Code"],
                "separator": ", " # Typical address format
            },
            # Add other multipart fields like "Property Address" if structured similarly
            "Subject Property Address": {
                 "parts": ["Property Street Address", "Property City", "Property State", "Property Zip Code"],
                 "separator": ", "
            }
        }
        
        # Create a dictionary from extracted_fields for easier lookup by llm_field_name
        llm_data_dict = {f["field_name"]: f for f in extracted_fields if f.get("field_value") is not None and f.get("confidence_score",0) >=0.1}

        concatenated_values = {}

        for pdf_target_key, config in multipart_field_config.items():
            value_parts = []
            any_part_present = False
            highest_confidence = 0.0
            for part_llm_name in config["parts"]:
                if part_llm_name in llm_data_dict:
                    field_part_obj = llm_data_dict[part_llm_name]
                    value_parts.append(str(field_part_obj["field_value"]))
                    any_part_present = True
                    highest_confidence = max(highest_confidence, field_part_obj.get("confidence_score", 0))
                    del llm_data_dict[part_llm_name] # Remove from dict to avoid reprocessing
                else:
                    # Add empty string if a middle part is missing to maintain order if separator matters
                    # For names/addresses, usually just skip missing middle parts.
                    pass 
            
            if any_part_present:
                concatenated_values[pdf_target_key] = {
                    "field_value": config["separator"].join(filter(None, value_parts)),
                    "confidence_score": highest_confidence, # Use highest confidence of parts
                    # The 'field_name' for mapping purposes should be the conceptual group name if it exists in map
                    # or one of its parts if the group name itself isn't directly mapped.
                    # This depends on how LLM_TO_PDF_FIELD_MAP is structured for these.
                    # For now, we assume pdf_target_key is the one used in field_mapping (e.g. "Borrower Name")
                    "original_llm_group": pdf_target_key 
                }

        # Add remaining single fields
        for llm_field_name, field_obj in llm_data_dict.items():
            single_fields.append(field_obj)
        
        # Combine concatenated and single fields for data preparation
        # The `field_data` preparation loop will use these.
        # `concatenated_values` items need to be transformed slightly to match `extracted_fields` items
        
        final_fields_for_pdf = single_fields
        for mapped_pdf_key, data in concatenated_values.items():
            # We need to find an appropriate LLM field name that maps to this mapped_pdf_key
            # or assume mapped_pdf_key can be used if it's in field_mapping.
            # This is tricky. Let's assume the 'original_llm_group' name is what should be used
            # for mapping lookups if it exists in field_mapping.
            # Otherwise, the mapping for concatenated fields is complex.
            
            # For simplicity, we'll pass the concatenated value using the PDF target key directly.
            # The `field_data` loop needs to be aware of this.
            # This means the field_mapping should map "Borrower Name" (the group) to the PDF field.
            final_fields_for_pdf.append({
                "field_name": data["original_llm_group"], # This must be a key in field_mapping
                "field_value": data["field_value"],
                "confidence_score": data["confidence_score"]
            })

        # --- Original field_data preparation loop (slightly modified) ---
        field_data = {}
        
        for field in final_fields_for_pdf: # Iterate over potentially concatenated fields
            # field_value can be None if confidence was too low or 'Not Found'
            if field.get('field_value') is None: # Check added in previous edit, keep it
                 logger.info(f"Skipping field \'{field.get('field_name')}\' due to None value before processing.")
                 continue

            llm_field_name = field['field_name']
            original_field_value = field['field_value'] # This is now potentially a concatenated string or original value

            pdf_field_target_name = field_mapping.get(llm_field_name)
            
            # The legacy_get_pdf_field_name fallback is less critical if map_fields is robust
            # but can be kept as a last resort if field_mapping might still miss something.
            if not pdf_field_target_name and llm_field_name not in multipart_field_config: # Avoid legacy for groups already handled
                 pdf_field_target_name = legacy_get_pdf_field_name(llm_field_name)
                 if pdf_field_target_name:
                      logger.warning(f"Field \'{llm_field_name}\' used legacy mapping directly. Consider updating primary mappings.")
            
            if not pdf_field_target_name:
                logger.warning(f"No PDF mapping found for LLM field: {llm_field_name} after all mapping attempts. Skipping.")
                continue

            value_to_set = original_field_value # Start with the (potentially concatenated) value

            # Handle \"Group: Value\" convention from LLM field names for radio/choice buttons
            # This logic applies if llm_field_name itself contains \": \", e.g. "Mortgage Type: Conventional"
            # For concatenated fields, llm_field_name is the group name (e.g. "Borrower Name"), so this won't apply to them.
            if ": " in llm_field_name and not field.get("original_llm_group"): # Check it's not a pre-concatenated field
                parts = llm_field_name.split(": ", 1)
                if len(parts) == 2:
                    # original_field_value for these choice fields is expected to be 'Yes' or True from test script
                    if original_field_value in [True, 'True', 'true', 'Yes', 'yes', 'On', 'on']:
                         value_to_set = parts[1].strip() # e.g., "VA"
                    else:
                        logger.info(f"LLM choice field \'{llm_field_name}\' has falsy value \'{original_field_value}\', not setting option \'{parts[1].strip()}\'.")
                        continue 
            elif llm_field_name not in multipart_field_config: # Apply boolean conversion only to non-group, non-choice fields
                if original_field_value is True:
                    value_to_set = "Yes"
                elif original_field_value is False:
                    logger.info(f"LLM field \'{llm_field_name}\' is False, not setting PDF field \'{pdf_field_target_name}\'.")
                    continue
            
            if value_to_set is not None:
                field_data[pdf_field_target_name] = value_to_set
                logger.info(f"Prepared PDF field: \'{pdf_field_target_name}\' with value: \'{value_to_set}\' (from LLM field: \'{llm_field_name}\')")
            else:
                logger.warning(f"Value for LLM field \'{llm_field_name}\' became None after processing, not setting PDF field \'{pdf_field_target_name}\'.")

        if not field_data:
            logger.warning("No data prepared for PDF filling after mapping. Extracted fields might be empty or not mappable.")
            # Depending on requirements, this could be an error or an allowed state (e.g., return empty PDF)
            # For now, let it proceed, as an empty field_data might be valid if no relevant fields were extracted.
            # If an empty filled PDF is an error, raise PDFFillError here.

        # Create a temporary file path for the output
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            output_path = temp_file.name
        
        # Use the enhanced PDF filler to fill the form
        # Removed the fallback to basic PDF filling. If this fails, an error will be raised.
        filler = PDFFiller(PDF_TEMPLATE_PATH)
        filled_pdf_path = filler.fill_form(
            field_data,
            output_path
        )
        
        # Log successful filling
        logger.info(f"Successfully filled PDF with {len(field_data)} fields at {filled_pdf_path}")
        return filled_pdf_path
            
    except Exception as e:
        # Catch any exception during the process (including from PDFFiller or mapping)
        # and wrap it in PDFFillError
        logger.error(f"Error during PDF filling process: {str(e)}", exc_info=True)
        # If it's already a PDFFillError, re-raise it directly
        if isinstance(e, PDFFillError):
            raise
        # Otherwise, wrap it
        raise PDFFillError(f"PDF filling failed: {str(e)}") 