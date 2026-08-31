from django.db import models
from django.utils import timezone
from django.core.validators import EmailValidator
import phonenumbers


class Lead(models.Model):
    email = models.EmailField(
        unique=True,
        null=True,
        blank=True,
        validators=[EmailValidator()],
        help_text="Unique email address of the lead"
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        help_text="Phone number (international format preferred)"
    )
    source = models.CharField(
        max_length=100,
        help_text="Source platform (e.g., upwork, reddit, x, google-maps)"
    )
    category = models.CharField(
        max_length=100,
        default="unknown",
        blank=True,
        help_text="Business category or service type"
    )
    service = models.CharField(
        max_length=100,
        blank=True,
        help_text="Specific service offered or needed"
    )
    location = models.CharField(
        max_length=255,
        blank=True,
        help_text="Geographic location of the lead"
    )
    link = models.URLField(
        blank=True,
        help_text="URL to the original source or profile"
    )
    problem_statement = models.TextField(
        blank=True,
        help_text="Description of the problem or service request"
    )
    found_at = models.DateTimeField(
        default=timezone.now,
        help_text="When this lead was discovered"
    )
    created_at = models.DateTimeField(
        default=timezone.now,
        help_text="When this record was created"
    )
    is_verified = models.BooleanField(
        default=False,
        help_text="Whether the email has been verified"
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['source']),
            models.Index(fields=['category']),
            models.Index(fields=['is_verified']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.email} ({self.source})"

    def clean_phone(self):
        """Normalize phone number if possible"""
        if self.phone:
            try:
                parsed = phonenumbers.parse(self.phone, None)
                if phonenumbers.is_valid_number(parsed):
                    self.phone = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
            except phonenumbers.NumberParseException:
                pass  # Keep original if parsing fails
        return self.phone

    def save(self, *args, **kwargs):
        self.clean_phone()
        super().save(*args, **kwargs)