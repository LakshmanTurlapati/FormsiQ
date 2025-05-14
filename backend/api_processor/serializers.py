from rest_framework import serializers

class TranscriptInputSerializer(serializers.Serializer):
    """Serializer for receiving call transcripts."""
    transcript = serializers.CharField(required=True)
    model = serializers.CharField(required=False, default='gemma')  # Add model selection, default to Gemma

class FieldExtractSerializer(serializers.Serializer):
    """Serializer for individual extracted fields."""
    field_name = serializers.CharField()
    field_value = serializers.CharField(allow_null=True, allow_blank=True)
    confidence_score = serializers.FloatField()

class FieldExtractionOutputSerializer(serializers.Serializer):
    """Serializer for the complete output of field extraction."""
    fields = FieldExtractSerializer(many=True)

class PDFGenerationInputSerializer(serializers.Serializer):
    """Serializer for receiving field data to generate a PDF."""
    fields = FieldExtractSerializer(many=True) 