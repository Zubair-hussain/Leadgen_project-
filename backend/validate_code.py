#!/usr/bin/env python
"""
Simple validation script for the refactored backend code.
Tests imports and basic functionality without requiring database.
"""

import os
import sys
import django
from pathlib import Path

# Setup Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leadgen.settings')

try:
    django.setup()
    print("✓ Django setup successful")
except Exception as e:
    print(f"✗ Django setup failed: {e}")
    sys.exit(1)

# Test imports
try:
    from leads.models import Lead
    from leads.serializers import LeadSerializer
    from leads.services import EmailVerifier, LeadGenerator
    from leads.views import health_check
    print("✓ All imports successful")
except ImportError as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

# Test EmailVerifier
try:
    verifier = EmailVerifier()
    # Test valid email
    assert verifier.is_valid_syntax("test@example.com") == True
    # Test invalid email
    assert verifier.is_valid_syntax("invalid-email") == False
    # Test blocked domain
    assert verifier.is_valid_syntax("test@noemail.com") == False
    print("✓ EmailVerifier tests passed")
except Exception as e:
    print(f"✗ EmailVerifier test failed: {e}")
    sys.exit(1)

# Test Lead model
try:
    # Test model creation (without saving)
    lead = Lead(
        email="test@example.com",
        phone="+1234567890",
        source="test",
        category="test",
        location="Test City"
    )
    # Test phone normalization
    lead.clean_phone()
    assert lead.phone == "+1234567890"  # Should remain formatted
    print("✓ Lead model tests passed")
except Exception as e:
    print(f"✗ Lead model test failed: {e}")
    sys.exit(1)

# Test serializer
try:
    serializer = LeadSerializer(lead)
    data = serializer.data
    assert 'email' in data
    assert 'phone' in data
    assert data['email'] == "test@example.com"
    print("✓ Serializer tests passed")
except Exception as e:
    print(f"✗ Serializer test failed: {e}")
    sys.exit(1)

print("\n🎉 All validation tests passed! Backend code is ready for review.")