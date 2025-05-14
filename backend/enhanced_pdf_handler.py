#!/usr/bin/env python
"""
Enhanced PDF Handler for FormsIQ

This module provides advanced capabilities for:
1. Identifying and analyzing fillable PDF fields
2. Extracting field properties (type, constraints, options, etc.)
3. Intelligent field mapping between extracted data and PDF fields
4. Advanced PDF filling with proper type handling and validation
5. Smart text handling for text that exceeds field size
"""

import os
import sys
import json
import tempfile
import logging
import warnings
import textwrap
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, TextStringObject, BooleanObject, DictionaryObject, ArrayObject
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Filter PyPDF warning messages about wrong pointing objects
class PyPDFWarningFilter(logging.Filter):
    def filter(self, record):
        return not (record.levelno == logging.WARNING and 
                  "Ignoring wrong pointing object" in record.getMessage())

# Add the filter to the pypdf logger
pypdf_logger = logging.getLogger('pypdf._reader')
pypdf_logger.addFilter(PyPDFWarningFilter())

# PDF field types mapping from PyPDF
FIELD_TYPE_MAP = {
    '/Tx': 'text',         # Text field
    '/Btn': 'button',      # Button (checkbox, radio button)
    '/Ch': 'choice',       # Choice field (dropdown, listbox)
    '/Sig': 'signature',   # Signature field
}

# Button flags for checkboxes and radio buttons
CHECKBOX_MASK = 1 << 15
RADIO_BUTTON_MASK = 1 << 16

class PDFFieldInfo:
    """Class to hold detailed information about a PDF field"""
    
    def __init__(self, name: str, field_obj: Dict):
        self.name = name
        self.raw_field = field_obj
        self.field_type = self._extract_field_type()
        self.field_subtype = self._extract_field_subtype()
        self.value = self._extract_value()
        self.options = self._extract_options()
        self.required = self._is_required()
        self.readonly = self._is_readonly()
        self.max_length = self._get_max_length()
        self.multiline = self._is_multiline()
        self.rect = self._get_rect()
        
    def _extract_field_type(self) -> str:
        """Extract the basic field type"""
        ft = self.raw_field.get('/FT', 'Unknown')
        return FIELD_TYPE_MAP.get(ft, 'unknown')
    
    def _extract_field_subtype(self) -> str:
        """Extract the field subtype for buttons"""
        if self.field_type != 'button':
            return 'n/a'
            
        flags = self.raw_field.get('/Ff', 0)
        if flags & CHECKBOX_MASK:
            return 'checkbox'
        elif flags & RADIO_BUTTON_MASK:
            return 'radio'
        else:
            return 'pushbutton'
            
    def _extract_value(self) -> Any:
        """Extract the current value of the field"""
        return self.raw_field.get('/V', None)
    
    def _extract_options(self) -> List[str]:
        """Extract options for choice fields"""
        if self.field_type != 'choice':
            return []
            
        opt = self.raw_field.get('/Opt', [])
        return [str(option) for option in opt]
    
    def _is_required(self) -> bool:
        """Check if the field is required"""
        flags = self.raw_field.get('/Ff', 0)
        return bool(flags & (1 << 22))  # Required flag
    
    def _is_readonly(self) -> bool:
        """Check if the field is read-only"""
        flags = self.raw_field.get('/Ff', 0)
        return bool(flags & (1 << 0))  # Read-only flag
    
    def _get_max_length(self) -> Optional[int]:
        """Get maximum length for text fields"""
        if self.field_type != 'text':
            return None
            
        return self.raw_field.get('/MaxLen', None)
    
    def _is_multiline(self) -> bool:
        """Check if the field is multiline"""
        if self.field_type != 'text':
            return False
            
        flags = self.raw_field.get('/Ff', 0)
        return bool(flags & (1 << 12))  # Multiline flag
    
    def _get_rect(self) -> Optional[List[float]]:
        """Get the field's rectangle dimensions"""
        # Try to find the widget annotation with this field's name
        if '/Kids' in self.raw_field:
            for kid in self.raw_field['/Kids']:
                try:
                    kid_obj = kid.get_object()
                    if '/Rect' in kid_obj:
                        return kid_obj['/Rect']
                except Exception:
                    continue
        
        # If no kids or couldn't find rect in kids, try the field itself
        return self.raw_field.get('/Rect', None)
    
    def estimate_character_limit(self) -> Optional[int]:
        """Estimate the number of characters that can fit in this field"""
        if self.field_type != 'text' or not self.rect:
            return None
            
        # Extract width and height from rect (x1, y1, x2, y2)
        try:
            width = abs(float(self.rect[2]) - float(self.rect[0]))
            height = abs(float(self.rect[3]) - float(self.rect[1]))
            
            # Rough estimate: 7 pixels per character, 14 pixels per line
            # This is a very rough estimate and might need adjustment
            chars_per_line = int(width / 7)
            lines = int(height / 14)
            
            if self.multiline:
                return chars_per_line * lines
            else:
                return chars_per_line
        except (IndexError, ValueError, TypeError):
            return None
        
    def to_dict(self) -> Dict:
        """Convert field info to dictionary"""
        char_limit = self.estimate_character_limit()
        return {
            'name': self.name,
            'type': self.field_type,
            'subtype': self.field_subtype,
            'current_value': str(self.value) if self.value is not None else None,
            'options': self.options,
            'required': self.required,
            'readonly': self.readonly,
            'max_length': self.max_length,
            'multiline': self.multiline,
            'estimated_char_limit': char_limit,
            'rect': self.rect
        }
    
    def can_fill_with(self, value: Any) -> Tuple[bool, str]:
        """
        Check if the field can be filled with the given value
        Returns: (can_fill, error_message)
        """
        # Check read-only
        if self.readonly:
            return False, "Field is read-only"
            
        # Handle different field types
        if self.field_type == 'text':
            # Check max length if specified
            if self.max_length is not None and len(str(value)) > self.max_length:
                return False, f"Value exceeds maximum length ({self.max_length})"
            return True, ""
            
        elif self.field_type == 'choice':
            # Check if value is in options
            str_value = str(value)
            if not self.options:
                return True, ""  # No options to validate against
            if str_value not in [str(opt) for opt in self.options]:
                return False, f"Value not in allowed options: {', '.join(self.options)}"
            return True, ""
            
        elif self.field_type == 'button':
            if self.field_subtype == 'checkbox':
                # For checkboxes, we accept boolean-like values
                try:
                    bool_value = bool(value) 
                    return True, ""
                except ValueError:
                    return False, "Value must be boolean-like for checkbox"
            elif self.field_subtype == 'radio':
                # For radio buttons, check against options
                return True, ""  # We'd need to check against specific radio values
                
        return True, ""  # Default to allowing the value


