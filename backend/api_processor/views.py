from django.shortcuts import render
import os
import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.http import FileResponse, HttpResponse, JsonResponse
import json
from datetime import datetime
import traceback
from urllib.parse import urljoin
from rest_framework.parsers import JSONParser
from pypdf.generic import NameObject

import inspect
from . import pdf_service
print(f"DEBUG: views.py is loading pdf_service from: {inspect.getfile(pdf_service)}")
from . import pdf_field_processor # Also check this directly from views if possible
print(f"DEBUG: views.py is loading pdf_field_processor directly from: {inspect.getfile(pdf_field_processor)}")

from .serializers import (
    TranscriptInputSerializer,
    FieldExtractionOutputSerializer,
    PDFGenerationInputSerializer
)
from .ai_service import extract_fields_from_transcript, AIExtractionError
from .grok_service import extract_fields_with_grok, GrokExtractionError
from .pdf_service import fill_pdf_form, get_pdf_fields_info, PDFFillError
from .pdf_field_processor import PDFFieldProcessor
from django.conf import settings

logger = logging.getLogger(__name__)

# Clean up existing PDF files in the output directory on startup
def cleanup_output_pdfs():
    """Delete all existing PDF files in the output directory."""
    try:
        output_dir = os.path.join(settings.MEDIA_ROOT, 'pdf', 'output')
        if not os.path.exists(output_dir):
            return
            
        count = 0
        for filename in os.listdir(output_dir):
            if filename.endswith('.pdf'):
                file_path = os.path.join(output_dir, filename)
                try:
                    os.unlink(file_path)
                    count += 1
                except Exception as e:
                    logger.error(f"Error deleting file {file_path}: {e}")
        
        logger.info(f"Cleaned up {count} PDF files from output directory")
    except Exception as e:
        logger.error(f"Error cleaning up output PDFs: {e}")

# Run cleanup on module import
cleanup_output_pdfs()

