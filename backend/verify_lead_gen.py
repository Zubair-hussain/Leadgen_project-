import os
import sys
import django
from dotenv import load_dotenv

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leadgen.settings')
django.setup()

from leads.views import generate_leads_from_sources

def test_lead_gen():
    print("Testing Lead Generation...")
    
    # Test case 1: Local business search (Should trigger Maps)
    category = "Dentist"
    location = "London"
    print(f"\n--- Searching for {category} in {location} ---")
    leads = generate_leads_from_sources(category, "looking for dental services", ["x"], target_location=location)
    
    print(f"Found {len(leads)} leads.")
    for l in leads[:5]:
        print(f"[{l['source']}] {l['email']} | {l['phone']} | {l['link']}")

    # Test case 2: Client search (Should trigger strict filtering)
    category = "Web Design"
    niche = "Real Estate"
    print(f"\n--- Searching for {category} clients in {niche} ---")
    leads = generate_leads_from_sources(category, "I need a website for my agency", ["x"], niche=niche)
    
    print(f"Found {len(leads)} leads.")
    for l in leads[:5]:
        print(f"[{l['source']}] {l['email']} | {l['problem_statement'][:50]}...")

if __name__ == "__main__":
    test_lead_gen()
