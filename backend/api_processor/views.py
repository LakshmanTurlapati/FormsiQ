from django.shortcuts import render
import os
import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.http import FileResponse, HttpResponse

from .serializers import (
    TranscriptInputSerializer,
    FieldExtractionOutputSerializer,
    PDFGenerationInputSerializer
)
from .ai_service import extract_fields_from_transcript, AIExtractionError
from .grok_service import extract_fields_with_grok, GrokExtractionError
from .pdf_service import fill_pdf_form, get_pdf_fields_info, PDFFillError

logger = logging.getLogger(__name__)


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
                logger.info("Using Grok 3 Mini model for field extraction")
                extracted_data = extract_fields_with_grok(transcript)
            else:
                logger.info("Using Gemma 3 model for field extraction")
                extracted_data = extract_fields_from_transcript(transcript)
            
            # Validate output
            output_serializer = FieldExtractionOutputSerializer(data=extracted_data)
            if not output_serializer.is_valid():
                logger.error(f"Invalid extraction output format: {output_serializer.errors}")
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
            fields_info = get_pdf_fields_info()
            return Response({"fields": fields_info}, status=status.HTTP_200_OK)
        except PDFFillError as e:
            return Response(
                {"error": "PDF field error", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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
        # Validate input
        serializer = PDFGenerationInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Invalid input", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        fields = serializer.validated_data['fields']
        
        try:
            # Fill the PDF form
            filled_pdf_path = fill_pdf_form(fields)
            
            # Return the filled PDF as a file download
            response = FileResponse(
                open(filled_pdf_path, 'rb'),
                content_type='application/pdf'
            )
            response['Content-Disposition'] = 'attachment; filename="filled_loan_application.pdf"'
            
            # Delete the temp file after it's been read
            response.close_file = True  # This will close the file when response is done
            
            return response
            
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