class ExtractFieldsView(APIView):
    """
    API endpoint for extracting fields from call transcripts.
    """
    
    def post(self, request):
        """
        POST request handler for field extraction.
        
        Args:
            request: The API request
            
        Returns:
            Response: The API response with extracted fields or error
        """
        # Validate input
        serializer = TranscriptInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Invalid input", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        transcript = serializer.validated_data['transcript']
        
        # Get the model selection from the request (default to "gemma")
        model = serializer.validated_data.get('model', 'gemma')
        
        try:
            # Extract fields using the selected AI service
            if model.lower() == 'grok':
                extracted_data = extract_fields_with_grok(transcript)
            else:
                extracted_data = extract_fields_from_transcript(transcript)
            
            # Validate output
            output_serializer = FieldExtractionOutputSerializer(data=extracted_data)
            if not output_serializer.is_valid():
                # Only log critical error
                print(f"Invalid extraction output format: {output_serializer.errors}")
                return Response(
                    {"error": "Invalid extraction output format", "details": output_serializer.errors},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Return the extracted fields
            return Response(extracted_data, status=status.HTTP_200_OK)
            
        except (AIExtractionError, GrokExtractionError) as e:
            logger.error(f"AI extraction error: {str(e)}")
            return Response(
                {"error": "AI extraction error", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            logger.error(f"Unexpected error in field extraction: {str(e)}")
            return Response(
                {"error": "Unexpected error", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GetPDFFieldsView(APIView):
    """
    API endpoint for getting PDF field information.
    This is mainly for development/debugging purposes.
    """
    
    def get(self, request):
        """
        GET request handler for PDF field information.
        
        Args:
            request: The API request
            
        Returns:
            Response: The API response with PDF field information or error
        """
        try:
            fields_info = get_pdf_fields_info() # This is Dict[internal_key, Dict[str, Any]]
            
            # --- TEMPORARY LOGGING FOR DESCRIPTIVE NAMES ---
            if fields_info:
                descriptive_names = sorted(list(set([details.get('name') for details in fields_info.values() if details.get('name')])))
                logger.info("--- Descriptive PDF Field Names (/T values) ---")
                for name in descriptive_names:
                    logger.info(f"  {name}")
                logger.info(f"Total {len(descriptive_names)} descriptive names found.")
                logger.info("--- End of Descriptive PDF Field Names ---")
            
            # Get checkbox and radio button details
            pdf_template_path = os.path.join(settings.MEDIA_ROOT, 'pdf', 'uniform_residential_loan_application.pdf')
            processor = PDFFieldProcessor(pdf_template_path)
            
            # Get checkbox details
            checkbox_fields = processor.list_checkbox_fields()
            if checkbox_fields:
                logger.info("--- PDF Checkbox Fields ---")
                for key, details in checkbox_fields.items():
                    logger.info(f"  Checkbox Key: {key}")
                    logger.info(f"    Descriptive Name: {details.get('partial_name')}")
                    logger.info(f"    Current Value: {details.get('current_value')}")
                    logger.info(f"    'ON' State Value: {details.get('on_state_value')}")
                logger.info(f"Total {len(checkbox_fields)} checkbox fields found.")
                logger.info("--- End of PDF Checkbox Fields ---")
                
            # Get radio button details
            radio_groups = {}
            for field_name, field_obj in processor.fields.items():
                if field_obj.get('/FT') == NameObject('/Btn') and field_obj.get('/Kids'):
                    radio_groups[field_name] = {
                        'name': field_obj.get('/T', field_name),
                        'kids_count': len(field_obj.get('/Kids', [])),
                    }
            
            if radio_groups:
                logger.info("--- PDF Radio Button Groups ---")
                for key, details in radio_groups.items():
                    logger.info(f"  Radio Group Key: {key}")
                    logger.info(f"    Descriptive Name: {details.get('name')}")
                    logger.info(f"    Options Count: {details.get('kids_count')}")
                logger.info(f"Total {len(radio_groups)} radio button groups found.")
                logger.info("--- End of PDF Radio Button Groups ---")
            
            return Response({
                'pdf_fields_info': fields_info,
                'checkbox_fields': checkbox_fields,
                'radio_groups': radio_groups,
                'field_count': len(fields_info) if fields_info else 0,
                'checkbox_count': len(checkbox_fields) if checkbox_fields else 0,
                'radio_group_count': len(radio_groups) if radio_groups else 0
            })
        except Exception as e:
            logger.error(f"Error in GetPDFFieldsView: {str(e)}")
            return Response({'error': str(e)}, status=500)


class FillPDFView(APIView):
    """
    API endpoint for filling the PDF form with extracted data.
    """
    
    def post(self, request):
        """
        POST request handler for PDF filling.
        
        Args:
            request: The API request
            
        Returns:
            FileResponse: The filled PDF file
        """
        logger.debug(f"Request body: {request.body}")
        try:
            try:
                data = json.loads(request.body.decode('utf-8'))
            except json.JSONDecodeError:
                return JsonResponse({'error': 'Invalid JSON in request body'}, status=400)
                
            fields = data.get('fields')
            perform_fill_flag = data.get('perform_fill', True) # Get the flag, default to True
            
            if fields is None:
                return JsonResponse({'error': 'Missing "fields" in request body'}, status=400)
                
            # For direct fill requests (perform_fill_flag True), generate PDF and return JSON with pdf_url
            service_result = fill_pdf_form(data)
            response_data_for_ui = service_result['response_data']
            return JsonResponse(response_data_for_ui, status=200)
            
        except PDFFillError as e:
            logger.error(f"PDF filling error: {str(e)}")
            return Response(
                {"error": "PDF filling error", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            logger.error(f"Unexpected error in PDF filling: {str(e)}")
            return Response(
                {"error": "Unexpected error", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


def process_transcript(request):
    """
    Process a transcript to extract data and fill a PDF form.
    This is the main endpoint that receives transcripts, extracts data, and returns processed results.
    """
    if request.method == 'POST':
        try:
            # Use request.body to handle large files and non-form data
            data = json.loads(request.body.decode('utf-8'))
            transcript = data.get('transcript')
            
            # Extract data using the chosen AI API
            extraction_result = extract_fields_with_grok(transcript)
            
            # Save raw extraction results for debugging
            with open("extraction_results.json", "w") as f:
                json.dump(extraction_result, f, indent=4)
            
            # Check if extraction was successful
            if not extraction_result or 'fields' not in extraction_result:
                logger.error("Field extraction failed or returned no fields.")
                return JsonResponse({
                    'status': 'error',
                    'message': 'Could not extract fields from transcript.'
                })
                
            logger.info(f"Successfully extracted {len(extraction_result.get('fields', []))} fields from transcript.")
            
            # Save raw Grok response to a file for debugging
            with open("grok_raw.txt", "w") as f:
                f.write("=== RAW GROK RESPONSE ===\n")
                f.write(json.dumps(extraction_result, indent=2))
                f.write("\n=== END RAW GROK RESPONSE ===\n")
            
            # Check if we have fields to process
            if not extraction_result.get('fields'):
                logger.warning("No fields extracted from transcript.")
                return JsonResponse({
                    'status': 'warning',
                    'message': 'No fields were extracted from the transcript. Please check the transcript content.',
                    'fields': [],
                    'pdf_mapping': {
                        'pdf_generation_status': 'skipped',
                        'message': 'No fields to map to PDF.',
                        'mapped_field_count': 0
                    }
                })
            
            # Add the perform_fill flag to trigger PDF filling
            extraction_result['perform_fill'] = True
            
            # Process the extracted data and fill a PDF form if requested
            pdf_result = fill_pdf_form(extraction_result)
            
            # Check if PDF filling was successful
            if pdf_result.get('pdf_generation_status') != 'success':
                logger.warning("PDF generation was not successful.")
                
            response_data = {
                'status': 'success',
                'fields': extraction_result.get('fields', []),
                'pdf_mapping': pdf_result
            }
            
            return JsonResponse(response_data)
            
        except Exception as e:
            logger.exception(f"Exception in process_transcript: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': f'An error occurred: {str(e)}'
            }, status=500)
            
    # Return method not allowed for non-POST requests
    return JsonResponse({
        'status': 'error',
        'message': 'Only POST requests are supported.'
    }, status=405)