class PDFAnalyzer:
    """Class to analyze and extract information from PDF forms"""
    
    def __init__(self, pdf_path: str):
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        self.pdf_path = pdf_path
        
        # Configure PyPDF to suppress the warnings about wrong pointing objects
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=UserWarning, module="pypdf")
            try:
                self.reader = PdfReader(pdf_path)
            except Exception as e:
                if "PdfReader has no attribute 'root'" in str(e):
                    raise ValueError(f"Error reading PDF: The file appears to be corrupted or not a valid PDF form: {str(e)}")
                raise
        
        # Check if the PDF has AcroForm fields
        try:
            if not hasattr(self.reader, 'get_fields') or not self.reader.get_fields():
                raise ValueError("The provided PDF does not contain fillable form fields")
        except Exception as e:
            raise ValueError(f"Error accessing PDF form fields: {str(e)}")
            
        self.raw_fields = self.reader.get_fields()
        self.fields = self._process_fields()
        
    def _process_fields(self) -> Dict[str, PDFFieldInfo]:
        """Process all fields and create PDFFieldInfo objects"""
        fields_info = {}
        
        for name, field_obj in self.raw_fields.items():
            fields_info[name] = PDFFieldInfo(name, field_obj)
            
        return fields_info
    
    def get_field_names(self) -> List[str]:
        """Get all field names"""
        return list(self.fields.keys())
    
    def get_field_info(self, field_name: str) -> Optional[PDFFieldInfo]:
        """Get detailed info for a specific field"""
        return self.fields.get(field_name)
    
    def get_all_fields_info(self) -> Dict[str, Dict]:
        """Get info for all fields as dictionary"""
        return {name: field.to_dict() for name, field in self.fields.items()}
    
    def export_fields_info(self, output_path: Optional[str] = None) -> str:
        """Export field information to a JSON file"""
        if not output_path:
            output_path = os.path.splitext(self.pdf_path)[0] + "_fields_info.json"
            
        fields_dict = self.get_all_fields_info()
        
        with open(output_path, 'w') as f:
            json.dump(fields_dict, f, indent=2)
            
        return output_path
    
    def categorize_fields(self) -> Dict[str, List[str]]:
        """Categorize fields by type"""
        categories = {
            'text': [],
            'checkbox': [],
            'radio': [],
            'choice': [],
            'signature': [],
            'other': []
        }
        
        for name, field in self.fields.items():
            if field.field_type == 'text':
                categories['text'].append(name)
            elif field.field_type == 'button':
                if field.field_subtype == 'checkbox':
                    categories['checkbox'].append(name)
                elif field.field_subtype == 'radio':
                    categories['radio'].append(name)
                else:
                    categories['other'].append(name)
            elif field.field_type == 'choice':
                categories['choice'].append(name)
            elif field.field_type == 'signature':
                categories['signature'].append(name)
            else:
                categories['other'].append(name)
                
        return categories


