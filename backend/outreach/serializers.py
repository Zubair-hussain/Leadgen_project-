from rest_framework import serializers

from leads.models import Lead

from .models import OutreachMessage, Suppression
from .services import content_warnings, normalize


class OutreachMessageSerializer(serializers.ModelSerializer):
    lead_id = serializers.PrimaryKeyRelatedField(
        source='lead', queryset=Lead.objects.none(), required=False, allow_null=True,
    )
    to_email = serializers.EmailField(required=False)
    warnings = serializers.SerializerMethodField()

    class Meta:
        model = OutreachMessage
        fields = [
            'id', 'lead_id', 'to_email', 'subject', 'body', 'status', 'skip_reason',
            'error', 'gmail_message_id', 'gmail_thread_id', 'dry_run', 'notified_at', 'notify_error',
            'approved_at', 'sent_at', 'created_at', 'updated_at', 'warnings',
        ]
        read_only_fields = [
            'status', 'skip_reason', 'error', 'gmail_message_id', 'gmail_thread_id',
            'dry_run', 'notified_at', 'notify_error', 'approved_at', 'sent_at', 'created_at', 'updated_at',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request is not None and request.user.is_authenticated:
            self.fields['lead_id'].queryset = Lead.objects.filter(owner=request.user)

    def get_warnings(self, obj):
        return content_warnings(obj.subject, obj.body)

    def validate(self, attrs):
        lead = attrs.get('lead', getattr(self.instance, 'lead', None))
        to_email = attrs.get('to_email') or getattr(self.instance, 'to_email', '')
        if not to_email and lead is not None:
            to_email = lead.email or ''
        if not to_email:
            raise serializers.ValidationError({'to_email': 'Provide to_email or a lead that has an email.'})
        attrs['to_email'] = normalize(to_email)
        return attrs


class SuppressionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Suppression
        fields = ['id', 'email', 'reason', 'note', 'created_at']
        read_only_fields = ['created_at']

    def validate_email(self, value):
        return normalize(value)
