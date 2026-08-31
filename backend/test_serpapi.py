import os
import serpapi
from dotenv import load_dotenv

def test_serpapi():
    # Load dotenv from backend folder
    load_dotenv()
    
    # Check OS env first (set by docker-compose)
    api_key = os.getenv("SERPAPI_KEY")
    
    if not api_key or api_key == "your-serpapi-key":
        print(f"Error: SERPAPI_KEY is still invalid: '{api_key}'")
        return

    print(f"Testing SerpApi with key starting with: {api_key[:10]}...")
    
    params = {
        "q": "Coffee",
        "api_key": api_key
    }

    try:
        # Check standard client
        client = serpapi.Client(api_key=api_key)
        results = client.search(params)
        
        if "error" in results:
            print(f"API Error: {results['error']}")
        elif "search_metadata" in results:
            print("Success! SerpApi connection established.")
            print(f"Search ID: {results['search_metadata'].get('id')}")
            print(f"Status: {results['search_metadata'].get('status')}")
        else:
            print(f"Unexpected response format: {results.keys()}")
            
    except Exception as e:
        print(f"Connection failed: {str(e)}")

if __name__ == "__main__":
    test_serpapi()
