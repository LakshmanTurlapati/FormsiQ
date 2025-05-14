"""
Test script for calling the Grok API directly to check if the API key and endpoint are working.
"""
import os
import json
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API key from environment
api_key = os.getenv("GROK_API_KEY")

if not api_key:
    print("ERROR: No Grok API key found in .env file")
    exit(1)

print(f"Using API key: {api_key[:5]}...{api_key[-5:]}")

def test_grok_model(model_name, max_tokens=200):
    print(f"\n=== Testing model: {model_name} ===")
    
    try:
        # Initialize OpenAI client with xAI base URL and API key
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.x.ai/v1",
        )
        
        print("Client initialized successfully")
        
        # Test prompt
        system_prompt = "You are a helpful assistant."
        user_prompt = "Explain why the sky is blue in 2-3 sentences."
        
        print(f"Sending request to Grok API...")
        
        # Make the API call using the client
        completion = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=max_tokens,
        )
        
        print("Response received!")
        print("\nResponse content:")
        content = completion.choices[0].message.content
        print(content or "EMPTY CONTENT")
        
        reasoning = completion.choices[0].message.reasoning_content
        if reasoning:
            print("\nReasoning content:")
            print(reasoning)
        
        # Print model name from response
        if hasattr(completion, 'model'):
            print(f"\nModel used: {completion.model}")
        
        print("\nTest completed successfully for", model_name)
        return True
        
    except Exception as e:
        print(f"ERROR with {model_name}: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

# Test different models
models_to_test = [
    "grok-3-mini", 
    "grok-3"
]

for model in models_to_test:
    test_grok_model(model) 