class PDFFiller:
    """Class to fill PDF forms with data"""
    
    def __init__(self, pdf_path: str):
        self.analyzer = PDFAnalyzer(pdf_path)
        self.pdf_path = pdf_path
        
    def _prepare_text_value(self, field_info: PDFFieldInfo, value: str) -> str:
        """
        Prepare a text value for a field, handling overflow and formatting
        
        Args:
            field_info: Information about the PDF field
            value: The text value to prepare
            
        Returns:
            str: The prepared text value
        """
        if not value or not isinstance(value, str):
            return value
            
        # If it's not a text field, return as is
        if field_info.field_type != 'text':
            return value
            
        # Get the estimated character limit
        char_limit = field_info.estimate_character_limit()
        
        # If no limit could be determined, use the max_length if available
        if char_limit is None and field_info.max_length is not None:
            char_limit = field_info.max_length
            
        # If we couldn't determine a limit, just return as is
        if char_limit is None:
            return value
            
        # If the value is shorter than the limit, return as is
        if len(value) <= char_limit:
            return value
            
        # If it's a multiline field, wrap the text
        if field_info.multiline:
            # Estimate chars per line
            if field_info.rect:
                width = abs(float(field_info.rect[2]) - float(field_info.rect[0]))
                chars_per_line = max(10, int(width / 7))  # Assume 7 pixels per character
            else:
                chars_per_line = 40  # Default fallback
                
            # Wrap the text
            wrapped_text = textwrap.fill(value, width=chars_per_line)
            
            # If still too long, truncate
            if len(wrapped_text) > char_limit:
                wrapped_text = wrapped_text[:char_limit-3] + "..."
                
            return wrapped_text
        else:
            # For single-line fields, truncate if too long
            return value[:char_limit-3] + "..." if len(value) > char_limit else value
    
    def _handle_overflow_text(self, text: str, field_name: str, writer: PdfWriter) -> None:
        """
        Handle text that overflows a field by adding it to a separate page or annotation
        
        Args:
            text: The full text that doesn't fit in the original field
            field_name: The name of the field that couldn't fit the text
            writer: The PDF writer object
            
        Note: This is an advanced feature and may not work with all PDFs
        """
        # This is a placeholder for future implementation
        # For now, we just log that overflow occurred
        logger.warning(f"Text overflow in field {field_name}. Consider using a dedicated comments page.")
        
    def fill_form(self, field_data: Dict[str, Any], output_path: str, flatten: bool = False) -> str:
        """
        Fill a PDF form with the provided data.
        
        Args:
            field_data: Dict mapping field names to values
            output_path: Path to save the filled PDF
            flatten: Whether to flatten the PDF (remove form fields)
            
        Returns:
            Path to the filled PDF
        """
        try:
            # Create PDF reader and writer objects
            # Suppress PyPDF warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                
                # Create a new writer
                writer = PdfWriter()
                
                # Add all pages from the original PDF
                for page in self.analyzer.reader.pages:
                    writer.add_page(page)
                
                # Ensure we have an /AcroForm by copying it from reader
                # This fixes the "No /AcroForm dictionary in PDF of PdfWriter Object" error
                try:
                    if hasattr(self.analyzer.reader, 'root') and "/AcroForm" in self.analyzer.reader.root:
                        writer._root_object.update({
                            NameObject("/AcroForm"): self.analyzer.reader.root["/AcroForm"]
                        })
                    else:
                        # Ensure we have an empty AcroForm dictionary if none exists
                        writer._root_object.update({
                            NameObject("/AcroForm"): DictionaryObject()
                        })
                except AttributeError:
                    logger.warning("Reader has no 'root' attribute, trying alternative method")
                    # Try to manually construct a minimal AcroForm
                    writer._root_object.update({
                        NameObject("/AcroForm"): DictionaryObject()
                    })
                
                # Process fields into types
                all_fields = self.analyzer.get_field_names()
                field_types = {}
                for field in all_fields:
                    field_types[field] = self._get_field_type(field)
                
                # Create a safe copy of field data for processing
                fields_to_fill = {}
                for field_name, value in field_data.items():
                    # Skip if field doesn't exist in PDF
                    if field_name not in all_fields:
                        continue
                    
                    # If the field is a checkbox, convert the value to boolean
                    field_type = field_types.get(field_name)
                    if field_type == "Btn" and self._is_checkbox(field_name):
                        # Convert values to boolean
                        if isinstance(value, bool):
                            fields_to_fill[field_name] = value
                        elif isinstance(value, str):
                            fields_to_fill[field_name] = value.lower() in ["true", "yes", "y", "1", "on"]
                        else:
                            # Default to false for safety
                            fields_to_fill[field_name] = False
                    else:
                        # For non-checkbox fields, ensure we have a string value
                        pdf_field_name = field_name
                        fields_to_fill[pdf_field_name] = value
                
                # Now fill all fields by type
                for field_name, value in fields_to_fill.items():
                    field_type = field_types.get(field_name)
                    
                    if field_type == "Btn" and self._is_checkbox(field_name):
                        # Handle checkbox
                        self._fill_checkbox(writer, field_name, value)
                    elif field_type == "Btn":
                        # Handle radio button
                        self._fill_radio_button(writer, field_name, str(value))
                    else:
                        # Handle text and other fields - use the existing update method
                        update_fields = {field_name: value}
                        try:
                            for page_num, page in enumerate(writer.pages):
                                writer.update_page_form_field_values(
                                    page, update_fields, auto_regenerate=False
                                )
                        except Exception as e:
                            logger.warning(f"Failed to update field {field_name}: {e}")
                
                # Write to the output file
                with open(output_path, "wb") as output_file:
                    writer.write(output_file)
                
                # Flatten if requested
                if flatten:
                    self._flatten_pdf(output_path)
                
                return output_path
        
        except Exception as e:
            logger.error(f"Error filling form: {str(e)}")
            # Handle the common "PdfReader has no attribute 'root'" error
            if "has no attribute 'root'" in str(e):
                logger.warning("Encountered 'root' attribute error, trying alternative filling method")
                return self._fill_form_alternative(field_data, output_path, flatten)
            raise
    
    def get_form_areas(self) -> Dict[str, Dict[str, Union[int, float]]]:
        """
        Get the areas/coordinates of form fields (not fully supported in all PDFs).
        This is an experimental feature that tries to extract positioning information.
        """
        # This is a simplified implementation and may not work with all PDFs
        form_areas = {}
        
        for page_num, page in enumerate(self.analyzer.reader.pages):
            if '/Annots' in page:
                annotations = page['/Annots']
                for annot in annotations:
                    try:
                        annot_obj = annot.get_object()
                        if annot_obj.get('/Subtype') == '/Widget' and '/T' in annot_obj:
                            field_name = annot_obj['/T']
                            if '/Rect' in annot_obj:
                                rect = annot_obj['/Rect']
                                form_areas[field_name] = {
                                    'page': page_num,
                                    'x1': rect[0],
                                    'y1': rect[1],
                                    'x2': rect[2],
                                    'y2': rect[3],
                                }
                    except Exception as e:
                        # Skip problematic annotations
                        logger.debug(f"Error processing annotation: {str(e)}")
                            
        return form_areas

    def _is_checkbox(self, field_name: str) -> bool:
        """
        Determine if a field is a checkbox (rather than a radio button)
        """
        # Most reliable way is to check for specific checkbox flags or attributes
        try:
            field = self._get_field_by_name(field_name)
            if field is None:
                return False
            
            # Check if this is a checkbox by examining its attributes
            if "/AS" in field:  # It has an appearance state
                return True
            
            if "/FT" in field and field["/FT"] == "/Btn":
                # Check button flags to distinguish checkboxes from radio buttons
                if "/Ff" in field:
                    flags = field["/Ff"]
                    # Radio button flag is 16 (bit position 4)
                    radio_button_flag = 1 << 15
                    pushbutton_flag = 1 << 16
                    return not (flags & radio_button_flag or flags & pushbutton_flag)
                
            # Check field name patterns that typically indicate checkboxes
            checkbox_patterns = ['check', 'chk', 'checkbox', 'tick', 'toggle']
            return any(pattern in field_name.lower() for pattern in checkbox_patterns)
            
        except Exception as e:
            logger.error(f"Error determining if field {field_name} is checkbox: {str(e)}")
            # Default to False if we can't determine
            return False

    def _fill_checkbox(self, writer: PdfWriter, field_name: str, checked: bool) -> None:
        """
        Set a checkbox field value
        
        Args:
            writer: PDF writer object 
            field_name: Name of the field to fill
            checked: Whether the checkbox should be checked
        """
        try:
            # Get the field object
            field = self._get_field_by_name(field_name)
            if field is None:
                logger.warning(f"Checkbox field {field_name} not found")
                return
            
            # Find out what the 'on' value is for this checkbox
            on_value = None
            if "/AP" in field and "/N" in field["/AP"]:
                appearance_dict = field["/AP"]["/N"]
                for key in appearance_dict:
                    if key != "/Off" and not key.startswith('/'):
                        on_value = key
                        break
                    
            # If we couldn't determine the on value, use standard values
            if on_value is None:
                on_value = "/Yes"  # Common default
            
            # Set the value
            if checked:
                field[NameObject("/V")] = NameObject(on_value)
                field[NameObject("/AS")] = NameObject(on_value)
            else:
                field[NameObject("/V")] = NameObject("/Off")
                field[NameObject("/AS")] = NameObject("/Off")
            
        except Exception as e:
            logger.error(f"Error filling checkbox {field_name}: {str(e)}")

    def _fill_radio_button(self, writer: PdfWriter, field_name: str, value: str) -> None:
        """
        Set a radio button field value
        
        Args:
            writer: PDF writer object
            field_name: Name of the field to fill
            value: Value to set
        """
        try:
            field = self._get_field_by_name(field_name)
            if field is None:
                logger.warning(f"Radio button field {field_name} not found")
                return
            
            # Radio buttons can have multiple possible values
            # We need to find the one matching our desired value
            if value == "" or value.lower() == "off":
                # Clear selection
                field[NameObject("/V")] = NameObject("/Off")
                field[NameObject("/AS")] = NameObject("/Off")
            else:
                # Look for a matching option
                found = False
                if "/AP" in field and "/N" in field["/AP"]:
                    appearance_dict = field["/AP"]["/N"]
                    for key in appearance_dict:
                        if key != "/Off" and not key.startswith('/'):
                            # Option value, normalize for comparison
                            option = key[1:] if key.startswith('/') else key
                            if option.lower() == value.lower():
                                field[NameObject("/V")] = NameObject(key)
                                field[NameObject("/AS")] = NameObject(key)
                                found = True
                                break
                            
                if not found:
                    # Try direct assignment in case it's a simple radio button
                    option_name = f"/{value}" if not value.startswith('/') else value
                    field[NameObject("/V")] = NameObject(option_name)
                    field[NameObject("/AS")] = NameObject(option_name)
                
        except Exception as e:
            logger.error(f"Error filling radio button {field_name}: {str(e)}")

    def _get_field_by_name(self, field_name: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve the field object by name
        
        Args:
            field_name: Name of the field to retrieve
            
        Returns:
            Field object or None if not found
        """
        # Get the AcroForm dictionary
        if "/AcroForm" not in self.analyzer.reader.root or "/Fields" not in self.analyzer.reader.root["/AcroForm"]:
            return None
        
        fields = self.analyzer.reader.root["/AcroForm"]["/Fields"]
        
        # Search for the field by name
        for field in fields:
            obj = field.get_object()
            if "/T" in obj and obj["/T"] == field_name:
                return obj
            
            # If it has kids, search them
            if "/Kids" in obj:
                for kid in obj["/Kids"]:
                    kid_obj = kid.get_object()
                    if "/T" in kid_obj and kid_obj["/T"] == field_name:
                        return kid_obj
                    
        return None

    def _get_field_type(self, field_name: str) -> str:
        """
        Get the type of a form field
        
        Args:
            field_name: Name of the field
            
        Returns:
            Field type string ('Tx', 'Btn', 'Ch', etc.) or 'Unknown'
        """
        field = self._get_field_by_name(field_name)
        if field is None:
            return "Unknown"
        
        if "/FT" in field:
            field_type = field["/FT"]
            # Remove the leading slash if present
            if field_type.startswith('/'):
                field_type = field_type[1:]
            return field_type
        
        return "Unknown"

    def _fill_form_alternative(self, field_data: Dict[str, Any], output_path: str, flatten: bool = False) -> str:
        """
        Alternative method to fill a PDF form when the primary method fails.
        Uses a simpler approach that may be less prone to errors.
        
        Args:
            field_data: Dict mapping field names to values
            output_path: Path to save the filled PDF
            flatten: Whether to flatten the PDF
            
        Returns:
            Path to the filled PDF
        """
        try:
            # Try with a fresh reader/writer approach
            with open(self.pdf_path, 'rb') as file:
                reader = PdfReader(file)
                writer = PdfWriter()
                
                # Copy all pages
                for page in reader.pages:
                    writer.add_page(page)
                
                # Manually add a proper AcroForm dictionary
                if '/AcroForm' not in writer._root_object:
                    logger.info("Adding minimal /AcroForm dictionary to writer")
                    acroform = DictionaryObject()
                    acroform[NameObject('/Fields')] = ArrayObject()
                    writer._root_object[NameObject('/AcroForm')] = acroform
                
                # Get field names from the PDF
                field_names = set()
                fields = reader.get_fields()
                if fields:
                    field_names.update(fields.keys())
                else:
                    logger.warning("No form fields found in the PDF")
                
                # Copy form fields from the original PDF if possible
                try:
                    if hasattr(reader, 'root') and '/AcroForm' in reader.root:
                        logger.info("Copying AcroForm structure from original PDF")
                        writer._root_object[NameObject('/AcroForm')] = reader.root['/AcroForm']
                except Exception as e:
                    logger.warning(f"Could not copy AcroForm: {e}")
                
                # Prepare a safe subset of fields to fill
                safe_fields = {}
                for name, value in field_data.items():
                    if name in field_names:
                        # Convert boolean values to strings for checkboxes
                        if isinstance(value, bool):
                            safe_fields[name] = "Yes" if value else "Off"
                        else:
                            safe_fields[name] = value
                
                # Update fields - simpler approach with better error handling
                if safe_fields:
                    try:
                        writer.update_page_form_field_values(writer.pages[0], safe_fields)
                        logger.info(f"Updated {len(safe_fields)} fields using alternative method")
                    except Exception as field_e:
                        logger.error(f"Could not update fields: {field_e}")
                        # Add specific handling for known error types
                        if "No /AcroForm dictionary" in str(field_e):
                            logger.warning("PDF structure issue: No /AcroForm dictionary available")
                            # Since we've already tried to add one, this is a deeper structural issue
                            logger.warning("Skipping field updates and just returning a copy of the PDF")
                
                # Write to output file
                try:
                    with open(output_path, 'wb') as output_file:
                        writer.write(output_file)
                    logger.info(f"Wrote PDF to {output_path} using alternative method")
                except Exception as write_e:
                    logger.error(f"Failed to write PDF: {write_e}")
                    raise
                
                # If flattening is requested, do a separate pass for that
                if flatten:
                    self._flatten_pdf(output_path)
                
                return output_path
        
        except Exception as e:
            logger.error(f"Alternative form filling method also failed: {str(e)}")
            # As a last resort, just copy the original PDF
            logger.warning("Falling back to copying the original PDF without filling")
            with open(self.pdf_path, 'rb') as src, open(output_path, 'wb') as dst:
                dst.write(src.read())
            return output_path

    def _flatten_pdf(self, pdf_path: str) -> None:
        """
        Flatten a PDF (make form fields non-interactive)
        
        Args:
            pdf_path: Path to the PDF to flatten
        """
        try:
            # Create a temporary file for the flattened output
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                temp_path = temp_file.name
            
            # Use pdftron if available (best option for flattening)
            try:
                import pdftron
                pdftron.PDFNet.Initialize()
                doc = pdftron.PDFDoc(pdf_path)
                doc.FlattenAnnotations()
                doc.Save(temp_path, pdftron.SDFDoc.e_linearized)
                
                # Replace original with flattened version
                os.replace(temp_path, pdf_path)
                return
            except ImportError:
                logger.debug("pdftron not available, trying alternative method")
            
            # Try with pikepdf as alternative
            try:
                import pikepdf
                pdf = pikepdf.Pdf.open(pdf_path)
                
                # Iterate through pages
                for page in pdf.pages:
                    if '/Annots' in page:
                        # Remove annotations which include form fields
                        del page['/Annots']
                
                # Save flattened file
                pdf.save(temp_path)
                os.replace(temp_path, pdf_path)
                return
            except ImportError:
                logger.debug("pikepdf not available, trying PyPDF method")
            
            # Fall back to PyPDF method (least effective but most compatible)
            with open(pdf_path, 'rb') as file:
                reader = PdfReader(file)
                writer = PdfWriter()
                
                # Copy pages and attempt to flatten
                for page in reader.pages:
                    writer.add_page(page)
                    
                    # Remove /AcroForm to make fields non-interactive
                    if '/AcroForm' in writer._root_object:
                        del writer._root_object['/AcroForm']
                    
                    # Copy field values as text
                    if hasattr(page, '/Annots') and page['/Annots']:
                        # This is a simplified approach and may not work perfectly
                        annotations = page['/Annots']
                        page[NameObject('/Annots')] = []
                
                # Save the flattened PDF
                with open(temp_path, 'wb') as output:
                    writer.write(output)
                
                # Replace original with flattened version
                os.replace(temp_path, pdf_path)
        
        except Exception as e:
            logger.error(f"Error flattening PDF: {str(e)}")
            # If flattening fails, just leave the PDF as is


def main():
    """CLI interface for the enhanced PDF handler"""
    if len(sys.argv) < 2:
        print("Usage: python enhanced_pdf_handler.py <pdf_file> [action]")
        print("Actions:")
        print("  analyze (default) - Analyze the PDF and export field information")
        print("  test_fill - Test fill the PDF with sample data")
        sys.exit(1)
        
    pdf_path = sys.argv[1]
    action = sys.argv[2] if len(sys.argv) > 2 else "analyze"
    
    try:
        if action == "analyze":
            analyzer = PDFAnalyzer(pdf_path)
            
            # Print basic stats
            field_count = len(analyzer.get_field_names())
            print(f"PDF has {field_count} fillable fields")
            
            # Export field info
            output_path = analyzer.export_fields_info()
            print(f"Field information exported to: {output_path}")
            
            # Show field categories
            categories = analyzer.categorize_fields()
            print("\nField types summary:")
            for category, fields in categories.items():
                if fields:
                    print(f"  {category}: {len(fields)} fields")
                    
        elif action == "test_fill":
            # Sample data for testing
            sample_data = [
                {"field_name": "Name", "field_value": "John Doe"},
                {"field_name": "Email", "field_value": "john.doe@example.com"},
                {"field_name": "Date", "field_value": datetime.now().strftime("%Y-%m-%d")},
            ]
            
            filler = PDFFiller(pdf_path)
            output_path = filler.fill_form(sample_data)
            print(f"Test filled PDF saved to: {output_path}")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main() 