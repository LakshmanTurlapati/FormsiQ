"""
Service to fill PDF forms with extracted data.
"""
import os
import logging
import tempfile
import sys
import json
import time
from pathlib import Path
from django.conf import settings
from django.http import JsonResponse
from datetime import datetime
import traceback

import inspect
from . import pdf_field_processor
print(f"DEBUG: pdf_service.py is loading pdf_field_processor from: {inspect.getfile(pdf_field_processor)}")

# Import NameObject here
from pypdf.generic import NameObject

# Add the backend directory to the Python path so we can import the enhanced modules
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.append(str(backend_dir))

# Import our enhanced PDF handling modules and the new PDFFieldProcessor
from enhanced_pdf_handler import PDFAnalyzer, PDFFiller
from ai_field_mapper import AIFieldMapper
from .pdf_field_processor import PDFFieldProcessor

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
        # Use the PDFFieldProcessor for more detailed field extraction
        processor = PDFFieldProcessor(PDF_TEMPLATE_PATH)
        return processor.extract_fields_info()
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


def fill_pdf_form(request_data_param):
    """
    Processes extracted data, maps it to PDF fields, gathers UI display data,
    and then, if requested, attempts to fill the PDF form.
    
    Args:
        request_data_param: Django request object or dict containing 'fields' and optionally 'perform_fill' flag.
        
    Returns:
        dict: Containing 'filled_pdf_path' (str or None) and 'response_data' (dict for UI)
    """
    output_filename = None # Initialize to handle potential early exit
    output_path = None
    data_to_fill = {} # Initialize
    
    # Initial response structure for UI, to be populated regardless of PDF fill success
    # This structure will be returned even if PDF generation fails later
    ui_response_data = {
        'pdf_generation_status': 'pending', # Can be 'success' or 'failed'
        'message': '',
        'pdf_url': None,
        'filled_pdf_path_ref': None, # Path to the successfully filled PDF, if any
        'mapped_field_count': 0,
        'all_mapped_fields': [],
        'checkbox_fields': [],
        'radio_groups': []
    }

    try:
        # Renaming 'request' to 'request_data_param' to avoid conflict with Django's request object if this function is called directly
        # with a dict that might itself contain a 'request' key (though unlikely here).
        # Standardize access to 'fields' and 'perform_fill'
        if hasattr(request_data_param, 'body') and isinstance(request_data_param.body, bytes): # Django HttpRequest
            try:
                request_data = json.loads(request_data_param.body.decode('utf-8'))
            except json.JSONDecodeError:
                logger.error("Failed to parse JSON from request body.")
                raise PDFFillError("Invalid JSON in request body.")
        elif isinstance(request_data_param, dict): # Already a dictionary
            request_data = request_data_param
        else:
            logger.error(f"Unexpected request_data_param type: {type(request_data_param)}")
            raise PDFFillError("Invalid request data format.")

        extracted_data = request_data.get('fields', request_data.get('extracted_data', []))
        # perform_fill flag will be retrieved later, after extracted_data is confirmed.
        
        logger.info(f"Received {len(extracted_data)} extracted fields to process for PDF form")
        
        if not extracted_data:
            logger.error("No extracted data provided for PDF processing")
            raise PDFFillError("No extracted data provided")
            
        template_path = os.path.join(settings.MEDIA_ROOT, 'pdf', 'uniform_residential_loan_application.pdf')
        output_dir = os.path.join(settings.MEDIA_ROOT, 'pdf', 'output')
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = int(time.time())
        output_filename = f"filled_loan_application_{timestamp}.pdf"
        output_path = os.path.join(output_dir, output_filename)
        
        processor = PDFFieldProcessor(template_path)
        
        logger.info("Mapping extracted data to PDF fields...")
        data_to_fill = processor.map_user_data_to_pdf_fields(extracted_data) # This is Dict[pdf_key, str_or_NameObject]
        ui_response_data['mapped_field_count'] = len(data_to_fill)
        
        logger.info("Extracting full PDF field information for UI response...")
        all_pdf_fields_info = processor.extract_fields_info() # Detailed info for all fields in PDF
        all_pdf_checkboxes_details = processor.list_checkbox_fields() # Info about all checkboxes in PDF

        # Prepare 'all_mapped_fields' for UI - Now includes ALL PDF fields
        temp_all_mapped_fields = []
        for pdf_key, pdf_field_detail in all_pdf_fields_info.items():
            display_name = str(pdf_field_detail.get('name', pdf_key))
            field_type_obj = pdf_field_detail.get('field_type', NameObject('Unknown'))
            field_type_str = str(field_type_obj) if isinstance(field_type_obj, NameObject) else field_type_obj
            
            mapped_value = data_to_fill.get(pdf_key) # This could be a string or NameObject
            
            value_for_ui = None
            if mapped_value is not None:
                value_for_ui = str(mapped_value) if isinstance(mapped_value, NameObject) else mapped_value
            else:
                # Only mark as not mapped if it's not a button type (buttons handled by checkboxes/radios)
                # or if it's a button type but doesn't have kids (standalone button that's not a typical checkbox)
                # This avoids marking radio group containers themselves as "not mapped" for value
                is_container_button = field_type_str == '/Btn' and pdf_field_detail.get('kids')
                if not is_container_button: # Text fields, or non-container buttons
                     value_for_ui = "__FIELD_NOT_MAPPED__"
                # For container buttons (radio groups), their "value" is the selected kid, handled by radio_groups section

            # Add to list if it's not a radio group container (those are handled in radio_groups)
            # or if it IS a radio group container but we want to list it (e.g. for debugging, but typically not shown as a fillable "text" field)
            # For now, let's exclude radio group containers from 'all_mapped_fields' to avoid redundancy,
            # as their state is fully described in 'radio_groups'.
            # We will also exclude checkbox containers if they are handled by `list_checkbox_fields` better.
            
            # We only want to add text fields, or unmapped/unhandled button types to this list.
            # Checkboxes are handled by `temp_checkbox_fields`. Radio groups by `temp_radio_groups`.
            if field_type_str == '/Tx': # It's a Text field
                temp_all_mapped_fields.append({
                    'name': display_name,
                    'key': pdf_key,
                    'value': value_for_ui,
                    'field_type': field_type_str
                })
            elif field_type_str == '/Btn' and not pdf_field_detail.get('kids') and pdf_key not in all_pdf_checkboxes_details:
                # A standalone button that wasn't categorized as a checkbox by list_checkbox_fields
                # These might be actual action buttons, or oddly defined checkboxes.
                temp_all_mapped_fields.append({
                    'name': display_name,
                    'key': pdf_key,
                    'value': value_for_ui if value_for_ui is not None else "__FIELD_NOT_MAPPED__", # Ensure it gets a not_mapped if no value
                    'field_type': field_type_str
                })

        ui_response_data['all_mapped_fields'] = temp_all_mapped_fields

        # Prepare 'checkbox_fields' for UI (all checkboxes from PDF and their intended state)
        temp_checkbox_fields = []
        for cb_key, cb_detail_from_processor in all_pdf_checkboxes_details.items():
            descriptive_name = str(cb_detail_from_processor.get('partial_name', cb_key))
            pdf_on_value_str = str(cb_detail_from_processor.get('on_state_value', '/Yes')) 
            
            intended_status_checked = False
            if cb_key in data_to_fill: 
                intended_value_obj = data_to_fill[cb_key] 
                if isinstance(intended_value_obj, NameObject) and intended_value_obj != NameObject("/Off"):
                    intended_status_checked = True
            # If not in data_to_fill, it remains false (unchecked) by default for UI.
            
            temp_checkbox_fields.append({
                'key': cb_key,
                'name': descriptive_name,
                'checked': intended_status_checked, 
                'on_value_in_pdf': pdf_on_value_str 
            })
        ui_response_data['checkbox_fields'] = temp_checkbox_fields

        # Prepare 'radio_groups' for UI (all radio groups from PDF and their intended selection)
        temp_radio_groups = []
        for field_key, field_detail in all_pdf_fields_info.items():
            if field_detail.get('field_type') == NameObject('/Btn') and 'kids' in field_detail and field_detail['kids']:
                group_descriptive_name = str(field_detail.get('name', field_key))
                options_for_ui = []
                intended_selected_option_export_value = None 

                selected_kid_on_state_nameobj = data_to_fill.get(field_key)

                for kid_info in field_detail['kids']: 
                    option_descriptive_name = str(kid_info.get('name', 'Unknown Option'))
                    option_export_value_str = str(kid_info.get('export_value', '')) 
                    
                    options_for_ui.append({
                        'name': option_descriptive_name,
                        'value': option_export_value_str 
                    })
                    
                    if selected_kid_on_state_nameobj and isinstance(selected_kid_on_state_nameobj, NameObject) and selected_kid_on_state_nameobj == NameObject(option_export_value_str):
                        intended_selected_option_export_value = option_export_value_str
                
                temp_radio_groups.append({
                    'name': group_descriptive_name, # This is the /T of the radio group field itself
                    'key': field_key, # The PDF key for the radio group
                    'options': options_for_ui,
                    'selected_value': intended_selected_option_export_value # The export value of the selected option, or null
                })
        ui_response_data['radio_groups'] = temp_radio_groups
        
        # Update mapped_field_count to reflect actual mapped data, not just length of all_mapped_fields
        # Count items in data_to_fill that were actually present in all_pdf_fields_info
        actually_mapped_count = 0
        for k_mapped in data_to_fill:
            if k_mapped in all_pdf_fields_info:
                 actually_mapped_count +=1
        ui_response_data['mapped_field_count'] = actually_mapped_count

        # At this point, ui_response_data is populated with all displayable field info.
        # Now, check if we should attempt the actual PDF filling.
        
        should_perform_fill = request_data.get('perform_fill', True) # Get 'perform_fill' flag from request_data
        logger.info(f"PDF Generation: 'perform_fill' flag is set to {should_perform_fill}.")

        if should_perform_fill:
            logger.info(f"Attempting to fill PDF with {len(data_to_fill)} mapped fields into {output_path}")
            try:
                # ADDITIONAL DEBUGGING: Log all checkbox and radio button values
                logger.info("DEBUG: Checkbox and radio button values being sent to processor.fill_pdf_form:")
                checkbox_count = 0
                radio_count = 0
                
                # Improved preprocessing for checkboxes and radio buttons
                processed_button_fields = {}
                for key, value in data_to_fill.items():
                    if key in processor.fields:
                        field_obj = processor.fields[key]
                        field_type = field_obj.get('/FT')
                        kids = field_obj.get('/Kids')
                        
                        if field_type == NameObject('/Btn'):
                            # For checkboxes (no kids)
                            if not kids:
                                # Ensure checkboxes are boolean values
                                if isinstance(value, bool):
                                    processed_button_fields[key] = value
                                elif isinstance(value, str):
                                    processed_button_fields[key] = value.lower() in ["yes", "true", "on", "1", "y"]
                                elif isinstance(value, NameObject):
                                    processed_button_fields[key] = str(value) != '/Off'
                                else:
                                    processed_button_fields[key] = False
                                
                                logger.info(f"Preprocessed checkbox {key}: {value} → {processed_button_fields[key]} (boolean)")
                            
                            # For radio buttons (with kids)
                            elif kids:
                                # Ensure radio button values are NameObject values with leading slash
                                if isinstance(value, NameObject):
                                    processed_button_fields[key] = value
                                elif isinstance(value, str):
                                    if not value.startswith('/'):
                                        processed_button_fields[key] = NameObject(f"/{value}")
                                    else:
                                        processed_button_fields[key] = NameObject(value)
                                    
                                    logger.info(f"Preprocessed radio button {key}: {value} → {processed_button_fields[key]} (NameObject)")
                
                # Update data_to_fill with processed button values
                data_to_fill.update(processed_button_fields)
                logger.info(f"Updated {len(processed_button_fields)} button fields with correct types")
                
                # This is where the PDF file is actually written
                filled_pdf_actual_path = processor.fill_pdf_form(data_to_fill, output_path) 
                
                # VERIFY THE FILLED PDF
                logger.info(f"Verifying filled PDF at: {filled_pdf_actual_path}")
                try:
                    from pypdf import PdfReader
                    verification_reader = PdfReader(filled_pdf_actual_path)
                    logger.info(f"Verification: PDF has {len(verification_reader.pages)} pages and contains {len(verification_reader.get_fields() or {})} form fields")
                except Exception as verify_err:
                    logger.error(f"Verification error: {verify_err}")
                
                # Make sure the URL starts with /media/ to match Django's MEDIA_URL setting
                pdf_url = f"/media/pdf/output/{output_filename}"
                ui_response_data['pdf_generation_status'] = 'success'
                ui_response_data['message'] = 'PDF generated successfully. Field data below shows mapped values.'
                ui_response_data['pdf_url'] = pdf_url
                ui_response_data['filled_pdf_path_ref'] = filled_pdf_actual_path
                logger.info(f"PDF filled successfully and saved to {filled_pdf_actual_path}")

            except Exception as pdf_fill_error:
                logger.error(f"Error during PDF file generation stage: {str(pdf_fill_error)}")
                logger.error(traceback.format_exc())
                ui_response_data['pdf_generation_status'] = 'failed'
                ui_response_data['message'] = f"Field data mapping processed. However, PDF file generation failed: {str(pdf_fill_error)}"
                # filled_pdf_path_ref remains None
        else:
            logger.info("PDF filling was deferred based on 'perform_fill' flag.")
            ui_response_data['pdf_generation_status'] = 'deferred'
            ui_response_data['message'] = 'Data processed and mapped for display. PDF generation was not requested.'
            ui_response_data['pdf_url'] = None
            ui_response_data['filled_pdf_path_ref'] = None


        # Log the detailed ui_response_data before returning
        try:
            logger.info("--- DETAILED UI RESPONSE DATA (fill_pdf_form) ---")
            logger.info(json.dumps(ui_response_data, indent=2, default=str)) # Use default=str for any non-serializable objects like NameObject if they sneak in
            logger.info("--- END DETAILED UI RESPONSE DATA ---")
        except Exception as log_e:
            logger.error(f"Error logging ui_response_data: {log_e}")

        return {
            'filled_pdf_path': ui_response_data['filled_pdf_path_ref'], # This is the actual path if successful, else None
            'response_data': ui_response_data
        }
        
    except PDFFillError as pfe: # Errors from pre-requisites like no data, or from processor methods before actual fill
        logger.error(f"PDFFillError occurred: {str(pfe)}")
        logger.error(traceback.format_exc())
        ui_response_data['pdf_generation_status'] = 'failed'
        ui_response_data['message'] = f"Error preparing data for PDF: {str(pfe)}"
        # Ensure mapped_field_count is based on the data_to_fill state at this point
        ui_response_data['mapped_field_count'] = len(data_to_fill) 
        return {
            'filled_pdf_path': None,
            'response_data': ui_response_data
        }
    except Exception as e:
        logger.error(f"Unexpected error in fill_pdf_form service: {str(e)}")
        logger.error(traceback.format_exc())
        # Populate a default error response if ui_response_data wasn't fully formed
        error_response = {
            'pdf_generation_status': 'failed',
            'message': f"An unexpected error occurred: {str(e)}",
            'pdf_url': None,
            'filled_pdf_path_ref': None,
            'mapped_field_count': len(data_to_fill), # data_to_fill might have some content
            'all_mapped_fields': [],
            'checkbox_fields': [],
            'radio_groups': []
        }
        # Try to merge any partially populated ui_response_data with defaults
        final_error_response = {**error_response, **ui_response_data} 
        final_error_response['message'] = error_response['message'] # Ensure the most recent error message is used
        final_error_response['pdf_generation_status'] = 'failed'

        # Log the detailed final_error_response before returning in case of unexpected error
        try:
            logger.info("--- DETAILED UI ERROR RESPONSE DATA (fill_pdf_form unexpected error) ---")
            logger.info(json.dumps(final_error_response, indent=2, default=str))
            logger.info("--- END DETAILED UI ERROR RESPONSE DATA ---")
        except Exception as log_e:
            logger.error(f"Error logging final_error_response: {log_e}")

        return {
            'filled_pdf_path': None,
            'response_data': final_error_response
        } 