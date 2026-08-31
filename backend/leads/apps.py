import os
import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class LeadsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'leads'

    def ready(self):
        """Display API key status on startup"""
        self.print_startup_warning()

    @staticmethod
    def print_startup_warning():
        """Print important startup information about API keys"""
        
        # Check which API keys are configured
        serpapi_key = os.getenv('SERPAPI_KEY', '').strip()
        google_api_key = os.getenv('GOOGLE_API_KEY', '').strip()
        google_cx = os.getenv('GOOGLE_CX', '').strip()
        apify_key = os.getenv('APIFY_API_KEY', '').strip()
        gemini_key = os.getenv('GEMINI_API_KEY', '').strip()
        
        print("\n" + "="*80)
        print("🚨 Important: Is this a problem?")
        print("="*80)
        
        print("\n✅ NOT a problem IF:")
        print("   • You're just testing basic backend")
        print("   • You're not using:")
        print("     - Google Search API")
        print("     - SerpAPI")
        print("     - Apify scraping")
        print("     - Gemini AI")
        print("\n   👉 In that case, you can ignore these warnings.")
        
        print("\n❌ PROBLEM IF:")
        print("   • You expect features like:")
        print("     - scraping (Apify)")
        print("     - search results (SerpAPI / Google CX)")
        print("     - AI responses (Gemini)")
        print("\n   👉 Then they will NOT work because keys are empty.")
        
        print("\n🧠 Why it's happening")
        print("   Either:")
        print("   1. .env file does NOT exist")
        print("   2. Docker Compose is NOT loading it")
        
        print("\n📋 Current API Key Status:")
        print(f"   {'SERPAPI_KEY':<20} {'✅ SET' if serpapi_key else '❌ MISSING'}")
        print(f"   {'GOOGLE_API_KEY':<20} {'✅ SET' if google_api_key else '❌ MISSING'}")
        print(f"   {'GOOGLE_CX':<20} {'✅ SET' if google_cx else '❌ MISSING'}")
        print(f"   {'APIFY_API_KEY':<20} {'✅ SET' if apify_key else '❌ MISSING'}")
        print(f"   {'GEMINI_API_KEY':<20} {'✅ SET' if gemini_key else '❌ MISSING'}")
        
        print("\n" + "="*80)
        print("✨ Backend is ready! Features without API keys will still work.")
        print("="*80 + "\n")