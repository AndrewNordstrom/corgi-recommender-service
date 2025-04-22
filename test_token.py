#!/usr/bin/env python3
"""
Script to test Mastodon token recognition by the Corgi proxy
"""

import requests
import logging
import sys

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('test')

def test_token(token):
    """Test token recognition by the Corgi proxy"""
    
    # Server URL
    base_url = "http://localhost:8000"
    
    # Test endpoints
    endpoints = [
        "/api/v1/proxy/instance",  # Debug endpoint to check instance detection
        "/api/v1/proxy/status",    # General proxy status
        "/api/v1/timelines/home",  # Home timeline endpoint that uses proxy
    ]
    
    # Authorization header with the token
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    logger.info(f"Testing token: {token[:5]}...")
    
    for endpoint in endpoints:
        url = f"{base_url}{endpoint}"
        logger.info(f"Calling endpoint: {url}")
        
        try:
            # Make the request
            response = requests.get(url, headers=headers)
            
            # Check the response
            if response.status_code == 200:
                logger.info(f"Endpoint {endpoint} returned success")
                logger.info(f"Response: {response.json()}")
            else:
                logger.error(f"Endpoint {endpoint} returned status {response.status_code}")
                logger.error(f"Response: {response.text}")
        except Exception as e:
            logger.error(f"Error calling {endpoint}: {e}")

def main():
    # Mastodon token to test
    token = "_Tb8IUyXBZ5Y8NmUcwY0-skXWQgP7xTVMZCFkqvZRIc"
    
    # Run the test
    test_token(token)

if __name__ == "__main__":
    main()