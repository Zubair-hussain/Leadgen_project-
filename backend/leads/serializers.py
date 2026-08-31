from rest_framework import serializers
from .models import Lead

class LeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lead
        fields = [
            'id', 'email', 'phone', 'source', 'category', 'service', 
            'location', 'found_at', 'link', 'problem_statement', 'is_verified'
        ]
        read_only_fields = ['found_at']