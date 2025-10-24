#!/usr/bin/env python3
"""
Script to help prepare the GOOGLE_TOKEN_JSON environment variable for Render deployment.
This script reads your local token.json and outputs the properly formatted JSON string.
"""

import json
import os

def prepare_token_for_render():
    """Convert token.json to a format suitable for Render environment variable"""
    
    token_file = "token.json"
    
    if not os.path.exists(token_file):
        print("❌ token.json file not found!")
        print("Please make sure you have completed the OAuth2 flow and have a token.json file.")
        return None
    
    try:
        # Read the token file
        with open(token_file, 'r') as f:
            token_data = json.load(f)
        
        # Convert to JSON string (escaped for environment variable)
        token_json_string = json.dumps(token_data)
        
        print("✅ Successfully prepared GOOGLE_TOKEN_JSON for Render")
        print("\n" + "="*60)
        print("COPY THE FOLLOWING TO YOUR RENDER ENVIRONMENT VARIABLE:")
        print("="*60)
        print(f"Key: GOOGLE_TOKEN_JSON")
        print(f"Value: {token_json_string}")
        print("="*60)
        print("\n📝 Instructions:")
        print("1. Go to your Render service dashboard")
        print("2. Navigate to Environment tab")
        print("3. Add new environment variable:")
        print("   - Key: GOOGLE_TOKEN_JSON")
        print("   - Value: [paste the value above]")
        print("4. Save and redeploy your service")
        
        return token_json_string
        
    except json.JSONDecodeError as e:
        print(f"❌ Error reading token.json: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None

if __name__ == "__main__":
    prepare_token_for_render()
