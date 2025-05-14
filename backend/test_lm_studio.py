#!/usr/bin/env python
"""
Test script to verify the connection to the LM Studio API.
Run this script to confirm that LM Studio is properly configured and accessible.
"""
import requests
import json
import sys

# LM Studio API endpoint (default)
LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"

def test_lm_studio_connection():
    """Test connection to LM Studio API with a simple prompt."""
    print(f"Testing connection to LM Studio API at {LM_STUDIO_URL}...")
    
    # Simple test payload
    payload = {
        "model": "gemma-3-12b",  # This should match the model loaded in LM Studio
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, are you working properly? Please respond with a simple 'Yes, I am working' if you can hear me."}
        ],
        "temperature": 0.1,
        "max_tokens": 500
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        # Make the request to LM Studio
        response = requests.post(
            LM_STUDIO_URL, 
            headers=headers, 
            json=payload,
            timeout=30  # 30 second timeout
        )
        
        # Check for success
        response.raise_for_status()
        
        # Parse the response
        response_json = response.json()
        
        # Extract and print the model's response
        if 'choices' in response_json and len(response_json['choices']) > 0:
            content = response_json['choices'][0]['message']['content']
            print("\nLM Studio API responded successfully! Response:")
            print("-" * 60)
            print(content)
            print("-" * 60)
            print("\nConnection test successful. LM Studio is properly configured.")
            return True
        else:
            print("\nError: Received unexpected response format from LM Studio.")
            print(json.dumps(response_json, indent=2))
            return False
            
    except requests.RequestException as e:
        print(f"\nError connecting to LM Studio: {str(e)}")
        print("\nPossible issues:")
        print("  1. LM Studio is not running")
        print("  2. LM Studio server is not started (go to Local Server tab and start it)")
        print("  3. The API endpoint URL is incorrect (default is http://localhost:1234)")
        print("  4. No model is loaded in LM Studio")
        return False

if __name__ == "__main__":
    success = test_lm_studio_connection()
    sys.exit(0 if success else 1) 