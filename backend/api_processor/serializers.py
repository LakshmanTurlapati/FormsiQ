from rest_framework import serializers

class TranscriptInputSerializer(serializers.Serializer):
    """Serializer for receiving call transcripts."""
    transcript = serializers.CharField(required=True)
    model = serializers.CharField(required=False, default='gemma')  # Add model selection, default to Gemma

class FieldExtractSerializer(serializers.Serializer):
    """Serializer for individual extracted fields."""
    field_name = serializers.CharField(required=False)
    name = serializers.CharField(required=False)  # Allow 'name' as an alternative to 'field_name'
    field_value = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    value = serializers.CharField(allow_null=True, allow_blank=True, required=False)  # Allow 'value' as an alternative to 'field_value'
    confidence_score = serializers.FloatField(required=False)
    confidence = serializers.FloatField(required=False)  # Allow 'confidence' as an alternative
    conf = serializers.FloatField(required=False)  # Allow 'conf' as an alternative
    
    def validate(self, data):
        """Ensure at least one name field and one value field is present."""
        if not ('field_name' in data or 'name' in data):
            raise serializers.ValidationError("Either 'field_name' or 'name' is required.")
        
        # Copy name to field_name if needed
        if 'name' in data and 'field_name' not in data:
            data['field_name'] = data['name']
            
        # Copy value to field_value if needed
        if 'value' in data and 'field_value' not in data:
            data['field_value'] = data['value']
            
        # Normalize confidence score
        if 'confidence' in data and 'confidence_score' not in data:
            data['confidence_score'] = data['confidence']
        elif 'conf' in data and 'confidence_score' not in data:
            # Convert 0-100 to 0-1 if needed
            conf = data['conf']
            data['confidence_score'] = conf / 100.0 if conf > 1.0 else conf
            
        return data

class FieldExtractionOutputSerializer(serializers.Serializer):
    """Serializer for the complete output of field extraction."""
    fields = FieldExtractSerializer(many=True)

class PDFGenerationInputSerializer(serializers.Serializer):
    """Serializer for receiving field data to generate a PDF."""
    fields = FieldExtractSerializer(many=True, required=True) 